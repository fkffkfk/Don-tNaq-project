# upload_api.py
import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import time

upload_api = Blueprint("upload_api", __name__)
ALLOWED = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")  # ✅ current_app 안 씀

@upload_api.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400

    ext = os.path.splitext(f.filename or "")[1].lower()
    if ext not in ALLOWED:
        return jsonify({"error": "unsupported type"}), 400

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    fname = secure_filename(f"{int(time.time())}_{f.filename}")
    save_path = os.path.join(UPLOAD_DIR, fname)
    f.save(save_path)

    base = request.host_url.rstrip("/")
    url = f"{base}/static/uploads/{fname}"
    return jsonify({"url": url}), 200
