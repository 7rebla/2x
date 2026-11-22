"""Acceptance of M1 over the API, without a browser (docs/ROADMAP.md, M1).

Condition: the device list of the test factory loaded per CSV
(``testfactory/layout/devices.csv``); one file with two versions; the change
log shows the changes. The same flow runs in the browser in
``web/e2e/m1-acceptance.spec.ts``.

The device list is the real file of the test factory, mounted read-only into
``backend-dev`` (``deploy/compose/compose.yaml``). The uploaded file is made
in the test; nothing comes from vendor documents.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient

from tests.accounts.users import make_user
from tests.assets.csv_files import TESTFACTORY_DEVICES_CSV

if TYPE_CHECKING:
    # Exists in the type stubs only; annotations are not evaluated at runtime.
    from rest_framework.response import _MonkeyPatchedResponse

pytestmark = pytest.mark.django_db

IMPORT_URL = "/api/v1/imports/devices/"
AUDIT_URL = "/api/v1/audit-log/"
LEVELS = ("sites", "areas", "plants", "devices")

#: Expected numbers of the device list (work order 106): 14 data rows,
#: 1 site, 3 areas, 10 plants, 13 devices.
ROWS = 14
EXPECTED = {"sites": 1, "areas": 3, "plants": 10, "devices": 13}
AREAS = ["Fertigungslinie", "Netzübergang", "Roboterzelle"]

#: The account of the test; it has the role ``manage``.
MANAGER = "manage"


@pytest.fixture
def media_root(tmp_path: Path, settings: Settings) -> Path:
    """A fresh storage root per test; nothing touches the media volume."""
    root = tmp_path / "media"
    root.mkdir()
    settings.TWOX_MEDIA_ROOT = root
    return root


@pytest.fixture
def manager(db: None) -> APIClient:
    """An API client signed in with the role ``manage``."""
    user = make_user(MANAGER)
    assert user is not None
    client = APIClient()
    client.force_login(user)
    return client


def import_devices(client: APIClient, *, dry_run: bool) -> dict[str, Any]:
    """Send the device list of the test factory to the import endpoint."""
    upload = SimpleUploadedFile(
        "devices.csv", TESTFACTORY_DEVICES_CSV.read_bytes(), content_type="text/csv"
    )
    response = client.post(
        IMPORT_URL,
        {"file": upload, "dry_run": "true" if dry_run else "false"},
        format="multipart",
    )
    assert response.status_code == 200, response.content
    body: dict[str, Any] = response.json()
    assert body["errors"] == []
    assert body["rows"] == ROWS
    return body


def counts(report: dict[str, Any], kind: str) -> dict[str, int]:
    """One kind of count (created, updated, unchanged) per level of the report."""
    return {level: report[level][kind] for level in LEVELS}


def audit_entries(client: APIClient, object_type: str) -> list[dict[str, Any]]:
    """All change log entries of an object type by the manager, newest first."""
    entries: list[dict[str, Any]] = []
    url: str | None = f"{AUDIT_URL}?object_type={object_type}&actor={MANAGER}"
    while url is not None:
        response = client.get(url)
        assert response.status_code == 200, response.content
        page = response.json()
        entries.extend(page["results"])
        url = page["next"]
    return entries


def get(client: APIClient, url: str) -> list[dict[str, Any]]:
    """A list endpoint of the API."""
    response = client.get(url)
    assert response.status_code == 200, response.content
    body: list[dict[str, Any]] = response.json()
    return body


def get_document(client: APIClient, document_id: int) -> dict[str, Any]:
    """A file with all its versions, oldest first."""
    response = client.get(f"/api/v1/documents/{document_id}/")
    assert response.status_code == 200, response.content
    body: dict[str, Any] = response.json()
    return body


def upload_file(
    client: APIClient, url: str, content: bytes, **fields: str
) -> _MonkeyPatchedResponse:
    upload = SimpleUploadedFile("m1-acceptance.txt", content, content_type="text/plain")
    return client.post(url, {"file": upload, **fields}, format="multipart")


@pytest.fixture
def imported(manager: APIClient) -> dict[str, Any]:
    """The device list after a dry run and the saved import; returns the saved report."""
    dry_run = import_devices(manager, dry_run=True)
    assert dry_run["saved"] is False
    assert counts(dry_run, "created") == EXPECTED
    assert get(manager, "/api/v1/devices/") == []

    saved = import_devices(manager, dry_run=False)
    assert saved["saved"] is True
    return saved


def test_device_list_of_the_test_factory_is_imported(
    manager: APIClient, imported: dict[str, Any]
) -> None:
    assert counts(imported, "created") == EXPECTED
    assert counts(imported, "updated") == dict.fromkeys(LEVELS, 0)

    # The structure: one site, its three areas, the PLC with its address and
    # the charging station as a plant without a device but with notes.
    assert [site["name"] for site in get(manager, "/api/v1/sites/")] == ["Testfabrik"]
    assert sorted(area["name"] for area in get(manager, "/api/v1/areas/")) == AREAS
    assert len(get(manager, "/api/v1/plants/")) == EXPECTED["plants"]
    devices = {device["key"]: device for device in get(manager, "/api/v1/devices/")}
    assert len(devices) == EXPECTED["devices"]
    assert devices["dps-plc"]["ip_address"] == "192.168.0.90"
    charging = next(p for p in get(manager, "/api/v1/plants/") if p["key"] == "aps-charging")
    assert charging["notes"].startswith("Kein Gerät angelegt")
    assert get(manager, f"/api/v1/devices/?plant={charging['id']}") == []


def test_change_log_shows_the_import_with_the_user(
    manager: APIClient, imported: dict[str, Any]
) -> None:
    for object_type, level in (
        ("assets.site", "sites"),
        ("assets.area", "areas"),
        ("assets.plant", "plants"),
        ("assets.device", "devices"),
    ):
        created = [e for e in audit_entries(manager, object_type) if e["action"] == "create"]
        assert len(created) == EXPECTED[level], object_type
        assert all(entry["actor"] == MANAGER for entry in created)

    devices = audit_entries(manager, "assets.device")
    plc = [entry for entry in devices if entry["object_repr"].endswith("(dps-plc)")]
    assert len(plc) == 1
    assert plc[0]["changes"]["ip_address"] == [None, "192.168.0.90"]


def test_repeated_import_changes_nothing(manager: APIClient, imported: dict[str, Any]) -> None:
    entries_before = len(audit_entries(manager, "assets.device"))

    for dry_run in (True, False):
        again = import_devices(manager, dry_run=dry_run)
        assert counts(again, "created") == dict.fromkeys(LEVELS, 0)
        assert counts(again, "updated") == dict.fromkeys(LEVELS, 0)
        assert counts(again, "unchanged") == EXPECTED

    assert len(audit_entries(manager, "assets.device")) == entries_before


def test_file_with_two_versions_and_its_change_log(
    manager: APIClient, imported: dict[str, Any], media_root: Path
) -> None:
    device = next(d for d in get(manager, "/api/v1/devices/") if d["key"] == "dps-plc")
    first_content = b"M1 acceptance test file\nversion 1\n"
    second_content = b"M1 acceptance test file\nversion 2\n"

    first = upload_file(
        manager,
        f"/api/v1/devices/{device['id']}/documents/",
        first_content,
        title="M1 acceptance",
    )
    assert first.status_code == 201, first.content
    document_id = first.json()["document"]["id"]
    second = upload_file(manager, f"/api/v1/documents/{document_id}/versions/", second_content)
    assert second.status_code == 201, second.content

    # Both versions, with their own checksum, uploader and time.
    versions = get_document(manager, document_id)["versions"]
    assert [version["number"] for version in versions] == [1, 2]
    assert [version["sha256"] for version in versions] == [
        hashlib.sha256(first_content).hexdigest(),
        hashlib.sha256(second_content).hexdigest(),
    ]
    assert versions[0]["sha256"] != versions[1]["sha256"]
    assert all(version["uploaded_by"] == MANAGER for version in versions)

    # The change log: the document once, each version with user and time.
    documents = audit_entries(manager, "files.document")
    assert [(e["action"], e["object_repr"]) for e in documents] == [("create", "M1 acceptance")]
    logged = audit_entries(manager, "files.documentversion")
    assert [(e["action"], e["object_repr"]) for e in logged] == [
        ("create", "M1 acceptance v2"),
        ("create", "M1 acceptance v1"),
    ]
    for entry, version in zip(logged, reversed(versions), strict=True):
        assert entry["actor"] == MANAGER
        assert entry["object_id"] == version["id"]
        assert datetime.fromisoformat(entry["timestamp"]).tzinfo is not None
        assert entry["changes"]["sha256"] == [None, version["sha256"]]
