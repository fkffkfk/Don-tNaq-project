# 낚낚시꾼 백엔드 (Naqjima Backend)

피싱 URL 탐지 서비스의 Flask 기반 백엔드입니다.  
QR 코드 보안 검증, ML 앙상블 모델을 이용한 악성 URL 분류, 사용자 관리 기능을 제공합니다.

---

## 기술 스택

| 분류 | 기술 |
|---|---|
| 웹 프레임워크 | Flask 3.x + Gunicorn |
| DB | MySQL 8.0 |
| 캐시 / Rate Limit | Redis 7 |
| ML | scikit-learn · XGBoost · LightGBM · CatBoost |
| 컨테이너 | Docker + Docker Compose |
| Python | 3.11 (가상환경 / Docker 권장) |

---

## 아키텍처 개요

```
클라이언트 (앱/웹)
        │
        ▼
  Gunicorn (워커 2개)
        │
        ▼
   Flask app.py
  ┌─────────────────────────────────────┐
  │  Blueprint 라우터                    │
  │  user_api / scan_api / model_api    │
  │  qr_api / stats_api / posts_api     │
  └──────────────┬──────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
   services/          MySQL DB
   model_service      scan_history
   qr_service         model_result
   user_service       users · posts
        │
        ▼
  ML 파이프라인
  feature_extractor → [XGB·LGB·CAT] → 앙상블 score
        │
        ▼
     Redis
  (캐시 · Rate Limit)
```

### 왜 이 구조인가

**Blueprint + Service 분리**  
라우터(`*_api.py`)는 HTTP 요청/응답만 담당하고, 실제 로직은 `services/` 안에 분리했습니다.  
덕분에 API 엔드포인트를 바꾸지 않고도 내부 로직을 독립적으로 수정할 수 있습니다.

**Gunicorn 멀티 워커**  
Flask 내장 서버는 요청을 한 번에 하나씩만 처리하고 에러 발생 시 서버 전체가 죽습니다.  
Gunicorn은 워커 2개가 동시에 요청을 받고, 워커 하나가 죽어도 나머지가 계속 동작하며 master가 자동 재시작합니다.  
`--timeout 120`은 DNS/SSL 실시간 조회처럼 오래 걸리는 작업을 고려한 설정입니다.

**Redis 이중 역할**  
Rate Limiter(flask-limiter)와 Cache(flask-caching) 모두 Redis를 백엔드로 씁니다.  
URL 예측 결과를 Redis에 캐싱해두면 동일 URL 재요청 시 ML 모델을 다시 돌리지 않아도 됩니다.

**블랙/화이트리스트 → 모델 순서**  
ML 예측은 DNS·SSL 실시간 조회 때문에 수 초가 걸릴 수 있습니다.  
DB 조회만으로 판단 가능한 블랙리스트와 화이트리스트를 먼저 확인해 불필요한 모델 호출을 줄입니다.

---

## ML 모델 동작 방식

### 파일 구성

| 파일 | 역할 |
|---|---|
| `ens_1021_xgb.pkl` | XGBoost 모델 |
| `ens_1021_lgb.pkl` | LightGBM 모델 |
| `ens_1021_cat.pkl` | CatBoost 모델 |
| `1021_feature_params.pkl` | 피처 정규화 기준값 (평균·표준편차·키워드 목록) |
| `ens_1021_config.json` | 앙상블 가중치 · 임계값 · 리스크 플래그 목록 |

### 앱 시작 시 (1회)

```
gunicorn 기동
  └─ model_service.py import
       ├─ joblib.load("ens_1021_xgb.pkl") → XGB 객체 메모리 상주
       ├─ joblib.load("ens_1021_lgb.pkl") → LGB 객체 메모리 상주
       ├─ joblib.load("ens_1021_cat.pkl") → CAT 객체 메모리 상주
       └─ joblib.load("1021_feature_params.pkl") → PARAMS 객체 메모리 상주
```

pkl 파일은 시작 시 딱 한 번만 읽습니다. 이후 요청이 들어올 때마다 메모리 객체를 재사용하므로 디스크 I/O가 없습니다.

### POST /model-results 요청 시

```
1. scan_history에서 scan_id → URL 조회 (DB)

2. 블랙리스트 확인 (DB sha256 매칭)
   → hit: score=1.0 저장, 422 반환 종료

3. 화이트리스트 확인 (신뢰 도메인 · 프로젝트 URL)
   → hit: score=0.0 저장, 200 반환 종료

4. 피처 추출 (feature_extractor.py)
   ├─ HTTPS 여부, 의심 키워드 (ExistenceBased)
   ├─ URL 길이 이상 여부 (LengthBased) ← PARAMS.url_avg, url_std 사용
   ├─ 특수문자·글자 수 이상 여부 (CountBased) ← PARAMS.schar_avg 사용
   ├─ DNS TTL · NS 일치 여부 (실시간 네트워크 조회)
   └─ SSL 인증서 상태 (실시간 네트워크 조회)
   → 17개 숫자 벡터 생성

5. 앙상블 예측 (메모리 객체 사용, 디스크 접근 없음)
   p_xgb = XGB.predict_proba(X)[:, 1]
   p_lgb = LGB.predict_proba(X)[:, 1]
   p_cat = CAT.predict_proba(X)[:, 1]
   score = (w1*p_xgb + w2*p_lgb + w3*p_cat) / (w1+w2+w3)
   ← 가중치 W는 ens_1021_config.json에서 로드

6. 임계값 판정
   리스크 플래그 2개 이상 → THR_RISK (0.3, 더 엄격)
   그 외               → THR_DEFAULT (0.5)
   score >= 임계값 → 악성 / 미만 → 정상

7. model_result 테이블 저장
```

---

## 프로젝트 구조

```
.
├── app.py                  # Flask 앱 진입점, Blueprint 등록
├── db.py                   # MySQL 커넥션 (환경변수 기반)
├── cache_config.py         # Flask-Caching (Redis)
├── limiter_config.py       # Flask-Limiter (Redis)
├── feature_extractor.py    # URL → 17개 피처 변환
├── feature_module.py       # 피처 추출 세부 로직
├── mail_utils.py           # SMTP 이메일 인증 발송
│
├── services/
│   ├── model_service.py    # ML 예측 파이프라인
│   ├── qr_service.py       # QR 서명 검증 + 예측
│   ├── user_service.py     # 회원가입·로그인·이메일 인증
│   ├── scan_service.py     # 스캔 이력 CRUD
│   └── stats_service.py    # 통계 집계
│
├── *_api.py                # Blueprint 라우터 (HTTP 계층만 담당)
│
├── utils/
│   ├── blacklist.py        # 블랙리스트 DB 조회
│   └── whitelist.py        # 화이트리스트 판정
│
├── models/                 # ML 모델 파일 (볼륨 마운트)
│   ├── ens_1021_xgb.pkl
│   ├── ens_1021_lgb.pkl
│   ├── ens_1021_cat.pkl
│   ├── ens_1021_config.json
│   └── 1021_feature_params.pkl
│
├── static/
│   └── uploads/
│       ├── cards/          # 카드뉴스 이미지 (이미지에 포함)
│       └── user/           # 사용자 업로드 (볼륨 관리)
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── init.sql                # DB 초기 스키마
```

---

## 실행 방법

### Docker (권장)

```bash
# 1. 환경변수 파일 생성
cp .env.example .env
# .env 열어서 DB_PASSWORD, SMTP_PASS 등 실제 값 입력

# 2. 실행
docker compose up --build
```

`http://localhost:5000/healthz` 에서 `{"status": "ok"}` 확인

### 로컬 가상환경 (개발용)

```bash
# Python 3.11 가상환경 생성
%LOCALAPPDATA%\Programs\Python\Python311\python.exe -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

pip install -r requirements.txt

set MODEL_DIR=.\models      # Windows
# export MODEL_DIR=./models # macOS/Linux

python app.py
```

### 자주 쓰는 Docker 명령어

```bash
docker compose up --build -d   # 백그라운드 실행
docker compose logs -f app     # 앱 로그 확인
docker compose restart app     # 앱만 재시작
docker compose down            # 전체 중지
```

---

## 환경변수

`.env.example` 파일을 복사해서 `.env`로 만든 뒤 값을 채웁니다.

| 변수 | 설명 | 기본값 |
|---|---|---|
| `SECRET_KEY` | Flask 보안 키 | — |
| `DB_HOST` | MySQL 호스트 | `db` (Docker) |
| `DB_PASSWORD` | MySQL 비밀번호 | — |
| `DB_NAME` | DB 이름 | `naqjima` |
| `REDIS_URL` | Redis 연결 URL | `redis://redis:6379/0` |
| `MODEL_DIR` | pkl 파일 디렉토리 경로 | 앱 루트 |
| `SERVICE_BASE_URL` | 이메일 인증 링크 기준 URL | — |
| `SMTP_HOST` | SMTP 서버 | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP 포트 | `587` |
| `SMTP_USER` | 발신 이메일 계정 | — |
| `SMTP_PASS` | 이메일 앱 비밀번호 | — |
| `RATE_LIMIT_GLOBAL` | 전역 요청 제한 | `100 per minute` |
| `ALLOW_ORIGINS` | CORS 허용 출처 (쉼표 구분) | — |

---

## 주요 API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/healthz` | 헬스체크 |
| POST | `/users` | 회원가입 |
| POST | `/users/login` | 로그인 |
| GET | `/verify` | 이메일 인증 |
| POST | `/scans` | 스캔 기록 생성 |
| GET | `/scans` | 스캔 이력 조회 |
| POST | `/model-results` | URL 악성 여부 예측 |
| POST | `/qr_secure-scan` | QR 서명 검증 + 예측 |
| POST | `/upload` | 이미지 업로드 |
| GET | `/stats` | 통계 조회 |

---

## 볼륨 구성

Docker Compose에서 관리하는 볼륨입니다.

| 볼륨 | 컨테이너 경로 | 설명 |
|---|---|---|
| `./models` | `/models` | pkl 모델 파일 (읽기 전용 마운트) |
| `uploads_data` | `/app/static/uploads/user` | 사용자 업로드 이미지 |
| `db_data` | `/var/lib/mysql` | MySQL 데이터 |
| `redis_data` | `/data` | Redis 데이터 |
| `./logs` | `/app/logs` | 앱 로그 |

모델 파일을 이미지에 굽지 않고 볼륨으로 마운트하는 이유는 pkl 파일 크기가 수십 MB에 달해 이미지가 무거워지고, 모델 교체 시 이미지를 다시 빌드하지 않아도 되기 때문입니다.
