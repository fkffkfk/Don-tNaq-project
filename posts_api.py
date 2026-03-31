import json
import logging
from flask import Blueprint, request, jsonify, current_app
from db import get_db_connection
from functools import wraps

posts_api = Blueprint("posts_api", __name__)
logger = logging.getLogger("user_activity")

ADMIN_ID = 6

def current_user_id_from_token():
    try:
        return int(request.headers.get("X-User-Id", "-1"))
    except Exception:
        return -1
    
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        uid = current_user_id_from_token()
        if uid != ADMIN_ID:
            return jsonify({"error": "관리자 권한이 필요합니다."}), 403
        return fn(*args, **kwargs)
    return wrapper

def _sanitize_image_list(images):
    if images is None:
        return None
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except Exception:
            images = []
    if not isinstance(images, list):
        images = []

    cleaned = []
    seen = set()
    for x in images:
        s = str(x).strip()
        if not s:
            continue
        if s not in seen:
            cleaned.append(s)
            seen.add(s)
    return cleaned

def _thumb_and_count(images_list):
    if not images_list:
        return None, 0
    return images_list[0], len(images_list)


# 글 생성 (관리자만)
@posts_api.route("/posts", methods=["POST"])
@admin_required
def create_post():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    images = _sanitize_image_list(data.get("image_urls", [])) or []

    if not title or not content:
        return jsonify({"error": "제목과 내용을 입력하세요."}), 400
    
    user_id = current_user_id_from_token()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO posts (user_id, title, content, image_urls)
            VALUES (%s, %s, %s, CAST(%s AS JSON))
        """, (user_id, title, content, json.dumps(images)))
        post_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT DATABASE() AS db")
        db_now = cursor.fetchone()["db"]
        cursor.execute("SELECT id, user_id, title, created_at FROM posts WHERE id=%s", (post_id,))
        row = cursor.fetchone()
        logger.info(f"[POST CREATE] id={post_id} db={db_now} row_exists={bool(row)}")

    finally:
        cursor.close()
        conn.close()


    logger.info(f"[POST CREATE] post_id={post_id} by uid={user_id}")
    return jsonify({"id": post_id, "db": db_now, "echo": row}), 201


# 글 목록 (전체 공개)
@posts_api.route("/posts", methods=["GET"])
def list_posts():
    limit = max(1, min(int(request.args.get("limit", 7)), 100))
    offset = max(0, int(request.args.get("offset", 0)))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, user_id, title, LEFT(content,120) AS preview,
                   thumb_url, image_count, created_at
            FROM posts
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return jsonify(rows), 200


@posts_api.route("/posts/<int:post_id>", methods=["GET"])
def get_post(post_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM posts WHERE id=%s", (post_id,))
        post = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not post:
        return jsonify({"error": "해당 글을 찾을 수 없습니다."}), 404

    img_val = post.get("image_urls")
    if isinstance(img_val, (bytes, bytearray)):
        img_val = img_val.decode("utf-8", errors="ignore")
    if isinstance(img_val, str):
        try:
            post["image_urls"] = json.loads(img_val)
        except Exception:
            post["image_urls"] = []
    elif img_val is None:
        post["image_urls"] = []

    return jsonify(post), 200


# 글 수정 (관리자만)
@posts_api.route("/posts/<int:post_id>", methods=["PUT"])
@admin_required
def update_post(post_id: int):
    data = request.get_json(silent=True) or {}
    title   = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()

    if not title or not content:
        return jsonify({"error": "제목과 내용을 입력하세요."}), 400

    has_images_key = "image_urls" in data
    images = _sanitize_image_list(data.get("image_urls")) if has_images_key else None

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if not has_images_key:
            cur.execute(
            "UPDATE posts SET title=%s, content=%s WHERE id=%s",
            (title, content, post_id),
        )
        else:
            thumb_url, image_count = _thumb_and_count(images)
            cur.execute(
                """
                UPDATE posts
                SET title=%s,
                    content=%s,
                    image_urls=CAST(%s AS JSON)
                WHERE id=%s
                """,
                (title, content, json.dumps(images), post_id),
            )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return jsonify({"ok": True}), 200


# 글 삭제 (관리자만)
@posts_api.route("/posts/<int:post_id>", methods=["DELETE"])
@admin_required
def delete_post(post_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM posts WHERE id=%s", (post_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return jsonify({"ok": True}), 200
