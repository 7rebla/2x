"""Ingest jobs and sections: constraints, search vector, embedding, helpers (042)."""

from dataclasses import dataclass

import pytest
from django.contrib.postgres.search import SearchQuery
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, connection, transaction
from django.db.models import ProtectedError
from pytest_django import DjangoAssertNumQueries

from tests.accounts.users import make_user
from tests.files.helpers import make_device
from twox.files.models import Document, DocumentVersion
from twox.files.storage import key_for_sha256
from twox.ingest.models import (
    EMBEDDING_DIMENSIONS,
    IngestErrorCode,
    IngestJob,
    IngestStatus,
    IngestStep,
    Section,
    join_headings,
    section_rows,
)

pytestmark = pytest.mark.django_db

SHA256 = "ab" * 32


def make_version(key: str = "dps-plc", sha256: str = SHA256) -> DocumentVersion:
    """A saved document version; its bytes are not needed here."""
    document = Document.objects.create(device=make_device(key), title=f"Manual {key}")
    return DocumentVersion.objects.create(
        document=document,
        number=1,
        blob_key=key_for_sha256(sha256),
        sha256=sha256,
        size=7,
        content_type="application/pdf",
        original_filename="manual.pdf",
    )


def make_section(
    job: IngestJob,
    ordinal: int = 1,
    text: str = "The pump starts.",
    heading_path: list[str] | None = None,
) -> Section:
    return Section.objects.create(
        document_version=job.document_version,
        ingest_job=job,
        ordinal=ordinal,
        heading_path=heading_path if heading_path is not None else ["Operation"],
        text=text,
    )


def lexemes(section: Section) -> dict[str, set[str]]:
    """Lexeme -> weights of the stored search vector of ``section``."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT v.lexeme, v.weights FROM ingest_section s,"
            " unnest(s.search_vector) AS v WHERE s.id = %s",
            [section.pk],
        )
        return {lexeme: set(weights) for lexeme, weights in cursor.fetchall()}


@pytest.fixture
def version() -> DocumentVersion:
    return make_version()


@pytest.fixture
def job(version: DocumentVersion) -> IngestJob:
    return IngestJob.objects.create(document_version=version)


# --- Ingest job ------------------------------------------------------------


def test_new_job_is_queued_without_step_or_error(job: IngestJob) -> None:
    job.refresh_from_db()

    assert job.status == IngestStatus.QUEUED
    assert job.step == ""
    assert job.error_code == ""
    assert job.error_detail == ""
    assert job.attempts == 0
    assert job.requested_by is None
    assert job.reused_from is None
    assert job.result_blob_key == ""
    assert job.page_count is None
    assert job.section_count is None
    assert job.created_at is not None
    assert job.updated_at is not None
    job.full_clean()


def test_choices_are_the_agreed_lists() -> None:
    assert IngestStatus.values == ["queued", "running", "done", "failed", "skipped"]
    assert IngestStep.values == ["convert", "sections", "embed"]
    assert IngestErrorCode.values == [
        "docling_unavailable",
        "docling_rejected",
        "conversion_failed",
        "content_missing",
        "unsupported_format",
        "embedding_unavailable",
        "embedding_rejected",
        "embedding_dimension_mismatch",
        "timeout",
        "internal",
    ]


@pytest.mark.parametrize("first", [IngestStatus.QUEUED, IngestStatus.RUNNING])
@pytest.mark.parametrize("second", [IngestStatus.QUEUED, IngestStatus.RUNNING])
def test_at_most_one_active_job_per_version(
    version: DocumentVersion, first: IngestStatus, second: IngestStatus
) -> None:
    IngestJob.objects.create(document_version=version, status=first)

    with pytest.raises(IntegrityError), transaction.atomic():
        IngestJob.objects.create(document_version=version, status=second)

    assert IngestJob.objects.count() == 1


def test_full_clean_reports_the_active_job(job: IngestJob) -> None:
    second = IngestJob(document_version=job.document_version, status=IngestStatus.RUNNING)

    with pytest.raises(ValidationError) as caught:
        second.full_clean()

    assert "already has a queued or running ingest job" in str(caught.value)


def test_finished_jobs_do_not_block_a_new_one(version: DocumentVersion) -> None:
    for status in (IngestStatus.DONE, IngestStatus.FAILED, IngestStatus.SKIPPED):
        IngestJob.objects.create(document_version=version, status=status)
        IngestJob.objects.create(document_version=version, status=status)

    IngestJob.objects.create(document_version=version, status=IngestStatus.QUEUED)

    assert IngestJob.objects.count() == 7


def test_active_jobs_of_different_versions_are_independent(job: IngestJob) -> None:
    other = make_version("hbw-plc", "cd" * 32)

    IngestJob.objects.create(document_version=other, status=IngestStatus.RUNNING)

    assert IngestJob.objects.filter(status__in=["queued", "running"]).count() == 2


def test_a_job_can_be_finished_and_retried(job: IngestJob) -> None:
    job.status = IngestStatus.FAILED
    job.step = IngestStep.CONVERT
    job.error_code = IngestErrorCode.DOCLING_UNAVAILABLE
    job.error_detail = "connection refused"
    job.save()

    retry = IngestJob.objects.create(document_version=job.document_version)

    assert retry.status == IngestStatus.QUEUED


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "paused"),
        ("status", ""),
        ("step", "upload"),
        ("error_code", "oops"),
    ],
)
def test_database_accepts_listed_values_only(job: IngestJob, field: str, value: str) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        IngestJob.objects.filter(pk=job.pk).update(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [("status", "paused"), ("step", "upload"), ("error_code", "oops")],
)
def test_full_clean_accepts_listed_values_only(job: IngestJob, field: str, value: str) -> None:
    setattr(job, field, value)

    with pytest.raises(ValidationError) as caught:
        job.full_clean()

    assert field in caught.value.message_dict


@pytest.mark.parametrize("code", IngestErrorCode.values)
def test_every_error_code_is_stored(job: IngestJob, code: str) -> None:
    IngestJob.objects.filter(pk=job.pk).update(status=IngestStatus.FAILED, error_code=code)

    job.refresh_from_db()
    job.full_clean()
    assert job.error_code == code


def test_error_detail_is_limited_and_without_nul(job: IngestJob) -> None:
    job.error_detail = "x" * 2001
    with pytest.raises(ValidationError) as too_long:
        job.full_clean()
    job.error_detail = "bad\x00byte"
    with pytest.raises(ValidationError) as with_nul:
        job.full_clean()

    assert "error_detail" in too_long.value.message_dict
    assert "error_detail" in with_nul.value.message_dict


def test_result_blob_key_must_be_a_storage_key(job: IngestJob) -> None:
    job.result_blob_key = "../../etc/passwd"
    with pytest.raises(ValidationError) as caught:
        job.full_clean()
    job.result_blob_key = key_for_sha256("ef" * 32)
    job.full_clean()

    assert "result_blob_key" in caught.value.message_dict


def test_reused_from_points_to_the_source_job(job: IngestJob) -> None:
    job.status = IngestStatus.DONE
    job.result_blob_key = key_for_sha256("ef" * 32)
    job.save()
    other = make_version("hbw-plc", SHA256)

    reuse = IngestJob.objects.create(
        document_version=other, reused_from=job, result_blob_key=job.result_blob_key
    )

    assert list(job.reused_by.all()) == [reuse]


def test_requested_by_is_optional_and_kept(version: DocumentVersion) -> None:
    user = make_user("manage")

    requested = IngestJob.objects.create(
        document_version=version, requested_by=user, status=IngestStatus.DONE
    )

    assert requested.requested_by == user
    assert user is not None
    assert list(user.ingest_jobs.all()) == [requested]


# --- PROTECT ---------------------------------------------------------------


def test_version_with_jobs_cannot_be_deleted(job: IngestJob) -> None:
    with pytest.raises(ProtectedError):
        job.document_version.delete()

    assert DocumentVersion.objects.filter(pk=job.document_version.pk).exists()


def test_version_with_sections_cannot_be_deleted(job: IngestJob) -> None:
    make_section(job)
    IngestJob.objects.filter(pk=job.pk).update(status=IngestStatus.DONE)

    with pytest.raises(ProtectedError):
        job.document_version.delete()


def test_job_with_sections_cannot_be_deleted(job: IngestJob) -> None:
    make_section(job)

    with pytest.raises(ProtectedError):
        job.delete()


def test_reused_job_cannot_be_deleted(job: IngestJob) -> None:
    IngestJob.objects.create(
        document_version=make_version("hbw-plc", SHA256),
        reused_from=job,
        status=IngestStatus.DONE,
    )

    with pytest.raises(ProtectedError):
        job.delete()


def test_user_with_jobs_cannot_be_deleted(version: DocumentVersion) -> None:
    user = make_user("manage")
    assert user is not None
    IngestJob.objects.create(document_version=version, requested_by=user)

    with pytest.raises(ProtectedError):
        user.delete()


# --- Section ---------------------------------------------------------------


def test_section_without_embedding_is_normal(job: IngestJob) -> None:
    section = make_section(job, heading_path=["Safety", "Stop"])
    section.refresh_from_db()

    section.full_clean()
    assert section.embedding is None
    assert section.embedding_model == ""
    assert section.heading_text == "Safety > Stop"
    assert section.page_start is None
    assert section.page_end is None


def test_save_keeps_heading_text_in_step(job: IngestJob) -> None:
    section = make_section(job, heading_path=["A"])

    section.heading_path = ["A", "B", "C"]
    section.save(update_fields=["heading_path"])
    section.refresh_from_db()

    assert section.heading_text == "A > B > C"


def test_join_headings() -> None:
    assert join_headings([]) == ""
    assert join_headings(["Chapter 1"]) == "Chapter 1"
    assert join_headings(("Chapter 1", "Safety")) == "Chapter 1 > Safety"


def test_ordinal_is_unique_per_version(job: IngestJob) -> None:
    make_section(job, ordinal=1)
    other_job = IngestJob.objects.create(
        document_version=make_version("hbw-plc", "cd" * 32), status=IngestStatus.DONE
    )
    make_section(other_job, ordinal=1)

    with pytest.raises(IntegrityError), transaction.atomic():
        make_section(job, ordinal=1)

    assert Section.objects.count() == 2


@pytest.mark.parametrize(
    ("page_start", "page_end"),
    [(3, 2), (0, 1), (None, 1), (1, None)],
)
def test_pages_must_be_a_valid_range(
    job: IngestJob, page_start: int | None, page_end: int | None
) -> None:
    section = Section(
        document_version=job.document_version,
        ingest_job=job,
        ordinal=1,
        page_start=page_start,
        page_end=page_end,
        text="Text",
    )

    with pytest.raises(ValidationError):
        section.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        section.save()


@pytest.mark.parametrize(("page_start", "page_end"), [(1, 1), (4, 9), (None, None)])
def test_valid_pages_are_stored(
    job: IngestJob, page_start: int | None, page_end: int | None
) -> None:
    section = Section(
        document_version=job.document_version,
        ingest_job=job,
        ordinal=1,
        page_start=page_start,
        page_end=page_end,
        text="Text",
    )

    section.full_clean()
    section.save()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("text", "before\x00after"),
        ("heading_path", ["Safety", "St\x00op"]),
    ],
)
def test_full_clean_rejects_nul(job: IngestJob, field: str, value: object) -> None:
    section = Section(document_version=job.document_version, ingest_job=job, ordinal=1, text="ok")
    setattr(section, field, value)

    with pytest.raises(ValidationError) as caught:
        section.full_clean()

    assert field in caught.value.message_dict


# --- Search vector ---------------------------------------------------------


def test_search_vector_weights_heading_a_and_text_b(job: IngestJob) -> None:
    section = make_section(job, heading_path=["Wartung"], text="Pumpen running")

    found = lexemes(section)

    # simple keeps the words, german and english reduce them to stems.
    assert found["wartung"] == {"A"}
    assert found["pumpen"] == {"B"}
    assert found["pump"] == {"B"}
    assert found["running"] == {"B"}
    assert found["run"] == {"B"}


def test_search_vector_is_a_generated_column() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT attgenerated FROM pg_attribute"
            " WHERE attrelid = 'ingest_section'::regclass AND attname = 'search_vector'"
        )
        row = cursor.fetchone()

    assert row == ("s",)


def test_search_vector_follows_save(job: IngestJob) -> None:
    section = make_section(job, text="Pumpe")

    section.text = "Ventil"
    section.save()

    found = lexemes(section)
    assert "ventil" in found
    assert "pumpe" not in found


def test_search_vector_follows_queryset_update(job: IngestJob) -> None:
    section = make_section(job, heading_path=["Alt"], text="Pumpe")

    Section.objects.filter(pk=section.pk).update(text="Ventil", heading_text="Neu")

    found = lexemes(section)
    assert found["ventil"] == {"B"}
    assert found["neu"] == {"A"}
    assert "pumpe" not in found
    assert "alt" not in found


@pytest.mark.parametrize(
    ("query", "config"),
    [
        ("Pumpe", "german"),
        ("pumpen", "simple"),
        ("run", "english"),
        ("S7-1200", "simple"),
        ("192.168.0.10", "simple"),
    ],
)
def test_keyword_queries_find_the_section(job: IngestJob, query: str, config: str) -> None:
    section = make_section(job, text="Die Pumpen der S7-1200 unter 192.168.0.10 are running.")
    make_section(job, ordinal=2, text="Something else entirely.")

    found = Section.objects.filter(search_vector=SearchQuery(query, config=config))

    assert list(found) == [section]


# --- Embedding -------------------------------------------------------------


def test_embedding_of_the_right_length_is_stored(job: IngestJob) -> None:
    section = make_section(job)
    vector = [0.5] * EMBEDDING_DIMENSIONS

    section.embedding = vector
    section.embedding_model = "bge-m3"
    section.full_clean()
    section.save()
    section.refresh_from_db()

    assert section.embedding is not None
    assert list(section.embedding) == vector


@pytest.mark.parametrize("length", [3, EMBEDDING_DIMENSIONS - 1, EMBEDDING_DIMENSIONS + 1])
def test_embedding_of_another_length_is_rejected(job: IngestJob, length: int) -> None:
    section = make_section(job)
    section.embedding = [0.5] * length
    section.embedding_model = "bge-m3"

    with pytest.raises(ValidationError) as caught:
        section.full_clean()
    with pytest.raises(DataError), transaction.atomic():
        section.save()
    with pytest.raises(DataError), transaction.atomic():
        Section.objects.filter(pk=section.pk).update(embedding=[0.5] * length)

    assert "embedding" in caught.value.message_dict
    assert Section.objects.get(pk=section.pk).embedding is None


@pytest.mark.parametrize(
    ("embedding", "model"),
    [([0.5] * EMBEDDING_DIMENSIONS, ""), (None, "bge-m3")],
)
def test_embedding_and_model_come_together(
    job: IngestJob, embedding: list[float] | None, model: str
) -> None:
    section = make_section(job)

    with pytest.raises(IntegrityError), transaction.atomic():
        Section.objects.filter(pk=section.pk).update(embedding=embedding, embedding_model=model)


def test_indexes_exist() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'ingest_section'"
        )
        indexes = dict(cursor.fetchall())

    assert "USING gin (search_vector)" in indexes["ingest_section_search_gin"]
    assert "USING gin (text gin_trgm_ops)" in indexes["ingest_section_text_trgm"]
    assert "USING hnsw (embedding vector_cosine_ops)" in indexes["ingest_section_embedding_hnsw"]
    assert "(document_version_id, ordinal)" in indexes["ingest_section_version_ordinal_unique"]


def test_embedding_column_has_the_fixed_dimension() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT format_type(atttypid, atttypmod) FROM pg_attribute"
            " WHERE attrelid = 'ingest_section'::regclass AND attname = 'embedding'"
        )
        row = cursor.fetchone()

    assert row == (f"vector({EMBEDDING_DIMENSIONS})",)


# --- section_rows ----------------------------------------------------------


@dataclass(frozen=True)
class Draft:
    """Shape of a section draft from 043."""

    ordinal: int
    heading_path: tuple[str, ...]
    text: str
    page_start: int | None
    page_end: int | None


def test_section_rows_fill_heading_text_for_bulk_create(job: IngestJob) -> None:
    drafts = [
        Draft(1, ("Chapter 1", "Safety"), "Wear gloves.", 1, 2),
        Draft(2, (), "Introduction without heading.", None, None),
    ]

    rows = section_rows(drafts, job.document_version, job)
    Section.objects.bulk_create(rows)

    saved = list(Section.objects.filter(document_version=job.document_version))
    assert [s.heading_text for s in saved] == ["Chapter 1 > Safety", ""]
    assert [s.heading_path for s in saved] == [["Chapter 1", "Safety"], []]
    assert [(s.page_start, s.page_end) for s in saved] == [(1, 2), (None, None)]
    assert all(s.ingest_job_id == job.pk for s in saved)
    assert all(s.embedding is None for s in saved)
    assert lexemes(saved[0])["safeti"] == {"A"}
    assert lexemes(saved[0])["glove"] == {"B"}


def test_section_rows_query_nothing(
    job: IngestJob, django_assert_num_queries: DjangoAssertNumQueries
) -> None:
    drafts = [Draft(n, ("H",), f"Text {n}", n, n) for n in range(1, 51)]

    with django_assert_num_queries(0):
        rows = section_rows(drafts, job.document_version, job)

    assert len(rows) == 50


@pytest.mark.parametrize(
    "draft",
    [
        Draft(1, ("Head",), "with\x00nul", None, None),
        Draft(1, ("He\x00ad",), "text", None, None),
        Draft(1, ("Head",), "", None, None),
        Draft(1, ("Head",), "text", 0, 1),
    ],
)
def test_section_rows_reject_invalid_drafts(job: IngestJob, draft: Draft) -> None:
    with pytest.raises(ValidationError):
        section_rows([draft], job.document_version, job)
