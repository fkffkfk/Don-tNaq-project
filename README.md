# 🎣 낚지마! — AI 기반 악성 QR코드 탐지 모바일 앱

> **"QR코드, 함부로 찍지 마세요."**  
> 큐싱(Quishing) 피해를 예방하는 머신러닝 기반 Android 보안 애플리케이션

<br>

## 📌 프로젝트 개요

QR코드와 피싱의 합성어인 **큐싱(Quishing)** — 정체불명의 QR코드를 통해 악성 URL로 유도하는 해킹 수법이 일상 속에서 급증하고 있습니다.  
낚지마!는 QR코드를 스캔하는 순간, **ML 모델이 URL의 특징을 분석해 악성 여부를 즉시 판별**하고, **ECDSA 디지털 서명 기반 인증 QR코드 생성** 기능으로 위조된 QR코드를 원천 차단합니다.

| 항목 | 내용 |
|---|---|
| **개발 기간** | 2024.09 ~ 2024.12 |
| **팀 구성** | 3인 팀 |
| **플랫폼** | Android |

<br>

## 🏗️ 시스템 아키텍처

```
[ Android App (Kotlin) ]
        │
        │  REST API (Retrofit)
        ▼
[ Flask Backend Server (Python) ]
   ├─ Rate Limiting (Flask-Limiter + Redis)
   ├─ Blacklist / Whitelist 필터링
   ├─ 보안 헤더 (X-Frame-Options, X-Content-Type-Options 등)
   ├─ RotatingFileHandler 로깅 (server / scan / user / qr 분리)
   │
   ├─────────────────────────┐
   ▼                         ▼
[ ML 탐지 모델 ]         [ MySQL DB ]
  RF + XGBoost + LightGBM    users
  + CatBoost                 scan_history
  VotingClassifier           model_result
  (앙상블, 정확도 91%)        secure_qr_log
                             blacklist_urls

[ ECDSA 디지털 서명 모듈 ]
  인증 QR 생성 (앱) / 서명 검증 (서버)
```

<br>

## ✨ 핵심 기능

### 1. 악성 URL 탐지 (QR코드 스캔)
- QR코드 스캔 즉시 URL을 서버로 전송, ML 모델이 악성/정상 판별
- 결과 화면에서 위험도 즉시 표시
- 스캔 히스토리 및 통계 차트 제공

### 2. 인증 QR코드 생성 (ECDSA 디지털 서명)
- **ECDSA(타원 곡선 디지털 서명 알고리즘)** 기반으로 QR코드에 서명 삽입
- 스캔 시 서명 검증 → 위조·변조된 QR코드 즉시 탐지
- 만료 시간 설정 기능으로 재사용 공격 방지

### 3. 보안 콘텐츠 및 커뮤니티
- 큐싱 피해 사례, 보안 가이드 게시판
- 즐겨찾기, 게시글 작성/편집 기능

<br>

## 🤖 ML 모델 상세

### 데이터셋
- 총 **16만 개** URL (악성 : 정상 = 1 : 1)
- 정상 URL: Tranco 상위 도메인 크롤링 수집
- 악성 URL: 공개 피싱 데이터셋 활용

### 추출 특징 (17개)

| 카테고리 | 특징 |
|---|---|
| **존재 기반** | HTTPS 여부, 피싱 키워드 포함 여부 |
| **길이 기반** | URL 길이 이상치 여부 |
| **개수 기반** | 특수문자 수, 숫자 수, 문자 수 이상치 여부 |
| **DNS 기반** | SOA TTL, NS 레코드 일치 여부, DNS 조회 성공 여부, DNS 악성 판정 |
| **WHOIS 기반** | 도메인 생성일, 최종 수정일, 만료일 기반 일수 분류 |
| **인증서 기반** | CA 신뢰도, SSL/TLS 프로토콜 버전, 키 알고리즘, 인증서 유효기간, 자체 서명 여부, CN 일치 여부 |

### 모델 구성 및 성능

```
RandomForest + XGBoost + LightGBM + CatBoost
         ↓  VotingClassifier (soft voting)
         정확도: 약 91%
```

- Mutual Information으로 특징 중요도 분석
- Feature Importance 히트맵으로 모델별 기여도 시각화

<br>

## 🛠️ 기술 스택

| 분류 | 기술 |
|---|---|
| **Frontend** | Android (Kotlin), Retrofit2 |
| **Backend** | Python 3.11, Flask 3.0, Blueprint 구조, REST API |
| **Database** | MySQL (mysql-connector-python) |
| **Cache / Rate Limit** | Redis, Flask-Limiter (fixed-window 전략) |
| **ML/AI** | RandomForest, XGBoost, LightGBM, CatBoost, VotingClassifier, TensorFlow (CNN) |
| **Security** | ECDSA (cryptography 라이브러리), URL Blacklist/Whitelist, 보안 HTTP 헤더 |
| **Data** | pandas, scikit-learn, tldextract, dnspython, python-whois |

<br>

## 📁 레포지토리 구조

```
don-t_nakk/
│
├── README.md
│
├── model/                        # ML 모델 학습 코드
│   ├── feature_module.py         # 특징 추출 클래스 (ExistenceBased, LengthBased, CountBased, DaysBased, DNS)
│   ├── feature_extractor.py      # FeatureExtractor 통합 클래스
│   ├── total_train_basic.py      # 모델 학습 메인 스크립트 (RF + XGBoost + 앙상블)
│   ├── deep.py                   # CNN (char-level) 딥러닝 모델
│   └── feature_feature_MI.py     # Mutual Information 분석
│
├── ExtractSafeURL.py             # 정상 URL 데이터 수집 (Tranco 크롤링)
├── fix_feature.py                # 특징 임계값 튜닝 실험
├── fix_module.py                 # 특징 모듈 수정 버전
├── module_application.py        # 모델 적용 파이프라인
├── normal.py                    # 정상 URL 추가 수집 스크립트
│
└── front/                        # Android 앱 (Kotlin)
    └── app/src/main/java/com/example/qrcode/
        ├── Scan/                 # QR 스캔 & 결과 화면
        ├── Board/                # 게시판
        ├── History/              # 스캔 히스토리 & 통계
        ├── Settings/             # 설정, 인증 QR 관리
        └── auth/                 # 로그인/회원가입

※ 백엔드 서버 코드는 [backend 브랜치](../../tree/backend)에 있습니다.

**Backend 브랜치 구조 (`back/`)**

```
back/
├── app.py                    # Flask 앱 진입점, Blueprint 등록, 보안 헤더 설정
├── config.py / db.py         # 환경변수 기반 설정, DB 연결
├── limiter_config.py         # Rate Limiting (Redis + fixed-window)
├── cache_config.py           # 캐시 설정
├── error_handler.py          # 전역 예외 처리
├── mail_utils.py             # 이메일 인증 발송
├── feature_module.py         # URL 특징 추출 클래스
├── feature_extractor.py      # FeatureExtractor 통합
│
├── [*_api.py]                # API Blueprint
│   ├── user_api.py           # 회원가입, 로그인, 이메일 인증, 회원탈퇴
│   ├── scan_api.py           # QR 스캔 기록 생성/조회 (Rate limit: 10/min)
│   ├── model_api.py          # ML 모델 예측 API
│   ├── qr_api.py             # QR코드 관련 API
│   ├── qr_secure_api.py      # ECDSA 서명 검증 + 인증 QR 처리
│   ├── stats_api.py          # 스캔 통계 API
│   ├── posts_api.py          # 게시판 API
│   └── upload_api.py         # 이미지 업로드 API
│
├── services/                 # 비즈니스 로직 레이어
│   ├── user_service.py
│   ├── scan_service.py
│   ├── model_service.py
│   ├── qr_service.py
│   └── stats_service.py
│
└── utils/
    ├── blacklist.py          # SHA-256 해시 기반 URL 블랙리스트 조회
    ├── whitelist.py          # 신뢰 도메인 화이트리스트 + Open Redirect 방어
    ├── cache.py              # 캐시 유틸
    ├── db_helpers.py
    └── response.py           # 공통 응답 포맷
```
```

<br>

## 🔐 보안 구현 포인트

백엔드/보안 직군 지원을 위해 특히 강조할 구현 내용입니다.

| 항목 | 구현 내용 |
|---|---|
| **ECDSA 디지털 서명** | 앱에서 개인키로 서명 → 서버에서 DB 저장 공개키로 검증, PEM/DER 포맷 유연 처리 |
| **Rate Limiting** | Flask-Limiter + Redis, fixed-window 전략, 스캔 API 10회/분 제한 |
| **URL 블랙리스트** | PhishTank 기반, SHA-256 해시로 정규화된 URL 조회 (평문 저장 없음) |
| **URL 화이트리스트** | 신뢰 도메인 목록 + Open Redirect 파라미터(`redirect`, `url`, `next` 등) 검사 |
| **보안 HTTP 헤더** | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` |
| **이메일 인증** | 회원가입 시 토큰 기반 이메일 인증, 재전송 기능 |
| **로그 분리** | server / scan_activity / user_activity / qr_activity 로그 파일 분리, RotatingFileHandler |
| **환경변수 기반 설정** | `.env`로 DB, SMTP, Redis, CORS 설정 분리 (하드코딩 없음) |

<br>



### 백엔드 서버

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정 (.env 파일 생성)
SERVICE_BASE_URL=http://localhost:5000
ALLOW_ORIGINS=http://localhost
RATE_LIMIT_GLOBAL=100 per minute
REDIS_URL=redis://127.0.0.1:6379/0
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
MAIL_FROM=your@email.com

# 서버 실행
python app.py
```

### ML 모델 학습

```bash
# 의존성 설치
pip install pandas scikit-learn xgboost lightgbm catboost dnspython tldextract python-whois joblib

# 특징 추출 및 모델 학습
python model/total_train_basic.py
```

> 학습에 사용된 전처리 기준값(feature_params)은 `0602_feature_params.pkl`에 저장됩니다.  
> 학습된 모델 파일(.pkl)은 용량 문제로 레포에 포함되지 않습니다. → [Google Drive 링크](#) *(추후 추가 예정)*

### Android 앱 빌드

```
Android Studio에서 front/ 폴더를 Open하여 빌드
minSdk: 26 / targetSdk: 34
```

<br>

## 📄 라이선스

본 프로젝트는 학술 목적의 졸업프로젝트입니다.
