"""The step embed writes the pieces of the sections (work order 150, E-75).

The model service is replaced by :class:`~tests.ingest.fake_converter.FakeEmbedder`:
the ``n``-th embedded text gets :func:`~tests.ingest.fake_converter.vector_for`
``(n)``, so a test sees which vector went where. A piece size of 20 characters
keeps the texts short.
"""

from collections.abc import Callable, Sequence

import pytest
from pytest_django.fixtures import Settings

from tests.ingest.fake_converter import (
    FAKE_MODEL,
    FakeEmbedder,
    install_embedder,
    isolated_services,
    make_version,
    vector_for,
)
from twox.answers.embeddings import EmbeddingUnavailableError
from twox.files.models import DocumentVersion
from twox.ingest import pipeline
from twox.ingest.models import (
    IngestJob,
    IngestStatus,
    IngestStep,
    Section,
    SectionPiece,
    section_rows,
)
from twox.ingest.pipeline import Outcome, StepResult, needs_embedding
from twox.ingest.sections import SectionDraft

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("isolated_services")]

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]

#: Piece size of these tests.
PIECE = 20
SHORT = "Short text."
#: Three pieces of at most 20 characters.
LONG = "Check the oil level before every shift and refill it."
LONG_PIECES = ["Check the oil level", "before every shift", "and refill it."]
HEADING = "Pump > Service"


@pytest.fixture(autouse=True)
def piece_settings(settings: Settings) -> None:
    settings.TWOX_PIECE_MAX_CHARS = PIECE
    settings.TWOX_EMBED_BATCH_SIZE = 4
    settings.TWOX_INGEST_MAX_RETRIES = 5
    settings.TWOX_INGEST_POLL_MIN_SECONDS = 10
    settings.TWOX_INGEST_POLL_MAX_SECONDS = 60
    settings.TWOX_EMBED_TIMEOUT_SECONDS = 120
    settings.TWOX_EMBED_TASK_MAX_SECONDS = 240
    settings.TWOX_TASK_SOFT_TIME_LIMIT = 300


def add_texts(version: DocumentVersion, *texts: str) -> list[Section]:
    """Sections of ``version`` with ``texts``, all under :data:`HEADING`."""
    job = IngestJob.objects.create(
        document_version=version, status=IngestStatus.DONE, step=IngestStep.SECTIONS
    )
    drafts = [
        SectionDraft(
            ordinal=ordinal,
            heading_path=tuple(HEADING.split(" > ")),
            text=text,
            page_start=1,
            page_end=1,
        )
        for ordinal, text in enumerate(texts)
    ]
    return Section.objects.bulk_create(section_rows(drafts, version, job))


def embed_job(version: DocumentVersion) -> IngestJob:
    return IngestJob.objects.create(
        document_version=version, status=IngestStatus.QUEUED, step=IngestStep.EMBED
    )


def run(job: IngestJob, clock: Callable[[], float] | None = None) -> StepResult:
    result = pipeline.embed(job.pk) if clock is None else pipeline.embed(job.pk, clock=clock)
    job.refresh_from_db()
    return result


def text_of(piece: str) -> str:
    return f"{HEADING}\n\n{piece}"


def pieces_of(section: Section) -> list[tuple[str, str, list[float]]]:
    """Text, model and vector of every piece of ``section``, in order."""
    section.refresh_from_db()
    return [
        (section.piece_text(piece), piece.embedding_model, [float(v) for v in piece.embedding])
        for piece in SectionPiece.objects.filter(section=section).order_by("ordinal")
    ]


def section_vector(section: Section) -> list[float] | None:
    section.refresh_from_db()
    return None if section.embedding is None else [float(v) for v in section.embedding]


def set_embedding(
    sections: Sequence[Section], vector: list[float], model: str = FAKE_MODEL
) -> None:
    """An embedding of the section only, as before 150 (no pieces)."""
    Section.objects.filter(pk__in=[s.pk for s in sections]).update(
        embedding=vector, embedding_model=model
    )


# --- Pieces arise ------------------------------------------------------------------------


def test_a_long_section_gets_a_vector_per_piece_and_a_short_one_the_vector_of_the_section(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    short, long = add_texts(version, SHORT, LONG)

    assert run(embed_job(version)) == StepResult(Outcome.DONE)

    # The section first, then its pieces; the short section is asked once.
    assert embedder.texts == [
        text_of(SHORT),
        text_of(LONG),
        *(text_of(piece) for piece in LONG_PIECES),
    ]
    assert section_vector(short) == vector_for(0)
    assert pieces_of(short) == [(SHORT, FAKE_MODEL, vector_for(0))]
    # The section keeps a vector of its own (context selection, E-61).
    assert section_vector(long) == vector_for(1)
    assert pieces_of(long) == [
        (piece, FAKE_MODEL, vector_for(2 + index)) for index, piece in enumerate(LONG_PIECES)
    ]
    spans = list(
        SectionPiece.objects.filter(section=long)
        .order_by("ordinal")
        .values_list("ordinal", "char_start", "char_end")
    )
    assert spans == [(0, 0, 19), (1, 20, 38), (2, 39, 53)]


def test_requests_hold_at_most_the_batch_size(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    add_texts(version, SHORT, LONG, SHORT + " 2", LONG)

    run(embed_job(version))

    # 1 + 4 texts do not fit into 4: the first request holds the short
    # section alone; a long section (4 texts) fills a request of its own.
    assert embedder.batches == [1, 4, 1, 4]
    assert SectionPiece.objects.filter(section__document_version=version).count() == 8


def test_a_section_with_more_texts_than_a_request_holds_goes_out_in_several(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.TWOX_EMBED_BATCH_SIZE = 2
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    (long,) = add_texts(version, LONG)

    run(embed_job(version))

    assert embedder.batches == [2, 2]
    assert [text for text, _, _ in pieces_of(long)] == LONG_PIECES


def test_heading_path_is_in_front_of_every_piece_and_a_section_without_one_is_embedded_alone(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    (section,) = add_texts(version, LONG)
    Section.objects.filter(pk=section.pk).update(heading_path=[], heading_text="")

    run(embed_job(version))

    assert embedder.texts == [LONG, *LONG_PIECES]


# --- Sections embedded before 150 (the way to embed again) -------------------------------


def test_sections_without_pieces_need_embedding_and_only_long_ones_ask_the_model(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    short, long = add_texts(version, SHORT, LONG)
    set_embedding([short, long], vector_for(700))
    assert set(Section.objects.filter(needs_embedding(FAKE_MODEL))) == {short, long}

    run(embed_job(version))

    # Only the pieces of the long section; the sections keep their vectors.
    assert embedder.texts == [text_of(piece) for piece in LONG_PIECES]
    assert section_vector(short) == section_vector(long) == vector_for(700)
    assert pieces_of(short) == [(SHORT, FAKE_MODEL, vector_for(700))]
    assert [vector for _, _, vector in pieces_of(long)] == [vector_for(n) for n in range(3)]
    assert not Section.objects.filter(needs_embedding(FAKE_MODEL)).exists()


def needing() -> list[Section]:
    return list(Section.objects.filter(needs_embedding(FAKE_MODEL)))


def test_needs_embedding_holds_while_a_piece_of_the_current_model_is_missing() -> None:
    version = make_version()
    (section,) = add_texts(version, SHORT)

    assert needing() == [section]
    set_embedding([section], vector_for(1))
    assert needing() == [section]
    SectionPiece.objects.create(
        section=section,
        ordinal=0,
        char_start=0,
        char_end=len(SHORT),
        embedding=vector_for(1),
        embedding_model=FAKE_MODEL,
    )
    assert needing() == []
    SectionPiece.objects.create(
        section=section,
        ordinal=1,
        char_start=0,
        char_end=len(SHORT),
        embedding=vector_for(1),
        embedding_model="old-model",
    )
    assert needing() == [section]


# --- Model change ------------------------------------------------------------------------


def test_a_change_of_the_model_replaces_every_piece(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_embedder(monkeypatch, settings, FakeEmbedder(model="old-model"))
    version = make_version()
    short, long = add_texts(version, SHORT, LONG)
    run(embed_job(version))
    assert {model for _, model, _ in pieces_of(long)} == {"old-model"}

    embedder = install_embedder(monkeypatch, settings, FakeEmbedder(model="new-model"))
    assert set(Section.objects.filter(needs_embedding("new-model"))) == {short, long}
    run(embed_job(version))

    assert len(embedder.texts) == 5
    for section in (short, long):
        assert {model for _, model, _ in pieces_of(section)} == {"new-model"}
    assert [text for text, _, _ in pieces_of(long)] == LONG_PIECES
    assert not SectionPiece.objects.filter(embedding_model="old-model").exists()


def test_pieces_of_another_model_go_even_when_the_section_vector_is_current(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    embedder = install_embedder(monkeypatch, settings)
    version = make_version()
    (short,) = add_texts(version, SHORT)
    set_embedding([short], vector_for(42))
    SectionPiece.objects.create(
        section=short,
        ordinal=0,
        char_start=0,
        char_end=len(SHORT),
        embedding=vector_for(9),
        embedding_model="old-model",
    )

    run(embed_job(version))

    assert embedder.texts == []
    assert pieces_of(short) == [(SHORT, FAKE_MODEL, vector_for(42))]


# --- Pausing and errors ------------------------------------------------------------------


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_a_paused_task_leaves_whole_sections_and_the_next_one_goes_on(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = FakeClock()
    embedder = install_embedder(monkeypatch, settings)

    def slow() -> None:
        clock.now += 100

    embedder.after_batch = slow
    version = make_version()
    sections = add_texts(version, LONG, LONG, LONG, LONG)
    job = embed_job(version)

    # 100 s per request: after two requests less than the request limit is
    # left before the soft time limit; the task stops between batches.
    assert run(job, clock) == StepResult(Outcome.EMBEDDING, embed_after=0)
    done = [s for s in sections if pieces_of(s)]
    assert len(done) == 2
    assert all(len(pieces_of(s)) == 3 for s in done)

    while run(job, clock).outcome == Outcome.EMBEDDING:
        pass

    assert job.status == IngestStatus.DONE
    assert all(len(pieces_of(s)) == 3 for s in sections)
    # Nothing twice: four sections with a text of their own and three pieces each.
    assert len(embedder.texts) == 16


def test_an_error_keeps_the_finished_sections_and_no_half_written_one(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.TWOX_EMBED_BATCH_SIZE = 2
    embedder = install_embedder(monkeypatch, settings)
    # The long section needs two requests; the second fails.
    embedder.errors = [None, None, EmbeddingUnavailableError("no answer")]
    version = make_version()
    short, long = add_texts(version, SHORT, LONG)
    job = embed_job(version)

    assert run(job).outcome == Outcome.EMBEDDING
    assert len(pieces_of(short)) == 1
    assert pieces_of(long) == []
    assert section_vector(long) is None

    assert run(job) == StepResult(Outcome.DONE)
    assert [text for text, _, _ in pieces_of(long)] == LONG_PIECES


# --- Same content ------------------------------------------------------------------------


def test_the_same_content_takes_over_the_pieces_without_asking_the_model(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_embedder(monkeypatch, settings)
    first = make_version(device="dps-plc")
    first_sections = add_texts(first, SHORT, LONG)
    run(embed_job(first))
    second = make_version(device="hbw-plc", filename="copy.pdf")
    assert second.sha256 == first.sha256
    second_sections = add_texts(second, SHORT, LONG)

    embedder = install_embedder(monkeypatch, settings)
    assert run(embed_job(second)) == StepResult(Outcome.DONE)

    assert embedder.texts == []
    for original, copy in zip(first_sections, second_sections, strict=True):
        assert pieces_of(copy) == pieces_of(original)
        assert section_vector(copy) == section_vector(original)


def test_pieces_of_another_model_are_not_taken_over(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_embedder(monkeypatch, settings, FakeEmbedder(model="old-model"))
    first = make_version(device="dps-plc")
    add_texts(first, LONG)
    run(embed_job(first))
    second = make_version(device="hbw-plc", filename="copy.pdf")
    (copy,) = add_texts(second, LONG)

    embedder = install_embedder(monkeypatch, settings)
    run(embed_job(second))

    assert len(embedder.texts) == 4
    assert {model for _, model, _ in pieces_of(copy)} == {FAKE_MODEL}


# --- Deleting ----------------------------------------------------------------------------


def test_pieces_go_with_their_sections(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    install_embedder(monkeypatch, settings)
    version = make_version()
    add_texts(version, SHORT, LONG)
    run(embed_job(version))
    assert SectionPiece.objects.count() == 4

    Section.objects.filter(document_version=version).only("pk").delete()

    assert SectionPiece.objects.count() == 0
