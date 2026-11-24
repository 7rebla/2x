"""The answer evaluation (work order 127).

The verdicts are tested with hand-made event sequences: invented checksums,
manifest ids and texts written for these tests (an invented gripper G-12),
no vendor text. The run and the command use the real answer service with
:class:`~twox.answers.chat.FakeChatModel` over a small database, with
:class:`FakeEmbedder`; no test reaches a model service. Only the tests of
``asked_text`` and of the statement groups read the real ``questions.yaml``
(mounted read-only into ``backend-dev``) and ``m3.json``, for identifiers
and pages only.
"""

import io
import itertools
import json
import logging
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pytest_django.fixtures import Settings

from tests.search.fake_embedder import FakeEmbedder, at_angle, embed, unit
from tests.search.test_keyword_search import add_sections, make_device, make_document, make_plant
from twox.answers import chat as chat_module
from twox.answers import service
from twox.answers.chat import FakeChatModel
from twox.answers.citations import value_occurs
from twox.answers.evaluation import (
    NOT_MEASURED_NOTE,
    Mode,
    Observed,
    PlaceLabel,
    Question,
    QuestionFormatError,
    QuestionKind,
    QuestionPlaces,
    QuestionResult,
    Report,
    Rule,
    RunResult,
    Verdict,
    Wording,
    aggregate,
    asked_text,
    contradiction_groups,
    evaluate,
    format_json,
    format_table,
    judge_run,
    load_questions,
    missing_key_facts,
    observe,
    question_places,
    summarise,
)
from twox.answers.types import (
    NO_EVIDENCE_TEXT,
    AnswerEvent,
    AnswerStatus,
    ContextSource,
    DeltaEvent,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    SourceRef,
    SourcesEvent,
    to_source_ref,
)
from twox.search.evaluation import ProbeFormatError, probe_list_text
from twox.search.interface import HitLocation

QUESTIONS_FILE = Path("/testfactory/questions.yaml")
#: Typographic quotes (U+201E, U+201C), a no-break space and a byte order mark.
OPEN_QUOTE, CLOSE_QUOTE, NBSP, BOM = map(chr, (0x201E, 0x201C, 0x00A0, 0xFEFF))

SHA_DE = "1a" * 32
SHA_EN = "2b" * 32
SHA_MD = "3c" * 32
SHA_OTHER = "4d" * 32

PROBES: dict[str, Any] = {
    "schema_version": 1,
    "probes": [
        {
            "id": "question-1",
            "query": "Wie schwer darf die Last am Greifer sein?",
            "basis": {"question": 1, "other_language_edition": {"gripper-en": "gripper-de"}},
            "expected": [
                {"manifest_id": "gripper-de", "sha256": SHA_DE, "pages": [4]},
                {"manifest_id": "gripper-en", "sha256": SHA_EN, "pages": [4]},
            ],
        },
        {
            "id": "question-2",
            "query": "Welche Baugröße hat der Greifer?",
            "basis": {"question": 2, "other_language_edition": {"gripper-en": "gripper-de"}},
            "expected": [
                {"manifest_id": "gripper-de", "sha256": SHA_DE, "pages": [3, 5, 7]},
                {"manifest_id": "gripper-en", "sha256": SHA_EN, "pages": [3, 5, 7]},
            ],
        },
        {
            "id": "question-4",
            "query": "Über welchen Port spricht der Greifer?",
            "basis": {"question": 4},
            "expected": [
                {
                    "manifest_id": "gripper-repo",
                    "sha256": SHA_MD,
                    "path": "docs/gripper.md",
                    "heading_path": ["Greifer", "Netz"],
                }
            ],
        },
        {
            "id": "control-9",
            "query": "Wann wurde der Greifer zuletzt geschmiert?",
            "basis": {"question": 9},
            "expected": [],
        },
    ],
}


def statement(manifest_id: str, locator: str, supports: str) -> dict[str, str]:
    return {"manifest_id": manifest_id, "locator": locator, "supports": supports}


QUESTIONS: dict[str, Any] = {
    "schema_version": 1,
    "questions": [
        {
            "id": 1,
            "question": "Wie viel hält der Greifer G-12?",
            "kind": "fact",
            "key_facts": ["5 kg"],
            "key_fact_alternatives": {"5 kg": ["fünf Kilogramm"]},
            "sources": [statement("gripper-de", "PDF-S. 4 (gedr. S. 3)", "Load of the gripper.")],
        },
        {
            "id": 2,
            "question": "Welche Baugröße hat der Greifer? (Die Unterlagen widersprechen sich.)",
            "kind": "contradiction",
            "key_facts": ["G-12", "G-14"],
            "sources": [
                statement("gripper-de", "PDF-S. 3", "Statement A: size G-12."),
                statement("gripper-de", "PDF-S. 5", "Statement B: size G-14."),
                statement("gripper-de", "PDF-S. 7, Tabelle", "Statement B: size G-14 again."),
                statement("gripper-repo", "Verzeichnis g14/", "Statement B: folder name."),
            ],
        },
        {
            "id": 3,
            "question": "Welche Farbe hat der Greifer?",
            "kind": "fact",
            "key_facts": ["blau"],
            "sources": [],
        },
        {
            "id": 4,
            "question": "Über welchen Port spricht der Greifer?",
            "kind": "fact",
            "key_facts": ["502"],
            "sources": [statement("gripper-repo", "docs/gripper.md, Zeile 3", "Port.")],
        },
        {
            "id": 9,
            "question": "Kontrollfrage ohne Beleg: Wann wurde der Greifer zuletzt geschmiert?"
            f" Erwartet wird {OPEN_QUOTE}Dazu finde ich nichts in den Unterlagen{CLOSE_QUOTE}.",
            "kind": "no-evidence",
            "key_facts": ["Dazu finde ich nichts in den Unterlagen"],
            "sources": [],
        },
    ],
    "candidates": [{"id": "c1", "question": "Nicht gezählt", "kind": "unknown"}],
}


def questions() -> dict[int, Question]:
    return {question.id: question for question in load_questions(json.dumps(QUESTIONS))}


def places() -> dict[int, QuestionPlaces]:
    return question_places(json.dumps(PROBES))


def location(section_id: int, device_key: str = "g-12") -> HitLocation:
    return HitLocation(
        section_id=section_id,
        document_id=1,
        document_title="Handbuch Greifer",
        version_id=11,
        version_number=1,
        version_filename="g12.pdf",
        is_latest_version=True,
        device_id=7,
        device_key=device_key,
        device_name="Greifer",
        plant_id=3,
        plant_key="line-a",
        plant_name="Linie A",
    )


def ref(
    n: int,
    sha256: str = SHA_DE,
    page: int | None = 4,
    *,
    headings: Sequence[str] = ("Technische Daten",),
    devices: Sequence[str] = ("g-12",),
    snippet: str = "Ein kurzer Ausschnitt.",
) -> SourceRef:
    return SourceRef(
        n=n,
        section_id=100 + n,
        version_id=11,
        sha256=sha256,
        page_start=page,
        page_end=page,
        heading_path=list(headings),
        locations=[location(100 + n, device) for device in devices],
        snippet=snippet,
    )


def seen(
    sources: Sequence[SourceRef],
    status: AnswerStatus = AnswerStatus.ANSWERED,
    cited: Sequence[int] = (1,),
    text: str = "Der Greifer G-12 hält 5 kg [1].",
) -> Observed:
    return Observed(
        sources=tuple(sources),
        done=DoneEvent(status=status, cited=list(cited), removed_sentences=0, final_text=text),
        total_seconds=1.0,
    )


def judged(question_id: int, observed: Observed, *, literal: bool = False) -> RunResult:
    return judge_run(questions()[question_id], places().get(question_id), observed, literal=literal)


# --- Reading -------------------------------------------------------------------------


def test_questions_are_read_and_candidates_ignored() -> None:
    read = questions()
    assert sorted(read) == [1, 2, 3, 4, 9]
    assert read[1].alternatives == (("5 kg", ("fünf Kilogramm",)),)
    assert read[9].is_control
    assert read[2].kind is QuestionKind.CONTRADICTION


def broken(path: str, value: object) -> str:
    data = json.loads(json.dumps(QUESTIONS))
    target = data
    *parents, last = path.split(".")
    for part in parents:
        target = target[int(part)] if isinstance(target, list) else target[part]
    if value is KeyError:
        del target[last]
    elif isinstance(target, list):
        target[int(last)] = value
    else:
        target[last] = value
    return json.dumps(data)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        ("schema_version", 2, "schema_version"),
        ("questions", [], "questions: expected a non-empty list"),
        ("questions.0.kind", "opinion", "questions[0].kind: expected one of"),
        ("questions.0.kind", KeyError, "questions[0].kind"),
        ("questions.0.id", "1", "questions[0].id"),
        ("questions.0.id", 2, "the id 2 occurs twice"),
        ("questions.0.question", KeyError, "questions[0].question"),
        ("questions.0.question", "(nur eine Bemerkung)", "nothing is left to ask"),
        ("questions.0.key_facts", [], "questions[0].key_facts"),
        ("questions.0.key_facts", KeyError, "questions[0].key_facts"),
        ("questions.0.sources", KeyError, "questions[0].sources"),
        ("questions.0.sources.0.locator", KeyError, "questions[0].sources[0].locator"),
        ("questions.0.key_fact_alternatives", {"7 kg": ["sieben"]}, "not one of the key_facts"),
        ("questions.0.key_fact_alternatives", {"5 kg": []}, "key_fact_alternatives.5 kg"),
        ("questions.1.sources.0.supports", "size", "a contradiction needs a source"),
    ],
)
def test_invalid_questions_name_the_place(path: str, value: object, message: str) -> None:
    with pytest.raises(QuestionFormatError, match=message.replace("[", r"\[").replace("]", r"\]")):
        load_questions(broken(path, value))


@pytest.mark.parametrize("text", ["", "  ", "{", "[]"])
def test_unreadable_questions(text: str) -> None:
    with pytest.raises(QuestionFormatError):
        load_questions(text)


def test_places_are_the_union_of_the_probes_of_a_question() -> None:
    data = json.loads(json.dumps(PROBES))
    data["probes"].append(
        {
            "id": "question-1b",
            "query": "Wie viel Last trägt der Greifer?",
            "basis": {"question": 1},
            "expected": [{"manifest_id": "gripper-de", "sha256": SHA_DE, "pages": [6]}],
        }
    )
    found = question_places(json.dumps(data))
    assert found[1].probe_ids == ("question-1", "question-1b")
    assert {(p.manifest_id, page) for p in found[1].expected for page in p.pages} == {
        ("gripper-de", 4),
        ("gripper-en", 4),
        ("gripper-de", 6),
    }
    assert found[1].query == "Wie schwer darf die Last am Greifer sein?"
    assert found[9].expected == ()
    assert 3 not in found


def test_invalid_probe_list_raises_probe_format_error() -> None:
    with pytest.raises(ProbeFormatError):
        question_places(json.dumps({"schema_version": 1, "probes": []}))


# --- asked_text (criterion 3) ----------------------------------------------------------


def real_questions() -> list[Question]:
    return load_questions(QUESTIONS_FILE.read_text(encoding="utf-8"))


def test_asked_text_of_all_eleven_test_questions() -> None:
    read = real_questions()
    assert [question.id for question in read] == list(range(1, 12))
    for question in read:
        text = asked_text(question.question)
        assert text, question.id
        assert NO_EVIDENCE_TEXT.rstrip(".") not in text, question.id
        assert "erwartet" not in text.casefold(), question.id
        assert "widersprechen" not in text.casefold(), question.id
        assert "Kontrollfrage" not in text, question.id
        assert "(" not in text, question.id


@pytest.mark.parametrize(
    ("question", "asked"),
    [
        ("Wie viel hält der Greifer?", "Wie viel hält der Greifer?"),
        ("Wie viel hält er? (Bemerkung für Menschen.)", "Wie viel hält er?"),
        (
            f"Kontrollfrage ohne Beleg: Wann war X? Erwartet wird {OPEN_QUOTE}Nichts{CLOSE_QUOTE}.",
            "Wann war X?",
        ),
        ("Wann war X? Erwartet wird eine Absage", "Wann war X?"),
        ("Erwartet wird nichts. Wann war X?", "Wann war X?"),
    ],
)
def test_asked_text_removes_the_notes(question: str, asked: str) -> None:
    assert asked_text(question) == asked


# --- Statement groups (criterion 4) ----------------------------------------------------


def group_pages(groups: dict[str, tuple[Any, ...]]) -> dict[str, set[int]]:
    return {
        name: {page for place in found for page in place.pages} for name, found in groups.items()
    }


def test_groups_of_question_6_come_from_questions_yaml() -> None:
    question = {q.id: q for q in real_questions()}[6]
    m3 = question_places(probe_list_text("m3"))
    groups = contradiction_groups(question, m3[6])
    assert group_pages(groups) == {"A": {34}, "B": {36, 38}}
    # The other language edition counts (E-61).
    assert {place.manifest_id for place in groups["A"]} == {
        "aps-documentation-de",
        "aps-documentation-en",
    }


def test_groups_leave_out_sources_without_a_page() -> None:
    groups = contradiction_groups(questions()[2], places()[2])
    assert group_pages(groups) == {"A": {3}, "B": {5, 7}}
    assert all(place.sha256 in {SHA_DE, SHA_EN} for found in groups.values() for place in found)


def test_m3_has_places_for_every_judged_test_question() -> None:
    m3 = question_places(probe_list_text("m3"))
    assert set(m3) == set(range(1, 12))
    assert all(m3[number].expected for number in range(1, 11))
    assert m3[11].expected == ()


# --- Verdict of one run (criterion 1) ---------------------------------------------------


def test_fact_with_key_fact_and_citation_of_an_expected_place_is_correct() -> None:
    result = judged(1, seen([ref(1)]))
    assert result.verdict is Verdict.CORRECT
    assert result.evidence_rank == 1
    assert result.evidence_cited
    assert result.found_places == [PlaceLabel("gripper-de", 4, None)]
    assert result.missing_key_facts == []
    assert (result.valid_citations, result.expected_citations, result.sources) == (1, 1, 1)


def test_missing_key_fact_is_wrong() -> None:
    result = judged(1, seen([ref(1)], text="Der Greifer G-12 hält viel [1]."))
    assert result.verdict is Verdict.WRONG
    assert result.missing_key_facts == ["5 kg"]
    assert result.evidence_cited


def test_key_fact_only_as_alternative_counts_unless_literal() -> None:
    observed = seen([ref(1)], text="Der Greifer G-12 hält fünf Kilogramm [1].")
    assert judged(1, observed).verdict is Verdict.CORRECT
    literal = judged(1, observed, literal=True)
    assert literal.verdict is Verdict.WRONG
    assert literal.missing_key_facts == ["5 kg"]


@pytest.mark.parametrize("written", ["5kg", "5 KG", f"5{NBSP}kg", "**5 kg**"])
def test_key_facts_are_normalised(written: str) -> None:
    assert missing_key_facts(questions()[1], f"Er hält {written}.") == []


def fact_question(*key_facts: str) -> Question:
    return Question(id=1, question="Frage?", kind=QuestionKind.FACT, key_facts=key_facts)


@pytest.mark.parametrize(
    ("fact", "text", "found"),
    [
        ("5 kg", "Er hält 25 kg [1].", False),
        ("5 kg", "Er hält 12,5 kg [1].", False),
        ("5 kg", "Er hält 5 kg [1].", True),
        ("5 kg", "Er hält 5kg [1].", True),
        ("1880", "Port 18800 [1].", False),
        ("1880", "Port 1880 [1].", True),
        ("1880", "unter http://192.168.0.100:1880 [1].", True),
        ("V18", "TIA Portal V180 [1].", False),
        ("V18", "TIA Portal V18 [1].", True),
        ("V18", "TIA Portal V 18 [1].", True),
        ("Reset", "Über den Reset-Button [1].", True),
        ("OPC UA", "Der OPC-UA-Server [1].", True),
        ("1512SP", "Die CPU1512SP hat zwei Schnittstellen [1].", True),
        ("1512SP", "Die CPU 1512SP hat zwei Schnittstellen [1].", True),
        ("1512SP", "Die CPU21512SP hat zwei Schnittstellen [1].", False),
        ("1512SP", "Die CPU1512SPX hat zwei Schnittstellen [1].", False),
    ],
)
def test_key_facts_are_whole_values(fact: str, text: str, found: bool) -> None:
    assert value_occurs(fact, text) is found
    assert missing_key_facts(fact_question(fact), text) == ([] if found else [fact])


def test_key_fact_of_a_designation_right_after_a_word_is_found() -> None:
    # Work order 154: a key fact like "1512SP" counts after "CPU" without a space.
    question = fact_question("1512SP")
    assert missing_key_facts(question, "Die Steuerung ist eine CPU1512SP [1].") == []
    assert missing_key_facts(question, "Die Steuerung ist eine CPU1512SP0 [1].") == ["1512SP"]


def test_a_lengthened_key_fact_makes_a_fact_question_wrong() -> None:
    result = judged(1, seen([ref(1)], text="Der Greifer G-12 hält 25 kg [1]."))
    assert result.verdict is Verdict.WRONG
    assert result.missing_key_facts == ["5 kg"]


def test_right_file_wrong_page_is_wrong() -> None:
    result = judged(1, seen([ref(1, page=6)]))
    assert result.verdict is Verdict.WRONG
    assert result.evidence_rank is None
    assert not result.evidence_cited
    assert result.missing_places == [PlaceLabel("gripper-de", 4, None)]


def test_citation_of_the_other_language_edition_counts() -> None:
    result = judged(1, seen([ref(1, SHA_EN)]))
    assert result.verdict is Verdict.CORRECT
    assert result.found_places == [PlaceLabel("gripper-de", 4, None)]


def test_a_place_at_any_device_of_a_cited_source_counts() -> None:
    sources = [ref(1, SHA_OTHER), ref(2, devices=("g-11", "g-12"))]
    assert judged(1, seen(sources, cited=[2])).verdict is Verdict.CORRECT


def test_number_not_in_cited_does_not_count() -> None:
    result = judged(1, seen([ref(1, page=6), ref(2)], cited=[1]))
    assert result.verdict is Verdict.WRONG
    assert result.evidence_rank == 2
    assert not result.evidence_cited
    assert result.expected_citations == 0


def test_fact_with_status_no_evidence_is_wrong() -> None:
    observed = seen([ref(1)], status=AnswerStatus.NO_EVIDENCE, cited=[], text=NO_EVIDENCE_TEXT)
    assert judged(1, observed).verdict is Verdict.WRONG


def test_heading_path_of_a_markdown_place() -> None:
    hit = ref(1, SHA_MD, None, headings=("Greifer", "Netz", "Ports"))
    assert judged(4, seen([hit], text="Port 502 [1].")).verdict is Verdict.CORRECT
    other = ref(1, SHA_MD, None, headings=("Greifer", "Mechanik"))
    result = judged(4, seen([other], text="Port 502 [1]."))
    assert result.verdict is Verdict.WRONG
    assert result.missing_places == [PlaceLabel("gripper-repo", None, ["Greifer", "Netz"])]


CONTRADICTION_TEXT = "Die Unterlagen widersprechen sich: G-12 [1], G-14 [2]."


def test_contradiction_with_one_group_only_is_wrong() -> None:
    result = judged(
        2,
        seen(
            [ref(1, page=3), ref(2, page=3)], AnswerStatus.CONTRADICTION, [1, 2], CONTRADICTION_TEXT
        ),
    )
    assert result.verdict is Verdict.WRONG
    assert result.groups_found == ["A"]


def test_contradiction_with_both_groups_is_correct() -> None:
    sources = [ref(1, page=3), ref(2, SHA_EN, page=7)]
    result = judged(2, seen(sources, AnswerStatus.CONTRADICTION, [1, 2], CONTRADICTION_TEXT))
    assert result.verdict is Verdict.CORRECT
    assert result.groups_found == ["A", "B"]


def test_contradiction_with_both_groups_but_status_answered_is_wrong() -> None:
    sources = [ref(1, page=3), ref(2, page=5)]
    result = judged(2, seen(sources, AnswerStatus.ANSWERED, [1, 2], CONTRADICTION_TEXT))
    assert result.verdict is Verdict.WRONG
    assert result.groups_found == ["A", "B"]


def test_contradiction_without_a_key_fact_is_wrong() -> None:
    sources = [ref(1, page=3), ref(2, page=5)]
    text = "Die Unterlagen widersprechen sich: G-12 [1] [2]."
    result = judged(2, seen(sources, AnswerStatus.CONTRADICTION, [1, 2], text))
    assert result.verdict is Verdict.WRONG
    assert result.missing_key_facts == ["G-14"]


def test_control_question_with_no_evidence_and_no_citation_is_correct() -> None:
    observed = Observed(
        done=DoneEvent(
            status=AnswerStatus.NO_EVIDENCE,
            cited=[],
            removed_sentences=0,
            final_text=NO_EVIDENCE_TEXT,
        )
    )
    result = judged(9, observed)
    assert result.verdict is Verdict.CORRECT
    assert result.status == "no_evidence"


def test_control_question_with_a_citation_fails() -> None:
    result = judged(9, seen([ref(1)], text="Zuletzt im Mai [1]."))
    assert result.verdict is Verdict.WRONG
    assert result.valid_citations == 1


def test_error_event_gives_error() -> None:
    def failing(question: str, **kwargs: object) -> Iterator[AnswerEvent]:
        yield SourcesEvent(sources=[ref(1)])
        yield ErrorEvent(code=ErrorCode.MODEL_UNAVAILABLE)

    observed = observe(failing, "Frage?", iter([0.0, 1.0, 2.0]).__next__)
    result = judged(1, observed)
    assert result.verdict is Verdict.ERROR
    assert result.error_code == "model_unavailable"
    assert result.sources == 1


def test_question_without_probe_gives_no_probe() -> None:
    assert judged(3, seen([ref(1)])).verdict is Verdict.NO_PROBE


def test_observe_reads_times_and_closes_the_stream() -> None:
    closed: list[bool] = []

    def stream() -> Iterator[AnswerEvent]:
        try:
            yield SourcesEvent(sources=[ref(1)])
            yield DeltaEvent(text="Der Greifer ")
            yield DeltaEvent(text="hält 5 kg [1].")
            yield DoneEvent(
                status=AnswerStatus.ANSWERED, cited=[1], removed_sentences=0, final_text="x [1]."
            )
            yield DeltaEvent(text="nach dem Ende")
        finally:
            closed.append(True)

    calls: list[tuple[str, tuple[int, ...], tuple[int, ...]]] = []

    def answer(
        question: str,
        *,
        device_ids: Sequence[int] = (),
        plant_ids: Sequence[int] = (),
        seed: int | None = None,
        on_context: service.ContextObserver | None = None,
    ) -> Iterator[AnswerEvent]:
        calls.append((question, tuple(device_ids), tuple(plant_ids)))
        return stream()

    ticks = iter([10.0, 10.5, 12.0])
    observed = observe(answer, "Frage?", ticks.__next__)
    assert calls == [("Frage?", (), ())]
    assert observed.first_token_seconds == 0.5
    assert observed.total_seconds == 2.0
    assert observed.done is not None
    assert closed == [True]


def test_observe_counts_a_failing_service_as_internal_error() -> None:
    def broken_service(question: str, **kwargs: object) -> Iterator[AnswerEvent]:
        raise RuntimeError("kaputt")

    observed = observe(broken_service, "Frage?", iter([0.0, 1.0]).__next__)
    assert observed.error is ErrorCode.INTERNAL
    assert observed.done is None


# --- Several runs (criterion 2) ----------------------------------------------------------


def runs_of(*verdicts: bool) -> list[RunResult]:
    return [
        RunResult(run=index, verdict=Verdict.CORRECT if right else Verdict.WRONG)
        for index, right in enumerate(verdicts, start=1)
    ]


FACT = Question(id=1, question="Frage?", kind=QuestionKind.FACT, key_facts=("5 kg",))
CONTROL = Question(id=11, question="Frage?", kind=QuestionKind.NO_EVIDENCE, key_facts=())


def test_majority_and_strict() -> None:
    two_of_three = runs_of(True, False, True)
    majority = aggregate(FACT, two_of_three, mode=Mode.MAJORITY)
    assert majority.verdict is Verdict.CORRECT
    assert (majority.correct_runs, majority.run_count) == (2, 3)
    assert aggregate(FACT, two_of_three, mode=Mode.STRICT).verdict is Verdict.WRONG
    assert aggregate(FACT, runs_of(True, False), mode=Mode.MAJORITY).verdict is Verdict.WRONG


def test_control_question_is_strict_unless_asked() -> None:
    one_cited = runs_of(True, False, True)
    assert aggregate(CONTROL, one_cited, mode=Mode.MAJORITY).verdict is Verdict.WRONG
    relaxed = aggregate(CONTROL, one_cited, mode=Mode.MAJORITY, control_mode=Mode.MAJORITY)
    assert relaxed.verdict is Verdict.CORRECT


def test_every_run_an_error_gives_error() -> None:
    errors = [RunResult(run=n, verdict=Verdict.ERROR, error_code="timeout") for n in (1, 2)]
    assert aggregate(FACT, errors).verdict is Verdict.ERROR


def test_spread_of_ranks_and_times() -> None:
    runs = [
        RunResult(run=1, verdict=Verdict.CORRECT, evidence_rank=3, total_seconds=1.0),
        RunResult(run=2, verdict=Verdict.CORRECT, evidence_rank=1, total_seconds=4.0),
        RunResult(run=3, verdict=Verdict.WRONG, total_seconds=2.0, first_token_seconds=0.5),
    ]
    result = aggregate(FACT, runs)
    assert (result.evidence_rank_min, result.evidence_rank_max) == (1, 3)
    assert (result.total_seconds.median, result.total_seconds.minimum) == (2.0, 1.0)
    assert result.total_seconds.maximum == 4.0
    assert result.first_token_seconds.median == 0.5


def matrix(rows: Sequence[Sequence[bool]], control: Sequence[bool]) -> list[QuestionResult]:
    results = [
        aggregate(
            Question(id=index, question="Frage?", kind=QuestionKind.FACT, key_facts=("x",)),
            runs_of(*row),
        )
        for index, row in enumerate(rows, start=1)
    ]
    return [*results, aggregate(CONTROL, runs_of(*control))]


ALWAYS = (True, True, True)


def test_per_run_counts_9_7_8() -> None:
    rows = [ALWAYS] * 7 + [(True, False, True), (True, False, False), (False, False, False)]
    summary = summarise(matrix(rows, ALWAYS), runs=3)
    assert [item.correct_count for item in summary.per_run] == [9, 7, 8]
    assert [item.passed for item in summary.per_run] == [True, False, True]
    assert summary.passed_per_run
    assert summary.correct_count == 8
    assert summary.passed_per_question
    assert summary.judged == 10


def test_rules_can_differ_and_passed_follows_the_rule() -> None:
    # Every question is right in two of three runs, but no run reaches 8 of 10.
    rows = [(False, True, True)] * 4 + [(True, False, True)] * 3 + [(True, True, False)] * 3
    results = matrix(rows, ALWAYS)
    per_question = summarise(results, runs=3, rule=Rule.PER_QUESTION)
    assert [item.correct_count for item in per_question.per_run] == [6, 7, 7]
    assert per_question.correct_count == 10
    assert per_question.passed_per_question
    assert not per_question.passed_per_run
    assert per_question.passed
    per_run = summarise(results, runs=3, rule=Rule.PER_RUN)
    assert not per_run.passed
    strict = summarise(results, runs=3, mode=Mode.STRICT, rule=Rule.PER_RUN)
    assert not strict.passed


def test_without_control_question_nothing_is_passed() -> None:
    results = matrix([ALWAYS] * 10, ALWAYS)[:-1]
    for rule in Rule:
        summary = summarise(results, runs=3, rule=rule)
        assert summary.correct_count == 10
        assert not summary.control_asked
        assert not summary.control_ok
        assert not summary.passed_per_question
        assert not summary.passed_per_run
        assert not summary.passed
        assert all(not item.control_ok and not item.passed for item in summary.per_run)


@pytest.mark.usefixtures("ai_on")
def test_report_says_control_question_not_asked() -> None:
    scripted = ScriptedAnswer([SourcesEvent(sources=[ref(1)]), done()])
    report = evaluate([questions()[1]], places(), answer=scripted, ingested=all_ingested)
    text = format_table(report)
    assert "1/1 right, control question not asked (strict); passed: no" in text
    assert "Rule per-question: NOT PASSED" in text
    assert "1    1/1    not asked         no" in text
    data = json.loads(format_json(report))
    assert data["summary"]["control_asked"] is False
    assert data["summary"]["passed"] is False


def test_failed_control_question_fails_even_with_ten_of_ten() -> None:
    summary = summarise(matrix([ALWAYS] * 10, (True, True, False)), runs=3)
    assert summary.correct_count == 10
    assert not summary.control_ok
    assert not summary.passed_per_question
    assert [item.control_ok for item in summary.per_run] == [True, True, False]
    assert summary.passed_per_run  # two of three runs pass
    assert not summary.passed


def test_per_run_strict_needs_every_run() -> None:
    rows = [ALWAYS] * 7 + [(True, False, True), (True, False, False), (False, False, False)]
    summary = summarise(matrix(rows, ALWAYS), runs=3, mode=Mode.STRICT, rule=Rule.PER_RUN)
    assert summary.runs_passed == 2
    assert not summary.passed_per_run
    assert not summary.passed


# --- The run without database and model --------------------------------------------------


class ScriptedAnswer:
    """Stands in for the answer service: the same events for every question."""

    def __init__(
        self,
        events: Sequence[AnswerEvent],
        contexts: Sequence[tuple[float | None, bool]] = (),
        *,
        twice: bool = False,
    ) -> None:
        self.events = list(events)
        #: ``(best_distance, below_threshold)`` reported by call number n (the last one
        #: repeats); nothing is reported without any.
        self.contexts = list(contexts)
        #: Report every context twice (the second call with the values turned around).
        self.twice = twice
        self.asked: list[str] = []
        self.seeds: list[int | None] = []

    def __call__(
        self,
        question: str,
        *,
        device_ids: Sequence[int] = (),
        plant_ids: Sequence[int] = (),
        seed: int | None = None,
        on_context: service.ContextObserver | None = None,
    ) -> Iterator[AnswerEvent]:
        assert not device_ids
        assert not plant_ids
        if on_context is not None and self.contexts:
            distance, below = self.contexts[min(len(self.asked), len(self.contexts) - 1)]
            on_context(distance, below)
            if self.twice:
                on_context(0.9999, not below)
        self.asked.append(question)
        self.seeds.append(seed)
        return iter(self.events)


def all_ingested(checksums: Iterable[str]) -> set[str]:
    return set(checksums)


def done(text: str = "Der Greifer G-12 hält 5 kg [1].", cited: Sequence[int] = (1,)) -> DoneEvent:
    return DoneEvent(
        status=AnswerStatus.ANSWERED, cited=list(cited), removed_sentences=0, final_text=text
    )


@pytest.fixture
def ai_on(settings: Settings) -> None:
    settings.TWOX_AI_ENABLED = True


@pytest.mark.usefixtures("ai_on")
def test_evaluate_asks_runs_times_and_reports_no_probe_and_not_ingested() -> None:
    scripted = ScriptedAnswer([SourcesEvent(sources=[ref(1)]), done()])
    ingested = {SHA_DE, SHA_EN}
    report = evaluate(
        list(questions().values()),
        places(),
        runs=2,
        answer=scripted,
        ingested=lambda checksums: ingested & set(checksums),
    )
    verdicts = {result.question_id: result.verdict for result in report.questions}
    assert verdicts == {
        1: Verdict.CORRECT,
        2: Verdict.WRONG,
        3: Verdict.NO_PROBE,
        4: Verdict.NOT_INGESTED,
        9: Verdict.WRONG,
    }
    # Questions 1, 2 and 9, twice each; the notes of question 9 are not asked.
    assert len(scripted.asked) == 6
    assert "Wann wurde der Greifer zuletzt geschmiert?" in scripted.asked
    assert not any("Erwartet" in asked or "Kontrollfrage" in asked for asked in scripted.asked)
    assert report.summary is not None
    assert (report.summary.no_probe_count, report.summary.not_ingested_count) == (1, 1)
    not_ingested = {result.question_id: result.not_ingested for result in report.questions}
    assert not_ingested[4] == ["gripper-repo"]
    assert report.summary.judged == 4
    assert report.summary.correct_count == 1
    assert not report.summary.control_ok
    assert not report.summary.passed


@pytest.mark.usefixtures("ai_on")
def test_evaluate_with_the_probe_wording_asks_the_probe_query() -> None:
    scripted = ScriptedAnswer([SourcesEvent(sources=[]), done(NO_EVIDENCE_TEXT, ())])
    subset = [questions()[1], questions()[9]]
    evaluate(subset, places(), answer=scripted, wording=Wording.PROBE, ingested=all_ingested)
    assert scripted.asked == [
        "Wie schwer darf die Last am Greifer sein?",
        "Wann wurde der Greifer zuletzt geschmiert?",
    ]


@pytest.mark.usefixtures("ai_on")
def test_header_names_model_settings_and_options(settings: Settings) -> None:
    settings.TWOX_CHAT_MODEL = "fake-chat:1b"
    settings.TWOX_CHAT_TEMPERATURE = 0.2
    report = evaluate(
        [questions()[9]],
        places(),
        runs=3,
        answer=ScriptedAnswer([SourcesEvent(sources=[]), done(NO_EVIDENCE_TEXT, ())]),
        ingested=all_ingested,
        mode=Mode.STRICT,
        rule=Rule.PER_RUN,
        literal=True,
    )
    text = format_table(report)
    assert "Chat model fake-chat:1b" in text
    assert "temperature 0.2" in text
    assert "TWOX_ANSWER_MAX_SOURCES" in text
    assert "runs 3; mode strict; control question strict; rule per-run" in text
    assert "key facts literal" in text
    data = json.loads(format_json(report))
    assert data["prompt_version"]
    assert data["answer_settings"]["TWOX_ANSWER_MAX_SOURCES"] == settings.TWOX_ANSWER_MAX_SOURCES
    assert data["questions"][0]["verdict_a7"] is None
    assert data["summary"]["per_run"] == [
        {"run": n, "correct_count": 0, "control_ok": False, "passed": False} for n in (1, 2, 3)
    ]


def test_ai_off_asks_nothing_and_says_not_measured(settings: Settings) -> None:
    settings.TWOX_AI_ENABLED = False

    def never(question: str, **kwargs: object) -> Iterator[AnswerEvent]:
        raise AssertionError("must not be asked")

    def no_database(checksums: Iterable[str]) -> set[str]:
        raise AssertionError("must not look")

    report = evaluate(list(questions().values()), places(), answer=never, ingested=no_database)
    assert not report.measured
    assert report.summary is None
    assert report.embed_model is None
    text = format_table(report)
    assert f"{NOT_MEASURED_NOTE}." in text
    assert "/10" not in text
    assert "right" not in text
    data = json.loads(format_json(report))
    assert data["measured"] is False
    assert data["summary"] is None
    assert data["note"] == NOT_MEASURED_NOTE


# --- No texts in the output (criterion 5) --------------------------------------------------

MARKERS = {
    "question": "Quokkafrage",
    "final": "Wombatantwort",
    "removed": "Numbatsatz",
    "section": "Bilbyabschnitt",
    "heading": "Dingoueberschrift",
}


def marked_events() -> list[AnswerEvent]:
    section = ContextSource(
        n=1,
        section_id=101,
        version_id=11,
        ordinal=0,
        sha256=SHA_DE,
        page_start=4,
        page_end=4,
        heading_path=[MARKERS["heading"]],
        text=f"{MARKERS['section']}: Der Greifer G-12 hält 5 kg.",
        locations=[location(101)],
    )
    return [
        SourcesEvent(sources=[to_source_ref(section)]),
        DeltaEvent(text=f"{MARKERS['removed']} 9 kg [7]. "),
        DeltaEvent(text=f"{MARKERS['final']} 5 kg [1]."),
        DoneEvent(
            status=AnswerStatus.ANSWERED,
            cited=[1],
            removed_sentences=1,
            final_text=f"{MARKERS['final']} 5 kg [1].",
        ),
    ]


@pytest.mark.usefixtures("ai_on")
def test_output_holds_no_question_answer_or_section_text() -> None:
    data = json.loads(json.dumps(QUESTIONS))
    for question in data["questions"]:
        question["question"] = f"{MARKERS['question']} {question['question']}"
    marked_questions = load_questions(json.dumps(data))
    reports = [
        evaluate(
            marked_questions,
            places(),
            runs=2,
            answer=ScriptedAnswer(events, [(0.25, False)]),
            ingested=all_ingested,
        )
        for events in (marked_events(), [*marked_events()[:2], ErrorEvent(code=ErrorCode.TIMEOUT)])
    ]
    for report in reports:
        assert report.summary is not None
        for output in (format_table(report), format_json(report)):
            for marker in MARKERS.values():
                assert marker not in output
    assert reports[0].questions[0].verdict is Verdict.CORRECT
    assert reports[0].questions[0].runs[0].removed_sentences == 1


# --- The command over the real answer service (criteria 6, 7, 8) ---------------------------

GRIPPER = "Der Greifer G-12 hält höchstens 5 kg."
NOTE = "Laut Nachtrag hält der Greifer G-12 höchstens 7 kg."
CONTROL_TEXT = "Wann wurde der Greifer zuletzt geschmiert?"


@pytest.fixture
def small_factory(fake_embedder: FakeEmbedder, tmp_path: Path) -> dict[str, Path]:
    """Two sections at two devices, a question file and a probe list in ``tmp_path``."""
    plant = make_plant()
    version_a = make_document(make_device(plant, "gripper-a"), title="Handbuch A")
    version_b = make_document(make_device(plant, "gripper-b"), title="Handbuch B")
    (section_a,) = add_sections(version_a, GRIPPER, page=4)
    (section_b,) = add_sections(version_b, NOTE, page=9)
    embed(section_a, at_angle(10, axis=1))
    embed(section_b, at_angle(20, axis=2))
    fake_embedder.queries[CONTROL_TEXT] = unit(5)  # far from every section
    question_file = tmp_path / "questions.json"
    question_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "questions": [
                    {
                        "id": 1,
                        "question": "Wie viel hält der Greifer G-12 höchstens?",
                        "kind": "fact",
                        "key_facts": ["5 kg"],
                        "sources": [statement("hb-a", "PDF-S. 4", "Load.")],
                    },
                    {
                        "id": 2,
                        "question": "Was sagt der Nachtrag zur Last des Greifers?",
                        "kind": "fact",
                        "key_facts": ["7 kg"],
                        "sources": [statement("hb-b", "PDF-S. 9", "Load in the note.")],
                    },
                    {
                        "id": 3,
                        "question": f"Kontrollfrage: {CONTROL_TEXT}",
                        "kind": "no-evidence",
                        "key_facts": [],
                        "sources": [],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    probe_file = tmp_path / "probes.json"
    probe_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "probes": [
                    {
                        "id": "question-1",
                        "query": "Last am Greifer",
                        "basis": {"question": 1},
                        "expected": [
                            {"manifest_id": "hb-a", "sha256": version_a.sha256, "pages": [4]}
                        ],
                    },
                    {
                        "id": "question-2",
                        "query": "Last laut Nachtrag",
                        "basis": {"question": 2},
                        "expected": [
                            {"manifest_id": "hb-b", "sha256": version_b.sha256, "pages": [9]}
                        ],
                    },
                    {
                        "id": "control-3",
                        "query": CONTROL_TEXT,
                        "basis": {"question": 3},
                        "expected": [],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return {"questions": question_file, "probes": probe_file}


def use_chat(monkeypatch: pytest.MonkeyPatch, pieces: Sequence[str]) -> FakeChatModel:
    chat = FakeChatModel(list(pieces))
    monkeypatch.setattr(chat_module, "get_chat_model", lambda: chat)
    return chat


def run_command(*args: str, stdin: io.StringIO | None = None) -> str:
    out = io.StringIO()
    options: dict[str, Any] = {"stdout": out}
    if stdin is not None:
        options["stdin"] = stdin
    call_command("evaluate_answers", *args, **options)
    return out.getvalue()


@pytest.mark.usefixtures("every_text_a_source")  # short texts, work order 153
@pytest.mark.django_db
def test_command_measures_over_the_real_answer_service(
    small_factory: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    chat = use_chat(monkeypatch, ["Der Greifer G-12 ", "hält höchstens 5 kg [1]."])
    files = [
        "--questions",
        str(small_factory["questions"]),
        "--probes",
        str(small_factory["probes"]),
    ]

    text = run_command(*files, "--runs", "1")

    assert "Per question (majority): 1/2 right, control question ok (strict); passed: no" in text
    assert "Rule per-question: NOT PASSED" in text
    # The control question was below the threshold: the model was asked twice only.
    assert len(chat.calls) == 2

    data = json.loads(run_command(*files, "--runs", "1", "--json"))
    assert data["measured"] is True
    assert data["summary"]["correct_count"] == 1
    assert data["summary"]["judged"] == 2
    assert data["summary"]["control_ok"] is True
    assert data["summary"]["per_run"] == [
        {"run": 1, "correct_count": 1, "control_ok": True, "passed": False}
    ]
    verdicts = {item["question_id"]: item["verdict"] for item in data["questions"]}
    assert verdicts == {1: "correct", 2: "wrong", 3: "correct"}
    second = data["questions"][1]["runs"][0]
    assert second["missing_key_facts"] == ["7 kg"]
    assert second["evidence_rank"] == 2
    assert second["evidence_cited"] is False


@pytest.mark.django_db
def test_command_reads_questions_from_standard_input_and_takes_a_subset(
    small_factory: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    use_chat(monkeypatch, ["Der Greifer G-12 hält höchstens 5 kg [1]."])
    stdin = io.StringIO(BOM + small_factory["questions"].read_text(encoding="utf-8"))
    data = json.loads(
        run_command(
            "--questions", "-", "--probes", str(small_factory["probes"]), "--only", "1",
            "--runs", "2", "--json", stdin=stdin,
        )
    )  # fmt: skip
    assert [item["question_id"] for item in data["questions"]] == [1]
    assert data["questions"][0]["correct_runs"] == 2
    assert data["runs"] == 2
    # --only without the control question: no acceptance.
    assert data["summary"]["control_asked"] is False
    assert data["summary"]["passed"] is False


@pytest.mark.django_db
def test_logs_hold_no_question_answer_or_section_text(
    small_factory: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    question_marker, answer_marker, section_marker = (
        "Quokkafrage",
        "Wombatstueck",
        "Numbatabschnitt",
    )
    data = json.loads(small_factory["questions"].read_text(encoding="utf-8"))
    data["questions"][0]["question"] = f"{question_marker} zum Greifer G-12?"
    small_factory["questions"].write_text(json.dumps(data), encoding="utf-8")
    plant = make_plant("line-log")
    version = make_document(make_device(plant, "gripper-log"))
    (section,) = add_sections(version, f"{section_marker}: Der Greifer G-12 hält 5 kg.", page=2)
    embed(section, at_angle(5, axis=3))
    use_chat(monkeypatch, [f"{answer_marker} G-12 hält 5 kg [1]."])
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="twox")

    run_command(
        "--questions", str(small_factory["questions"]),
        "--probes", str(small_factory["probes"]), "--runs", "2",
    )  # fmt: skip

    lines = [record.getMessage() for record in caplog.records]
    assert any(line.startswith("Evaluation run: question=1 run=2") for line in lines)
    for line in lines:
        for marker in (question_marker, answer_marker, section_marker, "geschmiert"):
            assert marker not in line


def test_command_with_ai_off_asks_nothing(
    settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.TWOX_AI_ENABLED = False

    def never(*args: object, **kwargs: object) -> Iterator[AnswerEvent]:
        raise AssertionError("must not be asked")

    monkeypatch.setattr(service, "answer", never)
    question_file = tmp_path / "questions.json"
    question_file.write_text(json.dumps(QUESTIONS), encoding="utf-8")
    probe_file = tmp_path / "probes.json"
    probe_file.write_text(json.dumps(PROBES), encoding="utf-8")

    text = run_command("--questions", str(question_file), "--probes", str(probe_file))

    assert "AI features off" in text
    assert f"{NOT_MEASURED_NOTE}." in text


@pytest.mark.parametrize(
    ("questions_text", "probes_text", "message"),
    [
        ("{", None, "Invalid test questions: not valid JSON"),
        (
            json.dumps({"schema_version": 1, "questions": [{"id": 1}]}),
            None,
            "Invalid test questions",
        ),
        (None, "{", "Invalid probe list: not valid JSON"),
        (None, json.dumps({"schema_version": 1, "probes": []}), "Invalid probe list"),
    ],
)
def test_command_rejects_invalid_files(
    tmp_path: Path, questions_text: str | None, probes_text: str | None, message: str
) -> None:
    question_file = tmp_path / "questions.json"
    question_file.write_text(questions_text or json.dumps(QUESTIONS), encoding="utf-8")
    probe_file = tmp_path / "probes.json"
    probe_file.write_text(probes_text or json.dumps(PROBES), encoding="utf-8")
    with pytest.raises(CommandError, match=message):
        run_command("--questions", str(question_file), "--probes", str(probe_file))


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--questions", "/nowhere/questions.json"], "Invalid test questions: cannot read"),
        (["--probes", "m9"], "Invalid --probes: there is no probe list"),
        (["--probes", "/nowhere/probes.json"], "Invalid probe list: cannot read"),
        (["--runs", "0"], "Invalid --runs"),
        (["--seed", "x"], "invalid int value"),
        (["--only", "1,x"], "Invalid --only"),
        (["--only", "12"], "Invalid --only: no test question 12"),
    ],
)
def test_command_rejects_invalid_options(args: list[str], message: str) -> None:
    with pytest.raises(CommandError, match=message):
        run_command(*args)


def test_command_with_the_real_test_questions_and_m3_reads_them(settings: Settings) -> None:
    settings.TWOX_AI_ENABLED = False
    text = run_command()
    assert "runs 3; mode majority; control question strict; rule per-question" in text
    assert f"{NOT_MEASURED_NOTE}." in text


# --- Seed and distance per run (work order 142) -------------------------------------------

ANSWERED: list[AnswerEvent] = [SourcesEvent(sources=[ref(1)]), done()]


def clock() -> Iterator[float]:
    return itertools.count(0.0, 1.0)


def test_observe_passes_the_seed_on_and_keeps_the_context_values() -> None:
    scripted = ScriptedAnswer(ANSWERED, [(0.25, False)])

    observed = observe(scripted, "Frage?", clock().__next__, seed=7)

    assert scripted.seeds == [7]
    assert (observed.best_distance, observed.below_threshold) == (0.25, False)


def test_observe_without_seed_sends_none() -> None:
    scripted = ScriptedAnswer(ANSWERED)

    observe(scripted, "Frage?", clock().__next__)

    assert scripted.seeds == [None]


def test_observe_keeps_the_first_of_several_context_calls() -> None:
    scripted = ScriptedAnswer(ANSWERED, [(0.25, False)], twice=True)

    observed = observe(scripted, "Frage?", clock().__next__)

    assert (observed.best_distance, observed.below_threshold) == (0.25, False)


def test_observe_without_a_context_call_gives_none() -> None:
    observed = observe(ScriptedAnswer(ANSWERED), "Frage?", clock().__next__)

    assert (observed.best_distance, observed.below_threshold) == (None, None)


def test_run_results_carry_distance_and_gate_for_every_verdict() -> None:
    answered = judged(1, replace(seen([ref(1)]), best_distance=0.25, below_threshold=False))
    closed = judged(
        9,
        replace(
            seen([], AnswerStatus.NO_EVIDENCE, (), NO_EVIDENCE_TEXT),
            best_distance=0.75,
            below_threshold=True,
        ),
    )
    failed = judged(1, Observed(error=ErrorCode.TIMEOUT, best_distance=0.5, below_threshold=False))
    no_probe = judged(3, replace(seen([ref(1)]), best_distance=0.125, below_threshold=False))
    silent = judged(1, seen([ref(1)]))

    assert answered.verdict is Verdict.CORRECT
    assert (answered.best_distance, answered.below_threshold) == (0.25, False)
    assert closed.verdict is Verdict.CORRECT
    assert (closed.best_distance, closed.below_threshold) == (0.75, True)
    assert failed.verdict is Verdict.ERROR
    assert (failed.best_distance, failed.below_threshold) == (0.5, False)
    assert no_probe.verdict is Verdict.NO_PROBE
    assert (no_probe.best_distance, no_probe.below_threshold) == (0.125, False)
    assert (silent.best_distance, silent.below_threshold) == (None, None)


def test_question_result_spreads_the_distance_and_counts_closed_gates() -> None:
    runs = [
        RunResult(run=1, verdict=Verdict.CORRECT, best_distance=0.5, below_threshold=False),
        RunResult(run=2, verdict=Verdict.WRONG, best_distance=0.25, below_threshold=True),
        RunResult(run=3, verdict=Verdict.WRONG, best_distance=0.75, below_threshold=True),
        RunResult(run=4, verdict=Verdict.ERROR),
    ]

    result = aggregate(FACT, runs)

    assert (result.best_distance.median, result.best_distance.minimum) == (0.5, 0.25)
    assert result.best_distance.maximum == 0.75
    assert result.below_threshold_runs == 2
    empty = aggregate(FACT, [RunResult(run=1, verdict=Verdict.ERROR)])
    assert empty.best_distance.median is None
    assert empty.below_threshold_runs == 0


@pytest.mark.usefixtures("ai_on")
def test_evaluate_sends_the_same_seed_with_every_question_and_run() -> None:
    scripted = ScriptedAnswer(ANSWERED)
    subset = [questions()[1], questions()[9]]

    report = evaluate(subset, places(), runs=3, answer=scripted, ingested=all_ingested, seed=7)
    without = ScriptedAnswer(ANSWERED)
    evaluate(subset, places(), runs=2, answer=without, ingested=all_ingested)

    assert scripted.seeds == [7] * 6
    assert without.seeds == [None] * 4
    assert report.seed == 7


@pytest.mark.usefixtures("ai_on")
def test_report_shows_seed_distance_and_gate_in_text_and_json() -> None:
    scripted = ScriptedAnswer(ANSWERED, [(0.25, False), (0.75, True)])
    subset = [questions()[1], questions()[9]]
    report = evaluate(subset, places(), answer=scripted, ingested=all_ingested, seed=7)

    text = format_table(report)

    assert "seed 7;" in text
    assert "best distance (min-max)" in text
    assert "0.2500 (0.2500-0.2500)" in text
    assert "0.7500 (0.7500-0.7500)" in text
    first_table, run_table = text.split("Runs:")
    assert "below threshold" in first_table
    assert "0/1" in first_table
    assert "1/1" in first_table
    assert "below threshold" in run_table
    data = json.loads(format_json(report))
    assert data["seed"] == 7
    first, control = data["questions"]
    assert first["runs"][0]["best_distance"] == 0.25
    assert first["runs"][0]["below_threshold"] is False
    assert first["best_distance"] == {"median": 0.25, "minimum": 0.25, "maximum": 0.25}
    assert first["below_threshold_runs"] == 0
    assert control["runs"][0]["best_distance"] == 0.75
    assert control["runs"][0]["below_threshold"] is True
    assert control["below_threshold_runs"] == 1


@pytest.mark.usefixtures("ai_on")
def test_report_shows_a_dash_without_seed_and_without_values() -> None:
    report = evaluate(
        [questions()[1]],
        places(),
        answer=ScriptedAnswer(ANSWERED),
        ingested=all_ingested,
    )

    text = format_table(report)

    assert "seed -;" in text
    run_line = next(line for line in text.split("Runs:")[1].splitlines() if "answered" in line)
    assert "0.2500" not in run_line
    data = json.loads(format_json(report))
    assert data["seed"] is None
    assert data["questions"][0]["runs"][0]["best_distance"] is None
    assert data["questions"][0]["runs"][0]["below_threshold"] is None
    assert data["questions"][0]["best_distance"]["median"] is None


def test_ai_off_report_names_the_seed(settings: Settings) -> None:
    settings.TWOX_AI_ENABLED = False

    report = evaluate([], {}, seed=7)

    assert report.seed == 7
    assert "seed 7;" in format_table(report)


@pytest.mark.django_db
def test_command_passes_the_seed_and_reports_distances_of_the_real_service(
    small_factory: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    chat = use_chat(monkeypatch, ["Der Greifer G-12 hält höchstens 5 kg [1]."])
    files = [
        "--questions",
        str(small_factory["questions"]),
        "--probes",
        str(small_factory["probes"]),
    ]

    data = json.loads(run_command(*files, "--runs", "2", "--seed", "7", "--json"))

    assert data["seed"] == 7
    assert chat.calls
    assert {call.seed for call in chat.calls} == {7}
    by_id = {item["question_id"]: item for item in data["questions"]}
    for question in (1, 2):
        for run in by_id[question]["runs"]:
            assert isinstance(run["best_distance"], float)
            assert run["below_threshold"] is False
    control = by_id[3]
    assert control["below_threshold_runs"] == 2
    assert all(run["below_threshold"] is True for run in control["runs"])
    assert all(isinstance(run["best_distance"], float) for run in control["runs"])

    plain = json.loads(run_command(*files, "--runs", "1", "--json"))
    assert plain["seed"] is None
    assert chat.calls[-1].seed is None


@pytest.mark.django_db
def test_command_hands_the_seed_to_evaluate(
    small_factory: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    seen_seeds: list[int | None] = []

    def spy(
        questions: Sequence[Question],
        places: dict[int, QuestionPlaces],
        *,
        runs: int,
        mode: Mode,
        control_mode: Mode,
        rule: Rule,
        wording: Wording,
        literal: bool,
        seed: int | None,
    ) -> Report:
        seen_seeds.append(seed)
        return evaluate(questions, places, runs=runs, answer=ScriptedAnswer(ANSWERED), seed=seed)

    monkeypatch.setattr("twox.answers.management.commands.evaluate_answers.evaluate", spy)
    files = ["--questions", str(small_factory["questions"])]
    files += ["--probes", str(small_factory["probes"])]

    run_command(*files, "--seed", "7")
    run_command(*files)

    assert seen_seeds == [7, None]


def test_command_help_names_the_seed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        call_command("evaluate_answers", "--help")
    assert "--seed N" in capsys.readouterr().out
