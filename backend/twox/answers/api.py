"""Answer API (work order 130): ``POST /api/v1/answers/`` and ``GET /api/v1/answers/status/``.

``POST /api/v1/answers/`` takes a question as JSON (``question``, optional
``device`` and ``plant`` ids) and streams the events of the answer service
(:func:`twox.answers.service.answer`) as server-sent events: ``sources``, then
``delta`` pieces, then ``done``; or ``error`` at any point. Each event is

    event: <type>
    data: <JSON>

followed by an empty line. The JSON is :func:`twox.answers.types.to_json` of
the event (so it carries ``type`` as well); an ``error`` adds a short
translated ``detail`` to its fixed ``code``. There is no ``id:`` and no
``retry:``: the client never reconnects on its own.

Permissions, CSRF, the throttle and the input check run in the usual DRF
order in a synchronous view; only then the stream starts. Failures before it
are plain JSON with ``detail`` (and ``code``): 400 invalid input, 403 no role
or no CSRF token, 409 ``ai_disabled`` (E-59: no search, no model, no
connection), 409 ``answer_in_progress`` (one answer per user at a time), 429
throttled, 503 ``chat_not_configured``. A failure of the model after the start
is an ``error`` event from the service, not an HTTP status.

The stream itself is asynchronous (E-03). It reads the synchronous events of
the service one by one in a worker thread, so no model piece blocks the event
loop. The first event runs the context selection with its database queries:
it is read in the thread of the request (``thread_sensitive=True``), whose
database connection Django closes when the request ends. The later events
only wait for the model and are read in any thread of the pool
(``thread_sensitive=False``); they open no database connection.

The stream ends after ``TWOX_ANSWER_TOTAL_TIMEOUT`` seconds at the latest with
``error`` and the code ``timeout``. When the time is up, when the client goes
away or when the answer ends, the chat model is closed (that stops a waiting
read at once), the generator of the service is closed (``close()``) and the
lock of the user is released.

``GET /api/v1/answers/status/`` says beforehand whether answers are
available: ``enabled`` (``TWOX_AI_ENABLED``), ``chat_model_configured``
(``TWOX_CHAT_MODEL`` set) and ``available`` (both, and the chat model passes
the check of the self-test, :func:`twox.config.selftest.check_chat`: only
``GET /api/tags``, nothing is generated). With the AI features off or without
a chat model nothing is contacted. The result of the check is kept in the
cache for :data:`STATUS_CACHE_SECONDS`.

Nothing is stored (D7 (a)). Neither the question, nor the answer, nor a
section text, nor a user name or the ids of the scope are logged: the service
writes its one line (:mod:`twox.answers.service`), this module only the
outcome of the stream. The question travels in the body only, never in the
address, so uvicorn's access log does not see it either.
"""

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
from typing import Any, Final

from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.http import StreamingHttpResponse
from django.utils.translation import gettext
from drf_spectacular.utils import OpenApiResponse, PolymorphicProxySerializer, extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from twox.accounts.permissions import CanRead
from twox.answers import chat as chat_module
from twox.answers import service
from twox.answers.chat import ChatModel
from twox.answers.types import (
    AnswerEvent,
    AnswerStatus,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    to_json,
)
from twox.assets.views import MAX_ID
from twox.config import selftest
from twox.files.serializers import ErrorDetailSerializer

logger = logging.getLogger(__name__)

#: Longest question, in characters after trimming (as the search query).
MAX_QUESTION_CHARS: Final = 500
#: Most ids in ``device`` or in ``plant``.
MAX_FILTER_IDS: Final = 100

#: ``code`` of the answers 409 and 503 before the stream.
CODE_AI_DISABLED: Final = "ai_disabled"
CODE_ANSWER_IN_PROGRESS: Final = "answer_in_progress"
CODE_CHAT_NOT_CONFIGURED: Final = "chat_not_configured"

#: Throttle scope of the answer endpoint; its rate is ``TWOX_ANSWER_RATE``.
THROTTLE_SCOPE: Final = "answers"

#: Lifetime of the lock "an answer runs for this user", in seconds. Longer
#: than the longest answer (``TWOX_ANSWER_TOTAL_TIMEOUT``, 180 by default, plus
#: the time to close), so that the lock of a crashed process ends by itself.
ANSWER_LOCK_SECONDS: Final = 600
ANSWER_LOCK_PREFIX: Final = "twox:answers:active:"

#: How long the result of the chat model check of the status is kept, in seconds.
STATUS_CACHE_SECONDS: Final = 30
STATUS_CACHE_KEY: Final = "twox:answers:chat_model_ready"

#: Media type of the stream.
EVENT_STREAM_TYPE: Final = "text/event-stream; charset=utf-8"

#: Outcome in the log line when the client went away before the end.
OUTCOME_CANCELLED: Final = "cancelled"


def error_details() -> dict[ErrorCode, str]:
    """The ``detail`` of every error code, in the language of the current request."""
    return {
        ErrorCode.AI_DISABLED: gettext("The AI features are switched off."),
        ErrorCode.MODEL_UNAVAILABLE: gettext("The language model is not available."),
        ErrorCode.MODEL_REJECTED: gettext("The language model refused the request."),
        ErrorCode.TIMEOUT: gettext("The answer took too long."),
        ErrorCode.SEARCH_FAILED: gettext("The documents could not be searched."),
        ErrorCode.INTERNAL: gettext("The answer failed."),
    }


def lock_seconds() -> int:
    """Lifetime of the lock: :data:`ANSWER_LOCK_SECONDS`, longer if the time limits need it."""
    longest = settings.TWOX_ANSWER_TOTAL_TIMEOUT + settings.TWOX_CHAT_TIMEOUT_SECONDS
    return max(ANSWER_LOCK_SECONDS, longest + 60)


# --- Serializers -----------------------------------------------------------------


def _id_list(description: str) -> serializers.ListField:
    return serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=MAX_ID),
        required=False,
        default=list,
        max_length=MAX_FILTER_IDS,
        help_text=description,
    )


class AnswerRequestSerializer(serializers.Serializer[Any]):
    """The question and its optional scope."""

    question = serializers.CharField(
        max_length=MAX_QUESTION_CHARS,
        help_text="The question, 1 to 500 characters after trimming white space.",
    )
    device = _id_list("Only sections of one of these devices (ids).")
    plant = _id_list("Only sections in one of these plants (ids).")


class AnswerRefusalSerializer(serializers.Serializer[Any]):
    """409 or 503: no answer is started; ``code`` says why."""

    detail = serializers.CharField()
    code = serializers.CharField(
        help_text=(
            f"{CODE_AI_DISABLED} (409), {CODE_ANSWER_IN_PROGRESS} (409) "
            f"or {CODE_CHAT_NOT_CONFIGURED} (503)."
        )
    )


class AnswerLocationSerializer(serializers.Serializer[Any]):
    """One place a source is stored at (document, version, device, plant)."""

    section_id = serializers.IntegerField()
    document_id = serializers.IntegerField()
    document_title = serializers.CharField()
    version_id = serializers.IntegerField()
    version_number = serializers.IntegerField()
    version_filename = serializers.CharField()
    is_latest_version = serializers.BooleanField()
    device_id = serializers.IntegerField()
    device_key = serializers.CharField()
    device_name = serializers.CharField()
    plant_id = serializers.IntegerField()
    plant_key = serializers.CharField()
    plant_name = serializers.CharField()


class AnswerSourceSerializer(serializers.Serializer[Any]):
    """A numbered source of the answer; the answer cites it as ``[n]``."""

    n = serializers.IntegerField(min_value=1)
    section_id = serializers.IntegerField()
    version_id = serializers.IntegerField()
    sha256 = serializers.CharField()
    page_start = serializers.IntegerField(allow_null=True)
    page_end = serializers.IntegerField(allow_null=True)
    heading_path = serializers.ListField(child=serializers.CharField())
    locations = AnswerLocationSerializer(many=True)
    snippet = serializers.CharField(
        help_text="Start of the section, at most 300 characters; not the whole section, not HTML."
    )


class AnswerSourcesEventSerializer(serializers.Serializer[Any]):
    """First event: the sources the answer may cite (empty: nothing found)."""

    type = serializers.CharField(help_text='Always "sources".')
    sources = AnswerSourceSerializer(many=True)


class AnswerDeltaEventSerializer(serializers.Serializer[Any]):
    """A piece of the answer text; provisional, ``done`` brings the checked text."""

    type = serializers.CharField(help_text='Always "delta".')
    text = serializers.CharField()


class AnswerDoneEventSerializer(serializers.Serializer[Any]):
    """Last event of an answer: the checked text replaces the pieces."""

    type = serializers.CharField(help_text='Always "done".')
    status = serializers.CharField(help_text=", ".join(item.value for item in AnswerStatus) + ".")
    cited = serializers.ListField(child=serializers.IntegerField(min_value=1))
    removed_sentences = serializers.IntegerField(min_value=0)
    final_text = serializers.CharField()


class AnswerErrorEventSerializer(serializers.Serializer[Any]):
    """The answer failed; nothing follows. No model output, no address."""

    type = serializers.CharField(help_text='Always "error".')
    code = serializers.CharField(help_text=", ".join(code.value for code in ErrorCode) + ".")
    detail = serializers.CharField()


class AnswerStatusSerializer(serializers.Serializer[Any]):
    """Whether answers can be asked for."""

    enabled = serializers.BooleanField(help_text="The AI features are on (TWOX_AI_ENABLED).")
    chat_model_configured = serializers.BooleanField(help_text="TWOX_CHAT_MODEL is set.")
    available = serializers.BooleanField(
        help_text="Both, and the chat model is loaded and can generate text."
    )


ANSWER_EVENT = PolymorphicProxySerializer(
    component_name="AnswerEvent",
    serializers={
        "sources": AnswerSourcesEventSerializer,
        "delta": AnswerDeltaEventSerializer,
        "done": AnswerDoneEventSerializer,
        "error": AnswerErrorEventSerializer,
    },
    resource_type_field_name="type",
)


# --- The stream ------------------------------------------------------------------


def server_sent_event(event: AnswerEvent, details: dict[ErrorCode, str]) -> bytes:
    """``event`` in the format of server-sent events, with ``detail`` for an error."""
    data = to_json(event)
    if isinstance(event, ErrorEvent):
        data["detail"] = details[event.code]
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event.type}\ndata: {text}\n\n".encode()


def _next_event(events: Iterator[AnswerEvent]) -> AnswerEvent | None:
    return next(events, None)


class AnswerLock:
    """The lock "an answer runs for this user" in the shared cache."""

    def __init__(self, key: str) -> None:
        self.key = key
        self._held = True

    @classmethod
    def acquire(cls, user_pk: object) -> AnswerLock | None:
        """Take the lock of the user; ``None`` if an answer of the user runs already."""
        key = f"{ANSWER_LOCK_PREFIX}{user_pk}"
        if not cache.add(key, 1, timeout=lock_seconds()):
            return None
        return cls(key)

    def release(self) -> None:
        """Release the lock; calling it again is harmless."""
        if self._held:
            self._held = False
            cache.delete(self.key)


class AnswerStream:
    """The events of one answer as server-sent events, within the total time."""

    def __init__(
        self,
        events: Generator[AnswerEvent],
        *,
        model: ChatModel,
        lock: AnswerLock,
        details: dict[ErrorCode, str],
        total_timeout: float,
    ) -> None:
        self.events = events
        self.model = model
        self.lock = lock
        self.details = details
        self.total_timeout = total_timeout
        self.started = False
        self.finished = False

    async def chunks(self) -> AsyncGenerator[bytes]:
        """Read the events one by one in a worker thread and send each at once."""
        self.started = True
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.total_timeout
        outcome = OUTCOME_CANCELLED
        pending: asyncio.Future[AnswerEvent | None] | None = None
        first = True
        try:
            while True:
                # The first event runs the context selection with its database
                # queries: in the thread of the request (see the module docstring).
                read = sync_to_async(_next_event, thread_sensitive=first)
                first = False
                pending = asyncio.ensure_future(read(self.events))
                done, _ = await asyncio.wait({pending}, timeout=max(0.0, deadline - loop.time()))
                if not done:
                    outcome = f"error code={ErrorCode.TIMEOUT.value}"
                    # Stops a read that waits for the model at once.
                    self.model.close()
                    yield server_sent_event(ErrorEvent(code=ErrorCode.TIMEOUT), self.details)
                    return
                step, pending = pending, None
                try:
                    event = step.result()
                except Exception as error:
                    logger.warning("Answer stream failed: %s", type(error).__name__)
                    event = ErrorEvent(code=ErrorCode.INTERNAL)
                if event is None:
                    return
                if isinstance(event, DoneEvent):
                    outcome = event.status.value
                elif isinstance(event, ErrorEvent):
                    outcome = f"error code={event.code.value}"
                yield server_sent_event(event, self.details)
                if isinstance(event, DoneEvent | ErrorEvent):
                    return
        finally:
            await self._finish(pending)
            logger.info("Answer stream ended: outcome=%s", outcome)

    async def _finish(self, pending: asyncio.Future[AnswerEvent | None] | None) -> None:
        """Close the model and the events and release the lock; also when cancelled."""
        self.finished = True
        try:
            self.model.close()
            if pending is not None:
                # A read still runs in its thread; with the model closed it ends
                # soon (at the latest after the time limit of its request).
                await asyncio.wait({pending})
                if not pending.cancelled():
                    pending.exception()
        finally:
            # ValueError: the read is still running (cancelled twice); the
            # generator is then closed when it is collected.
            with contextlib.suppress(ValueError):
                self.events.close()
            self.lock.release()

    def close_unstarted(self) -> None:
        """Free everything when the stream was never read (the response was dropped)."""
        if self.started:
            return
        self.started = self.finished = True
        try:
            self.events.close()
            self.model.close()
        finally:
            self.lock.release()


class AnswerStreamResponse(StreamingHttpResponse):
    """The answer as ``text/event-stream``; streamed under ASGI.

    Under ASGI Django iterates :meth:`__aiter__`; it closes the stream when it
    ends or when the client goes away. WSGI and the synchronous test client
    iterate :meth:`__iter__`, which collects all events first (the server of
    the project runs ASGI).
    """

    def __init__(self, stream: AnswerStream) -> None:
        self._stream = stream
        self._chunks = stream.chunks()
        super().__init__(self._chunks, content_type=EVENT_STREAM_TYPE)
        self.headers["Cache-Control"] = "no-cache"
        self.headers["X-Accel-Buffering"] = "no"
        self.headers["X-Content-Type-Options"] = "nosniff"

    async def __aiter__(self) -> AsyncIterator[bytes]:
        content = self.streaming_content
        try:
            if not isinstance(content, AsyncIterator):
                raise TypeError("the content of an answer stream is asynchronous")
            async for part in content:
                yield part
        finally:
            # Closing the outer iterator does not close the inner ones.
            await self._chunks.aclose()

    def __iter__(self) -> Iterator[bytes]:
        async def collect() -> list[bytes]:
            return [part async for part in self]

        return iter(async_to_sync(collect)())

    def close(self) -> None:
        self._stream.close_unstarted()
        super().close()


# --- Views -----------------------------------------------------------------------


def _refusal(detail: str, code: str, http_status: int) -> Response:
    return Response(AnswerRefusalSerializer({"detail": detail, "code": code}).data, http_status)


class AnswerView(APIView):
    """Ask a question; the answer comes as a stream of server-sent events."""

    permission_classes = (CanRead,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = THROTTLE_SCOPE

    @extend_schema(
        operation_id="answer",
        request=AnswerRequestSerializer,
        responses={
            (200, "text/event-stream"): OpenApiResponse(
                ANSWER_EVENT,
                description=(
                    "Server-sent events: sources, then delta pieces, then done; or error "
                    "at any point. Each event is 'event: <type>' and 'data: <JSON>'."
                ),
            ),
            400: OpenApiResponse(description="Invalid input; the errors are per field."),
            403: OpenApiResponse(ErrorDetailSerializer, description="No role or no CSRF token."),
            409: OpenApiResponse(
                AnswerRefusalSerializer,
                description="AI features off (ai_disabled), or an answer runs already.",
            ),
            429: OpenApiResponse(ErrorDetailSerializer, description="Too many questions."),
            503: OpenApiResponse(AnswerRefusalSerializer, description="No chat model configured."),
        },
    )
    def post(self, request: Request) -> Response | AnswerStreamResponse:
        """The answer to ``question`` from the documents, with numbered sources.

        Only one answer per user runs at a time. The pieces of ``delta`` are
        provisional; ``final_text`` of ``done`` is the checked answer.
        """
        payload = AnswerRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        values = payload.validated_data
        if not settings.TWOX_AI_ENABLED:
            return _refusal(
                gettext("Answers are not available: the AI features are switched off."),
                CODE_AI_DISABLED,
                status.HTTP_409_CONFLICT,
            )
        if not settings.TWOX_CHAT_MODEL:
            return _refusal(
                gettext("Answers are not available: no chat model is configured."),
                CODE_CHAT_NOT_CONFIGURED,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        lock = AnswerLock.acquire(request.user.pk)
        if lock is None:
            return _refusal(
                gettext("An answer of yours is still running. Wait for it or cancel it."),
                CODE_ANSWER_IN_PROGRESS,
                status.HTTP_409_CONFLICT,
            )
        try:
            model = chat_module.get_chat_model()
        except BaseException:
            lock.release()
            raise
        try:
            events = service.answer(
                values["question"],
                device_ids=values["device"],
                plant_ids=values["plant"],
                chat=model,
            )
        except BaseException:
            model.close()
            lock.release()
            raise
        stream = AnswerStream(
            events,
            model=model,
            lock=lock,
            details=error_details(),
            total_timeout=settings.TWOX_ANSWER_TOTAL_TIMEOUT,
        )
        return AnswerStreamResponse(stream)


def chat_model_ready() -> bool:
    """Whether the chat model passes the check of the self-test; kept for a short time."""
    model: str = settings.TWOX_CHAT_MODEL
    cached = cache.get(STATUS_CACHE_KEY)
    if isinstance(cached, dict) and cached.get("model") == model:
        return cached.get("ready") is True
    ready = selftest.check_chat(None)["chat_ok"]
    cache.set(STATUS_CACHE_KEY, {"model": model, "ready": ready}, STATUS_CACHE_SECONDS)
    return ready


class AnswerStatusView(APIView):
    """Whether answers are available, before a question is asked."""

    permission_classes = (CanRead,)

    @extend_schema(
        operation_id="answer_status",
        responses={
            200: AnswerStatusSerializer,
            403: OpenApiResponse(ErrorDetailSerializer, description="No role."),
        },
    )
    def get(self, request: Request) -> Response:
        """Whether the AI features are on, a chat model is set and ready.

        With the AI features off or without a chat model the model service is
        not contacted.
        """
        enabled: bool = settings.TWOX_AI_ENABLED
        configured = bool(settings.TWOX_CHAT_MODEL)
        available = enabled and configured and chat_model_ready()
        body = {"enabled": enabled, "chat_model_configured": configured, "available": available}
        return Response(AnswerStatusSerializer(body).data)
