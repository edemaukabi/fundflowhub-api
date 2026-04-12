"""
Test settings — extends local, swaps PostgreSQL for SQLite so tests run
without a live database server. Import everything from local then override.
"""
import os

# Ensure env vars that production code reads via os.getenv() are available
# during tests, before any Django app is loaded.
os.environ.setdefault("BANK_NAME", "FundFlowHub")
os.environ.setdefault("BANK_CARD_PREFIX", "4111")
os.environ.setdefault("BANK_CARD_CODE", "00")
os.environ.setdefault("CVV_SECRET_KEY", "test-cvv-secret-key-for-pytest")

from .local import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Faster password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Suppress Celery task execution during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use a predictable CVV secret so CVV tests are reproducible
CVV_SECRET_KEY = "test-cvv-secret-key-for-pytest"

# Silence email in tests (already console backend but make sure)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
