from .base import *  # noqa: F401,F403
from decouple import config, Csv

DEBUG = True

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())

# ---------------------------------------------------------------------------
# Database - PostgreSQL
# ---------------------------------------------------------------------------
DATABASES["default"].update(  # noqa: F405
    {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
)

# Console-only, verbose logging for development
LOGGING["root"]["level"] = "DEBUG"          # noqa: F405
LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Relaxed security for local development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
