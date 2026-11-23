"""The back channel ``on_context`` of the answer service (work order 142).

The callback gets ``best_distance`` and ``below_threshold`` of the context
selection, once per request, and nothing else. The context selection is a
stand-in; the chat model is a fake. All texts are written for these tests.
"""

import pytest
from pytest_django.fixtures import Settings

from tests.answers.test_service import (
    QUESTION,
    TWO_SOURCES,
    StandInContext,
    forbid_chat_model,
    types_of,
    use_context,
)
from twox.answers import context, service
from twox.answers.chat import ChatUnavailableError, FakeChatModel
from twox.answers.context import ContextSelection
from twox.answers.types import AnswerEvent, AnswerStatus, ErrorCode, ErrorEvent


@pytest.fixture
def ai_on(no_real_model_service: None, settings: Settings) -> None:
    """AI features on, the model service on a closed port."""
    settings.TWOX_AI_ENABLED = True


class Observer:
    """Records the calls of ``on_context``, and the events seen so far at each call."""

    def __init__(self) -> None:
        self.calls: list[tuple[float | None, bool]] = []

    def __call__(self, best_distance: float | None, below_threshold: bool) -> None:
        self.calls.append((best_distance, below_threshold))


def select(
    monkeypatch: pytest.MonkeyPatch,
    *,
    best_distance: float | None,
    below_threshold: bool,
    open_gate: bool = True,
) -> StandInContext:
    sources = list(TWO_SOURCES) if open_gate else []
    selection = ContextSelection(
        sources,
        below_threshold=below_threshold,
        best_distance=best_distance,
        hit_count=len(sources),
    )
    stand_in = StandInContext(selection=selection)
    monkeypatch.setattr(context, "select_context", stand_in)
    return stand_in


@pytest.mark.usefixtures("ai_on")
def test_open_gate_reports_the_two_values_once_before_the_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    select(monkeypatch, best_distance=0.2345, below_threshold=False)
    observer = Observer()
    seen_at_call: list[int] = []

    def observe(best_distance: float | None, below_threshold: bool) -> None:
        seen_at_call.append(len(events))
        observer(best_distance, below_threshold)

    chat = FakeChatModel(["Der Greifer G-12 hält höchstens 5 kg [1]."])
    events: list[AnswerEvent] = []
    for event in service.answer(QUESTION, chat=chat, on_context=observe):
        events.append(event)

    assert observer.calls == [(0.2345, False)]
    assert seen_at_call == [0]  # before the first event, so before ``sources``
    assert types_of(events)[0] == "sources"
    assert len(chat.calls) == 1  # the model was asked


@pytest.mark.usefixtures("ai_on")
def test_below_threshold_reports_the_values_and_does_not_ask_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    select(monkeypatch, best_distance=0.91, below_threshold=True, open_gate=False)
    attempts = forbid_chat_model(monkeypatch)
    failing = FakeChatModel(fail_on_call=ChatUnavailableError("must not be called"))
    observer = Observer()

    events = list(service.answer(QUESTION, chat=failing, on_context=observer))

    assert observer.calls == [(0.91, True)]
    assert types_of(events) == ["sources", "done"]
    assert failing.calls == []
    assert attempts == []


@pytest.mark.usefixtures("ai_on")
def test_no_distance_is_passed_on_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    select(monkeypatch, best_distance=None, below_threshold=True, open_gate=False)
    observer = Observer()

    list(service.answer(QUESTION, on_context=observer))

    assert observer.calls == [(None, True)]


@pytest.mark.usefixtures("ai_on")
def test_observer_gets_only_two_plain_values(monkeypatch: pytest.MonkeyPatch) -> None:
    select(monkeypatch, best_distance=0.3, below_threshold=False)
    received: list[tuple[object, ...]] = []

    def observe(*args: object, **kwargs: object) -> None:
        assert kwargs == {}
        received.append(args)

    list(service.answer(QUESTION, chat=FakeChatModel(["Nein."]), on_context=observe))

    assert len(received) == 1
    assert [type(value) for value in received[0]] == [float, bool]


def test_ai_off_does_not_call_the_observer(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, no_real_model_service: None
) -> None:
    settings.TWOX_AI_ENABLED = False
    stand_in = use_context(monkeypatch)
    observer = Observer()

    events = list(service.answer(QUESTION, on_context=observer))

    assert events == [ErrorEvent(code=ErrorCode.AI_DISABLED)]
    assert observer.calls == []
    assert stand_in.calls == []


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (RuntimeError("database down"), ErrorCode.SEARCH_FAILED),
        (context.ContextUnavailableError("no embedding"), ErrorCode.MODEL_UNAVAILABLE),
    ],
)
@pytest.mark.usefixtures("ai_on")
def test_failing_selection_does_not_call_the_observer(
    monkeypatch: pytest.MonkeyPatch, error: Exception, code: ErrorCode
) -> None:
    use_context(monkeypatch, error=error)
    observer = Observer()

    events = list(service.answer(QUESTION, on_context=observer))

    assert events == [ErrorEvent(code=code)]
    assert observer.calls == []


@pytest.mark.usefixtures("ai_on")
def test_a_raising_observer_leaves_the_generator_with_its_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The service catches nothing and makes no event of it (no ``except`` around the flow)."""
    select(monkeypatch, best_distance=0.2, below_threshold=False)
    chat = FakeChatModel(["Antwort."])

    def broken(best_distance: float | None, below_threshold: bool) -> None:
        raise KeyError("measuring aid failed")

    events: list[AnswerEvent] = []
    generator = service.answer(QUESTION, chat=chat, on_context=broken)
    with pytest.raises(KeyError, match="measuring aid failed"):
        for event in generator:
            events.append(event)

    assert events == []  # not even ``sources``
    assert chat.calls == []  # the model was not asked


@pytest.mark.usefixtures("ai_on")
def test_without_observer_the_events_are_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    select(monkeypatch, best_distance=0.2, below_threshold=False)
    pieces = ["Der Greifer G-12 hält ", "höchstens 5 kg [1]."]

    plain = list(service.answer(QUESTION, chat=FakeChatModel(pieces)))
    observed = list(service.answer(QUESTION, chat=FakeChatModel(pieces), on_context=Observer()))

    assert plain == observed
    last = plain[-1]
    assert getattr(last, "status", None) is AnswerStatus.ANSWERED
