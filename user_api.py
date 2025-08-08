from flask import Blueprint, request, jsonify
import bcrypt
from db import get_db_connection

user_api = Blueprint('user_api', __name__)

@user_api.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get("userName")
    password = data.get("userPassword")
    public_key = data.get("public_key")
    is_admin = data.get("is_admin", False)

    if not username or not password or not public_key:
        return jsonify({"error": "모든 필드를 입력해주세요."}), 400

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (userName, userPassword, public_key, is_admin)
        VALUES (%s, %s, %s, %s)
    """, (username, hashed_pw, public_key, is_admin))
    conn.commit()
    user_id = cursor.lastrowid

    cursor.close()
    conn.close()
    return jsonify({"message": "회원가입 완료", "user_id": user_id}), 201


@user_api.route('/users/login', methods=['POST'])
def login_user():
    data = request.get_json()
    username = data.get("userName")
    password = data.get("userPassword")

    if not username or not password:
        return jsonify({"error": "아이디 또는 비밀번호가 누락됨"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE userName = %s", (username,))
    user = cursor.fetchone()

    if not user or not bcrypt.checkpw(password.encode(), user['userPassword'].encode()):
        return jsonify({"error": "로그인 실패"}), 401

    # 로그인 성공 시 마지막 로그인 시간 갱신
    cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify({"message": "로그인 성공",
                    "user_id": user['id'],
                    "is_admin": bool(user['is_admin'])}), 200


@user_api.route('/withdraw', methods=['POST'])
def withdraw_user():
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id는 필수입니다."}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({"message": "회원 탈퇴가 완료되었습니다."}), 200
    
    except Exception as e:
        return jsonify({"error": f"탈퇴 중 오류: {str(e)}"}), 500


@user_api.route('/me/scans', methods=['GET'])
def get_my_scan_history():
    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id 쿼리 파라미터가 필요하다."}), 400
    
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
    result = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(result), 200