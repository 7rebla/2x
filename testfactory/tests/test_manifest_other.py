"""Tests for the manifest entries of the standard devices, the robot cell and the firewall.

They cover the Siemens S7-1200, the Raspberry Pi 4B, the TP-Link TL-WR902AC,
the UR5e manuals, the URSim image and the OPNsense documentation (work order
107). They read ``testfactory/manifest.yaml``, the device list and the source
file of work order 103 and need no network.
"""

from __future__ import annotations

import csv
import re
import unittest
from pathlib import Path, PurePosixPath

from testfactory import manifest_tools
from testfactory.manifest_tools import Entry

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "testfactory" / "manifest.yaml"
DEVICES_PATH = REPOSITORY_ROOT / "testfactory" / "layout" / "devices.csv"
SOURCES_PATH = (
    REPOSITORY_ROOT / "docs" / "testfabrik" / "quellen-standardgeraete-roboter-firewall.md"
)

# Entries of the production line (work order 105) are tested elsewhere.
APS_PREFIX = "aps-"

EXPECTED_IDS = (
    "siemens-s7-1200-system-manual-v4-6-de",
    "siemens-s7-1200-system-manual-v4-7-de",
    "rpi4b-datasheet-en",
    "rpi4b-product-brief-en",
    "rpi-documentation",
    "tl-wr902ac-user-guide-v3-en",
    "ur5e-user-manual-de",
    "ur5e-software-handbook-en",
    "ur5e-script-directory-en",
    "ur5e-service-manual-en",
    "ursim-e-series",
    "opnsense-docs",
)

UR5E_MANUAL_ID = "ur5e-user-manual-de"
URSIM_ID = "ursim-e-series"
SIEMENS_IDS = (
    "siemens-s7-1200-system-manual-v4-6-de",
    "siemens-s7-1200-system-manual-v4-7-de",
)
SIEMENS_PLC_IDS = ("dps-plc", "hbw-plc", "drill-plc", "mill-plc", "aiqs-plc")

# Only these licenses may carry ``redistribution: true``. CC-BY-SA-4.0 is not
# in the list: question 3 of work order 108 was answered with option A.
REDISTRIBUTABLE_LICENSES = ("BSD-2-Clause", "public-domain")

PATCH_TAG_RE = re.compile(r"\d+\.\d+\.\d+")
ADDRESS_FIELDS = ("url", "landing_page", "repository")


def _all_addresses(entry: Entry) -> list[tuple[str, str]]:
    """Return ``(field, address)`` for every address of the entry."""
    found: list[tuple[str, str]] = []
    for field in ADDRESS_FIELDS:
        address: str | None = getattr(entry, field)
        if address is not None:
            found.append((field, address))
    if entry.terms.terms_url is not None:
        found.append(("terms.terms_url", entry.terms.terms_url))
    return found


def _device_list_ids() -> set[str]:
    with DEVICES_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {row[column] for row in rows for column in ("plant_id", "device_id") if row[column]}


class OtherManifestTests(unittest.TestCase):
    all_entries: tuple[Entry, ...]
    entries: dict[str, Entry]

    @classmethod
    def setUpClass(cls) -> None:
        manifest = manifest_tools.load_manifest(MANIFEST_PATH)
        cls.all_entries = manifest.entries
        cls.entries = {
            entry.id: entry
            for entry in manifest.entries
            if not entry.id.startswith(APS_PREFIX)
        }

    def test_expected_entries_are_present(self) -> None:
        self.assertEqual(sorted(self.entries), sorted(EXPECTED_IDS))

    def test_ursim_is_pinned_to_a_patch_tag_and_a_digest(self) -> None:
        entry = self.entries[URSIM_ID]
        self.assertEqual(entry.kind, manifest_tools.KIND_CONTAINER_IMAGE)
        self.assertEqual(entry.fetch, manifest_tools.FETCH_NONE)
        self.assertEqual(entry.image, "universalrobots/ursim_e-series")
        self.assertRegex(entry.tag or "", PATCH_TAG_RE.pattern + r"\Z")
        self.assertNotEqual(entry.tag, "latest")
        self.assertRegex(entry.digest or "", r"\Asha256:[0-9a-f]{64}\Z")
        self.assertEqual(entry.assigned_to, ("ur5e",))

    def test_ur5e_manual_and_ursim_name_the_same_software_version(self) -> None:
        manual = self.entries[UR5E_MANUAL_ID]
        simulator = self.entries[URSIM_ID]
        self.assertIsNotNone(manual.software_version)
        self.assertEqual(manual.software_version, simulator.software_version)
        self.assertIn(simulator.tag or "", manual.software_version or "")

    def test_every_entry_has_a_terms_note(self) -> None:
        for entry in self.all_entries:
            with self.subTest(entry=entry.id):
                self.assertTrue(entry.terms.note.strip())

    def test_only_free_licenses_may_be_redistributed(self) -> None:
        for entry in self.all_entries:
            if entry.terms.redistribution:
                with self.subTest(entry=entry.id):
                    self.assertIn(entry.terms.license, REDISTRIBUTABLE_LICENSES)

    def test_no_moving_address_or_moving_tag(self) -> None:
        for entry in self.all_entries:
            for field, address in _all_addresses(entry):
                with self.subTest(entry=entry.id, field=field):
                    self.assertNotIn("/latest/", address.lower())
            if entry.kind == manifest_tools.KIND_CONTAINER_IMAGE:
                with self.subTest(entry=entry.id, field="tag"):
                    self.assertIsNotNone(PATCH_TAG_RE.fullmatch(entry.tag or ""))
                    self.assertIsNotNone(entry.digest)

    def test_siemens_is_never_fetched_automatically(self) -> None:
        for entry in self.all_entries:
            addresses = [address for _, address in _all_addresses(entry)]
            if any("siemens.com" in address for address in addresses):
                with self.subTest(entry=entry.id):
                    self.assertIn(
                        entry.fetch, (manifest_tools.FETCH_MANUAL, manifest_tools.FETCH_NONE)
                    )
        authoritative = self.entries[SIEMENS_IDS[0]]
        self.assertEqual(authoritative.kind, manifest_tools.KIND_FILE)
        self.assertEqual(authoritative.fetch, manifest_tools.FETCH_MANUAL)
        self.assertIn("V4.6", authoritative.document_version or "")
        pointer = self.entries[SIEMENS_IDS[1]]
        self.assertEqual(pointer.kind, manifest_tools.KIND_REFERENCE)
        self.assertIn("V4.7", pointer.document_version or "")
        for entry_id in SIEMENS_IDS:
            entry = self.entries[entry_id]
            with self.subTest(entry=entry_id):
                self.assertEqual(entry.assigned_to, SIEMENS_PLC_IDS)
                self.assertFalse(entry.terms.redistribution)
                self.assertIn("A.6.2", entry.notes or "")
                self.assertNotIn("04/2012", entry.document_version or "")

    def test_opnsense_documentation_is_a_pinned_bsd_archive(self) -> None:
        entry = self.entries["opnsense-docs"]
        self.assertEqual(entry.kind, manifest_tools.KIND_GIT_ARCHIVE)
        self.assertEqual(entry.fetch, manifest_tools.FETCH_AUTO)
        self.assertEqual(entry.repository, "https://github.com/opnsense/docs")
        self.assertEqual(entry.commit, "953dd3d1d1dd2739a18d0b6df5c936146153aff6")
        self.assertEqual(entry.terms.license, "BSD-2-Clause")
        self.assertTrue(entry.terms.redistribution)
        self.assertTrue(entry.terms.verified)
        self.assertIn(entry.commit or "", entry.terms.terms_url or "")
        self.assertIsNone(entry.software_version)
        self.assertIn("set in T2", entry.version_source or "")
        self.assertEqual(entry.assigned_to, ("opnsense-fw",))

    def test_raspberry_pi_documentation_is_only_a_reference(self) -> None:
        entry = self.entries["rpi-documentation"]
        self.assertEqual(entry.kind, manifest_tools.KIND_REFERENCE)
        self.assertEqual(entry.fetch, manifest_tools.FETCH_NONE)
        self.assertRegex(entry.commit or "", r"\A[0-9a-f]{40}\Z")
        self.assertTrue((entry.repository or "").startswith("https://github.com/"))

    def test_assignments_use_identifiers_of_the_device_list(self) -> None:
        known = _device_list_ids()
        for entry_id, entry in self.entries.items():
            with self.subTest(entry=entry_id):
                self.assertGreaterEqual(len(entry.assigned_to), 1)
                self.assertLessEqual(set(entry.assigned_to), known)
        self.assertIn("aps-router", self.entries["tl-wr902ac-user-guide-v3-en"].assigned_to)

    def test_unverified_terms_are_explained(self) -> None:
        for entry_id, entry in self.entries.items():
            with self.subTest(entry=entry_id):
                self.assertIsNotNone(entry.terms.checked_on)
                if not entry.terms.verified:
                    self.assertRegex(entry.notes or "", r"unverified|unchecked")

    def test_targets_are_below_a_vendor_folder_and_not_nested(self) -> None:
        own = {
            entry_id: PurePosixPath(entry.target)
            for entry_id, entry in self.entries.items()
            if entry.target is not None
        }
        everything = {
            entry.id: PurePosixPath(entry.target)
            for entry in self.all_entries
            if entry.target is not None
        }
        for entry_id, target in own.items():
            with self.subTest(entry=entry_id):
                self.assertGreaterEqual(len(target.parts), 2)
                self.assertNotEqual(target.parts[0], "fischertechnik")
                for other_id, other in everything.items():
                    if other_id != entry_id:
                        self.assertNotIn(other, target.parents)
                        self.assertNotIn(target, other.parents)

    def test_every_address_is_taken_from_the_source_file(self) -> None:
        sources = SOURCES_PATH.read_text(encoding="utf-8")
        for entry_id, entry in self.entries.items():
            for field, address in _all_addresses(entry):
                with self.subTest(entry=entry_id, field=field):
                    self.assertRegex(sources, re.escape(address) + r"(?![A-Za-z0-9_./-])")


if __name__ == "__main__":
    unittest.main()
