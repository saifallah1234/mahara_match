import os
from urllib.parse import parse_qsl, unquote, urlsplit

from backend.config.settings.base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
if database_url:
    try:
        parsed_database_url = urlsplit(database_url)
        database_port = parsed_database_url.port
    except ValueError as exc:
        raise ValueError(
            "TEST_DATABASE_URL or DATABASE_URL must be a valid PostgreSQL URL."
        ) from exc

    database_name = unquote(parsed_database_url.path.lstrip("/"))
    if (
        parsed_database_url.scheme not in {"postgres", "postgresql"}
        or not parsed_database_url.hostname
        or not database_name
    ):
        raise ValueError("TEST_DATABASE_URL or DATABASE_URL must be a valid PostgreSQL URL.")

    DATABASES["default"] = {  # noqa: F405
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_name,
        "USER": unquote(parsed_database_url.username or ""),
        "PASSWORD": unquote(parsed_database_url.password or ""),
        "HOST": parsed_database_url.hostname,
        "PORT": str(database_port or 5432),
        "CONN_MAX_AGE": 0,
        "OPTIONS": dict(parse_qsl(parsed_database_url.query)),
    }
