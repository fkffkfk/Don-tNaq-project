import joblib, json
import pandas as pd
import numpy as np
from flask import jsonify
from db import get_db_connection

from feature_extractor import FeatureExtractor
from feature_module import DaysBased, CountBased

from urllib.parse import urlparse, urlunparse
from utils.whitelist import is_project_whitelisted_url, is_whitelisted_url
from utils.blacklist import is_blacklisted_url
import logging, sys

logger = logging.getLogger("model_service")
if not logger.handlers:
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(sh)
logger.setLevel(logging.DEBUG)


CFG_PATH = "ens_1021_config.json"
with open(CFG_PATH, "r", encoding="utf-8") as f:
    CFG = json.load(f)

W = tuple(CFG["weights"])
THR_DEFAULT = float(CFG["thresholds"]["default"])
THR_RISK = float(CFG["thresholds"]["risk"])
RISK_FLAGS = CFG["risk_flags"]
RISK_MIN_HITS = int(CFG["risk_min_hits"])
REQUIRED_FEATURES = CFG["required_features"]
MODEL_VERSION = CFG.get("model_version", "ens_1021_v1_fixed")
EXPLANATION = "RF+XGB+LGB+CAT weighted soft voting"

RF = joblib.load("ens_1021_rf.pkl")
XGB = joblib.load("ens_1021_xgb.pkl")
LGB = joblib.load("ens_1021_lgb.pkl")
CAT = joblib.load("ens_1021_cat.pkl")
MODELS = (RF, XGB, LGB, CAT)

PARAMS = joblib.load("1021_feature_params.pkl")
EXTRACTOR = FeatureExtractor(
    url_avg=PARAMS['url_avg'],
    url_std=PARAMS['url_std'],
    schar_avg=PARAMS['schar_avg'],
    schar_std=PARAMS['schar_std'],
    letter_avg=PARAMS['letter_avg'],
    letter_std=PARAMS['letter_std'],
    keywords=PARAMS['keywords']
)



def _normalize_url(u: str) -> str:
    p = urlparse(u or "")
    scheme = (p.scheme or "").lower()
    netloc = (p.netloc or "").lower()
    path = (p.path or "").rstrip("/")
    if path == "/":
        path = ""
    return urlunparse((scheme, netloc, path, "", p.query or "", ""))

def _ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    drop_cols = [c for c in ['days_since_creation', 'days_since_update', 'days_until_expiration'] if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    return df.reindex(columns=REQUIRED_FEATURES, fill_value=0)


def _risk_mask(df: pd.DataFrame) -> np.ndarray:
    for k in RISK_FLAGS:
        if k not in df.columns:
            df[k] = 0
    return (df[RISK_FLAGS].fillna(0).astype(int).sum(axis=1) >= RISK_MIN_HITS).values


def _ensemble_proba(X: pd.DataFrame) -> np.ndarray:
    wrf, wxgb, wlgb, wcat = W
    p_rf = RF.predict_proba(X)[:, 1]
    p_xgb = XGB.predict_proba(X)[:, 1]
    p_lgb = LGB.predict_proba(X)[:, 1]
    p_cat = CAT.predict_proba(X)[:, 1]
    return (wrf*p_rf + wxgb*p_xgb + wlgb*p_lgb + wcat*p_cat) / (wrf+wxgb+wlgb+wcat)


def _explain_from_features(feat_row) -> str:
    def get(name, default=None):
        try: return feat_row[name] if name in feat_row else default
        except: return default
    def as_int(name, default=None):
        v = get(name, default)
        try: return int(v) if v is not None else default
        except: return default
    def as_float(name, default=None):
        v = get(name, default)
        try: return float(v) if v is not None else default
        except: return default

    dns_mal   = as_int("DNS_mal")
    ttl       = as_float("ttl")
    ns_match  = as_int("ns_match")
    dns_ok    = as_int("dns_query_success")

    if dns_mal == 1:
        if dns_ok == 0: return "사이트 주소를 찾지 못했습니다. (DNS 조회 실패)"
        if ttl == -1:  return "주소 확인 과정에서 통신 오류가 발생했습니다."
        if ttl == 86400 and ns_match == 0: return "사이트 주소 정보가 서버마다 달라 일관성이 부족합니다."
        if ns_match == 0: return "주소를 관리하는 서버 정보가 서로 달라 신뢰하기 어렵습니다."
        return "DNS 설정에서 일반적이지 않은 신호가 발견되었습니다."

    if as_int("is_expired") == 1:            return "보안 인증서가 만료되어 안전한 연결을 만들 수 없습니다."
    if as_int("is_self_signed") == 1:        return "공식 기관이 확인하지 않은 보안 인증서(자체 서명)입니다."
    if as_int("is_untrusted_ca") == 1:       return "신뢰할 수 있는 인증기관에서 발급되지 않은 보안 인증서입니다."
    if as_int("domain_cn_mismatch") == 1:    return "보안 인증서의 사이트 이름이 주소창의 사이트와 일치하지 않습니다."
    if as_int("is_weak_protocol") == 1:      return "오래되었거나 약한 방식의 보안 연결을 사용 중일 수 있습니다."
    if as_int("is_weak_key_algo") == 1:      return "암호 키 길이가 충분하지 않아 보호 수준이 낮습니다."
    if as_int("is_short_lived_cert") == 1:   return "보안 인증서 기간이 비정상적으로 짧아 임시 또는 의심 사이트일 수 있습니다."
    if as_int("san_count_high") == 1:        return "한 인증서에 사이트 이름이 묶여 있어 관리가 부정확할 수 있습니다."


    if as_int("check_keyword") == 1:         return "주소에 의심 단어가 포함되어 있습니다."
    if as_int("check_https") == 1:           return "HTTPS 보안 연결이 아닙니다(주소가 http로 시작). 비밀번호 또는 카드번호 입력은 금지하세요."
    
    url_len = as_float("url_length")
    try:
        if url_len is not None:
            url_avg = float(PARAMS["url_avg"])
            url_std = float(PARAMS["url_std"])
            low, high = url_avg - url_std, url_avg + url_std
            if CountBased.check_count_level(url_len, url_avg, url_std) == 1:
                return "URL 주소가 지나치게 길거나 짧아 실제 목적지를 숨길 수 있습니다."
    except Exception:
        pass


    special_cnt = as_float("specialchar_count")
    try:
        if special_cnt is not None:
            sch_avg = float(PARAMS["schar_avg"])
            sch_std = float(PARAMS["schar_std"])
            low, high = sch_avg - sch_std, sch_avg + sch_std
            if CountBased.check_count_level(special_cnt, sch_avg, sch_std) == 1:
                return "URL에 특수문자가 비정상적으로 포함되어 있습니다."
    except Exception:
        pass
    
    
    cnt_letters = as_float("countletter")
    try:
        if cnt_letters is not None:
            letter_avg = float(PARAMS["letter_avg"])
            letter_std = float(PARAMS["letter_std"])
            low, high = letter_avg - letter_std, letter_avg + letter_std
            if CountBased.check_count_level(cnt_letters, letter_avg, letter_std) == 1:
                return "URL에 무작위 문자 조합이 많아 자동 생성 또는 위장 주소일 수 있습니다."
    except Exception:
        pass

    return "여러 신호를 종합한 결과, 악성으로 분류되었습니다."


def _insert_result(conn, scan_id, score, result, reason):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO model_result (scan_id, model_version, score, result, explanation)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            model_version=VALUES(model_version),
            score=VALUES(score),
            result=VALUES(result),
            explanation=VALUES(explanation)
    """, (scan_id, MODEL_VERSION, score, result, reason))
    cursor.execute("UPDATE scan_history SET status=%s WHERE id=%s", ('done', scan_id))
    conn.commit()
    cursor.close()


# POST /model-results → 모델 예측 및 분석 결과 저장
def create_model_result(payload: dict):
    scan_id = payload.get("scan_id")
    if not scan_id:
        return jsonify({"error": "scan_id는 필수입니다."}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT url FROM scan_history WHERE id = %s", (scan_id,))
        row = cursor.fetchone()
        if not row or not row.get('url'):
            return jsonify({"error": "해당 scan_id에 대한 url을 찾을 수 없습니다."}), 404
        
        url = _normalize_url(row["url"])


        if is_blacklisted_url(url):
            logger.info("[BL HIT] scan_id=%s url=%s", scan_id, url)

            reason = "블랙리스트에 등록된 URL"
            _insert_result(conn, scan_id, 1.0, 1, reason)

            cursor.close(); conn.commit(); conn.close()

            return jsonify({
                "message": "블랙리스트 URL",
                "scan_id": scan_id,
                "prediction": 1,
                "reason": reason
            }), 422


        if is_project_whitelisted_url(url):
            logger.info("[PWL WE] scan_id=%s url=%s", scan_id, url)
            reason = "낚낚시꾼 깃허브 링크 및 자가진단테스트"
            _insert_result(conn, scan_id, 0.0, 0, reason)

            cursor.close(); conn.commit(); conn.close()

            return jsonify({
                "message": "우리 프로젝트 관련",
                "prediction": 0,
                "reason": reason
            }), 200



        if is_whitelisted_url(url):
            logger.info("[WL HIT] scan_id=%s url=%s", scan_id, url)
            reason = "화이트리스트"
            _insert_result(conn, scan_id, 0.0, 0, reason)

            cursor.close(); conn.commit(); conn.close()

            return jsonify({
                "message": "화이트리스트 URL",
                "prediction": 0,
                "reason": reason
            }), 200



        domain = DaysBased.extract_domain(url)
        if not domain:
            cursor.close()
            conn.close()
            return jsonify({"error": "도메인 추출 실패"}), 400


        base_df = pd.DataFrame([{"URL": url, "domain": domain}])
        feature_df = EXTRACTOR.transform(base_df)
        feature_df = _ensure_required_columns(feature_df)


        risk_mask = _risk_mask(feature_df)
        proba = float(_ensemble_proba(feature_df)[0])
        thr = THR_RISK if risk_mask[0] else THR_DEFAULT
        pred_label = int(proba >= thr)
        reason_text = _explain_from_features(feature_df.iloc[0]) if pred_label == 1 else None
 

        if pred_label == 1:
            logger.info("[MODEL MALICIOUS] scan_id=%s prob=%.4f reason=%s",
                scan_id, proba, reason_text)
        else:
            logger.info("[MODEL BENIGN] scan_id=%s prob=%.4f",
                scan_id, proba)

        cursor2 = conn.cursor()
        cursor2.execute(
            """
            INSERT INTO model_result (scan_id, model_version, score, result, explanation)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                model_version = VALUES(model_version),
                score = VALUES(score),
                result = VALUES(result),
                explanation = VALUES(explanation)
            """,
            (scan_id, MODEL_VERSION, proba, pred_label, reason_text)
        )

        cursor2.execute("UPDATE scan_history SET status=%s WHERE id=%s", ('done', scan_id))

        conn.commit()
        cursor2.close()
        cursor.close()
        conn.close()

        resp = {
            "message": "모델 예측 및 저장 완료",
            "scan_id": scan_id,
            "probability": round(proba, 4),
            "threshold": thr,
            "prediction": "malicious" if pred_label == 1 else "benign",
        }
        if pred_label == 1 and reason_text:
            resp["reason"] = reason_text
        return jsonify(resp), 200
    
    except Exception as e:
        logger.error("[MODEL ERROR] 예측 중 오류 발생", exc_info=True)
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return jsonify({"error": f"예측 실패: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()



# GET /model-results?user_id=3 → 사용자별 모델 결과 조회
def get_model_results(scan_id):
    if not scan_id:
        return jsonify({"error": "scan_id 쿼리 파라미터가 필요합니다."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT model_version, score, result, explanation, created_at
        FROM model_result
        WHERE scan_id = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, (scan_id,))
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(results), 200

