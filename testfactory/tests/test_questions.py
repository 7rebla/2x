"""Checks of the test questions with expected answers (work orders 111, 112).

``testfactory/questions.yaml`` holds the eleven test questions of section 11
of the project brief, the expected answers and their evidence. The file is
written in JSON notation like the manifest, so the standard library reads it.
The tests need no network and no downloaded material: they check the form of
the file and that every source names an entry of the manifest.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any

from testfactory import manifest_tools

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
QUESTIONS_PATH = REPOSITORY_ROOT / "testfactory" / "questions.yaml"
MANIFEST_PATH = REPOSITORY_ROOT / "testfactory" / "manifest.yaml"

# Wording of section 11 of the project brief, unchanged. Only a7 replaces the
# questions (at the first test); then this list changes with the file.
QUESTIONS = [
    "Unter welcher Adresse ist die Zentralsteuerung der Fertigungslinie erreichbar?",
    "Über welchen Port erreicht man Node-RED auf der Zentralsteuerung?",
    "Über welches Protokoll tauschen die TXT-Controller Daten mit der Zentralsteuerung aus?",
    "Wie gelangen Befehle der Zentralsteuerung zu den Siemens-Steuerungen der Module?",
    "Welche Version des TIA Portals setzen die SPS-Projekte voraus?",
    "Welche CPU steckt in den Modulsteuerungen? (Die Unterlagen widersprechen sich; "
    "erwartet werden beide Fundstellen.)",
    "Was ist zu tun, wenn das Transportfahrzeug seine Spur verliert?",
    "Welche MQTT-Topics verwendet die Bohrstation?",
    "Welche Nutzlast hat der UR5e?",
    "Wie wird der UR5e nach einem Schutzstopp wieder freigegeben?",
    "Kontrollfrage ohne Beleg: Wann wurde die Frässtation zuletzt gewartet? "
    "Erwartet wird „Dazu finde ich nichts in den Unterlagen\".",
]

NO_EVIDENCE_ANSWER = "Dazu finde ich nichts in den Unterlagen"
KINDS_BY_ID = {6: "contradiction", 11: "no-evidence"}
# Questions on the robot cell; their evidence lies in the UR documents
# (work order 112).
ROBOT_QUESTION_IDS = {9, 10}
ROBOT_DEVICE = "ur5e"
MAX_ANSWER_LENGTH = 400

FILE_FIELDS = {"schema_version", "manifest", "notes", "questions", "candidates"}
ITEM_FIELDS = {
    "id",
    "question",
    "kind",
    "status",
    "expected_answer",
    "key_facts",
    "sources",
    "verified_on",
    "notes",
}
SOURCE_FIELDS = {"manifest_id", "locator", "supports"}
KINDS = {"fact", "contradiction", "no-evidence"}
# Since work order 112 every question has its evidence; pending is gone.
STATUSES = {"verified"}
# Field names that would hold text copied from a source. None is allowed.
QUOTE_FIELD = re.compile(r"quot|zitat|excerpt|auszug|verbatim|citation_text", re.I)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _raw() -> str:
    return QUESTIONS_PATH.read_bytes().decode("utf-8")


def _load() -> dict[str, Any]:
    data = json.loads(_raw(), object_pairs_hook=_no_duplicate_keys)
    if not isinstance(data, dict):
        raise TypeError("questions.yaml must hold an object")
    return data


def _questions() -> list[dict[str, Any]]:
    questions = _load()["questions"]
    assert isinstance(questions, list)
    return questions


def _candidates() -> list[dict[str, Any]]:
    candidates = _load()["candidates"]
    assert isinstance(candidates, list)
    return candidates


def _all_keys(value: Any) -> list[str]:
    """Every key of every object below ``value``."""
    if isinstance(value, dict):
        keys = list(value)
        for item in value.values():
            keys.extend(_all_keys(item))
        return keys
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_all_keys(item))
        return result
    return []


def _label(item: dict[str, Any]) -> str:
    return f"id {item.get('id')!r}"


class QuestionFileTest(unittest.TestCase):
    def test_file_is_json_in_canonical_form(self) -> None:
        raw = _raw()
        self.assertNotIn("\r", raw)
        canonical = json.dumps(_load(), indent=2, ensure_ascii=False) + "\n"
        self.assertEqual(raw, canonical, "write the file like the manifest")

    def test_file_fields(self) -> None:
        data = _load()
        self.assertEqual(set(data), FILE_FIELDS)
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["manifest"], "manifest.yaml")

    def test_no_quote_field(self) -> None:
        for key in _all_keys(_load()):
            with self.subTest(key=key):
                self.assertIsNone(QUOTE_FIELD.search(key))


class QuestionTest(unittest.TestCase):
    def test_eleven_questions_with_ids_one_to_eleven(self) -> None:
        self.assertEqual([q["id"] for q in _questions()], list(range(1, 12)))

    def test_wording_is_unchanged(self) -> None:
        self.assertEqual([q["question"] for q in _questions()], QUESTIONS)

    def test_fields(self) -> None:
        for question in _questions():
            with self.subTest(question=_label(question)):
                self.assertEqual(set(question), ITEM_FIELDS)

    def test_kind(self) -> None:
        for question in _questions():
            with self.subTest(question=_label(question)):
                expected = KINDS_BY_ID.get(question["id"], "fact")
                self.assertEqual(question["kind"], expected)

    def test_every_question_is_verified(self) -> None:
        for question in _questions():
            with self.subTest(question=_label(question)):
                self.assertIn(question["status"], STATUSES)

    def test_no_pending_anywhere_in_the_file(self) -> None:
        self.assertNotIn("pending", _raw())

    def test_robot_questions_cite_a_ur_document(self) -> None:
        manifest = manifest_tools.load_manifest(MANIFEST_PATH)
        robot_entries = {
            entry.id for entry in manifest.entries if ROBOT_DEVICE in entry.assigned_to
        }
        self.assertTrue(robot_entries, "the manifest has no UR entries")
        for question in _questions():
            if question["id"] not in ROBOT_QUESTION_IDS:
                continue
            with self.subTest(question=_label(question)):
                cited = {source["manifest_id"] for source in question["sources"]}
                self.assertTrue(cited & robot_entries, "no source is a UR document")

    def test_verified_questions_have_sources(self) -> None:
        for question in _questions():
            if question["status"] != "verified":
                continue
            with self.subTest(question=_label(question)):
                if question["kind"] == "no-evidence":
                    self.assertEqual(question["sources"], [])
                elif question["kind"] == "contradiction":
                    self.assertGreaterEqual(len(question["sources"]), 2)
                else:
                    self.assertGreaterEqual(len(question["sources"]), 1)

    def test_contradiction_names_two_different_places(self) -> None:
        question = _questions()[5]
        locators = {source["locator"] for source in question["sources"]}
        self.assertGreaterEqual(len(locators), 2)

    def test_no_evidence_answer(self) -> None:
        question = _questions()[10]
        self.assertEqual(question["kind"], "no-evidence")
        self.assertEqual(question["expected_answer"], NO_EVIDENCE_ANSWER)
        self.assertEqual(question["sources"], [])


class ItemContentTest(unittest.TestCase):
    """Rules for both questions and candidates."""

    def _items(self) -> list[dict[str, Any]]:
        return _questions() + _candidates()

    def test_verified_items_have_an_answer_and_key_facts(self) -> None:
        for item in self._items():
            if item["status"] != "verified":
                continue
            with self.subTest(item=_label(item)):
                answer = item["expected_answer"]
                self.assertIsInstance(answer, str)
                self.assertTrue(answer.strip())
                self.assertLessEqual(len(answer), MAX_ANSWER_LENGTH)
                self.assertTrue(item["key_facts"])
                self.assertRegex(item["verified_on"], DATE)

    def test_key_facts_occur_in_the_answer(self) -> None:
        for item in self._items():
            for fact in item["key_facts"]:
                with self.subTest(item=_label(item), fact=fact):
                    self.assertIsInstance(fact, str)
                    self.assertTrue(fact.strip())
                    self.assertIn(fact.casefold(), item["expected_answer"].casefold())

    def test_sources_name_loaded_manifest_entries(self) -> None:
        manifest = manifest_tools.load_manifest(MANIFEST_PATH)
        entries = {entry.id: entry for entry in manifest.entries}
        for item in self._items():
            for source in item["sources"]:
                with self.subTest(item=_label(item), source=source.get("manifest_id")):
                    self.assertEqual(set(source), SOURCE_FIELDS)
                    entry = entries.get(source["manifest_id"])
                    self.assertIsNotNone(entry, "manifest_id is not in the manifest")
                    assert entry is not None
                    # Evidence must lie in material that is loaded and pinned.
                    self.assertIsNotNone(entry.target)
                    self.assertIsInstance(source["locator"], str)
                    self.assertTrue(source["locator"].strip())
                    self.assertIsInstance(source["supports"], str)
                    self.assertTrue(source["supports"].strip())


class CandidateTest(unittest.TestCase):
    def test_candidates(self) -> None:
        candidates = _candidates()
        ids = [candidate["id"] for candidate in candidates]
        self.assertEqual(len(ids), len(set(ids)))
        for candidate in candidates:
            with self.subTest(candidate=_label(candidate)):
                self.assertEqual(set(candidate), ITEM_FIELDS)
                self.assertIsInstance(candidate["id"], str)
                self.assertRegex(candidate["id"], r"^c\d+$")
                self.assertIn(candidate["kind"], KINDS)
                self.assertEqual(candidate["status"], "verified")
                self.assertTrue(candidate["sources"])
                if candidate["kind"] == "contradiction":
                    self.assertGreaterEqual(len(candidate["sources"]), 2)
                self.assertNotIn(candidate["question"], QUESTIONS)


if __name__ == "__main__":
    unittest.main()
