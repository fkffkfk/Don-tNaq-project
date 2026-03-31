import time, hashlib

_TTL_SEC = 300 #5분
_STORE = {}

def _key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

def get(url: str):
    k = _key(url)
    v = _STORE.get(k)
    if not v:
        return None
    if v["exp"] < time.time():
        _STORE.pop(k, None)
        return None
    return v["data"]

def set(url: str, data, ttl: int | None = None):
    exp = time.time() + (ttl if ttl is not None else _TTL_SEC)
    _STORE[_key(url)] = {"data": data, "exp": exp}

def delete(url: str) -> None:
    _STORE.pop(_key(url), None)

def clear() -> None:
    _STORE.clear()