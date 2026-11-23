"""Acceptance of M3 with the answer service (docs/ROADMAP.md, M3).

Condition: at least 8 of 10 test questions right; the control question without
an invented answer; question and answer, sources shown, limit to a device. The
browser parts are ``web/e2e/answer.spec.ts`` (CI, a stream written by the test)
and ``web/e2e/m3-acceptance.spec.ts`` (local); the run with the real manuals and
the chat model belongs to the acceptance run of the coordination (work order 138).

Two parts:

* The CI part checks :func:`judge_report`, the rule this test applies to the
  JSON report of ``evaluate_answers`` (work order 127), with reports written
  here, and :func:`run_conditions`. It needs no database and no network.
* The local part runs only with ``TWOX_M3_LOCAL=1`` in the test environment with
  the ingested manuals and the chat model. It is deliberately not a
  ``django_db`` test: pytest-django would give it an empty test database
  without manuals. It starts ``python manage.py evaluate_answers --json`` as a
  subprocess in the backend directory with the inherited environment, so the
  command uses the configured database of the test environment, like
  ``docker compose exec -T api python manage.py evaluate_search`` (work order
  060). ``backend-dev`` has the environment of ``api`` and reaches Ollama on the
  host through ``host.docker.internal``.

Run conditions, set only with ``docker compose run -e ...`` and never in
``.env``: ``TWOX_M3_RUNS`` (runs per question, default 3), ``TWOX_M3_MODE``
(``majority`` or ``strict``, default ``majority``, D5) and ``TWOX_M3_MINIMUM``
(right questions of the 10, default 8). The control question must be right in
every run. Messages name identifiers, pages, verdicts and the key facts of
``questions.yaml`` only, never a question, an answer or a section text (D7).
"""

import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings

LOCAL = os.environ.get("TWOX_M3_LOCAL") == "1"
LOCAL_REASON = (
    "Local part: runs only with TWOX_M3_LOCAL=1 in the test environment with the manuals"
    " and the chat model (acceptance run, work order 138)."
)
#: The directory of ``manage.py`` (``/app`` in ``backend-dev``).
BACKEND_DIR = Path(__file__).resolve().parents[2]
#: Test questions judged for the acceptance (questions 1 to 10; 11 is the control question).
JUDGED_QUESTIONS = 10
MODES = ("majority", "strict")
CONTROL_KIND = "no-evidence"
_WHOLE_NUMBER = re.compile(r"[0-9]+")


class ConditionError(ValueError):
    """An invalid value of ``TWOX_M3_RUNS``, ``TWOX_M3_MODE`` or ``TWOX_M3_MINIMUM``."""


@dataclass(frozen=True, slots=True)
class RunConditions:
    """How the local part runs ``evaluate_answers`` and what it requires."""

    runs: int = 3
    mode: str = "majority"
    minimum: int = 8


def _whole_number(
    environ: Mapping[str, str], name: str, default: int, lowest: int, highest: int | None
) -> int:
    text = environ.get(name, "").strip()
    if text == "":
        return default
    upper = "" if highest is None else f" to {highest}"
    if _WHOLE_NUMBER.fullmatch(text) is None:
        raise ConditionError(
            f"Invalid {name}={text!r}: expected a whole number from {lowest}{upper}."
        )
    value = int(text)
    if value < lowest or (highest is not None and value > highest):
        raise ConditionError(
            f"Invalid {name}={text!r}: expected a whole number from {lowest}{upper}."
        )
    return value


def run_conditions(environ: Mapping[str, str]) -> RunConditions:
    """The run conditions from ``environ``; :class:`ConditionError` for an invalid value."""
    default = RunConditions()
    runs = _whole_number(environ, "TWOX_M3_RUNS", default.runs, 1, None)
    mode = environ.get("TWOX_M3_MODE", "").strip() or default.mode
    if mode not in MODES:
        raise ConditionError(f"Invalid TWOX_M3_MODE={mode!r}: expected majority or strict.")
    minimum = _whole_number(environ, "TWOX_M3_MINIMUM", default.minimum, 1, JUDGED_QUESTIONS)
    return RunConditions(runs=runs, mode=mode, minimum=minimum)


# --- Judging the report of evaluate_answers ---------------------------------------


def _items(value: object) -> list[Mapping[str, Any]]:
    """The objects of a JSON list; anything else gives an empty list."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _is_evidence(place: Mapping[str, Any]) -> bool:
    """A place names its file and a page, or for Markdown its heading path."""
    headings = place.get("heading_path")
    has_headings = isinstance(headings, list) and any(str(item).strip() for item in headings)
    return bool(place.get("manifest_id")) and (isinstance(place.get("page"), int) or has_headings)


def _place_label(place: Mapping[str, Any]) -> str:
    """A place as the report of 127 names it: manifest id and page or heading path."""
    manifest_id = str(place.get("manifest_id") or "?")
    page = place.get("page")
    if isinstance(page, int):
        return f"{manifest_id} p. {page}"
    headings = place.get("heading_path")
    if isinstance(headings, list) and headings:
        return f"{manifest_id} > {' > '.join(map(str, headings))}"
    return manifest_id


def _outcome(run: Mapping[str, Any]) -> str:
    return str(run.get("status") or run.get("error_code") or "-")


def judge_report(report: Mapping[str, object], *, minimum: int) -> list[str]:
    """The violations of the acceptance rule in ``report``; empty when M3 is met.

    ``report`` is the JSON report of ``evaluate_answers --json`` (work order
    127). Required are: the report was measured; at least ``minimum`` of the
    judged questions are right by their final verdict; the control question
    was asked and is right in every run (status ``no_evidence``, no valid
    citation); every run judged right has a valid citation and a cited place
    with file and page, or file and heading path. Pure.
    """
    if report.get("measured") is not True:
        note = report.get("note") or "no note"
        return [f"evaluate_answers measured nothing ({note})."]
    questions = _items(report.get("questions"))
    judged = [question for question in questions if question.get("kind") != CONTROL_KIND]
    controls = [question for question in questions if question.get("kind") == CONTROL_KIND]
    violations: list[str] = []

    right = sum(question.get("verdict") == "correct" for question in judged)
    if right < minimum:
        violations.append(
            f"{right}/{len(judged)} test questions right; at least {minimum} required."
        )

    control_runs = [(control, run) for control in controls for run in _items(control.get("runs"))]
    if not control_runs:
        violations.append("The control question was not asked.")
    for control, run in control_runs:
        citations = run.get("valid_citations")
        if run.get("verdict") != "correct" or run.get("status") != "no_evidence" or citations != 0:
            violations.append(
                f"Control question {control.get('question_id')}, run {run.get('run')}:"
                f" {_outcome(run)} with {citations} valid citations;"
                " expected no_evidence without citations."
            )

    for question in judged:
        for run in _items(question.get("runs")):
            if run.get("verdict") != "correct":
                continue
            citations = run.get("valid_citations")
            places = [place for place in _items(run.get("found_places")) if _is_evidence(place)]
            if not isinstance(citations, int) or citations < 1 or not places:
                violations.append(
                    f"Question {question.get('question_id')}, run {run.get('run')}: judged right"
                    " without a valid citation of a place with file and page or heading path."
                )
    return violations


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def question_lines(report: Mapping[str, object]) -> list[str]:
    """One line per question: verdict, right runs, missing key facts and places (identifiers)."""
    lines: list[str] = []
    for question in _items(report.get("questions")):
        runs = _items(question.get("runs"))
        right_runs = f"{question.get('correct_runs')}/{question.get('run_count')}"
        missing_facts = _unique(
            [str(fact) for run in runs for fact in run.get("missing_key_facts") or []]
        )
        missing_places = _unique(
            [_place_label(place) for run in runs for place in _items(run.get("missing_places"))]
        )
        outcomes = ", ".join(f"run {run.get('run')}: {_outcome(run)}" for run in runs)
        line = (
            f"question {question.get('question_id')} ({question.get('kind')}):"
            f" {question.get('verdict')}, {right_runs} runs right"
        )
        if outcomes:
            line += f" ({outcomes})"
        if missing_facts:
            line += f"; missing key facts: {', '.join(missing_facts)}"
        if missing_places:
            line += f"; missing places: {', '.join(missing_places)}"
        not_ingested = question.get("not_ingested")
        if isinstance(not_ingested, list) and not_ingested:
            line += f"; not ingested: {', '.join(map(str, not_ingested))}"
        lines.append(line)
    return lines


def failure_message(report: Mapping[str, object], violations: Sequence[str]) -> str:
    """The message of a failed acceptance: the violations, then every question."""
    parts = ["M3 acceptance not met:"]
    parts += [f"- {violation}" for violation in violations]
    lines = question_lines(report)
    if lines:
        parts.append("Per question:")
        parts += [f"  {line}" for line in lines]
    return "\n".join(parts)


# --- Local part ------------------------------------------------------------------


def evaluate_answers_command(conditions: RunConditions) -> list[str]:
    """The command line of the local part."""
    return [
        sys.executable,
        "manage.py",
        "evaluate_answers",
        "--json",
        "--runs",
        str(conditions.runs),
        "--mode",
        conditions.mode,
    ]


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else "no output"


def run_evaluate_answers(conditions: RunConditions) -> Mapping[str, object]:
    """Runs ``evaluate_answers --json`` against the configured database; fails on an error."""
    completed = subprocess.run(
        evaluate_answers_command(conditions),
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        # The last line only: a CommandError is one line; a traceback is not repeated here.
        pytest.fail(
            f"evaluate_answers ended with exit code {completed.returncode}:"
            f" {_last_line(completed.stderr)}",
            pytrace=False,
        )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        pytest.fail("evaluate_answers --json printed no JSON report.", pytrace=False)
    if not isinstance(report, dict):
        pytest.fail("evaluate_answers --json printed no JSON object.", pytrace=False)
    return report


@pytest.mark.skipif(not LOCAL, reason=LOCAL_REASON)
def test_m3_acceptance_with_the_chat_model() -> None:
    try:
        conditions = run_conditions(os.environ)
    except ConditionError as error:
        pytest.fail(str(error), pytrace=False)
    # The acceptance counts with the AI features on only (D5, D10): fail, never skip.
    if not settings.TWOX_AI_ENABLED:
        pytest.fail(
            "The AI features are off (TWOX_AI_ENABLED): the acceptance of M3 needs them on"
            " (D5, D10).",
            pytrace=False,
        )
    if not str(settings.TWOX_CHAT_MODEL or "").strip():
        pytest.fail(
            "No chat model configured (TWOX_CHAT_MODEL is empty): the acceptance of M3 needs"
            " the chat model (D5, D10).",
            pytrace=False,
        )

    report = run_evaluate_answers(conditions)

    assert report.get("runs") == conditions.runs, "evaluate_answers ran another number of runs"
    assert report.get("mode") == conditions.mode, "evaluate_answers used another mode"
    violations = judge_report(report, minimum=conditions.minimum)
    if violations:
        pytest.fail(failure_message(report, violations), pytrace=False)


# --- CI part: the rule with reports written here ----------------------------------


def _run(
    run: int = 1,
    *,
    verdict: str = "correct",
    status: str | None = "answered",
    citations: int = 1,
    found: Sequence[Mapping[str, object]] = (
        {"manifest_id": "m-a", "page": 3, "heading_path": None},
    ),
    missing_facts: Sequence[str] = (),
    missing_places: Sequence[Mapping[str, object]] = (),
    error_code: str | None = None,
) -> dict[str, object]:
    return {
        "run": run,
        "verdict": verdict,
        "status": status,
        "error_code": error_code,
        "missing_key_facts": list(missing_facts),
        "found_places": [dict(place) for place in found],
        "missing_places": [dict(place) for place in missing_places],
        "valid_citations": citations,
    }


def _question(
    question_id: int, runs: Sequence[dict[str, object]], *, kind: str = "fact"
) -> dict[str, object]:
    correct = sum(run["verdict"] == "correct" for run in runs)
    return {
        "question_id": question_id,
        "kind": kind,
        "verdict": "correct" if correct * 2 > len(runs) else "wrong",
        "runs": list(runs),
        "correct_runs": correct,
        "run_count": len(runs),
        "not_ingested": [],
    }


def _wrong_runs(count: int = 3) -> list[dict[str, object]]:
    return [
        _run(
            run,
            verdict="wrong",
            citations=0,
            found=(),
            missing_facts=("12 test units",),
            missing_places=({"manifest_id": "m-b", "page": 7, "heading_path": None},),
        )
        for run in range(1, count + 1)
    ]


def _right_runs(count: int = 3) -> list[dict[str, object]]:
    return [_run(run) for run in range(1, count + 1)]


def _control(runs: Sequence[dict[str, object]] | None = None) -> dict[str, object]:
    if runs is None:
        runs = [_run(run, status="no_evidence", citations=0, found=()) for run in range(1, 4)]
    return _question(11, runs, kind=CONTROL_KIND)


def _report(right: int, *, control: dict[str, object] | None = None) -> dict[str, object]:
    questions = [
        _question(number, _right_runs() if number <= right else _wrong_runs())
        for number in range(1, JUDGED_QUESTIONS + 1)
    ]
    questions.append(_control() if control is None else control)
    return {"measured": True, "note": None, "runs": 3, "mode": "majority", "questions": questions}


def test_eight_of_ten_with_the_control_question_passes() -> None:
    assert judge_report(_report(8), minimum=8) == []
    assert judge_report(_report(10), minimum=8) == []


def test_seven_of_ten_fails() -> None:
    report = _report(7)

    violations = judge_report(report, minimum=8)

    assert violations == ["7/10 test questions right; at least 8 required."]
    message = failure_message(report, violations)
    # Per question: verdict, missing key facts and places, as identifiers.
    assert (
        "question 8 (fact): wrong, 0/3 runs right (run 1: answered, run 2: answered,"
        " run 3: answered); missing key facts: 12 test units; missing places: m-b p. 7"
    ) in message
    assert "question 1 (fact): correct, 3/3 runs right" in message


def test_the_minimum_comes_from_the_run_conditions() -> None:
    assert judge_report(_report(7), minimum=7) == []
    assert judge_report(_report(9), minimum=10) == [
        "9/10 test questions right; at least 10 required."
    ]


def test_a_control_question_with_a_citation_fails_in_any_run() -> None:
    runs = [_run(run, status="no_evidence", citations=0, found=()) for run in range(1, 4)]
    # Majority would still count the question as right; the acceptance needs every run.
    runs[1] = _run(2, verdict="wrong", status="answered", citations=1)
    report = _report(10, control=_control(runs))

    assert judge_report(report, minimum=8) == [
        "Control question 11, run 2: answered with 1 valid citations;"
        " expected no_evidence without citations."
    ]


def test_a_control_question_with_an_error_or_not_asked_fails() -> None:
    errored = _control(
        [_run(1, verdict="error", status=None, citations=0, found=(), error_code="timeout")]
    )
    assert judge_report(_report(10, control=errored), minimum=8) == [
        "Control question 11, run 1: timeout with 0 valid citations;"
        " expected no_evidence without citations."
    ]

    not_asked = _control([])
    assert judge_report(_report(10, control=not_asked), minimum=8) == [
        "The control question was not asked."
    ]


def test_a_right_answer_without_a_page_fails() -> None:
    report = _report(10)
    questions = _items(report["questions"])
    without_page = _run(2, found=({"manifest_id": "m-a", "page": None, "heading_path": []},))
    questions[3]["runs"][1] = without_page

    assert judge_report(report, minimum=8) == [
        "Question 4, run 2: judged right without a valid citation of a place with file and page"
        " or heading path."
    ]


def test_a_markdown_place_counts_with_its_heading_path() -> None:
    report = _report(10)
    questions = _items(report["questions"])
    markdown = _run(1, found=({"manifest_id": "m-c", "page": None, "heading_path": ["Setup"]},))
    questions[0]["runs"][0] = markdown

    assert judge_report(report, minimum=8) == []


def test_a_right_answer_without_a_valid_citation_fails() -> None:
    report = _report(10)
    questions = _items(report["questions"])
    questions[5]["runs"][2] = _run(3, citations=0)

    assert judge_report(report, minimum=8) == [
        "Question 6, run 3: judged right without a valid citation of a place with file and page"
        " or heading path."
    ]


def test_an_unmeasured_report_fails() -> None:
    report = {"measured": False, "note": "AI features not enabled: not measured", "questions": []}

    assert judge_report(report, minimum=8) == [
        "evaluate_answers measured nothing (AI features not enabled: not measured)."
    ]


def test_run_conditions_defaults_and_values() -> None:
    assert run_conditions({}) == RunConditions(runs=3, mode="majority", minimum=8)
    assert run_conditions(
        {"TWOX_M3_RUNS": "1", "TWOX_M3_MODE": "strict", "TWOX_M3_MINIMUM": "10"}
    ) == RunConditions(runs=1, mode="strict", minimum=10)
    assert run_conditions({"TWOX_M3_RUNS": " ", "TWOX_M3_MODE": ""}) == RunConditions()


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("TWOX_M3_RUNS", "0", "Invalid TWOX_M3_RUNS='0': expected a whole number from 1."),
        ("TWOX_M3_RUNS", "three", "Invalid TWOX_M3_RUNS='three': expected a whole number from 1."),
        ("TWOX_M3_MODE", "most", "Invalid TWOX_M3_MODE='most': expected majority or strict."),
        (
            "TWOX_M3_MINIMUM",
            "11",
            "Invalid TWOX_M3_MINIMUM='11': expected a whole number from 1 to 10.",
        ),
        (
            "TWOX_M3_MINIMUM",
            "-1",
            "Invalid TWOX_M3_MINIMUM='-1': expected a whole number from 1 to 10.",
        ),
    ],
)
def test_invalid_run_conditions_fail_with_a_message(name: str, value: str, message: str) -> None:
    with pytest.raises(ConditionError) as error:
        run_conditions({name: value})
    assert str(error.value) == message


def test_the_command_uses_the_run_conditions() -> None:
    command = evaluate_answers_command(RunConditions(runs=5, mode="strict", minimum=8))

    assert command[1:] == [
        "manage.py",
        "evaluate_answers",
        "--json",
        "--runs",
        "5",
        "--mode",
        "strict",
    ]
    assert (BACKEND_DIR / "manage.py").is_file()
