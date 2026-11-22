"""Asking for the ingestion of a document version: the one way for uploads and commands.

:func:`request_ingest` creates an :class:`~twox.ingest.models.IngestJob` for
a version and, once the database transaction is committed, sends the task
``twox.ingest.convert`` (:mod:`twox.ingest.tasks`). The upload services of
``twox.files`` call it for every new version of a document; the command
``ingest_versions`` calls it for existing, failed or stuck versions.

Rules (E-57, guard rail 5):

- Only versions of documents of the kind ``document`` are ingested; a
  configuration is refused with :class:`IngestNotAllowedError`. Access data
  in configurations are never ingested before redaction exists (M5).
- A version with a ``queued`` or ``running`` job gets no second one
  (:class:`IngestAlreadyActiveError`).
- A file outside the fixed format list (:mod:`twox.ingest.formats`) gets a
  job that is ``skipped`` at once with the error code ``unsupported_format``;
  Docling never sees it.
- Stored content that is missing gives a ``failed`` job (``content_missing``).
- If the task cannot be sent (broker down), the job stays ``queued`` and a
  warning goes to the server log; ``ingest_versions --stuck`` sends it again
  later. The caller never sees that error.

Ingestion works the same with and without the AI features (E-59): only
``convert`` is sent here.
"""

import logging
from functools import partial
from typing import Any, Final

from django.db import IntegrityError, transaction
from django.utils import timezone

from twox.accounts.models import User
from twox.files.models import DocumentKind, DocumentVersion
from twox.files.storage import BlobNotFoundError, get_blob_storage
from twox.ingest import tasks
from twox.ingest.formats import SUPPORTED_FORMATS_TEXT, FormatCheck, check_format
from twox.ingest.models import ACTIVE_STATUSES, IngestErrorCode, IngestJob, IngestStatus

logger = logging.getLogger(__name__)

#: Retries when the task is sent: short, so that an upload never waits long
#: for a broker that is down (the job stays queued then).
SEND_RETRY_POLICY: Final[dict[str, float]] = {
    "max_retries": 2,
    "interval_start": 0,
    "interval_step": 0.5,
    "interval_max": 1,
}

#: Detail of a job whose stored content is missing.
CONTENT_MISSING_DETAIL: Final = "the stored content is missing"


class IngestRequestError(Exception):
    """Base class of the errors of :func:`request_ingest`."""


class IngestAlreadyActiveError(IngestRequestError):
    """The version has a queued or running job already."""

    def __init__(self, job: IngestJob) -> None:
        self.job = job
        super().__init__(f"document version {job.document_version_id} has an active ingest job")


class IngestNotAllowedError(IngestRequestError):
    """The version belongs to a configuration, which is not ingested before M5."""

    def __init__(self, version: DocumentVersion) -> None:
        self.version = version
        super().__init__(
            f"document version {version.pk} is a configuration; configurations are not ingested"
        )


def active_job(version: DocumentVersion) -> IngestJob | None:
    """The ``queued`` or ``running`` job of the version, if there is one."""
    return IngestJob.objects.filter(document_version=version, status__in=ACTIVE_STATUSES).first()


def check_version_format(version: DocumentVersion) -> FormatCheck:
    """Check the stored content of the version against the format list.

    Raises :class:`~twox.files.storage.BlobNotFoundError` if the content is
    missing.
    """
    with get_blob_storage().open_blob(version.blob_key) as stream:
        return check_format(version.original_filename, stream)


def skipped_detail(check: FormatCheck) -> str:
    """The detail of a skipped job: the reason and the list of ingested formats."""
    return f"{check.reason}; ingested are {SUPPORTED_FORMATS_TEXT}"


def send_convert(job_id: int) -> bool:
    """Send ``twox.ingest.convert`` for the job; ``False`` (and a warning) if that fails."""
    try:
        tasks.convert.apply_async((job_id,), retry=True, retry_policy=SEND_RETRY_POLICY)
    except Exception:
        logger.warning(
            "ingest: job %s could not be sent to the task queue and stays queued; "
            "send it again with: manage.py ingest_versions --stuck <minutes> --commit",
            job_id,
            exc_info=True,
        )
        return False
    return True


def _job_fields(version: DocumentVersion) -> dict[str, Any]:
    """Status and error of the new job, from the format of the stored content."""
    try:
        check = check_version_format(version)
    except BlobNotFoundError:
        logger.warning("ingest: stored content of version %s is missing", version.pk)
        return {
            "status": IngestStatus.FAILED,
            "error_code": IngestErrorCode.CONTENT_MISSING,
            "error_detail": CONTENT_MISSING_DETAIL,
            "finished_at": timezone.now(),
        }
    if not check.supported:
        logger.info("ingest: version %s skipped: %s", version.pk, check.reason)
        return {
            "status": IngestStatus.SKIPPED,
            "error_code": IngestErrorCode.UNSUPPORTED_FORMAT,
            "error_detail": skipped_detail(check),
            "finished_at": timezone.now(),
        }
    return {"status": IngestStatus.QUEUED}


def request_ingest(version: DocumentVersion, user: User | None) -> IngestJob:
    """Create an ingest job for ``version`` and send it after the commit.

    ``user`` is stored as ``requested_by``. The job is ``queued`` for a
    supported format, ``skipped`` (``unsupported_format``) otherwise and
    ``failed`` (``content_missing``) without stored content; only a queued
    job is sent, by ``transaction.on_commit``. Inside a transaction the
    message leaves when the outermost transaction commits, and never if it
    rolls back.

    Raises :class:`IngestNotAllowedError` for a configuration and
    :class:`IngestAlreadyActiveError` if the version has an active job.
    """
    if version.document.kind != DocumentKind.DOCUMENT:
        raise IngestNotAllowedError(version)
    existing = active_job(version)
    if existing is not None:
        raise IngestAlreadyActiveError(existing)

    fields = _job_fields(version)
    try:
        with transaction.atomic():
            job = IngestJob.objects.create(document_version=version, requested_by=user, **fields)
            if job.status == IngestStatus.QUEUED:
                transaction.on_commit(partial(send_convert, job.pk))
    except IntegrityError as error:
        # Another request created the active job between the check and the insert.
        existing = active_job(version)
        if existing is None:
            raise
        raise IngestAlreadyActiveError(existing) from error
    return job
