from flask import Blueprint, request
from services import stats_service

stats_api = Blueprint('stats_api', __name__)


@stats_api.route('/stats', methods=['GET'])
def get_weekday_malicious():
    return stats_service.get_weekday_malicious(
        include_hidden=request.args.get('include_hidden', '0'),
        user_id=request.args.get('user_id', type=int),
        scope_raw=request.args.get('scope', ''),
        weeks_back_raw=request.args.get('weeks_back', '0'),
    )


# 관리자용 API
@stats_api.route('/stats/admin', methods=['GET'])
def get_admin_stats():
    return stats_service.get_admin_stats(request.args.get("user_id"))


# 일자별 스캔 수
@stats_api.route('/stats/daily-scans', methods=['GET'])
def get_daily_scans():
    return stats_service.get_daily_scans()


# 모델 결과 요약(전체)
@stats_api.route('/stats/model-results-summary', methods=['GET'])
def get_model_result_summary():
    return stats_service.get_model_result_summary()


# 사용자 요약
@stats_api.route('/stats/user-summary', methods=['GET'])
def get_user_summary():
    return stats_service.get_user_summary()


# 주차 리스트 집계
@stats_api.route('/stats/weeks', methods=['GET'])
def get_weekly_stats_list():
    return stats_service.get_weekly_stats_list(
        include_hidden=request.args.get('include_hidden', '0'),
        user_id=request.args.get('user_id', type=int),
        scope_raw=request.args.get('scope', ''),
        count_raw=request.args.get('count', '8'),
        start_date_str=request.args.get('start_date')
    )

