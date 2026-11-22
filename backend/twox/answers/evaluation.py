"""Answer evaluation: the test questions through the answer service (M3, work order 127).

The acceptance of M3 reads "at least 8 of 10 test questions right; the control
question without an invented answer". This module makes it measurable and
repeatable; the command ``evaluate_answers`` prints the report. It is the
counterpart of :mod:`twox.search.evaluation` (056, 120).

Inputs
    * **Test questions** (:func:`load_questions`): the format of
      ``testfactory/questions.yaml`` (JSON notation, ``schema_version`` 1).
      Only the entries under ``questions`` count; ``candidates`` are ignored.
      Read are ``id``, ``question``, ``kind`` (``fact``, ``contradiction``,
      ``no-evidence``), ``key_facts``, ``sources`` and the optional
      ``key_fact_alternatives`` (a key fact mapped to equivalent spellings).
    * **Expected places** (:func:`question_places`): a probe list of
      :mod:`twox.search.evaluation` (by default ``m3.json``), read with
      :func:`~twox.search.evaluation.load_probes`. For question N they are the
      union of the expected places of all probes with ``basis.question == N``;
      places in the other language edition are part of the probes already
      (E-61). A fact or contradiction question without a probe is
      ``no_probe``, one none of whose files is ingested ``not_ingested``;
      neither is asked, and both count as not right.
    * **Asked text** (:func:`asked_text`): the question without the notes for
      people (a leading "Kontrollfrage ...:", remarks in brackets, a sentence
      starting with "Erwartet wird"). With ``Wording.PROBE`` the query of the
      first probe of the question is asked instead.

Verdict of one run (:func:`judge_run`, pure)
    Only the structured events count, never instructions in an answer
    (guard rail 4), and always :attr:`~twox.answers.types.DoneEvent.final_text`,
    the checked text, never the streamed pieces. A *cited source* is a source
    of the ``sources`` event whose number is in ``done.cited``; each of its
    places (E-55: a section may be stored at several devices) is compared
    with :func:`~twox.search.evaluation.matching_place`, so pages and heading
    paths count exactly as in the search measurement. A key fact is present
    when its value, normalised by :func:`twox.answers.citations.normalise_value`
    (white space, case, dashes; "5 kg" = "5kg"), occurs in the normalised final
    text, or one of its alternatives does (not with ``literal``). The
    comparison is a plain containment of normalised text: "5 kg" is also found
    in "25 kg"; that is why a7 confirms every automatic verdict (D5).

    * ``fact``: right when the status is ``answered``, every key fact is
      present and at least one cited source points to an expected place.
    * ``contradiction``: right when the status is ``contradiction``, every key
      fact is present and the cited sources hit both statement groups. The
      groups come from ``questions.yaml``: sources whose ``supports`` starts
      with "Statement A:" or "Statement B:", with the page from the locator
      ("PDF-S. n") and file and checksum from the probe of the same
      ``manifest_id`` (the other language edition counts, E-61). Sources
      without a PDF page (a folder of a repository) are left out.
    * ``no-evidence``: right only when the status is ``no_evidence`` and
      nothing is cited.
    * An ``error`` event gives ``error``, never right.

Over several runs (:func:`aggregate`, :func:`summarise`, pure)
    A question is right by majority (more than half of its runs right) or
    strictly (every run right). The control question is always judged
    strictly unless ``control_mode`` says otherwise. Two acceptance rules
    are computed: *per question* (the final verdicts give x of the judged
    questions; passed when x reaches :data:`REQUIRED_CORRECT` and the control
    question is right) and *per run* (a run passes with at least
    :data:`REQUIRED_CORRECT` right questions and the control question right in
    that run; passed when the majority, or with ``strict`` every run, passes).
    ``rule`` decides which of them gives ``passed``.

With the AI features off (E-59) no question is asked and the model service
is never contacted: the report says "not measured" and gives no x/10.

The report holds identifiers, pages, heading paths of the probes, numbers,
statuses and codes, and the key facts of ``questions.yaml`` that were not
found; never the question, an answer, a removed sentence, a section text or
a snippet. Nothing is stored (D7). The log holds one line per run with the
question id, verdict, status or error code, model name, duration and number
of sources.
"""

import json
import logging
import re
import statistics
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from typing import Any, Protocol

from django.conf import settings

from twox.answers import prompt, service
from twox.answers.citations import normalise_value
from twox.answers.types import (
    AnswerEvent,
    AnswerStatus,
    DeltaEvent,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    SourceRef,
    SourcesEvent,
)
from twox.search.evaluation import (
    ExpectedPlace,
    Place,
    SearchKind,
    ingested_checksums,
    load_probes,
    matching_place,
)
from twox.search.evaluation import judge as judge_places

logger = logging.getLogger(__name__)

#: Version of the format of the test questions.
SCHEMA_VERSION = 1
#: Right questions a run or the final verdicts need (acceptance of M3: 8 of 10).
REQUIRED_CORRECT = 8
#: Runs per question unless asked otherwise (D5 (a), E-69: three runs, majority).
DEFAULT_RUNS = 3
#: Why nothing was measured.
NOT_MEASURED_NOTE = "AI features not enabled: not measured"
#: Prefixes of ``supports`` that put a source into a statement group.
STATEMENT_GROUPS = {"A": "Statement A:", "B": "Statement B:"}

#: A page index of a PDF file in a locator ("PDF-S. 31").
_PDF_PAGE = re.compile(r"PDF-S\.\s*(\d+)")
#: A leading label of the control question, up to the first colon.
_CONTROL_LABEL = re.compile(r"^\s*Kontrollfrage[^:]*:\s*", re.IGNORECASE)
#: A remark in round brackets.
_REMARK = re.compile(r"\s*\([^()]*\)")
#: Straight and typographic closing quotes (U+201C, U+201D, U+00BB) after a sentence end.
_CLOSING_QUOTES = "\"'" + "".join(map(chr, (0x201C, 0x201D, 0x00BB)))
#: A sentence starting with "Erwartet wird", up to its end (closing quotes included).
_EXPECTED_SENTENCE = re.compile(
    rf"(?:^|(?<=[.!?]))\s*Erwartet wird[^.!?]*(?:[.!?][{re.escape(_CLOSING_QUOTES)}]*|$)",
    re.IGNORECASE,
)
_SPACES = re.compile(r"\s+")


class QuestionFormatError(ValueError):
    """The test questions are not valid; the message names the place."""


class QuestionKind(StrEnum):
    """What a test question expects."""

    FACT = "fact"
    CONTRADICTION = "contradiction"
    NO_EVIDENCE = "no-evidence"


class Verdict(StrEnum):
    """The verdict of a run or of a question."""

    CORRECT = "correct"
    WRONG = "wrong"
    ERROR = "error"
    #: No probe names the expected places; not asked.
    NO_PROBE = "no_probe"
    #: None of the expected files is ingested; not asked.
    NOT_INGESTED = "not_ingested"


class Mode(StrEnum):
    """How the runs of a question (or the runs of the per-run rule) are combined."""

    #: More than half of the runs.
    MAJORITY = "majority"
    #: Every run.
    STRICT = "strict"


class Rule(StrEnum):
    """Which acceptance rule decides ``passed``."""

    PER_QUESTION = "per-question"
    PER_RUN = "per-run"


class Wording(StrEnum):
    """Where the asked text comes from."""

    #: The question of ``questions.yaml`` without its notes (:func:`asked_text`).
    YAML = "yaml"
    #: The query of the first probe of the question (own words, 120).
    PROBE = "probe"


@dataclass(frozen=True, slots=True)
class QuestionSource:
    """What the evaluation needs of a source of a test question: no text."""

    manifest_id: str
    #: The PDF page index of the locator; ``None`` without one.
    page: int | None
    #: ``"A"`` or ``"B"`` for a statement group of a contradiction, else ``None``.
    group: str | None


@dataclass(frozen=True, slots=True)
class Question:
    """A test question as the evaluation reads it."""

    id: int
    #: The text for people, with notes; asked only through :func:`asked_text`.
    question: str
    kind: QuestionKind
    key_facts: tuple[str, ...]
    sources: tuple[QuestionSource, ...] = ()
    #: Key fact -> equivalent spellings (``key_fact_alternatives``).
    alternatives: tuple[tuple[str, tuple[str, ...]], ...] = ()

    @property
    def is_control(self) -> bool:
        """Whether this is a control question (no evidence expected)."""
        return self.kind is QuestionKind.NO_EVIDENCE


@dataclass(frozen=True, slots=True)
class QuestionPlaces:
    """The expected places of one test question, from the probes of a probe list."""

    question: int
    probe_ids: tuple[str, ...]
    expected: tuple[ExpectedPlace, ...]
    #: Manifest id of another language edition -> id of the documented place.
    editions: tuple[tuple[str, str], ...]
    #: Query of the first probe of the question (for ``Wording.PROBE``).
    query: str


@dataclass(frozen=True, slots=True)
class Observed:
    """What one run of the answer service gave: structured events only, no text but the final."""

    sources: tuple[SourceRef, ...] = ()
    done: DoneEvent | None = None
    error: ErrorCode | None = None
    #: Seconds until the first ``delta``; ``None`` without one.
    first_token_seconds: float | None = None
    #: Seconds until ``done`` or ``error``.
    total_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class PlaceLabel:
    """An expected place as the report names it: manual and page or heading path."""

    manifest_id: str
    page: int | None
    heading_path: list[str] | None


@dataclass(frozen=True, slots=True)
class RunResult:
    """The verdict of one run of one question; numbers and identifiers only."""

    run: int
    verdict: Verdict
    status: str | None = None
    error_code: str | None = None
    #: Key facts of ``questions.yaml`` not found in the final text.
    missing_key_facts: list[str] = field(default_factory=list)
    #: Expected places hit by a cited source, and those not hit.
    found_places: list[PlaceLabel] = field(default_factory=list)
    missing_places: list[PlaceLabel] = field(default_factory=list)
    #: Statement groups hit by a cited source (contradiction only).
    groups_found: list[str] = field(default_factory=list)
    #: Smallest source number of a source on an expected place; ``None`` without one.
    evidence_rank: int | None = None
    #: Whether a source on an expected place is cited.
    evidence_cited: bool = False
    sources: int = 0
    #: Valid citations (``len(done.cited)``).
    valid_citations: int = 0
    #: Of them, those on an expected place.
    expected_citations: int = 0
    removed_sentences: int = 0
    first_token_seconds: float | None = None
    total_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class Spread:
    """Median, smallest and largest value; all ``None`` without values."""

    median: float | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, slots=True)
class QuestionResult:
    """The outcome of one test question over all its runs."""

    question_id: int
    kind: QuestionKind
    #: The final verdict after ``mode`` (the control question: ``control_mode``).
    verdict: Verdict
    runs: list[RunResult] = field(default_factory=list)
    correct_runs: int = 0
    run_count: int = 0
    evidence_rank_min: int | None = None
    evidence_rank_max: int | None = None
    first_token_seconds: Spread = field(default_factory=Spread)
    total_seconds: Spread = field(default_factory=Spread)
    #: Manifest ids of expected places whose file is not ingested.
    not_ingested: list[str] = field(default_factory=list)
    #: Filled in by a7 in the report of 128 and 138 (D5); always ``None`` here.
    verdict_a7: str | None = None

    @property
    def is_control(self) -> bool:
        """Whether this is the result of a control question."""
        return self.kind is QuestionKind.NO_EVIDENCE


@dataclass(frozen=True, slots=True)
class RunSummary:
    """One run over all questions (a line "x/10" per run, for 128 and 138)."""

    run: int
    #: Judged (not control) questions right in this run.
    correct_count: int
    #: Every control question right in this run (``True`` without one).
    control_ok: bool
    #: ``correct_count >= required`` and ``control_ok``.
    passed: bool


@dataclass(frozen=True, slots=True)
class Summary:
    """Both acceptance rules over all questions."""

    #: Questions that are not control questions (10 for M3).
    judged: int
    #: Judged questions whose final verdict is right.
    correct_count: int
    #: Every control question right by its final verdict.
    control_ok: bool
    passed_per_question: bool
    per_run: list[RunSummary]
    #: Runs that passed.
    runs_passed: int
    passed_per_run: bool
    #: The rule asked for decides.
    passed: bool
    valid_citations: int
    expected_citations: int
    #: ``expected_citations / valid_citations``; ``None`` without citations.
    expected_citation_share: float | None
    no_probe_count: int
    not_ingested_count: int


@dataclass(frozen=True, slots=True)
class Report:
    """The outcome of an evaluation."""

    measured: bool
    #: Why nothing was measured; ``None`` when measured.
    note: str | None
    ai_enabled: bool
    chat_model: str | None
    embed_model: str | None
    prompt_version: str
    temperature: float
    max_tokens: int
    reasoning_effort: str | None
    #: The settings ``TWOX_ANSWER_*`` (context of an answer, 125).
    answer_settings: dict[str, Any]
    runs: int
    mode: Mode
    control_mode: Mode
    rule: Rule
    wording: Wording
    literal: bool
    required: int
    questions: list[QuestionResult]
    #: ``None`` when nothing was measured.
    summary: Summary | None

    def as_dict(self) -> dict[str, Any]:
        """The report as plain data for JSON."""
        return asdict(self)


# --- Reading the test questions -------------------------------------------------


def _object(value: object, where: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise QuestionFormatError(f"{where}: expected an object")
    return value


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QuestionFormatError(f"{where}: expected non-empty text")
    return value


def _texts(value: object, where: str, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise QuestionFormatError(f"{where}: expected a non-empty list of texts")
    return tuple(_text(item, f"{where}[{index}]") for index, item in enumerate(value))


def _source(value: object, where: str) -> QuestionSource:
    data = _object(value, where)
    manifest_id = _text(data.get("manifest_id"), f"{where}.manifest_id")
    locator = _text(data.get("locator"), f"{where}.locator")
    supports = data.get("supports", "")
    if not isinstance(supports, str):
        raise QuestionFormatError(f"{where}.supports: expected text")
    page = _PDF_PAGE.search(locator)
    group = next(
        (name for name, prefix in STATEMENT_GROUPS.items() if supports.startswith(prefix)), None
    )
    return QuestionSource(
        manifest_id=manifest_id, page=None if page is None else int(page.group(1)), group=group
    )


def _alternatives(
    value: object, key_facts: Sequence[str], where: str
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if value is None:
        return ()
    data = _object(value, where)
    result: list[tuple[str, tuple[str, ...]]] = []
    for fact, spellings in data.items():
        if fact not in key_facts:
            raise QuestionFormatError(f"{where}.{fact}: not one of the key_facts")
        result.append((fact, _texts(spellings, f"{where}.{fact}", allow_empty=False)))
    return tuple(result)


def _question(value: object, where: str) -> Question:
    data = _object(value, where)
    question_id = data.get("id")
    if isinstance(question_id, bool) or not isinstance(question_id, int) or question_id < 1:
        raise QuestionFormatError(f"{where}.id: expected a whole number from 1")
    text = _text(data.get("question"), f"{where}.question")
    if not asked_text(text):
        raise QuestionFormatError(f"{where}.question: nothing is left to ask without the notes")
    try:
        kind = QuestionKind(str(data.get("kind")))
    except ValueError:
        known = ", ".join(kind.value for kind in QuestionKind)
        raise QuestionFormatError(f"{where}.kind: expected one of {known}") from None
    control = kind is QuestionKind.NO_EVIDENCE
    key_facts = _texts(data.get("key_facts"), f"{where}.key_facts", allow_empty=control)
    raw_sources = data.get("sources")
    if not isinstance(raw_sources, list):
        raise QuestionFormatError(f"{where}.sources: expected a list")
    sources = tuple(
        _source(source, f"{where}.sources[{index}]") for index, source in enumerate(raw_sources)
    )
    if kind is QuestionKind.CONTRADICTION:
        for name, prefix in STATEMENT_GROUPS.items():
            if not any(s.group == name and s.page is not None for s in sources):
                raise QuestionFormatError(
                    f"{where}.sources: a contradiction needs a source with a PDF page"
                    f" whose supports starts with {prefix!r}"
                )
    return Question(
        id=question_id,
        question=text,
        kind=kind,
        key_facts=key_facts,
        sources=sources,
        alternatives=_alternatives(
            data.get("key_fact_alternatives"), key_facts, f"{where}.key_fact_alternatives"
        ),
    )


def parse_questions(data: object) -> list[Question]:
    """The test questions (``questions`` only, not ``candidates``); :class:`QuestionFormatError`."""
    top = _object(data, "test questions")
    if top.get("schema_version") != SCHEMA_VERSION:
        raise QuestionFormatError(f"schema_version: expected {SCHEMA_VERSION}")
    questions = top.get("questions")
    if not isinstance(questions, list) or not questions:
        raise QuestionFormatError("questions: expected a non-empty list of questions")
    parsed = [_question(item, f"questions[{index}]") for index, item in enumerate(questions)]
    seen: set[int] = set()
    for question in parsed:
        if question.id in seen:
            raise QuestionFormatError(f"questions: the id {question.id} occurs twice")
        seen.add(question.id)
    return parsed


def load_questions(text: str) -> list[Question]:
    """The test questions in JSON text; :class:`QuestionFormatError` if invalid."""
    if not text.strip():
        raise QuestionFormatError("the input is empty; expected test questions in JSON")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise QuestionFormatError(
            f"not valid JSON (line {error.lineno}, column {error.colno}: {error.msg})"
        ) from None
    return parse_questions(data)


def asked_text(question: str) -> str:
    """``question`` without the notes for people; this text goes to the model.

    Removed are: a leading label up to the first colon when it starts with
    "Kontrollfrage"; every remark in round brackets; every sentence that
    starts with "Erwartet wird" (with the expected answer it may quote).
    White space is then collapsed.
    """
    text = _CONTROL_LABEL.sub("", question, count=1)
    text = _REMARK.sub("", text)
    text = _EXPECTED_SENTENCE.sub("", text)
    return _SPACES.sub(" ", text).strip()


def question_places(text: str) -> dict[int, QuestionPlaces]:
    """The expected places per test question of a probe list in JSON text.

    The list is read with :func:`~twox.search.evaluation.load_probes`
    (:class:`~twox.search.evaluation.ProbeFormatError` if invalid); the
    number of the test question comes from ``basis.question`` of each probe.
    Probes without it are ignored.
    """
    probes = load_probes(text)
    raw = json.loads(text)["probes"]
    grouped: dict[int, list[int]] = {}
    for index, item in enumerate(raw):
        basis = item.get("basis")
        number = basis.get("question") if isinstance(basis, dict) else None
        if isinstance(number, int) and not isinstance(number, bool):
            grouped.setdefault(number, []).append(index)
    result: dict[int, QuestionPlaces] = {}
    for number, indexes in grouped.items():
        chosen = [probes[index] for index in indexes]
        result[number] = QuestionPlaces(
            question=number,
            probe_ids=tuple(probe.id for probe in chosen),
            expected=tuple(dict.fromkeys(p for probe in chosen for p in probe.expected)),
            editions=tuple(dict.fromkeys(e for probe in chosen for e in probe.editions)),
            query=chosen[0].query,
        )
    return result


def contradiction_groups(
    question: Question, places: QuestionPlaces
) -> dict[str, tuple[ExpectedPlace, ...]]:
    """The expected places of the statement groups ``A`` and ``B`` of ``question``.

    A source of ``questions.yaml`` with a group and a PDF page gives that page
    of every probe place with the same ``manifest_id`` (its checksum) and of
    the places of its other language editions (E-61).
    """
    groups: dict[str, dict[ExpectedPlace, None]] = {name: {} for name in STATEMENT_GROUPS}
    for source in question.sources:
        if source.group is None or source.page is None:
            continue
        manifests = {source.manifest_id} | {
            edition for edition, documented in places.editions if documented == source.manifest_id
        }
        for place in places.expected:
            if place.manifest_id in manifests and place.heading_path is None:
                key = ExpectedPlace(
                    manifest_id=place.manifest_id,
                    sha256=place.sha256,
                    pages=frozenset({source.page}),
                    device=place.device,
                )
                groups[source.group][key] = None
    return {name: tuple(found) for name, found in groups.items()}


# --- Judging one run ----------------------------------------------------------------


def source_places(source: SourceRef) -> list[Place]:
    """Every place ``source`` is stored at, as the search measurement compares them."""
    return [
        Place(
            sha256=source.sha256,
            page_start=source.page_start,
            page_end=source.page_end,
            device_key=location.device_key,
            heading_path=tuple(source.heading_path),
            section_id=location.section_id,
            version_id=location.version_id,
        )
        for location in source.locations
    ]


def _hits(source: SourceRef, expected: Sequence[ExpectedPlace]) -> bool:
    return any(matching_place(place, expected) is not None for place in source_places(source))


def missing_key_facts(question: Question, text: str, *, literal: bool = False) -> list[str]:
    """The key facts of ``question`` found in ``text`` neither as written nor as an alternative.

    Both sides are normalised with :func:`twox.answers.citations.normalise_value`.
    """
    normalised = normalise_value(text)
    alternatives = {} if literal else dict(question.alternatives)
    return [
        fact
        for fact in question.key_facts
        if not any(
            normalise_value(spelling) in normalised
            for spelling in (fact, *alternatives.get(fact, ()))
        )
    ]


def judge_run(
    question: Question,
    places: QuestionPlaces | None,
    observed: Observed,
    *,
    run: int = 1,
    literal: bool = False,
) -> RunResult:
    """The verdict of one run of ``question`` (see the module docstring); pure.

    ``places`` are the expected places of the question (``None`` for a
    control question, or a fact or contradiction question without a probe,
    which gives ``no_probe``).
    """
    base: dict[str, Any] = {
        "run": run,
        "sources": len(observed.sources),
        "first_token_seconds": observed.first_token_seconds,
        "total_seconds": observed.total_seconds,
    }
    if not question.is_control and (places is None or not places.expected):
        return RunResult(verdict=Verdict.NO_PROBE, **base)
    done = observed.done
    if done is None:
        code = observed.error or ErrorCode.INTERNAL
        return RunResult(verdict=Verdict.ERROR, error_code=code.value, **base)
    base |= {
        "status": done.status.value,
        "valid_citations": len(done.cited),
        "removed_sentences": done.removed_sentences,
    }
    if question.is_control:
        right = done.status is AnswerStatus.NO_EVIDENCE and not done.cited
        return RunResult(verdict=Verdict.CORRECT if right else Verdict.WRONG, **base)

    assert places is not None
    expected = places.expected
    cited_numbers = set(done.cited)
    cited = [source for source in observed.sources if source.n in cited_numbers]
    on_expected = [source for source in cited if _hits(source, expected)]
    place_ranks = judge_places(
        SearchKind.COMBINED,
        [source_places(source) for source in cited],
        expected,
        0.0,
        editions=dict(places.editions),
    ).place_ranks
    labels = [
        (PlaceLabel(rank.manifest_id, rank.page, rank.heading_path), rank.first_rank is not None)
        for rank in place_ranks
    ]
    missing = missing_key_facts(question, done.final_text, literal=literal)
    groups_found: list[str] = []
    if question.kind is QuestionKind.CONTRADICTION:
        groups = contradiction_groups(question, places)
        groups_found = [
            name
            for name, group in groups.items()
            if group and any(_hits(source, group) for source in cited)
        ]
        right = (
            done.status is AnswerStatus.CONTRADICTION
            and not missing
            and len(groups_found) == len(STATEMENT_GROUPS)
        )
    else:
        right = done.status is AnswerStatus.ANSWERED and not missing and bool(on_expected)
    return RunResult(
        verdict=Verdict.CORRECT if right else Verdict.WRONG,
        missing_key_facts=missing,
        found_places=[label for label, found in labels if found],
        missing_places=[label for label, found in labels if not found],
        groups_found=groups_found,
        evidence_rank=min(
            (source.n for source in observed.sources if _hits(source, expected)), default=None
        ),
        evidence_cited=bool(on_expected),
        expected_citations=len(on_expected),
        **base,
    )


# --- Combining runs and questions ---------------------------------------------------


def combined(correct: int, total: int, mode: Mode) -> bool:
    """Whether ``correct`` of ``total`` is enough: more than half, or all with ``strict``."""
    if total < 1:
        return False
    return correct * 2 > total if mode is Mode.MAJORITY else correct == total


def _spread(values: Iterable[float | None]) -> Spread:
    present = [value for value in values if value is not None]
    if not present:
        return Spread()
    return Spread(statistics.median(present), min(present), max(present))


def aggregate(
    question: Question,
    runs: Sequence[RunResult],
    *,
    mode: Mode = Mode.MAJORITY,
    control_mode: Mode = Mode.STRICT,
) -> QuestionResult:
    """The final verdict of ``question`` over its ``runs``; pure.

    Right by ``mode`` (the control question by ``control_mode``); otherwise
    ``error`` when every run failed with an error, else ``wrong``.
    """
    correct = sum(run.verdict is Verdict.CORRECT for run in runs)
    if combined(correct, len(runs), control_mode if question.is_control else mode):
        verdict = Verdict.CORRECT
    elif runs and all(run.verdict is Verdict.ERROR for run in runs):
        verdict = Verdict.ERROR
    else:
        verdict = Verdict.WRONG
    ranks = [run.evidence_rank for run in runs if run.evidence_rank is not None]
    return QuestionResult(
        question_id=question.id,
        kind=question.kind,
        verdict=verdict,
        runs=list(runs),
        correct_runs=correct,
        run_count=len(runs),
        evidence_rank_min=min(ranks, default=None),
        evidence_rank_max=max(ranks, default=None),
        first_token_seconds=_spread(run.first_token_seconds for run in runs),
        total_seconds=_spread(run.total_seconds for run in runs),
    )


def not_asked(question: Question, verdict: Verdict, missing: Sequence[str] = ()) -> QuestionResult:
    """The result of a question that was not asked (``no_probe``, ``not_ingested``)."""
    return QuestionResult(
        question_id=question.id, kind=question.kind, verdict=verdict, not_ingested=list(missing)
    )


def _run_correct(result: QuestionResult, run: int) -> bool:
    return any(item.run == run and item.verdict is Verdict.CORRECT for item in result.runs)


def summarise(
    results: Sequence[QuestionResult],
    *,
    runs: int,
    mode: Mode = Mode.MAJORITY,
    rule: Rule = Rule.PER_QUESTION,
    required: int = REQUIRED_CORRECT,
) -> Summary:
    """Both acceptance rules over ``results`` of ``runs`` runs; pure."""
    judged = [result for result in results if not result.is_control]
    controls = [result for result in results if result.is_control]
    correct_count = sum(result.verdict is Verdict.CORRECT for result in judged)
    control_ok = all(result.verdict is Verdict.CORRECT for result in controls)
    per_run: list[RunSummary] = []
    for run in range(1, runs + 1):
        count = sum(_run_correct(result, run) for result in judged)
        run_control = all(_run_correct(result, run) for result in controls)
        per_run.append(
            RunSummary(
                run=run,
                correct_count=count,
                control_ok=run_control,
                passed=count >= required and run_control,
            )
        )
    runs_passed = sum(item.passed for item in per_run)
    passed_per_question = correct_count >= required and control_ok
    passed_per_run = combined(runs_passed, runs, mode)
    all_runs = [run for result in results for run in result.runs]
    valid = sum(run.valid_citations for run in all_runs)
    on_expected = sum(run.expected_citations for run in all_runs)
    return Summary(
        judged=len(judged),
        correct_count=correct_count,
        control_ok=control_ok,
        passed_per_question=passed_per_question,
        per_run=per_run,
        runs_passed=runs_passed,
        passed_per_run=passed_per_run,
        passed=passed_per_question if rule is Rule.PER_QUESTION else passed_per_run,
        valid_citations=valid,
        expected_citations=on_expected,
        expected_citation_share=on_expected / valid if valid else None,
        no_probe_count=sum(result.verdict is Verdict.NO_PROBE for result in results),
        not_ingested_count=sum(result.verdict is Verdict.NOT_INGESTED for result in results),
    )


# --- Running the questions ----------------------------------------------------------


class AnswerFunction(Protocol):
    """The signature of :func:`twox.answers.service.answer` that the evaluation uses."""

    def __call__(
        self, question: str, *, device_ids: Sequence[int] = (), plant_ids: Sequence[int] = ()
    ) -> Iterator[AnswerEvent]: ...


def observe(answer: AnswerFunction, text: str, clock: Callable[[], float]) -> Observed:
    """Ask ``text`` once, without restriction to devices or plants, and read the events.

    The stream is closed as soon as ``done`` or ``error`` has come (or on any
    failure). An exception of ``answer`` itself counts as ``error(internal)``;
    only its type name is logged.
    """
    started = clock()
    sources: tuple[SourceRef, ...] = ()
    first_token: float | None = None
    done: DoneEvent | None = None
    error: ErrorCode | None = None
    events: Iterator[AnswerEvent] | None = None
    try:
        events = answer(text, device_ids=(), plant_ids=())
        for event in events:
            match event:
                case SourcesEvent():
                    sources = tuple(event.sources)
                case DeltaEvent():
                    if first_token is None:
                        first_token = clock() - started
                case DoneEvent():
                    done = event
                    break
                case ErrorEvent():
                    error = event.code
                    break
    except Exception as failure:
        logger.warning("Evaluation: the answer service failed: %s", type(failure).__name__)
        error = ErrorCode.INTERNAL
    finally:
        close = getattr(events, "close", None)
        if callable(close):
            close()
    if done is None and error is None:
        error = ErrorCode.INTERNAL
    return Observed(
        sources=sources,
        done=done,
        error=error,
        first_token_seconds=first_token,
        total_seconds=clock() - started,
    )


def _answer_settings() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name in sorted(dir(settings)):
        if name.startswith("TWOX_ANSWER_"):
            value = getattr(settings, name)
            values[name] = value if isinstance(value, bool | int | float | str) else str(value)
    return values


def _expected_checksums(
    questions: Sequence[Question], places: Mapping[int, QuestionPlaces]
) -> set[str]:
    return {
        place.sha256
        for question in questions
        if not question.is_control and question.id in places
        for place in places[question.id].expected
    }


def evaluate(
    questions: Sequence[Question],
    places: Mapping[int, QuestionPlaces],
    *,
    runs: int = 1,
    answer: AnswerFunction | None = None,
    clock: Callable[[], float] = time.perf_counter,
    mode: Mode = Mode.MAJORITY,
    control_mode: Mode = Mode.STRICT,
    rule: Rule = Rule.PER_QUESTION,
    wording: Wording = Wording.YAML,
    literal: bool = False,
    required: int = REQUIRED_CORRECT,
    ingested: Callable[[Iterable[str]], set[str]] = ingested_checksums,
) -> Report:
    """Ask every question ``runs`` times through ``answer`` and judge the answers.

    ``answer`` defaults to :func:`twox.answers.service.answer`; ``ingested``
    returns those of the given checksums that are ingested (by default
    :func:`~twox.search.evaluation.ingested_checksums`). Both are injectable
    so that tests need neither a database nor a model. The runs go one after
    the other over all questions (run 1 for every question, then run 2, ...).
    With the AI features off nothing is asked and the report is "not measured".
    """
    if runs < 1:
        raise ValueError("runs must be at least 1")
    ai_enabled = bool(settings.TWOX_AI_ENABLED)
    header: dict[str, Any] = {
        "ai_enabled": ai_enabled,
        "chat_model": settings.TWOX_CHAT_MODEL or None,
        "embed_model": str(settings.TWOX_EMBED_MODEL) if ai_enabled else None,
        "prompt_version": prompt.prompt_version(),
        "temperature": float(settings.TWOX_CHAT_TEMPERATURE),
        "max_tokens": int(settings.TWOX_CHAT_MAX_TOKENS),
        "reasoning_effort": settings.TWOX_CHAT_REASONING_EFFORT,
        "answer_settings": _answer_settings(),
        "runs": runs,
        "mode": mode,
        "control_mode": control_mode,
        "rule": rule,
        "wording": wording,
        "literal": literal,
        "required": required,
    }
    if not ai_enabled:
        return Report(measured=False, note=NOT_MEASURED_NOTE, questions=[], summary=None, **header)

    if answer is None:
        answer = service.answer
    present = ingested(_expected_checksums(questions, places))
    finished: dict[int, QuestionResult] = {}
    asked: list[tuple[Question, QuestionPlaces | None, str]] = []
    for question in questions:
        own = places.get(question.id)
        if not question.is_control:
            if own is None or not own.expected:
                finished[question.id] = not_asked(question, Verdict.NO_PROBE)
                continue
            if not any(place.sha256 in present for place in own.expected):
                missing = sorted({place.manifest_id for place in own.expected})
                finished[question.id] = not_asked(question, Verdict.NOT_INGESTED, missing)
                continue
        if wording is Wording.PROBE:
            if own is None:
                finished[question.id] = not_asked(question, Verdict.NO_PROBE)
                continue
            text = own.query
        else:
            text = asked_text(question.question)
        asked.append((question, own, text))

    collected: dict[int, list[RunResult]] = {question.id: [] for question, _, _ in asked}
    model = settings.TWOX_CHAT_MODEL or "-"
    for run in range(1, runs + 1):
        for question, own, text in asked:
            outcome = judge_run(
                question, own, observe(answer, text, clock), run=run, literal=literal
            )
            collected[question.id].append(outcome)
            logger.info(
                "Evaluation run: question=%d run=%d verdict=%s result=%s model=%s"
                " duration_ms=%d sources=%d",
                question.id,
                run,
                outcome.verdict.value,
                outcome.error_code or outcome.status or "-",
                model,
                round(outcome.total_seconds * 1000),
                outcome.sources,
            )
    for question, own, _ in asked:
        result = aggregate(question, collected[question.id], mode=mode, control_mode=control_mode)
        if own is not None and not question.is_control:
            partly = {place.manifest_id for place in own.expected if place.sha256 not in present}
            result = replace(result, not_ingested=sorted(partly))
        finished[question.id] = result
    results = [finished[question.id] for question in questions]
    return Report(
        measured=True,
        note=None,
        questions=results,
        summary=summarise(results, runs=runs, mode=mode, rule=rule, required=required),
        **header,
    )


# --- Output ---------------------------------------------------------------------------


def _row(cells: Sequence[str], widths: Sequence[int]) -> str:
    return "  ".join(cell.ljust(width) for cell, width in zip(cells, widths, strict=True)).rstrip()


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    widths = [max(len(row[column]) for row in [header, *rows]) for column in range(len(header))]
    return [_row(header, widths), *(_row(row, widths) for row in rows)]


def _ms(seconds: float | None) -> str:
    return "-" if seconds is None else f"{seconds * 1000:.0f}"


def _spread_text(spread: Spread) -> str:
    if spread.median is None:
        return "-"
    return f"{_ms(spread.median)} ({_ms(spread.minimum)}-{_ms(spread.maximum)})"


def _optional(value: int | None) -> str:
    return "-" if value is None else str(value)


def _rank_range(result: QuestionResult) -> str:
    low, high = result.evidence_rank_min, result.evidence_rank_max
    if low is None:
        return "-"
    return str(low) if low == high else f"{low}-{high}"


def _label(label: PlaceLabel) -> str:
    if label.heading_path is not None:
        return f"{label.manifest_id}: {' > '.join(label.heading_path)}"
    return f"{label.manifest_id} p. {label.page}"


def _yes(value: bool) -> str:
    return "yes" if value else "no"


def _header_lines(report: Report) -> list[str]:
    ai = "on" if report.ai_enabled else "off"
    facts = "literal" if report.literal else "with alternatives"
    answer_settings = "; ".join(f"{name} {value}" for name, value in report.answer_settings.items())
    return [
        f"Answer evaluation: AI features {ai}; runs {report.runs}; mode {report.mode};"
        f" control question {report.control_mode}; rule {report.rule};"
        f" wording {report.wording}; key facts {facts}; required {report.required}",
        f"Chat model {report.chat_model or '-'}; embedding model {report.embed_model or '-'};"
        f" prompt version {report.prompt_version}; temperature {report.temperature:g};"
        f" max_tokens {report.max_tokens}; reasoning effort {report.reasoning_effort or '-'}",
        answer_settings or "No TWOX_ANSWER_* settings",
    ]


def _question_rows(report: Report) -> list[list[str]]:
    rows = []
    for result in report.questions:
        runs = f"{result.correct_runs}/{result.run_count}" if result.run_count else "-"
        rows.append(
            [
                str(result.question_id),
                result.kind,
                result.verdict,
                runs,
                _rank_range(result),
                _spread_text(result.first_token_seconds),
                _spread_text(result.total_seconds),
                ", ".join(result.not_ingested),
                result.verdict_a7 or "",
            ]
        )
    return rows


def _run_rows(report: Report) -> list[list[str]]:
    rows = []
    for result in report.questions:
        for run in result.runs:
            rows.append(
                [
                    str(result.question_id),
                    str(run.run),
                    run.verdict,
                    run.error_code or run.status or "-",
                    str(run.sources),
                    str(run.valid_citations),
                    str(run.expected_citations),
                    str(run.removed_sentences),
                    _optional(run.evidence_rank),
                    _yes(run.evidence_cited),
                    _ms(run.first_token_seconds),
                    _ms(run.total_seconds),
                    ", ".join(run.groups_found) or "-",
                    "; ".join(run.missing_key_facts) or "-",
                    "; ".join(_label(label) for label in run.missing_places) or "-",
                ]
            )
    return rows


def format_table(report: Report) -> str:
    """The report as text: header, one row per question, the runs, the totals."""
    lines = _header_lines(report)
    if not report.measured or report.summary is None:
        lines += ["", f"{report.note or NOT_MEASURED_NOTE}."]
        return "\n".join(lines) + "\n"
    summary = report.summary
    lines.append("")
    lines += _table(
        [
            "question",
            "kind",
            "verdict",
            "right runs",
            "evidence rank",
            "first token ms (min-max)",
            "total ms (min-max)",
            "not ingested",
            "verdict a7",
        ],
        _question_rows(report),
    )
    run_rows = _run_rows(report)
    if run_rows:
        lines += [
            "",
            "Runs:",
            *_table(
                [
                    "question",
                    "run",
                    "verdict",
                    "status",
                    "sources",
                    "cited",
                    "on expected",
                    "removed",
                    "evidence rank",
                    "evidence cited",
                    "first token ms",
                    "total ms",
                    "groups",
                    "missing key facts",
                    "missing places",
                ],
                run_rows,
            ),
        ]
    lines += [
        "",
        "Per run:",
        *_table(
            ["run", "right", "control question", "passed"],
            [
                [
                    str(item.run),
                    f"{item.correct_count}/{summary.judged}",
                    "ok" if item.control_ok else "not ok",
                    _yes(item.passed),
                ]
                for item in summary.per_run
            ],
        ),
        "",
        f"Per question ({report.mode}): {summary.correct_count}/{summary.judged} right,"
        f" control question {'ok' if summary.control_ok else 'not ok'}"
        f" ({report.control_mode}); passed: {_yes(summary.passed_per_question)}",
        f"Per run ({report.mode}): {summary.runs_passed} of {report.runs} runs passed;"
        f" passed: {_yes(summary.passed_per_run)}",
        f"Rule {report.rule}: {'PASSED' if summary.passed else 'NOT PASSED'}",
    ]
    share = summary.expected_citation_share
    lines += [
        f"Valid citations: {summary.valid_citations}, of them on an expected place:"
        f" {summary.expected_citations}"
        f" ({'-' if share is None else f'{share:.3f}'})",
        f"No probe: {summary.no_probe_count}; not ingested: {summary.not_ingested_count}",
    ]
    return "\n".join(lines) + "\n"


def format_json(report: Report) -> str:
    """The report as JSON."""
    return json.dumps(report.as_dict(), ensure_ascii=False, indent=2) + "\n"
