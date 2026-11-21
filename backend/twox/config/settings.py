"""Django settings for twox.

Every deployment-specific value comes from an environment variable with the
prefix ``TWOX_``. Importing this module never opens a database connection.
"""

import os
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy
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


def env_positive_int(name: str, default: int) -> int:
    """Return the variable ``name`` as a whole number greater than zero."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value < 1:
        raise ImproperlyConfigured(
            f"Environment variable {name} must be a whole number greater than zero."
        )
    return value


def env_absolute_path(name: str, default: str) -> Path:
    """Return the variable ``name`` as an absolute path."""
    value = Path(env_str(name, default))
    if not value.is_absolute():
        raise ImproperlyConfigured(f"Environment variable {name} must be an absolute path.")
    return value


BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env_str("TWOX_SECRET_KEY")
DEBUG = env_bool("TWOX_DEBUG", default=False)
ALLOWED_HOSTS = env_list("TWOX_ALLOWED_HOSTS")

INSTALLED_APPS = [
    # The Django admin with the project's own site (superusers only), see
    # twox/config/admin_site.py. Its app name stays django.contrib.admin.
    "twox.config.admin_site.TwoxAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    # Server-side sessions: the web UI signs in with a session cookie at the
    # same origin, no token in the browser (E-38).
    "django.contrib.sessions",
    "django.contrib.messages",
    # collectstatic gathers the built web UI and the admin's files at image
    # build time.
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

# Order as in the Django documentation (middleware ordering).
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves STATIC_ROOT below STATIC_URL; everything else passes through.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "twox.config.urls"
ASGI_APPLICATION = "twox.config.asgi.application"

# Needed by the admin (and later by allauth); the web UI itself is no template.
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

# Django's four standard validators; at least 12 characters, as there is no
# second factor in milestone M1 (E-38).
AUTH_PASSWORD_VALIDATORS: list[dict[str, Any]] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Sessions live in the database and last 8 hours, about one work shift (E-38).
SESSION_COOKIE_AGE = 8 * 60 * 60
# Both values are Django's defaults; set here so that a change is visible.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# Secure cookies, CSRF_TRUSTED_ORIGINS, HSTS and CSP follow in milestone M6.

# Shared by all API processes: it holds, for example, the login rate limit
# (work order 020). Valkey speaks the Redis protocol, hence redis://.
# Importing this module opens no connection.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env_str("TWOX_CACHE_URL", "redis://valkey:6379/2"),
    }
}

REST_FRAMEWORK = {
    # Closed by default: a view is public only if it says so itself.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # The web UI uses the Django session at the same origin; DRF then checks
    # the CSRF token on every write of a signed-in user (E-38). No HTTP basic,
    # no tokens in the browser.
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
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
# into STATIC_ROOT. WhiteNoise serves STATIC_ROOT; the UI view returns its
# index.html for / and every page path of the UI (see twox/config/urls.py).
# There is no Node server at runtime.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WEB_DIST_DIR = Path(env_str("TWOX_WEB_DIST_DIR", str(BASE_DIR.parent / "web" / "dist")))
# Only if a build exists: backend-dev and the tests run without one.
STATICFILES_DIRS = [WEB_DIST_DIR] if WEB_DIST_DIR.is_dir() else []
# The web UI build plus the files of the admin, including the licence files of
# the libraries it ships (jQuery, Select2, XRegExp). No other app folder is
# searched: the assets of the DRF browsable API (switched off, JSON only)
# would otherwise be shipped too.
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "twox.config.staticfinders.AdminAppDirectoriesFinder",
]
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
# German and English; LocaleMiddleware picks one per request. The catalogs
# follow in work order 034.
LANGUAGES = [
    ("de", gettext_lazy("German")),
    ("en", gettext_lazy("English")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Uploaded files. There is no MEDIA_URL on purpose: files leave the server
# through the API only, never as a plain URL.
TWOX_MEDIA_ROOT = env_absolute_path("TWOX_MEDIA_ROOT", "/data/media")
# Upper limit for one upload in bytes; 200 MB (decimal, 200,000,000 bytes) by
# default (E-42).
TWOX_UPLOAD_MAX_BYTES = env_positive_int("TWOX_UPLOAD_MAX_BYTES", 200 * 1000 * 1000)

# Defined here, used by later milestones.
TWOX_LLM_BASE_URL = env_str("TWOX_LLM_BASE_URL", "http://host.docker.internal:11434/v1")
TWOX_DOCLING_URL = env_str("TWOX_DOCLING_URL", "http://docling:5001")
