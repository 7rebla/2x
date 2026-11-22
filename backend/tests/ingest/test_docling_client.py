"""The docling-serve client against a stand-in from the standard library; no docling needed."""

import ast
import io
import json
import socket
from collections.abc import Buffer, Iterator
from contextlib import closing
from pathlib import Path

import pytest
from pytest_django import Settings

from tests.ingest.fake_docling import (
    BETRSICHV_FIXTURE,
    FIXTURES,
    MARKDOWN_FIXTURE,
    FakeDocling,
    fixture_document,
    result_answer,
    running_fake_docling,
)
from twox.ingest import docling
from twox.ingest.docling import (
    CHUNK_SIZE,
    OCR_PRESET,
    ConversionStatus,
    DoclingClient,
    DoclingConversionError,
    DoclingRejectedError,
    DoclingTaskLostError,
    DoclingUnavailableError,
    TaskStatus,
    load_result,
)

PDF_BYTES = b"%PDF-1.7\n" + bytes(range(256)) * 40 + b"\r\n--not-a-boundary\r\n%%EOF\n"


@pytest.fixture
def fake(settings: Settings) -> Iterator[FakeDocling]:
    with running_fake_docling(result_answer(fixture_document())) as stand_in:
        settings.TWOX_DOCLING_URL = stand_in.base_url
        yield stand_in


def unused_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
    return port


def assert_no_internals(error: BaseException, fake: FakeDocling | None = None) -> None:
    """Messages stay short and name neither address nor port nor file contents."""
    text = str(error)
    assert len(text) < 120
    assert "127.0.0.1" not in text
    assert "http" not in text
    assert "%PDF" not in text
    if fake is not None:
        assert fake.base_url.rsplit(":", 1)[1] not in text


class BlockOnlyStream(io.RawIOBase):
    """A stream that fails when asked for everything at once and records each read."""

    def __init__(self, content: bytes) -> None:
        self._content = io.BytesIO(content)
        self.read_sizes: list[int] = []

    def readable(self) -> bool:
        return True

    def read(self, size: int | None = -1) -> bytes:
        if size is None or size < 0:
            raise AssertionError("the upload must be read in blocks, not as a whole")
        self.read_sizes.append(size)
        return self._content.read(size)

    def readall(self) -> bytes:
        raise AssertionError("the upload must be read in blocks, not as a whole")


class RecordingSink(io.BytesIO):
    """A sink that records the size of each write."""

    def __init__(self) -> None:
        super().__init__()
        self.write_sizes: list[int] = []

    def write(self, data: Buffer, /) -> int:
        self.write_sizes.append(memoryview(data).nbytes)
        return super().write(data)


# Round trip


def test_submit_poll_fetch_and_load_round_trip(fake: FakeDocling) -> None:
    client = DoclingClient()

    task_id = client.submit(io.BytesIO(PDF_BYTES), "version-7.pdf", "application/pdf")
    first = client.poll(task_id)
    second = client.poll(task_id)
    sink = io.BytesIO()
    size = client.fetch(task_id, sink)

    assert first == ConversionStatus(task_id=task_id, status=TaskStatus.PENDING, position=1)
    assert not first.finished
    assert second.status is TaskStatus.SUCCESS
    assert second.finished
    assert second.position is None
    assert size == len(fake.result) == len(sink.getvalue())
    sink.seek(0)
    result = load_result(sink)
    assert result.status is TaskStatus.SUCCESS
    assert result.errors == ()
    assert result.processing_time == 1.5
    assert result.document == fixture_document()

    upload = fake.requests[0]
    assert upload.method == "POST"
    assert upload.path == "/v1/convert/file/async"
    assert upload.file is not None
    assert upload.file.filename == "version-7.pdf"
    assert upload.file.content_type == "application/pdf"
    assert upload.file.content == PDF_BYTES
    assert [request.path for request in fake.requests[1:]] == [
        f"/v1/status/poll/{task_id}",
        f"/v1/status/poll/{task_id}",
        f"/v1/result/{task_id}",
    ]


def test_poll_passes_wait_to_the_service(fake: FakeDocling) -> None:
    task_id = fake.add_task("started")

    status = DoclingClient().poll(task_id, wait=5)

    assert status.status is TaskStatus.STARTED
    assert fake.requests[-1].path == f"/v1/status/poll/{task_id}?wait=5"


def test_every_request_asks_for_json_with_rapidocr_and_placeholders(fake: FakeDocling) -> None:
    client = DoclingClient()
    client.submit(io.BytesIO(PDF_BYTES), "version-1.pdf", "application/pdf")
    client.submit(
        io.BytesIO(b"# Title\n"),
        "version-2.md",
        "text/markdown",
        page_range=(1, 5),
        document_timeout=60,
    )

    assert OCR_PRESET == "rapidocr"
    assert len(fake.requests) == 2
    for request in fake.requests:
        assert request.field_values("to_formats") == ["json"]
        assert request.field_values("ocr_preset") == ["rapidocr"]
        assert request.field_values("image_export_mode") == ["placeholder"]
        assert len(request.field_values("document_timeout")) == 1
        assert "ocr_engine" not in {name for name, _value in request.fields}
        assert b"easyocr" not in request.body.lower()
        assert b'"auto"' not in request.body
    assert fake.requests[0].field_values("document_timeout") == ["7200"]
    assert fake.requests[0].field_values("page_range") == []
    assert fake.requests[1].field_values("document_timeout") == ["60"]
    assert fake.requests[1].field_values("page_range") == ["1", "5"]


def test_module_never_names_another_ocr_engine() -> None:
    """No string the module can send names EasyOCR or ``auto`` (docstrings aside)."""
    tree = ast.parse(Path(docling.__file__).read_text(encoding="utf-8"))
    docstrings = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }
    strings = [
        node.value.lower()
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]

    assert strings
    assert not [value for value in strings if "easyocr" in value or value == "auto"]


# Streaming


def test_upload_is_read_in_blocks_and_sent_completely(fake: FakeDocling) -> None:
    content = bytes(range(256)) * (3 * CHUNK_SIZE // 256) + b"tail"
    stream = BlockOnlyStream(content)

    DoclingClient().submit(stream, "version-3.pdf", "application/pdf")  # type: ignore[arg-type]

    upload = fake.requests[0]
    assert upload.file is not None
    assert upload.file.content == content
    assert stream.read_sizes
    assert max(stream.read_sizes) <= CHUNK_SIZE
    assert len(stream.read_sizes) >= 4
    # No Content-Length: the body goes out in chunks and never as one piece.
    assert upload.headers.get("Transfer-Encoding") == "chunked"


def test_fetch_writes_the_result_in_blocks(fake: FakeDocling) -> None:
    padding = "x" * (2 * CHUNK_SIZE + 123)
    fake.result = result_answer(fixture_document() | {"padding": padding})
    task_id = fake.add_task("success")
    sink = RecordingSink()

    size = DoclingClient().fetch(task_id, sink)

    assert size == len(fake.result)
    assert sink.getvalue() == fake.result
    assert len(sink.write_sizes) >= 3
    assert max(sink.write_sizes) <= CHUNK_SIZE


# Errors


def test_validation_error_is_rejected(fake: FakeDocling) -> None:
    detail = {
        "detail": [
            {
                "type": "value_error",
                "loc": ["body", "ocr_preset"],
                "msg": "ocr_preset 'auto' is not allowed. Allowed values: ['rapidocr']",
                "input": "secret-content",
            }
        ]
    }
    fake.submit_answer = (422, json.dumps(detail).encode())

    with pytest.raises(DoclingRejectedError) as caught:
        DoclingClient().submit(io.BytesIO(PDF_BYTES), "version-1.pdf", "application/pdf")

    assert str(caught.value) == "docling-serve rejected the request (HTTP 422, fields: ocr_preset)"
    assert "secret-content" not in str(caught.value)
    assert_no_internals(caught.value, fake)


@pytest.mark.parametrize("code", [500, 502, 503])
def test_server_errors_mean_unavailable(fake: FakeDocling, code: int) -> None:
    fake.submit_answer = (code, b'{"detail":"Service Unavailable"}')
    fake.poll_answer = (code, b"")
    fake.result_answer = (code, b"")
    client = DoclingClient()
    task_id = fake.add_task("success")

    with pytest.raises(DoclingUnavailableError) as on_submit:
        client.submit(io.BytesIO(PDF_BYTES), "version-1.pdf", "application/pdf")
    with pytest.raises(DoclingUnavailableError):
        client.poll(task_id)
    with pytest.raises(DoclingUnavailableError):
        client.fetch(task_id, io.BytesIO())

    assert str(on_submit.value) == f"docling-serve answered with HTTP {code}"
    assert_no_internals(on_submit.value, fake)


def test_refused_connection_means_unavailable(settings: Settings) -> None:
    settings.TWOX_DOCLING_URL = f"http://127.0.0.1:{unused_port()}"
    client = DoclingClient()

    with pytest.raises(DoclingUnavailableError) as caught:
        client.submit(io.BytesIO(PDF_BYTES), "version-1.pdf", "application/pdf")
    with pytest.raises(DoclingUnavailableError):
        client.poll("4b8c2a3e-0000-4000-8000-000000000000")

    assert str(caught.value) == "docling-serve refused the connection"
    assert_no_internals(caught.value)


def test_unresolvable_host_means_unavailable(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_such_host(*args: object, **kwargs: object) -> list[object]:
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    # No real DNS query: the tests also have to pass without any network.
    monkeypatch.setattr(socket, "getaddrinfo", no_such_host)
    settings.TWOX_DOCLING_URL = "http://docling:5001"

    with pytest.raises(DoclingUnavailableError) as caught:
        DoclingClient().poll("4b8c2a3e-0000-4000-8000-000000000000")

    assert str(caught.value) == "the host name of docling-serve does not resolve"
    assert "docling:5001" not in str(caught.value)


def test_silent_service_runs_into_the_time_limit(settings: Settings) -> None:
    # The kernel completes the handshake for a listening socket, but nobody
    # ever accepts or answers.
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as silent:
        silent.bind(("127.0.0.1", 0))
        silent.listen(1)
        settings.TWOX_DOCLING_URL = f"http://127.0.0.1:{silent.getsockname()[1]}"
        client = DoclingClient(timeout=0.3)

        with pytest.raises(DoclingUnavailableError) as on_poll:
            client.poll("4b8c2a3e-0000-4000-8000-000000000000")
        with pytest.raises(DoclingUnavailableError) as on_fetch:
            client.fetch("4b8c2a3e-0000-4000-8000-000000000000", io.BytesIO())

    assert str(on_poll.value) == "docling-serve did not answer within the time limit"
    assert str(on_fetch.value) == "docling-serve did not answer within the time limit"


def test_unknown_task_is_lost_on_poll_and_fetch(fake: FakeDocling) -> None:
    client = DoclingClient()

    with pytest.raises(DoclingTaskLostError) as on_poll:
        client.poll("4b8c2a3e-0000-4000-8000-000000000000")
    with pytest.raises(DoclingTaskLostError) as on_fetch:
        client.fetch("4b8c2a3e-0000-4000-8000-000000000000", io.BytesIO())

    assert str(on_poll.value) == "docling-serve does not know the task"
    assert_no_internals(on_poll.value, fake)
    assert_no_internals(on_fetch.value, fake)


def test_task_is_lost_after_a_restart(fake: FakeDocling) -> None:
    client = DoclingClient()
    task_id = client.submit(io.BytesIO(PDF_BYTES), "version-1.pdf", "application/pdf")
    assert client.poll(task_id).status is TaskStatus.PENDING

    fake.restart()

    with pytest.raises(DoclingTaskLostError):
        client.poll(task_id)
    with pytest.raises(DoclingTaskLostError):
        client.fetch(task_id, io.BytesIO())


def test_second_fetch_after_removal_is_lost(fake: FakeDocling) -> None:
    client = DoclingClient()
    task_id = fake.add_task("success")
    client.fetch(task_id, io.BytesIO())

    with pytest.raises(DoclingTaskLostError):
        client.fetch(task_id, io.BytesIO())


def test_fetch_before_the_end_is_rejected_not_lost(fake: FakeDocling) -> None:
    task_id = fake.add_task("started")

    with pytest.raises(DoclingRejectedError) as caught:
        DoclingClient().fetch(task_id, io.BytesIO())

    assert "no result yet" in str(caught.value)


@pytest.mark.parametrize(
    "body",
    [b"<html></html>", b"[]", b'{"task_id": "x"}', b'{"task_id": "a b", "task_status": "pending"}'],
)
def test_unusable_status_answer_means_unavailable(fake: FakeDocling, body: bytes) -> None:
    fake.poll_answer = (200, body)

    with pytest.raises(DoclingUnavailableError, match="unexpected answer"):
        DoclingClient().poll("4b8c2a3e-0000-4000-8000-000000000000")


# Arguments


@pytest.mark.parametrize(
    "filename", ["", "../version-1.pdf", 'a".pdf', "a\r\nX: y.pdf", "Handbuch Ölpumpe.pdf"]
)
def test_filename_must_be_plain(fake: FakeDocling, filename: str) -> None:
    with pytest.raises(ValueError, match="filename"):
        DoclingClient().submit(io.BytesIO(PDF_BYTES), filename, "application/pdf")

    assert fake.requests == []


@pytest.mark.parametrize("page_range", [(0, 5), (5, 1), (-1, 2)])
def test_page_range_must_be_ordered(fake: FakeDocling, page_range: tuple[int, int]) -> None:
    with pytest.raises(ValueError, match="page_range"):
        DoclingClient().submit(
            io.BytesIO(PDF_BYTES), "version-1.pdf", "application/pdf", page_range=page_range
        )

    assert fake.requests == []


@pytest.mark.parametrize("timeout", [0, -1, 7201])
def test_document_timeout_is_bounded(fake: FakeDocling, timeout: float) -> None:
    with pytest.raises(ValueError, match="document_timeout"):
        DoclingClient().submit(
            io.BytesIO(PDF_BYTES), "version-1.pdf", "application/pdf", document_timeout=timeout
        )


@pytest.mark.parametrize("task_id", ["", "../health", "a/b", "a b", "x" * 200])
def test_task_id_is_checked(fake: FakeDocling, task_id: str) -> None:
    with pytest.raises(ValueError, match="task ID"):
        DoclingClient().poll(task_id)
    with pytest.raises(ValueError, match="task ID"):
        DoclingClient().fetch(task_id, io.BytesIO())

    assert fake.requests == []


def test_base_address_comes_from_the_settings(settings: Settings) -> None:
    settings.TWOX_DOCLING_URL = "docling:5001"

    with pytest.raises(ValueError, match="TWOX_DOCLING_URL"):
        DoclingClient()


def test_get_document_converter_returns_the_client(fake: FakeDocling) -> None:
    converter = docling.get_document_converter()

    assert isinstance(converter, DoclingClient)
    task_id = converter.submit(io.BytesIO(PDF_BYTES), "version-1.pdf", "application/pdf")
    assert fake.tasks.keys() == {task_id}


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("version-1.pdf", "application/pdf"),
        ("version-1.md", "text/markdown"),
        (
            "version-1.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("version-1.unknown", "application/octet-stream"),
    ],
)
def test_guess_content_type(filename: str, expected: str) -> None:
    assert docling.guess_content_type(filename) == expected


# Stored results


def stored(answer: bytes) -> io.BytesIO:
    return io.BytesIO(answer)


def test_partial_success_keeps_the_document_and_the_errors() -> None:
    errors = [
        {
            "component_type": "model",
            "module_name": "TableStructureModel",
            "error_message": "table failed",
            "category": "inference_failure",
            "page_no": 3,
        }
    ]
    answer = result_answer(fixture_document(), status="partial_success", errors=errors)

    result = load_result(stored(answer))

    assert result.status is TaskStatus.PARTIAL_SUCCESS
    assert len(result.errors) == 1
    assert result.errors[0].module_name == "TableStructureModel"
    assert result.errors[0].page_no == 3


@pytest.mark.parametrize("status", ["failure", "skipped", "pending", "nonsense"])
def test_result_without_success_is_a_conversion_error(status: str) -> None:
    with pytest.raises(DoclingConversionError):
        load_result(stored(result_answer(fixture_document(), status=status)))


def test_task_failure_result_is_a_conversion_error() -> None:
    answer = json.dumps(
        {
            "kind": "TaskFailureResult",
            "failure": {
                "category": "timeout",
                "message": "Document /tmp/x.pdf timed out",
                "retryable": False,
                "phase": "conversion",
                "details": {},
            },
        }
    ).encode()

    with pytest.raises(DoclingConversionError) as caught:
        load_result(stored(answer))

    assert str(caught.value) == "the conversion task failed (timeout)"


@pytest.mark.parametrize(
    "answer",
    [
        b"not json",
        b"[]",
        result_answer(None),
        result_answer({"schema_name": "Other"}),
    ],
)
def test_unusable_result_is_a_conversion_error(answer: bytes) -> None:
    with pytest.raises(DoclingConversionError):
        load_result(stored(answer))


# Checked-in results of the real service


@pytest.mark.parametrize("path", [BETRSICHV_FIXTURE, MARKDOWN_FIXTURE])
def test_fixtures_are_docling_documents(path: Path) -> None:
    raw = path.read_bytes()
    document = json.loads(raw)

    assert not raw.startswith(b"\xef\xbb\xbf")
    assert document["schema_name"] == "DoclingDocument"
    assert document["body"]["self_ref"] == "#/body"
    assert document["texts"]
    assert load_result(stored(result_answer(document))).document == document


def test_pdf_fixture_has_five_pages_and_stays_small() -> None:
    document = fixture_document(BETRSICHV_FIXTURE)
    pages = {
        provenance["page_no"] for text in document["texts"] for provenance in text.get("prov", [])
    }

    assert BETRSICHV_FIXTURE.stat().st_size <= 300_000
    assert sorted(document["pages"]) == ["1", "2", "3", "4", "5"]
    assert pages == {1, 2, 3, 4, 5}


def test_fixture_folder_has_a_readme() -> None:
    readme = (FIXTURES / "README.md").read_text(encoding="utf-8")

    assert "BetrSichV.pdf" in readme
    assert "BSD-2-Clause" in readme
    assert "1.38.2" in readme
