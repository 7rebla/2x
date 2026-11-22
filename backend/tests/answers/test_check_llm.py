"""`check_llm` reports every outcome in one line; no test talks to a real Ollama.

The model service is replaced by a small server from the standard library that
listens on the loopback interface of the test container.
"""

import json
import socket
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from typing import ClassVar

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pytest_django import Settings

from tests.answers.fake_ollama import FakeOllama, fake_ollama
from twox.answers.management.commands.check_llm import DISABLED_LINE, remote_host_warning

MODEL_LIST = json.dumps(
    {"object": "list", "data": [{"id": "model-a"}, {"id": "model-b"}, {"id": "model-c"}]}
).encode()


@pytest.fixture(autouse=True)
def ai_enabled(settings: Settings) -> None:
    """AI features on, unless a test switches them off (E-59: both states are tested)."""
    settings.TWOX_AI_ENABLED = True


class StubHandler(BaseHTTPRequestHandler):
    """Answers every GET with the configured status and body and records the path."""

    status: ClassVar[int] = 200
    body: ClassVar[bytes] = MODEL_LIST
    paths: ClassVar[list[str]] = []

    def do_GET(self) -> None:
        self.paths.append(self.path)
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, format: str, *args: object) -> None:
        """Keep the test output quiet."""


@contextmanager
def stub_server(status: int = 200, body: bytes = MODEL_LIST) -> Iterator[tuple[str, list[str]]]:
    """Run a stand-in model service; yields its base URL and the requested paths."""
    paths: list[str] = []
    handler = type("Handler", (StubHandler,), {"status": status, "body": body, "paths": paths})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1", paths
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def unused_port() -> int:
    """Return a loopback port on which nothing listens."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
    return port


def run_check(*args: str) -> tuple[int, str]:
    """Run the command; return its exit code and everything it wrote to stdout."""
    stdout = StringIO()
    try:
        call_command("check_llm", *args, stdout=stdout)
    except SystemExit as exit_:
        assert isinstance(exit_.code, int)
        return exit_.code, stdout.getvalue()
    return 0, stdout.getvalue()


def single_line(output: str) -> str:
    """Assert that ``output`` is exactly one line and return it without the newline."""
    assert output.endswith("\n")
    assert output.count("\n") == 1, output
    return output[:-1]


def test_ok_names_address_and_number_of_models(settings: Settings) -> None:
    with stub_server() as (base_url, paths):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check()

    line = single_line(output)
    assert code == 0
    assert line.startswith("OK: ")
    assert f"{base_url}/models" in line
    assert "3 model(s)" in line
    assert paths == ["/v1/models"]
    # Nothing of the model list itself is printed.
    assert "model-a" not in line


def test_ok_with_empty_model_list_and_trailing_slash(settings: Settings) -> None:
    body = json.dumps({"object": "list", "data": []}).encode()
    with stub_server(body=body) as (base_url, paths):
        settings.TWOX_LLM_BASE_URL = base_url + "/"
        code, output = run_check()

    assert code == 0
    assert "0 model(s)" in single_line(output)
    assert paths == ["/v1/models"]


def test_failed_cannot_resolve_host(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_such_host(*args: object, **kwargs: object) -> list[object]:
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    # No real DNS query: the tests also have to pass without any network.
    monkeypatch.setattr(socket, "getaddrinfo", no_such_host)
    settings.TWOX_LLM_BASE_URL = "http://nonexistent.invalid:11434/v1"
    code, output = run_check()

    line = single_line(output)
    assert code == 1
    assert line.startswith("FAILED: cannot resolve host 'nonexistent.invalid'")
    assert "extra_hosts" in line
    assert "Docker Desktop" in line


def test_failed_connection_refused(settings: Settings) -> None:
    port = unused_port()
    settings.TWOX_LLM_BASE_URL = f"http://127.0.0.1:{port}/v1"
    code, output = run_check()

    line = single_line(output)
    assert code == 1
    assert line.startswith(f"FAILED: connection refused by 127.0.0.1:{port}")
    assert "OLLAMA_HOST" in line


def test_failed_timeout_when_nothing_answers(settings: Settings) -> None:
    # The kernel completes the handshake for a listening socket, but nobody
    # ever accepts or answers: the port is open and the request runs into the limit.
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as silent:
        silent.bind(("127.0.0.1", 0))
        silent.listen(1)
        settings.TWOX_LLM_BASE_URL = f"http://127.0.0.1:{silent.getsockname()[1]}/v1"
        code, output = run_check("--timeout", "0.3")

    line = single_line(output)
    assert code == 1
    assert line.startswith("FAILED: timeout ")
    assert "after 0.3s" in line
    assert "firewall" in line


def test_failed_timeout_while_connecting(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[float | None] = []

    def never_connects(address: tuple[str, int], timeout: float | None = None) -> socket.socket:
        seen.append(timeout)
        raise TimeoutError("timed out")

    monkeypatch.setattr(socket, "create_connection", never_connects)
    settings.TWOX_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
    code, output = run_check("--timeout", "2")

    line = single_line(output)
    assert code == 1
    assert line.startswith("FAILED: timeout connecting to 127.0.0.1:11434 after 2s")
    assert "firewall" in line
    assert seen == [2.0]


def test_failed_unexpected_response_names_http_status(settings: Settings) -> None:
    with stub_server(status=404, body=b"not found") as (base_url, _paths):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check()

    line = single_line(output)
    assert code == 1
    assert line.startswith("FAILED: unexpected response ")
    assert line.endswith("HTTP 404")


@pytest.mark.parametrize("body", [b"<html>hello</html>", b'{"models": []}', b"[]"])
def test_failed_unexpected_response_when_not_a_model_list(settings: Settings, body: bytes) -> None:
    with stub_server(body=body) as (base_url, _paths):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check()

    line = single_line(output)
    assert code == 1
    assert line.startswith("FAILED: unexpected response ")
    assert "HTTP 200" in line


def test_failed_invalid_address(settings: Settings) -> None:
    settings.TWOX_LLM_BASE_URL = "host.docker.internal:11434"
    code, output = run_check()

    assert code == 1
    assert single_line(output).startswith("FAILED: invalid address ")


def test_default_timeout_is_five_seconds(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[float | None] = []

    def never_connects(address: tuple[str, int], timeout: float | None = None) -> socket.socket:
        seen.append(timeout)
        raise TimeoutError("timed out")

    monkeypatch.setattr(socket, "create_connection", never_connects)
    settings.TWOX_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
    code, _output = run_check()

    assert code == 1
    assert seen == [5.0]


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_timeout_must_be_a_positive_number(value: str) -> None:
    with pytest.raises(CommandError):
        call_command("check_llm", "--timeout", value, stdout=StringIO())


# --- AI switched off (E-59) --------------------------------------------------


def forbid_network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Make every attempt to resolve or connect fail loudly; returns the attempts."""
    attempts: list[str] = []

    def refuse(*args: object, **kwargs: object) -> object:
        attempts.append(repr(args))
        raise AssertionError("the model service must not be contacted")

    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    return attempts


@pytest.mark.parametrize("args", [(), ("--embed",)])
def test_disabled_is_a_neutral_state_and_contacts_nothing(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, args: tuple[str, ...]
) -> None:
    settings.TWOX_AI_ENABLED = False
    with stub_server() as (base_url, paths):
        settings.TWOX_LLM_BASE_URL = base_url
        attempts = forbid_network(monkeypatch)
        code, output = run_check(*args)

    assert code == 0
    assert single_line(output) == DISABLED_LINE
    assert DISABLED_LINE.startswith("DISABLED: ")
    assert "FAILED" not in output
    assert "WARNING" not in output
    assert paths == []
    assert attempts == []


# --- --embed -----------------------------------------------------------------


@pytest.fixture
def embed_settings(settings: Settings) -> Settings:
    settings.TWOX_EMBED_MODEL = "bge-m3"
    settings.TWOX_EMBED_DIMENSIONS = 4
    settings.TWOX_EMBED_BATCH_SIZE = 16
    settings.TWOX_EMBED_QUERY_PREFIX = ""
    settings.TWOX_EMBED_TIMEOUT_SECONDS = 5
    return settings


def test_embed_ok_names_model_dimensions_and_duration(embed_settings: Settings) -> None:
    with fake_ollama() as (base_url, fake):
        embed_settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--embed")

    line = single_line(output)
    assert code == 0
    assert line.startswith("OK: embedded a test sentence with bge-m3 ")
    assert f"{base_url}/embeddings" in line
    assert ": 4 dimensions in " in line
    assert line.endswith("s")
    # Only the model list and one embedding request; no reachability steps.
    assert [(request.method, request.path) for request in fake.requests] == [
        ("GET", "/api/tags"),
        ("POST", "/v1/embeddings"),
    ]
    (request,) = fake.embed_requests
    assert set(request.body) == {"model", "input"}
    assert len(request.body["input"]) == 1


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"models": []}, "FAILED: EmbeddingRejectedError: "),
        ({"embed_status": 404}, "FAILED: EmbeddingRejectedError: "),
        ({"embed_status": 503}, "FAILED: EmbeddingUnavailableError: "),
        ({"dimensions": 3}, "FAILED: EmbeddingDimensionError: "),
    ],
)
def test_embed_failed_names_the_kind_of_error(
    embed_settings: Settings, change: dict[str, object], error: str
) -> None:
    fake = FakeOllama()
    for name, value in change.items():
        setattr(fake, name, value)
    with fake_ollama(fake) as (base_url, _fake):
        embed_settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--embed")

    line = single_line(output)
    assert code == 1
    assert line.startswith(error)


@pytest.mark.parametrize("change", [{"models": []}, {"embed_status": 404}])
def test_embed_missing_model_names_ollama_pull(
    embed_settings: Settings, change: dict[str, object]
) -> None:
    fake = FakeOllama()
    for name, value in change.items():
        setattr(fake, name, value)
    with fake_ollama(fake) as (base_url, _fake):
        embed_settings.TWOX_LLM_BASE_URL = base_url
        _code, output = run_check("--embed")

    assert "ollama pull bge-m3" in single_line(output)


def test_embed_refuses_a_cloud_model(embed_settings: Settings) -> None:
    embed_settings.TWOX_EMBED_MODEL = "gpt-oss:120b-cloud"
    with fake_ollama() as (base_url, fake):
        embed_settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--embed")

    assert code == 1
    assert single_line(output).startswith("FAILED: EmbeddingRemoteModelError: ")
    assert fake.requests == []


def test_embed_connection_refused(embed_settings: Settings) -> None:
    embed_settings.TWOX_LLM_BASE_URL = f"http://127.0.0.1:{unused_port()}/v1"
    code, output = run_check("--embed")

    assert code == 1
    assert single_line(output).startswith("FAILED: EmbeddingUnavailableError: ")


def test_embed_timeout(embed_settings: Settings) -> None:
    embed_settings.TWOX_EMBED_TIMEOUT_SECONDS = 1
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as silent:
        silent.bind(("127.0.0.1", 0))
        silent.listen(1)
        embed_settings.TWOX_LLM_BASE_URL = f"http://127.0.0.1:{silent.getsockname()[1]}/v1"
        code, output = run_check("--embed")

    assert code == 1
    line = single_line(output)
    assert line.startswith("FAILED: EmbeddingUnavailableError: ")
    assert "within 1s" in line


def test_embed_invalid_address(embed_settings: Settings) -> None:
    embed_settings.TWOX_LLM_BASE_URL = "host.docker.internal:11434"
    code, output = run_check("--embed")

    assert code == 1
    assert single_line(output).startswith("FAILED: invalid configuration: ")


def test_embed_warns_when_the_model_service_is_not_on_this_machine(
    embed_settings: Settings,
) -> None:
    # 127.0.0.2 is a loopback address, but not one of the names the command
    # treats as "this machine": the check goes by the configured name.
    with fake_ollama(host="127.0.0.2") as (base_url, _fake):
        embed_settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--embed")

    warning, result, *rest = output.splitlines()
    assert code == 0
    assert warning.startswith("WARNING: TWOX_LLM_BASE_URL points to '127.0.0.2'")
    assert "own network" in warning
    assert result.startswith("OK: ")
    assert rest == []


@pytest.mark.parametrize(
    "base_url",
    [
        "http://host.docker.internal:11434/v1",
        "http://HOST.DOCKER.INTERNAL:11434/v1",
        "http://localhost:11434/v1",
        "http://127.0.0.1:11434/v1",
        "http://[::1]:11434/v1",
    ],
)
def test_no_warning_for_this_machine(base_url: str) -> None:
    assert remote_host_warning(base_url) is None


@pytest.mark.parametrize(
    "base_url", ["http://ollama.example.test:11434/v1", "http://10.0.0.5:11434/v1"]
)
def test_warning_for_other_hosts(base_url: str) -> None:
    warning = remote_host_warning(base_url)

    assert warning is not None
    assert warning.startswith("WARNING: ")


def test_without_embed_no_embedding_request_and_no_warning(settings: Settings) -> None:
    # Without --embed the reachability check stays as it was.
    with stub_server() as (base_url, paths):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check()

    assert code == 0
    assert single_line(output).startswith("OK: ")
    assert paths == ["/v1/models"]
