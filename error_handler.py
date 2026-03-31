from flask import jsonify
import logging

def handle_custom_error(status_code, message, details=""):
    logging.warning(f"[{status_code}] {message} | Details: {details}")
    return jsonify({
        "code": status_code,
        "message": message,
        "details": details
    }), status_code

def handle_500_error(e):
    logging.error(f"[500] Internal Server Error: {str(e)}")
    return jsonify({
        "code": 500,
        "message": "서버 내부 오류가 발생했습니다.",
        "details": str(e)
    }), 500
