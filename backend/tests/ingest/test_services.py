"""Asking for the ingestion of a version (twox.ingest.services, work order 049).

No test reaches the broker, Docling or the model service: the autouse
fixture ``ingest_messages`` (tests/conftest.py) records the messages, and
``isolated_services`` fails every test that reaches a real client.
"""

import io
import logging
import zipfile
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks, Settings

from tests.conftest import IngestMessages
from tests.files.helpers import client_for, make_device
from tests.ingest.fake_converter import isolated_services, make_version
from twox.accounts.models import User
from twox.files.models import Document, DocumentKind, DocumentVersion
from twox.ingest import services, tasks
from twox.ingest.models import IngestErrorCode, IngestJob, IngestStatus
from twox.ingest.services import (
    CONTENT_MISSING_DETAIL,
    IngestAlreadyActiveError,
    IngestNotAllowedError,
    request_ingest,
)

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("isolated_services")]

CONVERT = "twox.ingest.convert"
PDF = b"%PDF-1.7\n%stand-in, never converted\n"
MARKDOWN = b"# SFTP backup\n\nStand-in.\n"


def docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        archive.writestr("word/document.xml", "<document/>")
    return buffer.getvalue()


def pdf_upload(content: bytes) -> SimpleUploadedFile:
    return SimpleUploadedFile("BetrSichV.pdf", content, content_type="application/pdf")


def zip_archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("manual.pdf", PDF)
    return buffer.getvalue()


@pytest.fixture
def manager() -> User:
    return User.objects.create_user("ingest-manager")


def configuration_version() -> DocumentVersion:
    # No service creates a configuration in M2; a row made otherwise is refused.
    document = Document.objects.create(
        device=make_device("router"), title="Router", kind=DocumentKind.CONFIGURATION
    )
    return make_version(b"option=1\n", filename="router.conf", document=document)


# --- Queued -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("BetrSichV.pdf", PDF),
        ("manual.docx", docx()),
        ("sftp-backup.md", MARKDOWN),
    ],
)
def test_supported_file_is_queued_and_sent_after_the_commit(
    filename: str,
    content: bytes,
    manager: User,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version = make_version(content, filename=filename)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        job = request_ingest(version, manager)
        # Nothing leaves before the commit.
        assert ingest_messages.sent == []

    job.refresh_from_db()
    assert len(callbacks) == 1
    assert ingest_messages.sent == [(CONVERT, (job.pk,))]
    assert job.status == IngestStatus.QUEUED
    assert job.document_version == version
    assert job.requested_by == manager
    assert (job.error_code, job.error_detail, job.step) == ("", "", "")
    assert job.started_at is None
    assert job.finished_at is None


def test_declared_content_type_does_not_matter(
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version = make_version(b"key: value\n", filename="plant.yaml", content_type="application/pdf")

    with django_capture_on_commit_callbacks(execute=True):
        job = request_ingest(version, None)

    assert job.status == IngestStatus.SKIPPED
    assert ingest_messages.sent == []


@pytest.mark.parametrize("ai_enabled", [True, False], ids=["ai-on", "ai-off"])
def test_only_convert_is_sent_with_and_without_ai(
    ai_enabled: bool,
    settings: Settings,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    # E-59: ingestion works without AI; nothing here depends on the switch.
    settings.TWOX_AI_ENABLED = ai_enabled

    with django_capture_on_commit_callbacks(execute=True):
        job = request_ingest(make_version(), None)

    assert job.status == IngestStatus.QUEUED
    assert ingest_messages.names() == [CONVERT]


# --- Skipped and failed -------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("notes.txt", b"plain text"),
        ("export.json", b'{"user": "admin"}'),
        ("project.xml", b"<?xml version='1.0'?><project/>"),
        ("plant.yaml", b"key: value\n"),
        ("router.conf", b"option=1\n"),
        ("readme.rst", b"Title\n=====\n"),
        ("page.html", b"<html><body>x</body></html>"),
        ("archive.zip", zip_archive()),
        ("manual.pdf", b"option=1\n"),
    ],
)
def test_unsupported_file_is_skipped_without_docling(
    filename: str,
    content: bytes,
    manager: User,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version = make_version(content, filename=filename)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        job = request_ingest(version, manager)

    job.refresh_from_db()
    assert callbacks == []
    assert ingest_messages.sent == []
    assert job.status == IngestStatus.SKIPPED
    assert job.error_code == IngestErrorCode.UNSUPPORTED_FORMAT
    assert job.requested_by == manager
    assert job.finished_at is not None
    assert job.started_at is None
    suffix = filename.rsplit(".", 1)[1]
    assert f".{suffix}" in job.error_detail
    assert "ingested are PDF, DOCX, XLSX, PPTX, Markdown" in job.error_detail
    # The detail is shown to every role: never the file name.
    assert filename not in job.error_detail


def test_skipped_job_does_not_block_a_new_request() -> None:
    version = make_version(b"plain", filename="notes.txt")

    first = request_ingest(version, None)
    second = request_ingest(version, None)

    assert (first.status, second.status) == (IngestStatus.SKIPPED, IngestStatus.SKIPPED)
    assert first.pk != second.pk


def test_missing_content_gives_a_failed_job(
    isolated_services: Path,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version = make_version()
    (isolated_services / version.blob_key).unlink()

    with django_capture_on_commit_callbacks(execute=True):
        job = request_ingest(version, None)

    assert job.status == IngestStatus.FAILED
    assert job.error_code == IngestErrorCode.CONTENT_MISSING
    assert job.error_detail == CONTENT_MISSING_DETAIL
    assert job.finished_at is not None
    assert ingest_messages.sent == []


# --- Refused ------------------------------------------------------------------------


@pytest.mark.parametrize("status", [IngestStatus.QUEUED, IngestStatus.RUNNING])
def test_second_request_while_a_job_is_active_is_refused(
    status: IngestStatus,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version = make_version()
    active = IngestJob.objects.create(document_version=version, status=status)

    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(IngestAlreadyActiveError) as excinfo,
    ):
        request_ingest(version, None)

    assert excinfo.value.job == active
    assert IngestJob.objects.filter(document_version=version).count() == 1
    assert ingest_messages.sent == []


@pytest.mark.parametrize("status", [IngestStatus.DONE, IngestStatus.FAILED, IngestStatus.SKIPPED])
def test_finished_job_does_not_block_a_new_request(status: IngestStatus) -> None:
    version = make_version()
    IngestJob.objects.create(document_version=version, status=status)

    job = request_ingest(version, None)

    assert job.status == IngestStatus.QUEUED
    assert IngestJob.objects.filter(document_version=version).count() == 2


def test_concurrent_request_is_refused_by_the_constraint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The other request inserted its job between the check and the insert.
    version = make_version()
    other = IngestJob.objects.create(document_version=version)
    real_active_job = services.active_job
    calls: list[int] = []

    def active_job_missed_once(checked: DocumentVersion) -> IngestJob | None:
        calls.append(checked.pk)
        return None if len(calls) == 1 else real_active_job(checked)

    monkeypatch.setattr(services, "active_job", active_job_missed_once)

    with pytest.raises(IngestAlreadyActiveError) as excinfo:
        request_ingest(version, None)

    assert excinfo.value.job == other
    assert len(calls) == 2
    # The surrounding transaction is still usable.
    assert IngestJob.objects.filter(document_version=version).count() == 1


def test_configuration_is_never_ingested(ingest_messages: IngestMessages) -> None:
    version = configuration_version()

    with pytest.raises(IngestNotAllowedError) as excinfo:
        request_ingest(version, None)

    assert excinfo.value.version == version
    assert not IngestJob.objects.exists()
    assert ingest_messages.sent == []


# --- Sending ------------------------------------------------------------------------


def test_failed_send_leaves_the_job_queued_and_warns(
    ingest_messages: IngestMessages,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    ingest_messages.error = ConnectionRefusedError("broker down")

    with (
        caplog.at_level(logging.WARNING, logger="twox.ingest.services"),
        django_capture_on_commit_callbacks(execute=True),
    ):
        job = request_ingest(make_version(), None)

    job.refresh_from_db()
    assert job.status == IngestStatus.QUEUED
    assert ingest_messages.sent == []
    assert f"job {job.pk} could not be sent" in caplog.text
    assert "ingest_versions --stuck" in caplog.text


def test_send_keeps_no_result_and_retries_briefly(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, dict[str, object]]] = []

    def apply_async(args: object, **options: object) -> None:
        calls.append((args, options))

    monkeypatch.setattr(tasks.convert, "apply_async", apply_async)

    assert services.send_convert(42) is True
    # No result is kept: the sender never waits for the result store (Valkey).
    assert calls == [
        (
            (42,),
            {"ignore_result": True, "retry": True, "retry_policy": services.SEND_RETRY_POLICY},
        )
    ]
    assert services.SEND_RETRY_POLICY["max_retries"] <= 3


def test_rolled_back_transaction_sends_nothing(
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version = make_version()

    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        request_ingest(version, None)
        raise RuntimeError("rolled back")

    assert callbacks == []
    assert not IngestJob.objects.exists()
    assert ingest_messages.sent == []


# --- Upload through the API ---------------------------------------------------------


def test_upload_through_the_api_creates_exactly_one_job_after_the_commit(
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    client = client_for("manage")
    device = make_device()

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            f"/api/v1/devices/{device.pk}/documents/",
            {"file": pdf_upload(PDF), "title": "Manual"},
            format="multipart",
        )

    assert response.status_code == 201
    version = DocumentVersion.objects.get(pk=response.json()["version"]["id"])
    job = IngestJob.objects.get()
    assert job.document_version == version
    assert job.status == IngestStatus.QUEUED
    assert job.requested_by is not None
    assert job.requested_by.username == "manage"
    assert ingest_messages.sent == [(CONVERT, (job.pk,))]

    with django_capture_on_commit_callbacks(execute=True):
        second = client.post(
            f"/api/v1/documents/{version.document_id}/versions/",
            {"file": pdf_upload(PDF + b"%edition 2\n")},
            format="multipart",
        )

    assert second.status_code == 201
    jobs = list(IngestJob.objects.order_by("pk"))
    assert len(jobs) == 2
    assert jobs[1].document_version_id == second.json()["version"]["id"]
    assert ingest_messages.sent == [(CONVERT, (jobs[0].pk,)), (CONVERT, (jobs[1].pk,))]


def test_refused_upload_through_the_api_creates_no_job(
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    client = client_for("manage")
    device = make_device()
    with django_capture_on_commit_callbacks(execute=True):
        first = client.post(
            f"/api/v1/devices/{device.pk}/documents/",
            {"file": pdf_upload(PDF)},
            format="multipart",
        )
    sent_before = list(ingest_messages.sent)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        duplicate = client.post(
            f"/api/v1/documents/{first.json()['document']['id']}/versions/",
            {"file": pdf_upload(PDF)},
            format="multipart",
        )

    assert duplicate.status_code == 409
    assert callbacks == []
    assert IngestJob.objects.count() == 1
    assert ingest_messages.sent == sent_before
