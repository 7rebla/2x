"""The field ``conversion_error_count`` in the ingest flow and the API (E-62, work order 068).

A conversion that Docling finished only in part (``partial_success``) keeps
the number of its errors in a field of its own, no longer only as text in
``error_detail``. The field survives a failed embedding, decides whether an
answer is reused, and gives ``partly_converted`` in the API. Docling and the
model service are stand-ins (``isolated_services``).
"""

from pathlib import Path
from typing import Any

import pytest
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient

from tests.files.helpers import client_for
from tests.ingest.fake_converter import (
    FakeConverter,
    FakeEmbedder,
    NoDocling,
    install_embedder,
    isolated_services,
    make_job,
    make_version,
    run_job,
)
from tests.ingest.fake_docling import fixture_document, result_answer
from twox.answers.embeddings import EmbeddingUnavailableError
from twox.files.models import DocumentVersion
from twox.ingest import pipeline
from twox.ingest.docling import ConversionErrorItem, TaskStatus
from twox.ingest.models import IngestJob, IngestStatus, IngestStep
from twox.ingest.pipeline import Outcome

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("isolated_services")]

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]

#: Three errors of a partial conversion, two of them on pages.
ERRORS: list[dict[str, Any]] = [
    {
        "component_type": "model",
        "module_name": "table_structure",
        "error_message": "table could not be read",
        "page_no": 4,
    },
    {
        "component_type": "model",
        "module_name": "ocr",
        "error_message": "page could not be read",
        "page_no": 2,
    },
    {
        "component_type": "document_backend",
        "module_name": "pdf",
        "error_message": "timeout",
        "page_no": None,
    },
]


@pytest.fixture(autouse=True)
def ingest_settings(settings: Settings) -> None:
    """The defaults of work orders 045 and 048, independent of the .env of the run."""
    settings.TWOX_INGEST_MAX_RETRIES = 5
    settings.TWOX_INGEST_POLL_MIN_SECONDS = 10
    settings.TWOX_INGEST_POLL_MAX_SECONDS = 60
    settings.TWOX_SECTION_MAX_CHARS = 2000
    settings.TWOX_EMBED_BATCH_SIZE = 16


@pytest.fixture(params=[True, False], ids=["ai_on", "ai_off"])
def embedder(
    request: pytest.FixtureRequest,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    isolated_services: Path,
) -> FakeEmbedder | None:
    """The embedding stand-in with the AI features on; ``None`` with them off (E-59)."""
    if request.param:
        return install_embedder(monkeypatch, settings)
    return None


def partial_converter() -> FakeConverter:
    answer = result_answer(fixture_document(), status="partial_success", errors=ERRORS)
    return FakeConverter(statuses=[TaskStatus.PARTIAL_SUCCESS], answer=answer)


def run_to_the_end(job: IngestJob, converter: FakeConverter | NoDocling) -> IngestJob:
    """Convert, then embed as the worker would (with the AI features on)."""
    result = run_job(job, converter)[-1]
    for _ in range(20):
        if result.outcome != Outcome.EMBEDDING:
            break
        result = pipeline.embed(job.pk)
    else:
        pytest.fail("the embedding never ended")
    job.refresh_from_db()
    return job


def api_state(client: APIClient, version: DocumentVersion) -> tuple[dict[str, Any], dict[str, Any]]:
    """The newest job of ``version``: field ``ingest`` of the files API and its row in the list."""
    detail = client.get(f"/api/v1/documents/{version.document_id}/").json()
    listing = client.get(f"/api/v1/ingest-jobs/?version={version.pk}&latest=true").json()
    [row] = listing["results"]
    ingest: dict[str, Any] = detail["latest_version"]["ingest"]
    return ingest, row


# --- the ingest flow ----------------------------------------------------------------


def test_partial_success_sets_the_count(embedder: FakeEmbedder | None) -> None:
    job = make_job(make_version())

    run_to_the_end(job, partial_converter())

    assert (job.status, job.error_code) == (IngestStatus.DONE, "")
    assert job.conversion_error_count == 3
    # The note for people stays: count and pages, nothing from the messages.
    assert job.error_detail == "converted with 3 errors on pages 2, 4"
    assert job.section_count and job.section_count > 0
    assert job.step == (IngestStep.EMBED if embedder is not None else IngestStep.SECTIONS)


def test_complete_conversion_has_no_conversion_errors(embedder: FakeEmbedder | None) -> None:
    job = make_job(make_version())

    run_to_the_end(job, FakeConverter())

    assert job.status == IngestStatus.DONE
    assert (job.conversion_error_count, job.error_detail) == (0, "")


def test_partial_success_without_listed_errors_counts_one() -> None:
    answer = result_answer(fixture_document(), status="partial_success", errors=[])
    job = make_job(make_version())

    run_job(job, FakeConverter(statuses=[TaskStatus.PARTIAL_SUCCESS], answer=answer))

    assert (job.conversion_error_count, job.error_detail) == (1, "converted with 1 errors")


def test_a_new_conversion_of_the_version_sets_the_count_again() -> None:
    version = make_version()
    partial = make_job(version)
    run_job(partial, partial_converter())
    complete = make_job(version)

    run_job(complete, FakeConverter())

    partial.refresh_from_db()
    assert (partial.conversion_error_count, complete.conversion_error_count) == (3, 0)


@pytest.mark.parametrize("kind", ["read", "manage"])
def test_partial_conversion_with_failed_embedding_stays_partly_converted(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    # The gap of 048 and 061: the error text of the embedding replaces the
    # note; the field keeps the count, the API still says partly converted.
    embedder = install_embedder(monkeypatch, settings)
    embedder.errors = [EmbeddingUnavailableError("no answer from the model service")] * 20
    version = make_version()
    job = make_job(version)

    run_to_the_end(job, partial_converter())

    assert (job.status, job.step, job.error_code) == (
        IngestStatus.FAILED,
        IngestStep.EMBED,
        "embedding_unavailable",
    )
    assert "gave up after" in job.error_detail
    assert job.conversion_error_count == 3
    ingest, row = api_state(client_for(kind), version)
    for state in (ingest, row):
        assert (state["id"], state["status"], state["step"]) == (job.pk, "failed", "embed")
        assert (state["partly_converted"], state["conversion_error_count"]) == (True, 3)


@pytest.mark.parametrize("kind", ["read", "manage"])
def test_api_shows_the_count_of_the_flow(embedder: FakeEmbedder | None, kind: str) -> None:
    partial_version = make_version()
    partial = make_job(partial_version)
    run_to_the_end(partial, partial_converter())
    complete_version = make_version(b"%PDF-1.7 complete\n", device="hbw-plc")
    complete = make_job(complete_version)
    run_to_the_end(complete, FakeConverter())

    client = client_for(kind)
    for version, expected in ((partial_version, (True, 3)), (complete_version, (False, 0))):
        ingest, row = api_state(client, version)
        assert ingest["status"] == row["status"] == "done"
        assert (ingest["partly_converted"], ingest["conversion_error_count"]) == expected
        assert (row["partly_converted"], row["conversion_error_count"]) == expected


# --- reuse (046, 048) -----------------------------------------------------------------


def test_reused_answer_carries_the_count_of_the_complete_conversion(
    embedder: FakeEmbedder | None,
) -> None:
    first = make_job(make_version(device="dps-plc"))
    run_to_the_end(first, FakeConverter())
    second = make_job(make_version(device="hbw-plc"))

    run_to_the_end(second, NoDocling())

    assert second.reused_from_id == first.pk
    assert second.status == IngestStatus.DONE
    assert (second.conversion_error_count, second.error_detail) == (0, "")


def test_partial_answer_is_not_reused_by_its_count(embedder: FakeEmbedder | None) -> None:
    first = make_job(make_version(device="dps-plc"))
    run_to_the_end(first, partial_converter())
    second = make_job(make_version(device="hbw-plc"))
    converter = FakeConverter()

    run_to_the_end(second, converter)

    assert second.reused_from_id is None
    assert len(converter.submissions) == 1
    assert (second.conversion_error_count, second.error_detail) == (0, "")


def stored_done_job(content: bytes, device: str, **fields: Any) -> IngestJob:  # noqa: ANN401
    """A done job of a new version whose complete Docling answer is stored."""
    version = make_version(content, device=device)
    run_job(make_job(version), FakeConverter())
    job = IngestJob.objects.get(document_version=version)
    assert (job.status, job.result_blob_key != "") == (IngestStatus.DONE, True)
    IngestJob.objects.filter(pk=job.pk).update(**fields)
    return job


def test_reuse_follows_the_field_not_the_text() -> None:
    # A count without the note: not reused. The note without a count (for
    # example a text written by hand): reused; only the field decides.
    content = b"%PDF-1.7 same content\n"
    counted = stored_done_job(content, "dps-plc", conversion_error_count=2, error_detail="")
    worded = stored_done_job(
        b"%PDF-1.7 other content\n",
        "hbw-plc",
        conversion_error_count=0,
        error_detail=pipeline.partial_detail(5),
    )
    assert counted.pk != worded.pk

    again = make_job(make_version(content, device="vgr-plc"))
    converter = FakeConverter()
    run_job(again, converter)
    assert again.reused_from_id is None
    assert len(converter.submissions) == 1

    worded_again = make_job(make_version(b"%PDF-1.7 other content\n", device="mpo-plc"))
    run_job(worded_again, NoDocling())
    assert worded_again.reused_from_id == worded.pk
    assert worded_again.conversion_error_count == 0


# --- the note ---------------------------------------------------------------------------


def test_conversion_error_count_is_at_least_one() -> None:
    item = ConversionErrorItem(
        component_type="model", module_name="ocr", error_message="x", page_no=1
    )

    assert pipeline.conversion_error_count(()) == 1
    assert pipeline.conversion_error_count((item,)) == 1
    assert pipeline.conversion_error_count((item, item, item)) == 3


def test_partial_detail_names_count_and_pages() -> None:
    assert pipeline.partial_detail(2) == "converted with 2 errors"
    assert pipeline.partial_detail(3, [7, 3, 3]) == "converted with 3 errors on pages 3, 7"
    many = pipeline.partial_detail(30, range(30, 0, -1))
    assert many.endswith("on pages " + ", ".join(str(page) for page in range(1, 21)))
