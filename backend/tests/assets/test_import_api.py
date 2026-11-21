"""API of the device list import: POST /api/v1/imports/devices/."""

from io import StringIO
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from auditlog.models import LogEntry
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient

from tests.accounts.users import KINDS, make_user
from tests.assets.conftest import ClientFactory
from tests.assets.csv_files import TESTFACTORY_DEVICES_CSV, csv_text, row
from twox.assets.models import Device, Plant, Site

if TYPE_CHECKING:
    # Exists in the type stubs only; annotations are not evaluated at runtime.
    from rest_framework.response import _MonkeyPatchedResponse

pytestmark = pytest.mark.django_db

URL = "/api/v1/imports/devices/"


def upload(content: bytes, name: str = "devices.csv") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="text/csv")


def small_list() -> bytes:
    return csv_text([row(), row(device_id="press-hmi", device_name="Press HMI")]).encode()


def post(client: APIClient, content: bytes, **fields: str) -> _MonkeyPatchedResponse:
    return client.post(URL, {"file": upload(content), **fields}, format="multipart")


# --- rights ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "status"),
    [("anonymous", 403), ("no_role", 403), ("read", 403), ("manage", 200), ("superuser", 200)],
)
def test_only_the_role_manage_imports(client_for: ClientFactory, kind: str, status: int) -> None:
    response = post(client_for(kind), small_list(), dry_run="false")

    assert response.status_code == status
    assert Device.objects.count() == (2 if status == 200 else 0)


@pytest.mark.parametrize("kind", KINDS)
def test_get_is_not_an_operation(client_for: ClientFactory, kind: str) -> None:
    response = client_for(kind).get(URL)

    assert response.status_code == (405 if kind in {"manage", "superuser"} else 403)


# --- dry run and saving ------------------------------------------------------


def test_without_dry_run_field_it_is_a_dry_run(client_for: ClientFactory) -> None:
    response = post(client_for("manage"), small_list())

    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["saved"] is False
    assert body["devices"] == {"created": 2, "updated": 0, "unchanged": 0}
    assert Device.objects.count() == 0


@pytest.mark.parametrize("value", ["true", "True", "1"])
def test_dry_run_true_saves_nothing(client_for: ClientFactory, value: str) -> None:
    response = post(client_for("manage"), small_list(), dry_run=value)

    assert response.json()["dry_run"] is True
    assert Site.objects.count() == 0


@pytest.mark.parametrize("value", ["false", "False", "0"])
def test_dry_run_false_saves(client_for: ClientFactory, value: str) -> None:
    response = post(client_for("manage"), small_list(), dry_run=value)

    assert response.status_code == 200
    assert response.json() == {
        "dry_run": False,
        "saved": True,
        "rows": 2,
        "sites": {"created": 1, "updated": 0, "unchanged": 0},
        "areas": {"created": 1, "updated": 0, "unchanged": 0},
        "plants": {"created": 1, "updated": 0, "unchanged": 0},
        "devices": {"created": 2, "updated": 0, "unchanged": 0},
        "errors": [],
    }
    assert sorted(Device.objects.values_list("key", flat=True)) == ["press-hmi", "press-plc"]


def test_testfactory_device_list_over_the_api(client_for: ClientFactory) -> None:
    content = TESTFACTORY_DEVICES_CSV.read_bytes()
    client = client_for("manage")

    first = post(client, content, dry_run="false").json()
    second = post(client, content, dry_run="false").json()

    assert first["errors"] == []
    assert [first[level]["created"] for level in ("sites", "areas", "plants", "devices")] == [
        1,
        3,
        10,
        13,
    ]
    assert [second[level]["created"] for level in ("sites", "areas", "plants", "devices")] == [
        0,
        0,
        0,
        0,
    ]
    assert all(second[level]["updated"] == 0 for level in ("sites", "areas", "plants", "devices"))


def test_change_log_names_the_signed_in_user(client_for: ClientFactory) -> None:
    post(client_for("manage"), small_list(), dry_run="false")

    entries = LogEntry.objects.filter(content_type=ContentType.objects.get_for_model(Plant))
    assert [entry.actor.username if entry.actor else None for entry in entries] == ["manage"]


# --- errors ------------------------------------------------------------------


def test_errors_come_back_with_line_and_column(client_for: ClientFactory) -> None:
    content = csv_text([row(), row(device_id="second", ip_address="999.1.1.1")]).encode()

    response = post(client_for("manage"), content, dry_run="false")

    assert response.status_code == 200
    body = response.json()
    assert body["saved"] is False
    assert body["errors"] == [
        {"line": 3, "column": "ip_address", "message": "Enter a valid IPv4 or IPv6 address."}
    ]
    assert body["devices"] == {"created": 0, "updated": 0, "unchanged": 0}
    assert Device.objects.count() == 0


def test_file_error_has_no_column(client_for: ClientFactory) -> None:
    content = csv_text([row(plant_name="Frässtation")]).encode("latin-1")

    body = post(client_for("manage"), content, dry_run="false").json()

    assert [(error["line"], error["column"]) for error in body["errors"]] == [(2, None)]


def test_any_bytes_give_a_report_not_a_server_error(client_for: ClientFactory) -> None:
    content = bytes(range(256)) * 4

    response = post(client_for("manage"), content)

    assert response.status_code == 200
    assert response.json()["errors"]


def test_missing_file_is_400(client_for: ClientFactory) -> None:
    response = client_for("manage").post(URL, {"dry_run": "false"}, format="multipart")

    assert response.status_code == 400
    assert list(response.json()) == ["file"]


def test_invalid_dry_run_is_400(client_for: ClientFactory) -> None:
    response = post(client_for("manage"), small_list(), dry_run="maybe")

    assert response.status_code == 400
    assert list(response.json()) == ["dry_run"]
    assert Device.objects.count() == 0


def test_json_body_is_415(client_for: ClientFactory) -> None:
    response = client_for("manage").post(URL, {"dry_run": False}, format="json")

    assert response.status_code == 415


# --- size limit --------------------------------------------------------------


def test_file_over_the_upload_limit_is_413(client_for: ClientFactory, settings: Settings) -> None:
    content = small_list()
    settings.TWOX_UPLOAD_MAX_BYTES = len(content) - 1

    response = post(client_for("manage"), content, dry_run="false")

    assert response.status_code == 413
    assert str(len(content) - 1) in response.json()["detail"]
    assert Device.objects.count() == 0


def test_file_at_the_upload_limit_is_read(client_for: ClientFactory, settings: Settings) -> None:
    content = small_list()
    settings.TWOX_UPLOAD_MAX_BYTES = len(content)

    response = post(client_for("manage"), content, dry_run="false")

    assert response.status_code == 200
    assert Device.objects.count() == 2


# --- CSRF --------------------------------------------------------------------


def test_csrf_token_is_required_for_a_signed_in_import() -> None:
    client = APIClient(enforce_csrf_checks=True)
    manager = make_user("manage")
    assert manager is not None
    client.force_login(manager)
    client.get("/")
    token = client.cookies[settings.CSRF_COOKIE_NAME].value

    without = client.post(URL, {"file": upload(small_list())}, format="multipart")
    with_token = client.post(
        URL, {"file": upload(small_list())}, format="multipart", headers={"X-CSRFToken": token}
    )

    assert without.status_code == 403
    assert "CSRF" in without.json()["detail"]
    assert with_token.status_code == 200
    assert with_token.json()["errors"] == []


# --- schema ------------------------------------------------------------------


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    stdout = StringIO()
    stderr = StringIO()
    call_command("spectacular", "--validate", stdout=stdout, stderr=stderr)
    assert stderr.getvalue() == ""
    loaded: dict[str, Any] = yaml.safe_load(stdout.getvalue())
    return loaded


def test_schema_describes_the_import(schema: dict[str, Any]) -> None:
    operations = schema["paths"][URL]
    assert list(operations) == ["post"]
    post_operation = operations["post"]
    assert post_operation["operationId"] == "devices_import"
    assert list(post_operation["requestBody"]["content"]) == ["multipart/form-data"]
    assert set(post_operation["responses"]) == {"200", "400", "403", "413"}
    answer = post_operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert answer == {"$ref": "#/components/schemas/ImportReport"}


def test_schema_types_the_report(schema: dict[str, Any]) -> None:
    components = schema["components"]["schemas"]
    report = components["ImportReport"]
    form = components["DeviceImportForm"]["properties"]

    assert set(report["required"]) == {
        "dry_run",
        "saved",
        "rows",
        "sites",
        "areas",
        "plants",
        "devices",
        "errors",
    }
    assert report["properties"]["errors"]["items"] == {
        "$ref": "#/components/schemas/ImportRowError"
    }
    assert components["ImportRowError"]["properties"]["line"]["nullable"] is True
    assert components["ImportRowError"]["properties"]["column"]["nullable"] is True
    assert form["file"]["format"] == "binary"
    assert form["dry_run"]["default"] is True
