"""Check whether the model service behind ``TWOX_LLM_BASE_URL`` is reachable.

Three steps: resolve the host name, open a TCP connection, ask the
OpenAI-compatible interface for its model list. The command prints exactly one
line that starts with ``OK:`` (exit code 0) or ``FAILED:`` (exit code 1).

Nothing is sent to the service except the ``GET`` request for the model list,
and nothing of the answer is printed except the number of models.

With ``--embed`` the command instead embeds one fixed sentence through
:mod:`twox.answers.embeddings` and reports model, vector length and duration
(``OK:``) or the kind of error (``FAILED: <error>: <message>``). If the base
URL does not point to this machine, a line ``WARNING:`` comes first: a model
service in the own network is allowed (Startunterlage 5.2), but texts go there.

AI features are optional (E-59). With ``TWOX_AI_ENABLED`` off the command
contacts nothing and prints one neutral line ``DISABLED:`` (exit code 0), with
or without ``--embed``.
"""

import json
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.client import HTTPException
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from twox.answers.embeddings import EmbeddingError, OpenAICompatibleEmbedder

DEFAULT_TIMEOUT_SECONDS = 5.0
# Fixed, harmless text for --embed; nothing from the manuals.
EMBED_TEST_SENTENCE = "Check the oil level of the pump every 500 operating hours."
# Host names that mean "this machine" (the host of the containers included).
LOCAL_HOSTS = frozenset({"host.docker.internal", "localhost", "127.0.0.1", "::1"})
DISABLED_LINE = (
    "DISABLED: AI features are not enabled (TWOX_AI_ENABLED is false);"
    " the model service was not contacted"
)
# More than enough for a model list; protects against an endless answer.
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
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


def _count_models(body: bytes) -> int | None:
    """Return the number of models in an OpenAI-style model list, else ``None``."""
    try:
        document = json.loads(body)
    except ValueError:
        return None
    if not isinstance(document, dict):
        return None
    models = document.get("data")
    if not isinstance(models, list):
        return None
    return len(models)


def _fetch_model_count(models_url: str, timeout: float) -> CheckResult:
    """Step 3: request the model list and count its entries."""
    # No proxy on purpose: the check must talk to the configured address itself.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(models_url, headers={"Accept": "application/json"})
    try:
        with opener.open(request, timeout=timeout) as response:
            status: int = response.status
            body: bytes = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        return _failed(f"unexpected response from {models_url}: HTTP {error.code}")
    except (urllib.error.URLError, HTTPException, OSError) as error:
        if _is_timeout(error):
            return _failed(
                f"timeout waiting for an answer from {models_url} after {_seconds(timeout)}"
                " - the port accepts connections but nothing answers;"
                " check the firewall on the host"
            )
        return _failed(
            f"unexpected response from {models_url}: no valid HTTP answer ({type(error).__name__})"
        )

    if status != 200:
        return _failed(f"unexpected response from {models_url}: HTTP {status}")
    count = None if len(body) > MAX_RESPONSE_BYTES else _count_models(body)
    if count is None:
        return _failed(
            f"unexpected response from {models_url}: HTTP {status}, but not a model list"
        )
    return CheckResult(ok=True, message=f"{models_url} is reachable, {count} model(s) reported")


def check_llm(base_url: str, timeout: float) -> CheckResult:
    """Check the model service at ``base_url`` in three steps."""
    try:
        parts = urlsplit(base_url)
        host = parts.hostname
        port = parts.port or _DEFAULT_PORTS.get(parts.scheme)
    except ValueError:
        host, port = None, None
    if not host or port is None:
        return _failed(
            f"invalid address {base_url!r} - TWOX_LLM_BASE_URL must look like http://host:port/v1"
        )
    target = f"{host}:{port}"

    # Step 1: the host name resolves.
    try:
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        return _failed(
            f"cannot resolve host {host!r} ({error.strerror or error})"
            " - check extra_hosts (host.docker.internal:host-gateway) in the compose file"
            " and that Docker Desktop is running"
        )

    # Step 2: the port accepts connections.
    try:
        socket.create_connection((host, port), timeout=timeout).close()
    except ConnectionRefusedError:
        return _failed(
            f"connection refused by {target}"
            " - Ollama is not running or is bound to 127.0.0.1 only (see OLLAMA_HOST)"
        )
    except TimeoutError:
        return _failed(
            f"timeout connecting to {target} after {_seconds(timeout)}"
            " - check the firewall on the host"
        )
    except OSError as error:
        return _failed(f"connection error to {target} ({error.strerror or error})")

    # Step 3: the OpenAI-compatible interface answers with its model list.
    return _fetch_model_count(base_url.rstrip("/") + "/models", timeout)


def remote_host_warning(base_url: str) -> str | None:
    """Return a ``WARNING:`` line if ``base_url`` does not point to this machine."""
    try:
        host = urlsplit(base_url).hostname
    except ValueError:
        host = None
    # No host at all is an invalid address; the FAILED: line reports it.
    if host is None or host.lower() in LOCAL_HOSTS:
        return None
    return (
        f"WARNING: TWOX_LLM_BASE_URL points to {host!r}, not to this machine"
        " (host.docker.internal, localhost, 127.0.0.1, ::1) - texts are sent there;"
        " allowed only for a model service in your own network"
    )


def check_embed() -> CheckResult:
    """Embed one fixed sentence with the configured model."""
    try:
        embedder = OpenAICompatibleEmbedder.from_settings()
    except ValueError as error:
        return _failed(f"invalid configuration: {error}")
    started = time.monotonic()
    try:
        (vector,) = embedder.embed_documents([EMBED_TEST_SENTENCE])
    except EmbeddingError as error:
        return _failed(f"{type(error).__name__}: {error}")
    elapsed = time.monotonic() - started
    return CheckResult(
        ok=True,
        message=(
            f"embedded a test sentence with {embedder.model_name} at {embedder.embeddings_url}:"
            f" {len(vector)} dimensions in {elapsed:.2f}s"
        ),
    )


def _positive_seconds(value: str) -> float:
    """Parse the value of ``--timeout``."""
    seconds = float(value)
    if not 0 < seconds < float("inf"):
        raise ValueError(value)
    return seconds


class Command(BaseCommand):
    help = (
        "Check whether the model service at TWOX_LLM_BASE_URL is reachable."
        " Prints one line starting with OK: (exit code 0) or FAILED: (exit code 1);"
        " DISABLED: (exit code 0) if TWOX_AI_ENABLED is off."
    )
    # The check needs neither the database nor the system checks.
    requires_system_checks = []  # noqa: RUF012

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--timeout",
            type=_positive_seconds,
            default=DEFAULT_TIMEOUT_SECONDS,
            metavar="SECONDS",
            help=(
                "Time limit per step of the reachability check in seconds"
                " (default: %(default)g). --embed uses TWOX_EMBED_TIMEOUT_SECONDS instead."
            ),
        )
        parser.add_argument(
            "--embed",
            action="store_true",
            help=(
                "Embed a fixed test sentence with TWOX_EMBED_MODEL and report model,"
                " number of dimensions and duration."
            ),
        )

    def handle(self, *args: object, **options: object) -> None:
        timeout = options["timeout"]
        if not isinstance(timeout, float):
            raise CommandError("--timeout must be a number of seconds.")
        if not settings.TWOX_AI_ENABLED:
            # E-59: a neutral state, not an error; nothing is contacted.
            self.stdout.write(DISABLED_LINE)
            return
        if options["embed"]:
            warning = remote_host_warning(settings.TWOX_LLM_BASE_URL)
            if warning is not None:
                self.stdout.write(warning)
            result = check_embed()
        else:
            result = check_llm(settings.TWOX_LLM_BASE_URL, timeout)
        self.stdout.write(result.line)
        if not result.ok:
            sys.exit(1)
