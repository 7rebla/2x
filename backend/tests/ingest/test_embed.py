"""The step embed of the ingest flow and the system check of the embedding length (work order 048).

The model service is replaced by :class:`~tests.ingest.fake_converter.FakeEmbedder`;
no test reaches a real model service (``isolated_services``). Time is a fake
clock, so the time limits are tested without waiting.
"""

from collections.abc import Callable

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from django.core.checks import Error
from django.core.checks import Warning as CheckWarning
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from pytest_django.fixtures import Settings

from tests.conftest import IngestMessages
from tests.ingest.fake_converter import (
    FAKE_MODEL,
    FakeConverter,
    FakeEmbedder,
    NoDocling,
    add_sections,
    install_embedder,
    isolated_services,
    make_embed_job,
    make_job,
    make_version,
    run_job,
    vector_for,
)
from twox.answers.embeddings import (
    EmbeddingDimensionError,
    EmbeddingDisabledError,
    EmbeddingRejectedError,
    EmbeddingRemoteModelError,
    EmbeddingUnavailableError,
)
from twox.files.models import DocumentVersion
from twox.ingest import checks, pipeline, tasks
from twox.ingest.models import EMBEDDING_DIMENSIONS, IngestJob, IngestStatus, IngestStep, Section
from twox.ingest.pipeline import Outcome, StepResult

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("isolated_services")]

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]


@pytest.fixture(autouse=True)
def embed_settings(settings: Settings) -> None:
    """The defaults of work orders 044 and 045, independent of the .env of the run."""
    settings.TWOX_INGEST_MAX_RETRIES = 5
    settings.TWOX_INGEST_POLL_MIN_SECONDS = 10
    settings.TWOX_INGEST_POLL_MAX_SECONDS = 60
    settings.TWOX_EMBED_BATCH_SIZE = 2
    settings.TWOX_EMBED_TIMEOUT_SECONDS = 120
    settings.TWOX_EMBED_TASK_MAX_SECONDS = 240
    settings.TWOX_TASK_SOFT_TIME_LIMIT = 300


class FakeClock:
    """Monotonic seconds that only move when a test says so."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> Callable[[], None]:
        def step() -> None:
            self.now += seconds

        return step


def stored(version: DocumentVersion) -> list[tuple[int, str, list[float] | None]]:
    return [
        (
            section.ordinal,
            section.embedding_model,
            None if section.embedding is None else [float(v) for v in section.embedding],
        )
        for section in Section.objects.filter(document_version=version).order_by("ordinal")
    ]


def embedded_ordinals(version: DocumentVersion) -> list[int]:
    return list(
        Section.objects.filter(document_version=version, embedding__isnull=False)
        .order_by("ordinal")
        .values_list("ordinal", flat=True)
    )


def run_embedding(job: IngestJob, *, clock: Callable[[], float] | None = None) -> StepResult:
    result = pipeline.embed(job.pk) if clock is None else pipeline.embed(job.pk, clock=clock)
    job.refresh_from_db()
    return result


# --- Whole step ----------------------------------------------------------------------


def test_embeddings_and_model_name_are_stored_and_the_job_is_done(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    job = make_embed_job(version, sections=5)

    result = run_embedding(job)

    assert result == StepResult(Outcome.DONE)
    assert (job.status, job.step, job.error_code, job.error_detail) == (
        IngestStatus.DONE,
        IngestStep.EMBED,
        "",
        "",
    )
    assert job.started_at is not None
    assert job.finished_at is not None
    assert job.attempts == 0
    # Batches of TWOX_EMBED_BATCH_SIZE, in the order of the sections.
    assert embedder.batches == [2, 2, 1]
    assert embedder.texts == [f"Chapter > Part {n}\n\nText {n}" for n in range(5)]
    assert stored(version) == [(n, FAKE_MODEL, vector_for(n)) for n in range(5)]


def test_text_without_headings_is_embedded_alone() -> None:
    assert pipeline.embedding_text("", "Only text") == "Only text"
    assert pipeline.embedding_text("A > B", "Text") == "A > B\n\nText"


def test_ingest_flow_continues_with_embed_and_ends_done(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    job = make_job(version)

    results = run_job(job, FakeConverter())
    assert results[-1] == StepResult(Outcome.EMBEDDING, embed_after=0)
    final = run_embedding(job)

    assert final == StepResult(Outcome.DONE)
    assert (job.status, job.step) == (IngestStatus.DONE, IngestStep.EMBED)
    count = Section.objects.filter(document_version=version).count()
    assert job.section_count == count == len(embedder.texts) > 0
    assert set(Section.objects.values_list("embedding_model", flat=True)) == {FAKE_MODEL}


def test_version_without_sections_is_done_without_asking_the_model(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    job = IngestJob.objects.create(
        document_version=make_version(), status=IngestStatus.QUEUED, step=IngestStep.EMBED
    )

    assert run_embedding(job) == StepResult(Outcome.DONE)
    assert embedder.texts == []


def test_sections_of_another_model_are_embedded_again(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    job = make_embed_job(version, sections=3)
    Section.objects.filter(document_version=version, ordinal=0).update(
        embedding=vector_for(500), embedding_model="old-model"
    )
    Section.objects.filter(document_version=version, ordinal=1).update(
        embedding=vector_for(501), embedding_model=FAKE_MODEL
    )

    run_embedding(job)

    assert embedder.texts == ["Chapter > Part 0\n\nText 0", "Chapter > Part 2\n\nText 2"]
    assert stored(version) == [
        (0, FAKE_MODEL, vector_for(0)),
        (1, FAKE_MODEL, vector_for(501)),
        (2, FAKE_MODEL, vector_for(1)),
    ]


# --- Batches, errors in between and time limits -----------------------------------------


def test_error_in_the_second_batch_keeps_the_first_and_the_retry_embeds_only_the_rest(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    embedder.errors = [None, EmbeddingUnavailableError("no answer from the model service")]
    version = make_version()
    job = make_embed_job(version, sections=5)

    first = run_embedding(job)

    assert first == StepResult(Outcome.EMBEDDING, embed_after=10)
    assert (job.status, job.step, job.attempts) == (IngestStatus.RUNNING, IngestStep.EMBED, 1)
    assert embedded_ordinals(version) == [0, 1]

    second = run_embedding(job)

    assert second == StepResult(Outcome.DONE)
    assert job.status == IngestStatus.DONE
    assert embedder.batches == [2, 2, 1]
    assert embedder.texts == [f"Chapter > Part {n}\n\nText {n}" for n in range(5)]
    assert embedded_ordinals(version) == [0, 1, 2, 3, 4]


def test_time_limit_schedules_the_rest_in_a_new_task(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.TWOX_EMBED_BATCH_SIZE = 1
    clock = FakeClock()
    embedder = install_embedder(monkeypatch, settings, FakeEmbedder())
    embedder.after_batch = clock.advance(100)
    version = make_version()
    job = make_embed_job(version, sections=5)

    # 100 s per batch: after two batches only 100 s are left before the soft
    # limit of 300 s, less than one request may take (120 s).
    first = run_embedding(job, clock=clock)

    assert first == StepResult(Outcome.EMBEDDING, embed_after=0)
    assert (job.status, job.attempts) == (IngestStatus.RUNNING, 0)
    assert embedded_ordinals(version) == [0, 1]

    second = run_embedding(job, clock=clock)

    assert second == StepResult(Outcome.EMBEDDING, embed_after=0)
    assert embedded_ordinals(version) == [0, 1, 2, 3]

    third = run_embedding(job, clock=clock)

    assert third == StepResult(Outcome.DONE)
    assert job.status == IngestStatus.DONE
    assert len(embedder.texts) == len(set(embedder.texts)) == 5


def test_every_task_embeds_at_least_one_batch(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.TWOX_EMBED_BATCH_SIZE = 1
    clock = FakeClock()
    embedder = install_embedder(monkeypatch, settings)
    embedder.after_batch = clock.advance(1000)
    version = make_version()
    job = make_embed_job(version, sections=2)

    assert run_embedding(job, clock=clock).outcome == Outcome.EMBEDDING
    assert embedded_ordinals(version) == [0]
    assert run_embedding(job, clock=clock).outcome == Outcome.DONE


@pytest.mark.parametrize(
    ("elapsed", "pause"),
    [(0, False), (179.9, False), (180, False), (180.1, True), (239, True), (240, True)],
)
def test_no_new_batch_when_less_than_the_request_limit_is_left_before_the_soft_limit(
    elapsed: float, pause: bool
) -> None:
    # Review of 045: socket limit 120 s plus 240 s could pass the soft limit
    # of 300 s; a batch starts only while 120 s are left.
    assert pipeline.should_pause(elapsed) is pause


@pytest.mark.parametrize(
    ("elapsed", "pause"), [(0, False), (239.9, False), (240, True), (260, True)]
)
def test_task_time_limit_applies_with_a_short_request_limit(
    settings: Settings, elapsed: float, pause: bool
) -> None:
    settings.TWOX_EMBED_TIMEOUT_SECONDS = 30

    assert pipeline.should_pause(elapsed) is pause


# --- Taking over embeddings of the same content ---------------------------------------


def embedded_copy(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> tuple[DocumentVersion, DocumentVersion]:
    """A version with embeddings and a second version with the same content and sections."""
    install_embedder(monkeypatch, settings)
    first = make_version(device="dps-plc")
    run_embedding(make_embed_job(first, sections=3))
    second = make_version(device="hbw-plc", filename="copy.pdf")
    assert second.sha256 == first.sha256
    add_sections(second, 3)
    return first, second


def test_same_content_takes_over_the_embeddings_without_asking_the_model(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = embedded_copy(settings, monkeypatch)
    embedder = install_embedder(monkeypatch, settings)
    job = IngestJob.objects.create(
        document_version=second, status=IngestStatus.QUEUED, step=IngestStep.EMBED
    )

    assert run_embedding(job) == StepResult(Outcome.DONE)

    assert embedder.texts == []
    assert stored(second) == stored(first)
    assert [model for _, model, _ in stored(second)] == [FAKE_MODEL] * 3


def test_only_sections_with_the_same_ordinal_heading_and_text_are_taken_over(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = embedded_copy(settings, monkeypatch)
    Section.objects.filter(document_version=second, ordinal=1).update(text="Changed text")
    Section.objects.filter(document_version=second, ordinal=2).update(heading_text="Other")
    embedder = install_embedder(monkeypatch, settings)
    job = IngestJob.objects.create(
        document_version=second, status=IngestStatus.QUEUED, step=IngestStep.EMBED
    )

    run_embedding(job)

    assert embedder.texts == ["Chapter > Part 1\n\nChanged text", "Other\n\nText 2"]
    assert stored(second)[0] == stored(first)[0]


def test_embeddings_of_another_model_or_other_content_are_not_taken_over(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = embedded_copy(settings, monkeypatch)
    other = make_version(b"other content", device="vgr-plc")
    add_sections(other, 3)
    Section.objects.filter(document_version=other).update(
        embedding=vector_for(900), embedding_model=FAKE_MODEL
    )
    embedder = install_embedder(monkeypatch, settings, FakeEmbedder(model="another-model"))
    job = IngestJob.objects.create(
        document_version=second, status=IngestStatus.QUEUED, step=IngestStep.EMBED
    )

    run_embedding(job)

    assert len(embedder.texts) == 3
    assert {model for _, model, _ in stored(second)} == {"another-model"}
    assert {model for _, model, _ in stored(first)} == {FAKE_MODEL}


# --- Errors -------------------------------------------------------------------------


def test_unreachable_model_service_is_retried_with_growing_delay_and_then_fails(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    embedder.errors = [
        EmbeddingUnavailableError("the model service refused the connection (is Ollama running?)")
    ] * 6
    version = make_version()
    job = make_embed_job(version, sections=3)

    delays = [run_embedding(job).embed_after for _ in range(5)]
    last = run_embedding(job)

    assert delays == [10, 20, 40, 60, 60]
    assert last == StepResult(Outcome.FAILED)
    assert (job.status, job.step, job.error_code) == (
        IngestStatus.FAILED,
        IngestStep.EMBED,
        "embedding_unavailable",
    )
    assert job.error_detail == (
        "the model service refused the connection (is Ollama running?) (gave up after 5 retries)"
    )
    assert job.finished_at is not None
    # The sections stay and remain searchable by keywords.
    assert Section.objects.filter(document_version=version).count() == 3
    assert embedded_ordinals(version) == []


@pytest.mark.parametrize(
    ("error", "code", "detail"),
    [
        (
            EmbeddingRejectedError(
                "model 'fake-embed' is not loaded in Ollama; load it with: ollama pull fake-embed"
            ),
            "embedding_rejected",
            "model 'fake-embed' is not loaded in Ollama; load it with: ollama pull fake-embed",
        ),
        (
            EmbeddingRejectedError("the model service refused the request (HTTP 400)"),
            "embedding_rejected",
            "the model service refused the request (HTTP 400); if the model is not loaded,"
            " load it with: ollama pull fake-embed",
        ),
        (
            EmbeddingRemoteModelError(
                "model 'x:cloud' is an Ollama cloud model; only local models are allowed"
            ),
            "embedding_rejected",
            "model 'x:cloud' is an Ollama cloud model; only local models are allowed",
        ),
        (
            EmbeddingDimensionError("model 'fake-embed' returned 768 values, expected 1024"),
            "embedding_dimension_mismatch",
            "model 'fake-embed' returned 768 values, expected 1024",
        ),
        (SoftTimeLimitExceeded(), "timeout", "an ingest step ran past the time limit"),
        (RuntimeError("boom"), "internal", pipeline.INTERNAL_DETAIL),
    ],
    ids=["rejected-pull", "rejected-http", "remote", "dimension", "soft-limit", "internal"],
)
def test_each_kind_of_error_ends_with_its_status(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    code: str,
    detail: str,
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    embedder.errors = [None, error]
    version = make_version()
    job = make_embed_job(version, sections=4)

    result = run_embedding(job)

    assert result == StepResult(Outcome.FAILED)
    assert (job.status, job.step, job.error_code, job.error_detail) == (
        IngestStatus.FAILED,
        IngestStep.EMBED,
        code,
        detail,
    )
    assert job.attempts == 0
    assert job.finished_at is not None
    # What was embedded before the error stays.
    assert embedded_ordinals(version) == [0, 1]


def test_section_texts_never_reach_the_log(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    embedder.errors = [None, EmbeddingUnavailableError("no answer"), RuntimeError("boom")]
    version = make_version()
    job = make_embed_job(version, sections=4)

    with caplog.at_level("DEBUG"):
        run_embedding(job)
        run_embedding(job)

    assert job.error_code == "internal"
    assert "Text 1" not in caplog.text
    assert "Part 1" not in caplog.text


def test_ai_switched_off_ends_the_job_without_asking_the_model(settings: Settings) -> None:
    # E-59: isolated_services fails the test if the model service is asked.
    settings.TWOX_AI_ENABLED = False
    version = make_version()
    job = make_embed_job(version, sections=3)

    assert run_embedding(job) == StepResult(Outcome.DONE)
    assert (job.status, job.error_code) == (IngestStatus.DONE, "")
    assert embedded_ordinals(version) == []


def test_ai_switched_off_in_the_embedding_interface_ends_the_job_neutrally(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    embedder.errors = [EmbeddingDisabledError("AI features are not enabled")]
    job = make_embed_job(make_version(), sections=3)

    assert run_embedding(job) == StepResult(Outcome.DONE)
    assert (job.status, job.error_code) == (IngestStatus.DONE, "")


# --- Dimensions ---------------------------------------------------------------------


def test_dimension_setting_that_does_not_fit_the_column_fails_before_the_model_is_asked(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    settings.TWOX_EMBED_DIMENSIONS = 768
    version = make_version()
    job = make_embed_job(version, sections=3)

    result = run_embedding(job)

    assert result == StepResult(Outcome.FAILED)
    assert (job.status, job.error_code) == (IngestStatus.FAILED, "embedding_dimension_mismatch")
    assert job.error_detail == (
        "TWOX_EMBED_DIMENSIONS is 768, but the embedding column of the sections has 1024"
        " dimensions; no embedding could be stored"
    )
    assert embedder.texts == []


def test_embedder_with_other_dimensions_fails_before_it_is_asked(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings, FakeEmbedder(size=768))
    job = make_embed_job(make_version(), sections=3)

    assert run_embedding(job) == StepResult(Outcome.FAILED)
    assert job.error_code == "embedding_dimension_mismatch"
    assert embedder.texts == []


def test_vector_of_the_wrong_length_is_not_written(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    monkeypatch.setattr(embedder, "embed_documents", lambda texts: [[0.5] * 3 for _ in texts])
    version = make_version()
    job = make_embed_job(version, sections=3)

    assert run_embedding(job) == StepResult(Outcome.FAILED)
    assert job.error_code == "embedding_dimension_mismatch"
    assert embedded_ordinals(version) == []


def test_column_dimensions_come_from_the_model() -> None:
    assert checks.embedding_column_dimensions() == EMBEDDING_DIMENSIONS == 1024


def test_system_check_passes_when_the_setting_fits(settings: Settings) -> None:
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_EMBED_DIMENSIONS = 1024

    assert checks.check_embedding_dimensions() == []
    call_command("check")


def test_system_check_fails_with_ai_on_when_the_setting_does_not_fit(settings: Settings) -> None:
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_EMBED_DIMENSIONS = 768

    [message] = checks.check_embedding_dimensions()
    assert isinstance(message, Error)
    assert message.id == "twox.ingest.E001"
    assert "TWOX_EMBED_DIMENSIONS is 768" in message.msg
    assert message.hint is not None
    assert "TWOX_EMBED_DIMENSIONS=1024" in message.hint
    with pytest.raises(SystemCheckError, match=r"twox\.ingest\.E001"):
        call_command("check")


def test_system_check_only_warns_with_ai_off(settings: Settings) -> None:
    # E-59: without AI nothing is embedded; the product still starts.
    settings.TWOX_AI_ENABLED = False
    settings.TWOX_EMBED_DIMENSIONS = 768

    [message] = checks.check_embedding_dimensions()
    assert isinstance(message, CheckWarning)
    assert message.id == "twox.ingest.W001"
    call_command("check")


# --- Job states ---------------------------------------------------------------------


def test_unknown_job_is_logged_and_ignored(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="twox.ingest.pipeline"):
        assert pipeline.embed(9_000_000_000_000_000_000) == StepResult(Outcome.MISSING)
        assert pipeline.embed("7") == StepResult(Outcome.MISSING)

    assert "does not exist" in caplog.text
    assert "invalid job ID" in caplog.text


@pytest.mark.parametrize(
    ("status", "step"),
    [
        (IngestStatus.DONE, IngestStep.EMBED),
        (IngestStatus.FAILED, IngestStep.EMBED),
        (IngestStatus.RUNNING, IngestStep.CONVERT),
        (IngestStatus.QUEUED, ""),
        (IngestStatus.RUNNING, IngestStep.SECTIONS),
    ],
)
def test_job_in_another_state_is_left_alone(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, status: str, step: str
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    job = make_embed_job(version, sections=2)
    IngestJob.objects.filter(pk=job.pk).update(status=status, step=step)

    assert run_embedding(job) == StepResult(Outcome.IGNORED)
    assert (job.status, job.step) == (status, step)
    assert embedder.texts == []


def test_stray_poll_or_convert_does_not_touch_a_job_in_the_step_embed(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A repeated poll after the sections would build them again and drop the
    # embeddings; convert would take over a job that embed_sections created.
    install_embedder(monkeypatch, settings)
    version = make_version()
    job = make_job(version)
    run_job(job, FakeConverter())
    Section.objects.filter(document_version=version, ordinal=0).update(
        embedding=vector_for(7), embedding_model=FAKE_MODEL
    )
    queued = make_embed_job(make_version(b"other", device="hbw-plc"))

    # Review of 048: if the message embed was lost, such a message schedules
    # embed again instead of being dropped (embed only does what is missing).
    again = StepResult(Outcome.EMBEDDING, embed_after=0)
    assert pipeline.poll(job.pk, converter=NoDocling()) == again
    assert pipeline.convert(job.pk, converter=NoDocling()) == again
    assert pipeline.convert(queued.pk, converter=NoDocling()) == again

    job.refresh_from_db()
    queued.refresh_from_db()
    assert (job.status, job.step) == (IngestStatus.RUNNING, IngestStep.EMBED)
    assert (queued.status, queued.step) == (IngestStatus.QUEUED, IngestStep.EMBED)
    assert embedded_ordinals(version) == [0]
    assert Section.objects.filter(document_version=version).count() == job.section_count


def test_stray_message_for_a_job_in_the_step_embed_ends_it_when_ai_is_off(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # E-59: without AI there is no task embed to schedule.
    install_embedder(monkeypatch, settings)
    job = make_job(make_version())
    run_job(job, FakeConverter())
    settings.TWOX_AI_ENABLED = False

    assert pipeline.poll(job.pk, converter=NoDocling()) == StepResult(Outcome.DONE)

    job.refresh_from_db()
    assert (job.status, job.step, job.error_code) == (IngestStatus.DONE, IngestStep.EMBED, "")


def test_lost_embed_message_is_recovered_by_a_poll_task(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, ingest_messages: IngestMessages
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    job = make_job(version)
    run_job(job, FakeConverter())  # the result asks for embed; nobody sends it

    assert tasks.poll(job.pk) == "embedding"
    assert ingest_messages.sent == [("twox.ingest.embed", (job.pk,))]
    assert tasks.embed(job.pk) == "done"

    job.refresh_from_db()
    assert job.status == IngestStatus.DONE
    assert len(embedder.texts) == job.section_count


def test_a_second_message_for_a_done_job_changes_nothing(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    job = make_embed_job(make_version(), sections=2)
    run_embedding(job)
    finished = job.finished_at

    assert run_embedding(job) == StepResult(Outcome.IGNORED)
    assert job.finished_at == finished
    assert len(embedder.texts) == 2
