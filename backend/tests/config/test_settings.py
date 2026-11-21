"""The settings load from TWOX_* variables and never need a running database."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.settings import api_settings

from twox.accounts.permissions import CanRead

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

EXPECTED_APPS = (
    "twox.assets",
    "twox.files",
    "twox.ingest",
    "twox.search",
    "twox.answers",
    "twox.profiles",
    "twox.accounts",
    "twox.importers",
)

DUMP_SETTINGS = """
import json
import django
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

django.setup()
print(json.dumps({
    "debug": settings.DEBUG,
    "allowed_hosts": settings.ALLOWED_HOSTS,
    "db": settings.DATABASES["default"],
    "llm": settings.TWOX_LLM_BASE_URL,
    "docling": settings.TWOX_DOCLING_URL,
    "cache": settings.CACHES["default"],
    "media_root": str(settings.TWOX_MEDIA_ROOT),
    "media_root_type": type(settings.TWOX_MEDIA_ROOT).__name__,
    "upload_max_bytes": settings.TWOX_UPLOAD_MAX_BYTES,
    "media_url_set": settings.is_overridden("MEDIA_URL"),
}))
"""


def run_python(
    code: str, overrides: dict[str, str | None], args: list[str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``code`` with ``args`` in a fresh interpreter.

    A ``None`` override removes the variable.
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith("TWOX_")}
    base: dict[str, str | None] = {
        "TWOX_SECRET_KEY": "test-only",
        "TWOX_DB_PASSWORD": "test-only",
        # A host that cannot resolve: any connection attempt would fail.
        "TWOX_DB_HOST": "db.invalid",
    }
    for key, value in (base | overrides).items():
        if value is not None:
            env[key] = value
    env["DJANGO_SETTINGS_MODULE"] = "twox.config.settings"
    return subprocess.run(
        [sys.executable, "-c", code, *(args or [])],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_settings_import_without_running_database() -> None:
    result = run_python(DUMP_SETTINGS, {})

    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["db"]["ENGINE"] == "django.db.backends.postgresql"
    assert values["db"]["HOST"] == "db.invalid"
    assert values["db"]["PORT"] == "5432"
    assert values["db"]["NAME"] == "twox"
    assert values["db"]["USER"] == "twox"
    assert values["debug"] is False
    assert values["allowed_hosts"] == []
    assert values["llm"] == "http://host.docker.internal:11434/v1"
    assert values["docling"] == "http://docling:5001"
    assert values["cache"] == {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://valkey:6379/2",
    }
    assert values["media_root"] == "/data/media"
    assert values["media_root_type"] == "PosixPath"
    assert values["upload_max_bytes"] == 200_000_000
    # Files leave the server through the API only.
    assert values["media_url_set"] is False


def test_settings_read_twox_variables() -> None:
    result = run_python(
        DUMP_SETTINGS,
        {
            "TWOX_DEBUG": "true",
            "TWOX_ALLOWED_HOSTS": "localhost, example.test,",
            "TWOX_DB_PORT": "6543",
            "TWOX_DB_NAME": "other",
            "TWOX_DB_USER": "someone",
            "TWOX_LLM_BASE_URL": "http://llm.test/v1",
            "TWOX_DOCLING_URL": "http://docling.test",
            "TWOX_CACHE_URL": "redis://cache.test:6379/5",
            "TWOX_MEDIA_ROOT": "/srv/files",
            "TWOX_UPLOAD_MAX_BYTES": "1024",
        },
    )

    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["debug"] is True
    assert values["allowed_hosts"] == ["localhost", "example.test"]
    assert values["db"]["PORT"] == "6543"
    assert values["db"]["NAME"] == "other"
    assert values["db"]["USER"] == "someone"
    assert values["llm"] == "http://llm.test/v1"
    assert values["docling"] == "http://docling.test"
    assert values["cache"]["LOCATION"] == "redis://cache.test:6379/5"
    assert values["media_root"] == "/srv/files"
    assert values["upload_max_bytes"] == 1024


@pytest.mark.parametrize("name", ["TWOX_SECRET_KEY", "TWOX_DB_PASSWORD"])
def test_settings_require_secrets(name: str) -> None:
    result = run_python(DUMP_SETTINGS, {name: None})

    assert result.returncode != 0
    assert f"Environment variable {name} is required." in result.stderr


def test_settings_reject_invalid_boolean() -> None:
    result = run_python(DUMP_SETTINGS, {"TWOX_DEBUG": "maybe"})

    assert result.returncode != 0
    assert "TWOX_DEBUG must be true or false" in result.stderr


@pytest.mark.parametrize("app_name", EXPECTED_APPS)
def test_app_is_installed(app_name: str) -> None:
    assert apps.is_installed(app_name)


def test_exactly_the_eight_project_apps_are_installed() -> None:
    project_apps = sorted(
        config.name for config in apps.get_app_configs() if config.name.startswith("twox.")
    )

    assert project_apps == sorted(EXPECTED_APPS)


@pytest.mark.parametrize("value", ["0", "-5", "200MB", "1.5", "lots"])
def test_settings_reject_invalid_upload_limit(value: str) -> None:
    result = run_python(DUMP_SETTINGS, {"TWOX_UPLOAD_MAX_BYTES": value})

    assert result.returncode != 0
    assert "TWOX_UPLOAD_MAX_BYTES must be a whole number greater than zero" in result.stderr


@pytest.mark.parametrize("value", ["data/media", "./media"])
def test_settings_reject_relative_media_root(value: str) -> None:
    result = run_python(DUMP_SETTINGS, {"TWOX_MEDIA_ROOT": value})

    assert result.returncode != 0
    assert "TWOX_MEDIA_ROOT must be an absolute path" in result.stderr


@pytest.mark.parametrize(
    "app_name",
    [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "allauth",
        "allauth.account",
        "allauth.headless",
    ],
)
def test_django_app_is_installed(app_name: str) -> None:
    assert apps.is_installed(app_name)


@pytest.mark.parametrize(
    "app_name",
    [
        # OpenID Connect and two-factor sign-in follow after milestone M1.
        "allauth.socialaccount",
        "allauth.mfa",
        "allauth.usersessions",
        # Not needed by django-allauth 65.22.1.
        "django.contrib.sites",
    ],
)
def test_app_is_not_installed(app_name: str) -> None:
    assert not apps.is_installed(app_name)


def test_admin_uses_the_project_app_config() -> None:
    assert type(apps.get_app_config("admin")).__name__ == "TwoxAdminConfig"


def test_middleware_order_follows_the_django_documentation() -> None:
    assert settings.MIDDLEWARE == [
        "django.middleware.security.SecurityMiddleware",
        "whitenoise.middleware.WhiteNoiseMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.locale.LocaleMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "allauth.account.middleware.AccountMiddleware",
    ]


def test_templates_serve_the_admin() -> None:
    engines: list[dict[str, Any]] = settings.TEMPLATES
    (engine,) = engines

    assert engine["BACKEND"] == "django.template.backends.django.DjangoTemplates"
    assert engine["APP_DIRS"] is True
    assert engine["OPTIONS"]["context_processors"] == [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]


def test_languages_are_german_and_english() -> None:
    assert [code for code, _ in settings.LANGUAGES] == ["de", "en"]
    assert settings.LANGUAGE_CODE == "en"
    assert settings.LOCALE_PATHS == [BACKEND_ROOT / "locale"]
    assert settings.USE_I18N is True


def test_password_validators_are_the_four_standard_ones() -> None:
    validators: list[dict[str, Any]] = settings.AUTH_PASSWORD_VALIDATORS

    assert [validator["NAME"].rsplit(".", 1)[1] for validator in validators] == [
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    ]
    assert validators[1]["OPTIONS"] == {"min_length": 12}


def test_password_shorter_than_twelve_characters_is_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_password("k7#Qm2!xZp4")  # 11 characters
    validate_password("k7#Qm2!xZp4w")  # 12 characters


def test_session_lasts_eight_hours() -> None:
    assert settings.SESSION_COOKIE_AGE == 8 * 60 * 60
    assert settings.SESSION_EXPIRE_AT_BROWSER_CLOSE is False


def test_cookies_are_same_site_lax_and_session_cookie_http_only() -> None:
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"
    assert settings.SESSION_COOKIE_HTTPONLY is True


def test_default_permission_class_is_can_read() -> None:
    # A view without a permission class of its own needs a role (E-40).
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "twox.accounts.permissions.CanRead"
    ]
    assert [CanRead] == api_settings.DEFAULT_PERMISSION_CLASSES


def test_tests_run_with_the_local_memory_cache() -> None:
    # See tests/conftest.py: plain pytest needs no Valkey.
    assert settings.CACHES["default"]["BACKEND"] == (
        "django.core.cache.backends.locmem.LocMemCache"
    )
