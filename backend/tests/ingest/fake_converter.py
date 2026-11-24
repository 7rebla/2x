"""Stand-ins and helpers for the tests of the ingest flow (work order 046).

:class:`FakeConverter` replaces :class:`~twox.ingest.docling.DocumentConverter`
in memory: it answers with the real Docling results from ``fixtures/`` (041).
The fixture :func:`isolated_services` keeps every test away from a real
Docling and a real model service (E-59): their addresses point nowhere and the
factories of both clients fail the test if anything calls them.
"""

import io
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

import pytest
from django.conf import settings as django_settings
from pytest_django.fixtures import Settings

from tests.files.helpers import make_device
from tests.ingest.fake_docling import fixture_document, result_answer
from twox.answers import embeddings
from twox.files.models import Document, DocumentVersion
from twox.files.storage import get_blob_storage
from twox.ingest import docling, pipeline
from twox.ingest.docling import (
    DEFAULT_DOCUMENT_TIMEOUT_SECONDS,
    ConversionStatus,
    DocumentConverter,
    TaskStatus,
)
from twox.ingest.models import (
    EMBEDDING_DIMENSIONS,
    IngestJob,
    IngestStatus,
    IngestStep,
    Section,
    section_rows,
)
from twox.ingest.pieces import split_pieces
from twox.ingest.sections import SectionDraft

#: Stand-in bytes of BetrSichV.pdf; Docling never sees them, the fake answers.
PDF_CONTENT = b"%PDF-1.7 stand-in for testdata/klein/recht/BetrSichV.pdf\n"
MARKDOWN_CONTENT = b"# SFTP backup\n\nStand-in for sftp-backup.md.\n"


class UnexpectedServiceCallError(AssertionError):
    """A test reached a real Docling or model service client."""


@dataclass
class Submission:
    """One upload the fake received."""

    filename: str
    content_type: str
    document_timeout: float
    content: bytes


@dataclass
class FakeConverter:
    """A scripted :class:`DocumentConverter`.

    ``statuses`` are the answers of :meth:`poll` in order; the last one
    repeats. An exception in the list is raised instead. ``submit_errors`` and
    ``fetch_errors`` are raised by the next calls of :meth:`submit` and
    :meth:`fetch` before they succeed.
    """

    answer: bytes = field(default_factory=lambda: result_answer(fixture_document()))
    statuses: list[TaskStatus | Exception] = field(
        default_factory=lambda: [TaskStatus.STARTED, TaskStatus.SUCCESS]
    )
    submit_errors: list[Exception] = field(default_factory=list)
    fetch_errors: list[Exception] = field(default_factory=list)
    submissions: list[Submission] = field(default_factory=list)
    polled: list[str] = field(default_factory=list)
    fetched: list[str] = field(default_factory=list)

    def submit(
        self,
        stream: BinaryIO,
        filename: str,
        content_type: str,
        *,
        page_range: tuple[int, int] | None = None,
        document_timeout: float = DEFAULT_DOCUMENT_TIMEOUT_SECONDS,
    ) -> str:
        if self.submit_errors:
            raise self.submit_errors.pop(0)
        self.submissions.append(Submission(filename, content_type, document_timeout, stream.read()))
        return f"task-{len(self.submissions)}"

    def poll(self, task_id: str, *, wait: float = 0.0) -> ConversionStatus:
        self.polled.append(task_id)
        item = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        if isinstance(item, Exception):
            raise item
        return ConversionStatus(task_id=task_id, status=item, position=None)

    def fetch(self, task_id: str, sink: BinaryIO) -> int:
        self.fetched.append(task_id)
        if self.fetch_errors:
            raise self.fetch_errors.pop(0)
        sink.write(self.answer)
        return len(self.answer)


class NoDocling:
    """A converter that must not be used (reuse of a stored answer)."""

    def submit(
        self,
        stream: BinaryIO,
        filename: str,
        content_type: str,
        *,
        page_range: tuple[int, int] | None = None,
        document_timeout: float = DEFAULT_DOCUMENT_TIMEOUT_SECONDS,
    ) -> str:
        raise UnexpectedServiceCallError("Docling was asked to convert")

    def poll(self, task_id: str, *, wait: float = 0.0) -> ConversionStatus:
        raise UnexpectedServiceCallError("Docling was polled")

    def fetch(self, task_id: str, sink: BinaryIO) -> int:
        raise UnexpectedServiceCallError("a Docling result was fetched")


def _no_real_docling() -> DocumentConverter:
    raise UnexpectedServiceCallError("a test reached the real Docling client")


def _no_real_model_service() -> embeddings.Embedder:
    raise UnexpectedServiceCallError("a test reached the model service (E-59)")


@pytest.fixture
def isolated_services(
    settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    """Own blob storage per test; no real Docling, no real model service.

    The AI features are off unless a test switches them on (E-59): the
    containers get ``TWOX_AI_ENABLED=true`` from the development template,
    and the flow of work order 046 ends after the sections only without them.
    """
    media_root = tmp_path / "media"
    settings.TWOX_AI_ENABLED = False
    settings.TWOX_MEDIA_ROOT = media_root
    settings.TWOX_DOCLING_URL = "http://docling.invalid:5001"
    settings.TWOX_LLM_BASE_URL = "http://ollama.invalid:11434/v1"
    monkeypatch.setattr(pipeline, "get_document_converter", _no_real_docling)
    monkeypatch.setattr(docling, "get_document_converter", _no_real_docling)
    monkeypatch.setattr(embeddings, "get_embedder", _no_real_model_service)
    yield media_root


def make_version(
    content: bytes = PDF_CONTENT,
    *,
    device: str = "dps-plc",
    filename: str = "BetrSichV.pdf",
    content_type: str = "application/pdf",
    document: Document | None = None,
    number: int = 1,
) -> DocumentVersion:
    """A document version whose bytes are in the blob storage of the test."""
    stored = get_blob_storage().store_blob(io.BytesIO(content))
    if document is None:
        document = Document.objects.create(device=make_device(device), title=f"Manual {device}")
    return DocumentVersion.objects.create(
        document=document,
        number=number,
        blob_key=stored.key,
        sha256=stored.sha256,
        size=stored.size,
        content_type=content_type,
        original_filename=filename,
    )


def make_job(version: DocumentVersion) -> IngestJob:
    return IngestJob.objects.create(document_version=version)


# --- Step embed (work order 048) -------------------------------------------------------

#: Model name the embedding stand-in reports.
FAKE_MODEL = "fake-embed"


def vector_for(number: int) -> list[float]:
    """The vector of the ``number``-th embedded text: length 1 along one axis."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[number % EMBEDDING_DIMENSIONS] = 1.0
    return vector


@dataclass
class FakeEmbedder:
    """A scripted :class:`~twox.answers.embeddings.Embedder` for section texts.

    Every call of :meth:`embed_documents` first takes the next entry of
    ``errors`` (``None``: no error) and raises it. The texts that were
    embedded are kept in order; the ``n``-th text gets :func:`vector_for` ``(n)``.
    """

    model: str = FAKE_MODEL
    size: int = EMBEDDING_DIMENSIONS
    errors: list[Exception | None] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    batches: list[int] = field(default_factory=list)
    #: Called after every successful batch (to let time pass in a test).
    after_batch: Callable[[], None] | None = None

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def dimensions(self) -> int:
        return self.size

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if self.errors:
            error = self.errors.pop(0)
            if error is not None:
                raise error
        first = len(self.texts)
        self.texts.extend(texts)
        self.batches.append(len(texts))
        if self.after_batch is not None:
            self.after_batch()
        return [vector_for(first + index)[: self.size] for index in range(len(texts))]

    def embed_query(self, text: str) -> list[float]:
        raise UnexpectedServiceCallError("the ingest flow embeds section texts only")


def texts_to_embed(version: DocumentVersion) -> int:
    """How many texts the embed step sends for the sections of ``version`` without embeddings.

    One per section, plus one per piece of a section longer than
    ``TWOX_PIECE_MAX_CHARS`` (150); a section of one piece gives it its own vector.
    """
    count = 0
    for text in Section.objects.filter(document_version=version).values_list("text", flat=True):
        spans = split_pieces(text, django_settings.TWOX_PIECE_MAX_CHARS)
        count += 1 + (len(spans) if len(spans) > 1 else 0)
    return count


def install_embedder(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, embedder: FakeEmbedder | None = None
) -> FakeEmbedder:
    """Switch the AI features on; ``get_embedder()`` of 044 gives ``embedder``."""
    stand_in = embedder or FakeEmbedder()
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_EMBED_MODEL = stand_in.model
    settings.TWOX_EMBED_DIMENSIONS = EMBEDDING_DIMENSIONS
    monkeypatch.setattr(embeddings, "get_embedder", lambda: stand_in)
    return stand_in


def add_sections(version: DocumentVersion, count: int, *, prefix: str = "Text") -> IngestJob:
    """``count`` sections of ``version`` from a finished job, as the step sections leaves them."""
    job = IngestJob.objects.create(
        document_version=version, status=IngestStatus.DONE, step=IngestStep.SECTIONS
    )
    drafts = [
        SectionDraft(
            ordinal=number,
            heading_path=("Chapter", f"Part {number}"),
            text=f"{prefix} {number}",
            page_start=1,
            page_end=1,
        )
        for number in range(count)
    ]
    Section.objects.bulk_create(section_rows(drafts, version, job))
    return job


def make_embed_job(version: DocumentVersion, *, sections: int = 5) -> IngestJob:
    """A queued job in the step embed (as ``embed_sections`` creates it), with sections."""
    if not Section.objects.filter(document_version=version).exists():
        add_sections(version, sections)
    return IngestJob.objects.create(
        document_version=version, status=IngestStatus.QUEUED, step=IngestStep.EMBED
    )


def run_job(
    job: IngestJob, converter: DocumentConverter, *, max_steps: int = 60
) -> list[pipeline.StepResult]:
    """Call :func:`pipeline.convert` and then :func:`pipeline.poll` as the tasks would."""
    results = [pipeline.convert(job.pk, converter=converter)]
    while results[-1].poll_after is not None:
        assert len(results) < max_steps, "the job never ended"
        results.append(pipeline.poll(job.pk, converter=converter))
    job.refresh_from_db()
    return results
