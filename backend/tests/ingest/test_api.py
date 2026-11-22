"""Ingest API: list of jobs, starting a job again, rights per role (work order 051).

No test reaches the broker, Docling or the model service: the autouse
fixture ``ingest_messages`` (tests/conftest.py) records the messages, and
``isolated_services`` fails every test that reaches a real client.
"""

from typing import Any

import pytest
from django.conf import settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks, Settings
from rest_framework.test import APIClient

from tests.accounts.users import make_user
from tests.config.test_api import generate_schema
from tests.conftest import IngestMessages
from tests.files.helpers import client_for, make_device
from tests.ingest.fake_converter import isolated_services, make_version
from twox.accounts.models import User
from twox.files.models import Document, DocumentKind, DocumentVersion
from twox.ingest.api import CODE_CONFIGURATION, CODE_INGEST_ACTIVE
from twox.ingest.models import IngestErrorCode, IngestJob, IngestStatus, IngestStep

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("isolated_services")]

JOBS_URL = "/api/v1/ingest-jobs/"
CONVERT = "twox.ingest.convert"

JOB_FIELDS = {
    "id",
    "status",
    "step",
    "error_code",
    "error_detail",
    "partly_converted",
    "section_count",
    "page_count",
    "created_at",
    "finished_at",
    "document",
    "version",
    "device",
    "requested_by",
}

#: A cleaned technical text as the ingest flow writes it (046).
FAILED_DETAIL = "docling-serve refused the connection (gave up after 5 retries)"


def ingest_url(version_id: int) -> str:
    return f"/api/v1/document-versions/{version_id}/ingest/"


def make_job(version: DocumentVersion, **fields: Any) -> IngestJob:  # noqa: ANN401 - model fields
    return IngestJob.objects.create(document_version=version, **fields)


def failed_job(version: DocumentVersion, user: User | None = None) -> IngestJob:
    return make_job(
        version,
        status=IngestStatus.FAILED,
        step=IngestStep.CONVERT,
        error_code=IngestErrorCode.DOCLING_UNAVAILABLE,
        error_detail=FAILED_DETAIL,
        requested_by=user,
    )


def configuration_version() -> DocumentVersion:
    # No service creates a configuration in M2; a row made otherwise is refused.
    document = Document.objects.create(
        device=make_device("router"), title="Router", kind=DocumentKind.CONFIGURATION
    )
    return make_version(b"option=1\n", filename="router.conf", document=document)


def results(client: APIClient, query: str = "") -> list[dict[str, Any]]:
    response = client.get(JOBS_URL + query)
    assert response.status_code == 200, response.content
    items: list[dict[str, Any]] = response.json()["results"]
    return items


# --- rights -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("anonymous", 403), ("no_role", 403), ("read", 200), ("manage", 200), ("superuser", 200)],
)
def test_list_needs_a_role(kind: str, expected: int) -> None:
    make_job(make_version())

    assert client_for(kind).get(JOBS_URL).status_code == expected


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("anonymous", 403), ("no_role", 403), ("read", 403), ("manage", 202), ("superuser", 202)],
)
def test_only_manage_may_start_ingesting(
    kind: str, expected: int, ingest_messages: IngestMessages
) -> None:
    version = make_version()

    response = client_for(kind).post(ingest_url(version.pk))

    assert response.status_code == expected
    assert IngestJob.objects.count() == (1 if expected == 202 else 0)
    if expected != 202:
        assert ingest_messages.sent == []


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_ingest_endpoint_only_takes_post(method: str) -> None:
    version = make_version()

    response = getattr(client_for("manage"), method)(ingest_url(version.pk))

    assert response.status_code == 405
    assert not IngestJob.objects.exists()


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_job_list_is_read_only(method: str) -> None:
    response = getattr(client_for("manage"), method)(JOBS_URL)

    assert response.status_code == 405


def test_csrf_token_is_required_to_start_ingesting() -> None:
    version = make_version()
    client = APIClient(enforce_csrf_checks=True)
    manager = make_user("manage")
    assert manager is not None
    client.force_login(manager)
    client.get("/")
    token = client.cookies[settings.CSRF_COOKIE_NAME].value

    without = client.post(ingest_url(version.pk))
    with_token = client.post(ingest_url(version.pk), headers={"X-CSRFToken": token})

    assert without.status_code == 403
    assert "CSRF" in without.json()["detail"]
    assert with_token.status_code == 202
    assert IngestJob.objects.count() == 1


# --- start again: 202, 409, 400, 404 -------------------------------------------------


def test_start_creates_a_queued_job_and_sends_it_after_the_commit(
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version = make_version()
    client = client_for("manage")

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(ingest_url(version.pk))

    assert response.status_code == 202
    body = response.json()
    job = IngestJob.objects.get()
    assert set(body) == JOB_FIELDS
    assert body["id"] == job.pk
    assert body["status"] == "queued"
    assert (body["step"], body["error_code"], body["error_detail"]) == ("", "", "")
    assert body["partly_converted"] is False
    assert body["requested_by"] == "manage"
    assert body["version"] == {
        "id": version.pk,
        "number": 1,
        "original_filename": "BetrSichV.pdf",
    }
    assert body["document"] == {"id": version.document.pk, "title": "Manual dps-plc"}
    device = version.document.device
    assert body["device"] == {"id": device.pk, "key": "dps-plc", "name": "Device dps-plc"}
    assert job.requested_by is not None
    assert job.requested_by.username == "manage"
    assert ingest_messages.sent == [(CONVERT, (job.pk,))]


def test_start_of_an_unsupported_file_is_skipped_at_once(ingest_messages: IngestMessages) -> None:
    version = make_version(b"key: value\n", filename="plant.yaml", content_type="text/yaml")

    response = client_for("manage").post(ingest_url(version.pk))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "skipped"
    assert body["error_code"] == "unsupported_format"
    assert body["error_detail"].startswith("files with the extension .yaml are not ingested")
    assert body["finished_at"] is not None
    assert ingest_messages.sent == []


def test_start_without_stored_content_fails_at_once() -> None:
    version = make_version()
    # A key of content that was never stored.
    DocumentVersion.objects.filter(pk=version.pk).update(blob_key="sha256/00/00/" + "0" * 64)

    response = client_for("manage").post(ingest_url(version.pk))

    assert response.status_code == 202
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "content_missing"


@pytest.mark.parametrize("active", [IngestStatus.QUEUED, IngestStatus.RUNNING])
def test_start_while_a_job_is_active_is_409(
    active: IngestStatus, ingest_messages: IngestMessages
) -> None:
    version = make_version()
    running = make_job(version, status=active)

    response = client_for("manage").post(ingest_url(version.pk))

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == CODE_INGEST_ACTIVE
    assert body["detail"] == "This document version is already being ingested."
    assert body["job"]["id"] == running.pk
    assert body["job"]["status"] == active.value
    assert IngestJob.objects.count() == 1
    assert ingest_messages.sent == []


def test_409_is_translated() -> None:
    version = make_version()
    make_job(version, status=IngestStatus.QUEUED)

    response = client_for("manage").post(ingest_url(version.pk), headers={"Accept-Language": "de"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Diese Dokumentversion wird bereits eingelesen."


@pytest.mark.parametrize("finished", [IngestStatus.DONE, IngestStatus.FAILED, IngestStatus.SKIPPED])
def test_start_after_a_finished_job_is_allowed(finished: IngestStatus) -> None:
    version = make_version()
    old = make_job(version, status=finished)

    response = client_for("manage").post(ingest_url(version.pk))

    assert response.status_code == 202
    assert response.json()["id"] != old.pk
    assert IngestJob.objects.count() == 2


@pytest.mark.parametrize(
    ("language", "detail"),
    [
        ("en", "Configuration files are not ingested."),
        ("de", "Konfigurationsdateien werden nicht eingelesen."),
    ],
)
def test_configuration_is_400(language: str, detail: str, ingest_messages: IngestMessages) -> None:
    version = configuration_version()

    response = client_for("manage").post(
        ingest_url(version.pk), headers={"Accept-Language": language}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": detail, "code": CODE_CONFIGURATION}
    assert not IngestJob.objects.exists()
    assert ingest_messages.sent == []


def test_unknown_version_is_404() -> None:
    response = client_for("manage").post(ingest_url(999_999))

    assert response.status_code == 404
    assert not IngestJob.objects.exists()


# --- list: order, fields, pages ------------------------------------------------------


def test_list_is_newest_first_with_all_fields() -> None:
    version = make_version()
    first = failed_job(version)
    second = make_job(version, status=IngestStatus.QUEUED)

    items = results(client_for("read"))

    assert [item["id"] for item in items] == [second.pk, first.pk]
    assert set(items[1]) == JOB_FIELDS
    assert items[1]["status"] == "failed"
    assert items[1]["step"] == "convert"
    assert items[1]["error_code"] == "docling_unavailable"
    assert items[1]["error_detail"] == FAILED_DETAIL


def test_list_has_pages_of_50() -> None:
    version = make_version()
    IngestJob.objects.bulk_create(
        IngestJob(document_version=version, status=IngestStatus.DONE) for _ in range(51)
    )
    newest_first = list(
        IngestJob.objects.order_by("-created_at", "-pk").values_list("pk", flat=True)
    )
    client = client_for("read")

    first = client.get(JOBS_URL).json()
    second = client.get(JOBS_URL + "?page=2").json()

    assert first["count"] == 51
    assert len(first["results"]) == 50
    assert first["next"].endswith("?page=2")
    assert first["previous"] is None
    assert len(second["results"]) == 1
    assert second["next"] is None
    assert [item["id"] for item in first["results"] + second["results"]] == newest_first
    assert client.get(JOBS_URL + "?page=3").status_code == 404
    # The client cannot choose another page size.
    assert len(client.get(JOBS_URL + "?page_size=100").json()["results"]) == 50


def test_list_needs_a_fixed_number_of_queries() -> None:
    client = client_for("manage")
    manager = User.objects.get(username="manage")

    def count_queries() -> int:
        with CaptureQueriesContext(connection) as queries:
            response = client.get(JOBS_URL)
        assert response.status_code == 200
        return len(queries)

    failed_job(make_version(device="dps-plc"), manager)
    few = count_queries()
    for number in range(10):
        failed_job(make_version(f"other {number}".encode(), device=f"device-{number}"), manager)
    many = count_queries()

    assert few == many


# --- list: filters --------------------------------------------------------------------


@pytest.fixture
def two_devices() -> dict[str, IngestJob]:
    """Jobs of two devices: one document with two versions on the first, one on the second."""
    first = make_version(device="dps-plc")
    first_v2 = make_version(b"%PDF-1.7 v2\n", document=first.document, number=2)
    other = make_version(b"%PDF-1.7 other\n", device="hbw-plc")
    return {
        "first_failed": failed_job(first),
        "first_done": make_job(first, status=IngestStatus.DONE),
        "second_version": make_job(first_v2, status=IngestStatus.RUNNING),
        "other_skipped": make_job(other, status=IngestStatus.SKIPPED),
    }


def ids(items: list[dict[str, Any]]) -> set[int]:
    return {item["id"] for item in items}


def test_filter_by_status(two_devices: dict[str, IngestJob]) -> None:
    client = client_for("read")

    assert ids(results(client, "?status=failed")) == {two_devices["first_failed"].pk}
    assert ids(results(client, "?status=failed&status=skipped")) == {
        two_devices["first_failed"].pk,
        two_devices["other_skipped"].pk,
    }
    assert results(client, "?status=queued") == []


def test_filter_by_device_document_and_version(two_devices: dict[str, IngestJob]) -> None:
    client = client_for("read")
    first = two_devices["first_failed"].document_version
    second = two_devices["second_version"].document_version
    other = two_devices["other_skipped"].document_version

    assert ids(results(client, f"?device={first.document.device_id}")) == {
        two_devices["first_failed"].pk,
        two_devices["first_done"].pk,
        two_devices["second_version"].pk,
    }
    assert ids(results(client, f"?document={other.document_id}")) == {
        two_devices["other_skipped"].pk
    }
    assert ids(results(client, f"?version={second.pk}")) == {two_devices["second_version"].pk}
    assert ids(results(client, f"?device={first.document.device_id}&status=done")) == {
        two_devices["first_done"].pk
    }
    assert results(client, "?device=999999") == []


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("?status=finished", "status"),
        ("?status=done&status=", "status"),
        ("?device=abc", "device"),
        ("?document=0", "document"),
        ("?version=-1", "version"),
    ],
)
def test_invalid_filter_is_400(query: str, field: str) -> None:
    response = client_for("read").get(JOBS_URL + query)

    assert response.status_code == 400
    assert field in response.json()


# --- requested_by and error_detail per role ----------------------------------------


@pytest.mark.parametrize(
    ("kind", "shown"), [("manage", True), ("superuser", True), ("read", False)]
)
def test_requested_by_only_for_manage(kind: str, shown: bool) -> None:
    starter = User.objects.create_user("ingest-starter")
    version = make_version()
    by_user = failed_job(version, starter)
    by_system = make_job(version, status=IngestStatus.DONE)

    items = {item["id"]: item for item in results(client_for(kind))}

    assert items[by_user.pk]["requested_by"] == ("ingest-starter" if shown else None)
    assert items[by_system.pk]["requested_by"] is None


@pytest.mark.parametrize("kind", ["read", "manage"])
def test_error_code_and_detail_for_every_role(kind: str) -> None:
    job = failed_job(make_version())

    [item] = results(client_for(kind))

    assert item["id"] == job.pk
    assert item["error_code"] == "docling_unavailable"
    assert item["error_detail"] == FAILED_DETAIL


def test_partial_conversion_is_done_with_a_note() -> None:
    version = make_version()
    job = make_job(
        version,
        status=IngestStatus.DONE,
        step=IngestStep.SECTIONS,
        error_detail="converted with 2 errors on pages 3, 7",
        section_count=12,
        page_count=9,
    )

    [item] = results(client_for("read"))

    assert item["id"] == job.pk
    assert item["status"] == "done"
    assert item["partly_converted"] is True
    assert item["error_code"] == ""
    assert item["error_detail"] == "converted with 2 errors on pages 3, 7"
    assert (item["section_count"], item["page_count"]) == (12, 9)


@pytest.mark.parametrize("ai_enabled", [True, False], ids=["ai-on", "ai-off"])
def test_api_is_the_same_with_and_without_ai(
    ai_enabled: bool, settings: Settings, ingest_messages: IngestMessages
) -> None:
    # E-59: nothing here depends on embeddings; isolated_services fails any
    # call of the model service.
    settings.TWOX_AI_ENABLED = ai_enabled
    version = make_version()
    make_job(version, status=IngestStatus.DONE, step=IngestStep.SECTIONS, section_count=3)
    client = client_for("manage")

    items = results(client)
    started = client.post(ingest_url(make_version(b"%PDF-1.7 new\n", device="hbw-plc").pk))

    assert items[0]["status"] == "done"
    assert items[0]["error_code"] == ""
    assert started.status_code == 202
    assert started.json()["status"] == "queued"


# --- schema ---------------------------------------------------------------------------


def test_schema_lists_the_ingest_endpoints_and_fields() -> None:
    schema, stderr = generate_schema()
    paths: dict[str, Any] = schema["paths"]
    components: dict[str, Any] = schema["components"]["schemas"]

    assert stderr == ""
    listing = paths["/api/v1/ingest-jobs/"]["get"]
    start = paths["/api/v1/document-versions/{version_id}/ingest/"]["post"]
    assert set(paths["/api/v1/ingest-jobs/"]) == {"get"}
    assert set(paths["/api/v1/document-versions/{version_id}/ingest/"]) == {"post"}
    assert listing["operationId"] == "ingest_jobs_list"
    assert start["operationId"] == "document_version_ingest"
    assert "requestBody" not in start
    assert set(start["responses"]) == {"202", "400", "403", "404", "409"}
    assert set(listing["responses"]) >= {"200", "400", "403"}
    parameters = {parameter["name"]: parameter for parameter in listing["parameters"]}
    assert set(parameters) == {"status", "device", "document", "version", "page"}
    assert parameters["status"]["schema"]["type"] == "array"
    assert set(parameters["status"]["schema"]["items"]["enum"]) == set(IngestStatus.values)
    assert set(components["IngestJob"]["properties"]) == JOB_FIELDS
    assert components["IngestJob"]["properties"]["requested_by"]["nullable"] is True
    assert set(components["IngestJobSummary"]["properties"]) == JOB_FIELDS - {
        "document",
        "version",
        "device",
        "requested_by",
    }
    assert set(components["IngestStatusEnum"]["enum"]) == set(IngestStatus.values)
    assert set(components["IngestJobDevice"]["properties"]) == {"id", "key", "name"}
    assert set(components["IngestJobDocument"]["properties"]) == {"id", "title"}
    assert set(components["IngestJobVersion"]["properties"]) == {
        "id",
        "number",
        "original_filename",
    }
    assert set(components["IngestConflict"]["properties"]) == {"detail", "code", "job"}
    version = components["DocumentVersion"]["properties"]["ingest"]
    assert version["nullable"] is True
    assert version["allOf"] == [{"$ref": "#/components/schemas/IngestJobSummary"}]
