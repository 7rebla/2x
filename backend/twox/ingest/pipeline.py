"""The ingest flow of one job: convert with Docling or reuse an answer, store it, build sections.

The logic of the two Celery tasks in :mod:`twox.ingest.tasks`, without Celery:
every function here runs in a plain test with a stand-in converter. Each call
does one short step and says when the next status query is due; it never
sleeps and never waits for Docling (E-55).

:func:`convert` (task ``twox.ingest.convert``)
    Claims a ``queued`` job (``running``, step ``convert``). If a ``done`` job
    of any version with the same content (SHA-256) holds a stored Docling
    answer, that answer is reused and the sections are built at once.
    Otherwise the content is uploaded to Docling under a neutral name
    (``version-<id><suffix>``) and a status query is scheduled.

:func:`poll` (task ``twox.ingest.poll``)
    Asks Docling once about the task of a ``running`` job. While the task is
    pending or started, the next query is scheduled with a growing delay.
    When it has finished, the answer is streamed to a temporary file, stored
    in the blob storage at once (``result_blob_key``) and only then read; the
    sections replace those of the version in one transaction and the job is
    ``done``. A job without Docling task (first upload failed, or Docling
    lost the task) is uploaded again from here.

Errors end as ``failed`` with a fixed error code and a cleaned detail
(:func:`sanitize_error_detail`); the raw text goes to the server log only.
Docling being unreachable and a lost Docling task are retried with a growing
delay, at most ``TWOX_INGEST_MAX_RETRIES`` times per job (the counter is
``attempts``). The deadline ``TWOX_INGEST_TIMEOUT_SECONDS`` counts from the
first ``started`` reported by Docling; waiting in Docling's own queue does
not count.

Both entry points are idempotent: a job that is not in the expected state is
left alone, and the last step locks the job row, so a duplicate or
redelivered message changes nothing.

The flow is the same with and without the AI features (E-59): it ends after
the sections, never schedules an embedding task and never contacts the model
service. Work order 048 adds the embedding step behind ``TWOX_AI_ENABLED``.

Document contents are data, not instructions: nothing here interprets them.
"""

import ipaddress
import json
import logging
import mimetypes
import re
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import IO, Any, BinaryIO, Final, cast

from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from twox.files.models import DocumentVersion
from twox.files.storage import BlobNotFoundError, BlobStorage, get_blob_storage
from twox.ingest.docling import (
    ConversionErrorItem,
    DoclingConversionError,
    DoclingRejectedError,
    DoclingTaskLostError,
    DoclingUnavailableError,
    DocumentConverter,
    TaskStatus,
    get_document_converter,
    guess_content_type,
    load_result,
)
from twox.ingest.models import (
    ERROR_DETAIL_MAX_LENGTH,
    IngestErrorCode,
    IngestJob,
    IngestStatus,
    IngestStep,
    Section,
    section_rows,
)
from twox.ingest.sections import UnsupportedDocumentError, build_sections

logger = logging.getLogger(__name__)

#: Largest primary key of a job (PostgreSQL ``bigint``).
MAX_JOB_ID: Final = 2**63 - 1
#: Prefix of the neutral file name sent to Docling.
NEUTRAL_NAME_PREFIX: Final = "version-"
#: Suffixes taken over from the original file name (Docling reads the format from it).
_SUFFIX_RE: Final = re.compile(r"\.[a-z0-9]{1,10}")
#: Rows per INSERT when the sections are written.
SECTION_BATCH_SIZE: Final = 500
#: Most of a failed Docling answer that is read for its error messages.
MAX_FAILURE_ANSWER_BYTES: Final = 1024 * 1024
#: Detail of an unexpected error; the exception itself goes to the server log only.
INTERNAL_DETAIL: Final = "unexpected error in the ingest flow; details are in the server log"


class Outcome(StrEnum):
    """What one call of :func:`convert` or :func:`poll` did."""

    #: No job with this ID.
    MISSING = "missing"
    #: The job was not in the expected state; nothing changed.
    IGNORED = "ignored"
    #: Waiting for Docling; the next status query is due in ``poll_after`` seconds.
    POLLING = "polling"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class StepResult:
    """Result of one step; the task schedules :func:`poll` if ``poll_after`` is set."""

    outcome: Outcome
    #: Seconds until the next call of :func:`poll`; ``None``: no further call.
    poll_after: int | None = None


# --- Error details ------------------------------------------------------------

_URL_RE: Final = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s\"'<>]+")
_UNC_PATH_RE: Final = re.compile(r"\\\\[^\s\"'<>|]+")
_WINDOWS_PATH_RE: Final = re.compile(r"(?<![\w])[A-Za-z]:[\\/][^\s\"'<>|]*")
# A slash at the start of a word: "/tmp/x.pdf", "./x", "~/x"; not "4xx/5xx" or "N/A".
_POSIX_PATH_RE: Final = re.compile(r"(?<![\w.~/-])(?:~|\.{1,2})?/[^\s\"'<>|,;()\[\]{}]+")
_MAC_RE: Final = re.compile(
    r"(?<![0-9A-Fa-f:.-])"
    r"(?:[0-9A-Fa-f]{2}([:-])[0-9A-Fa-f]{2}(?:\1[0-9A-Fa-f]{2}){4}"
    r"|[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4})"
    r"(?![0-9A-Fa-f:.-])"
)
# Candidates only; ipaddress decides (so that times such as 12:30:45 stay).
_IPV6_CANDIDATE_RE: Final = re.compile(
    r"(?<![\w:.])(?:[0-9A-Fa-f]{0,4}:){2,7}(?:[0-9A-Fa-f]{0,4}|\d{1,3}(?:\.\d{1,3}){3})"
    r"(?:%[\w.-]+)?(?![\w:])"
)
_IPV4_RE: Final = re.compile(r"(?<![\w.])\d{1,3}(?:\.\d{1,3}){3}(?::\d{1,5})?(?![\w.])")
_CONTROL_RE: Final = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_WHITESPACE_RE: Final = re.compile(r"\s+")
#: Shorter stems of a file name are not replaced on their own (too many false hits).
MIN_STEM_LENGTH: Final = 4


def _file_name_variants(filenames: Iterable[str]) -> list[str]:
    """The names to hide: each name, its last path part and its stem, longest first."""
    variants: set[str] = set()
    for name in filenames:
        if not name:
            continue
        base = PurePosixPath(PureWindowsPath(name).name).name
        variants.update(value for value in (name, base) if value)
        stem = PurePosixPath(base).stem
        if len(stem) >= MIN_STEM_LENGTH:
            variants.add(stem)
    return sorted(variants, key=len, reverse=True)


def _hide_ipv6(match: re.Match[str]) -> str:
    candidate = match.group(0)
    try:
        ipaddress.IPv6Address(candidate.split("%", 1)[0])
    except ValueError:
        return candidate
    return "<ip>"


def sanitize_error_detail(text: str, *, filenames: Iterable[str] = ()) -> str:
    """A technical error text that is safe to show to every role (E-57).

    Removes the given file names (with their last path part and stem), URLs,
    file system paths, MAC addresses and IPv4/IPv6 addresses, as well as
    control characters; collapses white space and cuts the result to
    :data:`~twox.ingest.models.ERROR_DETAIL_MAX_LENGTH` characters. The raw
    text belongs in the server log only.
    """
    cleaned = text
    for name in _file_name_variants(filenames):
        cleaned = re.sub(re.escape(name), "<file>", cleaned, flags=re.IGNORECASE)
    cleaned = _URL_RE.sub("<url>", cleaned)
    cleaned = _UNC_PATH_RE.sub("<path>", cleaned)
    cleaned = _WINDOWS_PATH_RE.sub("<path>", cleaned)
    cleaned = _POSIX_PATH_RE.sub("<path>", cleaned)
    cleaned = _MAC_RE.sub("<mac>", cleaned)
    cleaned = _IPV6_CANDIDATE_RE.sub(_hide_ipv6, cleaned)
    cleaned = _IPV4_RE.sub("<ip>", cleaned)
    cleaned = _CONTROL_RE.sub(" ", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    if len(cleaned) > ERROR_DETAIL_MAX_LENGTH:
        cleaned = cleaned[: ERROR_DETAIL_MAX_LENGTH - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"
    return cleaned


# --- Timing -------------------------------------------------------------------


def poll_delay(elapsed_seconds: float) -> int:
    """Seconds until the next status query, growing with the time the job has run.

    A quarter of the time since the job started, at least
    ``TWOX_INGEST_POLL_MIN_SECONDS`` and at most ``..._MAX_SECONDS``: a short
    document is noticed quickly, a long one is asked about once a minute.
    """
    lower: int = settings.TWOX_INGEST_POLL_MIN_SECONDS
    upper: int = settings.TWOX_INGEST_POLL_MAX_SECONDS
    return min(upper, max(lower, int(elapsed_seconds) // 4))


def retry_delay(attempt: int) -> int:
    """Seconds before retry number ``attempt`` (from 1): doubling from the poll minimum."""
    lower: int = settings.TWOX_INGEST_POLL_MIN_SECONDS
    upper: int = settings.TWOX_INGEST_POLL_MAX_SECONDS
    doublings = min(max(attempt - 1, 0), 16)
    return min(upper, lower * (1 << doublings))


def _deadline_passed(job: IngestJob, now: datetime) -> bool:
    if job.docling_started_at is None:
        return False
    limit = timedelta(seconds=settings.TWOX_INGEST_TIMEOUT_SECONDS)
    return now - job.docling_started_at >= limit


# --- Names --------------------------------------------------------------------


def neutral_filename(version: DocumentVersion) -> str:
    """``version-<id><suffix>``: the only name Docling sees, never the original one.

    The suffix comes from the original name (lower case, letters and digits
    only); without a usable one, from the content type.
    """
    base = PurePosixPath(PureWindowsPath(version.original_filename).name).name
    suffix = PurePosixPath(base).suffix.lower()
    if not _SUFFIX_RE.fullmatch(suffix):
        guessed = mimetypes.guess_extension(version.content_type.lower(), strict=False) or ""
        suffix = guessed if _SUFFIX_RE.fullmatch(guessed) else ""
    return f"{NEUTRAL_NAME_PREFIX}{version.pk}{suffix}"


def _content_type(version: DocumentVersion, filename: str) -> str:
    content_type = version.content_type.lower()
    if content_type == "application/octet-stream":
        return guess_content_type(filename)
    return content_type


# --- Job state ----------------------------------------------------------------


def _load_job(job_id: object) -> IngestJob | None:
    """The job with ``job_id`` and its version, or ``None`` (logged as a warning)."""
    if isinstance(job_id, bool) or not isinstance(job_id, int) or not 1 <= job_id <= MAX_JOB_ID:
        logger.warning("ingest: ignoring a message with an invalid job ID %r", job_id)
        return None
    try:
        return IngestJob.objects.select_related("document_version").get(pk=job_id)
    except IngestJob.DoesNotExist:
        logger.warning("ingest: job %s does not exist; nothing to do", job_id)
        return None


def _update(job: IngestJob, **fields: object) -> bool:
    """Write ``fields`` if the job is still running; mirror them on ``job``.

    Returns ``False`` if another message finished the job in the meantime.
    """
    now = timezone.now()
    changed = IngestJob.objects.filter(pk=job.pk, status=IngestStatus.RUNNING).update(
        **fields, updated_at=now
    )
    if not changed:
        return False
    for name, value in fields.items():
        setattr(job, name, value)
    job.updated_at = now
    return True


def _fail(job: IngestJob, code: IngestErrorCode, detail: str) -> StepResult:
    """End the job as ``failed``; ``detail`` must already be clean."""
    now = timezone.now()
    IngestJob.objects.filter(pk=job.pk, status=IngestStatus.RUNNING).update(
        status=IngestStatus.FAILED,
        error_code=code,
        error_detail=detail,
        finished_at=now,
        updated_at=now,
    )
    return StepResult(Outcome.FAILED)


def _fail_with_error(job: IngestJob, code: IngestErrorCode, raw: str) -> StepResult:
    """Log ``raw`` and end the job with its cleaned form."""
    logger.warning("ingest: job %s failed (%s): %s", job.pk, code.value, raw)
    detail = sanitize_error_detail(raw, filenames=[job.document_version.original_filename])
    return _fail(job, code, detail)


def _retry(job: IngestJob, error: Exception, *, task_lost: bool) -> StepResult:
    """Retry later after a temporary Docling error, or fail once the retries are used up."""
    limit: int = settings.TWOX_INGEST_MAX_RETRIES
    if job.attempts >= limit:
        return _fail_with_error(
            job,
            IngestErrorCode.DOCLING_UNAVAILABLE,
            f"{error} (gave up after {limit} retries)",
        )
    attempt = job.attempts + 1
    logger.info("ingest: job %s, retry %s of %s after: %s", job.pk, attempt, limit, error)
    fields: dict[str, Any] = {"attempts": attempt}
    if task_lost:
        # The next status query uploads the content again.
        fields |= {"docling_task_id": "", "docling_started_at": None, "step": IngestStep.CONVERT}
    if not _update(job, **fields):
        return StepResult(Outcome.IGNORED)
    return StepResult(Outcome.POLLING, poll_after=retry_delay(attempt))


def _guarded(job: IngestJob, step: Callable[[], StepResult]) -> StepResult:
    """Run ``step`` and turn every error into a retry or a failed job."""
    try:
        return step()
    except DoclingUnavailableError as error:
        return _retry(job, error, task_lost=False)
    except DoclingTaskLostError as error:
        return _retry(job, error, task_lost=True)
    except DoclingRejectedError as error:
        return _fail_with_error(job, IngestErrorCode.DOCLING_REJECTED, str(error))
    except (DoclingConversionError, UnsupportedDocumentError) as error:
        return _fail_with_error(job, IngestErrorCode.CONVERSION_FAILED, str(error))
    except BlobNotFoundError:
        logger.warning("ingest: job %s, stored content missing", job.pk, exc_info=True)
        return _fail(job, IngestErrorCode.CONTENT_MISSING, "the stored content is missing")
    except SoftTimeLimitExceeded:
        logger.warning("ingest: job %s ran past the soft time limit of its task", job.pk)
        return _fail(job, IngestErrorCode.TIMEOUT, "an ingest step ran past the time limit")
    except Exception:
        logger.exception("ingest: job %s failed with an unexpected error", job.pk)
        return _fail(job, IngestErrorCode.INTERNAL, INTERNAL_DETAIL)


# --- Steps --------------------------------------------------------------------


def convert(
    job_id: object,
    *,
    converter: DocumentConverter | None = None,
    storage: BlobStorage | None = None,
) -> StepResult:
    """Start a ``queued`` job: reuse a stored answer or upload the content to Docling."""
    job = _load_job(job_id)
    if job is None:
        return StepResult(Outcome.MISSING)
    now = timezone.now()
    claimed = IngestJob.objects.filter(pk=job.pk, status=IngestStatus.QUEUED).update(
        status=IngestStatus.RUNNING, step=IngestStep.CONVERT, started_at=now, updated_at=now
    )
    if not claimed:
        logger.info("ingest: job %s is %s, not queued; nothing to do", job.pk, job.status)
        return StepResult(Outcome.IGNORED)
    job.status, job.step, job.started_at, job.updated_at = (
        IngestStatus.RUNNING,
        IngestStep.CONVERT,
        now,
        now,
    )
    blobs = storage or get_blob_storage()
    return _guarded(job, lambda: _start(job, blobs, converter))


def poll(
    job_id: object,
    *,
    converter: DocumentConverter | None = None,
    storage: BlobStorage | None = None,
) -> StepResult:
    """Ask Docling once about a ``running`` job and move it on."""
    job = _load_job(job_id)
    if job is None:
        return StepResult(Outcome.MISSING)
    if job.status != IngestStatus.RUNNING:
        logger.info("ingest: job %s is %s; no status query", job.pk, job.status)
        return StepResult(Outcome.IGNORED)
    blobs = storage or get_blob_storage()
    return _guarded(job, lambda: _poll(job, blobs, converter))


def _start(job: IngestJob, storage: BlobStorage, converter: DocumentConverter | None) -> StepResult:
    source = _reusable_job(job, storage)
    if source is not None:
        logger.info("ingest: job %s reuses the Docling answer of job %s", job.pk, source.pk)
        if not _update(
            job,
            reused_from=source,
            result_blob_key=source.result_blob_key,
            step=IngestStep.SECTIONS,
        ):
            return StepResult(Outcome.IGNORED)
        return _finish(job, storage)
    return _submit(job, storage, converter or get_document_converter())


def _reusable_job(job: IngestJob, storage: BlobStorage) -> IngestJob | None:
    """The newest other ``done`` job with the same content and a stored Docling answer.

    Only a job that is ``done`` counts: its answer gave sections. An answer
    that could not be read (``conversion_failed``) is never reused, so a new
    attempt asks Docling again.
    """
    candidates = (
        IngestJob.objects.filter(
            document_version__sha256=job.document_version.sha256, status=IngestStatus.DONE
        )
        .exclude(pk=job.pk)
        .exclude(result_blob_key="")
        .order_by("-pk")
    )
    for candidate in candidates:
        if storage.blob_exists(candidate.result_blob_key):
            return candidate
        logger.warning(
            "ingest: stored Docling answer of job %s is missing; not reused", candidate.pk
        )
    return None


def _submit(job: IngestJob, storage: BlobStorage, converter: DocumentConverter) -> StepResult:
    """Upload the content of the version to Docling and schedule the first query."""
    version = job.document_version
    filename = neutral_filename(version)
    with storage.open_blob(version.blob_key) as stream:
        task_id = converter.submit(
            cast(BinaryIO, stream),
            filename,
            _content_type(version, filename),
            document_timeout=settings.TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS,
        )
    logger.info("ingest: job %s submitted to Docling as task %s", job.pk, task_id)
    if not _update(job, docling_task_id=task_id, docling_started_at=None, step=IngestStep.CONVERT):
        return StepResult(Outcome.IGNORED)
    return StepResult(Outcome.POLLING, poll_after=poll_delay(_elapsed(job)))


def _elapsed(job: IngestJob) -> float:
    if job.started_at is None:
        return 0.0
    return (timezone.now() - job.started_at).total_seconds()


def _poll(job: IngestJob, storage: BlobStorage, converter: DocumentConverter | None) -> StepResult:
    if job.result_blob_key:
        # The answer is stored already (a repeated message after a crash).
        return _finish(job, storage)
    docling = converter or get_document_converter()
    if not job.docling_task_id:
        return _submit(job, storage, docling)
    if _deadline_passed(job, timezone.now()):
        return _timeout(job)

    status = docling.poll(job.docling_task_id)
    # The deadline counts from the first start, not from the wait in Docling's queue.
    first_start = status.status == TaskStatus.STARTED and job.docling_started_at is None
    if first_start and not _update(job, docling_started_at=timezone.now()):
        return StepResult(Outcome.IGNORED)
    if not status.finished:
        return StepResult(Outcome.POLLING, poll_after=poll_delay(_elapsed(job)))

    with tempfile.TemporaryFile() as answer:
        docling.fetch(job.docling_task_id, answer)
        answer.seek(0)
        if status.status not in {TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS}:
            raise DoclingConversionError(_failure_text(answer, status.status))
        # Into durable storage first: Docling removes the result soon after it
        # was fetched (work order 041).
        stored = storage.store_blob(answer)
    if not _update(job, result_blob_key=stored.key, step=IngestStep.SECTIONS):
        return StepResult(Outcome.IGNORED)
    return _finish(job, storage)


def _timeout(job: IngestJob) -> StepResult:
    seconds: int = settings.TWOX_INGEST_TIMEOUT_SECONDS
    logger.warning("ingest: job %s, Docling did not finish within %s s", job.pk, seconds)
    return _fail(
        job,
        IngestErrorCode.TIMEOUT,
        f"the conversion did not finish within {seconds} seconds after it started",
    )


def _failure_text(answer: IO[bytes], status: TaskStatus) -> str:
    """The raw error text of a failed Docling answer, for log and cleaned detail."""
    messages: list[str] = []
    try:
        content: Any = json.loads(answer.read(MAX_FAILURE_ANSWER_BYTES))
    except ValueError:
        content = None
    if isinstance(content, dict):
        failure = content.get("failure")
        if isinstance(failure, dict) and isinstance(failure.get("message"), str):
            messages.append(failure["message"])
        errors = content.get("errors")
        for item in errors if isinstance(errors, list) else []:
            if isinstance(item, dict) and isinstance(item.get("error_message"), str):
                messages.append(item["error_message"])
    text = f"the conversion ended with status {status.value}"
    return f"{text}: {'; '.join(messages)}" if messages else text


def _page_count(document: dict[str, Any]) -> int | None:
    """Pages of the DoclingDocument; ``None`` for formats without pages (Markdown)."""
    pages = document.get("pages")
    return len(pages) if isinstance(pages, dict) and pages else None


def _partial_detail(errors: tuple[ConversionErrorItem, ...]) -> str:
    """A short note for a partly converted document: number of errors and their pages."""
    pages = sorted({error.page_no for error in errors if error.page_no is not None})
    text = f"converted with {len(errors)} errors"
    if pages:
        text += f" on pages {', '.join(str(page) for page in pages[:20])}"
    return text


def _finish(job: IngestJob, storage: BlobStorage) -> StepResult:
    """Read the stored answer, replace the sections of the version and end the job."""
    with storage.open_blob(job.result_blob_key) as stream:
        result = load_result(cast(BinaryIO, stream))
    drafts = build_sections(result.document, max_chars=settings.TWOX_SECTION_MAX_CHARS)
    detail = ""
    if result.status == TaskStatus.PARTIAL_SUCCESS:
        logger.warning("ingest: job %s, partial conversion: %s", job.pk, result.errors)
        detail = _partial_detail(result.errors)

    with transaction.atomic():
        # The lock makes a repeated message wait here and then find the job done.
        locked = (
            IngestJob.objects.select_for_update(of=("self",))
            .select_related("document_version")
            .filter(pk=job.pk, status=IngestStatus.RUNNING)
            .first()
        )
        if locked is None:
            return StepResult(Outcome.IGNORED)
        rows = section_rows(drafts, locked.document_version, locked)
        # The old sections stay searchable until this moment.
        Section.objects.filter(document_version_id=locked.document_version_id).delete()
        Section.objects.bulk_create(rows, batch_size=SECTION_BATCH_SIZE)
        now = timezone.now()
        # Work order 048 continues with the step embed here when TWOX_AI_ENABLED
        # is on (E-59); until then, and always without AI, the job ends here.
        IngestJob.objects.filter(pk=locked.pk).update(
            status=IngestStatus.DONE,
            step=IngestStep.SECTIONS,
            section_count=len(rows),
            page_count=_page_count(result.document),
            error_code="",
            error_detail=sanitize_error_detail(
                detail, filenames=[locked.document_version.original_filename]
            ),
            finished_at=now,
            updated_at=now,
        )
    logger.info("ingest: job %s done with %s sections", job.pk, len(rows))
    return StepResult(Outcome.DONE)
