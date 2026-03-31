import os
import time, secrets, bcrypt
from flask import jsonify, render_template, current_app
from db import get_db_connection
from utils.response import error, success
from mail_utils import send_verification_email
from dotenv import load_dotenv

load_dotenv()

SERVICE_BASE_URL = os.getenv("SERVICE_BASE_URL", "http://127.0.0.1:5000")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER)
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "낚낚시꾼 팀")


def issue_email_token(minutes: int=30):
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time() + minutes * 60)
    return token, expires_at

def _verify_link(token: str, base_url: str) -> str:
    return f"{(base_url or SERVICE_BASE_URL).rstrip('/')}/verify?token={token}"

def _send_verify_email(to_email: str, verify_url: str):
    send_verification_email(
            smtp_host=SMTP_HOST, smtp_port=SMTP_PORT,
            smtp_user=SMTP_USER, smtp_pass=SMTP_PASS,
            mail_from=MAIL_FROM, mail_from_name=MAIL_FROM_NAME,
            to_email=to_email, verify_url=verify_url
        )

def find_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE email=%s LIMIT 1", (email,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

# 사전 인증 메일 발송
def pre_verify(payload: dict, base_url: str):
    email = (payload.get("email") or "").strip().lower()
    public_key = (payload.get("public_key") or "").strip()
    if not email:
        return error("이메일이 필요합니다.")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, is_verified FROM users WHERE email=%s LIMIT 1", (email,))
    row = cursor.fetchone()

    token, expires_at = issue_email_token(30)
    verify_url = _verify_link(token, base_url)

    try:
        if not row:
            cursor.execute("""
                INSERT INTO users (
                    userName, userPassword, public_key, is_admin,
                    email, is_verified, email_verify_token, email_token_expires
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (email, None, public_key, 0, email, 0, token, expires_at))
            user_id = cursor.lastrowid
        else:
            if row["is_verified"]:
                return error("이미 인증된 이메일입니다.", 409)
            cursor.execute("""
                UPDATE users
                   SET email_verify_token=%s,
                       email_token_expires=%s,
                       public_key = COALESCE(%s, public_key)
                 WHERE id=%s
            """, (token, expires_at, public_key or None, row["id"]))
            user_id = row["id"]

        conn.commit()
        _send_verify_email(email, verify_url)
        return success({"message": "인증 메일을 보냈습니다. 메일함을 확인하세요.", "user_id": user_id})
    except Exception:
        conn.rollback()
        current_app.logger.exception("pre-verify error")
        return error("메일 전송 실패. 잠시 후 다시 시도하세요.", 500, dev_verify_url=verify_url)
    finally:
        cursor.close()
        conn.close()


# 이메일 인증 여부 확인
def verify_status(email: str):
    email = (email or "").strip().lower()
    if not email:
        return error("이메일이 필요합니다.")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT is_verified FROM users WHERE email=%s LIMIT 1", (email,))
        row = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not row:
        return jsonify({"verified": False, "message": "해당 이메일이 존재하지 않습니다."}), 404
    return jsonify({"verified": bool(row["is_verified"])}), 200


# 회원가입
def signup(payload: dict):
    username   = (payload.get("userName") or "").strip()
    password   = (payload.get("userPassword") or "").strip()
    public_key = (payload.get("public_key") or "").strip()
    email      = (payload.get("email") or "").strip().lower()
    is_admin   = bool(payload.get("is_admin", False))

    if not email or not password or not public_key:
        return error("email, userPassword, public_key가 필요합니다.")

    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, is_verified, userPassword FROM users WHERE email=%s LIMIT 1", (email,))
        row = cur.fetchone()
        if not row:
            return error("사전 인증이 필요합니다. 먼저 인증 메일을 보내세요.", 403)
        if not row["is_verified"]:
            return error("이메일 인증이 완료되지 않았습니다.", 403)
        if row["userPassword"] is not None:
            return error("이미 가입이 완료된 계정입니다.", 409)

        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute("""
            UPDATE users
               SET userName=%s,
                   userPassword=%s,
                   public_key=%s,
                   is_admin=%s
             WHERE id=%s
        """, (username or email, hashed_pw, public_key, is_admin, row["id"]))
        conn.commit()
        return success({"message": "회원가입이 완료되었습니다.", "user_id": row["id"]}, 201)
    finally:
        cur.close(); conn.close()


# 이메일 인증 처리 (토큰)
def verify_email(token: str):
    token = (token or "").strip()
    if not token:
        return render_template("verify_fail.html", reason="잘못된 요청(토큰 없음)"), 400

    now = int(time.time())
    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, email_token_expires
              FROM users
             WHERE email_verify_token=%s
             LIMIT 1
        """, (token,))
        row = cur.fetchone()
        if not row:
            return render_template("verify_fail.html", reason="유효하지 않은 토큰이거나 이미 사용됨"), 400
        if not row["email_token_expires"] or row["email_token_expires"] < now:
            return render_template("verify_fail.html", reason="토큰이 만료되었습니다."), 400

        cur.execute("""
            UPDATE users
               SET is_verified=1,
                   email_verify_token=NULL,
                   email_token_expires=NULL
             WHERE id=%s
        """, (row["id"],))
        conn.commit()
        return render_template("verify_success.html"), 200
    finally:
        cur.close(); conn.close()


# 인증 메일 재전송
def resend_verify(payload: dict, base_url: str):
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "email이 필요합니다."}), 400

    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, is_verified FROM users WHERE email=%s LIMIT 1", (email,))
        user = cur.fetchone()
        if not user:
            return jsonify({"error": "해당 이메일로 가입된 계정이 없습니다."}), 404
        if user["is_verified"]:
            return jsonify({"message": "이미 인증된 이메일입니다."}), 200

        token, expires_at = issue_email_token(30)
        cur.execute("""
            UPDATE users
               SET email_verify_token=%s,
                   email_token_expires=%s
             WHERE id=%s
        """, (token, expires_at, user["id"]))
        conn.commit()

        verify_url = _verify_link(token, base_url)
        try:
            _send_verify_email(email, verify_url)
        except Exception:
            current_app.logger.exception("인증 메일 재전송 실패")
            return jsonify({
                "error": "메일 전송 실패. 잠시 후 다시 시도하세요.",
                "dev_verify_url": verify_url
            }), 500

        return jsonify({"message": "인증 메일을 다시 보냈습니다."}), 200
    finally:
        cur.close(); conn.close()


# 로그인
def login_user(payload: dict, remote_ip: str):
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("userPassword") or "").strip()

    if not email or not password:
        return jsonify({"error": "이메일 또는 비밀번호가 누락됨"}), 400

    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, userName, email, userPassword, is_admin, is_verified
              FROM users
             WHERE email=%s
             LIMIT 1
        """, (email,))
        user = cur.fetchone()
        if (not user) or (not user["userPassword"]) or (not user["is_verified"]):
            return jsonify({"error": "로그인 실패"}), 401

        db_hash = user["userPassword"]
        if isinstance(db_hash, str):
            db_hash = db_hash.encode()
        if not bcrypt.checkpw(password.encode(), db_hash):
            return jsonify({"error": "로그인 실패"}), 401

        # 마지막 로그인 시간 갱신
        cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user["id"],))
        conn.commit()

        return jsonify({
            "message": "로그인 성공",
            "user_id": user["id"],
            "is_admin": bool(user["is_admin"])
        }), 200
    finally:
        cur.close(); conn.close()


# 회원탈퇴
def withdraw_user(payload: dict):
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("password") or "").strip()
    mode = (payload.get("mode") or "soft").strip().lower()

    if not email or not password:
        return jsonify({"error": "email과 password는 필수입니다."}), 400
    if mode not in ("soft", "hard"):
        return jsonify({"error": "mode는 soft 또는 hard 여야 합니다."}), 400

    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, userPassword, is_admin
              FROM users
             WHERE email=%s
             LIMIT 1
        """, (email,))
        user = cur.fetchone()
        if not user:
            return jsonify({"error": "존재하지 않는 계정이거나 비밀번호가 올바르지 않습니다."}), 401

        db_hash = user["userPassword"]
        if isinstance(db_hash, str):
            db_hash = db_hash.encode()
        if not bcrypt.checkpw(password.encode(), db_hash):
            return jsonify({"error": "존재하지 않는 계정이거나 비밀번호가 올바르지 않습니다."}), 403

        if user.get("is_admin"):
            return jsonify({"error": "관리자 계정은 이 경로로 탈퇴할 수 없습니다."}), 403

        user_id = user["id"]

        if mode == "soft":
            anon_name = f"탈퇴회원_{user_id}"
            anon_email = f"deleted_{user_id}@example.invalid"
            random_pw = secrets.token_urlsafe(32).encode()
            new_hash = bcrypt.hashpw(random_pw, bcrypt.gensalt()).decode()

            cur.execute("""
                UPDATE users
                   SET userName=%s,
                       email=%s,
                       userPassword=%s,
                       is_verified=0,
                       is_deleted=1,
                       deleted_at=NOW(),
                       email_verify_token=NULL
                 WHERE id=%s
            """, (anon_name, anon_email, new_hash, user_id))

        else:
            cur.execute("""
                DELETE mr FROM model_result mr
                JOIN scan_history sh ON mr.scan_id = sh.id
                WHERE sh.user_id = %s
            """, (user_id,))
            cur.execute("DELETE FROM scan_history WHERE user_id=%s", (user_id,))
            cur.execute("DELETE FROM secure_qr_log WHERE user_id=%s", (user_id,))
            cur.execute("""
                DELETE pi FROM post_images pi
                JOIN posts p ON pi.post_id = p.id
                WHERE p.user_id = %s
            """, (user_id,))
            cur.execute("DELETE FROM posts WHERE user_id=%s", (user_id,))
            cur.execute("DELETE FROM users WHERE id=%s", (user_id,))

        conn.commit()
        return jsonify({"message": "회원 탈퇴가 완료되었습니다.", "mode": mode}), 200

    except Exception as e:
        conn.rollback()
        current_app.logger.exception("[WITHDRAW ERROR]")
        return jsonify({"error": f"회원 탈퇴 중 오류가 발생하였습니다: {str(e)}"}), 500
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass


# 스캔 기록
def get_my_scan_history(user_id):
    if not user_id:
        return jsonify({"error": "user_id 쿼리 파라미터가 필요하다."}), 400

    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT s.id AS scan_id, s.url, s.status, s.scanned_at,
                   m.result, m.score, m.created_at AS predicted_at
              FROM scan_history s
         LEFT JOIN model_result m ON s.id = m.scan_id
             WHERE s.user_id = %s
          ORDER BY s.scanned_at DESC
        """, (user_id,))
        result = cur.fetchall()
        return jsonify(result), 200
    finally:
        cur.close(); conn.close()