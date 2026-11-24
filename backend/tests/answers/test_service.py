"""The answer service (work order 126).

The chat model is always :class:`~twox.answers.chat.FakeChatModel`; no test
reaches a real model service or the internet. The context selection is either
the real one over the database with :class:`FakeEmbedder` (end to end) or a
stand-in put in place with ``monkeypatch`` where only the flow matters. All
texts are written for these tests (an invented gripper G-12).
"""

import contextlib
import gc
import json
import logging
import socket
import urllib.error
from collections.abc import Sequence
from dataclasses import dataclass, field
from email.message import Message

import pytest
from django.db import DatabaseError, connection
from django.test.utils import CaptureQueriesContext
from pytest_django.fixtures import Settings

from tests.answers.fake_ollama import CHAT_MODEL, EMBEDDING_ONLY_MODEL, FakeOllama, fake_ollama
from tests.search.fake_embedder import FakeEmbedder, at_angle, embed
from tests.search.test_keyword_search import (
    add_sections,
    add_version,
    make_device,
    make_document,
    make_plant,
)
from twox.answers import chat as chat_module
from twox.answers import citations, context, prompt, service
from twox.answers.chat import (
    ChatDisabledError,
    ChatError,
    ChatMessage,
    ChatRejectedError,
    ChatRemoteModelError,
    ChatStream,
    ChatUnavailableError,
    FakeChatModel,
    OpenAICompatibleChat,
)
from twox.answers.context import ContextSelection
from twox.answers.llm_guard import ModelNotLoadedError
from twox.answers.service import answer
from twox.answers.types import (
    CONTRADICTION_PHRASE,
    NO_EVIDENCE_TEXT,
    AnswerEvent,
    AnswerStatus,
    ContextSource,
    DeltaEvent,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    SourcesEvent,
    to_json,
    to_source_ref,
)
from twox.files.models import Document
from twox.search.interface import HitLocation

QUESTION = "Wie viel hält der Greifer?"
GRIPPER_TEXT = "Der Greifer G-12 hält höchstens 5 kg. Die Versorgung beträgt 24 V."
OTHER_TEXT = "Laut Nachtrag hält der Greifer G-12 höchstens 7 kg."
NONCE = "0123456789abcdef"


# --- Helpers -------------------------------------------------------------------


def location(
    section_id: int, title: str = "Handbuch Greifer", filename: str = "g12.pdf"
) -> HitLocation:
    return HitLocation(
        section_id=section_id,
        document_id=1,
        document_title=title,
        version_id=11,
        version_number=2,
        version_filename=filename,
        is_latest_version=True,
        device_id=7,
        device_key="g-12",
        device_name="Greifer links",
        plant_id=3,
        plant_key="line-a",
        plant_name="Linie A",
    )


def source(
    n: int, text: str, *, title: str = "Handbuch Greifer", filename: str = "g12.pdf"
) -> ContextSource:
    return ContextSource(
        n=n,
        section_id=100 + n,
        version_id=11,
        ordinal=n,
        sha256="ab" * 32,
        page_start=3 + n,
        page_end=3 + n,
        heading_path=["Technische Daten"],
        text=text,
        locations=[location(100 + n, title, filename)],
    )


TWO_SOURCES = [source(1, GRIPPER_TEXT), source(2, OTHER_TEXT)]


@dataclass
class StandInContext:
    """Replaces :func:`twox.answers.context.select_context`; records its calls."""

    selection: ContextSelection | None = None
    error: Exception | None = None
    calls: list[tuple[str, tuple[int, ...], tuple[int, ...]]] = field(default_factory=list)

    def __call__(
        self, question: str, *, device_ids: Sequence[int] = (), plant_ids: Sequence[int] = ()
    ) -> ContextSelection:
        self.calls.append((question, tuple(device_ids), tuple(plant_ids)))
        if self.error is not None:
            raise self.error
        assert self.selection is not None
        return self.selection


def use_context(
    monkeypatch: pytest.MonkeyPatch,
    sources: Sequence[ContextSource] = TWO_SOURCES,
    *,
    below_threshold: bool = False,
    error: Exception | None = None,
) -> StandInContext:
    selection = ContextSelection(
        list(sources), below_threshold=below_threshold, best_distance=0.3, hit_count=len(sources)
    )
    stand_in = StandInContext(selection=selection, error=error)
    monkeypatch.setattr(context, "select_context", stand_in)
    return stand_in


def forbid_chat_model(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """``get_chat_model`` fails loudly; returns the attempts."""
    attempts: list[str] = []

    def refuse() -> chat_module.ChatModel:
        attempts.append("get_chat_model")
        raise AssertionError("the chat model must not be fetched")

    monkeypatch.setattr(chat_module, "get_chat_model", refuse)
    return attempts


def forbid_network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every attempt to resolve or connect fails loudly (as in ``test_check_llm.py``)."""
    attempts: list[str] = []

    def refuse(*args: object, **kwargs: object) -> object:
        attempts.append(repr(args))
        raise AssertionError("the network must not be used")

    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    return attempts


class RecordingChat(FakeChatModel):
    """A :class:`FakeChatModel` that keeps the streams it returned."""

    def __init__(self, pieces: Sequence[str] = ("Antwort.",), **kwargs: object) -> None:
        super().__init__(pieces, **kwargs)  # type: ignore[arg-type]
        self.streams: list[ChatStream] = []

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> ChatStream:
        stream = super().stream(messages, max_tokens=max_tokens, temperature=temperature, seed=seed)
        self.streams.append(stream)
        return stream


def types_of(events: Sequence[AnswerEvent]) -> list[str]:
    return [event.type for event in events]


def done_of(events: Sequence[AnswerEvent]) -> DoneEvent:
    last = events[-1]
    assert isinstance(last, DoneEvent), events
    return last


@pytest.fixture
def ai_on(no_real_model_service: None, settings: Settings) -> None:
    """AI features on, the model service on a closed port."""
    settings.TWOX_AI_ENABLED = True


# --- The flow --------------------------------------------------------------------


@pytest.mark.usefixtures("ai_on")
def test_supported_answer_gives_sources_deltas_and_done(monkeypatch: pytest.MonkeyPatch) -> None:
    stand_in = use_context(monkeypatch)
    pieces = ["Der Greifer ", "G-12 hält ", "höchstens 5 kg [1]."]
    chat = FakeChatModel(pieces)

    events = list(answer(QUESTION, device_ids=[7], plant_ids=[3], chat=chat))

    assert types_of(events) == ["sources", "delta", "delta", "delta", "done"]
    sources_event = events[0]
    assert isinstance(sources_event, SourcesEvent)
    assert sources_event.sources == [to_source_ref(s) for s in TWO_SOURCES]
    assert [e.text for e in events if isinstance(e, DeltaEvent)] == pieces
    done = done_of(events)
    assert done.status is AnswerStatus.ANSWERED
    assert done.cited == [1]
    assert done.removed_sentences == 0
    assert done.final_text == "".join(pieces)
    assert stand_in.calls == [(QUESTION, (7,), (3,))]


@pytest.mark.usefixtures("ai_on")
def test_sources_event_carries_no_section_text(monkeypatch: pytest.MonkeyPatch) -> None:
    long_text = "Der Greifer G-12 hält höchstens 5 kg. " + "Füllsatz ohne Belang. " * 40
    use_context(monkeypatch, [source(1, long_text + "Schlussmarke")])

    events = list(answer(QUESTION, chat=FakeChatModel(["G-12 hält 5 kg [1]."])))

    assert "Schlussmarke" not in json.dumps(to_json(events[0]))


@pytest.mark.usefixtures("ai_on")
def test_invented_number_is_dropped_and_alone_gives_no_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_context(monkeypatch)

    events = list(answer(QUESTION, chat=FakeChatModel(["Der Greifer hält 5 kg [9]."])))

    done = done_of(events)
    assert done.status is AnswerStatus.NO_EVIDENCE
    assert done.cited == []
    assert done.removed_sentences == 1
    assert done.final_text == NO_EVIDENCE_TEXT


@pytest.mark.usefixtures("ai_on")
def test_invented_number_next_to_a_valid_one_is_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)

    events = list(answer(QUESTION, chat=FakeChatModel(["Der Greifer hält 5 kg [1][9]."])))

    done = done_of(events)
    assert done.status is AnswerStatus.ANSWERED
    assert done.cited == [1]
    assert done.removed_sentences == 1
    assert "[9]" not in done.final_text


@pytest.mark.usefixtures("ai_on")
def test_unsupported_sentence_is_dropped_from_the_final_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_context(monkeypatch)
    pieces = ["Der Greifer hält 5 kg [1]. ", "Er wiegt 9 kg [1]."]

    events = list(answer(QUESTION, chat=FakeChatModel(pieces)))

    done = done_of(events)
    assert done.status is AnswerStatus.ANSWERED
    assert done.removed_sentences == 1
    assert done.final_text.strip() == "Der Greifer hält 5 kg [1]."


@pytest.mark.parametrize(
    "pieces",
    [
        ["Dazu finde ich nichts ", "in den Unterlagen."],
        ["Dazu finde ich nichts in den Unterlagen"],
        ["Das weiß ich leider nicht."],
        [],
    ],
)
@pytest.mark.usefixtures("ai_on")
def test_refusal_of_the_model_gives_no_evidence(
    monkeypatch: pytest.MonkeyPatch, pieces: list[str]
) -> None:
    use_context(monkeypatch)

    events = list(answer(QUESTION, chat=FakeChatModel(pieces)))

    assert types_of(events) == ["sources", *["delta"] * len(pieces), "done"]
    done = done_of(events)
    assert done.status is AnswerStatus.NO_EVIDENCE
    assert done.cited == []
    assert done.final_text == NO_EVIDENCE_TEXT


@pytest.mark.usefixtures("ai_on")
def test_contradiction_with_two_valid_citations_is_recognised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The form the system prompt asks for: the phrase, a colon, both places.
    use_context(monkeypatch)
    text = f"{CONTRADICTION_PHRASE}: Der Greifer hält 5 kg [1], laut Nachtrag 7 kg [2]."

    events = list(answer(QUESTION, chat=FakeChatModel([text])))

    done = done_of(events)
    assert done.status is AnswerStatus.CONTRADICTION
    assert done.cited == [1, 2]
    assert done.final_text == text


# --- Below the threshold and AI off ----------------------------------------------


@pytest.mark.usefixtures("ai_on")
def test_below_threshold_the_model_is_not_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch, [], below_threshold=True)
    attempts = forbid_chat_model(monkeypatch)
    network = forbid_network(monkeypatch)
    failing = FakeChatModel(fail_on_call=ChatUnavailableError("must not be called"))

    with_chat = list(answer(QUESTION, chat=failing))
    without_chat = list(answer(QUESTION))

    for events in (with_chat, without_chat):
        assert types_of(events) == ["sources", "done"]
        assert events[0] == SourcesEvent(sources=[])
        assert events[1] == DoneEvent(
            status=AnswerStatus.NO_EVIDENCE,
            cited=[],
            removed_sentences=0,
            final_text=NO_EVIDENCE_TEXT,
        )
    assert failing.calls == []
    assert attempts == []
    assert network == []


@pytest.mark.usefixtures("ai_on")
def test_without_any_source_the_model_is_not_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch, [], below_threshold=False)
    forbid_chat_model(monkeypatch)

    events = list(answer(QUESTION))

    assert types_of(events) == ["sources", "done"]
    assert done_of(events).status is AnswerStatus.NO_EVIDENCE


def test_ai_off_gives_only_ai_disabled(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, no_real_model_service: None
) -> None:
    settings.TWOX_AI_ENABLED = False
    stand_in = use_context(monkeypatch)
    attempts = forbid_chat_model(monkeypatch)
    network = forbid_network(monkeypatch)
    chat = FakeChatModel()

    events = list(answer(QUESTION, chat=chat))
    empty = list(answer("   "))

    assert events == [ErrorEvent(code=ErrorCode.AI_DISABLED)]
    assert empty == [ErrorEvent(code=ErrorCode.AI_DISABLED)]
    assert stand_in.calls == []
    assert chat.calls == []
    assert chat.close_count == 0
    assert attempts == []
    assert network == []


@pytest.mark.parametrize("question", ["", "   ", "\n\t"])
@pytest.mark.usefixtures("ai_on")
def test_empty_question_raises_before_any_event(
    monkeypatch: pytest.MonkeyPatch, question: str
) -> None:
    stand_in = use_context(monkeypatch)

    with pytest.raises(ValueError, match="empty"):
        answer(question, chat=FakeChatModel())

    assert stand_in.calls == []


# --- Errors ----------------------------------------------------------------------

SECRET = "geheimnis-im-fehlertext http://10.9.8.7:11434"


def with_cause(error: ChatError, cause: BaseException) -> ChatError:
    error.__cause__ = cause
    return error


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://10.9.8.7:11434/v1", code, SECRET, Message(), None)


CHAT_ERRORS: list[tuple[BaseException, ErrorCode]] = [
    (ChatDisabledError(SECRET), ErrorCode.AI_DISABLED),
    (ChatUnavailableError(SECRET), ErrorCode.MODEL_UNAVAILABLE),
    # A model refused on purpose (no capability completion: raised without a cause).
    (ChatRejectedError(SECRET), ErrorCode.MODEL_REJECTED),
    (ChatRemoteModelError(SECRET), ErrorCode.MODEL_REJECTED),
    (with_cause(ChatRejectedError(SECRET), http_error(400)), ErrorCode.MODEL_REJECTED),
    # A missing model: not in /api/tags, or HTTP 404 from /chat/completions.
    (
        with_cause(ChatRejectedError(SECRET), ModelNotLoadedError(SECRET)),
        ErrorCode.MODEL_UNAVAILABLE,
    ),
    (with_cause(ChatRejectedError(SECRET), http_error(404)), ErrorCode.MODEL_UNAVAILABLE),
    (with_cause(ChatUnavailableError(SECRET), TimeoutError(SECRET)), ErrorCode.TIMEOUT),
    (
        with_cause(ChatUnavailableError(SECRET), urllib.error.URLError(TimeoutError(SECRET))),
        ErrorCode.TIMEOUT,
    ),
    (
        with_cause(ChatUnavailableError(SECRET), ConnectionError(SECRET)),
        ErrorCode.MODEL_UNAVAILABLE,
    ),
    (ChatError(SECRET), ErrorCode.MODEL_UNAVAILABLE),
    (RuntimeError(SECRET), ErrorCode.INTERNAL),
]


@pytest.mark.parametrize(("error", "code"), CHAT_ERRORS)
def test_chat_errors_map_to_fixed_codes(error: BaseException, code: ErrorCode) -> None:
    assert service.chat_error_code(error) is code


@pytest.mark.parametrize(
    ("model", "models", "chat_status", "code"),
    [
        # Not in /api/tags: missing, not refused.
        ("other-chat", [CHAT_MODEL], 200, ErrorCode.MODEL_UNAVAILABLE),
        # HTTP 404 from /chat/completions: missing as well.
        ("local-chat", [CHAT_MODEL], 404, ErrorCode.MODEL_UNAVAILABLE),
        # Refused on purpose: another HTTP 4xx, no capability completion, a cloud model.
        ("local-chat", [CHAT_MODEL], 400, ErrorCode.MODEL_REJECTED),
        ("bge-m3", [EMBEDDING_ONLY_MODEL], 200, ErrorCode.MODEL_REJECTED),
        (
            "big",
            [{"name": "big:latest", "model": "big:latest", "remote_host": "x"}],
            200,
            ErrorCode.MODEL_REJECTED,
        ),
    ],
)
@pytest.mark.usefixtures("ai_on")
def test_errors_of_the_real_chat_client_map_to_their_codes(
    monkeypatch: pytest.MonkeyPatch,
    model: str,
    models: list[dict[str, object]],
    chat_status: int,
    code: ErrorCode,
) -> None:
    use_context(monkeypatch)
    with fake_ollama(FakeOllama(models=[dict(entry) for entry in models])) as (base_url, fake):
        fake.chat_status = chat_status
        client = OpenAICompatibleChat(
            base_url=base_url,
            model=model,
            timeout=5.0,
            max_tokens=64,
            temperature=0.0,
            reasoning_effort="none",
        )
        events = list(answer(QUESTION, chat=client))

    assert types_of(events) == ["sources", "error"]
    assert events[-1] == ErrorEvent(code=code)


@pytest.mark.parametrize(("error", "code"), CHAT_ERRORS)
@pytest.mark.usefixtures("ai_on")
def test_model_failure_in_the_middle_gives_error_without_done(
    monkeypatch: pytest.MonkeyPatch, error: Exception, code: ErrorCode
) -> None:
    use_context(monkeypatch)
    chat = RecordingChat(
        ["Der Greifer ", "hält ", "5 kg [1]."],
        error=error,
        error_after=2,
    )

    events = list(answer(QUESTION, chat=chat))

    assert types_of(events) == ["sources", "delta", "delta", "error"]
    assert events[-1] == ErrorEvent(code=code)
    assert SECRET not in json.dumps([to_json(event) for event in events])
    assert chat.streams[0].closed
    assert chat.close_count == 0


@pytest.mark.parametrize(("error", "code"), CHAT_ERRORS)
@pytest.mark.usefixtures("ai_on")
def test_failing_call_of_the_model_gives_error(
    monkeypatch: pytest.MonkeyPatch, error: Exception, code: ErrorCode
) -> None:
    use_context(monkeypatch)
    chat = FakeChatModel(fail_on_call=error)  # type: ignore[arg-type]

    events = list(answer(QUESTION, chat=chat))

    assert types_of(events) == ["sources", "error"]
    assert events[-1] == ErrorEvent(code=code)


@pytest.mark.parametrize(("error", "code"), CHAT_ERRORS)
@pytest.mark.usefixtures("ai_on")
def test_failing_get_chat_model_gives_error(
    monkeypatch: pytest.MonkeyPatch, error: Exception, code: ErrorCode
) -> None:
    use_context(monkeypatch)

    def fail() -> chat_module.ChatModel:
        raise error

    monkeypatch.setattr(chat_module, "get_chat_model", fail)

    events = list(answer(QUESTION))

    assert types_of(events) == ["sources", "error"]
    assert events[-1] == ErrorEvent(code=code)


@pytest.mark.usefixtures("ai_on")
def test_empty_chat_model_setting_gives_model_unavailable(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    settings.TWOX_CHAT_MODEL = ""
    use_context(monkeypatch)
    network = forbid_network(monkeypatch)

    events = list(answer(QUESTION))

    assert events[-1] == ErrorEvent(code=ErrorCode.MODEL_UNAVAILABLE)
    assert network == []


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (context.ContextDisabledError(SECRET), ErrorCode.AI_DISABLED),
        (context.ContextUnavailableError(SECRET), ErrorCode.MODEL_UNAVAILABLE),
        (DatabaseError(SECRET), ErrorCode.SEARCH_FAILED),
        (RuntimeError(SECRET), ErrorCode.SEARCH_FAILED),
    ],
)
@pytest.mark.usefixtures("ai_on")
def test_context_failure_gives_error_without_sources(
    monkeypatch: pytest.MonkeyPatch, error: Exception, code: ErrorCode
) -> None:
    use_context(monkeypatch, error=error)
    attempts = forbid_chat_model(monkeypatch)

    events = list(answer(QUESTION))

    assert events == [ErrorEvent(code=code)]
    assert attempts == []
    assert service.context_error_code(error) is code


@pytest.mark.usefixtures("ai_on")
def test_failing_citation_check_gives_internal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)

    def broken(*args: object, **kwargs: object) -> object:
        raise KeyError(SECRET)

    monkeypatch.setattr(citations, "verify", broken)

    events = list(answer(QUESTION, chat=FakeChatModel(["G-12 hält 5 kg [1]."])))

    assert types_of(events) == ["sources", "delta", "error"]
    assert events[-1] == ErrorEvent(code=ErrorCode.INTERNAL)


# --- Cancelling and closing ------------------------------------------------------


@pytest.mark.usefixtures("ai_on")
def test_closing_after_the_first_delta_closes_the_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)
    chat = RecordingChat(["Der Greifer ", "hält ", "5 kg [1]."])

    events = answer(QUESTION, chat=chat)
    assert isinstance(next(events), SourcesEvent)
    assert next(events) == DeltaEvent(text="Der Greifer ")
    assert not chat.streams[0].closed
    # close() itself frees the stream, not the garbage collector.
    gc.disable()
    try:
        events.close()
        assert chat.streams[0].closed
    finally:
        gc.enable()

    assert chat.close_count == 0  # a model passed in is not closed, only its stream
    assert list(events) == []


@pytest.mark.usefixtures("ai_on")
def test_closing_after_the_sources_opens_no_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)
    passed_in = RecordingChat(["G-12 hält 5 kg [1]."])
    attempts = forbid_chat_model(monkeypatch)

    for events in (answer(QUESTION, chat=passed_in), answer(QUESTION)):
        assert isinstance(next(events), SourcesEvent)
        gc.disable()
        try:
            events.close()
        finally:
            gc.enable()
        assert list(events) == []

    # The stream is opened only after the sources event; closing there asks no model.
    assert passed_in.calls == []
    assert passed_in.streams == []
    assert attempts == []


@pytest.mark.usefixtures("ai_on")
def test_contextlib_closing_closes_the_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)
    chat = RecordingChat(["Der Greifer ", "hält ", "5 kg [1]."])

    with contextlib.closing(answer(QUESTION, chat=chat)) as events:
        for event in events:
            if isinstance(event, DeltaEvent):
                break
        assert not chat.streams[0].closed

    assert chat.streams[0].closed


@pytest.mark.usefixtures("ai_on")
def test_a_model_fetched_by_the_service_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)
    cancelled = RecordingChat(["Der Greifer ", "hält ", "5 kg [1]."])
    finished = RecordingChat(["G-12 hält 5 kg [1]."])
    models = iter([cancelled, finished])
    monkeypatch.setattr(chat_module, "get_chat_model", lambda: next(models))

    events = answer(QUESTION)
    next(events)
    next(events)
    events.close()
    complete = list(answer(QUESTION))

    assert cancelled.streams[0].closed
    assert cancelled.close_count == 1
    assert done_of(complete).status is AnswerStatus.ANSWERED
    assert finished.streams[0].closed
    assert finished.close_count == 1


@pytest.mark.usefixtures("ai_on")
def test_streams_are_closed_after_a_normal_end(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)
    chat = RecordingChat(["G-12 hält 5 kg [1]."])

    list(answer(QUESTION, chat=chat))

    assert chat.streams[0].closed
    assert chat.close_count == 0


# --- Seed and import form ----------------------------------------------------------


@pytest.mark.usefixtures("ai_on")
def test_seed_is_passed_on_and_settings_decide_the_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)
    chat = FakeChatModel(["G-12 hält 5 kg [1]."])

    list(answer(QUESTION, chat=chat, seed=7))
    list(answer(QUESTION, chat=chat))

    assert [call.seed for call in chat.calls] == [7, None]
    assert all(call.max_tokens is None and call.temperature is None for call in chat.calls)


@pytest.mark.usefixtures("ai_on")
def test_a_patched_nonce_reaches_build_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)
    seen: list[tuple[str, list[int], str]] = []
    original = prompt.build_messages

    def spy(question: str, sources: Sequence[ContextSource], nonce: str) -> list[ChatMessage]:
        seen.append((question, [s.n for s in sources], nonce))
        return original(question, sources, nonce)

    monkeypatch.setattr(prompt, "new_nonce", lambda: NONCE)
    monkeypatch.setattr(prompt, "build_messages", spy)
    chat = FakeChatModel(["G-12 hält 5 kg [1]."])

    list(answer(QUESTION, chat=chat))

    assert seen == [(QUESTION, [1, 2], NONCE)]
    assert chat.last_messages == original(QUESTION, TWO_SOURCES, NONCE)


@pytest.mark.usefixtures("ai_on")
def test_each_request_gets_a_fresh_nonce(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch)
    nonces: list[str] = []
    original = prompt.new_nonce

    def counting() -> str:
        nonces.append(original())
        return nonces[-1]

    monkeypatch.setattr(prompt, "new_nonce", counting)
    chat = FakeChatModel(["G-12 hält 5 kg [1]."])

    list(answer(QUESTION, chat=chat))
    list(answer(QUESTION, chat=chat))

    assert len(nonces) == 2
    assert nonces[0] != nonces[1]
    assert nonces[0] in chat.calls[0].messages[1]["content"]


# --- End to end over the database ----------------------------------------------------


@dataclass
class Factory:
    """Two devices with one section each, embedded close to the question."""

    device_a: int
    device_b: int


@pytest.fixture
def factory(fake_embedder: FakeEmbedder) -> Factory:
    plant = make_plant()
    device_a = make_device(plant, "gripper-a")
    device_b = make_device(plant, "gripper-b")
    (section_a,) = add_sections(
        make_document(device_a, title="Handbuch Greifer A"), GRIPPER_TEXT, page=4
    )
    (section_b,) = add_sections(
        make_document(device_b, title="Handbuch Greifer B"), OTHER_TEXT, page=9
    )
    embed(section_a, at_angle(10, axis=1))
    embed(section_b, at_angle(20, axis=2))
    return Factory(device_a=device_a.pk, device_b=device_b.pk)


@pytest.mark.usefixtures("every_text_a_source")  # short texts, work order 153
@pytest.mark.django_db
def test_end_to_end_over_the_real_context_selection(factory: Factory) -> None:
    chat = FakeChatModel(["Der Greifer G-12 ", "hält höchstens 5 kg [1]."])

    with CaptureQueriesContext(connection) as queries:
        events = list(answer(QUESTION, chat=chat))

    assert types_of(events) == ["sources", "delta", "delta", "done"]
    sources_event = events[0]
    assert isinstance(sources_event, SourcesEvent)
    assert [s.n for s in sources_event.sources] == [1, 2]
    assert sources_event.sources[0].locations[0].device_id == factory.device_a
    assert done_of(events).status is AnswerStatus.ANSWERED
    assert done_of(events).cited == [1]
    # The prompt holds both section texts, between the delimiters of build_messages.
    user = chat.last_messages[1]["content"]
    assert GRIPPER_TEXT in user
    assert OTHER_TEXT in user
    # The service writes nothing (D7): reading only.
    statements = [query["sql"].lstrip().split(None, 1)[0].upper() for query in queries]
    assert statements
    assert not {"INSERT", "UPDATE", "DELETE"} & set(statements)


@pytest.mark.usefixtures("every_text_a_source")  # short texts, work order 153
@pytest.mark.django_db
def test_end_to_end_device_scope(factory: Factory) -> None:
    chat = FakeChatModel(["Laut Nachtrag hält der Greifer G-12 höchstens 7 kg [1]."])

    events = list(answer(QUESTION, device_ids=[factory.device_b], chat=chat))

    sources_event = events[0]
    assert isinstance(sources_event, SourcesEvent)
    assert [s.locations[0].device_id for s in sources_event.sources] == [factory.device_b]
    assert done_of(events).status is AnswerStatus.ANSWERED


@pytest.mark.django_db
def test_end_to_end_below_the_threshold(
    fake_embedder: FakeEmbedder, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = make_device(make_plant(), "gripper-far")
    (section,) = add_sections(make_document(device), GRIPPER_TEXT)
    embed(section, at_angle(80, axis=1))  # distance 0.83, above the threshold of 0.60
    attempts = forbid_chat_model(monkeypatch)
    network = forbid_network(monkeypatch)
    failing = FakeChatModel(fail_on_call=ChatUnavailableError("must not be called"))

    events = list(answer("Wie wechsle ich die Batterie?", chat=failing))

    assert types_of(events) == ["sources", "done"]
    assert events[0] == SourcesEvent(sources=[])
    assert done_of(events).final_text == NO_EVIDENCE_TEXT
    assert failing.calls == []
    assert attempts == []
    assert network == []


# --- Logging ---------------------------------------------------------------------------

MARKERS = {
    "question": "Quokkafrage zum Greifer G-12?",
    "piece": "Wombatstueck",
    "section": "Numbatabschnitt",
    "title": "Bilbytitel",
    "filename": "dingotext.pdf",
}


@pytest.fixture
def marked(fake_embedder: FakeEmbedder) -> None:
    device = make_device(make_plant(), "gripper-log")
    document = Document.objects.create(device=device, title=MARKERS["title"])
    version = add_version(document, filename=MARKERS["filename"])
    (section,) = add_sections(version, f"{MARKERS['section']}: Der Greifer G-12 hält 5 kg.")
    embed(section, at_angle(10, axis=1))


def service_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == "twox.answers.service"]


@pytest.mark.parametrize(
    ("chat", "close_early", "result"),
    [
        (FakeChatModel([f"{MARKERS['piece']} G-12 hält 5 kg [1]."]), False, "answered"),
        (FakeChatModel([f"{MARKERS['piece']} weiß ich nicht."]), False, "no_evidence"),
        (
            FakeChatModel(
                [f"{MARKERS['piece']} ", "mehr"],
                error=ChatUnavailableError(MARKERS["piece"]),
                error_after=1,
            ),
            False,
            "model_unavailable",
        ),
        (
            FakeChatModel(
                [f"{MARKERS['piece']} ", "G-12 hält 5 kg [1]."],
                error=RuntimeError(MARKERS["piece"]),  # type: ignore[arg-type]
                error_after=1,
            ),
            False,
            "internal",
        ),
        (FakeChatModel([f"{MARKERS['piece']} ", "G-12 hält 5 kg [1]."]), True, "cancelled"),
    ],
)
@pytest.mark.django_db
def test_logs_hold_no_question_text_title_or_filename(
    marked: None,
    caplog: pytest.LogCaptureFixture,
    chat: FakeChatModel,
    close_early: bool,
    result: str,
) -> None:
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="twox")

    events = answer(MARKERS["question"], chat=chat)
    if close_early:
        next(events)
        next(events)
        events.close()
    else:
        list(events)

    (line,) = service_lines(caplog)
    assert f"result={result}" in line
    assert "model=fake-chat" in line
    assert "duration_ms=" in line
    assert "sources=1" in line
    for marker in MARKERS.values():
        assert marker not in caplog.text
        assert all(marker not in record.getMessage() for record in caplog.records)
    if result == "internal":
        assert "exception=RuntimeError" in line


@pytest.mark.usefixtures("ai_on")
def test_log_line_of_done_counts_citations_and_removed_sentences(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="twox")
    use_context(monkeypatch)

    list(answer(QUESTION, chat=FakeChatModel(["G-12 hält 5 kg [1][9]. Er wiegt 9 kg [2]."])))

    (line,) = service_lines(caplog)
    assert "result=answered" in line
    assert "sources=2" in line
    assert "cited=1" in line
    assert "removed_sentences=2" in line


def test_log_line_with_ai_off(
    settings: Settings, no_real_model_service: None, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="twox")
    settings.TWOX_AI_ENABLED = False

    list(answer(QUESTION))

    (line,) = service_lines(caplog)
    assert "result=ai_disabled" in line
    assert "model=-" in line
    assert "sources=0" in line
