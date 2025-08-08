from flask import Blueprint, request, jsonify
from db import get_db_connection
import base64
import joblib
import pandas as pd
import traceback
import re
import sys
import logging

from urllib.parse import urlparse, urlunparse
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from feature_extractor import FeatureExtractor
from feature_module import ExistenceBased, LengthBased, CountBased, DaysBased, DNS, SSL

# Blueprint & Logging
qr_api = Blueprint('qr_api', __name__)

logger = logging.getLogger("qr_secure")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def log(*args):
    logger.debug(" ".join(str(a) for a in args))

# URL Normalizer (앱과 규칙 맞추기)
def normalize_url(u: str) -> str:
    p = urlparse(u)
    scheme = p.scheme.lower()
    netloc = p.netloc.lower()
    path = p.path.rstrip("/")
    if path == "/":
        path = ""
    return urlunparse((scheme, netloc, path, "", p.query, ""))

# Public Key Loader
def _robust_load_public_key(public_key_pem_str: str):
    if public_key_pem_str is None:
        raise ValueError("empty public_key")

    s = public_key_pem_str.strip().strip('"').strip("'")
    s_fixed = s.replace("\\n", "\n")


    if "BEGIN PUBLIC KEY" in s_fixed or "BEGIN EC PUBLIC KEY" in s_fixed:
        try:
            return serialization.load_pem_public_key(s_fixed.encode())
        except Exception as e:
            log("WARN: PEM load failed once:", e)
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
        log("WARN: DER load failed:", e)


    try:
        s_compact = re.sub(r"\s+", "", s_fixed)
        _ = base64.b64decode(s_compact, validate=True)
        pem_wrapped = "-----BEGIN PUBLIC KEY-----\n"
        pem_wrapped += "\n".join([s_compact[i:i+64] for i in range(0, len(s_compact), 64)])
        pem_wrapped += "\n-----END PUBLIC KEY-----\n"
        return serialization.load_pem_public_key(pem_wrapped.encode())
    except Exception as e:
        log("WARN: wrap-PEM load failed:", e)

    raise ValueError("Unsupported public_key format")

# 모델/파라미터
log("[BOOT] Loading model/params ...")
model = joblib.load("0624_rfxgbcat_model.pkl")
params = joblib.load("0602_feature_params.pkl")
log("[BOOT] Model/params loaded.")

extractor = FeatureExtractor(
    letter_avg=params['letter_avg'],
    letter_std=params['letter_std'],
    thresholds=params['thresholds'],
    keywords=params['keywords']
)

MODEL_VERSION = "0624_rfxgbcat_v1"
EXPLANATION = "RF+XGB+CAT weighted soft voting"

# /qr_secure-scan
@qr_api.route('/qr_secure-scan', methods=['POST'])
def qr_secure_scan():
    try:
        data = request.get_json(force=False, silent=False)
    except Exception as ex:
        log("❌ JSON parse error:", ex)
        return jsonify({"error": "invalid json", "details": str(ex)}), 400

    data = data or {}
    raw_url = data.get("url") or data.get("original_url")
    signature_b64 = data.get("signature") or data.get("signature_b64")
    user_id = data.get("user_id")
    scan_id = data.get("scan_id")

    log("\n========== /qr_secure-scan DEBUG ==========")
    log("Raw payload:", data)
    log("==========================================")

    missing = []
    if not raw_url:       missing.append("url/original_url")
    if not signature_b64: missing.append("signature")
    if user_id is None:   missing.append("user_id")
    if missing:
        log("❌ Missing fields:", missing)
        return jsonify({"error": f"missing fields: {missing}"}), 400

    try:
        user_id = int(user_id)
        if scan_id is not None:
            scan_id = int(scan_id)
    except Exception:
        return jsonify({"error": "user_id/scan_id must be int"}), 400

    url = normalize_url(raw_url)
    log("[PARSE] norm_url:", url, "user_id:", user_id, "scan_id:", scan_id)

    conn = get_db_connection()
    try:
        # 1) 공개키 조회
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT public_key FROM users WHERE id=%s", (user_id,))
        row = cursor.fetchone(); cursor.close()
        if not row or not row["public_key"]:
            return jsonify({"error": "공개키를 찾을 수 없습니다."}), 404

        # 2) 공개키 로딩
        try:
            public_key = _robust_load_public_key(row["public_key"])
            log("[STEP] Public key loaded OK.")
        except Exception as e:
            log("❌ Public key load error:", e)
            return jsonify({"error": "공개키 로딩 실패", "details": str(e)}), 400

        # 3) 서명 검증 (앱과 동일 포맷: url + user_id)
        try:
            msg = (url + str(user_id)).encode("utf-8")
            signature = base64.b64decode(signature_b64)
            log("[STEP] Verifying signature ... (msg_len:", len(msg), ", sig_len:", len(signature), ")")
            public_key.verify(signature, msg, ec.ECDSA(hashes.SHA256()))
            log("[STEP] Signature verified OK.")
        except Exception as e:
            log("❌ Signature verify failed:", e)
            return jsonify({"error": "서명 검증 실패"}), 403

        # 4) scan_id 확보/검증
        if scan_id is None:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id FROM scan_history
                WHERE user_id=%s AND url=%s
                ORDER BY created_at DESC LIMIT 1
            """, (user_id, url))
            r = cursor.fetchone(); cursor.close()
            if r:
                scan_id = int(r["id"])
                log("[STEP] Found recent scan_id:", scan_id)
            else:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scan_history (user_id, url, status)
                    VALUES (%s, %s, %s)
                """, (user_id, url, 'pending'))
                conn.commit()
                scan_id = cursor.lastrowid
                cursor.close()
                log("[STEP] New scan_id created:", scan_id)
        else:
            log("[STEP] Using provided scan_id:", scan_id)

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, url FROM scan_history WHERE id=%s", (scan_id,))
        sh = cursor.fetchone(); cursor.close()
        if not sh:
            return jsonify({"error": "존재하지 않는 scan_id"}), 400
        if int(sh["user_id"]) != user_id or normalize_url(sh["url"]) != url:
            log("❌ scan_id mismatch:", sh, "vs", {"user_id": user_id, "url": url})
            return jsonify({"error": "scan_id가 요청의 user_id/url과 일치하지 않습니다."}), 400

        # 5) 모델 결과 조회/생성
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT result, score FROM model_result WHERE scan_id=%s", (scan_id,))
        rr = cursor.fetchone(); cursor.close()

        if rr:
            result = int(rr["result"])
            score = float(rr["score"] or 0.0)
            log(f"[STEP] Existing result loaded. result={result}, score={score:.4f}")
        else:
            log("[STEP] No model_result. Running prediction...")
            feat = extractor.extract(url)
            input_df = pd.DataFrame([feat])
            result = int(model.predict(input_df)[0])
            try:
                score = float(model.predict_proba(input_df)[0][1])
            except Exception:
                score = 0.0
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO model_result (scan_id, model_version, score, result, explanation)
                VALUES (%s, %s, %s, %s, %s)
            """, (scan_id, MODEL_VERSION, score, result, EXPLANATION))
            cursor.execute("UPDATE scan_history SET status = 'done' WHERE id = %s", (scan_id,))
            conn.commit()
            cursor.close()
            log(f"[STEP] Predict done. result={result}, score={score:.4f}")

        # 6) 악성 차단 → 여기서 종료 (로그 저장 안 함)
        if result == 1:
            payload = {
                "message": "악성 URL로 판단되어 무결성 QR 생성이 차단되었습니다.",
                "prediction": result,
                "probability": round(score, 4),
                "scan_id": scan_id
            }
            log("[DONE] 422:", payload)
            return jsonify(payload), 422

        # 7) 정상 → 검증 성공만 알리고 종료 (로그 저장은 /secure-qr에서)
        resp = {
            "message": "서명 검증 및 예측 완료",
            "prediction": result,
            "probability": round(score, 4),
            "scan_id": scan_id
        }
        log("[DONE] 200:", resp)
        return jsonify(resp), 200

    except Exception as e:
        log("❌ Unhandled error in /qr_secure-scan:", e)
        traceback.print_exc()
        conn.rollback()
        return jsonify({"error": "처리 실패", "details": str(e)}), 500
    finally:
        conn.close()



# /secure-qr (보조 API) + 경로 저장
@qr_api.route('/secure-qr', methods=['POST'])
def save_secure_qr_log():
    try:
        data = request.get_json(force=False, silent=False)
    except Exception as ex:
        log("❌ JSON parse error(/secure-qr):", ex)
        return jsonify({"error": "invalid json", "details": str(ex)}), 400

    data = data or {}
    user_id = data.get("user_id")
    original_url_raw = data.get("original_url") or data.get("url")
    signature = data.get("signature") or data.get("signature_b64")
    qr_image_path = data.get("qr_image_path", "")

    log("\n========== /secure-qr DEBUG ==========")
    log("Raw payload:", data)
    log("======================================")

    if user_id is None or not original_url_raw or not signature or not qr_image_path:
        log("❌ Missing fields in /secure-qr")
        return jsonify({"error": "필수 항목 누락"}), 400

    try:
        user_id = int(user_id)
    except Exception:
        log("❌ user_id cast error in /secure-qr")
        return jsonify({"error": "user_id must be int"}), 400

    original_url = normalize_url(original_url_raw)

    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 1 FROM secure_qr_log
            WHERE user_id=%s AND original_url=%s
        """, (user_id, original_url))
        exists_log = cursor.fetchone()
        cursor.close()

        if exists_log:
            log("[STEP] secure_qr_log already exists (helper API).")
            return jsonify({"message": "이미 로그가 존재합니다."}), 200

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO secure_qr_log (user_id, original_url, signature, qr_image_path)
            VALUES (%s, %s, %s, %s)
        """, (user_id, original_url, signature, qr_image_path))
        conn.commit()
        cursor.close()

        log("[DONE] /secure-qr inserted.")
        return jsonify({"message": "무결성 QR 생성 로그 저장 완료"}), 201

    except Exception as e:
        log("❌ Unhandled error in /secure-qr:", e)
        traceback.print_exc()
        conn.rollback()
        return jsonify({"error": f"저장 실패: {str(e)}"}), 500
    finally:
        conn.close()
