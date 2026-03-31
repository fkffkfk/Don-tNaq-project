# phishtank 블랙리스트 만들기

import os, sys, io, bz2, base64, hashlib, argparse
import pandas as pd
from urllib.parse import urlsplit, urlunsplit
import tldextract
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT)
from db import get_db_connection

def normalize_url(u: str) -> str:
    s = urlsplit((u or "").strip())
    scheme = (s.scheme or "http").lower()
    host = (s.hostname or "").lower()
    if s.port and not ((scheme == "http" and s.port == 80) or (scheme == "https" and s.port == 443)):
        netloc = f"{host}:{s.port}"
    else:
        netloc = host
    path = s.path or "/"
    return urlunsplit((scheme, netloc, path, s.query, ""))

_ext = tldextract.TLDExtract(suffix_list_urls=None)
def get_reg_domain(host: str) -> str:
    p = _ext(host or "")
    return f"{p.domain}.{p.suffix}" if p.domain  and p.suffix else (host or "")

def load_df_from_file(path: str) -> pd.DataFrame:
    if path.lower().endswith(".bz2"):
        with bz2.open(path, "rb") as f:
            return pd.read_csv(f)
    else:
        return pd.read_csv(path)
    
UPSERT_SQL = """
INSERT INTO blacklist_urls
(phish_id, original_b64, normalized_url, url_sha256, host, reg_domain,
 verified, online, submission_time, verification_time, target, source, first_seen_at, last_seen_at)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'phishtank_local', NOW(), NOW())
ON DUPLICATE KEY UPDATE
  original_b64=VALUES(original_b64),
  normalized_url=VALUES(normalized_url),
  url_sha256=VALUES(url_sha256),
  host=VALUES(host),
  reg_domain=VALUES(reg_domain),
  verified=VALUES(verified),
  online=VALUES(online),
  submission_time=VALUES(submission_time),
  verification_time=VALUES(verification_time),
  target=VALUES(target),
  last_seen_at=NOW();
"""

def upsert_rows(df: pd.DataFrame, only_verified_online: bool = True) -> int:
    required_cols = {"phish_id", "url"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError(f"CSV에 필수 컬럼이 없습니다: {required_cols} / 현재: {list(df.columns)}")
    
    rows = []
    for _, r in df.iterrows():
        url = str(r.get("url") or "").strip()
        if not url:
            continue

        nurl = normalize_url(url)
        sha = hashlib.sha256(nurl.encode("utf-8")).digest()
        host = urlsplit(nurl).hostname or ""
        rd = get_reg_domain(host)

        v = str(r.get("verified", "")).strip().lower()
        o = str(r.get("online", "")).strip().lower()
        verified = 1 if v in ("yes", "true", "1") else 0
        online = 1 if o in ("yes", "true", "1") else 0
        if only_verified_online and not (verified and online):
            continue

        sub_time = pd.to_datetime(r.get("submission_time"), errors="coerce")
        ver_time = pd.to_datetime(r.get("verification_time"), errors="coerce")
        target = None if pd.isna(r.get("target")) else str(r.get("target"))

        rows.append((
            int(r.get("phish_id")),
            base64.b64encode(url.encode("utf-8")).decode("ascii"),
            nurl,
            sha,
            host,
            rd,
            verified,
            online,
            None if pd.isna(sub_time) else sub_time.to_pydatetime(),
            None if pd.isna(ver_time) else ver_time.to_pydatetime(),
            target
        ))

    if not rows:
        print("No rows to upsert (after filter).")
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for i in range(0, len(rows), 20000):
            cursor.executemany(UPSERT_SQL, rows[i:i+20000])
            conn.commit()
        print(f"Upserted rows: {len(rows)}")
        return len(rows)
    finally:
        cursor.close()
        conn.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="로컬 CSV 경로(.csv 또는 .csv.bz2)")
    ap.add_argument("--no-filter", action="store_true", help="verified/online 필터 끄기")
    args = ap.parse_args()

    df = load_df_from_file(args.path)
    count = upsert_rows(df, only_verified_online=(not args.no_filter))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
          "INSERT INTO blacklist_sources(name, fetch_url, last_import_at, total_rows) "
          "VALUES('phishtank_local', %s, NOW(), %s) "
          "ON DUPLICATE KEY UPDATE fetch_url=VALUES(fetch_url), last_import_at=VALUES(last_import_at), total_rows=VALUES(total_rows)",
          (os.path.abspath(args.path), int(count or 0))
        )
        conn.commit()
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

if __name__ == "__main__":
    main()