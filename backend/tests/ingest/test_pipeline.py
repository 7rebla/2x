"""The ingest flow without Celery: convert, poll, reuse, sections, errors (work order 046).

Docling is replaced by :class:`~tests.ingest.fake_converter.FakeConverter`,
which answers with the real Docling results of work order 041. No test
reaches a real Docling or model service (``isolated_services``).
"""

import io
import json
from datetime import timedelta
from typing import Any

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from django.forms.models import model_to_dict
from django.utils import timezone
from pytest_django.fixtures import Settings

from tests.ingest.fake_converter import (
    MARKDOWN_CONTENT,
    PDF_CONTENT,
    FakeConverter,
    NoDocling,
    isolated_services,
    make_job,
    make_version,
    run_job,
)
from tests.ingest.fake_docling import MARKDOWN_FIXTURE, fixture_document, result_answer
from twox.files.models import Document, DocumentVersion
from twox.files.storage import get_blob_storage, key_for_sha256
from twox.ingest import pipeline
from twox.ingest.docling import (
    DoclingRejectedError,
    DoclingTaskLostError,
    DoclingUnavailableError,
    TaskStatus,
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
from twox.ingest.pipeline import Outcome, StepResult
from twox.ingest.sections import SectionDraft, build_sections

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("isolated_services")]

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]

POLLING = Outcome.POLLING
STARTED = TaskStatus.STARTED
PENDING = TaskStatus.PENDING
SUCCESS = TaskStatus.SUCCESS


@pytest.fixture(autouse=True)
def ingest_settings(settings: Settings) -> None:
    """The defaults of work order 045, independent of the .env of the run."""
    settings.TWOX_INGEST_MAX_RETRIES = 5
    settings.TWOX_INGEST_POLL_MIN_SECONDS = 10
    settings.TWOX_INGEST_POLL_MAX_SECONDS = 60
    settings.TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS = 7200
    settings.TWOX_INGEST_TIMEOUT_SECONDS = 9000
    settings.TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS = 86400
    settings.TWOX_SECTION_MAX_CHARS = 2000


def section_tuples(version: DocumentVersion) -> list[tuple[Any, ...]]:
    return [
        (s.ordinal, s.heading_path, s.text, s.page_start, s.page_end)
        for s in Section.objects.filter(document_version=version).order_by("ordinal")
    ]


def draft_tuples(drafts: list[SectionDraft]) -> list[tuple[Any, ...]]:
    return [(d.ordinal, list(d.heading_path), d.text, d.page_start, d.page_end) for d in drafts]


def job_state(job: IngestJob) -> dict[str, Any]:
    job.refresh_from_db()
    return model_to_dict(job) | {"updated_at": job.updated_at, "created_at": job.created_at}


def failure_answer(message: str) -> bytes:
    """A ``TaskFailureResult`` as docling-serve 1.38.2 sends it for a failed task."""
    return json.dumps(
        {
            "kind": "TaskFailureResult",
            "failure": {
                "category": "conversion",
                "message": message,
                "retryable": False,
                "phase": "convert",
            },
        }
    ).encode()


# --- Whole flow ------------------------------------------------------------------


def test_pdf_is_converted_and_its_sections_are_stored_with_pages(settings: Settings) -> None:
    version = make_version()
    job = make_job(version)
    converter = FakeConverter(statuses=[PENDING, STARTED, STARTED, SUCCESS])

    results = run_job(job, converter)

    assert [result.outcome for result in results] == [POLLING] * 4 + [Outcome.DONE]
    assert job.status == IngestStatus.DONE
    assert job.step == IngestStep.SECTIONS
    assert (job.error_code, job.error_detail, job.attempts) == ("", "", 0)
    assert job.started_at is not None
    assert job.docling_started_at is not None
    assert job.finished_at is not None
    assert job.started_at <= job.docling_started_at <= job.finished_at
    assert job.reused_from is None
    # The real result of BetrSichV.pdf, pages 1 to 5 (fixture of 041).
    assert job.page_count == 5
    expected = build_sections(fixture_document(), max_chars=settings.TWOX_SECTION_MAX_CHARS)
    assert job.section_count == len(expected) > 1
    assert section_tuples(version) == draft_tuples(expected)
    sections = Section.objects.filter(document_version=version)
    assert {section.ingest_job_id for section in sections} == {job.pk}
    assert min(section.page_start or 0 for section in sections) == 1
    assert max(section.page_end or 0 for section in sections) == 5
    assert all(section.page_start is not None for section in sections)


def test_docling_gets_a_neutral_file_name_and_the_stored_content(settings: Settings) -> None:
    version = make_version(filename="BetrSichV Ausgabe 2015.PDF")
    job = make_job(version)
    converter = FakeConverter()

    run_job(job, converter)

    [submission] = converter.submissions
    assert submission.filename == f"version-{version.pk}.pdf"
    assert submission.content_type == "application/pdf"
    assert submission.document_timeout == settings.TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS
    assert submission.content == PDF_CONTENT
    assert job.docling_task_id == "task-1"


def test_answer_is_stored_before_it_is_read() -> None:
    job = make_job(make_version())
    converter = FakeConverter()

    run_job(job, converter)

    assert job.result_blob_key
    with get_blob_storage().open_blob(job.result_blob_key) as stored:
        assert stored.read() == converter.answer


def test_markdown_has_sections_without_pages(settings: Settings) -> None:
    version = make_version(
        MARKDOWN_CONTENT, filename="sftp-backup.md", content_type="text/markdown"
    )
    job = make_job(version)
    converter = FakeConverter(answer=result_answer(fixture_document(MARKDOWN_FIXTURE)))

    run_job(job, converter)

    assert job.status == IngestStatus.DONE
    assert converter.submissions[0].filename == f"version-{version.pk}.md"
    assert job.page_count is None
    expected = build_sections(
        fixture_document(MARKDOWN_FIXTURE), max_chars=settings.TWOX_SECTION_MAX_CHARS
    )
    assert section_tuples(version) == draft_tuples(expected)
    assert job.section_count == len(expected)
    assert all(row[3] is None and row[4] is None for row in section_tuples(version))


@pytest.mark.parametrize(
    ("filename", "content_type", "expected_suffix"),
    [
        ("BetrSichV.pdf", "application/pdf", ".pdf"),
        ("MANUAL.PDF", "application/pdf", ".pdf"),
        ("C:\\data\\uploads\\Wiring plan.docx", "application/octet-stream", ".docx"),
        ("../../etc/passwd", "application/pdf", ".pdf"),
        ("manual", "application/pdf", ".pdf"),
        ("odd.p d f", "application/pdf", ".pdf"),
    ],
)
def test_neutral_file_name(filename: str, content_type: str, expected_suffix: str) -> None:
    version = make_version(filename=filename, content_type=content_type)

    assert pipeline.neutral_filename(version) == f"version-{version.pk}{expected_suffix}"


@pytest.mark.parametrize("ai_enabled", [True, False], ids=["ai-on", "ai-off"])
def test_ai_switch_decides_whether_the_step_embed_follows(
    settings: Settings, ai_enabled: bool
) -> None:
    # E-59: without AI the job ends after the sections; with AI it stays
    # running in the step embed and asks for the embed task (work order 048).
    # Neither state asks the model service here (isolated_services fails the
    # test otherwise, and the error would surface as an internal failure).
    settings.TWOX_AI_ENABLED = ai_enabled
    version = make_version()
    job = make_job(version)

    results = run_job(job, FakeConverter())

    if ai_enabled:
        assert results[-1] == StepResult(Outcome.EMBEDDING, embed_after=0)
        assert (job.status, job.step, job.error_code) == (IngestStatus.RUNNING, "embed", "")
        assert job.finished_at is None
    else:
        assert results[-1] == StepResult(Outcome.DONE)
        assert (job.status, job.step, job.error_code) == (IngestStatus.DONE, "sections", "")
        assert job.finished_at is not None
    assert all(result.embed_after is None for result in results[:-1])
    assert job.section_count == Section.objects.filter(document_version=version).count() > 0
    assert job.page_count == 5
    assert all(section.embedding is None for section in Section.objects.filter(ingest_job=job))


# --- Reuse ---------------------------------------------------------------------


def test_second_version_with_the_same_content_reuses_the_answer() -> None:
    first_version = make_version(device="dps-plc")
    first = make_job(first_version)
    run_job(first, FakeConverter())
    second_version = make_version(device="hbw-plc", filename="copy of the manual.pdf")
    second = make_job(second_version)

    results = run_job(second, NoDocling())

    assert results == [StepResult(Outcome.DONE)]
    assert second.status == IngestStatus.DONE
    assert second.reused_from_id == first.pk
    assert second.result_blob_key == first.result_blob_key
    assert second.docling_task_id == ""
    assert second.page_count == 5
    assert section_tuples(second_version) == section_tuples(first_version)
    assert second.section_count == first.section_count


def test_a_new_version_of_the_same_document_reuses_the_answer() -> None:
    first_version = make_version()
    first = make_job(first_version)
    run_job(first, FakeConverter())
    second_version = make_version(document=first_version.document, number=2)

    second = make_job(second_version)
    run_job(second, NoDocling())

    assert (second.status, second.reused_from_id) == (IngestStatus.DONE, first.pk)


def test_answer_is_not_reused_when_it_is_missing_from_the_storage() -> None:
    first_version = make_version(device="dps-plc")
    IngestJob.objects.create(
        document_version=first_version,
        status=IngestStatus.DONE,
        result_blob_key=key_for_sha256("cd" * 32),
    )
    second = make_job(make_version(device="hbw-plc"))
    converter = FakeConverter()

    run_job(second, converter)

    assert second.status == IngestStatus.DONE
    assert second.reused_from is None
    assert len(converter.submissions) == 1


def test_answer_of_a_failed_job_is_not_reused() -> None:
    first = make_job(make_version(device="dps-plc"))
    run_job(first, FakeConverter(answer=result_answer(None)))
    assert (first.status, first.error_code) == (IngestStatus.FAILED, "conversion_failed")
    assert first.result_blob_key
    second = make_job(make_version(device="hbw-plc"))
    converter = FakeConverter()

    run_job(second, converter)

    assert (second.status, second.reused_from) == (IngestStatus.DONE, None)
    assert len(converter.submissions) == 1


@pytest.mark.parametrize("status", [PENDING, STARTED], ids=["pending", "started"])
def test_every_status_query_of_a_running_job_writes_updated_at(status: TaskStatus) -> None:
    # From the review of 049 (work order 048): ingest_versions --stuck looks at
    # updated_at; a long conversion must not look stuck between state changes.
    job = make_job(make_version())
    converter = FakeConverter(statuses=[status])
    assert pipeline.convert(job.pk, converter=converter).outcome == POLLING
    long_ago = timezone.now() - timedelta(hours=1)

    for _ in range(3):
        IngestJob.objects.filter(pk=job.pk).update(updated_at=long_ago)
        before = timezone.now()

        assert pipeline.poll(job.pk, converter=converter).outcome == POLLING

        job.refresh_from_db()
        assert job.status == IngestStatus.RUNNING
        assert job.updated_at >= before


def test_status_query_does_not_touch_a_finished_job() -> None:
    job = make_job(make_version())
    run_job(job, FakeConverter())
    long_ago = timezone.now() - timedelta(hours=1)
    IngestJob.objects.filter(pk=job.pk).update(updated_at=long_ago)

    assert pipeline.poll(job.pk, converter=FakeConverter()) == StepResult(Outcome.IGNORED)

    job.refresh_from_db()
    assert job.updated_at == long_ago


def test_partial_answer_is_not_reused() -> None:
    # From the review of 046 (work order 048): an answer that Docling cut short
    # (partial_success, for example after document_timeout) is not reused for
    # the same content; the next job asks Docling again.
    partial = result_answer(fixture_document(), status="partial_success", errors=[])
    first = make_job(make_version(device="dps-plc"))
    run_job(first, FakeConverter(statuses=[TaskStatus.PARTIAL_SUCCESS], answer=partial))
    assert first.status == IngestStatus.DONE
    assert first.error_detail.startswith(pipeline.PARTIAL_DETAIL_PREFIX)
    second = make_job(make_version(device="hbw-plc"))
    converter = FakeConverter()

    run_job(second, converter)

    assert (second.status, second.reused_from, second.error_detail) == (
        IngestStatus.DONE,
        None,
        "",
    )
    assert len(converter.submissions) == 1
    # The complete answer of the second job is reused by a third.
    third = make_job(make_version(device="vgr-plc"))
    run_job(third, NoDocling())
    assert third.reused_from_id == second.pk


def test_partial_note_survives_a_file_name_like_its_words() -> None:
    # The note is built from numbers only and is not cleaned: a file named
    # like a word of it must not hide the prefix that excludes it from reuse.
    partial = result_answer(fixture_document(), status="partial_success", errors=[])
    job = make_job(make_version(filename="converted.pdf"))

    run_job(job, FakeConverter(statuses=[TaskStatus.PARTIAL_SUCCESS], answer=partial))

    assert job.error_detail == "converted with 0 errors"


# --- Errors ------------------------------------------------------------------------


def test_missing_content_fails_with_content_missing() -> None:
    document = Document.objects.create(
        device=make_version().document.device, title="Manual without bytes"
    )
    sha256 = "ef" * 32
    version = DocumentVersion.objects.create(
        document=document,
        number=1,
        blob_key=key_for_sha256(sha256),
        sha256=sha256,
        size=10,
        content_type="application/pdf",
        original_filename="gone.pdf",
    )
    job = make_job(version)
    converter = FakeConverter()

    results = run_job(job, converter)

    assert results == [StepResult(Outcome.FAILED)]
    assert (job.status, job.step, job.error_code) == ("failed", "convert", "content_missing")
    assert job.error_detail == "the stored content is missing"
    assert job.finished_at is not None
    assert converter.submissions == []


def test_unreachable_docling_is_retried_with_growing_delay_then_fails() -> None:
    job = make_job(make_version())
    refused = DoclingUnavailableError("docling-serve refused the connection")
    converter = FakeConverter(submit_errors=[refused] * 10)

    results = run_job(job, converter)

    assert [result.poll_after for result in results] == [10, 20, 40, 60, 60, None]
    assert results[-1].outcome == Outcome.FAILED
    assert job.attempts == 5
    assert (job.status, job.error_code) == ("failed", "docling_unavailable")
    assert "refused the connection" in job.error_detail
    assert "gave up after 5 retries" in job.error_detail
    assert job.finished_at is not None


def test_docling_back_in_time_ends_done() -> None:
    job = make_job(make_version())
    refused = DoclingUnavailableError("docling-serve refused the connection")
    converter = FakeConverter(submit_errors=[refused, refused], statuses=[refused, SUCCESS])

    run_job(job, converter)

    assert job.status == IngestStatus.DONE
    assert job.attempts == 3
    assert len(converter.submissions) == 1


def test_lost_docling_task_is_submitted_again() -> None:
    job = make_job(make_version())
    lost = DoclingTaskLostError("docling-serve does not know the task")
    converter = FakeConverter(statuses=[STARTED, lost, STARTED, SUCCESS])

    assert pipeline.convert(job.pk, converter=converter).outcome == POLLING
    assert pipeline.poll(job.pk, converter=converter).outcome == POLLING
    assert IngestJob.objects.get(pk=job.pk).docling_started_at is not None
    after_loss = pipeline.poll(job.pk, converter=converter)
    lost_state = IngestJob.objects.get(pk=job.pk)
    assert after_loss == StepResult(POLLING, poll_after=10)
    assert (lost_state.docling_task_id, lost_state.docling_started_at) == ("", None)
    assert lost_state.attempts == 1
    rest = [pipeline.poll(job.pk, converter=converter) for _ in range(3)]

    job.refresh_from_db()
    assert [result.outcome for result in rest] == [POLLING, POLLING, Outcome.DONE]
    assert job.status == IngestStatus.DONE
    assert [submission.filename for submission in converter.submissions] == [
        f"version-{job.document_version_id}.pdf"
    ] * 2
    assert job.docling_task_id == "task-2"
    assert converter.fetched == ["task-2"]


def test_result_lost_before_fetch_is_submitted_again() -> None:
    job = make_job(make_version())
    lost = DoclingTaskLostError("docling-serve does not know the task")
    converter = FakeConverter(statuses=[SUCCESS], fetch_errors=[lost])

    run_job(job, converter)

    assert job.status == IngestStatus.DONE
    assert len(converter.submissions) == 2


def test_task_lost_again_and_again_ends_as_unavailable_never_rejected() -> None:
    job = make_job(make_version())
    converter = FakeConverter(
        statuses=[DoclingTaskLostError("docling-serve does not know the task")]
    )

    run_job(job, converter)

    assert (job.status, job.error_code) == ("failed", "docling_unavailable")
    assert job.attempts == 5
    # The first upload and one per retry.
    assert len(converter.submissions) == 6


def test_rejected_upload_fails_at_once() -> None:
    job = make_job(make_version())
    rejected = DoclingRejectedError("docling-serve rejected the request (HTTP 422, fields: files)")
    converter = FakeConverter(submit_errors=[rejected])

    results = run_job(job, converter)

    assert results == [StepResult(Outcome.FAILED)]
    assert (job.status, job.error_code, job.attempts) == ("failed", "docling_rejected", 0)
    assert job.error_detail == "docling-serve rejected the request (HTTP 422, fields: files)"
    assert job.finished_at is not None


def test_failed_conversion_shows_a_cleaned_docling_message() -> None:
    version = make_version(filename="Pump P-101 manual.pdf")
    job = make_job(version)
    message = (
        "Conversion of /tmp/tmpq3x9/Pump P-101 manual.pdf failed: "
        "cannot reach http://10.0.0.7:8080/models from 10.0.0.12"
    )
    converter = FakeConverter(statuses=[TaskStatus.FAILURE], answer=failure_answer(message))

    run_job(job, converter)

    assert (job.status, job.step, job.error_code) == ("failed", "convert", "conversion_failed")
    assert job.error_detail == (
        "the conversion ended with status failure: Conversion of <path><file> failed: "
        "cannot reach <url> from <ip>"
    )
    assert job.result_blob_key == ""
    assert not Section.objects.filter(document_version=version).exists()


def test_failed_conversion_lists_the_error_messages_of_the_answer() -> None:
    job = make_job(make_version())
    answer = result_answer(
        None,
        status="failure",
        errors=[
            {
                "component_type": "document_backend",
                "module_name": "pdf",
                "error_message": "Input document version-1.pdf is not valid.",
                "page_no": None,
            }
        ],
    )
    converter = FakeConverter(statuses=[TaskStatus.FAILURE], answer=answer)

    run_job(job, converter)

    assert job.error_code == "conversion_failed"
    assert job.error_detail == (
        "the conversion ended with status failure: Input document version-1.pdf is not valid."
    )


def test_skipped_conversion_fails() -> None:
    job = make_job(make_version())

    run_job(job, FakeConverter(statuses=[TaskStatus.SKIPPED], answer=result_answer(None)))

    assert (job.status, job.error_code) == ("failed", "conversion_failed")
    assert "status skipped" in job.error_detail


def test_answer_without_document_fails_in_the_sections_step() -> None:
    job = make_job(make_version())

    run_job(job, FakeConverter(answer=result_answer(None)))

    assert (job.status, job.step, job.error_code) == ("failed", "sections", "conversion_failed")
    assert job.error_detail == "the stored result holds no DoclingDocument"
    assert job.finished_at is not None


def test_unknown_schema_fails_as_conversion_failed() -> None:
    document = fixture_document() | {"version": "2.0.0"}
    job = make_job(make_version())

    run_job(job, FakeConverter(answer=result_answer(document)))

    assert (job.status, job.error_code) == ("failed", "conversion_failed")
    assert "schema version is not supported" in job.error_detail


def test_partial_success_ends_done_with_a_note() -> None:
    errors = [
        {
            "component_type": "model",
            "module_name": "table_structure",
            "error_message": "table on page 3 could not be read from /opt/models/x",
            "page_no": 3,
        }
    ]
    answer = result_answer(fixture_document(), status="partial_success", errors=errors)
    job = make_job(make_version())

    run_job(job, FakeConverter(statuses=[TaskStatus.PARTIAL_SUCCESS], answer=answer))

    assert (job.status, job.error_code) == ("done", "")
    assert job.error_detail == "converted with 1 errors on pages 3"
    assert job.section_count and job.section_count > 0


def test_unexpected_error_fails_as_internal_with_details_in_the_log_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    job = make_job(make_version())
    converter = FakeConverter(submit_errors=[RuntimeError("boom in /srv/secret/BetrSichV.pdf")])

    with caplog.at_level("ERROR", logger="twox.ingest.pipeline"):
        run_job(job, converter)

    assert (job.status, job.error_code) == ("failed", "internal")
    assert job.error_detail == pipeline.INTERNAL_DETAIL
    assert "boom" not in job.error_detail
    assert "boom in /srv/secret/BetrSichV.pdf" in caplog.text
    assert job.finished_at is not None


def test_soft_time_limit_fails_as_timeout() -> None:
    job = make_job(make_version())

    run_job(job, FakeConverter(statuses=[SoftTimeLimitExceeded()]))

    assert (job.status, job.error_code) == ("failed", "timeout")
    assert job.finished_at is not None


# --- Deadline --------------------------------------------------------------------


def test_wait_in_the_docling_queue_within_the_deadline_goes_on(settings: Settings) -> None:
    job = make_job(make_version())
    converter = FakeConverter(statuses=[PENDING])
    pipeline.convert(job.pk, converter=converter)
    submitted = timezone.now() - timedelta(seconds=settings.TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS - 60)
    IngestJob.objects.filter(pk=job.pk).update(started_at=submitted)

    result = pipeline.poll(job.pk, converter=converter)

    job.refresh_from_db()
    assert result == StepResult(POLLING, poll_after=60)
    assert (job.status, job.docling_started_at) == ("running", None)


def test_long_wait_of_a_large_batch_below_the_queue_deadline_goes_on(settings: Settings) -> None:
    # A large batch waits in Docling's queue one document after another: ten
    # hours are far past the ingest deadline, but below the queue deadline.
    assert settings.TWOX_INGEST_TIMEOUT_SECONDS < 10 * 3600 < 86400
    job = make_job(make_version())
    converter = FakeConverter(statuses=[PENDING])
    pipeline.convert(job.pk, converter=converter)
    IngestJob.objects.filter(pk=job.pk).update(started_at=timezone.now() - timedelta(hours=10))

    result = pipeline.poll(job.pk, converter=converter)

    job.refresh_from_db()
    assert result == StepResult(POLLING, poll_after=60)
    assert (job.status, job.error_code, job.docling_started_at) == ("running", "", None)


def test_task_that_docling_never_starts_fails_with_timeout(settings: Settings) -> None:
    job = make_job(make_version())
    converter = FakeConverter(statuses=[PENDING])
    pipeline.convert(job.pk, converter=converter)
    pipeline.poll(job.pk, converter=converter)
    submitted = timezone.now() - timedelta(seconds=settings.TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS + 1)
    IngestJob.objects.filter(pk=job.pk).update(started_at=submitted)

    result = pipeline.poll(job.pk, converter=converter)

    job.refresh_from_db()
    assert result == StepResult(Outcome.FAILED)
    assert (job.status, job.error_code) == ("failed", "timeout")
    assert job.error_detail == (
        "Docling did not start the conversion within 86400 seconds after the job started"
        " (TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS)"
    )
    assert job.docling_started_at is None
    assert job.finished_at is not None


def test_late_start_after_a_long_wait_counts_from_the_start(settings: Settings) -> None:
    job = make_job(make_version())
    converter = FakeConverter(statuses=[PENDING, STARTED])
    pipeline.convert(job.pk, converter=converter)
    pipeline.poll(job.pk, converter=converter)
    submitted = timezone.now() - timedelta(seconds=settings.TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS + 1)
    IngestJob.objects.filter(pk=job.pk).update(started_at=submitted)
    before = timezone.now()

    first = pipeline.poll(job.pk, converter=converter)
    job.refresh_from_db()
    assert first.outcome == POLLING
    assert job.docling_started_at is not None
    assert job.docling_started_at >= before

    # From now on only the deadline from docling_started_at applies.
    assert pipeline.poll(job.pk, converter=converter).outcome == POLLING
    started = timezone.now() - timedelta(seconds=settings.TWOX_INGEST_TIMEOUT_SECONDS + 1)
    IngestJob.objects.filter(pk=job.pk).update(docling_started_at=started)

    result = pipeline.poll(job.pk, converter=converter)

    job.refresh_from_db()
    assert result == StepResult(Outcome.FAILED)
    assert job.error_detail == "the conversion did not finish within 9000 seconds after it started"


def test_finished_between_two_queries_without_started_is_done(settings: Settings) -> None:
    job = make_job(make_version())
    converter = FakeConverter(statuses=[PENDING, SUCCESS])
    pipeline.convert(job.pk, converter=converter)
    pipeline.poll(job.pk, converter=converter)
    # Even past the deadline without a start: Docling is asked first.
    submitted = timezone.now() - timedelta(seconds=settings.TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS + 1)
    IngestJob.objects.filter(pk=job.pk).update(started_at=submitted)

    result = pipeline.poll(job.pk, converter=converter)

    job.refresh_from_db()
    assert result == StepResult(Outcome.DONE)
    assert (job.status, job.error_code, job.docling_started_at) == ("done", "", None)
    assert job.section_count and job.section_count > 0


def test_first_started_sets_the_start_of_the_deadline() -> None:
    job = make_job(make_version())
    converter = FakeConverter(statuses=[STARTED])
    pipeline.convert(job.pk, converter=converter)
    before = timezone.now()

    pipeline.poll(job.pk, converter=converter)
    job.refresh_from_db()
    first_start = job.docling_started_at
    pipeline.poll(job.pk, converter=converter)
    job.refresh_from_db()

    assert first_start is not None
    assert first_start >= before
    assert job.docling_started_at == first_start


def test_long_conversion_after_start_fails_with_timeout(settings: Settings) -> None:
    job = make_job(make_version())
    converter = FakeConverter(statuses=[STARTED])
    pipeline.convert(job.pk, converter=converter)
    pipeline.poll(job.pk, converter=converter)
    started = timezone.now() - timedelta(seconds=settings.TWOX_INGEST_TIMEOUT_SECONDS + 1)
    IngestJob.objects.filter(pk=job.pk).update(docling_started_at=started)
    polls_before = len(converter.polled)

    result = pipeline.poll(job.pk, converter=converter)

    job.refresh_from_db()
    assert result == StepResult(Outcome.FAILED)
    assert (job.status, job.error_code) == ("failed", "timeout")
    assert job.error_detail == "the conversion did not finish within 9000 seconds after it started"
    assert job.finished_at is not None
    assert len(converter.polled) == polls_before


def test_conversion_within_the_deadline_goes_on(settings: Settings) -> None:
    job = make_job(make_version())
    converter = FakeConverter(statuses=[STARTED])
    pipeline.convert(job.pk, converter=converter)
    started = timezone.now() - timedelta(seconds=settings.TWOX_INGEST_TIMEOUT_SECONDS - 60)
    IngestJob.objects.filter(pk=job.pk).update(docling_started_at=started)

    assert pipeline.poll(job.pk, converter=converter).outcome == POLLING


def test_poll_delay_grows_from_the_minimum_to_the_maximum() -> None:
    assert [pipeline.poll_delay(seconds) for seconds in (0, 39, 40, 120, 239, 10_000)] == [
        10,
        10,
        10,
        30,
        59,
        60,
    ]
    assert [pipeline.retry_delay(attempt) for attempt in range(1, 7)] == [10, 20, 40, 60, 60, 60]


def test_first_status_query_comes_after_the_minimum() -> None:
    job = make_job(make_version())

    assert pipeline.convert(job.pk, converter=FakeConverter()) == StepResult(POLLING, 10)


# --- Idempotency --------------------------------------------------------------------


def test_second_convert_or_poll_of_a_done_job_changes_nothing() -> None:
    version = make_version()
    job = make_job(version)
    run_job(job, FakeConverter())
    state = job_state(job)
    sections = list(Section.objects.filter(document_version=version).values_list("pk", "text"))

    assert pipeline.convert(job.pk, converter=NoDocling()) == StepResult(Outcome.IGNORED)
    assert pipeline.poll(job.pk, converter=NoDocling()) == StepResult(Outcome.IGNORED)

    assert job_state(job) == state
    assert list(Section.objects.filter(document_version=version).values_list("pk", "text")) == (
        sections
    )


def test_second_convert_of_a_failed_job_changes_nothing() -> None:
    job = make_job(make_version())
    run_job(job, FakeConverter(submit_errors=[DoclingRejectedError("rejected (HTTP 400)")]))
    state = job_state(job)

    assert pipeline.convert(job.pk, converter=NoDocling()).outcome == Outcome.IGNORED
    assert pipeline.poll(job.pk, converter=NoDocling()).outcome == Outcome.IGNORED
    assert job_state(job) == state


def test_second_convert_of_a_running_job_does_not_submit_again() -> None:
    job = make_job(make_version())
    converter = FakeConverter()
    pipeline.convert(job.pk, converter=converter)

    assert pipeline.convert(job.pk, converter=converter) == StepResult(Outcome.IGNORED)
    assert len(converter.submissions) == 1


def test_poll_of_a_queued_job_does_nothing() -> None:
    job = make_job(make_version())
    state = job_state(job)

    assert pipeline.poll(job.pk, converter=NoDocling()) == StepResult(Outcome.IGNORED)
    assert job_state(job) == state


def test_repeated_poll_after_a_crash_finishes_from_the_stored_answer() -> None:
    # A worker died after storing the answer: the redelivered message builds
    # the sections from the storage without asking Docling again.
    job = make_job(make_version())
    converter = FakeConverter(statuses=[SUCCESS])
    pipeline.convert(job.pk, converter=converter)
    # The answer as poll would have stored it.
    stored = get_blob_storage().store_blob(io.BytesIO(converter.answer))
    IngestJob.objects.filter(pk=job.pk).update(result_blob_key=stored.key, step="sections")

    assert pipeline.poll(job.pk, converter=NoDocling()) == StepResult(Outcome.DONE)
    job.refresh_from_db()
    assert job.status == IngestStatus.DONE
    assert job.section_count and job.section_count > 0


@pytest.mark.parametrize("job_id", [987_654_321, 0, -1, 2**63, True, "1", None, 1.0])
def test_unknown_or_invalid_job_id_is_ignored(
    job_id: object, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING", logger="twox.ingest.pipeline"):
        assert pipeline.convert(job_id, converter=NoDocling()) == StepResult(Outcome.MISSING)
        assert pipeline.poll(job_id, converter=NoDocling()) == StepResult(Outcome.MISSING)

    assert caplog.records
    assert all(record.levelname == "WARNING" for record in caplog.records)


# --- Re-ingesting ---------------------------------------------------------------


def test_new_ingest_replaces_the_sections_only_at_the_end() -> None:
    version = make_version()
    old_job = IngestJob.objects.create(
        document_version=version, status=IngestStatus.DONE, step=IngestStep.SECTIONS
    )
    old_drafts = [
        SectionDraft(ordinal=0, heading_path=("Old",), text="Old text.", page_start=1, page_end=1)
    ]
    Section.objects.bulk_create(section_rows(old_drafts, version, old_job))
    old_ids = set(Section.objects.filter(document_version=version).values_list("pk", flat=True))
    job = make_job(version)
    converter = FakeConverter(statuses=[STARTED, SUCCESS])

    pipeline.convert(job.pk, converter=converter)
    during_convert = set(
        Section.objects.filter(document_version=version).values_list("pk", flat=True)
    )
    pipeline.poll(job.pk, converter=converter)
    during_poll = set(Section.objects.filter(document_version=version).values_list("pk", flat=True))
    assert pipeline.poll(job.pk, converter=converter).outcome == Outcome.DONE

    assert during_convert == during_poll == old_ids
    sections = Section.objects.filter(document_version=version)
    assert not old_ids & set(sections.values_list("pk", flat=True))
    assert {section.ingest_job_id for section in sections} == {job.pk}
    assert sections.count() == IngestJob.objects.get(pk=job.pk).section_count


def test_ingesting_the_same_version_again_reuses_and_replaces() -> None:
    version = make_version()
    first = make_job(version)
    run_job(first, FakeConverter())
    first_sections = section_tuples(version)
    second = make_job(version)

    run_job(second, NoDocling())

    assert second.reused_from_id == first.pk
    assert section_tuples(version) == first_sections
    assert set(
        Section.objects.filter(document_version=version).values_list("ingest_job", flat=True)
    ) == {second.pk}


# --- Error details -----------------------------------------------------------------


def test_sanitize_removes_path_url_addresses_and_file_name() -> None:
    raw = (
        "Conversion of 'Manual Pump P-101.pdf' failed: cannot read "
        "/tmp/tmpa1b2/Manual Pump P-101.pdf and C:\\data\\uploads\\Manual Pump P-101.pdf "
        "(see https://docling.example/errors?id=7 from 192.168.10.5:5001, [fe80::1%eth0]:80, "
        "2001:db8::42, device 00:1B:44:11:3A:B7 and 001b.4411.3ab7) at 12:30:45 "
        "for Manual Pump P-101"
    )

    cleaned = pipeline.sanitize_error_detail(raw, filenames=["Manual Pump P-101.pdf"])

    for secret in (
        "Manual",
        "P-101",
        "/tmp",
        "tmpa1b2",
        "C:\\",
        "uploads",
        "https",
        "docling.example",
        "192.168",
        "5001",
        "fe80",
        "2001:db8",
        "00:1B",
        "001b",
    ):
        assert secret not in cleaned
    assert cleaned == (
        "Conversion of '<file>' failed: cannot read <path><file> and <path><file> "
        "(see <url> from <ip>, [<ip>]:80, <ip>, device <mac> and <mac>) at 12:30:45 for <file>"
    )


def test_sanitize_keeps_harmless_text() -> None:
    text = "docling-serve rejected the request (HTTP 422, fields: files); 4xx/5xx, N/A, v1.38.2"

    assert pipeline.sanitize_error_detail(text) == text


def test_sanitize_removes_control_characters_and_cuts_to_the_limit() -> None:
    assert (
        pipeline.sanitize_error_detail("line one\x00\nline\ttwo\x1b[0m") == "line one line two [0m"
    )
    cleaned = pipeline.sanitize_error_detail("word " * 3000)
    assert len(cleaned) == ERROR_DETAIL_MAX_LENGTH
    assert cleaned.endswith("\N{HORIZONTAL ELLIPSIS}")


def test_sanitize_hides_a_file_name_given_with_a_path() -> None:
    cleaned = pipeline.sanitize_error_detail(
        "Wiring plan.docx is broken", filenames=["C:\\data\\Wiring plan.docx"]
    )

    assert cleaned == "<file> is broken"


def test_error_details_of_failed_jobs_never_hold_the_original_file_name() -> None:
    version = make_version(filename="Secret plant 7.pdf")
    job = make_job(version)
    rejected = DoclingRejectedError("could not read Secret plant 7.pdf at /data/media/x")

    run_job(job, FakeConverter(submit_errors=[rejected]))

    assert job.error_detail == "could not read <file> at <path>"
    assert IngestErrorCode(job.error_code) == IngestErrorCode.DOCLING_REJECTED
