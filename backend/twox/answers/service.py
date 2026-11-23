"""The answer service: question in, stream of answer events out (M3, work order 126).

:func:`answer` puts the building blocks together, without HTTP: the context
selection (:mod:`twox.answers.context`), the prompt
(:mod:`twox.answers.prompt`), the chat model (:mod:`twox.answers.chat`) and
the citation check (:mod:`twox.answers.citations`). The events follow the
contract of :mod:`twox.answers.types`: one ``sources``, then ``delta`` pieces,
then ``done``; or ``error`` at any point, after which nothing follows. The
only exception: with the AI features off the stream is a single
``error(ai_disabled)`` without ``sources``.

The steps, in this order:

1. AI features off (E-59, D10 (a)): ``error(ai_disabled)``. No context
   selection, no chat model, no connection; a ``chat`` passed in is not used.
2. An empty question raises :class:`ValueError` when :func:`answer` is
   called, before any event. The maximum length is checked by the caller.
3. Context: :func:`twox.answers.context.select_context`. A failure becomes
   ``error`` with a fixed code (:func:`context_error_code`). After a
   successful selection an optional observer gets ``best_distance`` and
   ``below_threshold`` (never the selection itself), once per request.
4. ``sources``: the public view (:func:`twox.answers.types.to_source_ref`) of
   the selected sources, numbered as the selection numbers them.
5. Below the threshold (or without any source): the ``sources`` event is
   empty and ``done(no_evidence)`` with :data:`NO_EVIDENCE_TEXT` follows at
   once. The chat model is neither fetched nor asked (D8 (a)).
6. Model: ``chat``, or :func:`twox.answers.chat.get_chat_model`. The messages
   come only from :func:`twox.answers.prompt.build_messages` with a fresh
   identifier from :func:`twox.answers.prompt.new_nonce` (guard rail 4).
   ``max_tokens`` and ``temperature`` stay ``None`` (the settings
   ``TWOX_CHAT_*`` apply); ``seed`` is passed on unchanged.
7. ``delta``: every piece of the model is passed on at once and collected.
8. ``done``: :func:`twox.answers.citations.verify` with
   ``drop_unsupported=True`` (D8 (c)). ``removed_sentences`` counts every
   flagged or dropped sentence. With ``no_evidence`` the final text is always
   :data:`NO_EVIDENCE_TEXT` and ``cited`` is empty.
9. Errors of the chat model become ``error`` with a fixed code
   (:func:`chat_error_code`), also after some ``delta``. Unexpected
   exceptions become ``error(internal)``. No event carries an exception
   text, an address or model output.
10. Cancelling: when the caller closes the generator (or drops it), the
    stream of the model is closed in a ``finally``. A ``chat`` passed in is
    not closed, only its stream; a model fetched here is closed as well.

Streaming (D9 (a)): the ``delta`` pieces are provisional. What counts is
:attr:`~twox.answers.types.DoneEvent.final_text`, the checked text.

Nothing is stored (D7 (a)): no model, no table, no cache. The logger
``twox.answers.service`` writes at most one line per request (E-62): the
result (status, error code or ``cancelled``), the model name, the duration
in ms, the number of sources and, for ``done``, the numbers of valid
citations and of removed sentences; for an error only the type name of the
exception. Never the question, the answer, a piece, a section text, a file
name, a title, a device or plant id or an address.

The module calls the building blocks through their modules
(``chat_module.get_chat_model()``, ``prompt.new_nonce()``, ...), so that tests
and recordings (work order 135) can replace them with ``monkeypatch``.
"""

import logging
import urllib.error
from collections.abc import Callable, Generator, Sequence
from dataclasses import dataclass
from http import HTTPStatus
from time import monotonic

from django.conf import settings

from twox.answers import chat as chat_module
from twox.answers import citations, context, prompt, types
from twox.answers.chat import ChatModel, ChatStream
from twox.answers.llm_guard import ModelNotLoadedError, is_timeout
from twox.answers.types import (
    AnswerEvent,
    AnswerStatus,
    DeltaEvent,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    SourcesEvent,
)

logger = logging.getLogger(__name__)

#: Non-public callback of the evaluation tool: ``(best_distance, below_threshold)``.
ContextObserver = Callable[[float | None, bool], None]

#: Result in the log line when the caller closed the stream before its end.
CANCELLED = "cancelled"
#: Model name in the log line when no model was fetched.
NO_MODEL = "-"
#: Results logged as a warning: every error code but the neutral "AI off".
_FAILURES = frozenset(code.value for code in ErrorCode if code is not ErrorCode.AI_DISABLED)


def _is_missing_model(error: chat_module.ChatRejectedError) -> bool:
    """Whether a refusal means "no such model": not in ``/api/tags`` or HTTP 404.

    :mod:`twox.answers.chat` raises :class:`~twox.answers.chat.ChatRejectedError`
    for both a missing model and an explicit refusal; the cause tells them apart.
    """
    cause = error.__cause__
    if isinstance(cause, ModelNotLoadedError):
        return True
    return isinstance(cause, urllib.error.HTTPError) and cause.code == HTTPStatus.NOT_FOUND


def chat_error_code(error: BaseException) -> ErrorCode:
    """The fixed code for an exception of the chat model (or of getting it).

    A model that is missing (not loaded, HTTP 404) is ``model_unavailable``;
    ``model_rejected`` is left for models refused on purpose (a cloud model,
    no capability ``completion``, another HTTP 4xx).
    """
    match error:
        case chat_module.ChatDisabledError():
            return ErrorCode.AI_DISABLED
        case chat_module.ChatRejectedError() if _is_missing_model(error):
            return ErrorCode.MODEL_UNAVAILABLE
        case chat_module.ChatRejectedError() | chat_module.ChatRemoteModelError():
            return ErrorCode.MODEL_REJECTED
        case chat_module.ChatError():
            cause = error.__cause__
            if isinstance(cause, BaseException) and is_timeout(cause):
                return ErrorCode.TIMEOUT
            return ErrorCode.MODEL_UNAVAILABLE
        case TimeoutError():
            return ErrorCode.TIMEOUT
    return ErrorCode.INTERNAL


def context_error_code(error: BaseException) -> ErrorCode:
    """The fixed code for an exception of the context selection."""
    match error:
        case context.ContextDisabledError():
            return ErrorCode.AI_DISABLED
        case context.ContextUnavailableError():
            # The vector search did not take part: "nothing found" would mislead.
            return ErrorCode.MODEL_UNAVAILABLE
    # Any other failure while selecting: the database or the search.
    return ErrorCode.SEARCH_FAILED


@dataclass
class _Outcome:
    """What the single log line of a request says."""

    started: float
    result: str = CANCELLED
    model: str = NO_MODEL
    sources: int = 0
    cited: int | None = None
    removed: int | None = None
    exception: str | None = None
    logged: bool = False

    def finish(self, result: str, *, exception: BaseException | None = None) -> None:
        """Write the one log line of this request (only once)."""
        self.result = result
        if exception is not None:
            self.exception = type(exception).__name__
        self.write()

    def write(self) -> None:
        if self.logged:
            return
        self.logged = True
        duration_ms = round((monotonic() - self.started) * 1000)
        parts = [
            f"result={self.result}",
            f"model={self.model}",
            f"duration_ms={duration_ms}",
            f"sources={self.sources}",
        ]
        if self.cited is not None:
            parts.append(f"cited={self.cited}")
        if self.removed is not None:
            parts.append(f"removed_sentences={self.removed}")
        if self.exception is not None:
            parts.append(f"exception={self.exception}")
        failed = self.result in _FAILURES
        logger.log(logging.WARNING if failed else logging.INFO, "Answer: %s", " ".join(parts))


def answer(
    question: str,
    *,
    device_ids: Sequence[int] = (),
    plant_ids: Sequence[int] = (),
    chat: ChatModel | None = None,
    seed: int | None = None,
    on_context: ContextObserver | None = None,
) -> Generator[AnswerEvent]:
    """The events of the answer to ``question``, within the devices and plants given.

    Returns a generator: ``sources``, then ``delta`` pieces, then ``done``;
    or ``error`` at any point (``error(ai_disabled)`` alone when the AI
    features are off). The ``delta`` pieces are provisional; the checked text
    is :attr:`~twox.answers.types.DoneEvent.final_text` of ``done`` (D9 (a)),
    and it replaces them.

    ``chat`` is used instead of :func:`twox.answers.chat.get_chat_model` and
    is not closed here (only its stream). ``seed`` goes to
    :meth:`~twox.answers.chat.ChatModel.stream` unchanged; ``None`` sends none.

    ``on_context`` is a non-public measuring aid (the evaluation tool, work
    order 142; not part of the event contract). It is called exactly once per
    request, right after a successful context selection and before the
    ``sources`` event, with the two values ``best_distance`` (the smallest
    cosine distance of all search hits before the selection, not the distance
    of a cited source) and ``below_threshold``; never with the selection or a
    section text. It is not called with the AI features off or when the
    selection fails. Exceptions of the callback are not caught here: they
    leave the generator like any other error of the caller.

    Raises :class:`ValueError` at once for an empty question (with the AI
    features on).

    A caller that does not read the events to their end must call
    ``close()`` on the generator (or use :func:`contextlib.closing`): that
    closes the stream of the model at once, and a model fetched here.
    Without it the stream stays open until the generator is garbage-collected.
    """
    if settings.TWOX_AI_ENABLED and not question.strip():
        raise ValueError("the question must not be empty")
    return _events(
        question,
        device_ids=tuple(device_ids),
        plant_ids=tuple(plant_ids),
        chat=chat,
        seed=seed,
        on_context=on_context,
    )


def _events(
    question: str,
    *,
    device_ids: tuple[int, ...],
    plant_ids: tuple[int, ...],
    chat: ChatModel | None,
    seed: int | None,
    on_context: ContextObserver | None,
) -> Generator[AnswerEvent]:
    outcome = _Outcome(started=monotonic())
    model: ChatModel | None = None
    owned = False
    stream: ChatStream | None = None
    try:
        # 1. AI features off: nothing is selected, fetched or contacted.
        if not settings.TWOX_AI_ENABLED:
            outcome.finish(ErrorCode.AI_DISABLED.value)
            yield ErrorEvent(code=ErrorCode.AI_DISABLED)
            return

        # 3. Context.
        try:
            selection = context.select_context(question, device_ids=device_ids, plant_ids=plant_ids)
        except Exception as error:
            code = context_error_code(error)
            outcome.finish(code.value, exception=error)
            yield ErrorEvent(code=code)
            return
        if on_context is not None:
            on_context(selection.best_distance, selection.below_threshold)

        # 4. and 5. Sources; below the threshold the model is not asked.
        if selection.below_threshold or not selection.sources:
            outcome.cited = 0
            outcome.removed = 0
            outcome.finish(AnswerStatus.NO_EVIDENCE.value)
            yield SourcesEvent(sources=[])
            yield DoneEvent(
                status=AnswerStatus.NO_EVIDENCE,
                cited=[],
                removed_sentences=0,
                final_text=types.NO_EVIDENCE_TEXT,
            )
            return
        sources = selection.sources
        outcome.sources = len(sources)
        yield SourcesEvent(sources=[types.to_source_ref(source) for source in sources])

        # 6. and 7. Model and streamed pieces.
        pieces: list[str] = []
        try:
            if chat is None:
                model = chat_module.get_chat_model()
                owned = True
            else:
                model = chat
            outcome.model = model.model_name
            messages = prompt.build_messages(question, sources, prompt.new_nonce())
            stream = model.stream(messages, seed=seed)
            for piece in stream:
                pieces.append(piece)
                yield DeltaEvent(text=piece)
        except Exception as error:
            code = chat_error_code(error)
            outcome.finish(code.value, exception=error)
            yield ErrorEvent(code=code)
            return
        finally:
            if stream is not None:
                stream.close()

        # 8. Citation check and the final event.
        try:
            verdict = citations.verify(
                "".join(pieces),
                {source.n: source.text for source in sources},
                drop_unsupported=True,
            )
            status = AnswerStatus(verdict.status)
            no_evidence = status is AnswerStatus.NO_EVIDENCE
            done = DoneEvent(
                status=status,
                cited=[] if no_evidence else list(verdict.cited),
                removed_sentences=len(verdict.removed_sentences),
                final_text=types.NO_EVIDENCE_TEXT if no_evidence else verdict.cleaned_text,
            )
        except Exception as error:
            outcome.finish(ErrorCode.INTERNAL.value, exception=error)
            yield ErrorEvent(code=ErrorCode.INTERNAL)
            return
        outcome.cited = len(done.cited)
        outcome.removed = done.removed_sentences
        outcome.finish(done.status.value)
        yield done
    finally:
        # 10. Cancelled or ended: free the stream and a model fetched here.
        if stream is not None:
            stream.close()
        if owned and model is not None:
            model.close()
        outcome.write()
