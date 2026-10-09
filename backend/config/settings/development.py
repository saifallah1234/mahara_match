from backend.config.settings.base import *  # noqa: F403

DEBUG = True
AUTH_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
