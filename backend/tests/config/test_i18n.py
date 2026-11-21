"""Backend messages in German and English (E-07, work order 034).

The API answers in the language of ``Accept-Language`` (LocaleMiddleware),
otherwise in English. The German catalogue is complete, and compiled
catalogues never end up in the source tree: the tests compile them into a
temporary directory (``tests/conftest.py``), the image in a build stage.
"""

import asyncio
import json
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import translation
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient

from tests.accounts.users import make_user
from tests.assets.csv_files import csv_text, row
from twox.accounts.roles import MANAGE, READ, ROLE_LABELS
from twox.assets.models import Area, Device, Plant, Site
from twox.config.asgi import application
from twox.files.models import Document
from twox.files.uploads import Message, Scope, max_request_bytes, scope_language

#: The catalogues as they are in the repository (the tests read compiled
#: copies from a temporary directory, see tests/conftest.py).
SOURCE_LOCALE_DIR = Path(settings.BASE_DIR) / "locale"
GERMAN_CATALOGUE = SOURCE_LOCALE_DIR / "de" / "LC_MESSAGES" / "django.po"

IMPORT_URL = "/api/v1/imports/devices/"


@pytest.fixture(autouse=True)
def back_to_the_default_language() -> Iterator[None]:
    """LocaleMiddleware leaves the language of the last request active; reset it."""
    yield
    translation.activate(settings.LANGUAGE_CODE)


def manager() -> APIClient:
    client = APIClient()
    user = make_user("manage")
    assert user is not None
    client.force_login(user)
    return client


def make_device() -> Device:
    site = Site.objects.create(name="Test site")
    area = Area.objects.create(site=site, name="Production line")
    plant = Plant.objects.create(area=area, key="aps-dps", name="Goods in and out")
    return Device.objects.create(plant=plant, key="dps-plc", name="Device")


def import_errors(client: APIClient, content: bytes, language: str) -> list[str]:
    response = client.post(
        IMPORT_URL,
        {"file": SimpleUploadedFile("devices.csv", content, content_type="text/csv")},
        format="multipart",
        headers={"Accept-Language": language},
    )
    assert response.status_code == 200
    return [error["message"] for error in response.json()["errors"]]


# --- API messages ------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "start"),
    [
        ("de", "Die erste Zeile muss genau diese 13 Spalten in dieser Reihenfolge nennen:"),
        ("en", "The first line must name exactly these 13 columns in this order:"),
    ],
)
def test_import_with_a_wrong_header(language: str, start: str) -> None:
    messages = import_errors(manager(), b"plant_id;device_id\nx;y\n", language)

    assert len(messages) == 1
    assert messages[0].startswith(start)


@pytest.mark.django_db
def test_import_messages_of_django_come_in_german_too() -> None:
    content = csv_text([row(ip_address="999.1.1.1")]).encode()

    assert import_errors(manager(), content, "de") == [
        "Bitte eine gültige IPv4 oder IPv6-Adresse eingeben."
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "detail"),
    [
        ("de", "Die Datei ist identisch mit der neuesten Version 1 dieses Dokuments."),
        ("en", "The file is identical to the newest version 1 of this document."),
    ],
)
def test_duplicate_version_is_409_in_the_language_asked_for(
    language: str, detail: str, tmp_path: Path, settings: Settings
) -> None:
    settings.TWOX_MEDIA_ROOT = tmp_path
    client = manager()
    device = make_device()
    first = client.post(
        f"/api/v1/devices/{device.pk}/documents/",
        {"file": SimpleUploadedFile("manual.pdf", b"same bytes", "application/pdf")},
        format="multipart",
    )
    assert first.status_code == 201
    document = Document.objects.get()

    response = client.post(
        f"/api/v1/documents/{document.pk}/versions/",
        {"file": SimpleUploadedFile("manual.pdf", b"same bytes", "application/pdf")},
        format="multipart",
        headers={"Accept-Language": language},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == detail


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "detail"),
    [
        ("de", "Anmeldedaten fehlen."),
        ("de-DE,de;q=0.9,en;q=0.8", "Anmeldedaten fehlen."),
        ("en", "Authentication credentials were not provided."),
        ("fr", "Authentication credentials were not provided."),
    ],
)
def test_drf_messages_follow_accept_language(language: str, detail: str) -> None:
    response = APIClient().get("/api/v1/me/", headers={"Accept-Language": language})

    assert response.status_code == 403
    assert response.json() == {"detail": detail}


@pytest.mark.django_db
def test_without_accept_language_the_api_answers_in_english() -> None:
    response = APIClient().get("/api/v1/me/")

    assert response.json() == {"detail": "Authentication credentials were not provided."}


# --- the 413 answer of the ASGI middleware -----------------------------------


def asgi_scope(accept_language: str | None) -> Scope:
    headers = [(b"host", b"testserver"), (b"content-length", str(max_request_bytes() + 1).encode())]
    if accept_language is not None:
        headers.append((b"accept-language", accept_language.encode()))
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/health/",
        "raw_path": b"/api/v1/health/",
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }


def too_large_detail(request_scope: Scope) -> str:
    sent: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(application(request_scope, receive, send))
    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == 413
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    detail: str = json.loads(body)["detail"]
    return detail


@pytest.mark.parametrize(
    ("accept_language", "detail"),
    [
        ("de", "Die Datei ist größer als die Grenze von 1000 Byte."),
        ("fr, de;q=0.5", "Die Datei ist größer als die Grenze von 1000 Byte."),
        ("en", "The file is larger than the limit of 1000 bytes."),
        (None, "The file is larger than the limit of 1000 bytes."),
    ],
)
def test_asgi_413_follows_accept_language(
    accept_language: str | None, detail: str, settings: Settings
) -> None:
    settings.TWOX_UPLOAD_MAX_BYTES = 1000
    settings.ALLOWED_HOSTS = ["testserver"]

    assert too_large_detail(asgi_scope(accept_language)) == detail
    # The middleware does not change the active language.
    assert translation.get_language() == settings.LANGUAGE_CODE


@pytest.mark.parametrize(
    ("accept_language", "language"),
    [("de-AT", "de"), ("*", "en"), ("xx", "en"), ("", "en"), ("en-GB, de", "en")],
)
def test_scope_language(accept_language: str, language: str) -> None:
    scope: Scope = {"headers": [(b"Accept-Language", accept_language.encode())]}

    assert scope_language(scope) == language


# --- labels ------------------------------------------------------------------


def test_role_labels_in_german() -> None:
    with translation.override("de"):
        assert {role: str(label) for role, label in ROLE_LABELS.items()} == {
            MANAGE: "Verwalten",
            READ: "Lesen",
        }


def test_admin_labels_in_german() -> None:
    with translation.override("de"):
        assert str(admin.site.site_header) == "2x-Verwaltung"
        assert str(Device._meta.verbose_name_plural) == "Geräte"
        assert str(Device._meta.get_field("software_version").verbose_name) == "Softwarestand"
        assert str(Document._meta.app_config.verbose_name) == "Dateien"


# --- the catalogue -----------------------------------------------------------


def msgattrib(option: str, catalogue: Path) -> str:
    tool = shutil.which("msgattrib")
    assert tool is not None, "msgattrib not found: the tests need GNU gettext (dev image)."
    result = subprocess.run(
        [tool, option, str(catalogue)], check=True, capture_output=True, text=True
    )
    return result.stdout


def test_german_catalogue_exists() -> None:
    assert sorted(SOURCE_LOCALE_DIR.rglob("*.po")) == [GERMAN_CATALOGUE]


@pytest.mark.parametrize("option", ["--untranslated", "--only-fuzzy"])
def test_german_catalogue_is_complete(option: str) -> None:
    assert msgattrib(option, GERMAN_CATALOGUE) == ""


def test_no_compiled_catalogue_in_the_source_tree() -> None:
    assert sorted(Path(settings.BASE_DIR).rglob("*.mo")) == []


def test_tests_read_compiled_catalogues_from_outside_the_source_tree() -> None:
    base_dir = Path(settings.BASE_DIR).resolve()
    for locale_path in settings.LOCALE_PATHS:
        compiled = Path(locale_path).resolve()
        assert not compiled.is_relative_to(base_dir)
        assert sorted(compiled.rglob("*.mo"))
