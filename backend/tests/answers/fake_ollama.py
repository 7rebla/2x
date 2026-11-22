"""A stand-in for Ollama's model interface, served from a thread in the test process.

Answers ``GET /api/tags`` and ``POST /v1/embeddings`` like Ollama 0.40.17
(measured in work order 044), ``POST /v1/chat/completions`` as a stream of
server-sent events and ``POST /api/show`` (work order 121), and records every
request. No test talks to a real model service.
"""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

LOCAL_MODEL = {"name": "bge-m3:latest", "model": "bge-m3:latest", "size": 1157672605}
# A chat model entry as Ollama 0.40.17 lists it, with its capabilities.
CHAT_MODEL = {
    "name": "local-chat:latest",
    "model": "local-chat:latest",
    "size": 5000000000,
    "capabilities": ["completion", "tools"],
}
# An embedding model entry with its capabilities: it cannot generate text.
EMBEDDING_ONLY_MODEL = dict(LOCAL_MODEL, capabilities=["embedding"])

CHAT_PATH = "/v1/chat/completions"


def chat_event(content: str | None, finish_reason: str | None = None) -> bytes:
    """One event of a streamed chat answer, shaped like Ollama's /v1 stream."""
    chunk = {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "model": "local-chat:latest",
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
    }
    return b"data: " + json.dumps(chunk).encode() + b"\n\n"


@dataclass
class Pause:
    """Wait this long before the next line; stop if the client closes meanwhile."""

    seconds: float


def vector_for(text: str, dimensions: int) -> list[float]:
    """The vector the stand-in returns for ``text``: different texts, different vectors."""
    values = [float(len(text)), float(sum(map(ord, text)) % 997)]
    return (values + [0.5] * dimensions)[:dimensions]


@dataclass
class Recorded:
    """One request as the stand-in saw it."""

    method: str
    path: str
    body: Any


@dataclass
class FakeOllama:
    """Behaviour of the stand-in; tests change the fields before they send."""

    dimensions: int = 4
    models: list[dict[str, Any]] = field(default_factory=lambda: [dict(LOCAL_MODEL)])
    tags_status: int = 200
    embed_status: int = 200
    # Answer the entries of "data" in reverse order (with correct indices).
    reverse_order: bool = False
    # Drop the last entry of "data".
    drop_one: bool = False
    # Replace the whole answer to /api/tags or /v1/embeddings.
    tags_body: bytes | None = None
    embed_body: bytes | None = None
    requests: list[Recorded] = field(default_factory=list)
    # Chat (work order 121). The text pieces of the streamed answer.
    chat_pieces: list[str] = field(default_factory=lambda: ["Hello", ", ", "world"])
    chat_status: int = 200
    # A blank line and a comment line before every piece.
    chat_blank_lines: bool = False
    chat_comments: bool = False
    # An event with empty content after every piece.
    chat_empty_pieces: bool = False
    # The closing event with finish_reason "stop", and "data: [DONE]".
    chat_finish: bool = True
    chat_done: bool = True
    # Pieces sent after "data: [DONE]" (a client must not read them).
    chat_after_done: list[str] = field(default_factory=list)
    # Stop sending (close the connection) before this piece.
    chat_abort_before: int | None = None
    # Wait chat_pause_seconds before this piece.
    chat_pause_before: int | None = None
    chat_pause_seconds: float = 5.0
    # Send an error object after the pieces (the text must never reach the user).
    chat_error_text: str | None = None
    # Replace the whole stream with these raw lines.
    chat_lines: list[bytes] | None = None
    # Set when the client closed the connection before the stream ended.
    client_closed: threading.Event = field(default_factory=threading.Event)
    # Answers to POST /api/show by full model name; missing names get 404.
    show_answers: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def embed_requests(self) -> list[Recorded]:
        return [request for request in self.requests if request.path == "/v1/embeddings"]

    @property
    def chat_requests(self) -> list[Recorded]:
        return [request for request in self.requests if request.path == CHAT_PATH]

    def chat_script(self) -> list[bytes | Pause]:
        """The lines of the streamed answer, with pauses between them."""
        if self.chat_lines is not None:
            return list(self.chat_lines)
        script: list[bytes | Pause] = []
        for index, piece in enumerate(self.chat_pieces):
            if index == self.chat_abort_before:
                return script
            if index == self.chat_pause_before:
                script.append(Pause(self.chat_pause_seconds))
            if self.chat_blank_lines:
                script.append(b"\n")
            if self.chat_comments:
                script.append(b": keep-alive\n")
            script.append(chat_event(piece))
            if self.chat_empty_pieces:
                script.append(chat_event(""))
        if self.chat_error_text is not None:
            error = {"error": {"message": self.chat_error_text, "type": "api_error"}}
            script.append(b"data: " + json.dumps(error).encode() + b"\n\n")
        if self.chat_finish:
            script.append(chat_event("", "stop"))
        if self.chat_done:
            script.append(b"data: [DONE]\n\n")
        script.extend(chat_event(piece) for piece in self.chat_after_done)
        return script

    def answer(self, method: str, path: str, body: object) -> tuple[int, bytes]:
        self.requests.append(Recorded(method, path, body))
        if method == "GET" and path == "/api/tags":
            if self.tags_status != 200:
                return self.tags_status, b'{"error":"not here"}'
            if self.tags_body is not None:
                return 200, self.tags_body
            return 200, json.dumps({"models": self.models}).encode()
        if method == "POST" and path == "/v1/embeddings" and isinstance(body, dict):
            if self.embed_status == 404:
                error = {
                    "message": f"model '{body.get('model')}' not found",
                    "type": "not_found_error",
                }
                return 404, json.dumps({"error": error}).encode()
            if self.embed_status != 200:
                return self.embed_status, b'{"error":{"message":"failed"}}'
            if self.embed_body is not None:
                return 200, self.embed_body
            return 200, self._embeddings(body)
        if method == "POST" and path == "/api/show" and isinstance(body, dict):
            details = self.show_answers.get(str(body.get("model")))
            if details is None:
                return 404, b'{"error":"model not found"}'
            return 200, json.dumps(details).encode()
        return 404, b"404 page not found"

    def _embeddings(self, body: dict[str, Any]) -> bytes:
        texts = body["input"] if isinstance(body["input"], list) else [body["input"]]
        data = [
            {"object": "embedding", "embedding": vector_for(text, self.dimensions), "index": index}
            for index, text in enumerate(texts)
        ]
        if self.reverse_order:
            data.reverse()
        if self.drop_one:
            data.pop()
        answer = {"object": "list", "data": data, "model": body["model"], "usage": {}}
        return json.dumps(answer).encode()


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def _reply(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        body = json.loads(raw) if raw else None
        if method == "POST" and self.path == CHAT_PATH:
            self._stream_chat(body)
            return
        status, answer = self.server.fake.answer(method, self.path, body)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(answer)))
        self.end_headers()
        self.wfile.write(answer)

    def _stream_chat(self, body: object) -> None:
        """Send the chat answer line by line; HTTP/1.0, so the end closes the connection."""
        fake = self.server.fake
        fake.requests.append(Recorded("POST", self.path, body))
        if fake.chat_status != 200:
            answer = json.dumps({"error": {"message": "refused", "type": "api_error"}}).encode()
            self.send_response(fake.chat_status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(answer)))
            self.end_headers()
            self.wfile.write(answer)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        try:
            for item in fake.chat_script():
                if isinstance(item, Pause):
                    if self._client_closed_within(item.seconds):
                        fake.client_closed.set()
                        return
                    continue
                self.wfile.write(item)
                self.wfile.flush()
        except BrokenPipeError, ConnectionResetError:
            fake.client_closed.set()

    def _client_closed_within(self, seconds: float) -> bool:
        """Wait up to ``seconds``; return whether the client closed the connection."""
        self.connection.settimeout(seconds)
        try:
            received: bytes = self.connection.recv(1)
            return received == b""
        except TimeoutError:
            return False
        except OSError:
            return True
        finally:
            self.connection.settimeout(None)

    def do_GET(self) -> None:
        self._reply("GET")

    def do_POST(self) -> None:
        self._reply("POST")

    def log_message(self, format: str, *args: object) -> None:
        """Keep the test output quiet."""


class _Server(ThreadingHTTPServer):
    fake: FakeOllama


@contextmanager
def fake_ollama(
    fake: FakeOllama | None = None, host: str = "127.0.0.1"
) -> Iterator[tuple[str, FakeOllama]]:
    """Run the stand-in; yields its OpenAI-compatible base URL (``.../v1``) and its state."""
    state = fake or FakeOllama()
    server = _Server((host, 0), _Handler)
    server.fake = state
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{server.server_address[1]}/v1", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
