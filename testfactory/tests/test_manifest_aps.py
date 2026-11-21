"""Tests for the manifest entries of the production line (fischertechnik APS 24V).

They read ``testfactory/manifest.yaml`` and the source file of work order 102
and need no network.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path, PurePosixPath

from testfactory import manifest_tools
from testfactory.manifest_tools import Entry

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "testfactory" / "manifest.yaml"
SOURCES_PATH = REPOSITORY_ROOT / "docs" / "testfabrik" / "quellen-fertigungslinie.md"

REPOSITORY_IDS = ("aps-repository", "aps-repository-dev")
DOCUMENT_TOPICS = (
    "quick-start",
    "documentation",
    "assignment-plans",
    "calibration",
    "troubleshooting",
    "change-ip-address",
    "software-versions",
    "software-update",
)
DOCUMENT_IDS = tuple(
    f"aps-{topic}-{language}" for topic in DOCUMENT_TOPICS for language in ("de", "en")
)
REFERENCE_IDS = ("aps-rpi-image",)
EXPECTED_IDS = REPOSITORY_IDS + DOCUMENT_IDS + REFERENCE_IDS

PINNED_COMMITS = {
    "aps-repository": "b8082e16282a69f7d219a39d993bf7d34cb9d349",
    "aps-repository-dev": "24568073f7f70d0d31dcaa83bcfcd7b595baba1f",
}

# Identifiers of the device list (work order 106).
PLANT_IDS = (
    "aps-dps",
    "aps-hbw",
    "aps-drill",
    "aps-mill",
    "aps-aiqs",
    "aps-agv",
    "aps-charging",
    "aps-core",
)
DEVICE_IDS = (
    "dps-plc",
    "dps-txt",
    "hbw-plc",
    "drill-plc",
    "mill-plc",
    "aiqs-plc",
    "aiqs-txt",
    "agv-txt",
    "cgw-txt",
    "ccu-rpi",
    "aps-router",
)

# Material that was decided not to be part of the test factory.
EXCLUDED_URL_PARTS = ("brennofen", "annealingfurnace", "dokumentationen-fts", "0424")


def _sources_text() -> str:
    """Return the source file with the short form ``P/...`` written out."""
    text = SOURCES_PATH.read_text(encoding="utf-8")
    match = re.search(r"\*\*P\*\* = `(https://[^`]+)`", text)
    if match is None:
        raise AssertionError("short form P is not defined in the source file")
    return text.replace("`P/", "`" + match.group(1) + "/")


class ApsManifestTests(unittest.TestCase):
    entries: dict[str, Entry]

    @classmethod
    def setUpClass(cls) -> None:
        manifest = manifest_tools.load_manifest(MANIFEST_PATH)
        cls.entries = {entry.id: entry for entry in manifest.entries if entry.id.startswith("aps-")}

    def test_expected_entries_are_present(self) -> None:
        self.assertEqual(sorted(self.entries), sorted(EXPECTED_IDS))

    def test_every_entry_has_terms_version_and_assignment(self) -> None:
        for entry_id, entry in self.entries.items():
            with self.subTest(entry=entry_id):
                self.assertTrue(entry.terms.note)
                self.assertTrue(entry.terms.holder)
                self.assertTrue(entry.software_version)
                self.assertTrue(entry.version_source)
                self.assertGreaterEqual(len(entry.assigned_to), 1)

    def test_repositories_are_pinned_to_a_full_commit(self) -> None:
        for entry_id, commit in PINNED_COMMITS.items():
            with self.subTest(entry=entry_id):
                entry = self.entries[entry_id]
                self.assertEqual(entry.kind, manifest_tools.KIND_GIT_ARCHIVE)
                self.assertEqual(entry.fetch, manifest_tools.FETCH_AUTO)
                self.assertIsNotNone(entry.commit)
                self.assertRegex(entry.commit or "", r"\A[0-9a-f]{40}\Z")
                self.assertEqual(entry.commit, commit)
                self.assertTrue(
                    (entry.repository or "").startswith("https://github.com/fischertechnik/")
                )
                self.assertTrue(entry.branch)

    def test_nothing_may_be_redistributed(self) -> None:
        for entry_id, entry in self.entries.items():
            with self.subTest(entry=entry_id):
                self.assertFalse(entry.terms.redistribution)
                self.assertEqual(entry.terms.license, "none-stated")

    def test_unverified_terms_are_explained(self) -> None:
        for entry_id, entry in self.entries.items():
            with self.subTest(entry=entry_id):
                if entry.terms.verified:
                    self.assertIsNotNone(entry.terms.checked_on)
                else:
                    self.assertRegex(entry.notes or "", r"unverified|unchecked")

    def test_documents_are_files_loaded_automatically(self) -> None:
        for entry_id in DOCUMENT_IDS:
            with self.subTest(entry=entry_id):
                entry = self.entries[entry_id]
                self.assertEqual(entry.kind, manifest_tools.KIND_FILE)
                self.assertEqual(entry.fetch, manifest_tools.FETCH_AUTO)
                self.assertEqual(entry.language, entry_id.rsplit("-", 1)[1])
                self.assertEqual(entry.terms.holder, "fischertechnik GmbH")
                self.assertTrue((entry.url or "").startswith("https://www.fischertechnik.de/"))

    def test_image_is_a_reference_that_is_not_loaded(self) -> None:
        entry = self.entries["aps-rpi-image"]
        self.assertEqual(entry.kind, manifest_tools.KIND_REFERENCE)
        self.assertEqual(entry.fetch, manifest_tools.FETCH_NONE)
        self.assertIsNone(entry.target)
        self.assertFalse(entry.terms.verified)
        self.assertEqual(entry.assigned_to, ("ccu-rpi",))

    def test_assignments_use_identifiers_of_the_device_list(self) -> None:
        known = set(PLANT_IDS) | set(DEVICE_IDS)
        for entry_id, entry in self.entries.items():
            with self.subTest(entry=entry_id):
                self.assertLessEqual(set(entry.assigned_to), known)

    def test_documents_about_the_whole_line_are_assigned_to_all_plants(self) -> None:
        for topic in ("quick-start", "documentation"):
            for language in ("de", "en"):
                entry = self.entries[f"aps-{topic}-{language}"]
                with self.subTest(entry=entry.id):
                    self.assertEqual(set(entry.assigned_to), set(PLANT_IDS))

    def test_targets_are_below_the_vendor_folder_and_not_nested(self) -> None:
        targets = {
            entry_id: PurePosixPath(entry.target)
            for entry_id, entry in self.entries.items()
            if entry.target is not None
        }
        self.assertEqual(len(targets), len(REPOSITORY_IDS) + len(DOCUMENT_IDS))
        for entry_id, target in targets.items():
            with self.subTest(entry=entry_id):
                self.assertEqual(target.parts[0], "fischertechnik")
                for other_id, other in targets.items():
                    if other_id != entry_id:
                        self.assertNotIn(other, target.parents)

    def test_excluded_material_is_not_listed(self) -> None:
        for entry_id, entry in self.entries.items():
            with self.subTest(entry=entry_id):
                address = (entry.url or "").lower()
                for part in EXCLUDED_URL_PARTS:
                    self.assertNotIn(part, address)

    def test_every_address_is_taken_from_the_source_file(self) -> None:
        sources = _sources_text()
        for entry_id, entry in self.entries.items():
            for field in ("url", "landing_page", "repository"):
                address: str | None = getattr(entry, field)
                if address is None:
                    continue
                with self.subTest(entry=entry_id, field=field):
                    self.assertRegex(sources, re.escape(address) + r"(?![A-Za-z0-9_./-])")


if __name__ == "__main__":
    unittest.main()
