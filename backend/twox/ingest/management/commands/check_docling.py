"""Check whether docling-serve behind ``TWOX_DOCLING_URL`` is reachable.

Three steps: resolve the host name, open a TCP connection, ask the service for
its version (``GET /version``). The command prints exactly one line that starts
with ``OK:`` (exit code 0) or ``FAILED:`` (exit code 1).

Nothing is sent to the service except that ``GET`` request, and nothing of the
answer is printed except the version of docling-serve itself.

With ``--convert PATH`` (``-`` for standard input) the command converts one
file through :mod:`twox.ingest.docling` instead and prints ``OK:`` with pages,
texts, tables and run time, or ``FAILED:`` with the kind of error. With
``--json-out -`` it prints only the DoclingDocument JSON (errors go to standard
error). Run it in ``api`` or ``worker``: ``backend-dev`` cannot reach docling.
"""

import json
import re
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.client import HTTPException
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from twox.ingest import docling
from twox.ingest.docling import (
    ConversionResult,
    DoclingError,
    DoclingUnavailableError,
    TaskStatus,
)

DEFAULT_TIMEOUT_SECONDS = 5.0
# --convert: docling-serve may hold a poll answer up to POLL_WAIT_SECONDS until
# the task finishes (its local engine answered at once in work order 041);
# between two polls the command waits POLL_INTERVAL_SECONDS.
POLL_WAIT_SECONDS = 5.0
POLL_INTERVAL_SECONDS = 2.0
# Time a task may wait in docling-serve's queue on top of the document limit.
QUEUE_MARGIN_SECONDS = 10 * 60.0
# The upload is named upload<suffix>; docling-serve tells the format by it.
UPLOAD_STEM = "upload"
STDIN_DEFAULT_SUFFIX = ".pdf"
SUFFIX_RE = re.compile(r"\.[A-Za-z0-9]{1,10}")
# A version document is a few hundred bytes; protects against an endless answer.
MAX_RESPONSE_BYTES = 64 * 1024
# Key of docling-serve's own version in the JSON object returned by /version.
VERSION_KEY = "docling-serve"
_DEFAULT_PORTS = {"http": 80, "https": 443}


@dataclass(frozen=True)
class CheckResult:
    """Outcome of the check: one line of text and whether it succeeded."""

    ok: bool
    message: str

    @property
    def line(self) -> str:
        return f"{'OK' if self.ok else 'FAILED'}: {self.message}"


def _failed(message: str) -> CheckResult:
    return CheckResult(ok=False, message=message)


def _is_timeout(error: BaseException) -> bool:
    """Return whether ``error`` is a timeout, also when urllib wrapped it."""
    if isinstance(error, TimeoutError):
        return True
    return isinstance(error, urllib.error.URLError) and isinstance(error.reason, TimeoutError)


def _seconds(timeout: float) -> str:
    return f"{timeout:g}s"


def _parse_version(body: bytes) -> str | None:
    """Return the docling-serve version from a ``/version`` answer, else ``None``."""
    try:
        document = json.loads(body)
    except ValueError:
        return None
    if not isinstance(document, dict):
        return None
    version = document.get(VERSION_KEY)
    if not isinstance(version, str) or not version.strip() or len(version) > 64:
        return None
    if not version.isprintable():
        return None
    return version.strip()


def _fetch_version(base_url: str, version_url: str, timeout: float) -> CheckResult:
    """Step 3: request the version document and read docling-serve's version."""
    # No proxy on purpose: the check must talk to the configured address itself.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(version_url, headers={"Accept": "application/json"})
    try:
        with opener.open(request, timeout=timeout) as response:
            status: int = response.status
            body: bytes = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        hint = ""
        if error.code == 403:
            hint = " - DOCLING_SERVE_SHOW_VERSION_INFO must stay enabled"
        return _failed(f"unexpected response from {version_url}: HTTP {error.code}{hint}")
    except (urllib.error.URLError, HTTPException, OSError) as error:
        if _is_timeout(error):
            return _failed(
                f"timeout waiting for an answer from {version_url} after {_seconds(timeout)}"
                " - the port accepts connections but nothing answers"
            )
        return _failed(
            f"unexpected response from {version_url}: no valid HTTP answer ({type(error).__name__})"
        )

    if status != 200:
        return _failed(f"unexpected response from {version_url}: HTTP {status}")
    version = None if len(body) > MAX_RESPONSE_BYTES else _parse_version(body)
    if version is None:
        return _failed(
            f"unexpected response from {version_url}: HTTP {status},"
            f" but no {VERSION_KEY!r} version in it"
        )
    return CheckResult(ok=True, message=f"docling-serve {version} at {base_url}")


def check_docling(base_url: str, timeout: float) -> CheckResult:
    """Check docling-serve at ``base_url`` in three steps."""
    try:
        parts = urlsplit(base_url)
        host = parts.hostname
        port = parts.port or _DEFAULT_PORTS.get(parts.scheme)
    except ValueError:
        host, port = None, None
    if not host or port is None:
        return _failed(
            f"invalid address {base_url!r} - TWOX_DOCLING_URL must look like http://host:port"
        )
    target = f"{host}:{port}"
    base = base_url.rstrip("/")

    # Step 1: the host name resolves.
    try:
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        return _failed(
            f"cannot resolve host {host!r} ({error.strerror or error})"
            " - is the docling container running in the same compose project?"
        )

    # Step 2: the port accepts connections.
    try:
        socket.create_connection((host, port), timeout=timeout).close()
    except ConnectionRefusedError:
        return _failed(
            f"connection refused by {target} - docling-serve is not listening (yet) on this port"
        )
    except TimeoutError:
        return _failed(f"timeout connecting to {target} after {_seconds(timeout)}")
    except OSError as error:
        return _failed(f"connection error to {target} ({error.strerror or error})")

    # Step 3: the service names its version.
    return _fetch_version(base, base + "/version", timeout)


def convert(
    stream: BinaryIO, filename: str, page_range: tuple[int, int] | None
) -> tuple[ConversionResult, float]:
    """Convert ``stream`` through the document converter; return the result and the seconds."""
    converter = docling.get_document_converter()
    started = time.monotonic()
    task_id = converter.submit(
        stream, filename, docling.guess_content_type(filename), page_range=page_range
    )
    deadline = started + docling.DEFAULT_DOCUMENT_TIMEOUT_SECONDS + QUEUE_MARGIN_SECONDS
    while not converter.poll(task_id, wait=POLL_WAIT_SECONDS).finished:
        if time.monotonic() > deadline:
            raise DoclingUnavailableError("the conversion did not finish within the time limit")
        time.sleep(POLL_INTERVAL_SECONDS)
    # The answer goes to a file first, as in the ingest task (046).
    with tempfile.TemporaryFile() as sink:
        converter.fetch(task_id, sink)
        sink.seek(0)
        result = docling.load_result(sink)
    return result, time.monotonic() - started


def _summary(result: ConversionResult, seconds: float) -> str:
    """One line with pages, texts, tables and run time of a conversion."""
    document = result.document
    counts = {key: len(document.get(key) or ()) for key in ("pages", "texts", "tables")}
    partial = ", partial success" if result.status is TaskStatus.PARTIAL_SUCCESS else ""
    return (
        f"converted {counts['pages']} pages, {counts['texts']} texts, {counts['tables']} tables"
        f" in {seconds:.1f}s (docling: {result.processing_time:.1f}s{partial})"
    )


def _positive_seconds(value: str) -> float:
    """Parse the value of ``--timeout``."""
    seconds = float(value)
    if not 0 < seconds < float("inf"):
        raise ValueError(value)
    return seconds


def _suffix(value: str) -> str:
    """Parse the value of ``--suffix``."""
    if not SUFFIX_RE.fullmatch(value):
        raise ValueError(value)
    return value.lower()


class Command(BaseCommand):
    help = (
        "Check whether docling-serve at TWOX_DOCLING_URL is reachable and report its version."
        " With --convert, convert one file instead and report pages, texts, tables and run"
        " time. Prints one line starting with OK: (exit code 0) or FAILED: (exit code 1);"
        " with --json-out - only the DoclingDocument JSON."
    )
    # The check needs neither the database nor the system checks.
    requires_system_checks = []  # noqa: RUF012

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--timeout",
            type=_positive_seconds,
            default=DEFAULT_TIMEOUT_SECONDS,
            metavar="SECONDS",
            help="Time limit per step of the reachability check in seconds (default: %(default)g).",
        )
        parser.add_argument(
            "--convert",
            metavar="PATH",
            help="Convert this file (- reads standard input) instead of checking the version.",
        )
        parser.add_argument(
            "--page-range",
            nargs=2,
            type=int,
            metavar=("FIRST", "LAST"),
            help="Convert only these pages (1-based, inclusive); needs --convert.",
        )
        parser.add_argument(
            "--json-out",
            choices=["-"],
            help="Write only the DoclingDocument JSON to standard output; needs --convert.",
        )
        parser.add_argument(
            "--suffix",
            type=_suffix,
            metavar=".EXT",
            help=(
                "File type of the input, such as .pdf or .md (default: the suffix of PATH,"
                f" {STDIN_DEFAULT_SUFFIX} for standard input)."
            ),
        )

    def handle(self, *args: object, **options: object) -> None:
        timeout = options["timeout"]
        if not isinstance(timeout, float):
            raise CommandError("--timeout must be a number of seconds.")
        source = options.get("convert")
        if source is None:
            if any(options.get(name) is not None for name in ("page_range", "json_out", "suffix")):
                raise CommandError("--page-range, --json-out and --suffix need --convert.")
            result = check_docling(settings.TWOX_DOCLING_URL, timeout)
            self.stdout.write(result.line)
            if not result.ok:
                sys.exit(1)
            return
        if not isinstance(source, str) or not source:
            raise CommandError("--convert needs a path or -.")
        self._convert(source, options)

    def _convert(self, source: str, options: dict[str, object]) -> None:
        page_range = options.get("page_range")
        pages: tuple[int, int] | None = None
        if isinstance(page_range, list):
            first, last = page_range
            if not 1 <= first <= last:
                raise CommandError("--page-range needs 1 <= FIRST <= LAST.")
            pages = (first, last)
        suffix = options.get("suffix")
        if not isinstance(suffix, str):
            suffix = STDIN_DEFAULT_SUFFIX if source == "-" else Path(source).suffix.lower()
            if not SUFFIX_RE.fullmatch(suffix):
                raise CommandError("Cannot tell the file type from PATH; pass --suffix.")
        # Neutral upload name: the original file name never reaches docling-serve.
        filename = f"{UPLOAD_STEM}{suffix}"
        json_out = options.get("json_out") == "-"

        try:
            if source == "-":
                result, seconds = convert(sys.stdin.buffer, filename, pages)
            else:
                with open(source, "rb") as stream:
                    result, seconds = convert(stream, filename, pages)
        except DoclingError as error:
            self._fail(f"{type(error).__name__}: {error}", json_out)
            return
        except OSError as error:
            self._fail(
                f"cannot read the input file ({error.strerror or type(error).__name__})", json_out
            )
            return

        if json_out:
            self.stdout.write(json.dumps(result.document, ensure_ascii=False, indent=1))
        else:
            self.stdout.write(f"OK: {_summary(result, seconds)}")

    def _fail(self, message: str, json_out: bool) -> None:
        """Report a failed conversion; with --json-out, standard output stays empty."""
        line = f"FAILED: {message}"
        if json_out:
            self.stderr.write(line)
        else:
            self.stdout.write(line)
        sys.exit(1)
