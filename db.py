import mysql.connector
from datetime import datetime, timezone

def get_db_connection():
    return mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "dmdekdnfdjTdj!",
        database = "naqjima"
    )


def get_user_public_key(user_id: int):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT public_key_pem FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
    conn.close()
    return None if not row else row[0]

def get_scan_created_at(scan_id: int):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT created_at FROM scan_history WHERE id=%s", (scan_id,))
        row = cur.fetchone()
    conn.close()
    if not row or not row[0]:
        return None
    ts = row[0]
    return ts if getattr(ts, "tzinfo", None) else ts.replace(tzinfo=timezone.utc)

def save_model_result(scan_id: int, model_version: str, prediction: int, explanation: str):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
          INSERT INTO model_result (scan_id, model_version, prediction, explanation, created_at)
          VALUES (%s,%s,%s,%s,NOW())
        """, (scan_id, model_version, prediction, explanation[:255]))
    conn.commit()
    conn.close()