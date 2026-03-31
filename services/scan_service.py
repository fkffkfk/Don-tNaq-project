import logging
from flask import jsonify
from db import get_db_connection

logger = logging.getLogger("scan_activity")

def _to_bool01(v, default=1):
    if v is None:
        return default
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "t", "yes", "y"):
            return 1
        if s in ("0", "false", "f", "no", "n"):
            return 0
        try:
            return 1 if int(s) != 0 else 0
        except Exception:
            return default
    try:
        return 1 if int(v) != 0 else 0
    except Exception:
        return default
    
def create_scan(payload: dict):
    try:
        try:
            user_id = int(payload.get("user_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "유효한 user_id가 필요합니다."}), 400
        
        url = payload.get("url")
        if not user_id or not url:
            return jsonify({"error": "user_id와 url은 필수입니다."}), 400
        
        is_user_visible = _to_bool01(payload.get("is_user_visible"), default=1)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        exists = cursor.fetchone() is not None
        cursor.close()
        conn.close()

        if not exists:
            return jsonify({"error": f"존재하지 않는 사용자입니다. user_id={user_id}"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scan_history (user_id, url, status, is_user_visible)
            VALUES (%s, %s, %s, %s)
        """, (user_id, url, 'pending', is_user_visible))
        conn.commit()
        scan_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return jsonify({
            "message": "스캔 기록 저장 완료",
            "scan_id": scan_id,
            "is_user_visible": is_user_visible
        }), 201
    
    except Exception as e:
        logger.error(f"[ERROR: create_scan] {str(e)}")
        return jsonify({"error": "스캔 기록 중 오류가 발생하였습니다."}), 500
    
def get_scans(user_id, include_hidden):
    try:
        if not user_id:
            return jsonify({"error": "user_id 쿼리 파라미터가 필요합니다."}), 400
        
        show_all = str(include_hidden) in ("1", "true", "True")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if show_all:
            query = """
                SELECT s.id AS scan_id, s.url, s.status, s.scanned_at,
                       s.is_user_visible,
                       m.result, m.score, m.created_at AS predicted_at
                  FROM scan_history s
             LEFT JOIN model_result m ON s.id = m.scan_id
                 WHERE s.user_id = %s
              ORDER BY s.scanned_at DESC
            """
        else:
            query = """
                SELECT s.id AS scan_id, s.url, s.status, s.scanned_at,
                       m.result, m.score, m.created_at AS predicted_at
                  FROM scan_history s
             LEFT JOIN model_result m ON s.id = m.scan_id
                 WHERE s.user_id = %s AND s.is_user_visible = 1
              ORDER BY s.scanned_at DESC
            """
        
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        logger.info(f"[QUERY] user_id={user_id} | show_all={show_all} | result_count={len(results)}")
        return jsonify(results), 200
    
    except Exception as e:
        logger.error(f"[ERROR: get_scans] {str(e)}")
        return jsonify({"error": "스캔 이력 조회 중 오류가 발생하였습니다."}), 500
    


