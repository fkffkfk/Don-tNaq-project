import pandas as pd
import base64
from urllib.parse import urlparse
from utils.blacklist import normalize_url, make_hash, reg_domain_of
from db import get_db_connection


def to_bool_int(val):
    if isinstance(val, str):
        return 1 if val.strip().lower() == "yes" else 0
    if pd.isna(val):
        return 0
    try:
        return int(val)
    except Exception:
        return 0


def load_phishtank_csv(path: str, limit: int | None = None):
    df = pd.read_csv(path)

    cols = ['phish_id', 'url', 'verified', 'online', 'submission_time', 'target']
    rows = df[[c for c in cols if c in df.columns]].dropna(subset=['url'])
    
    if limit:
        rows = rows.head(limit)

    sql = """
        INSERT IGNORE INTO blacklist_urls
         (phish_id, original_b64, normalized_url, url_sha256,
          host, reg_domain, verified, online, submission_time, target, source)
         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    conn = get_db_connection()
    inserted = 0
    total = len(rows)

    print(f"[START] 총 {total}개 URL 블랙리스트 등록 시작...")

    with conn.cursor() as cursor:
        for i, row in rows.iterrows():
            try:
                raw = row['url']
                norm = normalize_url(raw)
                h = make_hash(norm)
                host = urlparse(norm).netloc
                reg = reg_domain_of(host)

                phish_id = int(row['phish_id'])
                original_b64 = base64.b64encode(raw.encode()).decode()
                verified = to_bool_int(row['verified']) if 'verified' in row else 0
                online = to_bool_int(row['online']) if 'online' in row else 0
                submission_time = row['submission_time'] if 'submission_time' in row else None
                target = row['target'] if 'target' in row else None

                cursor.execute(sql, (
                    phish_id,
                    original_b64,
                    norm,
                    h,
                    host,
                    reg,
                    verified,
                    online,
                    submission_time,
                    target,
                    "phishtank_local"
                ))
                inserted += 1

                if inserted % 100 == 0:
                    conn.commit()
                    print(f"  - {inserted}/{total}개 등록 완료")

            except Exception as e:
                print(f"[SKIP] {i}번째 URL 무시됨 ({e})")

    conn.commit()
    print(f"[DONE] 총 {total}개 중 {inserted}개 URL 블랙리스트 DB 등록 완료")


if __name__ == "__main__":
    load_phishtank_csv("verified_online.csv", limit=None)

# 지금은 500개로 제한 뒀지만 나중에는 None 으로 설정해서 제한 풀기