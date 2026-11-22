"""A stand-in for Ollama's embedding interface, served from a thread in the test process.

Answers ``GET /api/tags`` and ``POST /v1/embeddings`` like Ollama 0.40.17
(measured in work order 044) and records every request. No test talks to a
real model service.
"""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

LOCAL_MODEL = {"name": "bge-m3:latest", "model": "bge-m3:latest", "size": 1157672605}


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

    @property
    def embed_requests(self) -> list[Recorded]:
        return [request for request in self.requests if request.path == "/v1/embeddings"]

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
        status, answer = self.server.fake.answer(method, self.path, body)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(answer)))
        self.end_headers()
        self.wfile.write(answer)

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
