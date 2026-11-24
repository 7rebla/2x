"""The answer API (work order 130): ``POST /api/v1/answers/`` and its status.

The chat model is always a stand-in (:class:`~twox.answers.chat.FakeChatModel`
or a subclass); no test reaches a real model service. The context selection
is a stand-in where only the flow matters, and the real one over the database
with :class:`FakeEmbedder` where database connections are checked. The
stream is read through the synchronous test client and through the ASGI
application. All texts are written for these tests (an invented gripper G-12).
"""

import asyncio
import inspect
import json
import logging
import threading
import time
import uuid
from collections.abc import Callable, Coroutine, Generator, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest
from asgiref.sync import async_to_sync
from django.conf import settings as django_settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import request_finished, request_started
from django.db import close_old_connections, connection, connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.test import Client
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from tests.accounts.users import make_user
from tests.answers.test_service import (
    GRIPPER_TEXT,
    OTHER_TEXT,
    QUESTION,
    forbid_chat_model,
    forbid_network,
    source,
    use_context,
)
from tests.config.test_logging import (
    ACCESS_FORMAT,
    CLIENT_ADDRESS,
    configured_access_log,
    restored_uvicorn_loggers,
)
from tests.search.fake_embedder import CLOSED_MODEL_SERVICE, FakeEmbedder, at_angle, embed
from tests.search.test_keyword_search import add_sections, make_device, make_document, make_plant
from twox.accounts.models import User
from twox.answers import api, context, service
from twox.answers import chat as chat_module
from twox.answers.chat import ChatStream, ChatUnavailableError, FakeChatModel
from twox.answers.types import NO_EVIDENCE_TEXT, SNIPPET_MAX_LENGTH, AnswerEvent, ErrorCode
from twox.config import selftest
from twox.config.asgi import application
from twox.config.settings import env_rate
from twox.files.uploads import Message, Scope

__all__ = ["restored_uvicorn_loggers"]

URL = "/api/v1/answers/"
STATUS_URL = "/api/v1/answers/status/"
CHAT_MODEL = "fake-chat"
ANSWER = ["Der Greifer G-12 ", "hält höchstens 5 kg [1]."]
CSRF_TOKEN = "a" * 32


# --- Fixtures and helpers ------------------------------------------------------------


@pytest.fixture(autouse=True)
def answers_on(settings: Settings) -> None:
    """AI on with a chat model, a cache of its own, no real model service."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": f"answers-{uuid.uuid4()}",
        }
    }
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_CHAT_MODEL = CHAT_MODEL
    settings.TWOX_LLM_BASE_URL = CLOSED_MODEL_SERVICE
    settings.ALLOWED_HOSTS = ["testserver"]


def install_chat[Chat: FakeChatModel](monkeypatch: pytest.MonkeyPatch, chat: Chat) -> Chat:
    """``get_chat_model`` returns ``chat``."""
    monkeypatch.setattr(chat_module, "get_chat_model", lambda: chat)
    return chat


@pytest.fixture
def chat(monkeypatch: pytest.MonkeyPatch) -> FakeChatModel:
    return install_chat(monkeypatch, FakeChatModel(ANSWER))


def signed_in(kind: str = "read", **kwargs: Any) -> tuple[APIClient, User]:  # noqa: ANN401
    client = APIClient(**kwargs)
    user = make_user(kind)
    assert user is not None
    client.force_login(user)
    return client, user


def ask(client: APIClient, body: object) -> Any:  # noqa: ANN401 - a test client response
    return client.post(URL, body, format="json")


def parse_events(body: bytes) -> list[dict[str, Any]]:
    """The events of a stream; checks the format of every event."""
    text = body.decode()
    assert text.endswith("\n\n"), text
    events: list[dict[str, Any]] = []
    for block in text[:-2].split("\n\n"):
        name_line, data_line = block.split("\n")
        assert name_line.startswith("event: ")
        assert data_line.startswith("data: ")
        data = json.loads(data_line.removeprefix("data: "))
        assert data["type"] == name_line.removeprefix("event: ")
        events.append(data)
    return events


def types_of(events: Sequence[dict[str, Any]]) -> list[str]:
    return [event["type"] for event in events]


def lock_key(user: User) -> str:
    return f"{api.ANSWER_LOCK_PREFIX}{user.pk}"


class GatedChat(FakeChatModel):
    """Yields one piece, then hangs until it is closed (a model that stopped).

    Records for every piece whether its thread held a database connection.
    """

    def __init__(self) -> None:
        super().__init__(["Der Greifer G-12 hält 5 kg [1]."])
        self.gate = threading.Event()
        self.streams: list[ChatStream] = []
        self.connection_free: list[bool] = []

    def stream(self, messages: Any, **kwargs: Any) -> ChatStream:  # noqa: ANN401
        stream = super().stream(messages, **kwargs)
        self.streams.append(stream)
        return stream

    def _pieces(self) -> Iterator[str]:
        self.connection_free.append(connections["default"].connection is None)
        yield self.pieces[0]
        # Bounded, so that a failing test does not hang.
        self.gate.wait(timeout=20)
        if not self.gate.is_set():
            yield "a late piece"

    def close(self) -> None:
        super().close()
        self.gate.set()


#: How long :class:`OpeningChat` needs to open its stream, in seconds.
OPENING_SECONDS = 1.5


class OpeningChat(FakeChatModel):
    """A model whose stream takes a while to open (model check, loading).

    As with the real client, a ``close()`` while ``stream()`` has not returned
    yet finds no stream and does nothing. The opened stream sends nothing
    until it is closed (the model takes long for the first piece).
    """

    def __init__(self) -> None:
        super().__init__(["Der Greifer G-12 hält 5 kg [1]."])
        self.gate = threading.Event()
        self.opened = threading.Event()
        self.streams: list[ChatStream] = []
        self.closes_while_opening = 0

    def stream(self, messages: Any, **kwargs: Any) -> ChatStream:  # noqa: ANN401
        time.sleep(OPENING_SECONDS)
        stream = super().stream(messages, **kwargs)
        self.streams.append(stream)
        self.opened.set()
        return stream

    def _pieces(self) -> Iterator[str]:
        # Bounded, so that a failing test does not hang.
        self.gate.wait(timeout=20)
        if not self.gate.is_set():
            yield from self.pieces

    def close(self) -> None:
        super().close()
        if self.opened.is_set():
            self.gate.set()
        else:
            self.closes_while_opening += 1


# --- ASGI ------------------------------------------------------------------------------


@dataclass
class AsgiAnswer:
    status: int
    headers: dict[bytes, bytes]
    bodies: list[bytes] = field(default_factory=list)

    @property
    def body(self) -> bytes:
        return b"".join(self.bodies)


def session_cookie(user: User) -> str:
    client = Client()
    client.force_login(user)
    return client.cookies[django_settings.SESSION_COOKIE_NAME].value


def asgi_scope(user: User, payload: bytes) -> Scope:
    cookie = (
        f"{django_settings.SESSION_COOKIE_NAME}={session_cookie(user)}; "
        f"{django_settings.CSRF_COOKIE_NAME}={CSRF_TOKEN}"
    )
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": URL,
        "raw_path": URL.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(payload)).encode()),
            (b"cookie", cookie.encode()),
            (b"x-csrftoken", CSRF_TOKEN.encode()),
        ],
        "client": ("192.0.2.10", 50000),
        "server": ("testserver", 80),
    }


def asgi_ask(
    user: User,
    body: object,
    *,
    disconnect_after_delta: bool = False,
    disconnect_when: Callable[[Message], bool] | None = None,
    runner: Callable[[Callable[[], Coroutine[Any, Any, None]]], None] | None = None,
) -> AsgiAnswer:
    """POST ``body`` through the ASGI application, as uvicorn would.

    ``disconnect_after_delta``: the client goes away after the first ``delta``;
    ``disconnect_when``: after the first message sent that it accepts.
    The default runner is :func:`async_to_sync`, which runs the synchronous
    parts in this thread (one database transaction with the test); pass
    ``lambda main: asyncio.run(main())`` for threads of their own.
    """
    payload = json.dumps(body).encode()
    request_scope = asgi_scope(user, payload)
    sent: list[Message] = []

    async def main() -> None:
        gone = asyncio.Event()
        delivered = False

        async def receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": payload, "more_body": False}
            await gone.wait()
            return {"type": "http.disconnect"}

        async def send(message: Message) -> None:
            sent.append(message)
            if disconnect_after_delta and b"event: delta" in message.get("body", b""):
                gone.set()
            if disconnect_when is not None and disconnect_when(message):
                gone.set()

        await application(request_scope, receive, send)

    if runner is None:
        # As the test client does: start and end of the request must not close
        # the connection of this thread, which holds the transaction of the test.
        request_started.disconnect(close_old_connections)
        request_finished.disconnect(close_old_connections)
        try:
            async_to_sync(main)()
        finally:
            request_started.connect(close_old_connections)
            request_finished.connect(close_old_connections)
    else:
        runner(main)
    start = next(m for m in sent if m["type"] == "http.response.start")
    answer = AsgiAnswer(status=start["status"], headers=dict(start["headers"]))
    answer.bodies = [m["body"] for m in sent if m["type"] == "http.response.body" and m.get("body")]
    return answer


# --- Permissions and input -------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["anonymous", "no_role"])
def test_without_role_both_endpoints_refuse(kind: str, chat: FakeChatModel) -> None:
    client = APIClient()
    user = make_user(kind)
    if user is not None:
        client.force_login(user)

    assert ask(client, {"question": QUESTION}).status_code == 403
    assert client.get(STATUS_URL).status_code == 403
    assert chat.calls == []


@pytest.mark.django_db
def test_without_csrf_token_the_question_is_refused(
    monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel
) -> None:
    stand_in = use_context(monkeypatch)
    client, _ = signed_in(enforce_csrf_checks=True)

    response = ask(client, {"question": QUESTION})

    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]
    assert stand_in.calls == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("body", "field_name"),
    [
        ({"question": ""}, "question"),
        ({"question": "   "}, "question"),
        ({"question": "x" * 501}, "question"),
        ({}, "question"),
        ({"question": QUESTION, "device": list(range(1, 102))}, "device"),
        ({"question": QUESTION, "plant": list(range(1, 102))}, "plant"),
        ({"question": QUESTION, "device": [0]}, "device"),
        ({"question": QUESTION, "plant": ["x"]}, "plant"),
    ],
)
def test_invalid_input_gives_400_at_the_field(
    body: dict[str, object], field_name: str, monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel
) -> None:
    stand_in = use_context(monkeypatch)
    client, user = signed_in()

    response = ask(client, body)

    assert response.status_code == 400
    assert field_name in response.json()
    assert stand_in.calls == []
    assert cache.get(lock_key(user)) is None


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["read", "manage"])
def test_both_roles_may_ask(
    kind: str, monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel
) -> None:
    use_context(monkeypatch)
    client, _ = signed_in(kind)

    response = ask(client, {"question": "x" * 500})

    assert response.status_code == 200
    assert types_of(parse_events(b"".join(response)))[-1] == "done"


@pytest.mark.django_db
def test_scope_and_trimmed_question_reach_the_service(
    monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel
) -> None:
    stand_in = use_context(monkeypatch)
    client, _ = signed_in()

    response = ask(client, {"question": f"  {QUESTION} ", "device": [7, 8], "plant": [3]})
    b"".join(response)

    assert stand_in.calls == [(QUESTION, (7, 8), (3,))]


# --- The stream ------------------------------------------------------------------------


def check_answered_stream(events: list[dict[str, Any]]) -> None:
    assert types_of(events) == ["sources", "delta", "delta", "done"]
    sources = events[0]["sources"]
    assert [item["n"] for item in sources] == [1, 2]
    assert set(sources[0]) == {
        "n",
        "section_id",
        "version_id",
        "sha256",
        "page_start",
        "page_end",
        "heading_path",
        "locations",
        "snippet",
    }
    assert sources[0]["snippet"] == GRIPPER_TEXT
    assert sources[0]["locations"][0]["device_key"] == "g-12"
    assert "text" not in sources[0]
    assert [event["text"] for event in events[1:3]] == ANSWER
    assert events[3] == {
        "type": "done",
        "status": "answered",
        "cited": [1],
        "removed_sentences": 0,
        "final_text": "".join(ANSWER),
    }


def check_stream_headers(headers: Callable[[str], str | None]) -> None:
    assert headers("Content-Type") == "text/event-stream; charset=utf-8"
    assert headers("Cache-Control") == "no-cache"
    assert headers("X-Accel-Buffering") == "no"
    assert headers("X-Content-Type-Options") == "nosniff"


@pytest.mark.django_db
def test_stream_through_the_synchronous_client(
    monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel
) -> None:
    use_context(monkeypatch)
    client, user = signed_in()

    response = ask(client, {"question": QUESTION})
    body = b"".join(response)

    assert response.status_code == 200
    check_stream_headers(response.get)
    check_answered_stream(parse_events(body))
    assert b"id:" not in body
    assert b"retry:" not in body
    assert cache.get(lock_key(user)) is None
    assert chat.close_count >= 1


@pytest.mark.django_db
def test_stream_through_the_asgi_application(
    monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel
) -> None:
    use_context(monkeypatch)
    user = make_user("read")
    assert user is not None

    answer = asgi_ask(user, {"question": QUESTION})

    assert answer.status == 200
    check_stream_headers(lambda name: answer.headers.get(name.encode()).decode())  # type: ignore[union-attr]
    events = parse_events(answer.body)
    check_answered_stream(events)
    # Sent event by event, not collected at the end.
    assert len(answer.bodies) == len(events)
    assert cache.get(lock_key(user)) is None


@pytest.mark.django_db
def test_below_the_threshold_the_model_is_not_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch, [], below_threshold=True)
    chat = install_chat(
        monkeypatch, FakeChatModel(fail_on_call=ChatUnavailableError("must not be asked"))
    )
    client, _ = signed_in()

    response = ask(client, {"question": QUESTION})
    events = parse_events(b"".join(response))

    assert events == [
        {"type": "sources", "sources": []},
        {
            "type": "done",
            "status": "no_evidence",
            "cited": [],
            "removed_sentences": 0,
            "final_text": NO_EVIDENCE_TEXT,
        },
    ]
    assert chat.calls == []


@pytest.mark.django_db
def test_sources_carry_a_snippet_not_the_whole_section(
    monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel
) -> None:
    hidden = "zzhidden-tail-of-the-section"
    long_text = "Der Greifer G-12 hält höchstens 5 kg. " * 20 + hidden
    assert len(long_text) > 2 * SNIPPET_MAX_LENGTH
    use_context(monkeypatch, [source(1, long_text)])
    client, _ = signed_in()

    body = b"".join(ask(client, {"question": QUESTION}))
    events = parse_events(body)

    snippet = events[0]["sources"][0]["snippet"]
    assert len(snippet) <= SNIPPET_MAX_LENGTH
    assert long_text.startswith(snippet.removesuffix("…"))
    assert hidden.encode() not in body


@pytest.mark.django_db
def test_model_failure_in_the_middle_is_an_error_event(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)
    failure = ChatUnavailableError("broke off at http://192.0.2.10:11434/v1 zzraw-model-text")
    install_chat(monkeypatch, FakeChatModel(ANSWER, error=failure, error_after=1))
    client, user = signed_in()

    response = ask(client, {"question": QUESTION})
    body = b"".join(response)
    events = parse_events(body)

    assert response.status_code == 200
    assert types_of(events) == ["sources", "delta", "error"]
    assert events[2] == {
        "type": "error",
        "code": "model_unavailable",
        "detail": "The language model is not available.",
    }
    assert b"192.0.2.10" not in body
    assert b"zzraw-model-text" not in body
    assert cache.get(lock_key(user)) is None


def test_every_error_code_has_a_detail() -> None:
    assert set(api.error_details()) == set(ErrorCode)


# --- Closing, lock, time limit -----------------------------------------------------------


@pytest.mark.django_db
def test_client_going_away_closes_the_model_and_frees_the_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_context(monkeypatch)
    chat = install_chat(monkeypatch, GatedChat())
    user = make_user("read")
    assert user is not None

    answer = asgi_ask(user, {"question": QUESTION}, disconnect_after_delta=True)

    assert types_of(parse_events(answer.body)) == ["sources", "delta"]
    assert chat.close_count >= 1
    assert all(stream.closed for stream in chat.streams)
    assert cache.get(lock_key(user)) is None


@pytest.mark.django_db
def test_closing_the_stream_after_the_first_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_context(monkeypatch)
    chat = install_chat(monkeypatch, GatedChat())
    client, user = signed_in()
    response = ask(client, {"question": QUESTION})

    async def first_two() -> list[bytes]:
        parts = aiter(response)
        received = [await anext(parts), await anext(parts)]
        await parts.aclose()
        return received

    received = async_to_sync(first_two)()

    assert types_of(parse_events(b"".join(received))) == ["sources", "delta"]
    assert chat.close_count >= 1
    assert all(stream.closed for stream in chat.streams)
    assert cache.get(lock_key(user)) is None


@pytest.mark.django_db
def test_a_stream_never_read_frees_the_lock_when_closed(
    monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel
) -> None:
    stand_in = use_context(monkeypatch)
    client, user = signed_in()

    response = ask(client, {"question": QUESTION})
    assert cache.get(lock_key(user)) == 1
    response.close()

    assert cache.get(lock_key(user)) is None
    assert chat.close_count == 1
    assert stand_in.calls == []


@pytest.mark.django_db
def test_total_time_limit_ends_the_stream_with_timeout(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    settings.TWOX_ANSWER_TOTAL_TIMEOUT = 1
    use_context(monkeypatch)
    chat = install_chat(monkeypatch, GatedChat())
    client, user = signed_in()

    started = time.monotonic()
    events = parse_events(b"".join(ask(client, {"question": QUESTION})))
    took = time.monotonic() - started

    assert types_of(events) == ["sources", "delta", "error"]
    assert events[-1]["code"] == "timeout"
    assert events[-1]["detail"] == "The answer took too long."
    assert 1 <= took < 10
    assert chat.close_count >= 1
    assert all(stream.closed for stream in chat.streams)
    assert cache.get(lock_key(user)) is None


@pytest.mark.django_db
def test_time_limit_while_the_stream_opens_closes_it_once_it_exists(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    settings.TWOX_ANSWER_TOTAL_TIMEOUT = 1
    use_context(monkeypatch)
    chat = install_chat(monkeypatch, OpeningChat())
    client, user = signed_in()

    started = time.monotonic()
    events = parse_events(b"".join(ask(client, {"question": QUESTION})))
    took = time.monotonic() - started

    assert types_of(events) == ["sources", "error"]
    assert events[-1]["code"] == "timeout"
    # The first close() came while the stream was opening and found nothing;
    # a later one closed the stream at once, without waiting for a piece.
    assert chat.closes_while_opening >= 1
    assert len(chat.streams) == 1
    assert chat.streams[0].closed
    assert took < OPENING_SECONDS + 2
    assert cache.get(lock_key(user)) is None


@pytest.mark.django_db
def test_client_going_away_while_the_stream_opens_frees_everything_soon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_context(monkeypatch)
    chat = install_chat(monkeypatch, OpeningChat())
    user = make_user("read")
    assert user is not None

    started = time.monotonic()
    answer = asgi_ask(
        user,
        {"question": QUESTION},
        disconnect_when=lambda message: b"event: sources" in message.get("body", b""),
    )
    took = time.monotonic() - started

    assert types_of(parse_events(answer.body)) == ["sources"]
    assert chat.closes_while_opening >= 1
    assert len(chat.streams) == 1
    assert chat.streams[0].closed
    assert took < OPENING_SECONDS + 2
    assert cache.get(lock_key(user)) is None


@pytest.mark.django_db
def test_client_going_away_during_the_context_selection(
    monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel
) -> None:
    stand_in = use_context(monkeypatch)

    def slow_select(question: str, **kwargs: Any) -> context.ContextSelection:  # noqa: ANN401
        time.sleep(1)
        return stand_in(question, **kwargs)

    monkeypatch.setattr(context, "select_context", slow_select)
    real_answer = service.answer
    generators: list[Generator[AnswerEvent]] = []

    def recording_answer(question: str, **kwargs: Any) -> Generator[AnswerEvent]:  # noqa: ANN401
        generator = real_answer(question, **kwargs)
        generators.append(generator)
        return generator

    monkeypatch.setattr(service, "answer", recording_answer)
    user = make_user("read")
    assert user is not None

    answer = asgi_ask(
        user,
        {"question": QUESTION},
        disconnect_when=lambda message: message["type"] == "http.response.start",
    )

    assert answer.body == b""
    assert len(stand_in.calls) == 1
    # close() ran on the generator of the service: it is finished.
    (generator,) = generators
    assert inspect.getgeneratorstate(generator) == inspect.GEN_CLOSED
    assert chat.calls == []
    assert chat.close_count >= 1
    assert cache.get(lock_key(user)) is None


@pytest.mark.django_db
def test_a_second_answer_of_the_same_user_waits_for_the_first(
    monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel
) -> None:
    stand_in = use_context(monkeypatch)
    client, user = signed_in()
    running = api.AnswerLock.acquire(user.pk)
    assert running is not None

    response = ask(client, {"question": QUESTION})

    assert response.status_code == 409
    assert response.json()["code"] == "answer_in_progress"
    assert response.json()["detail"]
    assert stand_in.calls == []
    running.release()
    assert ask(client, {"question": QUESTION}).status_code == 200


@pytest.mark.django_db
def test_lock_lives_longer_than_an_answer(settings: Settings) -> None:
    assert api.lock_seconds() == api.ANSWER_LOCK_SECONDS
    assert settings.TWOX_ANSWER_TOTAL_TIMEOUT + settings.TWOX_CHAT_TIMEOUT_SECONDS < 600
    settings.TWOX_ANSWER_TOTAL_TIMEOUT = 3000
    assert api.lock_seconds() > 3000 + settings.TWOX_CHAT_TIMEOUT_SECONDS


@pytest.mark.django_db
def test_throttle_counts_per_user(monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel) -> None:
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {api.THROTTLE_SCOPE: "2/min"})
    use_context(monkeypatch)
    first, _ = signed_in("read")
    second, _ = signed_in("manage")

    statuses = []
    for _ in range(3):
        response = ask(first, {"question": QUESTION})
        if response.status_code == 200:
            b"".join(response)
        statuses.append(response.status_code)
    other = ask(second, {"question": QUESTION})
    b"".join(other)

    assert statuses == [200, 200, 429]
    assert other.status_code == 200


def test_throttle_is_only_on_the_answer_endpoint() -> None:
    assert "DEFAULT_THROTTLE_CLASSES" not in django_settings.REST_FRAMEWORK
    assert django_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] == {
        "answers": django_settings.TWOX_ANSWER_RATE
    }
    assert api.AnswerView.throttle_classes == (ScopedRateThrottle,)
    assert api.AnswerStatusView.throttle_classes != (ScopedRateThrottle,)


# --- AI off, no chat model, status -------------------------------------------------------


def spy_check_chat(monkeypatch: pytest.MonkeyPatch, ok: bool = True) -> list[None]:
    calls: list[None] = []

    def check(embedder: object) -> selftest.ChatCheck:
        calls.append(None)
        return {"chat_model": CHAT_MODEL, "chat_ok": ok, "chat_error": "" if ok else "not loaded"}

    monkeypatch.setattr(selftest, "check_chat", check)
    return calls


def forbid_context(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    attempts: list[str] = []

    def refuse(question: str, **kwargs: object) -> object:
        attempts.append(question)
        raise AssertionError("nothing must be searched")

    monkeypatch.setattr(context, "select_context", refuse)
    return attempts


@pytest.mark.django_db
@pytest.mark.parametrize("model", [CHAT_MODEL, ""])
def test_ai_off_contacts_nothing(
    model: str, monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    settings.TWOX_AI_ENABLED = False
    settings.TWOX_CHAT_MODEL = model
    client, _ = signed_in()
    searched = forbid_context(monkeypatch)
    fetched = forbid_chat_model(monkeypatch)
    checks = spy_check_chat(monkeypatch)
    network = forbid_network(monkeypatch)

    response = ask(client, {"question": QUESTION})
    status = client.get(STATUS_URL)

    assert response.status_code == 409
    assert response.json()["code"] == "ai_disabled"
    assert response.json()["detail"]
    assert status.status_code == 200
    assert status.json() == {
        "enabled": False,
        "chat_model_configured": bool(model),
        "available": False,
    }
    assert searched == fetched == network == []
    assert checks == []


@pytest.mark.django_db
def test_without_chat_model_nothing_is_contacted(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    settings.TWOX_CHAT_MODEL = ""
    client, _ = signed_in()
    searched = forbid_context(monkeypatch)
    fetched = forbid_chat_model(monkeypatch)
    checks = spy_check_chat(monkeypatch)
    network = forbid_network(monkeypatch)

    response = ask(client, {"question": QUESTION})
    status = client.get(STATUS_URL)

    assert response.status_code == 503
    assert response.json()["code"] == "chat_not_configured"
    assert status.json() == {"enabled": True, "chat_model_configured": False, "available": False}
    assert searched == fetched == network == []
    assert checks == []


@pytest.mark.django_db
def test_status_available_after_the_check_and_kept_in_the_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks = spy_check_chat(monkeypatch)
    client, _ = signed_in()

    first = client.get(STATUS_URL)
    second = client.get(STATUS_URL)

    assert first.json() == {"enabled": True, "chat_model_configured": True, "available": True}
    assert second.json() == first.json()
    assert len(checks) == 1


@pytest.mark.django_db
def test_status_not_available_when_the_check_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    spy_check_chat(monkeypatch, ok=False)
    client, _ = signed_in()

    body = client.get(STATUS_URL).json()

    # Only the three flags: no model name, no address, no message of the check.
    assert body == {"enabled": True, "chat_model_configured": True, "available": False}


@pytest.mark.django_db
def test_status_asks_the_real_check_of_the_self_test(settings: Settings) -> None:
    # The model service is a closed port: the check fails, nothing breaks.
    client, _ = signed_in()

    assert client.get(STATUS_URL).json()["available"] is False


# --- Settings ----------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["10/min", "1/s", "100/hour", "5/day", "3/m"])
def test_valid_rates(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWOX_TEST_RATE", value)
    assert env_rate("TWOX_TEST_RATE", "10/min") == value


@pytest.mark.parametrize("value", ["0/min", "ten/min", "10", "10/week", "-1/min", "10 / min"])
def test_invalid_rates_stop_the_start(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWOX_TEST_RATE", value)
    with pytest.raises(ImproperlyConfigured, match="TWOX_TEST_RATE"):
        env_rate("TWOX_TEST_RATE", "10/min")


def test_unset_rate_takes_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TWOX_TEST_RATE", raising=False)
    assert env_rate("TWOX_TEST_RATE", "10/min") == "10/min"


# --- Database connections ----------------------------------------------------------------


def database_sessions() -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
        row = cursor.fetchone()
    assert row is not None
    return int(row[0])


def wait_for_sessions(expected: int) -> int:
    """The number of sessions once it is back at ``expected`` (or after 5 s)."""
    deadline = time.monotonic() + 5
    count = database_sessions()
    while count != expected and time.monotonic() < deadline:
        time.sleep(0.05)
        count = database_sessions()
    return count


@pytest.mark.usefixtures("every_text_a_source")  # short texts, work order 153
@pytest.mark.django_db(transaction=True)
def test_no_database_connection_stays_open_after_the_stream(
    fake_embedder: FakeEmbedder, monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    settings.TWOX_CHAT_MODEL = CHAT_MODEL
    device = make_device(make_plant(), "gripper-db")
    (section_a,) = add_sections(make_document(device, title="Handbuch A"), GRIPPER_TEXT, page=4)
    (section_b,) = add_sections(make_document(device, title="Handbuch B"), OTHER_TEXT, page=9)
    embed(section_a, at_angle(10, axis=1))
    embed(section_b, at_angle(20, axis=2))
    user = make_user("read")
    assert user is not None

    # The real context selection; note the connection of the thread it ran in.
    real_select = context.select_context
    used: list[tuple[BaseDatabaseWrapper, str]] = []

    def select(question: str, **kwargs: Any) -> context.ContextSelection:  # noqa: ANN401
        selection = real_select(question, **kwargs)
        used.append((connections["default"], threading.current_thread().name))
        return selection

    monkeypatch.setattr(context, "select_context", select)
    before = database_sessions()

    def run(main: Callable[[], Coroutine[Any, Any, None]]) -> None:
        # A loop of its own, as under uvicorn: the request gets its own thread.
        asyncio.run(main())

    for disconnect in (False, True, False):
        chat = install_chat(monkeypatch, GatedChat() if disconnect else FakeChatModel(ANSWER))
        answer = asgi_ask(
            user, {"question": QUESTION}, disconnect_after_delta=disconnect, runner=run
        )
        events = types_of(parse_events(answer.body))
        assert events[:2] == ["sources", "delta"]
        if isinstance(chat, GatedChat):
            # The model pieces were read in threads without a connection.
            assert chat.connection_free == [True]

    assert len(used) == 3
    assert all(wrapper.connection is None for wrapper, _ in used)
    assert threading.current_thread().name not in {name for _, name in used}
    assert wait_for_sessions(before) == before


# --- Logs ------------------------------------------------------------------------------


@pytest.mark.django_db
def test_logs_hold_no_question_answer_or_section_text(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    restored_uvicorn_loggers: None,
) -> None:
    logger, access = configured_access_log()
    caplog.set_level(logging.DEBUG)
    question = "Wie schwer darf zzfrage-marker am Greifer sein?"
    answer_text = "zzantwort-marker hält 5 kg [1]."
    section_text = "Der Greifer G-12 hält 5 kg. zzabschnitt-marker"
    use_context(monkeypatch, [source(1, section_text)])
    client, user = signed_in()

    # Answered.
    install_chat(monkeypatch, FakeChatModel([answer_text]))
    answered = ask(client, {"question": question})
    assert b"event: done" in b"".join(answered)
    # 400: too long.
    assert ask(client, {"question": question * 20}).status_code == 400
    # 409: an answer runs already.
    running = api.AnswerLock.acquire(user.pk)
    assert running is not None
    assert ask(client, {"question": question}).status_code == 409
    running.release()
    # The model fails in the middle.
    failure = ChatUnavailableError("zzantwort-marker")
    install_chat(monkeypatch, FakeChatModel([answer_text], error=failure, error_after=1))
    b"".join(ask(client, {"question": question}))
    # The access line uvicorn writes for such a request.
    logger.info(ACCESS_FORMAT, CLIENT_ADDRESS, "POST", URL, "1.1", 200)

    logged = caplog.text + access.getvalue()
    assert "Answer stream ended" in caplog.text
    assert f'"POST {URL} HTTP/1.1" 200' in access.getvalue()
    for marker in ("zzfrage-marker", "zzantwort-marker", "zzabschnitt-marker", "Greifer"):
        assert marker not in logged
