from os import getenv, path
from dotenv import load_dotenv
from .base import *  # noqa
from .base import BASE_DIR
from datetime import timedelta


prod_env_file = path.join(BASE_DIR, ".envs", ".env.production")

if path.isfile(prod_env_file):
    load_dotenv(prod_env_file)

SECRET_KEY = getenv("SECRET_KEY")

DEBUG = getenv("DEBUG", "False") == "True"

SITE_NAME = getenv("SITE_NAME", "FundFlowHub")

BANK_NAME = getenv("BANK_NAME", "FundFlowHub")

ADMINS = [(getenv("ADMIN_NAME", "Admin"), getenv("ADMIN_EMAIL", ""))]

ALLOWED_HOSTS = getenv("ALLOWED_HOSTS", "fundflowhub-api.edemaukabi.dev").split(",")

ADMIN_URL = getenv("ADMIN_URL", "admin/")

EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"
EMAIL_HOST = getenv("EMAIL_HOST")
EMAIL_HOST_USER = getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = getenv("EMAIL_HOST_PASSWORD")
EMAIL_PORT = int(getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = getenv("DEFAULT_FROM_EMAIL")
DOMAIN = getenv("DOMAIN", "fundflowhub.edemaukabi.dev")
ADMIN_EMAIL = getenv("ADMIN_EMAIL")

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB

CSRF_TRUSTED_ORIGINS = getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://fundflowhub-api.edemaukabi.dev,https://fundflowhub.edemaukabi.dev",
).split(",")

CORS_ALLOWED_ORIGINS = getenv(
    "CORS_ALLOWED_ORIGINS",
    "https://fundflowhub.edemaukabi.dev",
).split(",")

CORS_ALLOW_CREDENTIALS = True

LOCKOUT_DURATION = timedelta(minutes=10)

LOGIN_ATTEMPTS = 3

OTP_EXPIRATION = timedelta(minutes=5)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = getenv("SECURE_SSL_REDIRECT", "True") == "True"

SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 300

SECURE_HSTS_INCLUDE_SUBDOMAINS = getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "True") == "True"

SECURE_HSTS_PRELOAD = getenv("SECURE_HSTS_PRELOAD", "True") == "True"

SECURE_CONTENT_TYPE_NOSNIFF = getenv("SECURE_CONTENT_TYPE_NOSNIFF", "True") == "True"
