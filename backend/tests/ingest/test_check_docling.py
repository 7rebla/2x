"""`check_docling` reports every outcome in one line; no test needs a docling container.

docling-serve is replaced by a small server from the standard library that
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

# Answer of docling-serve 1.38.2 to GET /version (platform shortened; the key
# "plaform" is spelled like that by the service).
VERSIONS = json.dumps(
    {
        "docling-serve": "1.38.2",
        "docling-jobkit": "3.9.1",
        "docling": "2.142.1",
        "docling-core": "2.104.0",
        "docling-ibm-models": "4.0.4",
        "docling-parse": "7.23.0",
        "python": "cpython-312 (3.12.15)",
        "plaform": "Linux-x86_64",
    }
).encode()


class StubHandler(BaseHTTPRequestHandler):
    """Answers every GET with the configured status and body and records the path."""

    status: ClassVar[int] = 200
    body: ClassVar[bytes] = VERSIONS
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
def stub_server(status: int = 200, body: bytes = VERSIONS) -> Iterator[tuple[str, list[str]]]:
    """Run a stand-in docling-serve; yields its base URL and the requested paths."""
    paths: list[str] = []
    handler = type("Handler", (StubHandler,), {"status": status, "body": body, "paths": paths})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", paths
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
        call_command("check_docling", *args, stdout=stdout)
    except SystemExit as exit_:
        assert isinstance(exit_.code, int)
        return exit_.code, stdout.getvalue()
    return 0, stdout.getvalue()


def single_line(output: str) -> str:
    """Assert that ``output`` is exactly one line and return it without the newline."""
    assert output.endswith("\n")
    assert output.count("\n") == 1, output
    return output[:-1]


def test_ok_names_version_and_address(settings: Settings) -> None:
    with stub_server() as (base_url, paths):
        settings.TWOX_DOCLING_URL = base_url
        code, output = run_check()

    assert code == 0
    assert single_line(output) == f"OK: docling-serve 1.38.2 at {base_url}"
    assert paths == ["/version"]


def test_ok_with_trailing_slash(settings: Settings) -> None:
    with stub_server() as (base_url, paths):
        settings.TWOX_DOCLING_URL = base_url + "/"
        code, output = run_check()

    assert code == 0
    assert single_line(output) == f"OK: docling-serve 1.38.2 at {base_url}"
    assert paths == ["/version"]


def test_failed_cannot_resolve_host(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_such_host(*args: object, **kwargs: object) -> list[object]:
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    # No real DNS query: the tests also have to pass without any network.
    monkeypatch.setattr(socket, "getaddrinfo", no_such_host)
    settings.TWOX_DOCLING_URL = "http://docling:5001"
    code, output = run_check()

    line = single_line(output)
    assert code == 1
    assert line.startswith("FAILED: cannot resolve host 'docling'")
    assert "docling container" in line


def test_failed_connection_refused(settings: Settings) -> None:
    port = unused_port()
    settings.TWOX_DOCLING_URL = f"http://127.0.0.1:{port}"
    code, output = run_check()

    line = single_line(output)
    assert code == 1
    assert line.startswith(f"FAILED: connection refused by 127.0.0.1:{port}")


def test_failed_timeout_when_nothing_answers(settings: Settings) -> None:
    # The kernel completes the handshake for a listening socket, but nobody
    # ever accepts or answers: the port is open and the request runs into the limit.
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as silent:
        silent.bind(("127.0.0.1", 0))
        silent.listen(1)
        settings.TWOX_DOCLING_URL = f"http://127.0.0.1:{silent.getsockname()[1]}"
        code, output = run_check("--timeout", "0.3")

    line = single_line(output)
    assert code == 1
    assert line.startswith("FAILED: timeout waiting for an answer ")
    assert "after 0.3s" in line


def test_failed_timeout_while_connecting(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[float | None] = []

    def never_connects(address: tuple[str, int], timeout: float | None = None) -> socket.socket:
        seen.append(timeout)
        raise TimeoutError("timed out")

    monkeypatch.setattr(socket, "create_connection", never_connects)
    settings.TWOX_DOCLING_URL = "http://127.0.0.1:5001"
    code, output = run_check("--timeout", "2")

    assert code == 1
    assert single_line(output) == "FAILED: timeout connecting to 127.0.0.1:5001 after 2s"
    assert seen == [2.0]


def test_failed_unexpected_response_names_http_status(settings: Settings) -> None:
    with stub_server(status=503, body=b'{"detail": "Models not yet loaded"}') as (base_url, _):
        settings.TWOX_DOCLING_URL = base_url
        code, output = run_check()

    line = single_line(output)
    assert code == 1
    assert line.startswith(f"FAILED: unexpected response from {base_url}/version")
    assert line.endswith("HTTP 503")


def test_failed_when_version_info_is_switched_off(settings: Settings) -> None:
    body = b'{"detail": "Forbidden. The server is configured for not showing version details."}'
    with stub_server(status=403, body=body) as (base_url, _paths):
        settings.TWOX_DOCLING_URL = base_url
        code, output = run_check()

    line = single_line(output)
    assert code == 1
    assert "HTTP 403" in line
    assert "DOCLING_SERVE_SHOW_VERSION_INFO" in line


@pytest.mark.parametrize(
    "body",
    [
        b"<html>hello</html>",
        b"[]",
        b'{"docling": "2.0.0"}',
        b'{"docling-serve": 1}',
        b'{"docling-serve": "  "}',
        b'{"docling-serve": "1.0\\n2.0"}',
    ],
)
def test_failed_unexpected_response_without_version(settings: Settings, body: bytes) -> None:
    with stub_server(body=body) as (base_url, _paths):
        settings.TWOX_DOCLING_URL = base_url
        code, output = run_check()

    line = single_line(output)
    assert code == 1
    assert line.startswith("FAILED: unexpected response ")
    assert "HTTP 200" in line


def test_failed_when_something_else_answers(settings: Settings) -> None:
    # A port that accepts the connection and closes it without any HTTP answer.
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(2)

        def accept_and_close() -> None:
            for _ in range(2):
                connection, _address = server.accept()
                connection.close()

        thread = threading.Thread(target=accept_and_close, daemon=True)
        thread.start()
        settings.TWOX_DOCLING_URL = f"http://127.0.0.1:{server.getsockname()[1]}"
        code, output = run_check()
        thread.join(timeout=5)

    line = single_line(output)
    assert code == 1
    assert line.startswith("FAILED: unexpected response ")
    assert "no valid HTTP answer" in line


@pytest.mark.parametrize("url", ["docling:5001", "", "ftp://docling"])
def test_failed_invalid_address(settings: Settings, url: str) -> None:
    settings.TWOX_DOCLING_URL = url
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
    settings.TWOX_DOCLING_URL = "http://127.0.0.1:5001"
    code, _output = run_check()

    assert code == 1
    assert seen == [5.0]


@pytest.mark.parametrize("value", ["0", "-1", "abc", "inf"])
def test_timeout_must_be_a_positive_number(value: str) -> None:
    with pytest.raises(CommandError):
        call_command("check_docling", "--timeout", value, stdout=StringIO())
