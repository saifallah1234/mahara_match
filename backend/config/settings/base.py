import os
from datetime import timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlsplit

BASE_DIR = Path(__file__).resolve().parents[3]

# Local development values; process environment always takes precedence.
env_file = BASE_DIR / ".env"
if env_file.is_file():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if value[:1] == value[-1:] and value.startswith(('"', "'")):
            value = value[1:-1]
        if value:
            os.environ.setdefault(key.strip(), value)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "backend.apps.identity.apps.IdentityConfig",
    "backend.apps.matching.apps.MatchingConfig",
    "backend.apps.recruitment.apps.RecruitmentConfig",
    "backend.apps.training.apps.TrainingConfig",
    "backend.apps.taxonomy.apps.TaxonomyConfig",
    "backend.apps.documents.apps.DocumentsConfig",
    "backend.apps.candidates.apps.CandidatesConfig",
    "backend.apps.assistant.apps.AssistantConfig",
    "backend.apps.imports.apps.ImportsConfig",
    "backend.apps.platform.apps.PlatformConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.config.urls"
WSGI_APPLICATION = "backend.config.wsgi.application"
ASGI_APPLICATION = "backend.config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

pooler_url = os.getenv("POSTGRES_SESSION_POOLER")
pooler = urlsplit(pooler_url) if pooler_url else None
if pooler and (pooler.scheme not in {"postgres", "postgresql"} or not pooler.hostname):
    raise ValueError("POSTGRES_SESSION_POOLER must be a PostgreSQL connection URL.")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": pooler.path.lstrip("/") if pooler else os.getenv("POSTGRES_DB", "mahara_match"),
        "USER": unquote(pooler.username or "")
        if pooler
        else os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": unquote(pooler.password or "")
        if pooler
        else os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": pooler.hostname if pooler else os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": str(pooler.port or 5432) if pooler else os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"sslmode": "require"} if pooler else {},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "identity.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "backend.apps.identity.api.common_permissions.IsActiveAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "backend.common.api.pagination.StandardPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "backend.common.api.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": (
        "backend.apps.identity.api.authentication_serializers.EmailTokenObtainPairSerializer"
    ),
    "TOKEN_REFRESH_SERIALIZER": (
        "backend.apps.identity.api.authentication_serializers.ActiveTokenRefreshSerializer"
    ),
    "TOKEN_VERIFY_SERIALIZER": (
        "backend.apps.identity.api.authentication_serializers.ActiveTokenVerifySerializer"
    ),
}

AUTH_REFRESH_COOKIE_NAME = "mahara_refresh"
AUTH_REFRESH_COOKIE_PATH = "/api/v1/auth/"
AUTH_COOKIE_SECURE = not DEBUG
AUTH_COOKIE_SAMESITE: Literal["Lax"] = "Lax"
CSRF_COOKIE_SECURE = AUTH_COOKIE_SECURE
CSRF_COOKIE_SAMESITE = AUTH_COOKIE_SAMESITE

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT") or os.getenv("OBJECT_STORAGE_ENDPOINT", "")
MINIO_BUCKET = os.getenv("MINIO_BUCKET") or os.getenv("OBJECT_STORAGE_BUCKET", "")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY") or os.getenv("OBJECT_STORAGE_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY") or os.getenv("OBJECT_STORAGE_SECRET_KEY", "")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
DOCUMENT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024

MOCK_INTERVIEW_ENABLED = os.getenv("MOCK_INTERVIEW_ENABLED", "false").lower() == "true"
MOCK_INTERVIEW_BACKEND = os.getenv("MOCK_INTERVIEW_BACKEND", "disabled")
MOCK_INTERVIEW_LANGUAGES = ("fr",)
MOCK_INTERVIEW_ALLOW_LIVE_AWS = os.getenv("INTERVIEW_ALLOW_LIVE_AWS", "false").lower() == "true"
INTERVIEW_AWS_REGION = os.getenv("INTERVIEW_AWS_REGION", "")
INTERVIEW_PRIORITY_QUEUE_URL = os.getenv("INTERVIEW_PRIORITY_QUEUE_URL", "")
INTERVIEW_BACKGROUND_QUEUE_URL = os.getenv("INTERVIEW_BACKGROUND_QUEUE_URL", "")
INTERVIEW_STATUS_QUEUE_URL = os.getenv("INTERVIEW_STATUS_QUEUE_URL", "")
INTERVIEW_INFERENCE_REVISION = os.getenv("INTERVIEW_INFERENCE_REVISION", "")
MOCK_INTERVIEW_RECORDING_RETENTION_HOURS = int(
    os.getenv("INTERVIEW_RECORDING_RETENTION_HOURS", "24")
)
MOCK_INTERVIEW_MAX_RECORDING_BYTES = 25 * 1024 * 1024
MOCK_INTERVIEW_MAX_RECORDING_SECONDS = 180
MOCK_INTERVIEW_MAX_ATTEMPTS = int(os.getenv("INTERVIEW_MAX_ATTEMPTS", "3"))
if MOCK_INTERVIEW_RECORDING_RETENTION_HOURS <= 0 or not 1 <= MOCK_INTERVIEW_MAX_ATTEMPTS <= 3:
    raise ValueError("Interview retention must be positive and attempts must be between 1 and 3.")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "disabled")
STT_PROVIDER = os.getenv("STT_PROVIDER", "disabled")
INTERVIEW_VOICE = os.getenv("INTERVIEW_VOICE", "fr")
PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
INTERVIEW_PAID_TTS_ENABLED = os.getenv("INTERVIEW_PAID_TTS_ENABLED", "false").lower() == "true"
FASTER_WHISPER_MODEL_PATH = os.getenv("FASTER_WHISPER_MODEL_PATH", "")
INTERVIEW_FFMPEG = os.getenv("INTERVIEW_FFMPEG", "ffmpeg")
MOCK_INTERVIEW_AVATAR_DIR = BASE_DIR / "video"
MOCK_INTERVIEW_DERIVATIVE_DIR = BASE_DIR / "video" / "interview-derivatives"

SPECTACULAR_SETTINGS = {
    "TITLE": "Mahara Match API",
    "DESCRIPTION": "Controlled backend interfaces for Mahara Match.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "ApplicationStatusEnum": "backend.apps.recruitment.models.applications.ApplicationStatus.choices",
        "DeliveryModeEnum": "backend.apps.training.models.training_programs.DeliveryMode.choices",
        "EnrollmentStatusEnum": "backend.apps.training.models.training_enrollments.EnrollmentStatus.choices",
        "InterviewStatusEnum": "backend.apps.recruitment.models.interviews.InterviewStatus.choices",
        "InterviewTypeEnum": "backend.apps.recruitment.models.interviews.InterviewType.choices",
        "JobOfferStatusEnum": "backend.apps.recruitment.models.job_offers.JobOfferStatus.choices",
        "LanguageLevelEnum": "backend.apps.candidates.models.entities.LanguageLevel.choices",
        "OrganizationTypeEnum": "backend.apps.identity.models.organizations.OrganizationType.choices",
        "ProfileVisibilityEnum": "backend.apps.candidates.models.entities.ProfileVisibility.choices",
        "ProgramLevelEnum": "backend.apps.training.models.training_programs.ProgramLevel.choices",
        "ProgramStatusEnum": "backend.apps.training.models.training_programs.ProgramStatus.choices",
        "RelocationEnum": "backend.apps.candidates.models.entities.Relocation.choices",
        "SessionStatusEnum": "backend.apps.training.models.training_sessions.SessionStatus.choices",
        "SkillLevelEnum": "backend.apps.candidates.models.entities.SkillLevel.choices",
        "TrainingSkillPurposeEnum": "backend.apps.training.models.training_skills.TrainingSkillPurpose.choices",
        "UserStatusEnum": "backend.apps.identity.models.users.UserStatus.choices",
        "VerificationStatusEnum": "backend.apps.identity.models.organizations.VerificationStatus.choices",
        "WorkModeEnum": "backend.apps.candidates.models.entities.WorkMode.choices",
    },
}
