"""Generate answers with a local chat model behind an OpenAI-compatible interface.

The only way the backend asks a language model for text (Startunterlage 5.2,
E-04): callers use the :class:`ChatModel` protocol and get an instance from
:func:`get_chat_model`, so the provider stays exchangeable and tests can put a
stand-in there (:class:`FakeChatModel`, no network).

:class:`OpenAICompatibleChat` sends ``POST {TWOX_LLM_BASE_URL}/chat/completions``
with ``model``, ``messages``, ``stream: true``, ``max_tokens``, ``temperature``,
``seed`` (only when given) and ``reasoning_effort`` (unless the setting is
``omit``). Nothing else: no ``user`` field, no tools, no JSON mode. The
messages go out exactly as given; the client adds nothing.

The answer comes as server-sent events and is read line by line:
:meth:`OpenAICompatibleChat.stream` checks the model and sends the request
in the call itself (errors come before anything is returned) and returns a
:class:`ChatStream`: a synchronous iterator (E-03) over the text pieces of
``choices[0].delta.content`` as they arrive, which can be closed at any time,
also before its first piece, and then frees the connection.
``TWOX_CHAT_TIMEOUT_SECONDS`` is the socket time limit, so it bounds the wait
for every single piece, the first one included; there is no limit for the
whole answer here (the answer service sets one).

AI features are optional (E-59). With ``TWOX_AI_ENABLED`` off, nothing here
opens a connection: :func:`get_chat_model` and every request raise
:class:`ChatDisabledError` first.

No text may leave the house (Leitplanke 6). Before a request the client checks,
with :mod:`twox.answers.llm_guard`,

1. the model name (no Ollama cloud model) - before every request;
2. the local model list ``GET /api/tags`` - once per client: the model has to
   be listed there, without ``remote_host`` or ``remote_model``;
3. the capability ``completion`` - an embedding model such as ``bge-m3``
   cannot answer. Ollama 0.40.17 lists ``capabilities`` in every entry of
   ``/api/tags`` (checked read-only in work order 121), so they are read
   there. Only if the entry has none, ``POST /api/show`` is asked - and only
   after step 2, when the model is known to be local (``/api/show`` asks
   ollama.com for a cloud model that was never pulled).

A server without ``/api/tags`` (another OpenAI-compatible server in the own
network) gets the name check only; a server that names no capabilities gets
no capability check. Both are logged at level ``info``.

Errors come as subclasses of :class:`ChatError` with short English messages
that name neither addresses nor texts; the original exception stays attached
(``__cause__``) for the server log. The log gets the kind of error, the model
name and the duration, never messages, prompt or answer.
"""

import contextlib
import json
import logging
import math
import socket
import threading
import urllib.error
import urllib.request
import weakref
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import partial
from http.client import HTTPException, HTTPResponse
from time import monotonic
from types import TracebackType
from typing import Final, Literal, Protocol, Self, TypedDict
from urllib.parse import urlsplit

from django.conf import settings

from twox.answers.llm_guard import (
    SHOW_PATH,
    TAGS_PATH,
    ModelListError,
    ModelNotLoadedError,
    NoCompletionError,
    RemoteModelError,
    check_chat_model,
    is_timeout,
    model_capabilities,
    ollama_root,
    require_completion,
    require_local_name,
)

logger = logging.getLogger(__name__)

CHAT_PATH: Final = "/chat/completions"
#: Values of ``reasoning_effort`` the client sends; ``None`` leaves the field out.
REASONING_EFFORTS: Final = frozenset({"none", "low", "medium", "high"})
#: Longest line of the event stream, in bytes (one piece is a few hundred).
MAX_LINE_BYTES: Final = 1024 * 1024
#: Most bytes of one streamed answer; protects against an endless answer.
MAX_STREAM_BYTES: Final = 16 * 1024 * 1024
#: Most bytes of the model list or the details of a model.
MAX_ANSWER_BYTES: Final = 16 * 1024 * 1024
_DATA_PREFIX: Final = b"data:"
_DONE: Final = b"[DONE]"

Role = Literal["system", "user", "assistant"]
_ROLES: Final = frozenset({"system", "user", "assistant"})


class ChatMessage(TypedDict):
    """One message of a conversation, as the OpenAI-compatible interface takes it."""

    role: Role
    content: str


class ChatError(Exception):
    """Base class of all errors of the chat interface."""


class ChatDisabledError(ChatError):
    """AI features are switched off (``TWOX_AI_ENABLED``); nothing was sent (E-59)."""


class ChatUnavailableError(ChatError):
    """No model configured, no connection, time limit, HTTP 5xx, an unusable
    answer or a stream that broke off. Retrying may make sense."""


class ChatRejectedError(ChatError):
    """The model service refused the request (HTTP 4xx), the model is not
    loaded, or it cannot generate text."""


class ChatRemoteModelError(ChatError):
    """The model runs remotely (an Ollama cloud model); texts would leave the house."""


def _end_stream(pieces: Iterator[str], on_close: Callable[[], None] | None) -> None:
    """Free what one answer holds: first the connection, then the reading generator."""
    if on_close is not None:
        on_close()
    close = getattr(pieces, "close", None)
    if callable(close):
        # ValueError: another thread is iterating right now; on_close above
        # has already ended its connection, so that thread stops by itself.
        with contextlib.suppress(ValueError):
            close()


class ChatStream(Iterator[str]):
    """The pieces of one answer, in order; an iterator that can be closed.

    :meth:`close` (also through ``with`` or :func:`contextlib.closing`) ends
    the answer and frees its connection in every case - before the first
    piece, in the middle or after the end - and may be called more than once.
    A stream that is dropped unclosed is closed when it is garbage-collected
    (:func:`weakref.finalize`); :meth:`OpenAICompatibleChat.close` closes it
    as well. To stop an answer from another thread, call the client's
    ``close()``, not this one.
    """

    def __init__(self, pieces: Iterator[str], on_close: Callable[[], None] | None = None) -> None:
        """``pieces`` yields the text; ``on_close`` frees the connection (idempotent)."""
        self._pieces = pieces
        # The callback must not refer to self, or the stream would never be collected.
        self._finalizer = weakref.finalize(self, _end_stream, pieces, on_close)
        self._finalizer.atexit = False

    def __next__(self) -> str:
        return next(self._pieces)

    def close(self) -> None:
        """End the answer and free its connection; calling it again is harmless."""
        self._finalizer()

    @property
    def closed(self) -> bool:
        """Whether :meth:`close` ran (or the stream was collected)."""
        return not self._finalizer.alive

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class ChatModel(Protocol):
    """Generates the text of an answer piece by piece."""

    @property
    def model_name(self) -> str:
        """Name of the model as the model service knows it."""
        ...

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> ChatStream:
        """Return the pieces of the answer to ``messages`` in order.

        ``None`` takes the value from the settings. Errors are :class:`ChatError`;
        they can come from this call or while iterating. Close the stream
        (``with`` or ``close()``) when it is not read to its end.
        """
        ...

    def close(self) -> None:
        """Stop a running stream and close its connection; calling it again is harmless."""
        ...


def _check_ai_enabled() -> None:
    if not settings.TWOX_AI_ENABLED:
        raise ChatDisabledError("AI features are not enabled (TWOX_AI_ENABLED is false)")


def _check_max_tokens(value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError("max_tokens must be a whole number greater than zero")


def _check_temperature(value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 2:
        raise ValueError("temperature must be a number from 0 to 2")


def _check_messages(messages: Sequence[ChatMessage]) -> list[ChatMessage]:
    """Return a plain copy of ``messages``; refuse anything that is no message."""
    if isinstance(messages, str | bytes) or not messages:
        raise ValueError("messages must be a non-empty sequence of messages")
    checked: list[ChatMessage] = []
    for message in messages:
        if (
            not isinstance(message, Mapping)
            or message.get("role") not in _ROLES
            or not isinstance(message.get("content"), str)
        ):
            raise ValueError("every message needs a role (system, user, assistant) and a text")
        checked.append({"role": message["role"], "content": message["content"]})
    return checked


def _abort(response: HTTPResponse) -> None:
    """Close ``response`` at once, also while another thread waits for it to read.

    ``close()`` alone does not wake a blocked read; shutting the socket down does.
    """
    raw = getattr(getattr(response, "fp", None), "raw", None)
    sock = getattr(raw, "_sock", None)
    if isinstance(sock, socket.socket):
        with contextlib.suppress(OSError):
            sock.shutdown(socket.SHUT_RDWR)
    with contextlib.suppress(OSError, ValueError):
        response.close()


@dataclass(eq=False)
class _Stream:
    """One open answer: its response, and whether someone closed it."""

    response: HTTPResponse
    closed: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def close(self) -> None:
        with self.lock:
            if self.closed:
                return
            self.closed = True
        _abort(self.response)


class OpenAICompatibleChat:
    """Chat model for ``POST /chat/completions`` of an OpenAI-compatible server (Ollama)."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout: float,
        max_tokens: int,
        temperature: float,
        reasoning_effort: str | None,
    ) -> None:
        """``reasoning_effort``: ``none``, ``low``, ``medium`` or ``high``; ``None``
        leaves the field out of the request."""
        parts = urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("base_url must look like http://host:port/v1")
        if not model.strip():
            raise ValueError("model must not be empty")
        if not 0 < timeout < math.inf:
            raise ValueError("timeout must be a positive number of seconds")
        _check_max_tokens(max_tokens)
        _check_temperature(temperature)
        if reasoning_effort is not None and reasoning_effort not in REASONING_EFFORTS:
            raise ValueError("reasoning_effort must be none, low, medium, high or None")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._temperature = float(temperature)
        self._reasoning_effort = reasoning_effort
        self._model_checked = False
        self._streams: set[_Stream] = set()
        self._streams_lock = threading.Lock()
        # No proxy on purpose: texts go to the configured address and nowhere else.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def from_settings(cls) -> OpenAICompatibleChat:
        """Build a client from ``TWOX_LLM_BASE_URL`` and the ``TWOX_CHAT_*`` settings."""
        return cls(
            base_url=settings.TWOX_LLM_BASE_URL,
            model=settings.TWOX_CHAT_MODEL,
            timeout=float(settings.TWOX_CHAT_TIMEOUT_SECONDS),
            max_tokens=settings.TWOX_CHAT_MAX_TOKENS,
            temperature=settings.TWOX_CHAT_TEMPERATURE,
            reasoning_effort=settings.TWOX_CHAT_REASONING_EFFORT,
        )

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def timeout(self) -> float:
        """Socket time limit: the longest wait for one piece of the answer, in seconds."""
        return self._timeout

    @property
    def chat_url(self) -> str:
        """The address every chat request goes to."""
        return self._base_url + CHAT_PATH

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> ChatStream:
        """Send the request and return the pieces of the answer as a :class:`ChatStream`.

        The checks and the request happen in this call: a refused or
        unreachable model, an HTTP error or AI switched off raise here, before
        anything is returned. The pieces are read while iterating. The
        connection is closed when the stream ends, when the stream is closed
        (also before its first piece), when it is dropped, or by :meth:`close`.
        """
        payload = self._payload(messages, max_tokens, temperature, seed)
        _check_ai_enabled()
        started = monotonic()
        try:
            self._ensure_local_model()
            response = self._open_chat(payload)
        except ChatError as error:
            self._log_failure(error, started)
            raise
        state = _Stream(response)
        with self._streams_lock:
            self._streams.add(state)
        return ChatStream(self._read(state, started), partial(self._release, state))

    def _release(self, state: _Stream) -> None:
        """Forget one answer and close its connection; harmless if done already."""
        with self._streams_lock:
            self._streams.discard(state)
        state.close()

    def close(self) -> None:
        with self._streams_lock:
            streams = list(self._streams)
            self._streams.clear()
        for state in streams:
            state.close()

    def _payload(
        self,
        messages: Sequence[ChatMessage],
        max_tokens: int | None,
        temperature: float | None,
        seed: int | None,
    ) -> dict[str, object]:
        checked = _check_messages(messages)
        tokens = self._max_tokens if max_tokens is None else max_tokens
        _check_max_tokens(tokens)
        heat = self._temperature if temperature is None else temperature
        _check_temperature(heat)
        payload: dict[str, object] = {
            "model": self._model,
            "messages": checked,
            "stream": True,
            "max_tokens": tokens,
            "temperature": float(heat),
        }
        if seed is not None:
            if type(seed) is not int:
                raise ValueError("seed must be a whole number")
            payload["seed"] = seed
        if self._reasoning_effort is not None:
            payload["reasoning_effort"] = self._reasoning_effort
        return payload

    def _ensure_local_model(self) -> None:
        """Refuse cloud models and models that cannot generate text (module docstring)."""
        try:
            require_local_name(self._model)
        except RemoteModelError as error:
            raise ChatRemoteModelError(str(error)) from None
        if self._model_checked:
            return
        root = ollama_root(self._base_url)
        status, body = self._request("GET", root + TAGS_PATH, None)
        try:
            entry = check_chat_model(status, body, self._model)
            if entry is None:
                # Not Ollama (another OpenAI-compatible server in the own network,
                # Startunterlage 5.2): there is no model list to check against.
                logger.info("No Ollama model list (HTTP %s); checked the model name only", status)
            elif model_capabilities(entry) is None and not require_completion(
                # The model is local (checked above), so asking for its details
                # stays in the house.
                self._show_capabilities(root),
                self._model,
            ):
                logger.info("The model service names no capabilities; capability not checked")
        except ModelListError as error:
            raise ChatUnavailableError(str(error)) from error
        except RemoteModelError as error:
            raise ChatRemoteModelError(str(error)) from error
        except ModelNotLoadedError as error:
            raise ChatRejectedError(str(error)) from error
        except NoCompletionError as error:
            raise ChatRejectedError(str(error)) from error
        self._model_checked = True

    def _show_capabilities(self, root: str) -> frozenset[str] | None:
        status, body = self._request("POST", root + SHOW_PATH, {"model": self._model})
        if status != 200:
            return None
        try:
            details = json.loads(body)
        except ValueError:
            return None
        return model_capabilities(details) if isinstance(details, dict) else None

    def _request(self, method: str, url: str, payload: object) -> tuple[int, bytes]:
        """Send one small request; return status and body. Network failures become errors."""
        _check_ai_enabled()
        request = self._build(method, url, payload, "application/json")
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                status: int = response.status
                body: bytes = response.read(MAX_ANSWER_BYTES + 1)
        except urllib.error.HTTPError as error:
            error.close()
            if error.code >= 500:
                raise ChatUnavailableError(
                    f"the model service failed (HTTP {error.code})"
                ) from error
            return error.code, b""
        except (urllib.error.URLError, HTTPException, OSError) as error:
            raise self._connection_error(error) from error
        if len(body) > MAX_ANSWER_BYTES:
            raise ChatUnavailableError("unexpected answer: too large")
        return status, body

    def _open_chat(self, payload: dict[str, object]) -> HTTPResponse:
        _check_ai_enabled()
        request = self._build("POST", self.chat_url, payload, "text/event-stream")
        try:
            response = self._opener.open(request, timeout=self._timeout)
        except urllib.error.HTTPError as error:
            error.close()
            if error.code == 404:
                raise ChatRejectedError(
                    f"model {self._model!r} not found by the model service;"
                    f" load it with: ollama pull {self._model}"
                ) from error
            if 400 <= error.code < 500:
                raise ChatRejectedError(
                    f"the model service refused the request (HTTP {error.code})"
                ) from error
            raise ChatUnavailableError(f"the model service failed (HTTP {error.code})") from error
        except (urllib.error.URLError, HTTPException, OSError) as error:
            raise self._connection_error(error) from error
        if not isinstance(response, HTTPResponse) or response.status != 200:
            status = getattr(response, "status", "?")
            response.close()
            raise ChatUnavailableError(f"unexpected answer from the model service (HTTP {status})")
        return response

    def _build(self, method: str, url: str, payload: object, accept: str) -> urllib.request.Request:
        data = None if payload is None else json.dumps(payload).encode()
        headers = {"Accept": accept}
        if data is not None:
            headers["Content-Type"] = "application/json"
        return urllib.request.Request(url, data=data, headers=headers, method=method)

    def _connection_error(self, error: BaseException) -> ChatUnavailableError:
        if is_timeout(error):
            return ChatUnavailableError(
                f"no answer from the model service within {self._timeout:g}s"
            )
        if isinstance(error, urllib.error.URLError) and isinstance(
            error.reason, ConnectionRefusedError
        ):
            return ChatUnavailableError(
                "the model service refused the connection (is Ollama running?)"
            )
        return ChatUnavailableError(f"cannot reach the model service ({type(error).__name__})")

    def _read(self, state: _Stream, started: float) -> Iterator[str]:
        """Yield the pieces of one answer; close its connection in every case."""
        pieces = 0
        try:
            for piece in self._pieces(state):
                pieces += 1
                yield piece
        except ChatError as error:
            self._log_failure(error, started)
            raise
        finally:
            self._release(state)
        logger.info(
            "Chat answer of model %s finished: %d pieces in %.1fs",
            self._model,
            pieces,
            monotonic() - started,
        )

    def _pieces(self, state: _Stream) -> Iterator[str]:
        received = 0
        finished = False
        while True:
            line = self._read_line(state)
            if line is None:
                return
            if not line:
                if finished:
                    return
                raise ChatUnavailableError("the answer broke off before its end")
            received += len(line)
            if received > MAX_STREAM_BYTES:
                raise ChatUnavailableError("unexpected answer: too large")
            line = line.rstrip(b"\r\n")
            if not line.startswith(_DATA_PREFIX):
                # Blank lines end an event; ":" lines are comments; other
                # fields (event:, id:) carry nothing the client needs.
                continue
            data = line[len(_DATA_PREFIX) :].strip()
            if data == _DONE:
                return
            content, finish = self._parse_event(data)
            finished = finished or finish
            if content:
                yield content

    def _read_line(self, state: _Stream) -> bytes | None:
        """Return the next line, ``b""`` at the end, ``None`` if someone closed the stream."""
        if state.closed:
            return None
        try:
            line = state.response.readline(MAX_LINE_BYTES + 1)
        except (HTTPException, OSError, ValueError, AttributeError) as error:
            if state.closed:
                return None
            if is_timeout(error):
                raise ChatUnavailableError(
                    f"no further answer from the model service within {self._timeout:g}s"
                ) from error
            raise ChatUnavailableError(f"the answer broke off ({type(error).__name__})") from error
        if state.closed:
            return None
        if len(line) > MAX_LINE_BYTES:
            raise ChatUnavailableError("unexpected answer: a line is too long")
        return line

    @staticmethod
    def _parse_event(data: bytes) -> tuple[str, bool]:
        """Return the text piece of one event and whether it ends the answer."""
        try:
            event = json.loads(data)
        except ValueError as error:
            raise ChatUnavailableError("unexpected answer: an event is not JSON") from error
        if not isinstance(event, dict):
            raise ChatUnavailableError("unexpected answer: an event is not an object")
        if event.get("error") is not None:
            # The text of the error stays out: it may repeat parts of the prompt.
            raise ChatUnavailableError("the model service reported an error during the answer")
        choices = event.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            return "", False
        choice = choices[0]
        delta = choice.get("delta")
        content = delta.get("content") if isinstance(delta, dict) else None
        return (content if isinstance(content, str) else ""), bool(choice.get("finish_reason"))

    def _log_failure(self, error: ChatError, started: float) -> None:
        logger.warning(
            "Chat request to model %s failed after %.1fs: %s",
            self._model,
            monotonic() - started,
            type(error).__name__,
        )


def get_chat_model() -> ChatModel:
    """Return the configured chat model; tests replace this function with a stand-in.

    Raises :class:`ChatDisabledError` when AI features are off (E-59) and
    :class:`ChatUnavailableError` when no model is configured; neither opens a
    connection.
    """
    _check_ai_enabled()
    if not settings.TWOX_CHAT_MODEL:
        raise ChatUnavailableError("no chat model configured (TWOX_CHAT_MODEL is empty)")
    return OpenAICompatibleChat.from_settings()


@dataclass
class FakeChatCall:
    """One call of :meth:`FakeChatModel.stream` as the stand-in saw it."""

    messages: list[ChatMessage]
    max_tokens: int | None
    temperature: float | None
    seed: int | None


class FakeChatModel:
    """A stand-in for :class:`ChatModel` in tests; no network.

    It yields ``pieces``. With ``error`` set it raises that error after
    ``error_after`` pieces (``0``: before the first one). With ``fail_on_call``
    set, the call of :meth:`stream` itself raises it. Every call is recorded
    in :attr:`calls`, every :meth:`close` counted in :attr:`close_count`.
    """

    def __init__(
        self,
        pieces: Sequence[str] = ("A stand-in answer.",),
        *,
        model_name: str = "fake-chat",
        error: ChatError | None = None,
        error_after: int = 0,
        fail_on_call: ChatError | None = None,
    ) -> None:
        if error_after < 0:
            raise ValueError("error_after must not be negative")
        self.pieces = list(pieces)
        self.error = error
        self.error_after = error_after
        self.fail_on_call = fail_on_call
        self.calls: list[FakeChatCall] = []
        self.close_count = 0
        self._model_name = model_name
        self._closed = False

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def last_messages(self) -> list[ChatMessage]:
        """The messages of the latest call."""
        if not self.calls:
            raise AssertionError("stream() was not called")
        return self.calls[-1].messages

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> ChatStream:
        self.calls.append(
            FakeChatCall(
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                max_tokens=max_tokens,
                temperature=temperature,
                seed=seed,
            )
        )
        if self.fail_on_call is not None:
            raise self.fail_on_call
        self._closed = False
        return ChatStream(self._pieces())

    def _pieces(self) -> Iterator[str]:
        for index, piece in enumerate(self.pieces):
            if self.error is not None and index == self.error_after:
                raise self.error
            if self._closed:
                return
            yield piece
        if self.error is not None and self.error_after >= len(self.pieces):
            raise self.error

    def close(self) -> None:
        self.close_count += 1
        self._closed = True
