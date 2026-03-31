from dotenv import load_dotenv
load_dotenv()

import warnings
from sklearn.exceptions import InconsistentVersionWarning
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
warnings.filterwarnings("ignore", message=".*older XGBoost.*")


import os, logging, sys
from logging.handlers import RotatingFileHandler

for h in logging.root.handlers[:]:
    logging.root.removeHandler(h)

logging.getLogger().setLevel("INFO")
print("[ENV] SERVICE_BASE_URL =", os.getenv("SERVICE_BASE_URL"))
print("[ENV] SMTP_HOST =", os.getenv("SMTP_HOST"))
print("[ENV] SMTP_PORT =", os.getenv("SMTP_PORT"))
print("[ENV] MAIL_FROM =", os.getenv("MAIL_FROM"))


from flask import Flask, jsonify
from flask_cors import CORS
from limiter_config import limiter
from cache_config import cache
from error_handler import handle_500_error

from user_api import user_api
from scan_api import scan_api
from qr_api import qr_api
from model_api import model_api
from stats_api import stats_api
from posts_api import posts_api
from upload_api import upload_api

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
logger.propagate = False
fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(fmt)
if not logger.handlers:
    logger.addHandler(sh)

try:
    fh = RotatingFileHandler("server.log", maxBytes=5_000_000, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
except Exception:
    pass

logger.info("[ENV] SERVICE_BASE_URL=%s", os.getenv("SERVICE_BASE_URL"))
logger.info("[ENV] RATE_LIMIT_GLOBAL=%s", os.getenv("RATE_LIMIT_GLOBAL"))


app = Flask(__name__)

allow_origins = [o.strip() for o in os.getenv("ALLOW_ORIGINS", "").split(",") if o.strip()]
if allow_origins:
    CORS(app, resources={r"/*": {"origins": allow_origins}}, supports_credentials=True)
else:
    CORS(app)

limiter.init_app(app)
cache.init_app(app)


@app.after_request
def _security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    return resp

@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200

@app.get("/cache-test")
def cache_test():
    @cache.memoize(timeout=10)
    def slow(n):
        print("[cache-test] 실제 실행")
        return n * 2
    return jsonify({"value": slow(21)})




# Blueprint 등록
app.register_blueprint(user_api)
app.register_blueprint(scan_api)
app.register_blueprint(qr_api)
app.register_blueprint(model_api)
app.register_blueprint(stats_api)
app.register_blueprint(posts_api)
app.register_blueprint(upload_api)


@app.errorhandler(Exception)
def global_exception_handler(e):
    return handle_500_error(e)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

