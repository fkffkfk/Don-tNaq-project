from urllib.parse import urlparse, parse_qs, unquote
import unicodedata
import tldextract

PROJECT_WHITELIST_RULES = [
    {"host": "naq21.github.io", "path_prefix": "/qr_test"},
    {"host": "github.com", "path_prefix": "/dyanii/don-t_nakk/"},
]

REDIRECT_KEYS = {"redirect", "redirect_url", "url", "to", "next",
                "continue", "dest", "r", "u", "link", "target"}

TRUSTED_DOMAINS = {
    "coupang.com",
    "coupang.co.kr",
    "naver.com",
    "google.com",
    "kakao.com",
    "apple.com",
    "amazon.com",
    "bing.com",
    "costco.co.kr",
    "lms.duksung.ac.kr",
    "delight.duksung.ac.kr",
    "duksung.ac.kr",
    "toss.im",
    "canva.com",
    "q-net.or.kr",
    "cvsnet.co.kr",
    "youtube.com",
    "skshieldus.com",
    "welaaa.com",
    "saramin.co.kr",
    "gong-cha.co.kr",
    "bunjang.co.kr",
    "joongna.com",
    "yahoo.co.jp",

    "postype.com",
}

def reg_domain_of(host: str) -> str:
    e = tldextract.extract(host)
    if e.domain and e.suffix:
        return f"{e.domain}.{e.suffix}"
    return host

def _norm_host(host: str) -> str:
    if not host:
        return ""
    h = unicodedata.normalize("NFKC", host.strip().rstrip(".")).lower()
    try:
        return h.encode("idna").decode("ascii")
    except Exception:
        return h
    
def _https_port_ok(p) -> bool:
    scheme = (p.scheme or "").lower()
    if scheme not in {"https", "http"}:
        return False
    default_port = 443 if scheme == "https" else 80
    port = p.port or default_port
    return str(port) in {"443", "80"}

def _match_trusted(host: str, trusted_domains: set[str]) -> bool:
    if not host:
        return False
    reg = reg_domain_of(host)
    for t in trusted_domains:
        t_norm = _norm_host(t)
        if reg == t_norm or host == t_norm or host.endswith("." + t_norm):
            return True
    return False


def is_project_whitelisted_url(url: str) -> bool:
    try:
        p = urlparse(url)
        if not _https_port_ok(p):
            return False
        
        host = _norm_host(p.hostname or "")
        path = (p.path or "")

        for rule in PROJECT_WHITELIST_RULES:
            rule_host = _norm_host(rule["host"])
            path_prefix = (rule.get("path_prefix") or "").rstrip("/")

            if host == rule_host or host.endswith("." + rule_host):
                if not path_prefix or path.startswith(path_prefix):
                    return True
        return False
    except Exception:
        return False



def is_whitelisted_url_safe(url: str, trusted_domains: set[str]) -> bool:
    try:
        p = urlparse(url)
        if not _https_port_ok(p):
            return False
        
        host = _norm_host(p.hostname or "")
        if not _match_trusted(host, trusted_domains):
            return False
        
        qs = parse_qs(p.query or "")
        for k, vs in qs.items():
            if k.lower() in REDIRECT_KEYS:
                for v in vs:
                    vp = urlparse(unquote(v))

                    if not vp.scheme and not vp.hostname:
                        continue
                    if vp.scheme and vp.scheme.lower() not in {"http", "https"}:
                        return False

                    vhost = _norm_host(vp.hostname or "")
                    if vhost and not _match_trusted(vhost, trusted_domains):
                        return False
        return True
    except Exception:
        return False


def is_whitelisted_url(url: str) -> bool:
    return is_project_whitelisted_url(url) or is_whitelisted_url_safe(url, TRUSTED_DOMAINS)


