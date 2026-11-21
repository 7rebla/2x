"""Size limit for uploads (twox.files.uploads): declared length, stream and ASGI."""

import asyncio
import json
from collections.abc import Iterator

import pytest
from django.core.files.uploadhandler import StopUpload
from django.core.handlers.wsgi import WSGIRequest
from django.test import RequestFactory
from pytest_django.fixtures import Settings

from twox.files.uploads import (
    MULTIPART_OVERHEAD_BYTES,
    ASGIApp,
    LimitedUploadHandler,
    Message,
    Receive,
    RequestBodyLimitMiddleware,
    Scope,
    Send,
    UploadTooLarge,
    check_content_length,
    declared_content_length,
    install_upload_limit,
    max_request_bytes,
)

LIMIT = 1000


@pytest.fixture(autouse=True)
def small_limit(settings: Settings) -> None:
    settings.TWOX_UPLOAD_MAX_BYTES = LIMIT


# --- declared length --------------------------------------------------------


def test_request_bound_is_the_limit_plus_the_form_around_it() -> None:
    assert max_request_bytes() == LIMIT + MULTIPART_OVERHEAD_BYTES


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, None), ("", None), ("12", 12), ("0", 0), ("-1", None), ("abc", None)],
)
def test_declared_content_length(raw: str | None, expected: int | None) -> None:
    meta = {} if raw is None else {"CONTENT_LENGTH": raw}

    assert declared_content_length(meta) == expected


def request_with_length(length: int) -> WSGIRequest:
    request = RequestFactory().post("/", data=b"", content_type="application/octet-stream")
    request.META["CONTENT_LENGTH"] = str(length)
    return request


def test_length_up_to_the_bound_passes() -> None:
    check_content_length(request_with_length(max_request_bytes()))


def test_length_over_the_bound_is_413() -> None:
    with pytest.raises(UploadTooLarge) as caught:
        check_content_length(request_with_length(max_request_bytes() + 1))

    assert caught.value.status_code == 413
    assert caught.value.get_codes() == "upload_too_large"
    assert str(LIMIT) in str(caught.value.detail)


def test_install_puts_the_limit_first_and_keeps_djangos_handlers(settings: Settings) -> None:
    request = request_with_length(10)

    limit = install_upload_limit(request)

    handlers = request.upload_handlers
    assert handlers[0] is limit
    assert [type(h).__name__ for h in handlers[1:]] == [
        path.rsplit(".", 1)[1] for path in settings.FILE_UPLOAD_HANDLERS
    ]


def test_install_refuses_a_large_declared_body_before_anything_else() -> None:
    request = request_with_length(max_request_bytes() + 1)

    with pytest.raises(UploadTooLarge):
        install_upload_limit(request)


# --- stream -----------------------------------------------------------------


def test_handler_passes_chunks_until_the_limit() -> None:
    handler = LimitedUploadHandler(request_with_length(10), max_bytes=LIMIT)

    assert handler.receive_data_chunk(b"a" * 600, 0) == b"a" * 600
    assert handler.receive_data_chunk(b"b" * 400, 600) == b"b" * 400
    assert handler.received == LIMIT
    assert not handler.exceeded


def test_handler_stops_the_upload_past_the_limit() -> None:
    handler = LimitedUploadHandler(request_with_length(10), max_bytes=LIMIT)
    handler.receive_data_chunk(b"a" * LIMIT, 0)

    with pytest.raises(StopUpload) as caught:
        handler.receive_data_chunk(b"b", LIMIT)

    assert caught.value.connection_reset is True
    assert handler.exceeded


# --- ASGI middleware --------------------------------------------------------


class FakeApp:
    """An ASGI app that reads the whole body and answers 200 with its size."""

    def __init__(self) -> None:
        self.called = False
        self.messages: list[Message] = []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.called = True
        if scope["type"] != "http":
            return
        size = 0
        while True:
            message = await receive()
            self.messages.append(message)
            if message["type"] == "http.disconnect":
                return  # as Django: drop everything, send nothing
            size += len(message.get("body", b""))
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": str(size).encode()})


def http_scope(content_length: int | None) -> Scope:
    headers = [(b"host", b"testserver")]
    if content_length is not None:
        headers.append((b"content-length", str(content_length).encode()))
    return {"type": "http", "method": "POST", "path": "/api/v1/x/", "headers": headers}


def run(app: ASGIApp, scope: Scope, chunks: list[bytes]) -> list[Message]:
    """Call ``app`` with ``chunks`` as body; return what it sent."""
    sent: list[Message] = []
    pending: Iterator[bytes] = iter(chunks)
    remaining = len(chunks)

    async def receive() -> Message:
        nonlocal remaining
        chunk = next(pending, None)
        if chunk is None:
            raise AssertionError("the app read past the end of the body")
        remaining -= 1
        return {"type": "http.request", "body": chunk, "more_body": remaining > 0}

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    return sent


def status_and_body(sent: list[Message]) -> tuple[int, bytes]:
    start = [m for m in sent if m["type"] == "http.response.start"]
    assert len(start) == 1
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return start[0]["status"], body


def test_middleware_refuses_a_large_declared_body_without_calling_the_app() -> None:
    inner = FakeApp()

    sent = run(RequestBodyLimitMiddleware(inner), http_scope(max_request_bytes() + 1), [b"x"])

    status, body = status_and_body(sent)
    assert status == 413
    assert str(LIMIT) in json.loads(body)["detail"]
    assert not inner.called


def test_middleware_passes_a_body_within_the_bound() -> None:
    inner = FakeApp()
    chunks = [b"a" * 500, b"b" * 500]

    sent = run(RequestBodyLimitMiddleware(inner), http_scope(1000), chunks)

    assert status_and_body(sent) == (200, b"1000")
    assert [m["body"] for m in inner.messages] == chunks


def test_middleware_stops_a_body_without_length_past_the_bound() -> None:
    inner = FakeApp()
    bound = max_request_bytes()
    chunks = [b"a" * bound, b"b", b"never read"]

    sent = run(RequestBodyLimitMiddleware(inner), http_scope(None), chunks)

    status, body = status_and_body(sent)
    assert status == 413
    assert "detail" in json.loads(body)
    # The app saw the first chunk, then a disconnect instead of the rest.
    assert [m["type"] for m in inner.messages] == ["http.request", "http.disconnect"]


def test_middleware_passes_other_scopes_unchanged() -> None:
    inner = FakeApp()

    asyncio.run(
        RequestBodyLimitMiddleware(inner)({"type": "lifespan"}, _never_receive, _never_send)
    )

    assert inner.called


async def _never_receive() -> Message:
    raise AssertionError("not expected")


async def _never_send(message: Message) -> None:
    raise AssertionError("not expected")
