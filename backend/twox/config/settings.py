"""Django settings for twox.

Every deployment-specific value comes from an environment variable with the
prefix ``TWOX_``. Importing this module never opens a database connection.
"""

import math
import os
import re
from itertools import pairwise
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


def env_float(name: str, default: float, *, minimum: float, maximum: float) -> float:
    """Return the variable ``name`` as a number from ``minimum`` to ``maximum``."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not minimum <= value <= maximum:
        raise ImproperlyConfigured(
            f"Environment variable {name} must be a number from {minimum:g} to {maximum:g}."
        )
    return value


def env_positive_float(name: str, default: float, *, maximum: float) -> float:
    """Return the variable ``name`` as a number greater than zero and at most ``maximum``."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not 0 < value <= maximum:
        raise ImproperlyConfigured(
            f"Environment variable {name} must be a number greater than 0 and at most {maximum:g}."
        )
    return value


#: Values of TWOX_CHAT_REASONING_EFFORT that are sent as they are.
_CHAT_REASONING_EFFORTS = ("none", "low", "medium", "high")
#: The value of TWOX_CHAT_REASONING_EFFORT that leaves the field out.
_CHAT_REASONING_EFFORT_OMIT = "omit"


def env_reasoning_effort(name: str, default: str) -> str | None:
    """Return the variable ``name`` as a reasoning effort; ``None`` means "do not send".

    Unset and empty both mean ``default``: compose passes an empty string for a
    variable that is missing in .env.
    """
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw == _CHAT_REASONING_EFFORT_OMIT:
        return None
    if raw not in _CHAT_REASONING_EFFORTS:
        choices = ", ".join((*_CHAT_REASONING_EFFORTS, _CHAT_REASONING_EFFORT_OMIT))
        raise ImproperlyConfigured(f"Environment variable {name} must be one of: {choices}.")
    return raw


#: A request rate as Django REST framework reads it: a whole number, "/" and a
#: period whose first letter DRF uses (s, m, h or d).
_RATE_PATTERN = re.compile(r"(?P<number>[0-9]+)/(?P<period>s|sec|second|m|min|minute|h|hour|d|day)")


def env_rate(name: str, default: str) -> str:
    """Return the variable ``name`` as a DRF throttle rate such as ``10/min``."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    match = _RATE_PATTERN.fullmatch(raw)
    if match is None or int(match["number"]) < 1:
        raise ImproperlyConfigured(
            f"Environment variable {name} must be a rate such as 10/min "
            "(a whole number greater than zero, then /s, /min, /hour or /day)."
        )
    return raw


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
    # PostgreSQL-specific parts of Django: TrigramExtension, GinIndex, OpClass
    # and the full-text search building blocks (search, M2).
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    # Sign-in with local accounts through the headless API of django-allauth
    # (E-38). OpenID Connect (allauth.socialaccount) and two-factor sign-in
    # (allauth.mfa) follow after milestone M1.
    "allauth",
    "allauth.account",
    "allauth.headless",
    # Change log: who changed what and when (E-43). The models are registered
    # in twox/accounts/audit.py. Listed before the project apps, so that
    # twox/accounts/admin.py can replace the admin view of auditlog.
    "auditlog",
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
    # Attributes every change during a request to the signed-in user; needs
    # request.user, hence after the authentication middleware. auditlog's
    # middleware without values from request headers (twox/accounts/audit.py).
    "twox.accounts.audit.AuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Required by django-allauth; after the authentication middleware.
    "allauth.account.middleware.AccountMiddleware",
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

# Django's own backend (the admin form until work order 030) and the one of
# django-allauth.
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# django-allauth (E-38). The web UI builds its own sign-in page and talks to
# the headless API below /_allauth/browser/v1/ at the same origin: Django
# session cookie and CSRF token, no token in the browser. allauth renders no
# pages of its own.
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser",)
# No HEADLESS_FRONTEND_URLS: allauth needs them only for links in emails
# (verification, password reset, signup), and this installation sends none.
ACCOUNT_LOGIN_METHODS = {"username"}
# No self-registration and no email (see twox/accounts/adapter.py).
ACCOUNT_ADAPTER = "twox.accounts.adapter.AccountAdapter"
ACCOUNT_EMAIL_VERIFICATION = "none"
# No "unknown account" email after a password reset request either (with
# HEADLESS_ONLY it would also need a signup page of the web UI).
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False
# The defaults of allauth 65.22.1, set explicitly (E-38): failed sign-ins 10
# per minute per IP address and 5 per 5 minutes per account, sign-in attempts
# 30 per minute per IP address. allauth counts in the default cache, that is
# in Valkey, shared by all API processes.
ACCOUNT_RATE_LIMITS = {
    "login_failed": "10/m/ip,5/300s/key",
    "login": "30/m/ip",
}

# Change log (django-auditlog, E-43). No IP address in the log: the
# middleware stores none, also not from X-Forwarded-For.
AUDITLOG_DISABLE_REMOTE_ADDR = True
# No correlation id from the header X-Correlation-ID: a client value of more
# than 255 characters would make writing the entry fail after the change is
# saved. With None, auditlog never reads a header for it.
AUDITLOG_CID_HEADER = None
# Changes are stored as JSON values ([old, new] with null, true, false and
# numbers as such) instead of text, so that an empty value and the text
# "None" stay apart in the API.
AUDITLOG_STORE_JSON_CHANGES = True

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

# Most questions per user to POST /api/v1/answers/ (work order 130), counted
# per user in the cache above. One answer of a local model takes seconds to
# minutes and only one runs per user at a time; 10 per minute leaves room to
# ask again after a refusal or a cancel and stops scripts that would keep the
# model busy for everybody else.
TWOX_ANSWER_RATE = env_rate("TWOX_ANSWER_RATE", "10/min")

REST_FRAMEWORK = {
    # Closed by default: without a permission class of its own, a view needs
    # a role (E-40). Exceptions are listed in tests/config/test_api.py.
    "DEFAULT_PERMISSION_CLASSES": ["twox.accounts.permissions.CanRead"],
    # Rates of the views that name a throttle scope; there is no throttle
    # class for all views, so only those views are limited.
    "DEFAULT_THROTTLE_RATES": {"answers": TWOX_ANSWER_RATE},
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
    # A distinct name for the actions of the change log (generated: ActionEnum).
    "ENUM_NAME_OVERRIDES": {
        "AuditActionEnum": "twox.accounts.serializers.AUDIT_ACTION_CHOICES",
        # The states of an ingest job (another "status" than the health check's).
        "IngestStatusEnum": "twox.ingest.models.IngestStatus",
    },
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


def task_queues(*, ai_enabled: bool) -> tuple[Queue, ...]:
    """Return the Celery queues: one per kind of work, so that each can be scaled on its own.

    Each queue has its own exchange and routing key; a message for one queue
    never reaches another. The queue ``embed`` exists only with the AI
    features on (E-59): with them off, sending an embedding task fails at once
    instead of leaving a message that nobody consumes.
    """
    names = ("ingest", "embed", "default") if ai_enabled else ("ingest", "default")
    return tuple(Queue(name, Exchange(name, type="direct"), routing_key=name) for name in names)


# CELERY_TASK_QUEUES is set below TWOX_AI_ENABLED.
CELERY_TASK_DEFAULT_QUEUE = "default"
# A misspelled queue name is an error, not a new queue that nobody consumes.
CELERY_TASK_CREATE_MISSING_QUEUES = False
# Conversion and polling of the ingestion go to ingest, embedding to embed;
# every other task to default. The tasks themselves follow in 046 and 048.
CELERY_TASK_ROUTES = {
    "twox.ingest.convert": {"queue": "ingest"},
    "twox.ingest.poll": {"queue": "ingest"},
    "twox.ingest.embed": {"queue": "embed"},
}
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = "UTC"
# A worker process reserves one message at a time: a long task never holds
# further messages back that another process could already work on.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
# The Redis transport delivers a message again once it has not been
# acknowledged for this long (Celery's default, set explicitly). No task may
# run that long, and no countdown may reach it (see check_ingest_timing).
TWOX_BROKER_VISIBILITY_TIMEOUT_SECONDS = 60 * 60
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": TWOX_BROKER_VISIBILITY_TIMEOUT_SECONDS}
# Time limits of every task, ingestion included, far below the visibility
# timeout. A task that needs longer splits its work and schedules itself
# again. Soft: the task gets SoftTimeLimitExceeded and can clean up; hard: the
# worker process is replaced.
TWOX_TASK_SOFT_TIME_LIMIT = 300
TWOX_TASK_TIME_LIMIT = 360
CELERY_TASK_SOFT_TIME_LIMIT = TWOX_TASK_SOFT_TIME_LIMIT
CELERY_TASK_TIME_LIMIT = TWOX_TASK_TIME_LIMIT
# Soft shutdown: on a cold shutdown (SIGQUIT; compose maps SIGTERM to it with
# REMAP_SIGTERM) running tasks get this many seconds to finish; then they are
# cancelled. Tasks with acks_late (ingest, 046/048) go back to the queue at
# once instead of after the visibility timeout; other running tasks are lost.
# The stop_grace_period of the worker is longer.
CELERY_WORKER_SOFT_SHUTDOWN_TIMEOUT = 60.0

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
# German and English; LocaleMiddleware picks one per request. The German
# catalogue is backend/locale/de/LC_MESSAGES/django.po; the runtime image holds
# it compiled (.mo, built in the image only), the tests compile it on the fly
# (tests/conftest.py).
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

# Messages of the project's own code (for example failed sign-ins) go to the
# server log on stderr; Django's own logging stays as it is.
# uvicorn.access: the access log of uvicorn without query strings, so that no
# search text lands in it (052, E-57), and without the client address (069,
# E-62): the format leaves it out, and a filter replaces it in the record with
# "-" for any other formatter or handler. Method, path and status stay.
# Django configures logging after uvicorn did, and configuring a logger here
# replaces its handlers; the handler "uvicorn_access" is therefore uvicorn's own
# (same formatter class, standard output). Its level stays as uvicorn set it.
# uvicorn's --no-access-log no longer silences it; to switch the access log
# off, remove its handler here.
LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "drop_client_address": {"()": "twox.config.logging.DropClientAddress"},
        "drop_query_string": {"()": "twox.config.logging.DropQueryString"},
    },
    "formatters": {
        "uvicorn_access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "uvicorn_access": {
            "class": "logging.StreamHandler",
            "formatter": "uvicorn_access",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "twox": {"handlers": ["console"], "level": "INFO"},
        "uvicorn.access": {
            "handlers": ["uvicorn_access"],
            "filters": ["drop_client_address", "drop_query_string"],
            "propagate": False,
        },
    },
}

# OpenAI-compatible model service (Ollama on the host by default).
TWOX_LLM_BASE_URL = env_str("TWOX_LLM_BASE_URL", "http://host.docker.internal:11434/v1")
TWOX_DOCLING_URL = env_str("TWOX_DOCLING_URL", "http://docling:5001")

# AI features are optional and off by default (E-59): embeddings and vector
# search, later answers with a language model. Off means the model service is
# never contacted; everything else (ingestion, keyword search) works without it.
TWOX_AI_ENABLED = env_bool("TWOX_AI_ENABLED", default=False)
# Embedding model (E-56): bge-m3 with 1024 dimensions, matching the vector
# column of the sections. TWOX_EMBED_QUERY_PREFIX goes in front of search
# queries only (empty for bge-m3; qwen3-embedding needs an instruction there).
TWOX_EMBED_MODEL = env_str("TWOX_EMBED_MODEL", "bge-m3")
TWOX_EMBED_DIMENSIONS = env_positive_int("TWOX_EMBED_DIMENSIONS", 1024)
TWOX_EMBED_BATCH_SIZE = env_positive_int("TWOX_EMBED_BATCH_SIZE", 16)
TWOX_EMBED_QUERY_PREFIX = os.environ.get("TWOX_EMBED_QUERY_PREFIX", "")
# Socket time limit of one request in seconds; the first request after a
# start of Ollama also loads the model.
TWOX_EMBED_TIMEOUT_SECONDS = env_positive_int("TWOX_EMBED_TIMEOUT_SECONDS", 120)
# The same for embedding a search query (052): short, so a hanging model
# service holds a search up only briefly before it falls back to keywords.
TWOX_SEARCH_EMBED_TIMEOUT_SECONDS = env_positive_int("TWOX_SEARCH_EMBED_TIMEOUT_SECONDS", 20)
# Chat model for answers (M3, twox/answers/chat.py). No default: recommended is
# gemma4:31b-it-qat, fallback qwen3.8:27b-q4_K_M (E-70); it is loaded with
# ollama pull and set in the own .env. Empty means answers are unavailable.
# Read without env_str, whose fallback would require a value.
TWOX_CHAT_MODEL = os.environ.get("TWOX_CHAT_MODEL", "").strip()
# Socket time limit in seconds: the longest wait between two pieces of an
# answer, the first one included (it may have to wait for the model to load).
TWOX_CHAT_TIMEOUT_SECONDS = env_positive_int("TWOX_CHAT_TIMEOUT_SECONDS", 120)
# Most tokens the model may generate for one answer.
TWOX_CHAT_MAX_TOKENS = env_positive_int("TWOX_CHAT_MAX_TOKENS", 1024)
TWOX_CHAT_TEMPERATURE = env_float("TWOX_CHAT_TEMPERATURE", 0.0, minimum=0.0, maximum=2.0)
# reasoning_effort sent with every request: none, low, medium or high; "omit"
# leaves the field out (None). Unset or empty means none.
TWOX_CHAT_REASONING_EFFORT = env_reasoning_effort("TWOX_CHAT_REASONING_EFFORT", "none")

# Context of an answer (M3, twox/answers/context.py). Starting values decided
# in E-70 after the measurement run of work order 128.
# Most main sources (k); neighbouring sections do not count against it.
TWOX_ANSWER_MAX_SOURCES = env_positive_int("TWOX_ANSWER_MAX_SOURCES", 8)
# Characters of all source texts together: k sections of at most
# TWOX_SECTION_MAX_CHARS characters (8 x 2,000).
TWOX_ANSWER_CONTEXT_CHARS = env_positive_int("TWOX_ANSWER_CONTEXT_CHARS", 16000)
# Load the sections right before and after each main source as well.
TWOX_ANSWER_NEIGHBOURS = env_bool("TWOX_ANSWER_NEIGHBOURS", default=False)
# Relevance threshold, a cosine distance (0 < x <= 2): without a hit at most
# this far from the question (or an exact hit) the model is not asked. It is
# also a filter (E-70): only hits at most this far (or exact hits) become
# sources; hits further away are left out of the context.
TWOX_ANSWER_MAX_DISTANCE = env_positive_float("TWOX_ANSWER_MAX_DISTANCE", 0.55, maximum=2.0)
# Largest cosine distance of the stored embeddings of two sections from
# different documents of the same device that count as the same place in
# another language (E-61); less than TWOX_ANSWER_MAX_DISTANCE.
TWOX_ANSWER_TRANSLATION_DISTANCE = env_positive_float(
    "TWOX_ANSWER_TRANSLATION_DISTANCE", 0.15, maximum=2.0
)
# Longest time in seconds for one answer over the API, from the question to
# the last event (work order 130); beyond it the answer ends with the error
# code timeout and the connection to the model is closed.
TWOX_ANSWER_TOTAL_TIMEOUT = env_positive_int("TWOX_ANSWER_TOTAL_TIMEOUT", 180)


def check_answer_settings(*, max_distance: float, translation_distance: float) -> None:
    """Raise ImproperlyConfigured unless the distances of the answer context fit together."""
    if translation_distance >= max_distance:
        raise ImproperlyConfigured(
            f"TWOX_ANSWER_TRANSLATION_DISTANCE ({translation_distance:g}) must be less than "
            f"TWOX_ANSWER_MAX_DISTANCE ({max_distance:g})."
        )


check_answer_settings(
    max_distance=TWOX_ANSWER_MAX_DISTANCE,
    translation_distance=TWOX_ANSWER_TRANSLATION_DISTANCE,
)

CELERY_TASK_QUEUES = task_queues(ai_enabled=TWOX_AI_ENABLED)

# Ingestion (M2). All times in seconds.
# Attempts of one ingestion step after a temporary error (Docling or the
# model service not reachable) before the job fails.
TWOX_INGEST_MAX_RETRIES = env_positive_int("TWOX_INGEST_MAX_RETRIES", 5)
# Wait between two status queries at Docling: starts at the minimum and grows
# up to the maximum. The poll task schedules itself again, it never sleeps.
TWOX_INGEST_POLL_MIN_SECONDS = env_positive_int("TWOX_INGEST_POLL_MIN_SECONDS", 10)
TWOX_INGEST_POLL_MAX_SECONDS = env_positive_int("TWOX_INGEST_POLL_MAX_SECONDS", 60)
# Upper limit of the Docling service per document (E-55): the value of
# DOCLING_SERVE_MAX_DOCUMENT_TIMEOUT in compose.yaml and of
# DEFAULT_DOCUMENT_TIMEOUT_SECONDS in twox/ingest/docling.py. Raising it
# means changing all three.
TWOX_DOCLING_MAX_DOCUMENT_TIMEOUT_SECONDS = 2 * 60 * 60
# Sent with every conversion as document_timeout: Docling stops converting
# one document after this time. At most the limit above.
TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS = env_positive_int(
    "TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS", TWOX_DOCLING_MAX_DOCUMENT_TIMEOUT_SECONDS
)
# Deadline of one conversion in the backend. It counts from the status
# "started" at Docling, not while the document waits in Docling's queue (for
# that, see the next value), and is longer than document_timeout, so that
# Docling's own error arrives first.
TWOX_INGEST_TIMEOUT_SECONDS = env_positive_int("TWOX_INGEST_TIMEOUT_SECONDS", 9000)
# Deadline of a job whose Docling task never starts (stays pending), counted
# from the start of the job (work order 065). Long, so that a large batch
# waiting in Docling's queue one document after another is not cut off; at
# least the deadline above.
TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS = env_positive_int(
    "TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS", 24 * 60 * 60
)
# Largest section in characters (twox/ingest/sections.py).
TWOX_SECTION_MAX_CHARS = env_positive_int("TWOX_SECTION_MAX_CHARS", 2000)
# One embedding task embeds for at most this long, then schedules itself
# again for the rest; below the soft time limit of a task.
TWOX_EMBED_TASK_MAX_SECONDS = env_positive_int("TWOX_EMBED_TASK_MAX_SECONDS", 240)


def check_ingest_timing(
    *,
    max_retries: int,
    poll_min_seconds: int,
    poll_max_seconds: int,
    docling_document_timeout_seconds: int,
    docling_max_document_timeout_seconds: int,
    ingest_timeout_seconds: int,
    docling_queue_timeout_seconds: int,
    section_max_chars: int,
    embed_task_max_seconds: int,
    task_soft_time_limit: int,
    task_time_limit: int,
    visibility_timeout_seconds: int,
) -> None:
    """Raise ImproperlyConfigured unless the ingestion and Celery values fit together.

    Runs when the settings load, so that a wrong value stops the API, the
    worker and every management command at start with a clear message.
    """
    values = {
        "TWOX_INGEST_MAX_RETRIES": max_retries,
        "TWOX_INGEST_POLL_MIN_SECONDS": poll_min_seconds,
        "TWOX_INGEST_POLL_MAX_SECONDS": poll_max_seconds,
        "TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS": docling_document_timeout_seconds,
        "TWOX_INGEST_TIMEOUT_SECONDS": ingest_timeout_seconds,
        "TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS": docling_queue_timeout_seconds,
        "TWOX_SECTION_MAX_CHARS": section_max_chars,
        "TWOX_EMBED_TASK_MAX_SECONDS": embed_task_max_seconds,
        "TWOX_TASK_SOFT_TIME_LIMIT": task_soft_time_limit,
        "TWOX_TASK_TIME_LIMIT": task_time_limit,
        "visibility_timeout": visibility_timeout_seconds,
    }
    for name, value in values.items():
        # bool is a subclass of int, but True is no number of seconds.
        if type(value) is not int or value < 1:
            raise ImproperlyConfigured(
                f"{name} must be a whole number greater than zero, not {value!r}."
            )
    if docling_document_timeout_seconds > docling_max_document_timeout_seconds:
        raise ImproperlyConfigured(
            f"TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS ({docling_document_timeout_seconds}) "
            "must not exceed the limit of the Docling service "
            f"({docling_max_document_timeout_seconds} seconds)."
        )
    if ingest_timeout_seconds <= docling_document_timeout_seconds:
        raise ImproperlyConfigured(
            f"TWOX_INGEST_TIMEOUT_SECONDS ({ingest_timeout_seconds}) must be greater than "
            f"TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS ({docling_document_timeout_seconds}), "
            "the document_timeout sent to Docling; otherwise the backend gives up on a "
            "conversion that Docling is still allowed to finish."
        )
    if docling_queue_timeout_seconds < ingest_timeout_seconds:
        raise ImproperlyConfigured(
            f"TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS ({docling_queue_timeout_seconds}) must not be "
            f"less than TWOX_INGEST_TIMEOUT_SECONDS ({ingest_timeout_seconds}); a job waiting "
            "in Docling's queue would get less time than a conversion that has started."
        )
    if poll_min_seconds > poll_max_seconds:
        raise ImproperlyConfigured(
            f"TWOX_INGEST_POLL_MIN_SECONDS ({poll_min_seconds}) must not be greater than "
            f"TWOX_INGEST_POLL_MAX_SECONDS ({poll_max_seconds})."
        )
    if poll_max_seconds >= visibility_timeout_seconds:
        raise ImproperlyConfigured(
            f"TWOX_INGEST_POLL_MAX_SECONDS ({poll_max_seconds}) must be less than the "
            f"visibility_timeout of the broker ({visibility_timeout_seconds}); a task "
            "scheduled further ahead would be delivered twice."
        )
    chain = [
        ("TWOX_EMBED_TASK_MAX_SECONDS", embed_task_max_seconds),
        ("TWOX_TASK_SOFT_TIME_LIMIT", task_soft_time_limit),
        ("TWOX_TASK_TIME_LIMIT", task_time_limit),
        ("visibility_timeout of the broker", visibility_timeout_seconds),
    ]
    for (lower_name, lower), (upper_name, upper) in pairwise(chain):
        if lower >= upper:
            raise ImproperlyConfigured(
                f"{lower_name} ({lower}) must be less than {upper_name} ({upper})."
            )


check_ingest_timing(
    max_retries=TWOX_INGEST_MAX_RETRIES,
    poll_min_seconds=TWOX_INGEST_POLL_MIN_SECONDS,
    poll_max_seconds=TWOX_INGEST_POLL_MAX_SECONDS,
    docling_document_timeout_seconds=TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS,
    docling_max_document_timeout_seconds=TWOX_DOCLING_MAX_DOCUMENT_TIMEOUT_SECONDS,
    ingest_timeout_seconds=TWOX_INGEST_TIMEOUT_SECONDS,
    docling_queue_timeout_seconds=TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS,
    section_max_chars=TWOX_SECTION_MAX_CHARS,
    embed_task_max_seconds=TWOX_EMBED_TASK_MAX_SECONDS,
    task_soft_time_limit=TWOX_TASK_SOFT_TIME_LIMIT,
    task_time_limit=TWOX_TASK_TIME_LIMIT,
    visibility_timeout_seconds=TWOX_BROKER_VISIBILITY_TIMEOUT_SECONDS,
)
