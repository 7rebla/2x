"""Stand-ins and helpers for the tests of the ingest flow (work order 046).

:class:`FakeConverter` replaces :class:`~twox.ingest.docling.DocumentConverter`
in memory: it answers with the real Docling results from ``fixtures/`` (041).
The fixture :func:`isolated_services` keeps every test away from a real
Docling and a real model service (E-59): their addresses point nowhere and the
factories of both clients fail the test if anything calls them.
"""

import io
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

import pytest
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
from twox.ingest.models import IngestJob

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
    """Own blob storage per test; no real Docling, no real model service."""
    media_root = tmp_path / "media"
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
