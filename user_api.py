import os
import logging
from dotenv import load_dotenv


from flask import Blueprint, request, jsonify, current_app, render_template
from db import get_db_connection
from limiter_config import limiter
from flask_limiter.util import get_remote_address
from mail_utils import send_verification_email

from utils.response import error, success
from services import user_service

load_dotenv()
SERVICE_BASE_URL = os.getenv("SERVICE_BASE_URL", "http://127.0.0.1:5000")


user_api = Blueprint('user_api', __name__)

logger = logging.getLogger("user_activity")
if not logger.handlers:
    handler = logging.FileHandler("user_activity.log")
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


#사전 인증 메일 발송
@user_api.route('/users/pre-verify', methods=['POST'])
def pre_verify():
    payload = request.get_json(silent=True) or {}
    return user_service.pre_verify(payload, SERVICE_BASE_URL)


# 이메일 인증 여부 확인
@user_api.route('/users/verify-status', methods=['GET'])
def verify_status():
    email = (request.args.get("email") or "").strip().lower()
    return user_service.verify_status(email)



#회원가입
@user_api.route('/users', methods=['POST'])
def signup():
    payload = request.get_json(silent=True) or {}
    return user_service.signup(payload)


# 이메일 인증 처리 (링크)
@user_api.route('/verify', methods=['GET'])
def verify_email():
    token = (request.args.get("token") or "").strip()
    return user_service.verify_email(token)


# 인증 메일 재전송
@user_api.route('/verify/resend', methods=['POST'])
def resend_verify():
    payload = request.get_json(silent=True) or {}
    return user_service.resend_verify(payload, SERVICE_BASE_URL)


#로그인
@user_api.route('/users/login', methods=['POST'])
# @limiter.limit("5 per second", key_func=get_remote_address, override_defaults=True)
def login_user():
    payload = request.get_json(silent=True) or {}
    return user_service.login_user(payload, request.remote_addr)


# 회원탈퇴
@user_api.route('/withdraw', methods=['POST'])
def withdraw_user():
    payload = request.get_json(silent=True) or {}
    return user_service.withdraw_user(payload)


#스캔기록
@user_api.route('/me/scans', methods=['GET'])
def get_my_scan_history():
    user_id = request.args.get("user_id")
    return user_service.get_my_scan_history(user_id)

