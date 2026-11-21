"""Tests for testfactory.manifest_tools. They need no network."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

from testfactory import manifest_tools
from testfactory.manifest_tools import ManifestError

COMMIT = "0123456789abcdef0123456789abcdef01234567"
SHA_A = "a" * 64
SHA_B = "b" * 64

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def terms(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "holder": "Example Vendor",
        "license": "proprietary",
        "redistribution": False,
        "terms_url": "https://example.org/terms",
        "note": "Download allowed, redistribution not allowed.",
        "checked_on": "2026-11-21",
        "verified": True,
    }
    data.update(changes)
    return data


def file_entry(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "vendor-manual-en",
        "title": "Vendor manual",
        "language": "en",
        "kind": "file",
        "fetch": "auto",
        "url": "https://example.org/docs/manual.pdf",
        "landing_page": "https://example.org/docs",
        "software_version": "1.2.3",
        "document_version": "2026-01",
        "version_source": "title page",
        "sha256": SHA_A,
        "size_bytes": 1234,
        "target": "vendor/manual.pdf",
        "terms": terms(),
        "assigned_to": ["line-1"],
        "retrieved_on": "2026-11-21",
        "notes": None,
    }
    data.update(changes)
    return data


def git_archive_entry(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "vendor-repository",
        "title": "Vendor repository",
        "kind": "git-archive",
        "fetch": "auto",
        "repository": "https://example.org/vendor/repository",
        "branch": "main",
        "commit": COMMIT,
        "tree_sha256": SHA_B,
        "target": "vendor/repository",
        "terms": terms(license="none-stated", verified=False, checked_on=None),
    }
    data.update(changes)
    return data


def container_image_entry(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "vendor-simulator",
        "title": "Vendor simulator image",
        "kind": "container-image",
        "fetch": "none",
        "image": "example/simulator",
        "tag": "5.0.0",
        "digest": "sha256:" + SHA_A,
        "terms": terms(),
    }
    data.update(changes)
    return data


def reference_entry(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "vendor-portal",
        "title": "Vendor download portal",
        "kind": "reference",
        "fetch": "none",
        "url": "https://example.org/portal",
        "terms": terms(),
    }
    data.update(changes)
    return data


def local_entry(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "free-doc-page",
        "title": "Freely licensed documentation page",
        "language": "en",
        "kind": "local",
        "fetch": "none",
        "url": "https://example.org/free/page.rst",
        "repository": "https://example.org/free/docs",
        "commit": COMMIT,
        "derived_from": "free-doc-repository",
        "generated_by": "cp source/page.rst page.rst",
        "sha256": SHA_A,
        "size_bytes": 10,
        "target": "docs/page.rst",
        "terms": terms(license="BSD-2-Clause", redistribution=True),
    }
    data.update(changes)
    return data


def manifest_text(*entries: dict[str, object], root: str = "extern") -> str:
    return json.dumps({"schema_version": 1, "root": root, "entries": list(entries)})


def without(entry: dict[str, object], key: str) -> dict[str, object]:
    return {name: value for name, value in entry.items() if name != key}


class ManifestTestCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)

    def write(self, text: str, name: str = "manifest.yaml") -> Path:
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def problems(
        self, text: str, *, allow_insecure_loopback: bool = False
    ) -> set[tuple[str | None, str]]:
        """Return (entry, field) of every problem found in ``text``."""
        with self.assertRaises(ManifestError) as caught:
            manifest_tools.parse_manifest(text, allow_insecure_loopback=allow_insecure_loopback)
        return {(problem.entry, problem.field) for problem in caught.exception.problems}

    def run_cli(self, *arguments: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = manifest_tools.main(list(arguments))
        return code, stdout.getvalue(), stderr.getvalue()


class ValidExamplesTest(ManifestTestCase):
    def test_valid_example_of_every_kind(self) -> None:
        examples = {
            "file": file_entry(),
            "git-archive": git_archive_entry(),
            "container-image": container_image_entry(),
            "reference": reference_entry(),
            "local": local_entry(),
        }
        self.assertEqual(set(examples), set(manifest_tools.KINDS))
        for kind, example in examples.items():
            with self.subTest(kind=kind):
                manifest = manifest_tools.parse_manifest(manifest_text(example))
                self.assertEqual(len(manifest.entries), 1)
                self.assertEqual(manifest.entries[0].kind, kind)
                self.assertEqual(manifest.entries[0].id, example["id"])

    def test_all_kinds_in_one_manifest(self) -> None:
        manifest = manifest_tools.parse_manifest(
            manifest_text(
                file_entry(),
                git_archive_entry(),
                container_image_entry(),
                reference_entry(),
                local_entry(),
            )
        )
        self.assertEqual(len(manifest.entries), 5)
        entry = manifest.entries[0]
        self.assertEqual(entry.terms.holder, "Example Vendor")
        self.assertEqual(entry.assigned_to, ("line-1",))
        self.assertEqual(entry.size_bytes, 1234)

    def test_checksums_may_be_null_before_first_fetch(self) -> None:
        manifest = manifest_tools.parse_manifest(
            manifest_text(
                file_entry(sha256=None, size_bytes=None),
                git_archive_entry(tree_sha256=None),
            )
        )
        self.assertIsNone(manifest.entries[0].sha256)
        self.assertIsNone(manifest.entries[1].tree_sha256)

    def test_manual_fetch_is_valid_for_file(self) -> None:
        manifest = manifest_tools.parse_manifest(manifest_text(file_entry(fetch="manual")))
        self.assertEqual(manifest.entries[0].fetch, "manual")

    def test_reference_with_repository_and_commit_is_valid(self) -> None:
        entry = reference_entry(
            url=None,
            repository="https://example.org/vendor/repository",
            branch="main",
            commit=COMMIT,
        )
        manifest = manifest_tools.parse_manifest(manifest_text(entry))
        self.assertEqual(manifest.entries[0].commit, COMMIT)

    def test_root_may_be_current_directory(self) -> None:
        manifest = manifest_tools.parse_manifest(manifest_text(local_entry(), root="."))
        self.assertEqual(manifest.root, ".")

    def test_repository_manifest_skeleton_is_valid(self) -> None:
        manifest = manifest_tools.load_manifest(REPOSITORY_ROOT / "testfactory" / "manifest.yaml")
        self.assertEqual(manifest.root, "extern")


class InvalidManifestTest(ManifestTestCase):
    def test_missing_required_field(self) -> None:
        cases: list[tuple[dict[str, object], tuple[str | None, str]]] = [
            (without(file_entry(), "title"), ("vendor-manual-en", "title")),
            (without(file_entry(), "url"), ("vendor-manual-en", "url")),
            (without(file_entry(), "fetch"), ("vendor-manual-en", "fetch")),
            (without(file_entry(), "target"), ("vendor-manual-en", "target")),
            (without(file_entry(), "terms"), ("vendor-manual-en", "terms")),
            (without(file_entry(), "kind"), ("vendor-manual-en", "kind")),
            (without(file_entry(), "id"), ("#1", "id")),
            (file_entry(terms=without(terms(), "holder")), ("vendor-manual-en", "terms.holder")),
            (file_entry(terms=without(terms(), "note")), ("vendor-manual-en", "terms.note")),
            (without(git_archive_entry(), "repository"), ("vendor-repository", "repository")),
            (without(git_archive_entry(), "branch"), ("vendor-repository", "branch")),
            (without(git_archive_entry(), "commit"), ("vendor-repository", "commit")),
            (without(container_image_entry(), "digest"), ("vendor-simulator", "digest")),
        ]
        for entry, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.problems(manifest_text(entry)))

    def test_missing_top_level_fields(self) -> None:
        self.assertEqual(
            self.problems("{}"),
            {(None, "schema_version"), (None, "root"), (None, "entries")},
        )

    def test_wrong_schema_version(self) -> None:
        text = json.dumps({"schema_version": 2, "root": "extern", "entries": []})
        self.assertEqual(self.problems(text), {(None, "schema_version")})

    def test_not_json_notation(self) -> None:
        self.assertEqual(self.problems("schema_version: 1\n"), {(None, "file")})

    def test_duplicate_key_is_rejected(self) -> None:
        text = '{"schema_version": 1, "root": "extern", "root": ".", "entries": []}'
        self.assertEqual(self.problems(text), {(None, "file")})

    def test_unknown_field_is_rejected(self) -> None:
        self.assertIn(
            ("vendor-manual-en", "checksum"),
            self.problems(manifest_text(file_entry(checksum=SHA_A))),
        )

    def test_duplicate_id(self) -> None:
        text = manifest_text(file_entry(), file_entry(target="vendor/other.pdf"))
        self.assertEqual(self.problems(text), {("vendor-manual-en", "id")})

    def test_duplicate_target(self) -> None:
        text = manifest_text(file_entry(), file_entry(id="second-manual"))
        self.assertEqual(self.problems(text), {("second-manual", "target")})

    def test_invalid_id(self) -> None:
        for bad in ("Vendor-Manual", "vendor_manual", "-vendor", "vendor--manual", "vendor manual"):
            with self.subTest(id=bad):
                self.assertIn(("#1", "id"), self.problems(manifest_text(file_entry(id=bad))))

    def test_wrong_commit_length(self) -> None:
        for bad in (COMMIT[:39], COMMIT + "0", COMMIT[:7], COMMIT.upper()):
            with self.subTest(commit=bad):
                self.assertEqual(
                    self.problems(manifest_text(git_archive_entry(commit=bad))),
                    {("vendor-repository", "commit")},
                )

    def test_wrong_checksum_format(self) -> None:
        self.assertEqual(
            self.problems(manifest_text(file_entry(sha256="abc"))),
            {("vendor-manual-en", "sha256")},
        )
        self.assertEqual(
            self.problems(manifest_text(container_image_entry(digest=SHA_A))),
            {("vendor-simulator", "digest")},
        )

    def test_local_without_sha256_is_rejected(self) -> None:
        for entry in (local_entry(sha256=None), without(local_entry(), "sha256")):
            with self.subTest(entry=entry):
                self.assertEqual(self.problems(manifest_text(entry)), {("free-doc-page", "sha256")})

    def test_fields_of_other_kinds_are_rejected(self) -> None:
        cases: list[tuple[dict[str, object], tuple[str | None, str]]] = [
            (file_entry(tree_sha256=SHA_B), ("vendor-manual-en", "tree_sha256")),
            (file_entry(derived_from="other-entry"), ("vendor-manual-en", "derived_from")),
            (
                file_entry(repository="https://example.org/r", commit=COMMIT),
                ("vendor-manual-en", "commit"),
            ),
            (git_archive_entry(sha256=SHA_A), ("vendor-repository", "sha256")),
            (container_image_entry(target="x"), ("vendor-simulator", "target")),
            (reference_entry(sha256=SHA_A), ("vendor-portal", "sha256")),
            (reference_entry(image="example/simulator"), ("vendor-portal", "image")),
        ]
        for entry, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.problems(manifest_text(entry)))

    def test_fetch_mode_must_fit_kind(self) -> None:
        cases = [
            file_entry(fetch="none"),
            container_image_entry(fetch="auto"),
            reference_entry(fetch="manual"),
            local_entry(fetch="auto"),
            file_entry(fetch="sometimes"),
        ]
        for entry in cases:
            with self.subTest(kind=entry["kind"], fetch=entry["fetch"]):
                self.assertEqual(self.problems(manifest_text(entry)), {(entry["id"], "fetch")})

    def test_reference_without_any_address_is_rejected(self) -> None:
        self.assertEqual(
            self.problems(manifest_text(reference_entry(url=None))), {("vendor-portal", "url")}
        )

    def test_unsafe_target_is_rejected(self) -> None:
        for bad in (
            "/etc/passwd",
            "../outside.pdf",
            "a/../../b",
            "a\\b.pdf",
            "C:/x.pdf",
            "a//b",
            "./a",
        ):
            with self.subTest(target=bad):
                self.assertEqual(
                    self.problems(manifest_text(file_entry(target=bad))),
                    {("vendor-manual-en", "target")},
                )

    def test_unsafe_root_is_rejected(self) -> None:
        for bad in ("..", "/extern", "extern/..", ""):
            with self.subTest(root=bad):
                self.assertEqual(self.problems(manifest_text(root=bad)), {(None, "root")})

    def test_terms_are_checked(self) -> None:
        cases: list[tuple[dict[str, object], str]] = [
            (terms(redistribution="no"), "terms.redistribution"),
            (terms(verified=None), "terms.verified"),
            (terms(license="not a license"), "terms.license"),
            (terms(checked_on="21.11.2026"), "terms.checked_on"),
            (terms(checked_on="2026-02-30"), "terms.checked_on"),
            (terms(checked_on=None), "terms.checked_on"),
            (terms(terms_url="http://example.org/terms"), "terms.terms_url"),
            (terms(unknown=1), "terms.unknown"),
        ]
        for changed, field in cases:
            with self.subTest(field=field, terms=changed):
                self.assertEqual(
                    self.problems(manifest_text(file_entry(terms=changed))),
                    {("vendor-manual-en", field)},
                )

    def test_wrong_types_are_rejected(self) -> None:
        cases: list[tuple[dict[str, object], str]] = [
            (file_entry(size_bytes=-1), "size_bytes"),
            (file_entry(size_bytes=True), "size_bytes"),
            (file_entry(size_bytes="12"), "size_bytes"),
            (file_entry(assigned_to="line-1"), "assigned_to"),
            (file_entry(assigned_to=["line-1", "line-1"]), "assigned_to"),
            (file_entry(assigned_to=[1]), "assigned_to"),
            (file_entry(language="fr"), "language"),
            (file_entry(title=""), "title"),
            (file_entry(notes=5), "notes"),
            (file_entry(retrieved_on="yesterday"), "retrieved_on"),
        ]
        for entry, field in cases:
            with self.subTest(field=field, value=entry[field]):
                self.assertEqual(self.problems(manifest_text(entry)), {("vendor-manual-en", field)})

    def test_all_problems_are_reported_together(self) -> None:
        text = manifest_text(file_entry(url=None, sha256="abc"), git_archive_entry(commit="1234"))
        self.assertEqual(
            self.problems(text),
            {
                ("vendor-manual-en", "url"),
                ("vendor-manual-en", "sha256"),
                ("vendor-repository", "commit"),
            },
        )


class AddressTest(ManifestTestCase):
    def test_http_address_is_rejected(self) -> None:
        for field in ("url", "landing_page"):
            with self.subTest(field=field):
                entry = file_entry(**{field: "http://example.org/docs/manual.pdf"})
                self.assertEqual(self.problems(manifest_text(entry)), {("vendor-manual-en", field)})
        self.assertEqual(
            self.problems(manifest_text(git_archive_entry(repository="http://example.org/r"))),
            {("vendor-repository", "repository")},
        )

    def test_other_schemes_and_malformed_addresses_are_rejected(self) -> None:
        bad_addresses = (
            "ftp://example.org/manual.pdf",
            "file:///etc/passwd",
            "git@example.org:vendor/repository.git",
            "example.org/manual.pdf",
            "https:///manual.pdf",
            "https://user:secret@example.org/manual.pdf",
            "https://example.org/a b.pdf",
            "https://example.org:port/manual.pdf",
        )
        for address in bad_addresses:
            with self.subTest(address=address):
                self.assertIsNotNone(manifest_tools.address_problem(address))
                self.assertIsNotNone(
                    manifest_tools.address_problem(address, allow_insecure_loopback=True)
                )

    def test_loopback_is_rejected_by_default(self) -> None:
        for address in ("http://127.0.0.1:8000/manual.pdf", "http://localhost/manual.pdf"):
            with self.subTest(address=address):
                self.assertEqual(
                    self.problems(manifest_text(file_entry(url=address))),
                    {("vendor-manual-en", "url")},
                )

    def test_allow_insecure_loopback_allows_only_loopback(self) -> None:
        for address in ("http://127.0.0.1:8000/manual.pdf", "http://localhost:8000/manual.pdf"):
            with self.subTest(address=address):
                manifest = manifest_tools.parse_manifest(
                    manifest_text(file_entry(url=address)), allow_insecure_loopback=True
                )
                self.assertEqual(manifest.entries[0].url, address)
        not_loopback = (
            "http://example.org/manual.pdf",
            "http://127.0.0.1.example.org/manual.pdf",
            "http://localhost.example.org/manual.pdf",
            "http://127.0.0.2/manual.pdf",
            "http://192.168.0.1/manual.pdf",
            "http://localhost@example.org/manual.pdf",
            "ftp://127.0.0.1/manual.pdf",
        )
        for address in not_loopback:
            with self.subTest(address=address):
                self.assertEqual(
                    self.problems(
                        manifest_text(file_entry(url=address)), allow_insecure_loopback=True
                    ),
                    {("vendor-manual-en", "url")},
                )

    def test_load_manifest_passes_loopback_switch(self) -> None:
        path = self.write(manifest_text(file_entry(url="http://127.0.0.1:8000/manual.pdf")))
        with self.assertRaises(ManifestError):
            manifest_tools.load_manifest(path)
        manifest = manifest_tools.load_manifest(path, allow_insecure_loopback=True)
        self.assertEqual(manifest.entries[0].url, "http://127.0.0.1:8000/manual.pdf")


class CommandLineTest(ManifestTestCase):
    def test_check_reports_success(self) -> None:
        path = self.write(manifest_text(file_entry(), local_entry()))
        code, stdout, stderr = self.run_cli("check", str(path))
        self.assertEqual(code, 0)
        self.assertIn("OK (2 entries)", stdout)
        self.assertEqual(stderr, "")

    def test_check_names_entry_and_field(self) -> None:
        path = self.write(manifest_text(git_archive_entry(commit="1234")))
        code, stdout, stderr = self.run_cli("check", str(path))
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("entry 'vendor-repository': field 'commit'", stderr)

    def test_check_fails_for_missing_file(self) -> None:
        code, _, stderr = self.run_cli("check", str(self.tmp / "missing.yaml"))
        self.assertEqual(code, 1)
        self.assertIn("field 'file'", stderr)

    def test_command_line_always_rejects_http(self) -> None:
        addresses = (
            "http://example.org/manual.pdf",
            "http://127.0.0.1:8000/manual.pdf",
            "http://localhost:8000/manual.pdf",
        )
        for address in addresses:
            for options in ((), ("--complete",)):
                with self.subTest(address=address, options=options):
                    path = self.write(manifest_text(file_entry(url=address)))
                    code, _, stderr = self.run_cli("check", *options, str(path))
                    self.assertEqual(code, 1)
                    self.assertIn("entry 'vendor-manual-en': field 'url'", stderr)

    def test_command_line_has_no_loopback_option(self) -> None:
        path = self.write(manifest_text(file_entry(url="http://127.0.0.1:8000/manual.pdf")))
        for option in ("--allow-insecure-loopback", "--allow_insecure_loopback", "--insecure"):
            with self.subTest(option=option):
                with (
                    self.assertRaises(SystemExit) as caught,
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    manifest_tools.main(["check", option, str(path)])
                self.assertEqual(caught.exception.code, 2)

    def test_complete_fails_for_missing_checksum(self) -> None:
        path = self.write(
            manifest_text(file_entry(sha256=None), git_archive_entry(tree_sha256=None))
        )
        code, _, _ = self.run_cli("check", str(path))
        self.assertEqual(code, 0)
        code, stdout, stderr = self.run_cli("check", "--complete", str(path))
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("entry 'vendor-manual-en': field 'sha256'", stderr)
        self.assertIn("entry 'vendor-repository': field 'tree_sha256'", stderr)

    def test_complete_ignores_manual_entries_and_passes_when_complete(self) -> None:
        path = self.write(
            manifest_text(
                file_entry(fetch="manual", sha256=None),
                git_archive_entry(),
                container_image_entry(),
                reference_entry(),
                local_entry(),
            )
        )
        code, stdout, _ = self.run_cli("check", "--complete", str(path))
        self.assertEqual(code, 0)
        self.assertIn("OK (5 entries)", stdout)

    def test_default_path_is_the_test_factory_manifest(self) -> None:
        previous = Path.cwd()
        os.chdir(REPOSITORY_ROOT)
        self.addCleanup(os.chdir, previous)
        code, stdout, _ = self.run_cli("check")
        self.assertEqual(code, 0)
        self.assertIn("testfactory/manifest.yaml: OK", stdout)


class WriteTest(ManifestTestCase):
    def full_manifest(self) -> manifest_tools.Manifest:
        return manifest_tools.parse_manifest(
            manifest_text(
                file_entry(title="Handbuch für Gerät \u2013 Ausgabe „A“", language="de"),
                git_archive_entry(tree_sha256=None),
                container_image_entry(),
                reference_entry(),
                local_entry(),
            )
        )

    def test_written_manifest_is_stable(self) -> None:
        first = manifest_tools.dump_manifest(self.full_manifest())
        reloaded = manifest_tools.parse_manifest(first)
        self.assertEqual(reloaded, self.full_manifest())
        self.assertEqual(manifest_tools.dump_manifest(reloaded), first)

    def test_write_and_load_give_identical_bytes(self) -> None:
        path = self.tmp / "manifest.yaml"
        manifest_tools.write_manifest(path, self.full_manifest())
        first = path.read_bytes()
        manifest_tools.write_manifest(path, manifest_tools.load_manifest(path))
        self.assertEqual(path.read_bytes(), first)
        self.assertTrue(first.endswith(b"}\n"))
        self.assertNotIn(b"\r", first)
        self.assertIn("für Gerät \u2013 Ausgabe „A“".encode(), first)

    def test_key_order_of_input_does_not_matter(self) -> None:
        entry = file_entry()
        reversed_entry = dict(reversed(list(entry.items())))
        self.assertEqual(
            manifest_tools.dump_manifest(manifest_tools.parse_manifest(manifest_text(entry))),
            manifest_tools.dump_manifest(
                manifest_tools.parse_manifest(manifest_text(reversed_entry))
            ),
        )

    def test_repository_manifest_is_in_canonical_form(self) -> None:
        path = REPOSITORY_ROOT / "testfactory" / "manifest.yaml"
        manifest = manifest_tools.load_manifest(path)
        self.assertEqual(manifest_tools.dump_manifest(manifest).encode("utf-8"), path.read_bytes())

    def test_target_path(self) -> None:
        manifest = manifest_tools.parse_manifest(manifest_text(file_entry(), reference_entry()))
        manifest_path = Path("testfactory") / "manifest.yaml"
        self.assertEqual(
            manifest_tools.target_path(manifest_path, manifest, manifest.entries[0]),
            Path("testfactory") / "extern" / "vendor" / "manual.pdf",
        )
        self.assertIsNone(manifest_tools.target_path(manifest_path, manifest, manifest.entries[1]))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TreeChecksumTest(ManifestTestCase):
    def make_tree(self, base: Path) -> None:
        (base / "sub" / "deeper").mkdir(parents=True)
        (base / "b.txt").write_bytes(b"second\n")
        (base / "a.txt").write_bytes(b"first\n")
        (base / "sub" / "c.bin").write_bytes(b"\x00\x01\x02")
        (base / "sub" / "deeper" / "ü.txt").write_bytes(b"")

    def expected(self) -> str:
        # Written out by hand, following the definition in the README.
        records = [
            ("a.txt", b"first\n"),
            ("b.txt", b"second\n"),
            ("sub/c.bin", b"\x00\x01\x02"),
            ("sub/deeper/ü.txt", b""),
        ]
        data = b"".join(
            path.encode("utf-8") + b"\0" + sha256_hex(content).encode("ascii") + b"\n"
            for path, content in records
        )
        return sha256_hex(data)

    def test_small_directory(self) -> None:
        base = self.tmp / "tree"
        self.make_tree(base)
        self.assertEqual(manifest_tools.tree_sha256(base), self.expected())
        self.assertEqual(manifest_tools.tree_sha256(str(base)), self.expected())

    def test_empty_directories_times_and_modes_do_not_count(self) -> None:
        base = self.tmp / "tree"
        self.make_tree(base)
        (base / "empty" / "nested").mkdir(parents=True)
        os.utime(base / "a.txt", (0, 0))
        os.chmod(base / "b.txt", 0o600)
        self.assertEqual(manifest_tools.tree_sha256(base), self.expected())

    def test_content_and_path_count(self) -> None:
        base = self.tmp / "tree"
        self.make_tree(base)
        (base / "a.txt").write_bytes(b"changed\n")
        self.assertNotEqual(manifest_tools.tree_sha256(base), self.expected())
        (base / "a.txt").write_bytes(b"first\n")
        self.assertEqual(manifest_tools.tree_sha256(base), self.expected())
        (base / "a.txt").rename(base / "renamed.txt")
        self.assertNotEqual(manifest_tools.tree_sha256(base), self.expected())

    def test_empty_directory(self) -> None:
        base = self.tmp / "empty"
        base.mkdir()
        self.assertEqual(manifest_tools.tree_sha256(base), sha256_hex(b""))

    def test_sorting_is_by_path_bytes(self) -> None:
        base = self.tmp / "tree"
        (base / "a").mkdir(parents=True)
        (base / "a" / "x").write_bytes(b"1")
        (base / "a.txt").write_bytes(b"2")
        (base / "B").write_bytes(b"3")
        records = [("B", b"3"), ("a.txt", b"2"), ("a/x", b"1")]
        data = b"".join(
            path.encode("utf-8") + b"\0" + sha256_hex(content).encode("ascii") + b"\n"
            for path, content in records
        )
        self.assertEqual(manifest_tools.tree_sha256(base), sha256_hex(data))

    def test_symbolic_link_counts_as_file_with_target_text(self) -> None:
        linked = self.tmp / "linked"
        linked.mkdir()
        (linked / "a.txt").write_bytes(b"first\n")
        try:
            os.symlink("a.txt", linked / "link.txt")
            os.symlink("..", linked / "up")
        except OSError as error:
            self.skipTest(f"symbolic links are not available here: {error}")
        plain = self.tmp / "plain"
        plain.mkdir()
        (plain / "a.txt").write_bytes(b"first\n")
        (plain / "link.txt").write_bytes(b"a.txt")
        (plain / "up").write_bytes(b"..")
        self.assertEqual(manifest_tools.tree_sha256(linked), manifest_tools.tree_sha256(plain))

    def test_not_a_directory(self) -> None:
        with self.assertRaises(ValueError):
            manifest_tools.tree_sha256(self.tmp / "missing")

    def test_file_sha256(self) -> None:
        path = self.tmp / "file.bin"
        path.write_bytes(b"first\n")
        self.assertEqual(manifest_tools.file_sha256(path), sha256_hex(b"first\n"))


class CheckedTargetPathTest(ManifestTestCase):
    """Follow-up 1: the resolved target must stay below the resolved root."""

    def symlink(self, target: Path | str, link: Path) -> None:
        try:
            os.symlink(target, link, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symbolic links are not available here: {error}")

    def test_plain_target_is_returned(self) -> None:
        root = self.tmp / "extern"
        (root / "vendor").mkdir(parents=True)
        self.assertEqual(
            manifest_tools.checked_target_path(root, "vendor/manual.pdf"),
            root / "vendor" / "manual.pdf",
        )
        # Nothing of the chain has to exist yet.
        self.assertEqual(
            manifest_tools.checked_target_path(self.tmp / "missing", "a/b/c.pdf"),
            self.tmp / "missing" / "a" / "b" / "c.pdf",
        )

    def test_unclean_target_is_rejected(self) -> None:
        for bad in ("../outside.pdf", "/etc/passwd", "a/../../b", "a\\b", ".", ""):
            with self.subTest(target=bad), self.assertRaises(manifest_tools.UnsafePathError):
                manifest_tools.checked_target_path(self.tmp, bad)

    def test_link_in_the_chain_is_rejected(self) -> None:
        root = self.tmp / "extern"
        root.mkdir()
        outside = self.tmp / "outside"
        outside.mkdir()
        (root / "inside").mkdir()
        self.symlink(outside, root / "escape")
        # A link is rejected even if it points to a place below the root.
        self.symlink(root / "inside", root / "alias")
        for target in ("escape/manual.pdf", "escape", "alias/manual.pdf", "inside/../escape/x"):
            with self.subTest(target=target), self.assertRaises(manifest_tools.UnsafePathError):
                manifest_tools.checked_target_path(root, target)
        self.assertEqual(list(outside.iterdir()), [])

    def test_link_as_target_is_rejected(self) -> None:
        root = self.tmp / "extern"
        root.mkdir()
        (self.tmp / "secret.txt").write_bytes(b"secret")
        try:
            os.symlink(self.tmp / "secret.txt", root / "manual.pdf")
            os.symlink(root / "nowhere", root / "dangling.pdf")
        except OSError as error:
            self.skipTest(f"symbolic links are not available here: {error}")
        for target in ("manual.pdf", "dangling.pdf"):
            with self.subTest(target=target), self.assertRaises(manifest_tools.UnsafePathError):
                manifest_tools.checked_target_path(root, target)

    def test_root_itself_may_be_reached_through_a_link(self) -> None:
        real = self.tmp / "real"
        real.mkdir()
        self.symlink(real, self.tmp / "extern")
        self.assertEqual(
            manifest_tools.checked_target_path(self.tmp / "extern", "manual.pdf"),
            self.tmp / "extern" / "manual.pdf",
        )

    def test_root_path(self) -> None:
        manifest = manifest_tools.parse_manifest(manifest_text(file_entry()))
        self.assertEqual(
            manifest_tools.root_path(Path("testfactory") / "manifest.yaml", manifest),
            Path("testfactory") / "extern",
        )


class FollowUpValidationTest(ManifestTestCase):
    def test_target_inside_another_target_is_rejected(self) -> None:
        """Follow-up 2, in both orders of the entries."""
        inner = file_entry(target="vendor/repository/docs/manual.pdf")
        outer = git_archive_entry(target="vendor/repository")
        for entries in ((inner, outer), (outer, inner)):
            with self.subTest(first=entries[0]["id"]):
                self.assertEqual(
                    self.problems(manifest_text(*entries)), {("vendor-manual-en", "target")}
                )

    def test_targets_are_compared_by_segments(self) -> None:
        manifest = manifest_tools.parse_manifest(
            manifest_text(
                git_archive_entry(target="vendor/repository"),
                file_entry(target="vendor/repository-2/manual.pdf"),
                file_entry(id="second-manual", target="vendor/repository.pdf"),
                file_entry(id="third-manual", target="vendor/manual.pdf"),
            )
        )
        self.assertEqual(len(manifest.entries), 4)

    def test_schema_version_must_be_an_integer(self) -> None:
        """Follow-up 4."""
        for bad in ("1.0", '"1"', "true", "1e0", "[1]"):
            with self.subTest(schema_version=bad):
                text = f'{{"schema_version": {bad}, "root": "extern", "entries": []}}'
                self.assertEqual(self.problems(text), {(None, "schema_version")})
        text = '{"schema_version": 1, "root": "extern", "entries": []}'
        self.assertEqual(manifest_tools.parse_manifest(text).schema_version, 1)

    def test_reference_may_have_size_bytes(self) -> None:
        """Follow-up 5."""
        manifest = manifest_tools.parse_manifest(manifest_text(reference_entry(size_bytes=4096)))
        self.assertEqual(manifest.entries[0].size_bytes, 4096)
        self.assertEqual(
            manifest_tools.parse_manifest(manifest_tools.dump_manifest(manifest)), manifest
        )
        self.assertEqual(
            self.problems(manifest_text(container_image_entry(size_bytes=4096))),
            {("vendor-simulator", "size_bytes")},
        )

    def test_manual_file_needs_landing_page_instead_of_url(self) -> None:
        """Follow-up 6."""
        manifest = manifest_tools.parse_manifest(
            manifest_text(file_entry(fetch="manual", url=None, sha256=None))
        )
        self.assertIsNone(manifest.entries[0].url)
        self.assertEqual(
            self.problems(manifest_text(file_entry(fetch="manual", landing_page=None))),
            {("vendor-manual-en", "landing_page")},
        )
        self.assertEqual(
            self.problems(manifest_text(file_entry(fetch="manual", url=None, landing_page=None))),
            {("vendor-manual-en", "landing_page")},
        )
        # Fetched automatically: the address stays required, the page optional.
        self.assertEqual(
            self.problems(manifest_text(file_entry(url=None))), {("vendor-manual-en", "url")}
        )
        manifest_tools.parse_manifest(manifest_text(file_entry(landing_page=None)))


class UnreadableDirectoryTest(ManifestTestCase):
    def test_unreadable_subdirectory_is_an_error(self) -> None:
        """Follow-up 3. Simulated, because root in a container may read everything."""
        base = self.tmp / "tree"
        (base / "open").mkdir(parents=True)
        (base / "locked").mkdir()
        (base / "open" / "a.txt").write_bytes(b"first\n")
        (base / "locked" / "b.txt").write_bytes(b"second\n")
        complete = manifest_tools.tree_sha256(base)
        real_scandir = os.scandir

        def scandir(path: str | os.PathLike[str]) -> Iterator[os.DirEntry[str]]:
            if Path(os.fspath(path)).name == "locked":
                raise PermissionError(13, "Permission denied", os.fspath(path))
            return real_scandir(path)

        with mock.patch.object(os, "scandir", scandir), self.assertRaises(PermissionError):
            manifest_tools.tree_sha256(base)
        self.assertEqual(manifest_tools.tree_sha256(base), complete)

    def test_really_unreadable_subdirectory_is_an_error(self) -> None:
        base = self.tmp / "tree"
        (base / "locked").mkdir(parents=True)
        (base / "locked" / "b.txt").write_bytes(b"second\n")
        os.chmod(base / "locked", 0)
        self.addCleanup(os.chmod, base / "locked", 0o700)
        if os.access(base / "locked", os.R_OK):
            self.skipTest("this user may read every directory")
        with self.assertRaises(PermissionError):
            manifest_tools.tree_sha256(base)


class FormatCommandTest(ManifestTestCase):
    """Follow-up 7."""

    def test_format_rewrites_in_canonical_form(self) -> None:
        text = manifest_text(file_entry(), reference_entry()).replace("\n", "\r\n")
        path = self.write(text)
        before = manifest_tools.load_manifest(path)
        code, stdout, stderr = self.run_cli("format", str(path))
        self.assertEqual((code, stderr), (0, ""))
        self.assertIn("rewritten in canonical form", stdout)
        self.assertEqual(manifest_tools.load_manifest(path), before)
        canonical = path.read_bytes()
        self.assertEqual(canonical, manifest_tools.dump_manifest(before).encode("utf-8"))
        code, stdout, _ = self.run_cli("format", str(path))
        self.assertEqual(code, 0)
        self.assertIn("already in canonical form", stdout)
        self.assertEqual(path.read_bytes(), canonical)

    def test_format_check_does_not_write(self) -> None:
        path = self.write(manifest_text(file_entry()))
        original = path.read_bytes()
        code, stdout, stderr = self.run_cli("format", "--check", str(path))
        self.assertEqual((code, stdout), (1, ""))
        self.assertIn("NOT in canonical form", stderr)
        self.assertEqual(path.read_bytes(), original)
        self.run_cli("format", str(path))
        code, _, _ = self.run_cli("format", "--check", str(path))
        self.assertEqual(code, 0)

    def test_format_leaves_invalid_file_untouched(self) -> None:
        for entry in (git_archive_entry(commit="1234"), file_entry(url="http://127.0.0.1/a.pdf")):
            with self.subTest(entry=entry["id"]):
                path = self.write(manifest_text(entry))
                original = path.read_bytes()
                code, stdout, stderr = self.run_cli("format", str(path))
                self.assertEqual((code, stdout), (1, ""))
                self.assertIn("INVALID", stderr)
                self.assertEqual(path.read_bytes(), original)
        code, _, stderr = self.run_cli("format", str(self.tmp / "missing.yaml"))
        self.assertEqual(code, 1)
        self.assertIn("field 'file'", stderr)

    def test_format_default_path_is_the_test_factory_manifest(self) -> None:
        previous = Path.cwd()
        os.chdir(REPOSITORY_ROOT)
        self.addCleanup(os.chdir, previous)
        code, stdout, _ = self.run_cli("format", "--check")
        self.assertEqual(code, 0)
        self.assertIn("testfactory/manifest.yaml: already in canonical form", stdout)


if __name__ == "__main__":
    unittest.main()
