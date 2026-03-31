"""08/08 기준 이 코드 사용안함"""

from flask import Blueprint, request, jsonify
from db import get_db_connection
import base64
import joblib
import pandas as pd
import traceback
import re

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from feature_extractor import FeatureExtractor
from feature_module import ExistenceBased, LengthBased, CountBased, DaysBased, DNS, SSL

qr_secure_api = Blueprint('qr_secure_api', __name__)

# --- 모델/파라미터 로드 (부팅 로그) ---
print("[BOOT] Loading model/params ...")
model = joblib.load("0624_rfxgbcat_model.pkl")
params = joblib.load("0602_feature_params.pkl")
print("[BOOT] Model/params loaded.")

extractor = FeatureExtractor(
    letter_avg=params['letter_avg'],
    letter_std=params['letter_std'],
    thresholds=params['thresholds'],
    keywords=params['keywords']
)

MODEL_VERSION = "0624_rfxgbcat_v1"
EXPLANATION = "RF+XGB+CAT weighted soft voting"


def _robust_load_public_key(public_key_pem_str: str):
    """
    DB에 저장된 공개키 문자열을 최대한 유연하게 로딩:
    - \\n -> \n 복원
    - PEM 헤더가 있으면 PEM 로드
    - 헤더 없으면 base64 DER 시도
    - base64 본문을 PEM 래핑해서 재시도
    """
    if public_key_pem_str is None:
        raise ValueError("empty public_key")

    s = public_key_pem_str.strip().strip('"').strip("'")
    s_fixed = s.replace("\\n", "\n")

    # PEM 헤더가 있으면 PEM 우선
    if "BEGIN PUBLIC KEY" in s_fixed or "BEGIN EC PUBLIC KEY" in s_fixed:
        try:
            return serialization.load_pem_public_key(s_fixed.encode())
        except Exception as e:
            print("WARN: PEM load failed once:", e)
            # 공백/탭/CR 제거 후 재시도
            s_compact = re.sub(r"[ \t\r]+", "", s_fixed)
            s_compact = s_compact.replace("-----BEGINPUBLICKEY-----", "-----BEGIN PUBLIC KEY-----") \
                                 .replace("-----ENDPUBLICKEY-----", "-----END PUBLIC KEY-----") \
                                 .replace("-----BEGINECPUBLICKEY-----", "-----BEGIN EC PUBLIC KEY-----") \
                                 .replace("-----ENDECPUBLICKEY-----", "-----END EC PUBLIC KEY-----")
            return serialization.load_pem_public_key(s_compact.encode())

    # 헤더 없으면 base64 DER로 시도
    try:
        s_compact = re.sub(r"\s+", "", s_fixed)
        der = base64.b64decode(s_compact, validate=True)
        return serialization.load_der_public_key(der)
    except Exception as e:
        print("WARN: DER load failed:", e)

    # 마지막 시도: base64 같으면 PEM 래핑
    try:
        s_compact = re.sub(r"\s+", "", s_fixed)
        _ = base64.b64decode(s_compact, validate=True)
        pem_wrapped = "-----BEGIN PUBLIC KEY-----\n"
        pem_wrapped += "\n".join([s_compact[i:i+64] for i in range(0, len(s_compact), 64)])
        pem_wrapped += "\n-----END PUBLIC KEY-----\n"
        return serialization.load_pem_public_key(pem_wrapped.encode())
    except Exception as e:
        print("WARN: wrap-PEM load failed:", e)

    raise ValueError("Unsupported public_key format")


@qr_secure_api.route('/qr_secure-scan', methods=['POST'])
def qr_secure_scan():
    data = request.get_json(silent=True) or {}

    # --- 입력 파싱 ---
    url = data.get("url") or data.get("original_url")
    signature_b64 = data.get("signature") or data.get("signature_b64")
    user_id = data.get("user_id")
    scan_id = data.get("scan_id")
    qr_image_path = data.get("qr_image_path", "")

    # === 🔍 디버그: 입력 요약 ===
    print("\n========== /qr_secure-scan DEBUG ==========")
    try:
        print("Raw payload:", data)
        print("Parsed url:", url)
        print("Parsed signature_b64 exists:", bool(signature_b64),
              "len=", len(signature_b64) if signature_b64 else 0)
        print("Parsed user_id:", user_id, "(type:", type(user_id), ")")
        print("Parsed scan_id:", scan_id, "(type:", type(scan_id), ")")
        print("Parsed qr_image_path:", qr_image_path)
    except Exception:
        pass
    print("==========================================")

    # --- 필수값 체크 ---
    missing = []
    if not url:
        missing.append("url/original_url")
    if not signature_b64:
        missing.append("signature")
    if user_id is None:  # 0 허용
        missing.append("user_id")
    if missing:
        print("Missing fields:", missing)
        return jsonify({"error": f"missing fields: {missing}"}), 400

    # --- 타입 변환 ---
    try:
        user_id = int(user_id)
        if scan_id is not None:
            scan_id = int(scan_id)
    except Exception as e:
        print("Type cast error:", e)
        return jsonify({"error": "user_id/scan_id must be int"}), 400

    conn = get_db_connection()
    try:
        # --- 공개키 조회 ---
        print("[STEP] Fetching public key for user_id:", user_id)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT public_key FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()

        if not row or not row['public_key']:
            print("No public key in DB for user:", user_id)
            return jsonify({"error": "공개키를 찾을 수 없습니다."}), 404

        # --- 공개키 로딩 (강인) ---
        try:
            public_key_pem_str = row['public_key']
            print("DEBUG: raw public_key head:",
                  repr(public_key_pem_str[:80]) if public_key_pem_str else None)
            public_key = _robust_load_public_key(public_key_pem_str)
            print("[STEP] Public key loaded OK.")
        except Exception as e:
            print("Public key load error (robust):", e)
            return jsonify({"error": "공개키 로딩 실패", "details": str(e)}), 400

        # --- 서명 검증 ---
        try:
            # ⚠️ 앱과 동일 포맷. 강화하려면 url+user_id+scan_id 로 맞추고 양쪽 모두 변경
            message = (url + str(user_id)).encode('utf-8')
            signature = base64.b64decode(signature_b64)
            print("[STEP] Verifying signature ... (msg_len:", len(message),
                  ", sig_len:", len(signature), ")")
            public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
            print("[STEP] Signature verified OK.")
        except Exception as e:
            print("Signature verify failed:", e)
            return jsonify({"error": "서명 검증 실패", "details": str(e)}), 403

        # --- scan_id 확보 ---
        if scan_id is None:
            print("[STEP] scan_id not provided. Trying to find recent scan...")
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id FROM scan_history
                WHERE user_id=%s AND url=%s
                ORDER BY created_at DESC LIMIT 1
            """, (user_id, url))
            row = cursor.fetchone()
            cursor.close()

            if row:
                scan_id = int(row["id"])
                print("[STEP] Found recent scan_id:", scan_id)
            else:
                print("[STEP] No recent scan. Creating new scan_history record...")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scan_history (user_id, url, status)
                    VALUES (%s, %s, %s)
                """, (user_id, url, 'pending'))
                conn.commit()
                scan_id = cursor.lastrowid
                cursor.close()
                print("[STEP] New scan_id created:", scan_id)
        else:
            print("[STEP] Using provided scan_id:", scan_id)

        # --- scan_id ↔ (user_id, url) 교차검증 ---
        print("[STEP] Cross-check scan_id with (user_id, url)")
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, url FROM scan_history WHERE id=%s", (scan_id,))
        scan_row = cursor.fetchone()
        cursor.close()

        if not scan_row:
            print("scan_id not found:", scan_id)
            return jsonify({"error": "존재하지 않는 scan_id"}), 400

        if int(scan_row["user_id"]) != user_id or scan_row["url"] != url:
            print("scan_id mismatch:", scan_row, "vs", {"user_id": user_id, "url": url})
            return jsonify({"error": "scan_id가 요청의 user_id/url과 일치하지 않습니다."}), 400

        # --- 모델 결과 존재 여부 확인 ---
        print("[STEP] Checking existing model_result for scan_id:", scan_id)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT result, score FROM model_result WHERE scan_id=%s", (scan_id,))
        rr = cursor.fetchone()
        cursor.close()

        if rr:
            result = int(rr["result"])
            score = float(rr["score"]) if rr["score"] is not None else 0.0
            print(f"[STEP] Existing result loaded. result={result}, score={score:.4f}")
        else:
            print("[STEP] No model_result. Running prediction...")
            feature_dict = extractor.extract(url)
            input_df = pd.DataFrame([feature_dict])

            result = int(model.predict(input_df)[0])
            try:
                score = float(model.predict_proba(input_df)[0][1])  # 1=악성 확률 가정
            except Exception:
                score = 0.0
            print(f"[STEP] Predict done. result={result}, score={score:.4f}")

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO model_result (scan_id, model_version, score, result, explanation)
                VALUES (%s, %s, %s, %s, %s)
            """, (scan_id, MODEL_VERSION, score, result, EXPLANATION))
            cursor.execute("UPDATE scan_history SET status = 'done' WHERE id = %s", (scan_id,))
            conn.commit()
            cursor.close()
            print("[STEP] model_result inserted & scan_history updated.")

        # --- 악성이면 차단 (정상일 때만 다음 단계 진행) ---
        if result == 1:
            print("[STEP] Malicious detected. Block secure QR creation.")
            resp = {
                "message": "악성 URL로 판단되어 무결성 QR 생성이 차단되었습니다.",
                "prediction": result,
                "probability": round(float(score), 4),
                "scan_id": scan_id
            }
            print("[DONE] Response:", resp)
            return jsonify(resp), 422  # 정책에 따라 403/409/422 등 선택

        # --- secure_qr_log 중복 방지 후 기록 (정상일 때만) ---
        print("[STEP] Checking secure_qr_log duplication ...")
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 1 FROM secure_qr_log
            WHERE user_id=%s AND original_url=%s
        """, (user_id, url))
        exists_log = cursor.fetchone()
        cursor.close()

        if not exists_log:
            print("[STEP] Inserting secure_qr_log ...")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO secure_qr_log (user_id, original_url, signature, qr_image_path)
                VALUES (%s, %s, %s, %s)
            """, (user_id, url, signature_b64, qr_image_path))
            conn.commit()
            cursor.close()
            print("[STEP] secure_qr_log inserted.")
        else:
            print("[STEP] secure_qr_log already exists. Skip insert.")

        # --- 응답 ---
        resp = {
            "message": "서명 검증 및 예측 완료",
            "prediction": result,                 # 0=정상, 1=악성 (모델 정의에 따름)
            "probability": round(float(score), 4),
            "scan_id": scan_id
        }
        print("[DONE] Response:", resp)
        return jsonify(resp), 200

    except Exception as e:
        print("Unhandled error in /qr_secure-scan:", e)
        traceback.print_exc()
        conn.rollback()
        return jsonify({"error": "처리 실패", "details": str(e)}), 500
    finally:
        conn.close()


# (선택) 무결성 QR 생성 로그만 단독 저장하는 보조 API
@qr_secure_api.route('/secure-qr', methods=['POST'])
def save_secure_qr_log():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    original_url = data.get("original_url") or data.get("url")
    signature = data.get("signature") or data.get("signature_b64")
    qr_image_path = data.get("qr_image_path", "")

    print("\n========== /secure-qr DEBUG ==========")
    print("Raw payload:", data)
    print("======================================")

    if user_id is None or not original_url or not signature:
        print("Missing fields in /secure-qr")
        return jsonify({"error": "필수 항목 누락"}), 400

    try:
        user_id = int(user_id)
    except Exception:
        print("user_id cast error in /secure-qr")
        return jsonify({"error": "user_id must be int"}), 400

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
            print("[STEP] secure_qr_log already exists (helper API).")
            return jsonify({"message": "이미 로그가 존재합니다."}), 200

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO secure_qr_log (user_id, original_url, signature, qr_image_path)
            VALUES (%s, %s, %s, %s)
        """, (user_id, original_url, signature, qr_image_path))
        conn.commit()
        cursor.close()

        print("[DONE] /secure-qr inserted.")
        return jsonify({"message": "무결성 QR 생성 로그 저장 완료"}), 201

    except Exception as e:
        print("Unhandled error in /secure-qr:", e)
        traceback.print_exc()
        conn.rollback()
        return jsonify({"error": f"저장 실패: {str(e)}"}), 500
    finally:
        conn.close()
