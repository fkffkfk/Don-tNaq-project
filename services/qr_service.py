from flask import jsonify
from db import get_db_connection
import base64
import joblib
import pandas as pd
import numpy as np
import traceback
import re
import sys
import logging
import json
from urllib.parse import urlparse, urlunparse
from datetime import datetime, timezone, timedelta
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from feature_extractor import FeatureExtractor
from feature_module import ExistenceBased, LengthBased, CountBased, DaysBased, DNS, SSL
from utils.blacklist import is_blacklisted_url
from utils.whitelist import is_whitelisted_url, is_project_whitelisted_url

from utils.cache import get as cache_get, set as cache_set

QR_MAX_AGE_MINUTES = int(os.getenv("QR_MAX_AGE_MINUTES", "1440"))


logger = logging.getLogger("qr_secure")
if not logger.handlers:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    file_handler = logging.FileHandler("qr_activity.log")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

def _log(*args):
    logger.debug(" ".join(str(a) for a in args))


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


def _log_malicious_reason(*, source: str, user_id: int, scan_id: int | None, url: str, reason: str, probability: float | None):
    try:
        payload = {
            "event" : "malicious_detected",
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "user_id": user_id,
            "scan_id": scan_id,
            "url": url,
            "reason": reason,
            "probability": probability,
        }
        logger.info(json.dumps(payload, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"[LOG_FAIL] malicious_reason: {e} ({reason})")


# URL 정규화
def _normalize_url(u: str) -> str:
    p = urlparse(u or "")
    scheme = (p.scheme or "").lower()
    netloc = (p.netloc or "").lower()
    path = (p.path or "").rstrip("/")
    if path == "/":
        path = ""
    return urlunparse((scheme, netloc, path, "", p.query or "", ""))

# 공개키 불러오기
def _robust_load_public_key(public_key_pem_str: str):
    if public_key_pem_str is None:
        raise ValueError("empty public_key")

    s = public_key_pem_str.strip().strip('"').strip("'")
    s_fixed = s.replace("\\n", "\n")


    if "BEGIN PUBLIC KEY" in s_fixed or "BEGIN EC PUBLIC KEY" in s_fixed:
        try:
            return serialization.load_pem_public_key(s_fixed.encode())
        except Exception as e:
            _log("WARN: PEM load failed once:", e)
            s_compact = re.sub(r"[ \t\r]+", "", s_fixed)
            s_compact = (s_compact
                         .replace("-----BEGINPUBLICKEY-----", "-----BEGIN PUBLIC KEY-----")
                         .replace("-----ENDPUBLICKEY-----", "-----END PUBLIC KEY-----")
                         .replace("-----BEGINECPUBLICKEY-----", "-----BEGIN EC PUBLIC KEY-----")
                         .replace("-----ENDECPUBLICKEY-----", "-----END EC PUBLIC KEY-----"))
            return serialization.load_pem_public_key(s_compact.encode())

    try:
        s_compact = re.sub(r"\s+", "", s_fixed)
        der = base64.b64decode(s_compact, validate=True)
        return serialization.load_der_public_key(der)
    except Exception as e:
        _log("WARN: DER load failed:", e)


    try:
        s_compact = re.sub(r"\s+", "", s_fixed)
        _ = base64.b64decode(s_compact, validate=True)
        pem_wrapped = "-----BEGIN PUBLIC KEY-----\n"
        pem_wrapped += "\n".join([s_compact[i:i+64] for i in range(0, len(s_compact), 64)])
        pem_wrapped += "\n-----END PUBLIC KEY-----\n"
        return serialization.load_pem_public_key(pem_wrapped.encode())
    except Exception as e:
        _log("WARN: wrap-PEM load failed:", e)

    raise ValueError("Unsupported public_key format")


# 악성 QR코드 일 경우, 특징 뽑아서 안내
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


# /qr_secure-scan
def qr_secure_scan(payload: dict):
    data = payload or {}
    raw_url = data.get("url") or data.get("original_url")
    signature_b64 = data.get("signature") or data.get("signature_b64")
    scanner_id = data.get("user_id")
    scan_id = data.get("scan_id")

    _log("\n========== /qr_secure-scan DEBUG ==========")
    _log("Raw payload:", data)
    _log("==========================================")

    missing = []
    if not raw_url:       missing.append("url/original_url")
    if not signature_b64: missing.append("signature")
    if scanner_id is None:   missing.append("user_id")
    if missing:
        _log("Missing fields:", missing)
        return jsonify({"error": f"missing fields: {missing}"}), 400

    try:
        scanner_id = int(scanner_id)
        if scan_id is not None:
            scan_id = int(scan_id)
    except Exception:
        return jsonify({"error": "user_id/scan_id must be int"}), 400

    url = _normalize_url(raw_url)
    _log("[PARSE] norm_url:", url, "scanner_id:", scanner_id, "scan_id:", scan_id)


    conn = get_db_connection()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT
                  id,
                  user_id         AS qr_user_id,
                  original_url    AS qr_url,
                  expires_at,
                  CASE WHEN expires_at IS NULL THEN 0
                       WHEN NOW() > expires_at THEN 1
                       ELSE 0 END AS expired_flag
                FROM secure_qr_log
                WHERE signature = %s
                ORDER BY id DESC
                LIMIT 1
            """, (signature_b64,))
            qr_row = cursor.fetchone()
        
        if (not qr_row) or qr_row["expired_flag"] == 1:
            _log("[EXPIRE/NOT_FOUND] expired or not found by signature")
            try:
                if scan_id is None:
                    with conn.cursor() as c:
                        c.execute("""
                            INSERT INTO scan_history (user_id, url, status, is_user_visible)
                            VALUES (%s, %s, %s, %s)
                        """, (scanner_id, url, 'expired', 0))
                        conn.commit()
                        scan_id = c.lastrowid
                        _log("[STEP] Hidden expired scan_history created:", scan_id)
                else:
                    with conn.cursor() as c:
                        c.execute("""
                            UPDATE scan_history
                               SET status = %s,
                                   is_user_visible = 0
                             WHERE id = %s
                        """, ('expired', scan_id))
                        conn.commit()
                        _log("[STEP] scan_history marked hidden+expired:", scan_id)
            except Exception as e:
                _log("WARN: failed to write hidden scan_history for expired:", e)

            return jsonify({
                "success": False,
                "message": "QR코드 유효기간이 만료되었거나 등록되지 않은 인증 QR입니다.",
                "scan_id": scan_id
            }), 410
        
        creator_id = int(qr_row["qr_user_id"])
        db_qr_url     = _normalize_url(qr_row["qr_url"])
        if db_qr_url != url:
            _log("QR payload mismatch:",
                 {"db_url": db_qr_url, "req_url": url})
            return jsonify({"error": "QR payload mismatch"}), 409


        # 공개키 조회하고
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT public_key FROM users WHERE id=%s", (creator_id,))
        user_row = cursor.fetchone(); cursor.close()
        if not user_row or not user_row["public_key"]:
            return jsonify({"error": "공개키를 찾을 수 없습니다."}), 404

        # 2) 공개키 로딩
        try:
            public_key = _robust_load_public_key(user_row["public_key"])
            _log("[STEP] Public key loaded OK.")
        except Exception as e:
            _log("Public key load error:", e)
            return jsonify({"error": "공개키 로딩 실패", "details": str(e)}), 400
        

        # 3) 서명 검증 (앱과 동일하게 url + user_id)
        try:
            msg = (url + str(creator_id)).encode("utf-8")
            signature = base64.b64decode(signature_b64, validate=True)
            public_key.verify(signature, msg, ec.ECDSA(hashes.SHA256()))
            _log("[STEP] Signature verified OK.")
        except Exception as e:
            return jsonify({"error": "서명 검증 실패"}), 401


        # 4) scan_id 확보/검증
        if scan_id is None:
            # 새로 만들 때는 숨김으로 생성
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scan_history (user_id, url, status, is_user_visible)
                VALUES (%s, %s, %s, %s)
            """, (scanner_id, url, 'pending', 0))
            conn.commit()
            scan_id = cursor.lastrowid
            cursor.close()
            _log("[STEP] Hidden scan_history created:", scan_id)
        else:
            _log("[STEP] Using provided scan_id:", scan_id)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT user_id, url FROM scan_history WHERE id=%s", (scan_id,))
            sh = cursor.fetchone()
            cursor.close()
            if not sh:
                return jsonify({"error": "존재하지 않는 scan_id"}), 400
            if int(sh["user_id"]) != scanner_id or _normalize_url(sh["url"]) != url:
                _log("scan_id mismatch:", sh, "vs", {"user_id": scanner_id, "url": url})
                return jsonify({"error": "scan_id가 요청의 user_id/url과 일치하지 않습니다."}), 400

            # 기존 레코드라도 숨김 처리
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE scan_history
                SET is_user_visible = 0
                WHERE id = %s AND is_user_visible <> 0
            """, (scan_id,))
            conn.commit()
            cursor.close()
            _log("[STEP] scan_history hidden (force is_user_visible=0):", scan_id)

        if is_blacklisted_url(url):
            _log_malicious_reason(
                source="blacklist",
                user_id=scanner_id,
                scan_id=scan_id,
                url=url,
                reason="블랙리스트에 등록된 URL입니다.",
                probability=None,
            )
            try:
                with conn.cursor() as c:
                    c.execute("UPDATE scan_history SET status=%s WHERE id=%s", ('blocked', scan_id))
                    conn.commit()
            except Exception as e:
                _log("WARN: failed to mark scan_history bloacked:", e)
            
            return jsonify({
                "scan_id": scan_id,
                "result": "malicious",
                "reason": "블랙리스트에 등록된 URL입니다."
            }), 422
        
        def _get_creator_name(conn_, cid: int) -> str | None:
            try:
                with conn_.cursor(dictionary=True) as c:
                    c.execute("""
                        SELECT COALESCE(userName, email) AS creator_name
                          FROM users
                         WHERE id = %s
                         LIMIT 1
                    """, (cid,))
                    r = c.fetchone()
                    return r["creator_name"] if r else None
            except Exception as e:
                _log("WARN: creator info load failed:", e)
                return None

        if is_whitelisted_url(url):
            creator_name = _get_creator_name(conn, creator_id)
            _log("[WHITELIST] Trusted domain detected: ", url)
            return jsonify({
                "message": "서명 검증 및 예측 완료",
                "scan_id": scan_id,
                "prediction": 0,
                "result": "benign",
                "probability": 0.0,
                "reason": "신뢰된 도메인입니다.",
                "creator": creator_name
            }), 200

    
        # 5) 모델 결과 조회/생성
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT result, score, explanation FROM model_result WHERE scan_id=%s",
            (scan_id,))
        rr = cursor.fetchone(); cursor.close()

        proba = 0.0
        result = 0
        reason_text = None

        if rr:
            proba = float(rr["score"] or 0.0)
            result = int(rr.get("result") or 0)
            reason_text = rr["explanation"] if result == 1 else None
            _log(f"[STEP] Existing result loaded. result={result}, proba={proba:.4f}")
        
            if result == 1:
                _log_malicious_reason(
                    source="db",
                    user_id=scanner_id,
                    scan_id=scan_id,
                    url=url,
                    reason=reason_text or "악성으로 분류",
                    probability=proba,
                )
        
        else:
            cached = cache_get(url)
            if cached:
                proba = float(cached["score"])
                thr_cached = cached.get("thr")
                if "result" in cached:
                    result = int(cached["result"])
                elif thr_cached is not None:
                    result = int(proba >= float(thr_cached))
                else:
                    result = int(proba >= 0.5)
                
                reason_text = cached.get("reason") if result == 1 else None
                _log("[CACHE HIT] use cached prediction")

                if result == 1:
                    _log_malicious_reason(
                        source="cache",
                        user_id=scanner_id,
                        scan_id=scan_id,
                        url=url,
                        reason=reason_text or "악성으로 분류",
                        probability=proba,
                    )

            else:
                _log("[STEP] No model_result. Running prediction...")
                input_df = pd.DataFrame([{"URL":url}])
                feat_df = EXTRACTOR.transform(input_df)
                feat_df = feat_df.reindex(columns=REQUIRED_FEATURES, fill_value=0)
                
                risk_mask = _risk_mask(feat_df)
                proba = float(_ensemble_proba(feat_df)[0])
                thr = THR_RISK if risk_mask[0] else THR_DEFAULT
                result = int(proba >= thr)
                reason_text = _explain_from_features(feat_df.iloc[0]) if result == 1 else None

                
                cache_pay = {"score": proba, "result": result, "thr": thr}
                if reason_text:
                    cache_pay["reason"] = reason_text
                cache_set(url, cache_pay)

                if result == 1:
                    _log_malicious_reason(
                        source="model",
                        user_id=scanner_id,
                        scan_id=scan_id,
                        url=url,
                        reason=reason_text or "악성으로 분류",
                        probability=proba,
                    )

            
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO model_result (scan_id, model_version, score, result, explanation)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  model_version=VALUES(model_version),
                  score=VALUES(score),
                  result=VALUES(result),
                  explanation=VALUES(explanation)
            """, (scan_id, MODEL_VERSION, proba, result, reason_text))
            cursor.execute("UPDATE scan_history SET status = 'done' WHERE id = %s", (scan_id,))
            conn.commit()
            cursor.close()
            _log(f"[STEP] Predict done. result={result}, score={proba:.4f}, reason={reason_text}")

        # 6) 악성 차단 → 여기서 종료 (로그 저장 안 함)
        if result == 1:
            payload = {
                "message": "악성 URL로 판단되어 인증 QR 생성이 차단되었습니다.",
                "prediction": result,
                "probability": round(proba, 4),
                "scan_id": scan_id,
                "reason": reason_text
            }
            _log("[DONE] 422:", payload)
            return jsonify(payload), 422

        # 7) 정상 → 인증 QR일 때만 creator 정보 포함
        creator_name = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT userName FROM users WHERE id=%s", (creator_id,))
            creator = cursor.fetchone()
            cursor.close()
            if creator:
                creator_name = creator["userName"]
        except Exception as e:
            _log("WARN: creator info load failed: ", e)
        
        resp = {
            "message": "서명 검증 및 예측 완료",
            "prediction": result,
            "probability": round(proba, 4),
            "scan_id": scan_id,
            "creator": creator_name
        }
        _log("[DONE] 200:", resp)
        return jsonify(resp), 200

    except Exception as e:
        _log("Unhandled error in /qr_secure-scan:", e)
        traceback.print_exc()
        try: conn.rollback()
        except: pass
        return jsonify({"error": "처리 실패", "details": str(e)}), 500
    finally:
        try: conn.close()
        except: pass



# /secure-qr (보조 API) + 경로 저장
def save_secure_qr_log(payload: dict):
    data = payload or {}
    user_id = data.get("user_id")
    original_url_raw = data.get("original_url") or data.get("url")
    signature = data.get("signature") or data.get("signature_b64")
    qr_image_path = data.get("qr_image_path", "")
    validity = data.get("validity")

    _log("\n========== /secure-qr DEBUG ==========")
    _log("Raw payload:", data)
    _log("======================================")

    if user_id is None or not original_url_raw or not signature or not qr_image_path or not validity:
        _log("Missing fields in /secure-qr")
        return jsonify({"error": "필수 항목 누락"}), 400

    try:
        user_id = int(user_id)
    except Exception:
        _log("user_id cast error in /secure-qr")
        return jsonify({"error": "user_id must be int"}), 400

    original_url = _normalize_url(original_url_raw)

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    if validity == "1day":
        expires_at = now + timedelta(days=1)
    elif validity == "7days":
        expires_at = now + timedelta(days=7)
    elif validity == "30days":
        expires_at = now + timedelta(days=30)
    elif validity == "90days":
        expires_at = now + timedelta(days=90)
    elif validity == "180days":
        expires_at = now + timedelta(days=180)
    else:
        _log("Invalid validity option: ", validity)
        return jsonify({"error": "유효기간 선택이 잘못되었습니다."}), 400

    conn = get_db_connection()
    try:
        conn.start_transaction()

        # 중복 방지용 조회
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id FROM secure_qr_log
             WHERE user_id = %s
               AND original_url = %s
               AND (expires_at IS NULL OR expires_at > NOW())
             LIMIT 1
             FOR UPDATE
        """, (user_id, original_url))
        exists_log = cursor.fetchone()
        cursor.close()

        if exists_log:
            _log("[STEP] secure_qr_log already exists (helper API).")
            conn.rollback()
            return jsonify({"message": "이미 로그가 존재합니다."}), 409

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO secure_qr_log (user_id, original_url, signature, qr_image_path, created_at, expires_at)
            VALUES (%s, %s, %s, %s, NOW(), %s)
        """, (user_id, original_url, signature, qr_image_path, expires_at))
        conn.commit()
        cursor.close()

        _log(f"[DONE] /secure-qr inserted. expires_at={expires_at.isoformat()}")
        return jsonify({
            "message": "인증 QR 생성 로그 저장 완료",
            "expires_at": expires_at.isoformat()
            }), 201
    

    except Exception as e:
        _log("Unhandled error in /secure-qr:", e)
        traceback.print_exc()
        try: conn.rollback()
        except: pass
        return jsonify({"error": f"저장 실패: {str(e)}"}), 500
    finally:
        try: conn.close()
        except: pass



def list_secure_qr_logs(user_id):
    if not user_id:
        return jsonify({"error": "user_id 필요"}), 400
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, original_url, signature, qr_image_path, created_at, expires_at
            FROM secure_qr_log
            WHERE user_id=%s
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return jsonify(rows), 200
    finally:
        conn.close()

