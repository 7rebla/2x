"""Django settings for twox.

Every deployment-specific value comes from an environment variable with the
prefix ``TWOX_``. Importing this module never opens a database connection.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from kombu import Exchange, Queue

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def env_str(name: str, default: str | None = None) -> str:
    """Return the variable ``name``; unset and empty both fall back to ``default``."""
    value = os.environ.get(name) or default
    if value is None:
        raise ImproperlyConfigured(f"Environment variable {name} is required.")
    return value


def env_bool(name: str, default: bool) -> bool:
    """Return the variable ``name`` as a boolean."""
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    raise ImproperlyConfigured(f"Environment variable {name} must be true or false.")


def env_list(name: str) -> list[str]:
    """Return the comma-separated variable ``name`` as a list without empty items."""
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env_str("TWOX_SECRET_KEY")
DEBUG = env_bool("TWOX_DEBUG", default=False)
ALLOWED_HOSTS = env_list("TWOX_ALLOWED_HOSTS")

INSTALLED_APPS = [
    # auth and contenttypes are what the custom user model needs. Sessions,
    # admin and the login itself arrive with milestone M1.
    "django.contrib.auth",
    "django.contrib.contenttypes",
    # collectstatic gathers the built web UI at image build time.
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "twox.assets",
    "twox.files",
    "twox.ingest",
    "twox.search",
    "twox.answers",
    "twox.profiles",
    "twox.accounts",
    "twox.importers",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves STATIC_ROOT below STATIC_URL; everything else passes through.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "twox.config.urls"
ASGI_APPLICATION = "twox.config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env_str("TWOX_DB_HOST", "db"),
        "PORT": env_str("TWOX_DB_PORT", "5432"),
        "NAME": env_str("TWOX_DB_NAME", "twox"),
        "USER": env_str("TWOX_DB_USER", "twox"),
        "PASSWORD": env_str("TWOX_DB_PASSWORD"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Set before the first migration; changing it later is costly.
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    # Closed by default: a view is public only if it says so itself.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # No way to log in yet. Authentication is decided in milestone M1; until
    # then DRF's defaults (session and HTTP basic) stay switched off.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "2x API",
    "DESCRIPTION": "Asset records with sourced answers.",
    "VERSION": "0.0.0",
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

# Celery. Valkey speaks the Redis protocol; Celery has no valkey:// scheme, so
# the addresses use redis://. Importing this module opens no connection.
CELERY_BROKER_URL = env_str("TWOX_CELERY_BROKER_URL", "redis://valkey:6379/0")
CELERY_RESULT_BACKEND = env_str("TWOX_CELERY_RESULT_BACKEND", "redis://valkey:6379/1")
# JSON only: nothing that arrives through the broker is ever unpickled.
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_ACCEPT_CONTENT = ["json"]
# One queue per kind of work, so that each can be scaled on its own.
# Each queue has its own exchange and routing key; a message for one queue
# never reaches another.
CELERY_TASK_QUEUES = tuple(
    Queue(name, Exchange(name, type="direct"), routing_key=name)
    for name in ("ingest", "embed", "default")
)
CELERY_TASK_DEFAULT_QUEUE = "default"
# A misspelled queue name is an error, not a new queue that nobody consumes.
CELERY_TASK_CREATE_MISSING_QUEUES = False
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = "UTC"

# Web UI. Vite builds it with base "/static/" (web/vite.config.ts); the image
# build runs collectstatic, which copies the build output from WEB_DIST_DIR
# into STATIC_ROOT. WhiteNoise serves STATIC_ROOT, the view at / returns its
# index.html. There is no Node server at runtime.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WEB_DIST_DIR = Path(env_str("TWOX_WEB_DIST_DIR", str(BASE_DIR.parent / "web" / "dist")))
# Only if a build exists: backend-dev and the tests run without one.
STATICFILES_DIRS = [WEB_DIST_DIR] if WEB_DIST_DIR.is_dir() else []
# Only the web UI build. The app folders are not searched: the assets of the
# DRF browsable API (switched off, JSON only) would otherwise be shipped too.
# The admin arrives with milestone M1 and has to be added here then.
STATICFILES_FINDERS = ["django.contrib.staticfiles.finders.FileSystemFinder"]
# Plain storage: Vite already puts a content hash into every asset name, and
# no compressed copies are made (nothing between server and browser should
# compress or buffer, see the answer stream in milestone M3).
STORAGES = {
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Never look into STATICFILES_DIRS at request time, also not with DEBUG on:
# only what collectstatic put into STATIC_ROOT is served.
WHITENOISE_USE_FINDERS = False
WHITENOISE_AUTOREFRESH = False


def web_asset_is_immutable(path: str, url: str) -> bool:
    """Files below /static/assets/ carry a content hash from Vite and never change."""
    return url.startswith(STATIC_URL + "assets/")


WHITENOISE_IMMUTABLE_FILE_TEST = web_asset_is_immutable

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Defined here, used by later milestones.
TWOX_LLM_BASE_URL = env_str("TWOX_LLM_BASE_URL", "http://host.docker.internal:11434/v1")
TWOX_DOCLING_URL = env_str("TWOX_DOCLING_URL", "http://docling:5001")
