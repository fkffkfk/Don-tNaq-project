from flask import Blueprint, request, jsonify
from services import qr_service

qr_api = Blueprint('qr_api', __name__)

# 인증 QR코드 생성 전 사전검증 (서명+블랙리스트+모델)
@qr_api.route('/qr_secure-scan', methods=['POST'])
def qr_secure_scan():
    payload = request.get_json(force=False, silent=False)
    return qr_service.qr_secure_scan(payload)


# 인증 QR코드 생성 로그 저장
@qr_api.route('/secure-qr', methods=['POST'])
def save_secure_qr_log():
    payload = request.get_json(force=False, silent=False)
    return qr_service.save_secure_qr_log(payload)

# 인증 QR코드 생성 로그 조회
@qr_api.route('/secure-qr', methods=['GET'])
def list_secure_qr_logs():
    user_id = request.args.get("user_id")
    return qr_service.list_secure_qr_logs(user_id)

