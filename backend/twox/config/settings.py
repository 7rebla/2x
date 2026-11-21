"""Django settings for twox.

Every deployment-specific value comes from an environment variable with the
prefix ``TWOX_``. Importing this module never opens a database connection.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

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

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Defined here, used by later milestones.
TWOX_LLM_BASE_URL = env_str("TWOX_LLM_BASE_URL", "http://host.docker.internal:11434/v1")
TWOX_DOCLING_URL = env_str("TWOX_DOCLING_URL", "http://docling:5001")
