"""Acceptance of M2 over the API, without a browser (docs/ROADMAP.md, M2).

Condition: manuals ingested; the search finds an IP address and a question
asked in other words; errors are visible. The browser part is
``web/e2e/m2-acceptance.spec.ts``; the runs with the real manuals of the test
factory belong to the acceptance run of the coordination (work order 060).

The whole way goes through the API and the real tasks of the worker: an
upload starts the ingestion, the messages to the broker are recorded
(``ingest_messages``, tests/conftest.py) and then run one after the other
like a worker would. Docling is the HTTP stand-in of work order 041
(``tests/ingest/fake_docling.py``), reached by the real Docling client; it
answers with the real Docling results of the free test documents
(``tests/ingest/fixtures/``). The model service is a stand-in as well: every
test runs with the AI features off and with them on (E-59). No test reaches a
real Docling or a real model service; the uploaded files are made in the test.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks, Settings
from rest_framework.test import APIClient

from tests.conftest import IngestMessages
from tests.files.helpers import client_for, make_device
from tests.ingest.fake_converter import FakeEmbedder as SectionEmbedder
from tests.ingest.fake_converter import UnexpectedServiceCallError, install_embedder
from tests.ingest.fake_docling import (
    MARKDOWN_FIXTURE,
    FakeDocling,
    fixture_document,
    result_answer,
    running_fake_docling,
)
from tests.search.fake_embedder import CLOSED_MODEL_SERVICE
from tests.search.fake_embedder import FakeEmbedder as QueryEmbedder
from twox.answers import embeddings
from twox.config import celery_app
from twox.files.storage import key_for_sha256
from twox.ingest.models import Section

if TYPE_CHECKING:
    # Exists in the type stubs only; annotations are not evaluated at runtime.
    from rest_framework.response import _MonkeyPatchedResponse

pytestmark = pytest.mark.django_db

SEARCH_URL = "/api/v1/search/"
JOBS_URL = "/api/v1/ingest-jobs/"

#: Pages of the PDF fixture (BetrSichV, pages 1 to 5).
PDF_PAGES = 5
#: An identifier on page 1 of the PDF fixture (a CELEX number in a footnote).
IDENTIFIER = "31990L0270"
IDENTIFIER_PAGE = 1
#: An IP address in the Markdown fixture (an example target of a backup).
IP_ADDRESS = "192.168.1.10"
#: A question in other words: none of its words stands in the section it means
#: (the definition of who counts as an expert, section 2 (5) of the PDF fixture).
QUESTION = "Wer ist sachverständig genug für eine Aufgabe nach dieser Regel?"
QUESTION_TARGET = "Fachkundig ist"

#: Upper bound of worker messages per test; the flow ends far below it.
MAX_MESSAGES = 50


def make_pdf(text: str) -> bytes:
    """A small one-page PDF with ``text``, made in the test (valid signature and cross-reference).

    Docling never sees it: the stand-in answers with the fixture. The format
    check of the upload (049) only reads the signature.
    """
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n%b\nendstream" % (len(stream), stream),
    ]
    content = b"%PDF-1.7\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(content))
        content += b"%d 0 obj\n%b\nendobj\n" % (number, body)
    xref = len(content)
    content += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    content += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    content += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return content


@dataclass
class World:
    """The services of one test: the Docling stand-in, the recorded messages, the media root."""

    docling: FakeDocling
    messages: IngestMessages
    media_root: Path
    ai_enabled: bool
    #: Set when the AI features are on: the stand-ins of the model service.
    section_embedder: SectionEmbedder | None = None
    query_embedder: QueryEmbedder | None = None

    def run_worker(self) -> list[str]:
        """Run every recorded message like a worker, the messages they send included.

        Returns the task names in the order they ran. Countdowns are not
        waited for: the next status query follows at once.
        """
        ran: list[str] = []
        while self.messages.sent:
            assert len(ran) < MAX_MESSAGES, f"the ingestion never ended: {ran}"
            name, args = self.messages.sent.pop(0)
            celery_app.tasks[name](*args)
            ran.append(name)
        return ran


def _no_model_service() -> embeddings.Embedder:
    raise UnexpectedServiceCallError("the model service was asked with the AI features off")


@pytest.fixture(params=[False, True], ids=["ai-off", "ai-on"])
def world(
    request: pytest.FixtureRequest,
    settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ingest_messages: IngestMessages,
) -> Iterator[World]:
    """Docling stand-in over HTTP; the model service off, or on with stand-ins (E-59)."""
    ai_enabled: bool = request.param
    media_root = tmp_path / "media"
    settings.TWOX_MEDIA_ROOT = media_root
    settings.TWOX_AI_ENABLED = False
    settings.TWOX_LLM_BASE_URL = CLOSED_MODEL_SERVICE
    monkeypatch.setattr(embeddings, "get_embedder", _no_model_service)
    monkeypatch.setattr(embeddings, "get_query_embedder", _no_model_service)
    embeddings.forget_query_embedder()
    with running_fake_docling(result_answer(fixture_document())) as docling:
        settings.TWOX_DOCLING_URL = docling.base_url
        state = World(docling, ingest_messages, media_root, ai_enabled)
        if ai_enabled:
            state.section_embedder = install_embedder(monkeypatch, settings)
            state.query_embedder = QueryEmbedder(state.section_embedder.model_name)
            monkeypatch.setattr(embeddings, "get_query_embedder", lambda: state.query_embedder)
        yield state
    embeddings.forget_query_embedder()


@pytest.fixture
def manager() -> APIClient:
    return client_for("manage")


@pytest.fixture
def reader() -> APIClient:
    return client_for("read")


def upload(
    client: APIClient,
    device_id: int,
    filename: str,
    content: bytes,
    content_type: str,
    captured: DjangoCaptureOnCommitCallbacks,
) -> dict[str, Any]:
    """Upload a new file to the device; the ingestion is requested after the commit."""
    with captured(execute=True):
        response = client.post(
            f"/api/v1/devices/{device_id}/documents/",
            {
                "file": SimpleUploadedFile(filename, content, content_type=content_type),
                "title": filename,
            },
            format="multipart",
        )
    assert response.status_code == 201, response.content
    answer: dict[str, Any] = response.json()
    return answer


def get(client: APIClient, url: str, params: Any = None) -> Any:  # noqa: ANN401 - JSON
    response = client.get(url, params)
    assert response.status_code == 200, response.content
    return response.json()


def ingest_of(client: APIClient, document_id: int) -> dict[str, Any]:
    """The newest ingest job of the only version of a file, as the file page reads it."""
    [version] = get(client, f"/api/v1/documents/{document_id}/")["versions"]
    job: dict[str, Any] = version["ingest"]
    assert job is not None
    return job


def search(client: APIClient, query: str) -> dict[str, Any]:
    answer: dict[str, Any] = get(client, SEARCH_URL, {"q": query})
    return answer


def open_jobs(client: APIClient) -> int:
    """Number of queued and running jobs."""
    count: int = get(client, JOBS_URL + "?status=queued&status=running")["count"]
    return count


def start_again(client: APIClient, version_id: int) -> _MonkeyPatchedResponse:
    return client.post(f"/api/v1/document-versions/{version_id}/ingest/")


@dataclass
class Ingested:
    """The two manuals of the test after the ingestion."""

    device_id: int
    pdf: dict[str, Any]
    markdown: dict[str, Any]


@pytest.fixture
def ingested(
    world: World,
    manager: APIClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> Ingested:
    """A PDF and a Markdown manual uploaded and ingested through the worker tasks."""
    device = make_device("dps-plc")
    pdf = upload(
        manager,
        device.pk,
        "m2-acceptance-manual.pdf",
        make_pdf("M2 acceptance manual"),
        "application/pdf",
        django_capture_on_commit_callbacks,
    )
    # The upload has queued the job and sent it to the broker.
    assert ingest_of(manager, pdf["document"]["id"])["status"] == "queued"
    assert world.messages.names() == ["twox.ingest.convert"]
    ran = world.run_worker()
    assert ran[0] == "twox.ingest.convert"
    assert "twox.ingest.poll" in ran
    assert ("twox.ingest.embed" in ran) is world.ai_enabled

    world.docling.result = result_answer(fixture_document(MARKDOWN_FIXTURE))
    markdown = upload(
        manager,
        device.pk,
        "m2-acceptance-backup.md",
        b"# M2 acceptance\n\nA note written for the test.\n",
        "text/markdown",
        django_capture_on_commit_callbacks,
    )
    world.run_worker()
    return Ingested(device.pk, pdf, markdown)


# --- Ingested ------------------------------------------------------------------------------


def test_manuals_are_ingested_with_pages_and_sections(
    world: World, ingested: Ingested, reader: APIClient
) -> None:
    pdf_job = ingest_of(reader, ingested.pdf["document"]["id"])
    markdown_job = ingest_of(reader, ingested.markdown["document"]["id"])

    for job in (pdf_job, markdown_job):
        assert job["status"] == "done", job
        assert (job["error_code"], job["error_detail"], job["partly_converted"]) == ("", "", False)
        assert job["section_count"] > 0
        assert job["finished_at"] is not None
        # The step embed only runs with the AI features on (E-59).
        assert job["step"] == ("embed" if world.ai_enabled else "sections")
    assert pdf_job["page_count"] == PDF_PAGES
    assert markdown_job["page_count"] is None
    assert open_jobs(reader) == 0

    # Docling got each file under a neutral name, with the uploaded content.
    uploads = [request.file for request in world.docling.requests if request.file is not None]
    assert [file.filename for file in uploads] == [
        f"version-{ingested.pdf['version']['id']}.pdf",
        f"version-{ingested.markdown['version']['id']}.md",
    ]
    assert uploads[0].content.startswith(b"%PDF-1.7")

    # Every section of the PDF has its pages; embeddings exist only with the AI features.
    sections = Section.objects.filter(document_version_id=ingested.pdf["version"]["id"])
    assert sections.count() == pdf_job["section_count"]
    pages = [(section.page_start, section.page_end) for section in sections]
    assert all(
        start is not None and end is not None and 1 <= start <= end <= PDF_PAGES
        for start, end in pages
    )
    # The sections cover the pages of the manual.
    assert {page for start, end in pages for page in range(start or 0, (end or 0) + 1)} == set(
        range(1, PDF_PAGES + 1)
    )
    embedded = Section.objects.filter(embedding__isnull=False).count()
    assert embedded == (Section.objects.count() if world.ai_enabled else 0)


# --- Search --------------------------------------------------------------------------------


def test_search_finds_an_identifier_word_for_word_with_its_page(
    world: World, ingested: Ingested, reader: APIClient
) -> None:
    answer = search(reader, IDENTIFIER)

    assert answer["semantic"] == ("used" if world.ai_enabled else "disabled")
    first = answer["hits"][0]
    assert "exact" in first["match_kinds"]
    assert first["page_start"] <= IDENTIFIER_PAGE <= first["page_end"]
    marked = [first["snippet"][h["start"] : h["end"]] for h in first["highlights"]]
    assert IDENTIFIER in marked
    [location] = first["locations"]
    assert location["version"] == {
        "id": ingested.pdf["version"]["id"],
        "number": 1,
        "original_filename": "m2-acceptance-manual.pdf",
        "is_latest": True,
    }
    assert location["device"]["id"] == ingested.device_id
    # Only the hit with the identifier is exact.
    assert [hit for hit in answer["hits"] if "exact" in hit["match_kinds"]] == [first]


def test_search_finds_an_ip_address_word_for_word(
    world: World, ingested: Ingested, reader: APIClient
) -> None:
    answer = search(reader, IP_ADDRESS)

    first = answer["hits"][0]
    assert "exact" in first["match_kinds"]
    assert IP_ADDRESS in [first["snippet"][h["start"] : h["end"]] for h in first["highlights"]]
    # Markdown has no pages.
    assert (first["page_start"], first["page_end"]) == (None, None)
    [location] = first["locations"]
    assert location["version"]["original_filename"] == "m2-acceptance-backup.md"
    # A neighbouring address is not the same address: no exact hit, no keyword
    # hit (with the AI features on, the vector part still lists the nearest
    # sections by meaning).
    neighbour = search(reader, "192.168.1.1")["hits"]
    assert all(hit["match_kinds"] == ["semantic"] for hit in neighbour)
    assert (neighbour == []) is not world.ai_enabled


def test_search_answers_a_question_in_other_words_by_meaning(
    world: World, ingested: Ingested, reader: APIClient
) -> None:
    target = Section.objects.get(
        document_version_id=ingested.pdf["version"]["id"], text__contains=QUESTION_TARGET
    )
    if world.query_embedder is not None:
        # The stand-in model puts the question next to the section it means.
        assert target.embedding is not None
        world.query_embedder.queries[QUESTION] = list(target.embedding)

    answer = search(reader, QUESTION)

    if not world.ai_enabled:
        # Keyword search only, as a normal state (E-59); none of the words matches.
        assert answer == {"semantic": "disabled", "hits": []}
        return
    assert answer["semantic"] == "used"
    first = answer["hits"][0]
    assert first["section_id"] == target.pk
    assert first["match_kinds"] == ["semantic"]
    assert (first["page_start"], first["page_end"]) == (target.page_start, target.page_end)
    assert first["locations"][0]["version"]["original_filename"] == "m2-acceptance-manual.pdf"
    assert world.query_embedder is not None
    assert world.query_embedder.calls == [QUESTION]


# --- Errors are visible ---------------------------------------------------------------------


def test_errors_are_visible_over_the_api(
    world: World,
    manager: APIClient,
    reader: APIClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    device = make_device("dps-plc")

    # Docling refuses the file (as it does with a damaged one).
    world.docling.submit_answer = (
        422,
        b'{"detail":[{"loc":["body","files"],"msg":"invalid file","type":"value_error"}]}',
    )
    rejected = upload(
        manager,
        device.pk,
        "m2-damaged.pdf",
        make_pdf("damaged"),
        "application/pdf",
        django_capture_on_commit_callbacks,
    )
    world.run_worker()
    world.docling.submit_answer = None

    # The stored content is gone before the worker takes the job.
    missing = upload(
        manager,
        device.pk,
        "m2-missing.pdf",
        make_pdf("missing"),
        "application/pdf",
        django_capture_on_commit_callbacks,
    )
    (world.media_root / key_for_sha256(missing["version"]["sha256"])).unlink()
    world.run_worker()

    # A format that is not ingested in M2: skipped at once, nothing is sent.
    skipped = upload(
        manager,
        device.pk,
        "m2-notes.txt",
        b"M2 acceptance plain text\n",
        "text/plain",
        django_capture_on_commit_callbacks,
    )
    assert world.messages.sent == []

    expected = {
        rejected["document"]["id"]: ("failed", "docling_rejected", "convert"),
        missing["document"]["id"]: ("failed", "content_missing", "convert"),
        skipped["document"]["id"]: ("skipped", "unsupported_format", ""),
    }
    # Every role sees status, kind of error and the cleaned detail (E-57).
    for client in (manager, reader):
        for document_id, (status, code, step) in expected.items():
            job = ingest_of(client, document_id)
            assert (job["status"], job["error_code"], job["step"]) == (status, code, step)
            assert job["error_detail"] != ""
            assert job["finished_at"] is not None
        listed = get(client, JOBS_URL + "?status=failed&status=skipped")["results"]
        assert sorted((job["status"], job["error_code"]) for job in listed) == sorted(
            (status, code) for status, code, _step in expected.values()
        )
        # Who started a job: the role manage only (E-57); the uploads were by "manage".
        shown = "manage" if client is manager else None
        assert [job["requested_by"] for job in listed] == [shown] * len(expected)
    # The cleaned detail names neither the file nor the address of Docling.
    detail = ingest_of(reader, rejected["document"]["id"])["error_detail"]
    assert "422" in detail
    assert "m2-damaged" not in detail
    assert "127.0.0.1" not in detail
    assert ingest_of(reader, skipped["document"]["id"])["error_detail"].startswith(
        "files with the extension .txt are not ingested"
    )
    assert open_jobs(reader) == 0
    # Nothing of the failed files is searchable.
    assert Section.objects.count() == 0


# --- Ingest again ---------------------------------------------------------------------------


def test_manage_starts_the_ingestion_again_read_may_not(
    world: World,
    ingested: Ingested,
    manager: APIClient,
    reader: APIClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    version_id = ingested.pdf["version"]["id"]
    first_job = ingest_of(manager, ingested.pdf["document"]["id"])
    submitted = len([r for r in world.docling.requests if r.file is not None])

    refused = start_again(reader, version_id)
    assert refused.status_code == 403
    assert world.messages.sent == []

    with django_capture_on_commit_callbacks(execute=True):
        accepted = start_again(manager, version_id)
    assert accepted.status_code == 202, accepted.content
    new_job = accepted.json()
    assert new_job["id"] != first_job["id"]
    assert (new_job["status"], new_job["requested_by"]) == ("queued", "manage")
    assert world.messages.names() == ["twox.ingest.convert"]

    world.run_worker()
    again = ingest_of(manager, ingested.pdf["document"]["id"])
    assert again["id"] == new_job["id"]
    assert again["status"] == "done"
    assert again["section_count"] == first_job["section_count"]
    # The stored Docling answer of the same content is used again (046).
    assert len([r for r in world.docling.requests if r.file is not None]) == submitted
    # Both attempts stay listed, newest first (E-55).
    jobs = get(manager, JOBS_URL + f"?version={version_id}")["results"]
    assert [job["id"] for job in jobs] == [new_job["id"], first_job["id"]]
    # The search still finds the identifier.
    assert "exact" in search(reader, IDENTIFIER)["hits"][0]["match_kinds"]
