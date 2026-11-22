"""Management command ingest_versions (work order 049).

The command runs inside the test transaction, so the messages it sends after
the commit are released with ``django_capture_on_commit_callbacks``; the
autouse fixture ``ingest_messages`` records them instead of sending.
"""

from datetime import timedelta
from io import StringIO
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks

from tests.accounts.users import make_user
from tests.conftest import IngestMessages
from tests.files.helpers import make_device
from tests.ingest.fake_converter import isolated_services, make_version
from twox.accounts.models import User
from twox.files.models import Document, DocumentKind, DocumentVersion
from twox.files.services import create_document
from twox.ingest.models import IngestErrorCode, IngestJob, IngestStatus

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("isolated_services")]

CONVERT = "twox.ingest.convert"
DRY_RUN = "Dry run: nothing was changed. Add --commit to start the jobs."
SAVED = "Saved."


@pytest.fixture
def manager() -> User:
    user = make_user("manage")
    assert user is not None
    return user


def counts(
    versions: int,
    *,
    created: int = 0,
    skipped: int = 0,
    content_missing: int = 0,
    running: int = 0,
    stuck: int = 0,
) -> list[str]:
    return [
        f"versions: {versions}",
        f"created: {created}",
        f"skipped (unsupported format): {skipped}",
        f"failed (content missing): {content_missing}",
        f"running (left alone): {running}",
        f"stuck (set to failed and started again): {stuck}",
    ]


def run(*args: str) -> list[str]:
    stdout = StringIO()
    call_command("ingest_versions", *args, stdout=stdout)
    return stdout.getvalue().splitlines()


def text_version() -> DocumentVersion:
    return make_version(
        b"plain text", device="text", filename="notes.txt", content_type="text/plain"
    )


def pdf_version(device: str = "dps-plc", content: bytes | None = None) -> DocumentVersion:
    return make_version(content or f"%PDF-1.7 {device}\n".encode(), device=device)


def job(version: DocumentVersion, status: IngestStatus, minutes_ago: int = 0) -> IngestJob:
    created = IngestJob.objects.create(document_version=version, status=status)
    if minutes_ago:
        moment = timezone.now() - timedelta(minutes=minutes_ago)
        IngestJob.objects.filter(pk=created.pk).update(created_at=moment, updated_at=moment)
        created.refresh_from_db()
    return created


# --- --missing ----------------------------------------------------------------------


def test_missing_dry_run_counts_and_changes_nothing(
    manager: User,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    pdf_version("dps-plc")
    pdf_version("hbw-plc")
    text_version()
    done = pdf_version("vgr-plc")
    job(done, IngestStatus.DONE)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        out = run("--missing", "--user", manager.username)

    assert out == [*counts(3, created=2, skipped=1), DRY_RUN]
    assert IngestJob.objects.count() == 1
    assert callbacks == []
    assert ingest_messages.sent == []


def test_missing_commit_creates_the_jobs_and_a_second_run_finds_none(
    manager: User,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    first = pdf_version("dps-plc")
    second = pdf_version("hbw-plc")
    text = text_version()

    with django_capture_on_commit_callbacks(execute=True):
        out = run("--missing", "--user", manager.username, "--commit")

    assert out == [*counts(3, created=2, skipped=1), SAVED]
    queued = IngestJob.objects.filter(status=IngestStatus.QUEUED).order_by("document_version")
    assert [j.document_version for j in queued] == [first, second]
    assert {j.requested_by for j in IngestJob.objects.all()} == {manager}
    skipped = IngestJob.objects.get(document_version=text)
    assert (skipped.status, skipped.error_code) == (
        IngestStatus.SKIPPED,
        IngestErrorCode.UNSUPPORTED_FORMAT,
    )
    assert sorted(ingest_messages.sent) == sorted((CONVERT, (j.pk,)) for j in queued)

    with django_capture_on_commit_callbacks(execute=True):
        again = run("--missing", "--user", manager.username, "--commit")

    assert again == [*counts(0), SAVED]
    assert IngestJob.objects.count() == 3


def test_missing_content_is_counted(manager: User, isolated_services: Path) -> None:
    version = pdf_version()
    (isolated_services / version.blob_key).unlink()

    assert run("--missing", "--user", manager.username) == [
        *counts(1, content_missing=1),
        DRY_RUN,
    ]
    assert run("--missing", "--user", manager.username, "--commit") == [
        *counts(1, content_missing=1),
        SAVED,
    ]
    failed = IngestJob.objects.get()
    assert (failed.status, failed.error_code) == (
        IngestStatus.FAILED,
        IngestErrorCode.CONTENT_MISSING,
    )


def test_configurations_are_never_selected(manager: User) -> None:
    document = Document.objects.create(
        device=make_device("router"), title="Router", kind=DocumentKind.CONFIGURATION
    )
    make_version(b"option=1\n", filename="router.conf", document=document)

    assert run("--missing", "--all", "--user", manager.username, "--commit") == [
        *counts(0),
        SAVED,
    ]
    assert not IngestJob.objects.exists()


# --- --failed -----------------------------------------------------------------------


def test_failed_takes_versions_whose_newest_job_failed(
    manager: User,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    failed = pdf_version("dps-plc")
    job(failed, IngestStatus.FAILED, minutes_ago=5)
    recovered = pdf_version("hbw-plc")
    job(recovered, IngestStatus.FAILED, minutes_ago=10)
    job(recovered, IngestStatus.DONE, minutes_ago=5)
    skipped = text_version()
    job(skipped, IngestStatus.SKIPPED)
    pdf_version("vgr-plc")  # no job at all

    assert run("--failed", "--user", manager.username) == [*counts(1, created=1), DRY_RUN]
    with django_capture_on_commit_callbacks(execute=True):
        out = run("--failed", "--user", manager.username, "--commit")

    assert out == [*counts(1, created=1), SAVED]
    new = IngestJob.objects.get(status=IngestStatus.QUEUED)
    assert new.document_version == failed
    assert ingest_messages.sent == [(CONVERT, (new.pk,))]


# --- --stuck ------------------------------------------------------------------------


@pytest.mark.parametrize("status", [IngestStatus.QUEUED, IngestStatus.RUNNING])
def test_stuck_job_fails_with_timeout_and_is_started_again(
    status: IngestStatus,
    manager: User,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    stuck_version = pdf_version("dps-plc")
    stuck = job(stuck_version, status, minutes_ago=30)
    busy_version = pdf_version("hbw-plc")
    busy = job(busy_version, IngestStatus.RUNNING, minutes_ago=1)

    assert run("--stuck", "10", "--user", manager.username) == [
        *counts(1, created=1, stuck=1),
        DRY_RUN,
    ]
    stuck.refresh_from_db()
    assert stuck.status == status

    with django_capture_on_commit_callbacks(execute=True):
        out = run("--stuck", "10", "--user", manager.username, "--commit")

    assert out == [*counts(1, created=1, stuck=1), SAVED]
    stuck.refresh_from_db()
    assert stuck.status == IngestStatus.FAILED
    assert stuck.error_code == IngestErrorCode.TIMEOUT
    assert stuck.error_detail == (
        "no progress for at least 10 minutes; started again by ingest_versions"
    )
    assert stuck.finished_at is not None
    new = IngestJob.objects.get(document_version=stuck_version, status=IngestStatus.QUEUED)
    assert new.requested_by == manager
    assert ingest_messages.sent == [(CONVERT, (new.pk,))]
    busy.refresh_from_db()
    assert busy.status == IngestStatus.RUNNING
    assert IngestJob.objects.filter(document_version=busy_version).count() == 1


def test_failed_send_is_repaired_with_stuck_zero(
    manager: User,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    # The broker is down during the upload: the job stays queued.
    ingest_messages.error = ConnectionRefusedError("broker down")
    with django_capture_on_commit_callbacks(execute=True):
        result = create_document(
            make_device(),
            SimpleUploadedFile("BetrSichV.pdf", b"%PDF-1.7 upload\n", "application/pdf"),
            "Manual",
            DocumentKind.DOCUMENT,
            manager,
        )
    lost = IngestJob.objects.get()
    assert lost.status == IngestStatus.QUEUED
    assert ingest_messages.sent == []

    ingest_messages.error = None
    with django_capture_on_commit_callbacks(execute=True):
        out = run("--stuck", "0", "--user", manager.username, "--commit")

    assert out == [*counts(1, created=1, stuck=1), SAVED]
    lost.refresh_from_db()
    assert (lost.status, lost.error_code) == (IngestStatus.FAILED, IngestErrorCode.TIMEOUT)
    new = IngestJob.objects.get(status=IngestStatus.QUEUED)
    assert new.document_version == result.version
    assert ingest_messages.sent == [(CONVERT, (new.pk,))]


# --- --all and --version ------------------------------------------------------------


def test_all_creates_a_new_job_for_every_version_but_leaves_active_ones(
    manager: User,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    done = pdf_version("dps-plc")
    job(done, IngestStatus.DONE)
    fresh = pdf_version("hbw-plc")
    active = pdf_version("vgr-plc")
    running = job(active, IngestStatus.RUNNING)
    text_version()

    with django_capture_on_commit_callbacks(execute=True):
        out = run("--all", "--user", manager.username, "--commit")

    assert out == [*counts(4, created=2, skipped=1, running=1), SAVED]
    queued = IngestJob.objects.filter(status=IngestStatus.QUEUED)
    assert {j.document_version for j in queued} == {done, fresh}
    running.refresh_from_db()
    assert running.status == IngestStatus.RUNNING
    assert len(ingest_messages.sent) == 2


def test_version_selects_the_given_ids(
    manager: User,
    ingest_messages: IngestMessages,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    first = pdf_version("dps-plc")
    pdf_version("hbw-plc")
    third = pdf_version("vgr-plc")
    job(third, IngestStatus.DONE)

    with django_capture_on_commit_callbacks(execute=True):
        out = run(
            "--version",
            str(first.pk),
            "--version",
            str(third.pk),
            "--user",
            manager.username,
            "--commit",
        )

    assert out == [*counts(2, created=2), SAVED]
    queued = IngestJob.objects.filter(status=IngestStatus.QUEUED)
    assert {j.document_version for j in queued} == {first, third}
    assert len(ingest_messages.sent) == 2


def test_selections_are_combined_without_doubles(manager: User) -> None:
    failed = pdf_version("dps-plc")
    job(failed, IngestStatus.FAILED)
    missing = pdf_version("hbw-plc")

    out = run("--missing", "--failed", "--version", str(missing.pk), "--user", manager.username)

    assert out == [*counts(2, created=2), DRY_RUN]


def test_unknown_version_is_an_error(manager: User) -> None:
    version = pdf_version()

    with pytest.raises(CommandError, match="no document version 999999"):
        run("--version", "999999", "--version", str(version.pk), "--user", manager.username)

    assert not IngestJob.objects.exists()


def test_version_of_a_configuration_is_an_error(manager: User) -> None:
    document = Document.objects.create(
        device=make_device("router"), title="Router", kind=DocumentKind.CONFIGURATION
    )
    version = make_version(b"option=1\n", filename="router.conf", document=document)

    with pytest.raises(CommandError, match="Configurations are not ingested"):
        run("--version", str(version.pk), "--user", manager.username, "--commit")

    assert not IngestJob.objects.exists()


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--stuck", "-1"], id="negative-minutes"),
        pytest.param(["--stuck", "ten"], id="minutes-not-a-number"),
        pytest.param(["--version", "0"], id="version-zero"),
        pytest.param(["--version", "abc"], id="version-not-a-number"),
    ],
)
def test_invalid_numbers_are_errors(args: list[str], manager: User) -> None:
    with pytest.raises(CommandError):
        run(*args, "--user", manager.username)


# --- Account and options ------------------------------------------------------------


def test_a_selection_is_required(manager: User) -> None:
    pdf_version()

    with pytest.raises(CommandError, match="Choose at least one of"):
        run("--user", manager.username, "--commit")

    assert not IngestJob.objects.exists()


@pytest.mark.parametrize("kind", ["no_role", "read"])
def test_account_without_role_manage_is_refused(kind: str) -> None:
    user = make_user(kind)
    assert user is not None
    pdf_version()

    with pytest.raises(CommandError, match="does not have the role 'manage'"):
        run("--missing", "--user", user.username, "--commit")

    assert not IngestJob.objects.exists()


def test_unknown_and_inactive_accounts_are_refused(manager: User) -> None:
    pdf_version()
    with pytest.raises(CommandError, match="no active account 'nobody'"):
        run("--missing", "--user", "nobody", "--commit")

    manager.is_active = False
    manager.save()
    with pytest.raises(CommandError, match="no active account"):
        run("--missing", "--user", manager.username, "--commit")

    assert not IngestJob.objects.exists()


def test_user_is_required() -> None:
    with pytest.raises(CommandError, match="--user"):
        run("--missing")
