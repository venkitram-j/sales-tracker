from .base import *  # noqa: F401,F403
from decouple import config, Csv

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

# ---------------------------------------------------------------------------
# Security hardening
# ---------------------------------------------------------------------------
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# ---------------------------------------------------------------------------
# Logging - rotating file handler + console, no DEBUG-level noise
# ---------------------------------------------------------------------------
LOGGING["handlers"]["file"] = {  # noqa: F405
    "class": "logging.handlers.RotatingFileHandler",
    "filename": str(LOGS_DIR / "sales_tracker.log"),  # noqa: F405
    "maxBytes": 50 * 1024 * 1024,  # 50 MB per file
    "backupCount": 10,
    "formatter": "verbose",
}
LOGGING["handlers"]["error_file"] = {  # noqa: F405
    "class": "logging.handlers.RotatingFileHandler",
    "filename": str(LOGS_DIR / "sales_tracker_error.log"),  # noqa: F405
    "maxBytes": 50 * 1024 * 1024,
    "backupCount": 10,
    "level": "ERROR",
    "formatter": "verbose",
}
LOGGING["root"]["handlers"] = ["console", "file"]  # noqa: F405
LOGGING["root"]["level"] = "INFO"  # noqa: F405
LOGGING["loggers"]["django"]["handlers"] = ["console", "file", "error_file"]  # noqa: F405
LOGGING["loggers"]["apps"]["handlers"] = ["console", "file", "error_file"]  # noqa: F405
LOGGING["loggers"]["apps"]["level"] = "INFO"  # noqa: F405

EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
