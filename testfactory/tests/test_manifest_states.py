"""Version statements, terms checks and pinned values of the manifest (work order 110).

Work order 110 read the title pages, imprints and license files of the loaded
material and recorded the results in ``testfactory/manifest.yaml``. These
tests keep the result in shape:

- every ``kind: file`` entry names its edition (``document_version``) and
  where that statement comes from (``version_source``);
- a version statement that is still unverified carries its reason in
  ``notes``, as a sentence starting with ``Version unverified because``;
- every entry with ``terms.verified: true`` has ``terms.checked_on``;
- checksums, addresses, commits and digests are present for exactly the
  entries listed below, so that none of them gets lost by a later edit.

The tests read only the manifest and need no network.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from testfactory import manifest_tools
from testfactory.manifest_tools import Entry

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "testfactory" / "manifest.yaml"

# A version statement counts as open if it says so in English or German.
OPEN_VERSION_RE = re.compile(r"\bunverified\b|\bungepr(?:ü|ue)ft\b", re.IGNORECASE)
# The reason for an open version statement, as written into ``notes``.
OPEN_VERSION_REASON_RE = re.compile(r"Version unverified because \S")

# Entries whose ``sha256`` is set: every file with ``fetch: auto``
# (first fetch in work order 109). The Siemens V4.6 manual is fetched by hand
# and has no checksum yet (E-27).
SHA256_IDS = frozenset(
    {
        "aps-quick-start-de",
        "aps-documentation-de",
        "aps-assignment-plans-de",
        "aps-calibration-de",
        "aps-troubleshooting-de",
        "aps-change-ip-address-de",
        "aps-software-versions-de",
        "aps-software-update-de",
        "aps-quick-start-en",
        "aps-documentation-en",
        "aps-assignment-plans-en",
        "aps-calibration-en",
        "aps-troubleshooting-en",
        "aps-change-ip-address-en",
        "aps-software-versions-en",
        "aps-software-update-en",
        "rpi4b-datasheet-en",
        "rpi4b-product-brief-en",
        "tl-wr902ac-user-guide-v3-en",
        "ur5e-user-manual-de",
        "ur5e-software-handbook-en",
        "ur5e-script-directory-en",
        "ur5e-service-manual-en",
    }
)

# Entries whose ``tree_sha256`` is set: the three loaded repositories.
TREE_SHA256_IDS = frozenset({"aps-repository", "aps-repository-dev", "opnsense-docs"})

# Entries whose ``url`` is set: every file (including the Siemens V4.6 manual)
# plus two references.
URL_IDS = SHA256_IDS | frozenset(
    {
        "siemens-s7-1200-system-manual-v4-6-de",
        "siemens-s7-1200-system-manual-v4-7-de",
        "aps-rpi-image",
    }
)

# Entries whose ``commit`` is set: repositories pinned to a fixed commit.
COMMIT_IDS = frozenset(
    {"aps-repository", "aps-repository-dev", "opnsense-docs", "rpi-documentation"}
)

# Entries whose ``digest`` is set: the one container image.
DIGEST_IDS = frozenset({"ursim-e-series"})

PINNED_FIELDS: dict[str, frozenset[str]] = {
    "sha256": SHA256_IDS,
    "tree_sha256": TREE_SHA256_IDS,
    "url": URL_IDS,
    "commit": COMMIT_IDS,
    "digest": DIGEST_IDS,
}


class ManifestStateTests(unittest.TestCase):
    entries: tuple[Entry, ...]

    @classmethod
    def setUpClass(cls) -> None:
        cls.entries = manifest_tools.load_manifest(MANIFEST_PATH).entries

    def test_manifest_has_the_known_entries(self) -> None:
        # A new entry needs a decision about its pinned values here.
        self.assertEqual(len(self.entries), 31)

    def test_every_file_names_its_edition_and_the_source_of_it(self) -> None:
        for entry in self.entries:
            if entry.kind != manifest_tools.KIND_FILE:
                continue
            with self.subTest(entry=entry.id):
                self.assertTrue((entry.document_version or "").strip())
                self.assertTrue((entry.version_source or "").strip())

    def test_open_version_statements_are_explained_in_notes(self) -> None:
        for entry in self.entries:
            if not OPEN_VERSION_RE.search(entry.version_source or ""):
                continue
            with self.subTest(entry=entry.id):
                self.assertRegex(entry.notes or "", OPEN_VERSION_REASON_RE)

    def test_verified_terms_have_a_check_date(self) -> None:
        for entry in self.entries:
            if not entry.terms.verified:
                continue
            with self.subTest(entry=entry.id):
                self.assertIsNotNone(entry.terms.checked_on)

    def test_pinned_values_are_present_for_exactly_the_listed_entries(self) -> None:
        known = {entry.id for entry in self.entries}
        for field, expected in PINNED_FIELDS.items():
            with self.subTest(field=field):
                self.assertLessEqual(expected, known, "the list names an unknown entry")
                present = {entry.id for entry in self.entries if getattr(entry, field) is not None}
                self.assertEqual(present, set(expected))


if __name__ == "__main__":
    unittest.main()
