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
from django.core.exceptions import ImproperlyConfigured, ValidationError
from rest_framework.settings import api_settings

from twox.accounts.permissions import CanRead
from twox.config import settings as settings_module

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
    "ai_enabled": settings.TWOX_AI_ENABLED,
    "embed_model": settings.TWOX_EMBED_MODEL,
    "embed_dimensions": settings.TWOX_EMBED_DIMENSIONS,
    "embed_batch_size": settings.TWOX_EMBED_BATCH_SIZE,
    "embed_query_prefix": settings.TWOX_EMBED_QUERY_PREFIX,
    "embed_timeout_seconds": settings.TWOX_EMBED_TIMEOUT_SECONDS,
    "search_embed_timeout_seconds": settings.TWOX_SEARCH_EMBED_TIMEOUT_SECONDS,
    "ingest_max_retries": settings.TWOX_INGEST_MAX_RETRIES,
    "ingest_poll_min_seconds": settings.TWOX_INGEST_POLL_MIN_SECONDS,
    "ingest_poll_max_seconds": settings.TWOX_INGEST_POLL_MAX_SECONDS,
    "docling_document_timeout_seconds": settings.TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS,
    "ingest_timeout_seconds": settings.TWOX_INGEST_TIMEOUT_SECONDS,
    "docling_queue_timeout_seconds": settings.TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS,
    "section_max_chars": settings.TWOX_SECTION_MAX_CHARS,
    "embed_task_max_seconds": settings.TWOX_EMBED_TASK_MAX_SECONDS,
}))
"""

INGEST_VARIABLES = (
    "TWOX_INGEST_MAX_RETRIES",
    "TWOX_INGEST_POLL_MIN_SECONDS",
    "TWOX_INGEST_POLL_MAX_SECONDS",
    "TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS",
    "TWOX_INGEST_TIMEOUT_SECONDS",
    "TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS",
    "TWOX_SECTION_MAX_CHARS",
    "TWOX_EMBED_TASK_MAX_SECONDS",
)

# Values that fit together; each test below breaks exactly one condition.
VALID_TIMING: dict[str, int] = {
    "max_retries": 5,
    "poll_min_seconds": 10,
    "poll_max_seconds": 60,
    "docling_document_timeout_seconds": 7200,
    "docling_max_document_timeout_seconds": 7200,
    "ingest_timeout_seconds": 9000,
    "docling_queue_timeout_seconds": 86400,
    "section_max_chars": 2000,
    "embed_task_max_seconds": 240,
    "task_soft_time_limit": 300,
    "task_time_limit": 360,
    "visibility_timeout_seconds": 3600,
}


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
    # E-59: AI features are off unless switched on; E-56: bge-m3, 1024 values.
    assert values["ai_enabled"] is False
    assert values["embed_model"] == "bge-m3"
    assert values["embed_dimensions"] == 1024
    assert values["embed_batch_size"] == 16
    assert values["embed_query_prefix"] == ""
    assert values["embed_timeout_seconds"] == 120
    # Search queries have their own, short time limit (052).
    assert values["search_embed_timeout_seconds"] == 20
    # Ingestion (work order 045).
    assert values["ingest_max_retries"] == 5
    assert values["ingest_poll_min_seconds"] == 10
    assert values["ingest_poll_max_seconds"] == 60
    assert values["docling_document_timeout_seconds"] == 7200
    assert values["ingest_timeout_seconds"] == 9000
    # A job whose Docling task never starts: 24 hours (work order 065).
    assert values["docling_queue_timeout_seconds"] == 86400
    assert values["section_max_chars"] == 2000
    assert values["embed_task_max_seconds"] == 240


def test_ingest_settings_read_twox_variables() -> None:
    result = run_python(
        DUMP_SETTINGS,
        {
            "TWOX_INGEST_MAX_RETRIES": "3",
            "TWOX_INGEST_POLL_MIN_SECONDS": "5",
            "TWOX_INGEST_POLL_MAX_SECONDS": "30",
            "TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS": "3600",
            "TWOX_INGEST_TIMEOUT_SECONDS": "4000",
            "TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS": "4000",
            "TWOX_SECTION_MAX_CHARS": "1500",
            "TWOX_EMBED_TASK_MAX_SECONDS": "120",
        },
    )

    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["ingest_max_retries"] == 3
    assert values["ingest_poll_min_seconds"] == 5
    assert values["ingest_poll_max_seconds"] == 30
    assert values["docling_document_timeout_seconds"] == 3600
    assert values["ingest_timeout_seconds"] == 4000
    # Equal to the ingest deadline is allowed.
    assert values["docling_queue_timeout_seconds"] == 4000
    assert values["section_max_chars"] == 1500
    assert values["embed_task_max_seconds"] == 120


@pytest.mark.parametrize("name", INGEST_VARIABLES)
@pytest.mark.parametrize("value", ["0", "-1", "1.5", "many"])
def test_settings_reject_invalid_ingest_numbers(name: str, value: str) -> None:
    result = run_python(DUMP_SETTINGS, {name: value})

    assert result.returncode != 0
    assert f"{name} must be a whole number greater than zero" in result.stderr


def test_settings_stop_when_the_ingest_deadline_is_below_the_docling_timeout() -> None:
    result = run_python(DUMP_SETTINGS, {"TWOX_INGEST_TIMEOUT_SECONDS": "60"})

    assert result.returncode != 0
    assert (
        "TWOX_INGEST_TIMEOUT_SECONDS (60) must be greater than "
        "TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS (7200)"
    ) in result.stderr


def test_settings_stop_when_the_queue_deadline_is_below_the_ingest_deadline() -> None:
    result = run_python(DUMP_SETTINGS, {"TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS": "8999"})

    assert result.returncode != 0
    assert (
        "TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS (8999) must not be less than "
        "TWOX_INGEST_TIMEOUT_SECONDS (9000)"
    ) in result.stderr


def test_settings_stop_when_embedding_runs_longer_than_a_task_may() -> None:
    result = run_python(DUMP_SETTINGS, {"TWOX_EMBED_TASK_MAX_SECONDS": "300"})

    assert result.returncode != 0
    assert (
        "TWOX_EMBED_TASK_MAX_SECONDS (300) must be less than TWOX_TASK_SOFT_TIME_LIMIT (300)"
    ) in result.stderr


def test_settings_values_pass_the_ingest_check() -> None:
    settings_module.check_ingest_timing(
        max_retries=settings.TWOX_INGEST_MAX_RETRIES,
        poll_min_seconds=settings.TWOX_INGEST_POLL_MIN_SECONDS,
        poll_max_seconds=settings.TWOX_INGEST_POLL_MAX_SECONDS,
        docling_document_timeout_seconds=settings.TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS,
        docling_max_document_timeout_seconds=settings.TWOX_DOCLING_MAX_DOCUMENT_TIMEOUT_SECONDS,
        ingest_timeout_seconds=settings.TWOX_INGEST_TIMEOUT_SECONDS,
        docling_queue_timeout_seconds=settings.TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS,
        section_max_chars=settings.TWOX_SECTION_MAX_CHARS,
        embed_task_max_seconds=settings.TWOX_EMBED_TASK_MAX_SECONDS,
        task_soft_time_limit=settings.TWOX_TASK_SOFT_TIME_LIMIT,
        task_time_limit=settings.TWOX_TASK_TIME_LIMIT,
        visibility_timeout_seconds=settings.TWOX_BROKER_VISIBILITY_TIMEOUT_SECONDS,
    )


def test_ingest_check_accepts_values_that_fit() -> None:
    settings_module.check_ingest_timing(**VALID_TIMING)


def test_ingest_check_accepts_a_queue_deadline_equal_to_the_ingest_deadline() -> None:
    settings_module.check_ingest_timing(**(VALID_TIMING | {"docling_queue_timeout_seconds": 9000}))


def test_ingest_check_accepts_equal_poll_bounds() -> None:
    settings_module.check_ingest_timing(**(VALID_TIMING | {"poll_min_seconds": 60}))


@pytest.mark.parametrize(
    ("argument", "name"),
    [
        ("max_retries", "TWOX_INGEST_MAX_RETRIES"),
        ("poll_min_seconds", "TWOX_INGEST_POLL_MIN_SECONDS"),
        ("poll_max_seconds", "TWOX_INGEST_POLL_MAX_SECONDS"),
        ("docling_document_timeout_seconds", "TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS"),
        ("ingest_timeout_seconds", "TWOX_INGEST_TIMEOUT_SECONDS"),
        ("docling_queue_timeout_seconds", "TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS"),
        ("section_max_chars", "TWOX_SECTION_MAX_CHARS"),
        ("embed_task_max_seconds", "TWOX_EMBED_TASK_MAX_SECONDS"),
        ("task_soft_time_limit", "TWOX_TASK_SOFT_TIME_LIMIT"),
        ("task_time_limit", "TWOX_TASK_TIME_LIMIT"),
        ("visibility_timeout_seconds", "visibility_timeout"),
    ],
)
@pytest.mark.parametrize("value", [0, -1, 1.5, True, "60"])
def test_ingest_check_rejects_values_that_are_no_positive_whole_number(
    argument: str, name: str, value: object
) -> None:
    with pytest.raises(ImproperlyConfigured, match=f"^{name} must be a whole number"):
        settings_module.check_ingest_timing(**(VALID_TIMING | {argument: value}))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {"docling_document_timeout_seconds": 7201, "ingest_timeout_seconds": 9000},
            "TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS (7201) must not exceed the limit of the "
            "Docling service (7200 seconds)",
        ),
        (
            {"ingest_timeout_seconds": 7200},
            "TWOX_INGEST_TIMEOUT_SECONDS (7200) must be greater than "
            "TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS (7200)",
        ),
        (
            {"docling_queue_timeout_seconds": 8999},
            "TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS (8999) must not be less than "
            "TWOX_INGEST_TIMEOUT_SECONDS (9000)",
        ),
        (
            {"poll_min_seconds": 61},
            "TWOX_INGEST_POLL_MIN_SECONDS (61) must not be greater than "
            "TWOX_INGEST_POLL_MAX_SECONDS (60)",
        ),
        (
            {"poll_max_seconds": 3600},
            "TWOX_INGEST_POLL_MAX_SECONDS (3600) must be less than the visibility_timeout "
            "of the broker (3600)",
        ),
        (
            {"embed_task_max_seconds": 300},
            "TWOX_EMBED_TASK_MAX_SECONDS (300) must be less than TWOX_TASK_SOFT_TIME_LIMIT (300)",
        ),
        (
            {"task_soft_time_limit": 360},
            "TWOX_TASK_SOFT_TIME_LIMIT (360) must be less than TWOX_TASK_TIME_LIMIT (360)",
        ),
        (
            {"task_time_limit": 3600},
            "TWOX_TASK_TIME_LIMIT (3600) must be less than visibility_timeout of the broker (3600)",
        ),
    ],
)
def test_ingest_check_rejects_each_broken_condition(changes: dict[str, int], message: str) -> None:
    with pytest.raises(ImproperlyConfigured) as error:
        settings_module.check_ingest_timing(**(VALID_TIMING | changes))

    assert message in str(error.value)


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
            "TWOX_AI_ENABLED": "true",
            "TWOX_EMBED_MODEL": "qwen3-embedding:0.6b",
            "TWOX_EMBED_DIMENSIONS": "768",
            "TWOX_EMBED_BATCH_SIZE": "4",
            "TWOX_EMBED_QUERY_PREFIX": "Query: ",
            "TWOX_EMBED_TIMEOUT_SECONDS": "30",
            "TWOX_SEARCH_EMBED_TIMEOUT_SECONDS": "5",
        },
    )

    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["ai_enabled"] is True
    assert values["embed_model"] == "qwen3-embedding:0.6b"
    assert values["embed_dimensions"] == 768
    assert values["embed_batch_size"] == 4
    # Kept as written, trailing space included.
    assert values["embed_query_prefix"] == "Query: "
    assert values["embed_timeout_seconds"] == 30
    assert values["search_embed_timeout_seconds"] == 5
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


@pytest.mark.parametrize(
    "name",
    [
        "TWOX_EMBED_DIMENSIONS",
        "TWOX_EMBED_BATCH_SIZE",
        "TWOX_EMBED_TIMEOUT_SECONDS",
        "TWOX_SEARCH_EMBED_TIMEOUT_SECONDS",
    ],
)
@pytest.mark.parametrize("value", ["0", "-1", "1.5", "many"])
def test_settings_reject_invalid_embedding_numbers(name: str, value: str) -> None:
    result = run_python(DUMP_SETTINGS, {name: value})

    assert result.returncode != 0
    assert f"{name} must be a whole number greater than zero" in result.stderr


@pytest.mark.parametrize(("value", "expected"), [("false", False), ("0", False), ("on", True)])
def test_ai_switch_reads_booleans(value: str, expected: bool) -> None:
    result = run_python(DUMP_SETTINGS, {"TWOX_AI_ENABLED": value})

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ai_enabled"] is expected


def test_settings_reject_invalid_ai_switch() -> None:
    result = run_python(DUMP_SETTINGS, {"TWOX_AI_ENABLED": "sometimes"})

    assert result.returncode != 0
    assert "TWOX_AI_ENABLED must be true or false" in result.stderr


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
        "auditlog",
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
        "twox.accounts.audit.AuditMiddleware",
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
    # The settings module itself: the tests point LOCALE_PATHS at compiled
    # copies outside the source tree (tests/conftest.py).
    assert settings_module.LOCALE_PATHS == [BACKEND_ROOT / "locale"]
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


def test_change_log_stores_no_ip_address_and_json_changes() -> None:
    # E-43: no IP address in the change log.
    assert settings.AUDITLOG_DISABLE_REMOTE_ADDR is True
    assert settings.AUDITLOG_STORE_JSON_CHANGES is True
    # No correlation id from a request header.
    assert settings.AUDITLOG_CID_HEADER is None


def test_audit_middleware_runs_after_authentication() -> None:
    middleware: list[str] = settings.MIDDLEWARE

    assert middleware.index("twox.accounts.audit.AuditMiddleware") > middleware.index(
        "django.contrib.auth.middleware.AuthenticationMiddleware"
    )
    # Only the project's subclass, never auditlog's own middleware as well.
    assert "auditlog.middleware.AuditlogMiddleware" not in middleware


def test_tests_run_with_the_local_memory_cache() -> None:
    # See tests/conftest.py: plain pytest needs no Valkey.
    assert settings.CACHES["default"]["BACKEND"] == (
        "django.core.cache.backends.locmem.LocMemCache"
    )
