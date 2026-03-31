from flask import Blueprint, request
from services import model_service


model_api = Blueprint('model_api', __name__)


# POST /model-results → 모델 예측 및 분석 결과 저장
@model_api.route('/model-results', methods=['POST'])
def create_model_result():
    payload = request.get_json(silent=True) or {}
    return model_service.create_model_result(payload)


# GET /model-results?user_id=3 → 사용자별 모델 결과 조회
@model_api.route('/model-results', methods=['GET'])
def get_model_results():
    scan_id = request.args.get("scan_id")
    return model_service.get_model_results(scan_id)
