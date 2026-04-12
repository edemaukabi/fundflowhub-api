from os import getenv, path
from dotenv import load_dotenv
from .base import *  # noqa
from .base import BASE_DIR
from datetime import timedelta


local_env_file = path.join(BASE_DIR, ".envs", ".env.local")

if path.isfile(local_env_file):
    load_dotenv(local_env_file)

SECRET_KEY = getenv("SECRET_KEY", "django-insecure-local-dev-key-change-in-production")

DEBUG = getenv("DEBUG", "True") == "True"

SITE_NAME = getenv("SITE_NAME", "FundFlowHub")

BANK_NAME = getenv("BANK_NAME", "FundFlowHub")

ALLOWED_HOSTS = ["*"]

ADMIN_URL = getenv("ADMIN_URL", "admin/")

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(getenv("EMAIL_PORT", "1025"))
DEFAULT_FROM_EMAIL = getenv("DEFAULT_FROM_EMAIL", "noreply@fundflowhub.local")
DOMAIN = getenv("DOMAIN", "localhost:5173")
ADMIN_EMAIL = getenv("ADMIN_EMAIL", "admin@fundflowhub.local")

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB

CSRF_TRUSTED_ORIGINS = ["http://localhost:8080", "http://localhost:5173"]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]

CORS_ALLOW_CREDENTIALS = True

LOCKOUT_DURATION = timedelta(minutes=1)

LOGIN_ATTEMPTS = 3

OTP_EXPIRATION = timedelta(minutes=5)

# Card CVV — HMAC key. Override in production with a strong random value.
CVV_SECRET_KEY = getenv("CVV_SECRET_KEY", "local-dev-cvv-secret-change-in-production")

# Card number generation prefix/code — safe defaults for local dev
BANK_CARD_PREFIX = getenv("BANK_CARD_PREFIX", "4111")
BANK_CARD_CODE = getenv("BANK_CARD_CODE", "00")
