"""ASGI entry point: Django behind the request body limit of twox.files.uploads."""

import asyncio
import json
from collections.abc import Iterator

import pytest
from pytest_django.fixtures import Settings

from twox.config.asgi import application, django_application
from twox.files.uploads import Message, RequestBodyLimitMiddleware, Scope, max_request_bytes

LIMIT = 1000


@pytest.fixture(autouse=True)
def small_limit(settings: Settings) -> None:
    settings.TWOX_UPLOAD_MAX_BYTES = LIMIT
    settings.ALLOWED_HOSTS = ["testserver"]


def scope(method: str, path: str, content_length: int | None) -> Scope:
    headers = [(b"host", b"testserver")]
    if content_length is not None:
        headers.append((b"content-length", str(content_length).encode()))
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }


def call(request_scope: Scope, chunks: list[bytes]) -> tuple[int, bytes, int]:
    """Run the ASGI application; return status, body and the number of chunks read."""
    pending: Iterator[bytes] = iter(chunks)
    read = 0
    sent: list[Message] = []

    async def receive() -> Message:
        nonlocal read
        chunk = next(pending, None)
        if chunk is None:
            # Django listens for a disconnect while it answers.
            await asyncio.Event().wait()
        read += 1
        return {"type": "http.request", "body": chunk, "more_body": read < len(chunks)}

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(application(request_scope, receive, send))
    start = next(m for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return start["status"], body, read


def test_application_is_django_behind_the_limit() -> None:
    assert isinstance(application, RequestBodyLimitMiddleware)
    assert application.app is django_application


def test_small_request_reaches_django() -> None:
    status, body, _ = call(scope("GET", "/api/v1/health/", 0), [b""])

    assert status == 200
    assert json.loads(body) == {"status": "ok"}


def test_large_declared_body_is_refused_before_django_reads_it() -> None:
    status, body, read = call(scope("POST", "/api/v1/health/", max_request_bytes() + 1), [b"x"])

    assert status == 413
    assert str(LIMIT) in json.loads(body)["detail"]
    assert read == 0


def test_streamed_body_past_the_bound_is_stopped() -> None:
    chunks = [b"x" * max_request_bytes(), b"x", b"never read"]

    status, body, read = call(scope("POST", "/api/v1/health/", None), chunks)

    assert status == 413
    assert "detail" in json.loads(body)
    assert read == 2
