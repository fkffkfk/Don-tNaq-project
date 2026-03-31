import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    SERVICE_BASE_URL = os.getenv("SERVICE_BASE_URL")
    QR_MAX_AGE_MINUTES = int(os.getenv("QR_MAX_AGE_MINUTES", "1440"))
    