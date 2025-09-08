import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv

# Load environment variables from .env if present
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # points to security-scanner/backend
PROJECT_DIR = Path(__file__).resolve().parent.parent      # points to backend/src
ENV_PATH = BASE_DIR.parent / ".env"                       # security-scanner/.env
load_dotenv(dotenv_path=ENV_PATH)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes", "on")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()] or ["*"]

# Applications
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",

    # Local apps
    "health",
    "core",
    "accounts",
    "projects",
    "targets",
    "scans",
    "findings",
    "evidence",
    "reports",
    "schedules",
    "notifications",
    "integrations",
    "compliance",
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

ROOT_URLCONF = "api_server.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "api_server.wsgi.application"
ASGI_APPLICATION = "api_server.asgi.application"

# Database
# Database
# Prefer PostgreSQL when POSTGRES_HOST is provided; otherwise fall back to SQLite for local dev.
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
if POSTGRES_HOST:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "security_scanner"),
            "USER": os.getenv("POSTGRES_USER", "scanner"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "scannerpass"),
            "HOST": POSTGRES_HOST,
            "PORT": int(os.getenv("POSTGRES_PORT", "5432")),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": PROJECT_DIR / "db.sqlite3",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = str(PROJECT_DIR / "staticfiles")

# Media (for storage fallback)
MEDIA_ROOT = str(PROJECT_DIR / "media")
MEDIA_URL = "/media/"

# Reports storage directory and WeasyPrint flag
REPORTS_STORAGE_DIR = str(BASE_DIR / "var" / "reports")
os.makedirs(REPORTS_STORAGE_DIR, exist_ok=True)

# WeasyPrint availability flag
try:
    import weasyprint  # noqa: F401
    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# DRF
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

# SimpleJWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# drf-spectacular
SPECTACULAR_SETTINGS = {
    "TITLE": "Security Scanner API",
    "DESCRIPTION": "API documentation",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # OpenAPI components security scheme for JWT Bearer
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [{"bearerAuth": []}],
    "COMPONENTS": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    # Optional: tag ordering
    "TAGS": [
        {"name": "Notifications"},
        {"name": "Integrations"},
        {"name": "Reports"},
        {"name": "Schedules"},
    ],
}

# Celery - Use memory broker for testing when Redis is not available
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL + "/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL + "/1")
else:
    # Fallback to memory broker for testing
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Celery Beat schedule for DB-driven scheduler
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "enqueue_due_scans": {
        "task": "schedules.tasks.enqueue_due_scans",
        "schedule": crontab(minute="*"),
        "options": {"queue": "scans.control", "routing_key": "scans.control"},
    },
}

# Scanner/Celery routing and defaults
SCANNER_DEFAULTS = {
    "USER_AGENT": "SecurityScanner/0.1 (+https://scanner.local)",
    "HTTP_TIMEOUT_SECS": 5,
    "RETRY_BACKOFF_MIN": 5,
    "STATIC": {"SOFT_TIME_LIMIT": 8 * 60, "HARD_TIME_LIMIT": 10 * 60},
    "DYNAMIC": {"SOFT_TIME_LIMIT": 25 * 60, "HARD_TIME_LIMIT": 30 * 60},
    "CONTROL": {"HARD_TIME_LIMIT": 2 * 60},
    # Dynamic crawler defaults (new)
    "dynamic_max_pages": 10,
    "rate_limit_rps": 2,
    "user_agent": "SecurityScannerBot/1.0",
}

# Notifications defaults
NOTIFICATIONS_DEFAULTS = {
    "threshold_severity": os.getenv("NOTIFY_THRESHOLD_SEVERITY", "high").lower(),
    "email_from": os.getenv("EMAIL_FROM", os.getenv("DEFAULT_FROM_EMAIL", "no-reply@scanner.local")),
}

from kombu import Exchange, Queue  # noqa: E402

CELERY_TASK_QUEUES = (
    Queue("scans.control", Exchange("scans"), routing_key="scans.control"),
    Queue("scans.static", Exchange("scans"), routing_key="scans.static"),
    Queue("scans.dynamic", Exchange("scans"), routing_key="scans.dynamic"),
    Queue("reports.export", Exchange("reports"), routing_key="reports.export"),
    # Notifications routing
    Queue("notifications.send", Exchange("notifications"), routing_key="notifications.send"),
)

CELERY_TASK_DEFAULT_QUEUE = "scans.control"
CELERY_TASK_DEFAULT_EXCHANGE = "scans"
CELERY_TASK_DEFAULT_ROUTING_KEY = "scans.control"

CELERY_TASK_ROUTES = {
    "scans.start_scan": {"queue": "scans.control", "routing_key": "scans.control"},
    "scans.run_static_scan": {"queue": "scans.static", "routing_key": "scans.static"},
    "scans.run_dynamic_scan": {"queue": "scans.dynamic", "routing_key": "scans.dynamic"},
    "scans.aggregate_results": {"queue": "scans.control", "routing_key": "scans.control"},
    # Reports export routing
    "reports.tasks.generate_report": {"queue": "reports.export", "routing_key": "reports.export"},
    # Notifications routing
    "notifications.tasks.dispatch_event": {"queue": "notifications.send", "routing_key": "notifications.send"},
}

# ZAP (for later use)
ZAP_HOST = os.getenv("ZAP_HOST", "zap")
ZAP_PORT = int(os.getenv("ZAP_PORT", "8090"))
ZAP_API_KEY = os.getenv("ZAP_API_KEY", "changeme")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"