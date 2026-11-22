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

With ``--chat`` (work order 129) the command lets the chat model of
``TWOX_CHAT_MODEL`` answer one fixed test prompt through
:func:`twox.answers.chat.get_chat_model` (cloud check, model list and
capability ``completion`` included) with a small ``max_tokens``, temperature 0
and a fixed seed. It reports the time until the first text piece and the
number of pieces per second (``OK:``), or the kind of error (``FAILED:``). The
chat interface yields text pieces, not tokens, so the rate is given in
``chunks``. The answer of the model is never printed or logged. The time
limit is ``TWOX_CHAT_TIMEOUT_SECONDS``, not ``--timeout``. The ``WARNING:``
line comes first, as with ``--embed``.

AI features are optional (E-59). With ``TWOX_AI_ENABLED`` off the command
contacts nothing and prints one neutral line ``DISABLED:`` (exit code 0), with
or without ``--embed`` or ``--chat``.
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

from twox.answers import chat
from twox.answers.embeddings import EmbeddingError, OpenAICompatibleEmbedder

DEFAULT_TIMEOUT_SECONDS = 5.0
# Fixed, harmless text for --embed; nothing from the manuals.
EMBED_TEST_SENTENCE = "Check the oil level of the pump every 500 operating hours."
# Fixed, harmless prompt for --chat; nothing from the manuals.
CHAT_TEST_PROMPT = "Reply with one short sentence: what colour is a clear sky at noon?"
# Small limits for --chat: a short, repeatable answer.
CHAT_TEST_MAX_TOKENS = 32
CHAT_TEST_TEMPERATURE = 0.0
CHAT_TEST_SEED = 129
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


def check_chat() -> CheckResult:
    """Let the chat model answer one fixed prompt; report timing, never the answer."""
    if not settings.TWOX_CHAT_MODEL:
        return _failed("invalid configuration: TWOX_CHAT_MODEL is empty")
    try:
        model = chat.get_chat_model()
    except ValueError as error:
        return _failed(f"invalid configuration: {error}")
    except chat.ChatError as error:
        return _failed(f"{type(error).__name__}: {error}")
    messages: list[chat.ChatMessage] = [{"role": "user", "content": CHAT_TEST_PROMPT}]
    started = time.monotonic()
    first_piece: float | None = None
    pieces = 0
    try:
        stream = model.stream(
            messages,
            max_tokens=CHAT_TEST_MAX_TOKENS,
            temperature=CHAT_TEST_TEMPERATURE,
            seed=CHAT_TEST_SEED,
        )
        try:
            # Only counted: the text of the answer is neither kept nor shown.
            for _piece in stream:
                if first_piece is None:
                    first_piece = time.monotonic() - started
                pieces += 1
        finally:
            stream.close()
    except chat.ChatError as error:
        return _failed(f"{type(error).__name__}: {error}")
    finally:
        model.close()
    elapsed = time.monotonic() - started
    if first_piece is None:
        # For example a thinking model that spent all tokens on reasoning.
        return _failed(
            f"empty answer: model {model.model_name!r} returned no text"
            f" within {CHAT_TEST_MAX_TOKENS} tokens"
        )
    rate = pieces / elapsed if elapsed > 0 else 0.0
    return CheckResult(
        ok=True,
        message=(
            f"chat with {model.model_name}: first token after {first_piece:.2f}s,"
            f" {pieces} chunks in {elapsed:.2f}s ({rate:.1f} chunks/s)"
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
        " DISABLED: (exit code 0) if TWOX_AI_ENABLED is off. --embed and --chat"
        " test the embedding or the chat model instead."
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
                " (default: %(default)g). --embed uses TWOX_EMBED_TIMEOUT_SECONDS,"
                " --chat TWOX_CHAT_TIMEOUT_SECONDS instead."
            ),
        )
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument(
            "--embed",
            action="store_true",
            help=(
                "Embed a fixed test sentence with TWOX_EMBED_MODEL and report model,"
                " number of dimensions and duration."
            ),
        )
        mode.add_argument(
            "--chat",
            action="store_true",
            help=(
                "Let TWOX_CHAT_MODEL answer a fixed test prompt (at most"
                f" {CHAT_TEST_MAX_TOKENS} tokens) and report the time until the first text"
                " piece and the pieces per second; the answer is not shown."
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
        if options["embed"] or options["chat"]:
            warning = remote_host_warning(settings.TWOX_LLM_BASE_URL)
            if warning is not None:
                self.stdout.write(warning)
            result = check_embed() if options["embed"] else check_chat()
        else:
            result = check_llm(settings.TWOX_LLM_BASE_URL, timeout)
        self.stdout.write(result.line)
        if not result.ok:
            sys.exit(1)
