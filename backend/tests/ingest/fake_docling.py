"""A stand-in for docling-serve 1.38.2, built from the standard library.

It runs ``http.server`` in a thread on the loopback interface and answers the
three endpoints the backend uses the way the real service did in work order
041: ``POST /v1/convert/file/async``, ``GET /v1/status/poll/{task_id}`` and
``GET /v1/result/{task_id}``. Unknown task IDs answer ``404 {"detail": "Task
not found."}``, a result asked for too early ``404 {"detail": "Task result not
found. Please wait for a completion status."}``.

Every request is recorded with its decoded body (chunked transfer encoding
included) and, for uploads, the parsed form fields and file.
"""

import json
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

FIXTURES = Path(__file__).parent / "fixtures"
BETRSICHV_FIXTURE = FIXTURES / "betrsichv-p1-5.docling.json"
MARKDOWN_FIXTURE = FIXTURES / "sftp-backup.docling.json"

TASK_NOT_FOUND = b'{"detail":"Task not found."}'
RESULT_NOT_READY = b'{"detail":"Task result not found. Please wait for a completion status."}'


def result_answer(
    document: dict[str, Any] | None,
    *,
    status: str = "success",
    errors: list[dict[str, Any]] | None = None,
    processing_time: float = 1.5,
) -> bytes:
    """A ``ConvertDocumentResponse`` as docling-serve 1.38.2 sends it."""
    return json.dumps(
        {
            "document": {
                "filename": "version-1.pdf",
                "md_content": None,
                "json_content": document,
                "html_content": None,
                "text_content": None,
                "doctags_content": None,
                "doclang_content": None,
            },
            "status": status,
            "errors": errors or [],
            "processing_time": processing_time,
            "timings": {},
            "confidence": None,
        }
    ).encode()


def fixture_document(path: Path = BETRSICHV_FIXTURE) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(path.read_bytes())
    return document


@dataclass
class UploadedFile:
    filename: str
    content_type: str
    content: bytes


@dataclass
class RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes
    fields: list[tuple[str, str]] = field(default_factory=list)
    file: UploadedFile | None = None

    def field_values(self, name: str) -> list[str]:
        return [value for key, value in self.fields if key == name]


@dataclass
class FakeDocling:
    """State and behaviour of the stand-in; tests change the attributes."""

    base_url: str = ""
    requests: list[RecordedRequest] = field(default_factory=list)
    # Statuses a new task reports on successive polls; the last one stays.
    status_sequence: tuple[str, ...] = ("pending", "success")
    result: bytes = b""
    # Fixed answer (status, body) for submit, poll or result instead of the normal one.
    submit_answer: tuple[int, bytes] | None = None
    poll_answer: tuple[int, bytes] | None = None
    result_answer: tuple[int, bytes] | None = None
    tasks: dict[str, list[str]] = field(default_factory=dict)

    def restart(self) -> None:
        """Forget every task, like docling-serve after a restart."""
        self.tasks.clear()

    def add_task(self, *statuses: str) -> str:
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = list(statuses or self.status_sequence)
        return task_id


def _read_body(handler: BaseHTTPRequestHandler) -> bytes:
    """Read the request body, decoding chunked transfer encoding."""
    if handler.headers.get("Transfer-Encoding", "").lower() == "chunked":
        body = bytearray()
        while True:
            size = int(handler.rfile.readline().split(b";")[0].strip(), 16)
            if size == 0:
                while handler.rfile.readline() not in {b"\r\n", b"\n", b""}:
                    pass
                return bytes(body)
            body += handler.rfile.read(size)
            handler.rfile.readline()
    length = int(handler.headers.get("Content-Length") or 0)
    return handler.rfile.read(length)


def _parse_multipart(content_type: str, body: bytes, recorded: RecordedRequest) -> None:
    """Split a ``multipart/form-data`` body exactly, without touching file bytes."""
    boundary = content_type.split("boundary=", 1)[1].encode()
    for part in body.split(b"--" + boundary)[1:]:
        if part.startswith(b"--"):
            break
        head, _, content = part[2:].partition(b"\r\n\r\n")
        content = content.removesuffix(b"\r\n")
        headers = dict(line.split(": ", 1) for line in head.decode().split("\r\n") if ": " in line)
        disposition = headers["Content-Disposition"]
        name = disposition.split('name="', 1)[1].split('"', 1)[0]
        if 'filename="' in disposition:
            filename = disposition.split('filename="', 1)[1].split('"', 1)[0]
            recorded.file = UploadedFile(filename, headers.get("Content-Type", ""), content)
        else:
            recorded.fields.append((name, content.decode()))


class _Handler(BaseHTTPRequestHandler):
    fake: ClassVar[FakeDocling]
    protocol_version = "HTTP/1.1"

    def _answer(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record(self, body: bytes) -> RecordedRequest:
        recorded = RecordedRequest(self.command, self.path, dict(self.headers.items()), body)
        self.fake.requests.append(recorded)
        return recorded

    def do_POST(self) -> None:
        body = _read_body(self)
        recorded = self._record(body)
        content_type = self.headers.get("Content-Type", "")
        if self.path != "/v1/convert/file/async" or "boundary=" not in content_type:
            self._answer(404, b'{"detail":"Not Found"}')
            return
        _parse_multipart(content_type, body, recorded)
        if self.fake.submit_answer is not None:
            self._answer(*self.fake.submit_answer)
            return
        task_id = self.fake.add_task()
        self._answer(200, self._status(task_id, "pending", 1))

    def do_GET(self) -> None:
        self._record(b"")
        path = self.path.split("?", 1)[0]
        if path.startswith("/v1/status/poll/"):
            if self.fake.poll_answer is not None:
                self._answer(*self.fake.poll_answer)
                return
            statuses = self.fake.tasks.get(path.rsplit("/", 1)[1])
            if statuses is None:
                self._answer(404, TASK_NOT_FOUND)
                return
            status = statuses.pop(0) if len(statuses) > 1 else statuses[0]
            position = 1 if status == "pending" else None
            self._answer(200, self._status(path.rsplit("/", 1)[1], status, position))
        elif path.startswith("/v1/result/"):
            if self.fake.result_answer is not None:
                self._answer(*self.fake.result_answer)
                return
            task_id = path.rsplit("/", 1)[1]
            statuses = self.fake.tasks.get(task_id)
            if statuses is None:
                self._answer(404, TASK_NOT_FOUND)
            elif statuses[0] in {"pending", "started"}:
                self._answer(404, RESULT_NOT_READY)
            else:
                # The real service removes the task DOCLING_SERVE_RESULT_REMOVAL_DELAY
                # seconds after the first fetch; the stand-in shows the state after it.
                del self.fake.tasks[task_id]
                self._answer(200, self.fake.result)
        else:
            self._answer(404, b'{"detail":"Not Found"}')

    @staticmethod
    def _status(task_id: str, status: str, position: int | None) -> bytes:
        return json.dumps(
            {
                "task_id": task_id,
                "task_type": "convert",
                "task_status": status,
                "task_position": position,
                "task_meta": None,
                "error_message": None,
                "failure": None,
            }
        ).encode()

    def log_message(self, format: str, *args: object) -> None:
        """Keep the test output quiet."""


@contextmanager
def running_fake_docling(result: bytes) -> Iterator[FakeDocling]:
    """Start the stand-in; yields its state with ``base_url`` filled in."""
    fake = FakeDocling(result=result)
    handler = type("Handler", (_Handler,), {"fake": fake})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    fake.base_url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
