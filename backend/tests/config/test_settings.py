"""The settings load from TWOX_* variables and never need a running database."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.apps import apps

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

django.setup()
print(json.dumps({
    "debug": settings.DEBUG,
    "allowed_hosts": settings.ALLOWED_HOSTS,
    "db": settings.DATABASES["default"],
    "llm": settings.TWOX_LLM_BASE_URL,
    "docling": settings.TWOX_DOCLING_URL,
}))
"""


def run_python(code: str, overrides: dict[str, str | None]) -> subprocess.CompletedProcess[str]:
    """Run ``code`` in a fresh interpreter; a ``None`` override removes the variable."""
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
        [sys.executable, "-c", code],
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
    project_apps = sorted(config.name for config in apps.get_app_configs())

    assert project_apps == sorted(EXPECTED_APPS)
