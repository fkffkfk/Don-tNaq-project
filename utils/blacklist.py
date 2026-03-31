import hashlib
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import tldextract
from db import get_db_connection

def normalize_url(raw_url: str) -> str:
    u = urlparse(raw_url.strip())
    scheme = u.scheme.lower() or "http"
    netloc = u.netloc.lower()

    if netloc.endswith(':80') and scheme == 'http':
        netloc = netloc[:-3]
    if netloc.endswith(':443') and scheme == 'https':
        netloc = netloc[:-4]

    
    path = u.path or '/'
    if not path.startswith('/'):
        path = '/' + path

    query_items = sorted(parse_qsl(u.query, keep_blank_values=True))
    query = urlencode(query_items)

    return urlunparse((scheme, netloc, path, '', query, ''))

def make_hash(normalized_url: str) -> bytes:
    return hashlib.sha256(normalized_url.encode("utf-8")).digest()

def reg_domain_of(host: str) -> str:
    e = tldextract.extract(host)
    if e.domain and e.suffix:
        return f"{e.domain}.{e.suffix}"
    return host

def is_blacklisted_url(raw_url: str) -> bool:
    norm = normalize_url(raw_url)
    h = make_hash(norm)

    sql = """
        SELECT 1 FROM blacklist_urls
        WHERE url_sha256=%s
          AND verified = 1
          AND online = 1
        LIMIT 1
    """

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (h,))
            return cursor.fetchone() is not None
    finally:
        try:
            conn.close()
        except Exception:
            pass
