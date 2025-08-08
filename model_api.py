from flask import Blueprint, request, jsonify
from db import get_db_connection
import joblib
import pandas as pd

from feature_extractor import FeatureExtractor
from feature_module import DaysBased

model_api = Blueprint('model_api', __name__)

model = joblib.load("0624_rfxgbcat_model.pkl")
feature_params = joblib.load("0602_feature_params.pkl")

extractor = FeatureExtractor(
    letter_avg=feature_params['letter_avg'],
    letter_std=feature_params['letter_std'],
    thresholds=feature_params['thresholds'],
    keywords=feature_params['keywords']
)

# POST /model-results → 모델 예측 및 분석 결과 저장
@model_api.route('/model-results', methods=['POST'])
def create_model_result():
    data = request.get_json()
    scan_id = data.get("scan_id")
    model_version = "0624_rfxgbcat_v1"
    explanation = "RF+XGB+CAT weighted soft voting"

    if not scan_id:
        return jsonify({"error": "scan_id는 필수입니다."}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT url FROM scan_history WHERE id = %s", (scan_id,))
        row = cursor.fetchone()
        if not row or not row['url']:
            return jsonify({"error": "해당 scan_id에 대한 url을 찾을 수 없습니다."}), 404
        url = row['url']

        domain = DaysBased.extract_domain(url)
        if not domain:
            return jsonify({"error": "도메인 추출 실패"}), 400

        df = pd.DataFrame([{"URL": url, "domain": domain}])
        feature_df = extractor.transform(df)

        required_features = [
            'check_https', 'check_keyword', 'countletter',
            'ttl', 'ns_match', 'dns_query_success', 'DNS_mal',
            'daytime', 'is_untrusted_ca', 'is_weak_protocol',
            'is_weak_key_algo', 'is_short_lived_cert', 'is_expired',
            'domain_cn_mismatch', 'is_self_signed', 'san_count_high'
        ]

        for col in ['days_since_creation', 'days_since_update', 'days_until_expiration']:
            if col in feature_df.columns:
                feature_df.drop(columns=col, inplace=True)

        feature_df = feature_df[required_features]

        result = int(model.predict(feature_df)[0])
        score = float(model.predict_proba(feature_df)[0][1])

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO model_result (scan_id, model_version, score, result, explanation)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                model_version = VALUES(model_version),
                score = VALUES(score),
                result = VALUES(result),
                explanation = VALUES(explanation)
        """, (scan_id, model_version, score, result, explanation))

        cursor.execute("""
            UPDATE scan_history SET status = %s WHERE id = %s
        """, ('done', scan_id))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        return jsonify({"error": f"예측 실패: {str(e)}"}), 500
    
    return jsonify({
        "message": "모델 예측 및 저장 완료",
        "scan_id": scan_id,
        "prediction": "malicious" if result == 1 else "benign",
        "probability": round(score, 4)
    }), 201


# GET /model-results?user_id=3 → 사용자별 모델 결과 조회
@model_api.route('/model-results', methods=['GET'])
def get_model_results():
    scan_id = request.args.get("scan_id")
    if not scan_id:
        return jsonify({"error": "scan_id 쿼리 파라미터가 필요합니다."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT model_version, score, result, explanation, created_at
        FROM model_result
        WHERE scan_id = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, (scan_id,))
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(results), 200
