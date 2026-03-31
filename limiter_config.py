import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
DEFAULT_LIMIT = os.getenv("RATE_LIMIT_GLOBAL")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    default_limits=[DEFAULT_LIMIT] if DEFAULT_LIMIT else [],
    strategy="fixed-window",
)