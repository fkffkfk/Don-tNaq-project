from flask import Blueprint, request, jsonify
from db import get_db_connection

scan_api = Blueprint('scan_api', __name__)

# 스캔 기록 생성
@scan_api.route('/scans', methods=['POST'])
def create_scan():
    data = request.get_json()

    try:
        user_id = int(data.get("user_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "유효한 user_id가 필요해요"}), 400
    
    url = data.get("url")

    if not user_id or not url:
        return jsonify({"error": "user_id와 url은 필수입니다."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        return jsonify({"error": f"존재하지 않는 사용자입니다. user_id={user_id}"}), 400
    cursor.close()
    conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scan_history (user_id, url, status)
        VALUES (%s, %s, %s)
    """, (user_id, url, 'pending'))
    conn.commit()

    scan_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return jsonify({
        "message": "스캔 기록 저장 완료",
        "scan_id": scan_id
    }), 201

# 사용자별 QR코드 스캔 기록 조회 (모델 결과 포함)
@scan_api.route('/scans', methods=['GET'])
def get_scans():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id 쿼리 파라미터가 필요합니다."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.id AS scan_id, s.url, s.status, s.scanned_at,
               m.result, m.score, m.created_at AS predicted_at
        FROM scan_history s
        LEFT JOIN model_result m ON s.id = m.scan_id
        WHERE s.user_id = %s
        ORDER BY s.scanned_at DESC
    """, (user_id,))
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(results), 200
