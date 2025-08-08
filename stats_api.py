from flask import Blueprint, jsonify
from db import get_db_connection

stats_api = Blueprint('stats_api', __name__)

@stats_api.route('/stats', methods=['GET'])
def get_malicious_stats():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT DATE(s.scanned_at) AS date, COUNT(*) AS malicious_count
        FROM scan_history s
        JOIN model_result m ON s.id = m.scan_id
        WHERE m.result = 1
        GROUP BY DATE(s.scanned_at)
        ORDER BY date DESC
        LIMIT 10
    """)
    result = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(result), 200