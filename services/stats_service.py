from flask import jsonify
from db import get_db_connection
from datetime import datetime, date, time, timedelta, timezone

KST_OFFSET = timedelta(hours=9)
DOW_KO = ["월", "화", "수", "목", "금", "토", "일"]

def _kst_today() -> date:
    return (datetime.utcnow().replace(tzinfo=timezone.utc) + KST_OFFSET).date()

def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())

def _kst_midnight_to_utc(d_kst: date) -> datetime:
    return datetime.combine(d_kst, time.min, tzinfo=timezone.utc) - KST_OFFSET

def _parse_bool_str(v) -> bool:
    return str(v).lower() in ('1', 'true', 'yes')

def _normalize_scope(raw: str, has_user_id: bool) -> str:
    if not raw:
        return "personal" if has_user_id else "global"
    raw = raw.lower()
    if raw in {"personal", "me", "mine", "user", "self"}:
        return "personal"
    if raw in {"global", "all", "total", "overall"}:
        return "global"
    return "personal" if has_user_id else "global"


# 요일별 악성
def get_weekday_malicious(include_hidden, user_id, scope_raw, weeks_back_raw):
    include_hidden = _parse_bool_str(include_hidden)
    scope = _normalize_scope(scope_raw, has_user_id=(user_id is not None))

    try:
        weeks_back = int(weeks_back_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "weeks_back must be integer"}), 400
    weeks_back = max(0, min(weeks_back, 104))

    if scope == 'personal' and not user_id:
        return jsonify({"error": "user_id is required for personal scope"}), 400
    
    # 집계 구간
    today_kst = _kst_today()
    this_monday_kst = _monday_of(today_kst)
    week_start_kst = this_monday_kst - timedelta(weeks=weeks_back)
    week_end_kst = week_start_kst + timedelta(days=6)

    start_utc = _kst_midnight_to_utc(week_start_kst)
    end_utc = _kst_midnight_to_utc(week_end_kst + timedelta(days=1))

    where = [
        "m.result = 1",
        "s.scanned_at >= %s",
        "s.scanned_at < %s",
    ]
    params = [start_utc, end_utc]

    if not include_hidden:
        where.append("s.is_user_visible = 1")
    if scope == 'personal':
        where.append("s.user_id = %s")
        params.append(user_id)

    where_sql = " AND ".join(where)
    select_cols = "s.scanned_at AS ts_utc" + (", s.user_id" if scope == 'global' else "")

    query = f"""
        SELECT {select_cols}
          FROM scan_history s
          JOIN model_result m ON m.scan_id = s.id
         WHERE {where_sql}
         ORDER BY s.scanned_at ASC
    """

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SET time_zone = '+00:00'")
        cursor.execute(query, params)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    
    counts = [0] * 7
    daily_users = [set() for _ in range(7)] if scope == 'global' else None
    all_users_in_range = set() if scope == 'global' else None

    for r in rows:
        ts_utc = r.get("ts_utc")
        if ts_utc is None:
            continue
        if ts_utc.tzinfo is None:
            ts_utc = ts_utc.replace(tzinfo=timezone.utc)
        ts_kst = ts_utc + KST_OFFSET
        idx = ts_kst.weekday()
        if 0 <= idx <= 6:
            counts[idx] += 1
            if scope == 'global':
                uid = r.get("user_id")
                if uid is not None:
                    daily_users[idx].add(uid)
                    all_users_in_range.add(uid)

    days = []
    total_mal = 0
    for i in range(7):
        day_kst = week_start_kst + timedelta(days=i)
        c = int(counts[i])
        total_mal += c
        uniq_users = (1 if c > 0 else 0) if scope == 'personal' else len(daily_users[i])
        days.append({
            "index": i,
            "day": DOW_KO[i],
            "date": day_kst.isoformat(),
            "malicious_count": c,
            "unique_user_count": uniq_users,
        })

    summary_unique = (1 if total_mal > 0 else 0) if scope == 'personal' else len(all_users_in_range)

    return jsonify({
        "scope": scope,
        "week_start": week_start_kst.isoformat(),
        "week_end": week_end_kst.isoformat(),
        "weeks_back": weeks_back,
        "include_hidden": include_hidden,
        "summary": {"total_malicious": total_mal, "unique_users_in_range": summary_unique},
        "days": days,
        "debug": {
            "raw_scope": scope_raw,
            "effective_scope": scope,
            "user_id": user_id,
            "weeks_back": weeks_back,
            "include_hidden": include_hidden,
            "range_kst": [week_start_kst.isoformat(), week_end_kst.isoformat()]
        }
    }), 200


def get_admin_stats(user_id_raw):
    if not user_id_raw:
        return jsonify({"error": "user_id 쿼리 파라미터가 필요합니다."}), 400
    try:
        user_id = int(user_id_raw)
    except:
        return jsonify({"error": "user_id는 숫자여야 합니다."}), 400

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user or not user["is_admin"]:
            return jsonify({"error": "관리자 권한이 없습니다."}), 403

        cur.execute("SELECT COUNT(*) AS total_users FROM users")
        total_users = cur.fetchone()["total_users"]

        cur.execute("SELECT COUNT(*) AS total_scans FROM scan_history")
        total_scans = cur.fetchone()["total_scans"]

        cur.execute("SELECT COUNT(*) AS malicious_count FROM model_result WHERE result = 1")
        malicious_count = cur.fetchone()["malicious_count"]

        benign_count = total_scans - malicious_count

        cur.execute("""
            SELECT user_id, COUNT(*) AS scan_count
              FROM scan_history
             GROUP BY user_id
             ORDER BY scan_count DESC
             LIMIT 1
        """)
        most_active = cur.fetchone()

        return jsonify({
            "total_users": total_users,
            "total_scans": total_scans,
            "malicious": malicious_count,
            "benign": benign_count,
            "most_active_user": most_active or {}
        }), 200
    finally:
        cur.close(); conn.close()


def get_daily_scans():
    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT DATE(scanned_at) AS date, COUNT(*) AS count
              FROM scan_history
             GROUP BY DATE(scanned_at)
             ORDER BY DATE(scanned_at) DESC
             LIMIT 30
        """)
        result = cur.fetchall()
        return jsonify(result), 200
    finally:
        cur.close(); conn.close()


def get_model_result_summary():
    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT result, COUNT(*) AS count
              FROM model_result
             GROUP BY result
        """)
        result = cur.fetchall()
        return jsonify(result), 200
    finally:
        cur.close(); conn.close()


def get_user_summary():
    conn = get_db_connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT COUNT(*) AS total_users FROM users")
        total = cur.fetchone()['total_users']

        cur.execute("SELECT COUNT(*) AS admin_users FROM users WHERE is_admin = TRUE")
        admins = cur.fetchone()['admin_users']

        return jsonify({"total_users": total, "admin_users": admins}), 200
    finally:
        cur.close(); conn.close()


def get_weekly_stats_list(include_hidden, user_id, scope_raw, count_raw, start_date_str):
    include_hidden = _parse_bool_str(include_hidden)
    scope = _normalize_scope(scope_raw, has_user_id=(user_id is not None))

    if scope == 'personal' and not user_id:
        return jsonify({"error": "user_id is required for personal scope"}), 400

    try:
        count = int(count_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "count must be integer"}), 400
    count = max(1, min(count, 104))

    if start_date_str:
        try:
            start_kst = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "start_date must be YYYY-MM-DD"}), 400
        start_monday_kst = _monday_of(start_kst)
        end_monday_kst = start_monday_kst
        first_monday_kst = end_monday_kst - timedelta(weeks=count-1)
    else:
        today_kst = _kst_today()
        end_monday_kst = _monday_of(today_kst)
        first_monday_kst = end_monday_kst - timedelta(weeks=count-1)

    # 요청 주차 범위(KST)
    week_ranges_kst = []
    cur = first_monday_kst
    for _ in range(count):
        week_start_kst = cur
        week_end_kst = cur + timedelta(days=6)
        week_ranges_kst.append((week_start_kst, week_end_kst))
        cur += timedelta(weeks=1)

    total_start_utc = _kst_midnight_to_utc(week_ranges_kst[0][0])
    total_end_utc   = _kst_midnight_to_utc(week_ranges_kst[-1][1] + timedelta(days=1))

    where_clauses = [
        "s.scanned_at >= %s",
        "s.scanned_at < %s"
    ]
    params = [total_start_utc, total_end_utc]

    if not include_hidden:
        where_clauses.append("s.is_user_visible = 1")
    if scope == 'personal':
        where_clauses.append("s.user_id = %s")
        params.append(user_id)

    where_sql = " AND ".join(where_clauses)

    # scope를 파라미터로 넘겨 global일 때만 COUNT(DISTINCT s.user_id)
    sql = f"""
        SELECT
            DATE(
                DATE_SUB(
                    DATE_ADD(s.scanned_at, INTERVAL 9 HOUR),
                    INTERVAL WEEKDAY(DATE_ADD(s.scanned_at, INTERVAL 9 HOUR)) DAY
                )
            ) AS week_start_kst,
            COUNT(*) AS total_scans,
            SUM(CASE WHEN m.result = 0 THEN 1 ELSE 0 END) AS benign_cnt,
            SUM(CASE WHEN m.result = 1 THEN 1 ELSE 0 END) AS malicious_cnt,
            COUNT(DISTINCT CASE WHEN %s = 'global' THEN s.user_id END) AS uniq_users
          FROM scan_history s
          JOIN model_result m ON m.scan_id = s.id
         WHERE {where_sql}
         GROUP BY week_start_kst
         ORDER BY week_start_kst ASC
    """

    conn = get_db_connection(); cur2 = conn.cursor(dictionary=True)
    try:
        cur2.execute("SET time_zone = '+00:00'")
        exec_params = [scope, *params]
        cur2.execute(sql, exec_params)
        rows = cur2.fetchall()
    finally:
        cur2.close(); conn.close()

    by_week = { r["week_start_kst"]: r for r in rows }

    result = []
    for idx, (ws_kst, we_kst) in enumerate(week_ranges_kst, start=1):
        r = by_week.get(ws_kst)
        total_scans   = int(r["total_scans"])   if r else 0
        benign_cnt    = int(r["benign_cnt"])    if r else 0
        malicious_cnt = int(r["malicious_cnt"]) if r else 0
        uniq_users    = (1 if total_scans > 0 else 0) if scope == 'personal' else (int(r["uniq_users"]) if r else 0)

        label = f"{idx}주차 ({ws_kst.strftime('%m.%d')}~{we_kst.strftime('%m.%d')})"
        result.append({
            "weekNo": idx,
            "start": ws_kst.isoformat(),
            "end": we_kst.isoformat(),
            "label": label,
            "scans": {"total": total_scans, "benign": benign_cnt, "malicious": malicious_cnt},
            "uniqueUsers": uniq_users
        })

    return jsonify({"weeks": result}), 200
