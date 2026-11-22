"""Files API: list, upload, versions, duplicates, rights, size limit and safe download."""

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from django.db import connection
from django.http import HttpResponseBase, StreamingHttpResponse
from django.test.utils import CaptureQueriesContext
from pytest_django.fixtures import (
    DjangoAssertNumQueries,
    DjangoCaptureOnCommitCallbacks,
    Settings,
)
from rest_framework.test import APIClient

from tests.accounts.users import make_user
from tests.config.test_api import generate_schema
from tests.files.helpers import (
    client_for,
    files_below,
    make_device,
    multipart_body,
    post_multipart,
)
from twox.assets.models import Device
from twox.files.models import Document, DocumentKind, DocumentVersion
from twox.files.serializers import PARTIAL_DETAIL_PREFIX
from twox.files.services import add_version, create_document
from twox.files.uploads import MULTIPART_OVERHEAD_BYTES
from twox.ingest import pipeline
from twox.ingest.docling import ConversionErrorItem
from twox.ingest.models import IngestErrorCode, IngestJob, IngestStatus, IngestStep

if TYPE_CHECKING:
    # Exists in the type stubs only; annotations are not evaluated at runtime.
    from rest_framework.response import _MonkeyPatchedResponse

pytestmark = pytest.mark.django_db


def documents_url(device: Device | int) -> str:
    device_id = device if isinstance(device, int) else device.pk
    return f"/api/v1/devices/{device_id}/documents/"


def document_url(document_id: int) -> str:
    return f"/api/v1/documents/{document_id}/"


def versions_url(document_id: int) -> str:
    return f"/api/v1/documents/{document_id}/versions/"


def download_url(version_id: int) -> str:
    return f"/api/v1/document-versions/{version_id}/download/"


def a_file(
    content: bytes, name: str = "manual.pdf", content_type: str = "application/pdf"
) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type=content_type)


def upload(
    client: APIClient, device: Device, content: bytes, **fields: object
) -> _MonkeyPatchedResponse:
    file = fields.pop("file", None) or a_file(content)
    return client.post(documents_url(device), {"file": file, **fields}, format="multipart")


def body_of(response: HttpResponseBase) -> bytes:
    assert isinstance(response, StreamingHttpResponse)
    return b"".join(response.streaming_content)  # type: ignore[arg-type]


# --- upload, versions, list and detail -------------------------------------


def test_upload_creates_document_with_version_one(media_root: Path) -> None:
    device = make_device()

    response = upload(client_for("manage"), device, b"edition 1", title="Operating manual")

    assert response.status_code == 201
    body = response.json()
    assert body["document"]["title"] == "Operating manual"
    assert body["document"]["device"] == device.pk
    assert body["document"]["kind"] == "document"
    assert body["document"]["created_by"] == "manage"
    assert body["document"]["latest_version"]["number"] == 1
    assert body["version"] == body["document"]["latest_version"]
    assert body["version"]["sha256"] == hashlib.sha256(b"edition 1").hexdigest()
    assert body["version"]["size"] == len(b"edition 1")
    assert body["version"]["content_type"] == "application/pdf"
    assert body["version"]["original_filename"] == "manual.pdf"
    assert body["version"]["uploaded_by"] == "manage"
    assert body["duplicates"] == []
    assert Document.objects.get().device == device


def test_title_defaults_to_the_file_name(media_root: Path) -> None:
    response = upload(client_for("manage"), make_device(), b"x", file=a_file(b"x", "plan.pdf"))

    assert response.status_code == 201
    assert response.json()["document"]["title"] == "plan.pdf"


def test_second_version_and_detail_and_list(media_root: Path) -> None:
    client = client_for("manage")
    device = make_device()
    first = upload(client, device, b"edition 1").json()
    document_id = first["document"]["id"]

    second = client.post(
        versions_url(document_id),
        {"file": a_file(b"edition 2", "manual-2.pdf")},
        format="multipart",
    )

    assert second.status_code == 201
    assert second.json()["version"]["number"] == 2
    assert second.json()["document"]["latest_version"]["number"] == 2
    assert second.json()["duplicates"] == []

    detail = client.get(document_url(document_id))
    assert detail.status_code == 200
    assert [v["number"] for v in detail.json()["versions"]] == [1, 2]
    assert detail.json()["versions"][1]["original_filename"] == "manual-2.pdf"
    assert detail.json()["latest_version"]["number"] == 2

    listing = client.get(documents_url(device))
    assert listing.status_code == 200
    assert [d["id"] for d in listing.json()] == [document_id]
    assert listing.json()[0]["latest_version"]["sha256"] == (
        hashlib.sha256(b"edition 2").hexdigest()
    )
    assert "versions" not in listing.json()[0]


def test_list_is_per_device_and_sorted_by_title(media_root: Path) -> None:
    client = client_for("manage")
    device = make_device("dps-plc")
    other = make_device("hbw-plc")
    upload(client, device, b"b", title="B manual")
    upload(client, device, b"a", title="A manual")
    upload(client, other, b"c", title="Other device")

    titles = [d["title"] for d in client.get(documents_url(device)).json()]

    assert titles == ["A manual", "B manual"]


def test_list_needs_a_fixed_number_of_queries(
    media_root: Path, django_assert_max_num_queries: DjangoAssertNumQueries
) -> None:
    device = make_device()
    client = client_for("read")
    for number in range(5):
        result = create_document(
            device, a_file(f"doc {number}".encode()), f"Doc {number}", DocumentKind.DOCUMENT, None
        )
        add_version(result.document, a_file(f"doc {number} v2".encode()), None)

    with django_assert_max_num_queries(8):
        response = client.get(documents_url(device))

    assert response.status_code == 200
    assert len(response.json()) == 5


# --- ingest state of the versions (work order 051) ---------------------------

INGEST_FIELDS = {
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
}


def two_versions(client: APIClient, device: Device) -> tuple[int, list[DocumentVersion]]:
    """A document with two versions, uploaded through the API."""
    document_id = upload(client, device, b"edition 1").json()["document"]["id"]
    client.post(versions_url(document_id), {"file": a_file(b"edition 2")}, format="multipart")
    return document_id, list(DocumentVersion.objects.order_by("number"))


def test_version_without_ingest_job_has_ingest_null(media_root: Path) -> None:
    client = client_for("manage")
    created = upload(client, make_device(), b"edition 1").json()

    detail = client.get(document_url(created["document"]["id"])).json()

    assert created["version"]["ingest"] is None
    assert detail["versions"][0]["ingest"] is None
    assert detail["latest_version"]["ingest"] is None


def test_detail_shows_the_newest_job_of_every_version(media_root: Path) -> None:
    client = client_for("read")
    document_id, (first, second) = two_versions(client_for("manage"), make_device())
    IngestJob.objects.create(
        document_version=first,
        status=IngestStatus.FAILED,
        step=IngestStep.CONVERT,
        error_code=IngestErrorCode.TIMEOUT,
        error_detail="time limit exceeded after 9000 s",
    )
    newest_of_first = IngestJob.objects.create(
        document_version=first, status=IngestStatus.DONE, section_count=4, page_count=2
    )
    newest_of_second = IngestJob.objects.create(document_version=second)

    body = client.get(document_url(document_id)).json()

    old, new = body["versions"]
    assert set(old["ingest"]) == INGEST_FIELDS
    assert old["ingest"]["id"] == newest_of_first.pk
    assert old["ingest"]["status"] == "done"
    assert (old["ingest"]["section_count"], old["ingest"]["page_count"]) == (4, 2)
    assert new["ingest"]["id"] == newest_of_second.pk
    assert new["ingest"]["status"] == "queued"
    assert body["latest_version"]["ingest"] == new["ingest"]


def test_device_list_shows_the_job_of_the_newest_version(media_root: Path) -> None:
    device = make_device()
    _, (first, second) = two_versions(client_for("manage"), device)
    IngestJob.objects.create(document_version=first, status=IngestStatus.DONE)
    failed = IngestJob.objects.create(
        document_version=second,
        status=IngestStatus.FAILED,
        step=IngestStep.CONVERT,
        error_code=IngestErrorCode.DOCLING_UNAVAILABLE,
        error_detail="docling-serve refused the connection",
    )

    [item] = client_for("read").get(documents_url(device)).json()

    ingest = item["latest_version"]["ingest"]
    assert ingest["id"] == failed.pk
    assert ingest["status"] == "failed"
    assert ingest["step"] == "convert"
    assert ingest["error_code"] == "docling_unavailable"
    # The cleaned detail is for every role (E-57).
    assert ingest["error_detail"] == "docling-serve refused the connection"
    assert ingest["partly_converted"] is False


def test_partial_conversion_is_marked(media_root: Path) -> None:
    created = upload(client_for("manage"), make_device(), b"edition 1").json()
    version = DocumentVersion.objects.get(pk=created["version"]["id"])
    # The note exactly as the ingest flow writes it after partial_success (046).
    note = pipeline._partial_detail(
        (
            ConversionErrorItem(
                component_type="model", module_name="ocr", error_message="x", page_no=3
            ),
        )
    )
    IngestJob.objects.create(document_version=version, status=IngestStatus.DONE, error_detail=note)

    ingest = (
        client_for("read")
        .get(document_url(created["document"]["id"]))
        .json()["latest_version"]["ingest"]
    )

    assert note.startswith(PARTIAL_DETAIL_PREFIX)
    assert ingest["status"] == "done"
    assert ingest["partly_converted"] is True
    assert ingest["error_detail"] == note


def test_job_after_upload_shows_in_the_detail(
    media_root: Path, django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks
) -> None:
    client = client_for("manage")

    with django_capture_on_commit_callbacks(execute=True):
        created = upload(client, make_device(), b"%PDF-1.7 manual\n").json()

    detail = client.get(document_url(created["document"]["id"])).json()
    assert detail["latest_version"]["ingest"]["status"] == "queued"
    assert detail["latest_version"]["ingest"]["id"] == IngestJob.objects.get().pk


def ingest_queries(queries: CaptureQueriesContext) -> list[str]:
    return [
        query["sql"] for query in queries.captured_queries if "ingest_ingestjob" in query["sql"]
    ]


@pytest.mark.parametrize("url_of", ["list", "detail"])
def test_ingest_state_costs_one_query(media_root: Path, url_of: str) -> None:
    device = make_device()
    client = client_for("read")

    def count(document_id: int) -> tuple[int, list[str]]:
        url = documents_url(device) if url_of == "list" else document_url(document_id)
        with CaptureQueriesContext(connection) as queries:
            assert client.get(url).status_code == 200
        return len(queries), ingest_queries(queries)

    first = create_document(device, a_file(b"doc 0"), "Doc 0", DocumentKind.DOCUMENT, None)
    IngestJob.objects.create(document_version=first.version, status=IngestStatus.DONE)
    few, few_ingest = count(first.document.pk)
    for number in range(1, 6):
        result = create_document(
            device, a_file(f"doc {number}".encode()), f"Doc {number}", DocumentKind.DOCUMENT, None
        )
        newer = add_version(result.document, a_file(f"doc {number} v2".encode()), None)
        for version in (result.version, newer.version, newer.version):
            IngestJob.objects.create(document_version=version, status=IngestStatus.FAILED)
        add_version(first.document, a_file(f"doc 0 v{number + 1}".encode()), None)
    many, many_ingest = count(first.document.pk)

    assert many == few
    assert len(few_ingest) == len(many_ingest) == 1


# --- duplicates -------------------------------------------------------------


def test_same_content_as_newest_version_is_409(media_root: Path) -> None:
    client = client_for("manage")
    first = upload(client, make_device(), b"same bytes").json()

    response = client.post(
        versions_url(first["document"]["id"]),
        {"file": a_file(b"same bytes", "renamed.pdf")},
        format="multipart",
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "duplicate_version"
    assert body["existing_version"]["id"] == first["version"]["id"]
    assert body["existing_version"]["number"] == 1
    assert "version 1" in body["detail"]
    assert DocumentVersion.objects.count() == 1


def test_same_content_on_another_device_is_accepted_with_a_hint(media_root: Path) -> None:
    client = client_for("manage")
    first_device = make_device("dps-plc")
    second_device = make_device("hbw-plc")
    first = upload(client, first_device, b"shared manual", title="Manual").json()

    response = upload(client, second_device, b"shared manual", title="Same manual")

    assert response.status_code == 201
    assert response.json()["duplicates"] == [
        {
            "device": first_device.pk,
            "device_key": "dps-plc",
            "device_name": "Device dps-plc",
            "document": first["document"]["id"],
            "document_title": "Manual",
            "version": first["version"]["id"],
            "version_number": 1,
        }
    ]
    # The content is stored once.
    assert len(files_below(media_root / "sha256")) == 1


# --- errors -----------------------------------------------------------------


def test_configuration_is_refused_with_400(media_root: Path) -> None:
    response = upload(client_for("manage"), make_device(), b"password=x", kind="configuration")

    assert response.status_code == 400
    assert "Configuration files are not accepted" in response.json()["kind"][0]
    assert not Document.objects.exists()
    assert files_below(media_root) == []


@pytest.mark.parametrize("kind", ["manual", "Document"])
def test_unknown_kind_is_refused_with_400(media_root: Path, kind: str) -> None:
    response = upload(client_for("manage"), make_device(), b"x", kind=kind)

    assert response.status_code == 400
    assert "kind" in response.json()


def test_missing_file_is_400(media_root: Path) -> None:
    response = client_for("manage").post(
        documents_url(make_device()), {"title": "no file"}, format="multipart"
    )

    assert response.status_code == 400
    assert "file" in response.json()


def test_json_upload_is_415(media_root: Path) -> None:
    response = client_for("manage").post(documents_url(make_device()), {}, format="json")

    assert response.status_code == 415


@pytest.mark.parametrize("method", ["get", "post"])
def test_unknown_device_is_404(media_root: Path, method: str) -> None:
    client = client_for("manage")
    url = documents_url(999_999)

    if method == "get":
        response = client.get(url)
    else:
        response = client.post(url, {"file": a_file(b"x")}, format="multipart")

    assert response.status_code == 404
    assert not Document.objects.exists()


def test_unknown_document_and_version_are_404(media_root: Path) -> None:
    client = client_for("manage")

    assert client.get(document_url(999_999)).status_code == 404
    assert (
        client.post(versions_url(999_999), {"file": a_file(b"x")}, format="multipart").status_code
        == 404
    )
    assert client.get(download_url(999_999)).status_code == 404


# --- rights -----------------------------------------------------------------


@pytest.fixture
def stored_version(media_root: Path) -> DocumentVersion:
    result = create_document(
        make_device(), a_file(b"stored content"), "Manual", DocumentKind.DOCUMENT, None
    )
    return result.version


def test_anonymous_requests_are_refused(stored_version: DocumentVersion) -> None:
    client = APIClient()
    document_id = stored_version.document.pk
    device_id = stored_version.document.device.pk

    assert client.get(documents_url(device_id)).status_code == 403
    assert (
        client.post(
            documents_url(device_id), {"file": a_file(b"x")}, format="multipart"
        ).status_code
        == 403
    )
    assert client.get(document_url(document_id)).status_code == 403
    assert (
        client.post(
            versions_url(document_id), {"file": a_file(b"x")}, format="multipart"
        ).status_code
        == 403
    )
    assert client.get(download_url(stored_version.pk)).status_code == 403


def test_role_read_may_download_but_not_upload(stored_version: DocumentVersion) -> None:
    client = client_for("read")
    document_id = stored_version.document.pk
    device_id = stored_version.document.device.pk

    assert client.get(documents_url(device_id)).status_code == 200
    assert client.get(document_url(document_id)).status_code == 200
    download = client.get(download_url(stored_version.pk))
    assert download.status_code == 200
    assert body_of(download) == b"stored content"

    new_file = client.post(documents_url(device_id), {"file": a_file(b"x")}, format="multipart")
    new_version = client.post(versions_url(document_id), {"file": a_file(b"y")}, format="multipart")
    assert new_file.status_code == 403
    assert new_version.status_code == 403
    assert Document.objects.count() == 1
    assert DocumentVersion.objects.count() == 1


def test_csrf_token_is_required_for_a_signed_in_upload(media_root: Path) -> None:
    client = APIClient(enforce_csrf_checks=True)
    manager = make_user("manage")
    assert manager is not None
    client.force_login(manager)
    client.get("/")
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    device = make_device()

    without = client.post(documents_url(device), {"file": a_file(b"one")}, format="multipart")
    with_token = client.post(
        documents_url(device),
        {"file": a_file(b"one")},
        format="multipart",
        headers={"X-CSRFToken": token},
    )

    assert without.status_code == 403
    assert "CSRF" in without.json()["detail"]
    assert with_token.status_code == 201
    assert Document.objects.count() == 1


# --- download ---------------------------------------------------------------


def test_download_returns_the_same_bytes(media_root: Path) -> None:
    content = bytes(range(256)) * 1000
    client = client_for("manage")
    created = upload(client, make_device(), content, file=a_file(content, "dump.bin")).json()

    response = client.get(download_url(created["version"]["id"]))

    assert response.status_code == 200
    data = body_of(response)
    assert hashlib.sha256(data).hexdigest() == created["version"]["sha256"]
    assert data == content
    assert response["Content-Length"] == str(len(content))


def test_download_headers_of_a_pdf(media_root: Path) -> None:
    client = client_for("manage")
    created = upload(client, make_device(), b"%PDF-1.7 test").json()

    response = client.get(download_url(created["version"]["id"]))

    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == 'attachment; filename="manual.pdf"'
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Content-Security-Policy"] == "sandbox"


@pytest.mark.parametrize(
    ("name", "content_type", "content"),
    [
        ("page.html", "text/html", b"<script>alert(document.cookie)</script>"),
        (
            "drawing.svg",
            "image/svg+xml",
            b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>',
        ),
        ("data.xml", "application/xhtml+xml", b"<html><script/></html>"),
    ],
)
def test_active_content_is_delivered_as_octet_stream_attachment(
    media_root: Path, name: str, content_type: str, content: bytes
) -> None:
    client = client_for("manage")
    created = upload(client, make_device(), content, file=a_file(content, name, content_type))
    assert created.json()["version"]["content_type"] == content_type

    response = client.get(download_url(created.json()["version"]["id"]))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/octet-stream"
    assert response["Content-Disposition"] == f'attachment; filename="{name}"'
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Content-Security-Policy"] == "sandbox"
    assert body_of(response) == content


def test_download_ignores_the_accept_header(stored_version: DocumentVersion) -> None:
    response = client_for("read").get(
        download_url(stored_version.pk), headers={"Accept": "application/octet-stream"}
    )

    assert response.status_code == 200


def test_file_name_with_path_and_control_characters_is_cleaned(media_root: Path) -> None:
    client = client_for("manage")
    device = make_device()
    body = multipart_body("../../etc/sub\\dir\\re\x01port\x7f.pdf", b"report", "application/pdf")

    created = post_multipart(client, documents_url(device), body)

    assert created.status_code == 201
    version = created.json()["version"]
    assert version["original_filename"] == "report.pdf"
    response = client.get(download_url(version["id"]))
    assert response["Content-Disposition"] == 'attachment; filename="report.pdf"'


def test_stored_name_is_cleaned_again_on_download(stored_version: DocumentVersion) -> None:
    # A row written past the services (admin, shell) with a raw name.
    raw = DocumentVersion.objects.create(
        document=stored_version.document,
        number=2,
        blob_key=stored_version.blob_key,
        sha256=stored_version.sha256,
        size=stored_version.size,
        content_type="text/plain",
        original_filename='C:\\dir/../in"ject\r\nX-Evil: 1.txt',
    )

    response = client_for("read").get(download_url(raw.pk))

    assert response.status_code == 200
    assert response["Content-Disposition"] == r'attachment; filename="in\"jectX-Evil: 1.txt"'
    assert "X-Evil" not in response.headers
    assert response["Content-Type"] == "text/plain"


def test_non_ascii_file_name_is_encoded_after_rfc_5987(media_root: Path) -> None:
    client = client_for("manage")
    name = "Handbuch Ölpumpe.pdf"
    created = upload(client, make_device(), b"oil", file=a_file(b"oil", name)).json()

    response = client.get(download_url(created["version"]["id"]))

    assert response["Content-Disposition"] == (
        "attachment; filename*=utf-8''Handbuch%20%C3%96lpumpe.pdf"
    )


# --- size limit -------------------------------------------------------------


class RecordingTemporaryFileUploadHandler(TemporaryFileUploadHandler):
    """Writes every file part to disk and remembers the temporary paths."""

    paths: ClassVar[list[Path]] = []

    def new_file(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401 - as in Django
        super().new_file(*args, **kwargs)
        RecordingTemporaryFileUploadHandler.paths.append(Path(self.file.temporary_file_path()))


@pytest.fixture
def upload_tmp(tmp_path: Path, settings: Settings) -> Path:
    """Django's temporary upload folder for one test; every file part goes to disk."""
    directory = tmp_path / "upload-tmp"
    directory.mkdir()
    settings.FILE_UPLOAD_TEMP_DIR = str(directory)
    settings.FILE_UPLOAD_MAX_MEMORY_SIZE = 0
    settings.FILE_UPLOAD_HANDLERS = [
        f"{RecordingTemporaryFileUploadHandler.__module__}.RecordingTemporaryFileUploadHandler"
    ]
    RecordingTemporaryFileUploadHandler.paths = []
    return directory


LIMIT = 100_000


def post_raw(client: APIClient, device: Device, content: bytes) -> _MonkeyPatchedResponse:
    body = multipart_body("big.bin", content, "application/octet-stream")
    return post_multipart(client, documents_url(device), body)


def assert_nothing_left(media_root: Path, upload_tmp: Path) -> None:
    assert files_below(upload_tmp) == []
    assert files_below(media_root) == []
    assert not Document.objects.exists()


def test_file_at_the_limit_is_accepted(
    media_root: Path, upload_tmp: Path, settings: Settings
) -> None:
    settings.TWOX_UPLOAD_MAX_BYTES = LIMIT

    response = post_raw(client_for("manage"), make_device(), b"x" * LIMIT)

    assert response.status_code == 201
    assert response.json()["version"]["size"] == LIMIT
    # The part went through a temporary file, which is gone again.
    assert RecordingTemporaryFileUploadHandler.paths
    assert files_below(upload_tmp) == []


def test_file_just_over_the_limit_is_stopped_while_streaming(
    media_root: Path, upload_tmp: Path, settings: Settings
) -> None:
    settings.TWOX_UPLOAD_MAX_BYTES = LIMIT

    response = post_raw(client_for("manage"), make_device(), b"x" * (LIMIT + 1))

    assert response.status_code == 413
    assert str(LIMIT) in response.json()["detail"]
    # Django had started a temporary file; stopping the upload deleted it.
    assert len(RecordingTemporaryFileUploadHandler.paths) == 1
    assert not RecordingTemporaryFileUploadHandler.paths[0].exists()
    assert_nothing_left(media_root, upload_tmp)


def test_body_just_over_the_limit_is_refused_before_parsing(
    media_root: Path, upload_tmp: Path, settings: Settings
) -> None:
    settings.TWOX_UPLOAD_MAX_BYTES = LIMIT
    client = client_for("manage")
    device = make_device()
    allowed = LIMIT + MULTIPART_OVERHEAD_BYTES
    framing = len(multipart_body("big.bin", b"", "application/octet-stream"))
    content = b"x" * (allowed - framing + 1)
    body = multipart_body("big.bin", content, "application/octet-stream")
    assert len(body) == allowed + 1

    response = post_multipart(client, documents_url(device), body)

    assert response.status_code == 413
    assert str(LIMIT) in response.json()["detail"]
    # Refused on the declared length: the parser never opened a file.
    assert RecordingTemporaryFileUploadHandler.paths == []
    assert_nothing_left(media_root, upload_tmp)


def test_limit_holds_when_the_csrf_check_reads_the_form(
    media_root: Path, upload_tmp: Path, settings: Settings
) -> None:
    # With a session, DRF's CSRF check parses the form before the view runs.
    settings.TWOX_UPLOAD_MAX_BYTES = LIMIT
    client = APIClient(enforce_csrf_checks=True)
    manager = make_user("manage")
    assert manager is not None
    client.force_login(manager)
    client.get("/")
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    body = multipart_body("big.bin", b"x" * (LIMIT + 1), "application/octet-stream")

    response = post_multipart(
        client, documents_url(make_device()), body, headers={"X-CSRFToken": token}
    )

    assert response.status_code == 413
    assert len(RecordingTemporaryFileUploadHandler.paths) == 1
    assert_nothing_left(media_root, upload_tmp)


def test_new_version_over_the_limit_is_413(
    stored_version: DocumentVersion, upload_tmp: Path, settings: Settings
) -> None:
    settings.TWOX_UPLOAD_MAX_BYTES = LIMIT
    body = multipart_body("big.bin", b"y" * (LIMIT + 1), "application/octet-stream")

    response = post_multipart(client_for("manage"), versions_url(stored_version.document.pk), body)

    assert response.status_code == 413
    assert files_below(upload_tmp) == []
    assert DocumentVersion.objects.count() == 1


# --- schema -----------------------------------------------------------------


def test_schema_types_uploads_and_download() -> None:
    schema, stderr = generate_schema()
    paths: dict[str, Any] = schema["paths"]

    def content_of(operation: dict[str, Any]) -> dict[str, Any]:
        content: dict[str, Any] = operation["requestBody"]["content"]
        return content

    assert stderr == ""
    create = paths["/api/v1/devices/{device_id}/documents/"]["post"]
    version = paths["/api/v1/documents/{document_id}/versions/"]["post"]
    download = paths["/api/v1/document-versions/{version_id}/download/"]["get"]
    assert list(content_of(create)) == ["multipart/form-data"]
    assert list(content_of(version)) == ["multipart/form-data"]
    assert set(create["responses"]) >= {"201", "400", "403", "404", "413"}
    assert set(version["responses"]) >= {"201", "403", "404", "409", "413"}
    assert download["responses"]["200"]["content"]["*/*"]["schema"] == {
        "type": "string",
        "format": "binary",
    }
    components = schema["components"]["schemas"]
    assert components["DocumentUpload"]["properties"]["file"]["format"] == "binary"
    assert components["VersionUpload"]["properties"]["file"]["format"] == "binary"
    assert components["DocumentUpload"]["required"] == ["file"]
