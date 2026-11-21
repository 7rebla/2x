"""Check whether docling-serve behind ``TWOX_DOCLING_URL`` is reachable.

Three steps: resolve the host name, open a TCP connection, ask the service for
its version (``GET /version``). The command prints exactly one line that starts
with ``OK:`` (exit code 0) or ``FAILED:`` (exit code 1).

Nothing is sent to the service except that ``GET`` request, and nothing of the
answer is printed except the version of docling-serve itself.
"""

import json
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.client import HTTPException
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

DEFAULT_TIMEOUT_SECONDS = 5.0
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


def _positive_seconds(value: str) -> float:
    """Parse the value of ``--timeout``."""
    seconds = float(value)
    if not 0 < seconds < float("inf"):
        raise ValueError(value)
    return seconds


class Command(BaseCommand):
    help = (
        "Check whether docling-serve at TWOX_DOCLING_URL is reachable and report its version."
        " Prints one line starting with OK: (exit code 0) or FAILED: (exit code 1)."
    )
    # The check needs neither the database nor the system checks.
    requires_system_checks = []  # noqa: RUF012

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--timeout",
            type=_positive_seconds,
            default=DEFAULT_TIMEOUT_SECONDS,
            metavar="SECONDS",
            help="Time limit per step in seconds (default: %(default)g).",
        )

    def handle(self, *args: object, **options: object) -> None:
        timeout = options["timeout"]
        if not isinstance(timeout, float):
            raise CommandError("--timeout must be a number of seconds.")
        result = check_docling(settings.TWOX_DOCLING_URL, timeout)
        self.stdout.write(result.line)
        if not result.ok:
            sys.exit(1)
