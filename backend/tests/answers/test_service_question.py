"""The answer service passes the question to the citation check (140, E-70).

The chat model is :class:`~twox.answers.chat.FakeChatModel` and the context
selection a stand-in; no test reaches a model service or the internet. All
texts are written for these tests (an invented gripper G-12).
"""

from collections.abc import Mapping

import pytest
from pytest_django.fixtures import Settings

from tests.answers.test_service import source, use_context
from twox.answers import citations
from twox.answers.chat import FakeChatModel
from twox.answers.service import answer
from twox.answers.types import AnswerStatus, DoneEvent

QUESTION = "Welche Nutzlast hat der Greifer G-12?"
# The section names the payload, not the designation from the question.
SECTION = "Die Nutzlast beträgt 5 kg."


@pytest.fixture
def ai_on(no_real_model_service: None, settings: Settings) -> None:
    """AI features on, the model service on a closed port."""
    settings.TWOX_AI_ENABLED = True


@pytest.mark.usefixtures("ai_on")
def test_answer_passes_the_question_to_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    use_context(monkeypatch, [source(1, SECTION)])
    calls: list[str | None] = []
    real_verify = citations.verify

    def recording(
        answer_text: str,
        sources: Mapping[int, str],
        *,
        drop_unsupported: bool,
        question: str | None = None,
    ) -> citations.Verdict:
        calls.append(question)
        return real_verify(
            answer_text, sources, drop_unsupported=drop_unsupported, question=question
        )

    monkeypatch.setattr(citations, "verify", recording)

    list(answer(QUESTION, chat=FakeChatModel(["Der G-12 hat 5 kg [1]."])))

    assert calls == [QUESTION]


@pytest.mark.usefixtures("ai_on")
def test_designation_from_the_question_is_supported_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_context(monkeypatch, [source(1, SECTION)])
    reply = "Der G-12 hat eine Nutzlast von 5 kg [1]."

    chat = FakeChatModel(["Der G-12 hat ", "eine Nutzlast von 5 kg [1]."])

    events = list(answer(QUESTION, chat=chat))

    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert done.status is AnswerStatus.ANSWERED
    assert done.cited == [1]
    assert done.removed_sentences == 0
    assert done.final_text == reply


@pytest.mark.usefixtures("ai_on")
def test_designation_alone_from_the_question_stays_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_context(monkeypatch, [source(1, SECTION)])

    events = list(answer(QUESTION, chat=FakeChatModel(["Der G-12 ist ein Greifer [1]."])))

    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert done.status is AnswerStatus.NO_EVIDENCE
    assert done.cited == []
    assert done.removed_sentences == 1
