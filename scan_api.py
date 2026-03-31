from flask import Blueprint, request
from limiter_config import limiter
import logging
from services import scan_service

scan_api = Blueprint('scan_api', __name__)

logger = logging.getLogger("scan_activity")
if not logger.handlers:
    handler = logging.FileHandler("scan_activity.log")
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# 스캔 기록 생성
@scan_api.route('/scans', methods=['POST'])
@limiter.limit("10 per minute")
def create_scan():
    payload = request.get_json(silent=True) or {}
    return scan_service.create_scan(payload)


# 스캔 이력 조회 API
@scan_api.route('/scans', methods=['GET'])
def get_scans():
    user_id = request.args.get("user_id")
    include_hidden = request.args.get("inlcude_hidden", "0")
    return scan_service.get_scans(user_id, include_hidden)

