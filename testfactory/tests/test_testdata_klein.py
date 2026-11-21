"""Tests for the freely licensed test documents in ``testdata/klein`` (work order 108).

They read ``testdata/klein/manifest.yaml`` and the files it lists and need no
network.
"""

from __future__ import annotations

import unittest
from pathlib import Path, PurePosixPath

from testfactory import manifest_tools
from testfactory.manifest_tools import Entry, Manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TESTDATA_DIR = REPOSITORY_ROOT / "testdata" / "klein"
MANIFEST_PATH = TESTDATA_DIR / "manifest.yaml"

ALLOWED_LICENSES = ("BSD-2-Clause", "public-domain")
# Files that may lie in the folder without a manifest entry.
UNLISTED_NAMES = ("README.md", "LICENSE", "manifest.yaml")
MAX_FOLDER_BYTES = 2 * 1024 * 1024
MARKDOWN_SUFFIX = ".md"


def _load() -> Manifest:
    return manifest_tools.load_manifest(MANIFEST_PATH)


def _target(manifest: Manifest, entry: Entry) -> Path:
    path = manifest_tools.target_path(MANIFEST_PATH, manifest, entry)
    if path is None:
        raise AssertionError(f"entry '{entry.id}' has no target")
    return path


def _files_in_folder() -> list[Path]:
    return sorted(path for path in TESTDATA_DIR.rglob("*") if path.is_file())


class TestdataKleinManifestTest(unittest.TestCase):
    def test_manifest_is_valid_and_complete(self) -> None:
        manifest = _load()
        self.assertEqual(manifest.root, ".")
        self.assertGreater(len(manifest.entries), 0)
        self.assertEqual(manifest_tools.find_incomplete(manifest), [])

    def test_manifest_is_in_canonical_form(self) -> None:
        manifest = _load()
        self.assertEqual(
            MANIFEST_PATH.read_bytes(), manifest_tools.dump_manifest(manifest).encode("utf-8")
        )

    def test_every_entry_is_a_checked_in_local_file(self) -> None:
        for entry in _load().entries:
            with self.subTest(entry=entry.id):
                self.assertEqual(entry.kind, manifest_tools.KIND_LOCAL)
                self.assertEqual(entry.fetch, manifest_tools.FETCH_NONE)
                self.assertIsNotNone(entry.url)

    def test_every_file_exists_with_recorded_checksum_and_size(self) -> None:
        manifest = _load()
        for entry in manifest.entries:
            with self.subTest(entry=entry.id):
                path = _target(manifest, entry)
                self.assertTrue(path.is_file(), f"{path} is missing")
                self.assertEqual(manifest_tools.file_sha256(path), entry.sha256)
                self.assertEqual(path.stat().st_size, entry.size_bytes)

    def test_no_unlisted_file_in_folder(self) -> None:
        manifest = _load()
        listed = {_target(manifest, entry).resolve() for entry in manifest.entries}
        for path in _files_in_folder():
            if path.name in UNLISTED_NAMES:
                continue
            with self.subTest(path=path.relative_to(TESTDATA_DIR).as_posix()):
                self.assertIn(path.resolve(), listed)

    def test_terms_allow_redistribution_under_free_license(self) -> None:
        for entry in _load().entries:
            with self.subTest(entry=entry.id):
                self.assertTrue(entry.terms.redistribution)
                self.assertIn(entry.terms.license, ALLOWED_LICENSES)
                self.assertTrue(entry.terms.verified)
                self.assertIsNotNone(entry.terms.terms_url)

    def test_markdown_versions_name_origin_and_command(self) -> None:
        manifest = _load()
        by_id = {entry.id: entry for entry in manifest.entries}
        markdown = [
            entry
            for entry in manifest.entries
            if entry.target is not None and entry.target.endswith(MARKDOWN_SUFFIX)
        ]
        self.assertGreater(len(markdown), 0)
        for entry in markdown:
            with self.subTest(entry=entry.id):
                self.assertIsNotNone(entry.derived_from)
                self.assertIsNotNone(entry.generated_by)
                # For the type checker; the assertions above report the failure.
                assert entry.derived_from is not None
                assert entry.generated_by is not None
                self.assertIn(entry.derived_from, by_id)
                origin = by_id[entry.derived_from]
                assert origin.target is not None
                assert entry.target is not None
                # The command runs in the folder of the files; it names both by
                # their path below that folder.
                self.assertIn(PurePosixPath(origin.target).name, entry.generated_by)
                self.assertIn(PurePosixPath(entry.target).name, entry.generated_by)
                # The tool is pinned by tag and digest.
                self.assertRegex(entry.generated_by, r"pandoc/core:[^\s@]+@sha256:[0-9a-f]{64}")

    def test_readme_names_every_generating_command(self) -> None:
        readme = (TESTDATA_DIR / "README.md").read_text(encoding="utf-8")
        for entry in _load().entries:
            if entry.generated_by is None:
                continue
            with self.subTest(entry=entry.id):
                self.assertIn(entry.generated_by, readme)

    def test_folder_is_smaller_than_limit(self) -> None:
        total = sum(path.stat().st_size for path in _files_in_folder())
        self.assertLess(total, MAX_FOLDER_BYTES)


if __name__ == "__main__":
    unittest.main()
