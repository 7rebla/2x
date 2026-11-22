"""The probe list of M3 refers only to what the test factory documents (120).

``twox/search/probes/m3.json`` holds one probe per test question of
``testfactory/questions.yaml`` (questions 3, 7 and 10 twice, in other words),
a control probe for question 11 and none for question 8 yet. Every place is
checked against ``testfactory/manifest.yaml``:

* a place by pages is a file of the manifest (``kind: file``) with its
  checksum, and its pages are exactly the PDF pages of the question's sources;
* a place by heading path (a Markdown file of a repository, E-55) belongs to
  a repository archive of the manifest (``kind: git-archive``), whose entry
  has no checksum per file, so only the format of the checksum is checked;
  its ``path`` is the file of a source of the question (the locator before
  the comma). Work order 136 adds the probe for question 8 this way.

The checks are functions that return the problems found, so that the tests
below can also show them on probe lists written for the test.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from tests.search.test_probes import (
    APS_EDITIONS,
    MANIFEST,
    QUESTIONS,
    documented_places,
    other_editions,
    pages_of_question,
    read_json,
)
from twox.search.evaluation import CONTROL_PREFIX, PROBE_LISTS, load_probes

PROBES = PROBE_LISTS / "m3.json"
#: Keys a probe of the list may have.
PROBE_KEYS = {"id", "query", "expected", "basis", "notes"}
#: Test questions with a probe, and those with two probes in different words.
COVERED_QUESTIONS = {1, 2, 3, 4, 5, 6, 7, 9, 10}
TWICE = {3, 7, 10}
#: The control question (no evidence) and the question without a probe for now.
CONTROL_QUESTION = 11
NOT_MEASURABLE_QUESTION = 8
SHA256 = re.compile(r"[0-9a-f]{64}")
#: Checksum of aps-documentation-de in the manifest.
APS_DE_SHA256 = "662ae19b00945aab2b014c72d6a6bd966403bf0f2cc2b939f6b97a4658350d55"

Manifest = dict[str, dict[str, Any]]
Questions = dict[object, dict[str, Any]]


@pytest.fixture(scope="module")
def probe_list() -> dict[str, Any]:
    return read_json(PROBES)


@pytest.fixture(scope="module")
def manifest() -> Manifest:
    return {entry["id"]: entry for entry in read_json(MANIFEST)["entries"]}


@pytest.fixture(scope="module")
def questions() -> Questions:
    return {question["id"]: question for question in read_json(QUESTIONS)["questions"]}


def source_files(question: dict[str, Any], manifest_id: str) -> set[str]:
    """Files of the sources of ``question`` in ``manifest_id`` (locator before the comma)."""
    return {
        source["locator"].split(",", 1)[0].strip()
        for source in question["sources"]
        if source["manifest_id"] == manifest_id
    }


def place_problems(
    probe: dict[str, Any], place: dict[str, Any], manifest: Manifest, questions: Questions
) -> list[str]:
    """What is wrong with one expected place of ``probe``."""
    where = f"{probe['id']}: {place['manifest_id']}"
    entry = manifest.get(place["manifest_id"])
    if entry is None:
        return [f"{where}: not in the manifest"]
    if "heading_path" in place:
        problems = []
        if entry["kind"] != "git-archive":
            problems.append(f"{where}: a heading path needs a repository archive")
        if SHA256.fullmatch(place["sha256"]) is None:
            problems.append(f"{where}: checksum is not 64 lower-case hexadecimal characters")
        question = questions[probe["basis"]["question"]]
        if place.get("path") not in source_files(question, place["manifest_id"]):
            problems.append(f"{where}: path {place.get('path')!r} is no source of the question")
        return problems
    if entry["kind"] != "file":
        return [f"{where}: pages need a file of the manifest"]
    if entry["sha256"] != place["sha256"]:
        return [f"{where}: checksum differs from the manifest"]
    return []


def probe_problems(probe: dict[str, Any], manifest: Manifest, questions: Questions) -> list[str]:
    """What is wrong with ``probe`` against the manifest and the test questions."""
    problems = []
    if not set(probe) <= PROBE_KEYS:
        problems.append(f"{probe['id']}: keys {sorted(set(probe) - PROBE_KEYS)}")
    question = questions.get(probe["basis"].get("question"))
    if question is None:
        return [*problems, f"{probe['id']}: no test question in the basis"]
    if probe["query"].strip() == question["question"].strip():
        problems.append(f"{probe['id']}: the query is the test question")
    if probe["id"].startswith(CONTROL_PREFIX):
        if probe["expected"] or question["sources"] or question["kind"] != "no-evidence":
            problems.append(f"{probe['id']}: a control probe needs a question without evidence")
        return problems
    for place in probe["expected"]:
        problems += place_problems(probe, place, manifest, questions)
    documented = {
        (place["manifest_id"], page)
        for place in documented_places(probe)
        for page in place.get("pages", [])
    }
    if documented != pages_of_question(question):
        problems.append(f"{probe['id']}: pages differ from the PDF pages of the question")
    return problems


def list_problems(data: dict[str, Any], manifest: Manifest, questions: Questions) -> list[str]:
    """What is wrong with a whole probe list."""
    problems = []
    for probe in data["probes"]:
        problems += probe_problems(probe, manifest, questions)
    return problems


def probes_of(data: dict[str, Any], number: int) -> list[dict[str, Any]]:
    return [probe for probe in data["probes"] if probe["basis"].get("question") == number]


# --- The probe list of M3 -----------------------------------------------------


def test_probe_list_is_valid() -> None:
    probes = load_probes(PROBES.read_text(encoding="utf-8"))

    assert [probe.id for probe in probes if probe.is_control] == ["control-11"]


def test_every_place_is_documented(
    probe_list: dict[str, Any], manifest: Manifest, questions: Questions
) -> None:
    assert list_problems(probe_list, manifest, questions) == []


def test_probes_have_the_keys_of_the_format_only(probe_list: dict[str, Any]) -> None:
    for probe in probe_list["probes"]:
        assert set(probe) <= PROBE_KEYS, probe["id"]
        assert set(probe) >= {"id", "query", "expected", "basis"}, probe["id"]


def test_the_test_questions_are_covered_in_own_words(
    probe_list: dict[str, Any], questions: Questions
) -> None:
    covered = {probe["basis"]["question"] for probe in probe_list["probes"]}

    # Question 8 may be added later (136), by heading path.
    assert covered - {NOT_MEASURABLE_QUESTION} == COVERED_QUESTIONS | {CONTROL_QUESTION}
    for number in TWICE:
        queries = [probe["query"] for probe in probes_of(probe_list, number)]
        assert len(queries) == 2, number
        assert len(set(queries)) == 2, number
    queries = [probe["query"] for probe in probe_list["probes"]]
    assert len(set(queries)) == len(queries)
    for probe in probe_list["probes"]:
        assert probe["query"] != questions[probe["basis"]["question"]]["question"], probe["id"]


def test_the_control_probe_expects_nothing(probe_list: dict[str, Any]) -> None:
    (control,) = probes_of(probe_list, CONTROL_QUESTION)

    assert control["id"] == "control-11"
    assert control["expected"] == []
    assert control["basis"] == {"question": CONTROL_QUESTION}


def test_question_8_is_missing_with_a_reason_or_located_by_heading_path(
    probe_list: dict[str, Any],
) -> None:
    """No probe for question 8 until 136; then only places by heading path."""
    probes = probes_of(probe_list, NOT_MEASURABLE_QUESTION)

    if not probes:
        assert "Test question 8 is not measurable yet" in probe_list["notes"]
        assert "136" in probe_list["notes"]
    for probe in probes:
        assert all("heading_path" in place for place in probe["expected"]), probe["id"]


def test_places_in_the_other_language_edition_match_the_documented_place(
    probe_list: dict[str, Any], manifest: Manifest
) -> None:
    """E-61: same pages of the same manual in another language, as in m2.json."""
    covered = []
    for probe in probe_list["probes"]:
        editions = other_editions(probe)
        places = {place["manifest_id"]: place for place in probe["expected"]}
        for edition, documented in APS_EDITIONS.items():
            if documented in places:
                assert editions.get(edition) == documented, probe["id"]
                covered.append(probe["id"])
        for edition, documented in editions.items():
            assert sorted(places[edition]["pages"]) == sorted(places[documented]["pages"])
            this, that = manifest[edition], manifest[documented]
            assert this["document_version"] == that["document_version"], probe["id"]
            assert this["language"] != that["language"], probe["id"]
    assert covered == [
        "question-1",
        "question-2",
        "question-3",
        "question-3b",
        "question-4",
        "question-5",
        "question-6",
        "question-7",
        "question-7b",
    ]


def test_m2_is_unchanged() -> None:
    """The probe list of M2 stays as it was (056, 067); m3.json is a list of its own."""
    m2 = Path(PROBE_LISTS / "m2.json").read_bytes()

    assert len(load_probes(m2.decode("utf-8"))) == 7
    assert b"question-3b" not in m2


# --- The checks on probe lists written for the test (for work order 136) ---------


def markdown_probe(**place_changes: object) -> dict[str, Any]:
    """A probe for question 8 located by heading path, as 136 will add one."""
    place: dict[str, object] = {
        "manifest_id": "aps-repository-dev",
        "sha256": "0" * 64,
        "heading_path": ["Drill"],
        "path": "docs/06-modules/drill.md",
    }
    place.update(place_changes)
    return {
        "id": "question-8",
        "query": "Unter welchen Themen meldet sich die Bohrstation beim Broker?",
        "basis": {"question": NOT_MEASURABLE_QUESTION},
        "expected": [place],
    }


def test_a_probe_by_heading_path_is_accepted(manifest: Manifest, questions: Questions) -> None:
    probe = markdown_probe()

    assert probe_problems(probe, manifest, questions) == []
    assert load_probes(json.dumps({"schema_version": 1, "probes": [probe]}))[0].expected


def test_the_list_with_a_probe_for_question_8_is_accepted(
    probe_list: dict[str, Any], manifest: Manifest, questions: Questions
) -> None:
    """A probe for question 8 by heading path (136) passes the same checks as the list of 120.

    The test replaces the probe question-8 of m3.json, if there is one, by the
    example, so it holds before and after 136.
    """
    others = [probe for probe in probe_list["probes"] if probe["id"] != "question-8"]
    extended = {**probe_list, "probes": [*others, markdown_probe()]}

    assert list_problems(extended, manifest, questions) == []
    assert len(load_probes(json.dumps(extended))) == len(others) + 1
    test_the_test_questions_are_covered_in_own_words(extended, questions)
    test_question_8_is_missing_with_a_reason_or_located_by_heading_path(extended)
    test_places_in_the_other_language_edition_match_the_documented_place(extended, manifest)


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"path": "docs/06-modules/mill.md"}, "path 'docs/06-modules/mill.md' is no source"),
        ({"manifest_id": "aps-repository"}, "path 'docs/06-modules/drill.md' is no source"),
        ({"manifest_id": "aps-documentation-de"}, "a heading path needs a repository archive"),
        ({"sha256": "A" * 64}, "checksum is not 64 lower-case hexadecimal characters"),
    ],
)
def test_a_wrong_probe_by_heading_path_is_found(
    manifest: Manifest, questions: Questions, changes: dict[str, object], problem: str
) -> None:
    problems = probe_problems(markdown_probe(**changes), manifest, questions)

    assert any(problem in found for found in problems), problems


@pytest.mark.parametrize(
    ("probe", "problem"),
    [
        (
            {
                "id": "question-5",
                "query": "TIA",
                "basis": {"question": 5},
                "expected": [
                    {
                        "manifest_id": "aps-documentation-de",
                        "sha256": APS_DE_SHA256,
                        "pages": [33],
                    }
                ],
            },
            "pages differ from the PDF pages of the question",
        ),
        (
            {
                "id": "question-9",
                "query": "Nutzlast",
                "basis": {"question": 9},
                "expected": [
                    {"manifest_id": "ur5e-user-manual-de", "sha256": "1" * 64, "pages": [16]}
                ],
            },
            "checksum differs from the manifest",
        ),
        (
            {
                "id": "question-9",
                "query": "Welche Nutzlast hat der UR5e?",
                "basis": {"question": 9},
                "expected": [],
            },
            "the query is the test question",
        ),
        (
            {
                "id": "control-1",
                "query": "Wie heißt die Anlage?",
                "basis": {"question": 1},
                "expected": [],
            },
            "a control probe needs a question without evidence",
        ),
    ],
)
def test_a_wrong_probe_by_pages_is_found(
    manifest: Manifest, questions: Questions, probe: dict[str, Any], problem: str
) -> None:
    problems = probe_problems(probe, manifest, questions)

    assert any(problem in found for found in problems), problems
