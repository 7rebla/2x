"""Tests for testfactory.fetch.

They need no internet: a local ``http.server`` on 127.0.0.1 serves test files
from a temporary directory, and the functions are called with
``allow_insecure_loopback=True``. Nothing is written into the repository.
"""

from __future__ import annotations

import contextlib
import dataclasses
import functools
import hashlib
import http.server
import io
import json
import os
import tarfile
import tempfile
import threading
import unittest
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast
from unittest import mock

from testfactory import fetch, manifest_tools
from testfactory.fetch import Options, Settings

COMMIT = "0123456789abcdef0123456789abcdef01234567"
TOP = "repo-" + COMMIT
TODAY = "2026-11-21"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# No pauses and short limits, so that failing downloads do not slow the tests.
FAST = Settings(timeout=5.0, total_timeout=30.0, attempts=2, retry_pause=0.0)

Member = tuple[tarfile.TarInfo, bytes]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_checksum(files: dict[str, bytes]) -> str:
    """The tree checksum written out by hand, following the README."""
    records = sorted((path.encode("utf-8"), sha256_hex(content)) for path, content in files.items())
    return sha256_hex(
        b"".join(path + b"\0" + digest.encode("ascii") + b"\n" for path, digest in records)
    )


def terms() -> dict[str, object]:
    return {
        "holder": "Example Vendor",
        "license": "proprietary",
        "redistribution": False,
        "note": "Download allowed, redistribution not allowed.",
        "verified": False,
    }


def file_entry(entry_id: str, url: str | None, content: bytes | None, **changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": entry_id,
        "title": "Test file " + entry_id,
        "kind": "file",
        "fetch": "auto",
        "url": url,
        "landing_page": "https://example.org/downloads",
        "sha256": None if content is None else sha256_hex(content),
        "target": f"vendor/{entry_id}.bin",
        "terms": terms(),
    }
    data.update(changes)
    return data


def member(name: str, data: bytes = b"", *, kind: bytes = tarfile.REGTYPE, linkname: str = "") -> Member:
    info = tarfile.TarInfo(name)
    info.type = kind
    info.linkname = linkname
    info.mode = 0o755 if kind == tarfile.DIRTYPE else 0o644
    return info, data


def repository_members(files: dict[str, bytes], top: str = TOP) -> list[Member]:
    return [member(top, kind=tarfile.DIRTYPE)] + [
        member(f"{top}/{path}", content) for path, content in files.items()
    ]


def tar_bytes(members: Sequence[Member]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for info, data in members:
            if info.isreg():
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            else:
                tar.addfile(info)
    return buffer.getvalue()


class _Server(http.server.ThreadingHTTPServer):
    """Serves a directory and records every request."""

    daemon_threads = True

    def __init__(self, directory: Path) -> None:
        super().__init__(("127.0.0.1", 0), functools.partial(_Handler, directory=str(directory)))
        self.requests: list[tuple[str, dict[str, str]]] = []
        self.special: dict[str, Callable[[_Handler], None]] = {}


class _Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        server = cast(_Server, self.server)
        server.requests.append((self.path, {key.lower(): value for key, value in self.headers.items()}))
        special = server.special.get(self.path)
        if special is not None:
            special(self)
            return
        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        pass


def respond_status(code: int) -> Callable[[_Handler], None]:
    def respond(request: _Handler) -> None:
        request.send_response(code)
        request.send_header("Content-Length", "0")
        request.end_headers()

    return respond


def respond_redirect(location: str, code: int = 302) -> Callable[[_Handler], None]:
    def respond(request: _Handler) -> None:
        request.send_response(code)
        request.send_header("Location", location)
        request.send_header("Content-Length", "0")
        request.end_headers()

    return respond


def respond_body(body: bytes, content_length: int | None) -> Callable[[_Handler], None]:
    """Send ``body`` with the given (possibly wrong or missing) Content-Length."""

    def respond(request: _Handler) -> None:
        request.send_response(200)
        if content_length is not None:
            request.send_header("Content-Length", str(content_length))
        request.end_headers()
        request.wfile.write(body)

    return respond


class FetchTestCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        self.served = self.tmp / "served"
        self.served.mkdir()
        self.work = self.tmp / "work"
        self.work.mkdir()
        self.manifest_path = self.work / "manifest.yaml"
        self.root = self.work / "extern"

        self.server = _Server(self.served)
        self._thread: threading.Thread | None = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self._thread.start()
        self.addCleanup(self.stop_server)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def stop_server(self) -> None:
        if self._thread is not None:
            self.server.shutdown()
            self.server.server_close()
            self._thread.join()
            self._thread = None

    def serve(self, name: str, content: bytes) -> str:
        path = self.served / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return f"{self.base}/{name}"

    def serve_archive(self, members: Sequence[Member]) -> str:
        """Serve an archive of COMMIT and return the repository address."""
        self.serve(f"owner/repo/archive/{COMMIT}.tar.gz", tar_bytes(members))
        return f"{self.base}/owner/repo"

    def archive_entry(self, repository: str, tree_sha256: str | None, **changes: object) -> dict[str, object]:
        data: dict[str, object] = {
            "id": "vendor-repository",
            "title": "Vendor repository",
            "kind": "git-archive",
            "fetch": "auto",
            "repository": repository,
            "branch": "main",
            "commit": COMMIT,
            "tree_sha256": tree_sha256,
            "target": "vendor/repository",
            "terms": terms(),
        }
        data.update(changes)
        return data

    def write_manifest(self, *entries: dict[str, object], root: str = "extern") -> None:
        text = json.dumps({"schema_version": 1, "root": root, "entries": list(entries)})
        # Stored in the canonical form, as the real manifest is.
        manifest = manifest_tools.parse_manifest(text, allow_insecure_loopback=True)
        manifest_tools.write_manifest(self.manifest_path, manifest)

    def write_raw_manifest(self, *entries: dict[str, object]) -> None:
        """Write without validation, for manifests that must be refused."""
        text = json.dumps({"schema_version": 1, "root": "extern", "entries": list(entries)})
        self.manifest_path.write_text(text, encoding="utf-8")

    def entry(self, entry_id: str) -> manifest_tools.Entry:
        manifest = manifest_tools.load_manifest(self.manifest_path, allow_insecure_loopback=True)
        return next(entry for entry in manifest.entries if entry.id == entry_id)

    def run_fetch(
        self,
        options: Options = Options(),
        *,
        only: Sequence[str] | None = None,
        dest: Path | None = None,
        settings: Settings = FAST,
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = fetch.run(
                self.manifest_path,
                dest=dest,
                only=only,
                options=options,
                settings=settings,
                today=TODAY,
                allow_insecure_loopback=True,
            )
        return code, stdout.getvalue(), stderr.getvalue()

    def run_cli(self, *arguments: str) -> tuple[int, str, str]:
        """Run the real command line, which never allows http://."""
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = fetch.main(list(arguments))
            except SystemExit as error:
                code = error.code if isinstance(error.code, int) else 1
        return code, stdout.getvalue(), stderr.getvalue()

    def rows(self, stdout: str) -> dict[str, tuple[str, str, str]]:
        """Parse the summary table: ID -> (result, HTTP status, size)."""
        lines = stdout.splitlines()
        start = next(index for index, line in enumerate(lines) if line.split() == ["ID", "RESULT", "HTTP", "SIZE"])
        result: dict[str, tuple[str, str, str]] = {}
        for line in lines[start + 1 :]:
            if not line.strip():
                break
            entry_id, outcome, status, size = line.split()
            result[entry_id] = (outcome, status, size)
        return result

    def paths(self) -> list[str]:
        return [path for path, _ in self.server.requests]

    def assert_nothing_left_over(self) -> None:
        self.assertFalse((self.root / fetch.PARTIAL_DIR_NAME).exists())


class FileTest(FetchTestCase):
    def test_success(self) -> None:
        content = b"manual content\n" * 1000
        self.write_manifest(file_entry("manual", self.serve("manual.bin", content), content))
        code, stdout, stderr = self.run_fetch()
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(self.rows(stdout), {"manual": ("loaded", "-", str(len(content)))})
        self.assertEqual((self.root / "vendor" / "manual.bin").read_bytes(), content)
        self.assert_nothing_left_over()

    def test_request_carries_no_personal_data(self) -> None:
        content = b"x"
        self.write_manifest(file_entry("manual", self.serve("manual.bin", content), content))
        self.run_fetch()
        ((path, headers),) = self.server.requests
        self.assertEqual(path, "/manual.bin")
        self.assertEqual(headers["user-agent"], fetch.USER_AGENT)
        self.assertNotIn("python", headers["user-agent"].lower())
        for forbidden in ("cookie", "authorization", "referer", "from", "proxy-authorization"):
            self.assertNotIn(forbidden, headers)

    def test_wrong_checksum_discards_the_file(self) -> None:
        url = self.serve("manual.bin", b"tampered content")
        self.write_manifest(file_entry("manual", url, b"expected content"))
        code, stdout, stderr = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["manual"][0], "mismatch")
        self.assertIn(sha256_hex(b"tampered content"), stdout)
        self.assertIn("FAILED", stderr)
        self.assertFalse((self.root / "vendor" / "manual.bin").exists())
        self.assert_nothing_left_over()

    def test_wrong_checksum_keeps_an_older_file(self) -> None:
        url = self.serve("manual.bin", b"tampered content")
        self.write_manifest(file_entry("manual", url, b"expected content"))
        target = self.root / "vendor" / "manual.bin"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"older content")
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["manual"][0], "mismatch")
        self.assertEqual(target.read_bytes(), b"older content")

    def test_present_file_is_skipped_and_needs_no_network(self) -> None:
        content = b"manual content"
        self.write_manifest(file_entry("manual", self.serve("manual.bin", content), content))
        self.assertEqual(self.run_fetch()[0], 0)
        self.assertEqual(len(self.server.requests), 1)
        self.stop_server()
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout), {"manual": ("ok", "-", str(len(content)))})
        self.assertEqual(len(self.server.requests), 1)

    def test_changed_file_is_loaded_again(self) -> None:
        content = b"manual content"
        self.write_manifest(file_entry("manual", self.serve("manual.bin", content), content))
        target = self.root / "vendor" / "manual.bin"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"damaged")
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["manual"][0], "loaded")
        self.assertEqual(target.read_bytes(), content)

    def test_without_checksum_nothing_is_loaded(self) -> None:
        self.write_manifest(file_entry("manual", self.serve("manual.bin", b"x"), None))
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["manual"][0], "no-checksum")
        self.assertEqual(self.server.requests, [])
        self.assertFalse(self.root.exists())

    def test_record_writes_checksum_and_leaves_existing_ones(self) -> None:
        new = b"new content"
        known = b"known content"
        self.write_manifest(
            file_entry("new", self.serve("new.bin", new), None),
            file_entry("known", self.serve("known.bin", known), known, retrieved_on="2026-01-01"),
            # The server delivers something else than the manifest expects.
            file_entry("changed", self.serve("changed.bin", b"other"), b"expected", size_bytes=None),
        )
        known_before = self.entry("known")
        changed_before = self.entry("changed")
        code, stdout, _ = self.run_fetch(Options(record=True))
        self.assertEqual(code, 1)  # because of "changed"
        rows = self.rows(stdout)
        self.assertEqual(rows["new"], ("recorded", "-", str(len(new))))
        self.assertEqual(rows["known"][0], "loaded")
        self.assertEqual(rows["changed"][0], "mismatch")

        recorded = self.entry("new")
        self.assertEqual(recorded.sha256, sha256_hex(new))
        self.assertEqual(recorded.size_bytes, len(new))
        self.assertEqual(recorded.retrieved_on, TODAY)
        self.assertEqual((self.root / "vendor" / "new.bin").read_bytes(), new)
        self.assertEqual(self.entry("known"), known_before)
        self.assertEqual(self.entry("changed"), changed_before)
        self.assertFalse((self.root / "vendor" / "changed.bin").exists())
        # The manifest is still in the canonical form.
        manifest = manifest_tools.load_manifest(self.manifest_path, allow_insecure_loopback=True)
        self.assertEqual(
            manifest_tools.dump_manifest(manifest).encode("utf-8"), self.manifest_path.read_bytes()
        )

        # A second run finds everything recorded and changes nothing.
        before = self.manifest_path.read_bytes()
        code, stdout, _ = self.run_fetch(Options(record=True), only=["new", "known"])
        self.assertEqual(code, 0)
        self.assertEqual({row[0] for row in self.rows(stdout).values()}, {"ok"})
        self.assertEqual(self.manifest_path.read_bytes(), before)

    def test_record_refuses_a_size_that_contradicts_the_manifest(self) -> None:
        url = self.serve("manual.bin", b"short")
        self.write_manifest(file_entry("manual", url, None, size_bytes=1000))
        before = self.manifest_path.read_bytes()
        code, stdout, _ = self.run_fetch(Options(record=True))
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["manual"][0], "mismatch")
        self.assertEqual(self.manifest_path.read_bytes(), before)
        self.assertFalse((self.root / "vendor" / "manual.bin").exists())

    def test_verify_loads_nothing(self) -> None:
        good = b"good"
        self.write_manifest(
            file_entry("good", self.serve("good.bin", good), good),
            file_entry("changed", self.serve("changed.bin", b"expected"), b"expected"),
            file_entry("absent", self.serve("absent.bin", b"absent"), b"absent"),
            file_entry("unknown", self.serve("unknown.bin", b"unknown"), None),
        )
        vendor = self.root / "vendor"
        vendor.mkdir(parents=True)
        (vendor / "good.bin").write_bytes(good)
        (vendor / "changed.bin").write_bytes(b"damaged")
        (vendor / "unknown.bin").write_bytes(b"unknown")
        code, stdout, _ = self.run_fetch(Options(verify=True))
        self.assertEqual(code, 1)
        self.assertEqual(
            {entry_id: row[0] for entry_id, row in self.rows(stdout).items()},
            {"good": "ok", "changed": "mismatch", "absent": "missing", "unknown": "no-checksum"},
        )
        self.assertEqual(self.server.requests, [])
        self.assertEqual((vendor / "changed.bin").read_bytes(), b"damaged")
        self.assertFalse((vendor / "absent.bin").exists())
        code, stdout, _ = self.run_fetch(Options(verify=True), only=["good"])
        self.assertEqual((code, self.rows(stdout)), (0, {"good": ("ok", "-", "4")}))

    def test_manual_entry_missing(self) -> None:
        self.write_manifest(file_entry("form", None, b"content", fetch="manual"))
        code, stdout, stderr = self.run_fetch()
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["form"][0], "manual")
        self.assertIn("https://example.org/downloads", stdout)
        self.assertIn("vendor/form.bin", stdout)
        self.assertIn("WARNING", stderr)
        code, _, stderr = self.run_fetch(Options(strict=True))
        self.assertEqual(code, 1)
        self.assertIn("FAILED", stderr)
        self.assertEqual(self.server.requests, [])

    def test_manual_entry_present(self) -> None:
        content = b"fetched by hand"
        # Even with an address a manual entry is never loaded.
        url = self.serve("form.bin", content)
        self.write_manifest(file_entry("form", url, content, fetch="manual"))
        target = self.root / "vendor" / "form.bin"
        target.parent.mkdir(parents=True)
        target.write_bytes(content)
        code, stdout, stderr = self.run_fetch(Options(strict=True))
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(self.rows(stdout)["form"], ("ok", "-", str(len(content))))
        target.write_bytes(b"something else")
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["form"][0], "mismatch")
        self.assertEqual(self.server.requests, [])

    def test_manual_entry_without_checksum(self) -> None:
        content = b"fetched by hand"
        self.write_manifest(file_entry("form", None, None, fetch="manual"))
        target = self.root / "vendor" / "form.bin"
        target.parent.mkdir(parents=True)
        target.write_bytes(content)
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["form"][0], "unverified")
        self.assertIsNone(self.entry("form").sha256)
        code, stdout, _ = self.run_fetch(Options(record=True))
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["form"][0], "recorded")
        self.assertEqual(self.entry("form").sha256, sha256_hex(content))
        self.assertEqual(self.entry("form").size_bytes, len(content))
        self.assertEqual(self.entry("form").retrieved_on, TODAY)

    def test_http_error_is_shown_with_status(self) -> None:
        self.server.special["/busy.bin"] = respond_status(503)
        self.write_manifest(
            file_entry("gone", f"{self.base}/gone.bin", b"x"),
            file_entry("busy", f"{self.base}/busy.bin", b"x"),
        )
        code, stdout, stderr = self.run_fetch()
        self.assertEqual(code, 1)
        rows = self.rows(stdout)
        self.assertEqual(rows["gone"], ("failed", "404", "-"))
        self.assertEqual(rows["busy"], ("failed", "503", "-"))
        self.assertIn("FAILED", stderr)
        # 404 is final; 503 is tried again (FAST allows two attempts).
        self.assertEqual(self.paths(), ["/gone.bin", "/busy.bin", "/busy.bin"])
        self.assert_nothing_left_over()

    def test_overloaded_server_is_tried_again(self) -> None:
        content = b"finally"
        self.serve("flaky.bin", content)
        calls: list[int] = []

        def flaky(request: _Handler) -> None:
            calls.append(1)
            if len(calls) == 1:
                respond_status(503)(request)
            else:
                http.server.SimpleHTTPRequestHandler.do_GET(request)

        self.server.special["/flaky.bin"] = flaky
        self.write_manifest(file_entry("flaky", f"{self.base}/flaky.bin", content))
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["flaky"][0], "loaded")
        self.assertEqual(len(calls), 2)

    def test_unreachable_server(self) -> None:
        content = b"x"
        self.write_manifest(file_entry("manual", self.serve("manual.bin", content), content))
        self.stop_server()
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["manual"], ("failed", "-", "-"))
        self.assertIn("connection failed", stdout)

    def test_redirect_within_allowed_addresses_is_followed(self) -> None:
        content = b"moved content"
        self.serve("real.bin", content)
        self.server.special["/old.bin"] = respond_redirect("/real.bin", 301)
        self.write_manifest(file_entry("moved", f"{self.base}/old.bin", content))
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["moved"][0], "loaded")
        self.assertEqual(self.paths(), ["/old.bin", "/real.bin"])

    def test_redirect_to_forbidden_address_is_refused(self) -> None:
        locations = (
            "http://example.org/manual.bin",
            "http://192.168.0.1/manual.bin",
            "ftp://127.0.0.1/manual.bin",
            "file:///etc/passwd",
            "https://user:secret@example.org/manual.bin",
        )
        for number, location in enumerate(locations):
            with self.subTest(location=location):
                self.server.requests.clear()
                self.server.special[f"/r{number}.bin"] = respond_redirect(location)
                self.write_manifest(file_entry("moved", f"{self.base}/r{number}.bin", b"x"))
                code, stdout, _ = self.run_fetch()
                self.assertEqual(code, 1)
                self.assertEqual(self.rows(stdout)["moved"][0], "failed")
                self.assertIn("refused", stdout)
                # One request only: a refused address is not tried again.
                self.assertEqual(self.paths(), [f"/r{number}.bin"])
                self.assertFalse((self.root / "vendor" / "moved.bin").exists())

    def test_endless_redirects_are_stopped(self) -> None:
        self.server.special["/loop.bin"] = respond_redirect("/loop.bin")
        self.write_manifest(file_entry("loop", f"{self.base}/loop.bin", b"x"))
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["loop"][0], "failed")
        self.assertEqual(len(self.server.requests), fetch.MAX_REDIRECTS + 1)

    def test_size_limit(self) -> None:
        content = b"0123456789" * 100
        small = dataclasses.replace(FAST, max_bytes=999)
        # Once with an honest Content-Length, once without any.
        self.serve("announced.bin", content)
        self.server.special["/silent.bin"] = respond_body(content, None)
        self.write_manifest(
            file_entry("announced", f"{self.base}/announced.bin", content),
            file_entry("silent", f"{self.base}/silent.bin", content),
        )
        code, stdout, _ = self.run_fetch(settings=small)
        self.assertEqual(code, 1)
        self.assertEqual({row[0] for row in self.rows(stdout).values()}, {"failed"})
        self.assertIn("allowed", stdout)
        self.assertFalse((self.root / "vendor").exists())
        self.assert_nothing_left_over()
        code, stdout, _ = self.run_fetch(settings=dataclasses.replace(FAST, max_bytes=1000))
        self.assertEqual(code, 0)

    def test_size_from_manifest_limits_the_download(self) -> None:
        content = b"0123456789" * 100
        url = self.serve("manual.bin", content)
        self.write_manifest(file_entry("manual", url, content, size_bytes=10))
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["manual"][0], "failed")
        self.assertFalse((self.root / "vendor" / "manual.bin").exists())

    def test_truncated_download_is_refused(self) -> None:
        self.server.special["/cut.bin"] = respond_body(b"only the start", 1000)
        self.write_manifest(file_entry("cut", f"{self.base}/cut.bin", b"only the start"))
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["cut"][0], "failed")
        self.assertFalse((self.root / "vendor" / "cut.bin").exists())

    def test_dry_run_changes_nothing(self) -> None:
        content = b"content"
        self.write_manifest(
            file_entry("load", self.serve("load.bin", content), content, size_bytes=len(content)),
            file_entry("first", self.serve("first.bin", content), None),
            file_entry("form", None, content, fetch="manual"),
        )
        before = self.manifest_path.read_bytes()
        code, stdout, stderr = self.run_fetch(Options(dry_run=True))
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(
            {entry_id: row[0] for entry_id, row in self.rows(stdout).items()},
            {"load": "would-load", "first": "no-checksum", "form": "manual"},
        )
        self.assertIn("Dry run", stdout)
        code, stdout, _ = self.run_fetch(Options(dry_run=True, record=True, strict=True))
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["first"][0], "would-record")
        self.assertEqual(self.server.requests, [])
        self.assertFalse(self.root.exists())
        self.assertEqual(self.manifest_path.read_bytes(), before)

    def test_only_selects_entries(self) -> None:
        content = b"content"
        self.write_manifest(
            file_entry("first", self.serve("first.bin", content), content),
            file_entry("second", f"{self.base}/missing.bin", content),
            file_entry("third", self.serve("third.bin", content), content),
        )
        code, stdout, _ = self.run_fetch(only=["third", "first"])
        self.assertEqual(code, 0)
        self.assertEqual(list(self.rows(stdout)), ["first", "third"])
        self.assertEqual(self.paths(), ["/first.bin", "/third.bin"])
        code, stdout, stderr = self.run_fetch(only=["first", "fourth"])
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("fourth", stderr)

    def test_entries_that_are_not_loaded(self) -> None:
        local = b"checked in"
        self.write_manifest(
            {
                "id": "simulator",
                "title": "Simulator image",
                "kind": "container-image",
                "fetch": "none",
                "image": "example/simulator",
                "tag": "5.0.0",
                "digest": "sha256:" + "a" * 64,
                "terms": terms(),
            },
            {
                "id": "portal",
                "title": "Download portal",
                "kind": "reference",
                "fetch": "none",
                "url": f"{self.base}/portal",
                "size_bytes": 4096,
                "terms": terms(),
            },
            {
                "id": "free-page",
                "title": "Free page",
                "kind": "local",
                "fetch": "none",
                "sha256": sha256_hex(local),
                "target": "docs/page.rst",
                "terms": terms(),
            },
            root=".",
        )
        page = self.work / "docs" / "page.rst"
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(
            self.rows(stdout),
            {
                "simulator": ("reference-only", "-", "-"),
                "portal": ("reference-only", "-", "4096"),
                "free-page": ("missing", "-", "-"),
            },
        )
        page.parent.mkdir()
        page.write_bytes(local)
        for options in (Options(), Options(verify=True), Options(record=True)):
            code, stdout, _ = self.run_fetch(options)
            self.assertEqual(code, 0)
            self.assertEqual(self.rows(stdout)["free-page"], ("ok", "-", str(len(local))))
        page.write_bytes(b"edited")
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["free-page"][0], "mismatch")
        self.assertEqual(self.server.requests, [])

    def test_dest_replaces_the_root_of_the_manifest(self) -> None:
        content = b"content"
        self.write_manifest(file_entry("manual", self.serve("manual.bin", content), content))
        elsewhere = self.tmp / "elsewhere"
        code, _, _ = self.run_fetch(dest=elsewhere)
        self.assertEqual(code, 0)
        self.assertEqual((elsewhere / "vendor" / "manual.bin").read_bytes(), content)
        self.assertFalse(self.root.exists())

    def test_target_behind_a_link_is_refused(self) -> None:
        content = b"content"
        self.write_manifest(file_entry("manual", self.serve("manual.bin", content), content))
        outside = self.tmp / "outside"
        outside.mkdir()
        self.root.mkdir()
        try:
            os.symlink(outside, self.root / "vendor", target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symbolic links are not available here: {error}")
        for options in (Options(), Options(verify=True), Options(record=True)):
            with self.subTest(options=options):
                code, stdout, _ = self.run_fetch(options)
                self.assertEqual(code, 1)
                self.assertEqual(self.rows(stdout)["manual"][0], "failed")
                self.assertIn("symbolic link", stdout)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(self.server.requests, [])

    def test_working_directory_is_no_target(self) -> None:
        content = b"content"
        url = self.serve("manual.bin", content)
        self.write_manifest(
            file_entry("manual", url, content, target=f"{fetch.PARTIAL_DIR_NAME}/manual.bin")
        )
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["manual"][0], "failed")

    def test_download_refuses_http_without_the_test_switch(self) -> None:
        url = self.serve("manual.bin", b"content")
        destination = self.tmp / "download"
        with self.assertRaises(fetch.FetchError) as caught:
            fetch.download(url, destination, settings=FAST)
        self.assertIn("only https://", str(caught.exception))
        self.assertFalse(caught.exception.retryable)
        self.assertEqual(self.server.requests, [])
        result = fetch.download(url, destination, settings=FAST, allow_insecure_loopback=True)
        self.assertEqual(result, fetch.Download(sha256_hex(b"content"), 7))


class ArchiveTest(FetchTestCase):
    FILES = {
        "README.md": b"# Repository\n",
        "flows/flows.json": b'{"flows": []}\n',
        "plc/project.zap18": b"\x00\x01\x02 binary",
        "docs/übersicht.txt": b"",
    }

    def target(self) -> Path:
        return self.root / "vendor" / "repository"

    def test_archive_is_loaded_and_extracted(self) -> None:
        repository = self.serve_archive(repository_members(self.FILES))
        self.write_manifest(self.archive_entry(repository, tree_checksum(self.FILES)))
        code, stdout, stderr = self.run_fetch()
        self.assertEqual((code, stderr), (0, ""))
        size = sum(len(content) for content in self.FILES.values())
        self.assertEqual(self.rows(stdout), {"vendor-repository": ("loaded", "-", str(size))})
        self.assertEqual(self.paths(), [f"/owner/repo/archive/{COMMIT}.tar.gz"])
        # The top-level directory of the archive is left out.
        for path, content in self.FILES.items():
            self.assertEqual((self.target() / path).read_bytes(), content)
        self.assertEqual(manifest_tools.tree_sha256(self.target()), tree_checksum(self.FILES))
        self.assert_nothing_left_over()

        # Second run and --verify need no network.
        self.stop_server()
        for options in (Options(), Options(verify=True)):
            code, stdout, _ = self.run_fetch(options)
            self.assertEqual(code, 0)
            self.assertEqual(self.rows(stdout)["vendor-repository"][0], "ok")

    def test_changed_tree_is_replaced(self) -> None:
        repository = self.serve_archive(repository_members(self.FILES))
        self.write_manifest(self.archive_entry(repository, tree_checksum(self.FILES)))
        self.target().mkdir(parents=True)
        (self.target() / "stale.txt").write_bytes(b"stale")
        code, stdout, _ = self.run_fetch(Options(verify=True))
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["vendor-repository"][0], "mismatch")
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["vendor-repository"][0], "loaded")
        self.assertFalse((self.target() / "stale.txt").exists())
        self.assertEqual(manifest_tools.tree_sha256(self.target()), tree_checksum(self.FILES))

    def test_wrong_tree_checksum_discards_everything(self) -> None:
        repository = self.serve_archive(repository_members(self.FILES))
        self.write_manifest(self.archive_entry(repository, "f" * 64))
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["vendor-repository"][0], "mismatch")
        self.assertIn(tree_checksum(self.FILES), stdout)
        self.assertFalse(self.target().exists())
        self.assert_nothing_left_over()

    def test_record_writes_tree_checksum(self) -> None:
        repository = self.serve_archive(repository_members(self.FILES))
        self.write_manifest(self.archive_entry(repository, None))
        code, stdout, _ = self.run_fetch(Options(record=True))
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["vendor-repository"][0], "recorded")
        recorded = self.entry("vendor-repository")
        self.assertEqual(recorded.tree_sha256, tree_checksum(self.FILES))
        self.assertEqual(recorded.size_bytes, sum(len(content) for content in self.FILES.values()))
        self.assertEqual(recorded.retrieved_on, TODAY)
        self.assertIsNone(recorded.sha256)

    def test_archive_that_leaves_the_target_is_refused(self) -> None:
        good = repository_members({"README.md": b"readme"})
        cases: dict[str, list[Member]] = {
            "parent directory": [*good, member(f"{TOP}/../../evil.txt", b"evil")],
            "parent directory at the start": [*good, member("../evil.txt", b"evil")],
            "absolute path": [*good, member("/tmp/twox-test-evil.txt", b"evil")],
            "second top-level directory": [*good, member("other/evil.txt", b"evil")],
            "file beside the top-level directory": [*good, member("evil.txt", b"evil")],
            "backslash": [*good, member(f"{TOP}/..\\..\\evil.txt", b"evil")],
            "hard link": [
                *good,
                member(f"{TOP}/link", kind=tarfile.LNKTYPE, linkname=f"{TOP}/README.md"),
            ],
            "hard link to the outside": [
                *good,
                member(f"{TOP}/link", kind=tarfile.LNKTYPE, linkname="../../../etc/passwd"),
            ],
            "character device": [*good, member(f"{TOP}/device", kind=tarfile.CHRTYPE)],
            "block device": [*good, member(f"{TOP}/device", kind=tarfile.BLKTYPE)],
            "pipe": [*good, member(f"{TOP}/pipe", kind=tarfile.FIFOTYPE)],
            "file through a link": [
                *good,
                member(f"{TOP}/escape", kind=tarfile.SYMTYPE, linkname="../../.."),
                member(f"{TOP}/escape/evil.txt", b"evil"),
            ],
        }
        for name, members in cases.items():
            with self.subTest(case=name):
                repository = self.serve_archive(members)
                # --record accepts any checksum, so only the archive check can stop this.
                self.write_manifest(self.archive_entry(repository, None))
                before = self.manifest_path.read_bytes()
                code, stdout, _ = self.run_fetch(Options(record=True))
                self.assertEqual(code, 1)
                self.assertEqual(self.rows(stdout)["vendor-repository"][0], "failed")
                self.assertFalse(self.target().exists())
                self.assert_nothing_left_over()
                self.assertEqual(self.manifest_path.read_bytes(), before)
                # Nothing appeared anywhere else.
                self.assertEqual(sorted(path.name for path in self.work.iterdir()), ["extern", "manifest.yaml"])
                self.assertEqual(sorted(path.name for path in self.tmp.iterdir()), ["served", "work"])
                self.assertFalse(Path("/tmp/twox-test-evil.txt").exists())
                self.assertEqual([path for path in self.root.rglob("*") if path.is_file()], [])

    def test_symbolic_link_becomes_a_small_file(self) -> None:
        members = [
            *repository_members({"README.md": b"readme"}),
            member(f"{TOP}/docs", kind=tarfile.DIRTYPE),
            member(f"{TOP}/docs/latest", kind=tarfile.SYMTYPE, linkname="../README.md"),
            member(f"{TOP}/outside", kind=tarfile.SYMTYPE, linkname="/etc/passwd"),
        ]
        as_files = {
            "README.md": b"readme",
            "docs/latest": b"../README.md",
            "outside": b"/etc/passwd",
        }
        repository = self.serve_archive(members)
        self.write_manifest(self.archive_entry(repository, tree_checksum(as_files)))
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["vendor-repository"][0], "loaded")
        for path, content in as_files.items():
            self.assertFalse((self.target() / path).is_symlink())
            self.assertEqual((self.target() / path).read_bytes(), content)

    def test_extract_archive_limits(self) -> None:
        archive = self.tmp / "archive.tar.gz"
        archive.write_bytes(tar_bytes(repository_members({"a": b"12345", "b": b"12345"})))
        fetch.extract_archive(archive, self.tmp / "fits", max_bytes=10)
        self.assertEqual((self.tmp / "fits" / "b").read_bytes(), b"12345")
        with self.assertRaises(fetch.FetchError) as caught:
            fetch.extract_archive(archive, self.tmp / "content", max_bytes=9)
        self.assertIn("exceeds", str(caught.exception))
        with self.assertRaises(fetch.FetchError) as caught:
            fetch.extract_archive(archive, self.tmp / "members", max_bytes=10, max_members=2)
        self.assertIn("more than 2 members", str(caught.exception))

    def test_extracted_files_keep_no_dangerous_modes(self) -> None:
        info, data = member(f"{TOP}/tool", b"#!/bin/sh\n")
        info.mode = 0o6777
        info.uid = 12345
        info.gid = 12345
        archive = self.tmp / "archive.tar.gz"
        archive.write_bytes(tar_bytes([member(TOP, kind=tarfile.DIRTYPE), (info, data)]))
        fetch.extract_archive(archive, self.tmp / "tree", max_bytes=100)
        status = (self.tmp / "tree" / "tool").stat()
        self.assertEqual(status.st_mode & 0o7022, 0)
        self.assertEqual(status.st_uid, os.getuid())

    def test_broken_or_empty_archive_is_refused(self) -> None:
        cases = {
            "not an archive": b"this is not a tar archive",
            "empty file": b"",
            "empty archive": tar_bytes([]),
            "cut off": tar_bytes(repository_members({"a": os.urandom(4096)}))[:-200],
        }
        for name, content in cases.items():
            with self.subTest(case=name):
                self.serve(f"owner/repo/archive/{COMMIT}.tar.gz", content)
                self.write_manifest(self.archive_entry(f"{self.base}/owner/repo", None))
                code, stdout, _ = self.run_fetch(Options(record=True))
                self.assertEqual(code, 1)
                self.assertEqual(self.rows(stdout)["vendor-repository"][0], "failed")
                self.assertFalse(self.target().exists())
                self.assert_nothing_left_over()

    def test_manual_archive_is_only_verified(self) -> None:
        self.write_manifest(
            self.archive_entry(
                f"{self.base}/owner/repo", tree_checksum({"a.txt": b"a"}), fetch="manual"
            )
        )
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["vendor-repository"][0], "manual")
        self.target().mkdir(parents=True)
        (self.target() / "a.txt").write_bytes(b"a")
        code, stdout, _ = self.run_fetch(Options(strict=True))
        self.assertEqual(code, 0)
        self.assertEqual(self.rows(stdout)["vendor-repository"], ("ok", "-", "1"))
        self.assertEqual(self.server.requests, [])

    def test_archive_url(self) -> None:
        expected = f"https://github.com/owner/repo/archive/{COMMIT}.tar.gz"
        for repository in (
            "https://github.com/owner/repo",
            "https://github.com/owner/repo/",
            "https://github.com/owner/repo.git",
        ):
            with self.subTest(repository=repository):
                self.assertEqual(fetch.archive_url(repository, COMMIT), expected)
        for repository in (
            "https://example.org/owner/repo",
            "https://github.com.example.org/owner/repo",
            "https://github.com/owner",
            "https://github.com/owner/repo/tree/main",
            "https://github.com/owner/repo?ref=main",
            "https://github.com//repo",
        ):
            with self.subTest(repository=repository):
                with self.assertRaises(fetch.FetchError):
                    fetch.archive_url(repository, COMMIT)

    def test_repository_on_unknown_host_is_not_loaded(self) -> None:
        self.write_manifest(self.archive_entry("https://example.org/owner/repo", "f" * 64))
        code, stdout, _ = self.run_fetch()
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["vendor-repository"][0], "failed")
        self.assertIn("github.com", stdout)


class CommandLineTest(FetchTestCase):
    SWITCHES = ("--only", "--verify", "--record", "--dry-run", "--strict", "--manifest", "--dest")

    def test_help_shows_every_switch(self) -> None:
        code, stdout, _ = self.run_cli("--help")
        self.assertEqual(code, 0)
        for switch in self.SWITCHES:
            self.assertIn(switch, stdout)
        self.assertNotIn("loopback", stdout.lower())
        self.assertNotIn("insecure", stdout.lower())

    def test_command_line_always_rejects_http(self) -> None:
        content = b"content"
        served = self.serve("manual.bin", content)
        addresses = (
            served,
            served.replace("127.0.0.1", "localhost"),
            "http://example.org/manual.bin",
        )
        modes: tuple[tuple[str, ...], ...] = (
            (),
            ("--verify",),
            ("--record",),
            ("--dry-run",),
            ("--strict",),
            ("--only", "manual"),
        )
        for address in addresses:
            # Valid for the tests, with the right checksum - and still refused.
            self.write_raw_manifest(file_entry("manual", address, content))
            before = self.manifest_path.read_bytes()
            for mode in modes:
                with self.subTest(address=address, mode=mode):
                    code, stdout, stderr = self.run_cli(
                        *mode, "--manifest", str(self.manifest_path), "--dest", str(self.root)
                    )
                    self.assertEqual((code, stdout), (2, ""))
                    self.assertIn("entry 'manual': field 'url': only https://", stderr)
            self.assertEqual(self.manifest_path.read_bytes(), before)
        self.assertEqual(self.server.requests, [])
        self.assertFalse(self.root.exists())

    def test_command_line_has_no_switch_for_http(self) -> None:
        content = b"content"
        self.write_manifest(file_entry("manual", self.serve("manual.bin", content), content))
        for switch in ("--allow-insecure-loopback", "--allow_insecure_loopback", "--insecure"):
            with self.subTest(switch=switch):
                code, _, stderr = self.run_cli(switch, "--manifest", str(self.manifest_path))
                self.assertEqual(code, 2)
                self.assertIn("unrecognized arguments", stderr)
        environment = {
            "ALLOW_INSECURE_LOOPBACK": "1",
            "TESTFACTORY_ALLOW_INSECURE_LOOPBACK": "1",
            "TWOX_ALLOW_INSECURE_LOOPBACK": "true",
        }
        with mock.patch.dict(os.environ, environment):
            code, _, stderr = self.run_cli("--manifest", str(self.manifest_path))
        self.assertEqual(code, 2)
        self.assertIn("only https://", stderr)
        self.assertEqual(self.server.requests, [])

    def test_verify_and_record_exclude_each_other(self) -> None:
        self.write_manifest()
        code, _, stderr = self.run_cli("--verify", "--record", "--manifest", str(self.manifest_path))
        self.assertEqual(code, 2)
        self.assertIn("not allowed with", stderr)

    def test_exit_codes_of_the_command_line(self) -> None:
        """Without any network: nothing here is loaded."""
        self.stop_server()
        present = b"present"
        self.write_manifest(
            file_entry("present", "https://example.org/present.bin", present),
            file_entry("form", None, b"form", fetch="manual"),
        )
        target = self.root / "vendor" / "present.bin"
        target.parent.mkdir(parents=True)
        target.write_bytes(present)
        arguments = ("--manifest", str(self.manifest_path))

        code, stdout, stderr = self.run_cli(*arguments)
        self.assertEqual(code, 0)
        self.assertEqual(
            self.rows(stdout),
            {"present": ("ok", "-", str(len(present))), "form": ("manual", "-", "-")},
        )
        self.assertIn("WARNING", stderr)
        self.assertEqual(self.run_cli(*arguments, "--strict")[0], 1)
        self.assertEqual(self.run_cli(*arguments, "--strict", "--dry-run")[0], 0)
        self.assertEqual(self.run_cli(*arguments, "--strict", "--only", "present")[0], 0)
        self.assertEqual(self.run_cli(*arguments, "--only", "absent")[0], 2)
        target.write_bytes(b"damaged")
        self.assertEqual(self.run_cli(*arguments, "--verify")[0], 1)
        self.assertEqual(self.run_cli(*arguments, "--verify", "--dry-run")[0], 0)
        # --dest replaces the root: nothing is there.
        code, stdout, _ = self.run_cli(*arguments, "--verify", "--dest", str(self.tmp / "empty"))
        self.assertEqual(code, 1)
        self.assertEqual(self.rows(stdout)["present"][0], "missing")

        self.manifest_path.write_text("schema_version: 1\n", encoding="utf-8")
        code, stdout, stderr = self.run_cli(*arguments)
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("INVALID", stderr)
        code, _, stderr = self.run_cli("--manifest", str(self.tmp / "missing.yaml"))
        self.assertEqual(code, 2)

    def test_max_size_switch(self) -> None:
        self.write_manifest()
        arguments = ("--manifest", str(self.manifest_path))
        self.assertEqual(self.run_cli(*arguments, "--max-size", "10")[0], 0)
        self.assertEqual(self.run_cli(*arguments, "--max-size", "0")[0], 2)

    def test_dry_run_against_the_repository_manifest(self) -> None:
        previous = Path.cwd()
        os.chdir(REPOSITORY_ROOT)
        self.addCleanup(os.chdir, previous)
        code, stdout, _ = self.run_cli("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("Dry run", stdout)
        self.assertEqual(self.server.requests, [])


class SummaryTest(unittest.TestCase):
    def test_table_and_notes(self) -> None:
        text = fetch.format_summary(
            [
                fetch.Outcome("first-entry", fetch.RESULT_LOADED, size_bytes=1234),
                fetch.Outcome("second", fetch.RESULT_FAILED, http_status=404, detail="gone"),
            ]
        )
        self.assertEqual(
            text.splitlines(),
            [
                "ID           RESULT  HTTP  SIZE",
                "first-entry  loaded     -  1234",
                "second       failed   404     -",
                "",
                "2 entries, 1 loaded, 1 failed",
                "",
                "second: failed: gone",
            ],
        )

    def test_exit_code(self) -> None:
        def code(*results: str, options: Options = Options()) -> int:
            return fetch.exit_code([fetch.Outcome("x", result) for result in results], options)

        harmless = (
            fetch.RESULT_LOADED,
            fetch.RESULT_RECORDED,
            fetch.RESULT_OK,
            fetch.RESULT_UNVERIFIED,
            fetch.RESULT_MANUAL,
            fetch.RESULT_REFERENCE,
        )
        self.assertEqual(code(), 0)
        self.assertEqual(code(*harmless), 0)
        self.assertEqual(code(*harmless, options=Options(strict=True)), 1)
        for result in fetch.FAILURE_RESULTS:
            with self.subTest(result=result):
                self.assertEqual(code(*harmless, result), 1)
                self.assertEqual(code(result, options=Options(dry_run=True)), 0)

    def test_text_from_outside_is_made_printable(self) -> None:
        text = fetch.format_summary(
            [fetch.Outcome("x", fetch.RESULT_FAILED, detail="a\x1b[31mb\nc")]
        )
        self.assertEqual(text.splitlines()[-1], "x: failed: a?[31mb?c")


if __name__ == "__main__":
    unittest.main()
