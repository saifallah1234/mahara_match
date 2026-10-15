"""Explicitly isolated PostgreSQL settings for interview and regression checks."""

import os

from backend.config.settings.test import *  # noqa: F403

if not os.environ.get("INTERVIEW_TEST_DB_NAME", "").startswith("test_interview_"):
    raise ValueError("Set INTERVIEW_TEST_DB_NAME to an isolated test_interview_* database.")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["INTERVIEW_TEST_DB_NAME"],
        "USER": os.environ.get("INTERVIEW_TEST_DB_USER", "saif"),
        # Defaults: a native cluster's socket. Override for a Docker container over TCP.
        "HOST": os.environ.get("INTERVIEW_TEST_DB_HOST", "/tmp/mahara-interview-pg"),
        "PORT": os.environ.get("INTERVIEW_TEST_DB_PORT", "55439"),
        "TEST": {
            "NAME": os.environ["INTERVIEW_TEST_DB_NAME"],
            "CHARSET": "UTF8",
            "TEMPLATE": "template0",
        },
    }
}
