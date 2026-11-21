"""Self-test endpoint: database part, worker part, failures and schema.

Plain ``pytest`` needs the database only; the worker part is replaced or made
to fail on purpose. The success case against a running worker carries the
marker ``worker``.
"""

import re
import time
from io import StringIO
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml
from celery.exceptions import TimeoutError as CeleryTimeoutError
from django.conf import settings
from django.core.management import call_command
from django.db import OperationalError as DjangoOperationalError
from django.db import connection
from kombu.exceptions import OperationalError as KombuOperationalError
from rest_framework.test import APIClient

from twox.config import selftest, taskqueue
from twox.config.tasks import ping

URL = "/api/v1/selftest/"
# Stands in for a real secret inside fake error messages.
FAKE_PASSWORD = "fake-secret-for-test-only"
UNREACHABLE_BROKER = f"redis://:{FAKE_PASSWORD}@broker.invalid:6379/0"


def generate_schema() -> tuple[dict[str, Any], str]:
    """Run `manage.py spectacular` and return the parsed schema and stderr."""
    stdout = StringIO()
    stderr = StringIO()
    call_command("spectacular", "--validate", stdout=stdout, stderr=stderr)
    schema: dict[str, Any] = yaml.safe_load(stdout.getvalue())
    return schema, stderr.getvalue()


def forbidden_fragments() -> list[str]:
    """Strings that must never appear in an error text of the response."""
    database = settings.DATABASES["default"]
    return [
        FAKE_PASSWORD,
        "broker.invalid",
        "redis://",
        "6379",
        str(database["PASSWORD"]),
        str(database["HOST"]),
        settings.CELERY_BROKER_URL,
        "valkey",
        "Traceback",
    ]


def assert_no_internals(text: str) -> None:
    for fragment in forbidden_fragments():
        assert fragment not in text, f"error text leaks {fragment!r}: {text!r}"


def get_selftest() -> dict[str, Any]:
    response = APIClient().get(URL)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    body: dict[str, Any] = response.json()
    return body


@pytest.fixture
def worker_answers_pong(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(taskqueue, "ping_worker", lambda timeout_seconds: "pong")


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_response_has_exactly_the_agreed_fields() -> None:
    body = get_selftest()

    assert set(body) == {"database", "worker"}
    assert set(body["database"]) == {"ok", "server_version", "error"}
    assert set(body["worker"]) == {"ok", "result", "duration_ms", "error"}


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_database_part_reports_running_postgresql_version() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SHOW server_version_num")
        (version_num,) = cursor.fetchone()
    # e.g. 180001 for 18.1: the major version is the part above 10000.
    major = int(version_num) // 10000

    database = get_selftest()["database"]

    assert database["ok"] is True
    assert database["error"] == ""
    assert re.match(rf"{major}(\D|$)", database["server_version"]), database


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_worker_part_reports_pong() -> None:
    worker = get_selftest()["worker"]

    assert worker == {
        "ok": True,
        "result": "pong",
        "duration_ms": worker["duration_ms"],
        "error": "",
    }
    assert isinstance(worker["duration_ms"], int)
    assert worker["duration_ms"] >= 0


@pytest.mark.django_db
def test_unreachable_broker_is_a_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # A real connection attempt to an address that cannot resolve.
    monkeypatch.setattr(ping.app.conf, "broker_url", UNREACHABLE_BROKER)

    started = time.monotonic()
    body = get_selftest()
    elapsed = time.monotonic() - started

    assert body["database"]["ok"] is True
    worker = body["worker"]
    assert worker["ok"] is False
    assert worker["result"] == ""
    assert worker["error"] == "message broker not reachable"
    assert_no_internals(worker["error"])
    assert elapsed < selftest.WORKER_TIMEOUT_SECONDS + 1


@pytest.mark.django_db
def test_worker_timeout_is_a_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def time_out(timeout_seconds: float) -> str:
        raise taskqueue.WorkerTimeoutError(
            f"no result from a worker within {timeout_seconds:g} seconds"
        )

    monkeypatch.setattr(taskqueue, "ping_worker", time_out)

    body = get_selftest()

    assert body["database"]["ok"] is True
    assert body["worker"]["ok"] is False
    assert body["worker"]["error"] == "no result from a worker within 5 seconds"


@pytest.mark.django_db
def test_unexpected_worker_failure_does_not_leak_its_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(timeout_seconds: float) -> str:
        raise ConnectionError(f"Error 111 connecting to {UNREACHABLE_BROKER}")

    monkeypatch.setattr(taskqueue, "ping_worker", explode)

    worker = get_selftest()["worker"]

    assert worker["ok"] is False
    assert worker["error"] == "worker check failed"
    assert_no_internals(worker["error"])


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_unexpected_worker_answer_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(taskqueue, "ping_worker", lambda timeout_seconds: "pang")

    worker = get_selftest()["worker"]

    assert worker["ok"] is False
    assert worker["result"] == ""
    assert worker["error"] == "unexpected result from the worker"


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_database_failure_is_a_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    database = settings.DATABASES["default"]

    broken = MagicMock()
    broken.cursor.side_effect = DjangoOperationalError(
        f'connection to server at "{database["HOST"]}", port 5432 failed: '
        f'password authentication failed (password "{database["PASSWORD"]}")'
    )
    monkeypatch.setattr(selftest, "connection", broken)

    body = get_selftest()

    assert body["database"] == {
        "ok": False,
        "server_version": "",
        "error": "database not reachable",
    }
    assert_no_internals(body["database"]["error"])
    assert body["worker"]["ok"] is True


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_selftest_needs_no_credentials_and_rejects_writes() -> None:
    client = APIClient()

    assert client.get(URL).status_code == 200
    assert client.post(URL, {}, format="json").status_code == 405


def fake_connection_for_write() -> MagicMock:
    """Replaces ``connection_for_write``: the broker connects fine, nothing is sent."""
    connection_mock = MagicMock()
    connection_mock.__enter__.return_value = connection_mock
    return MagicMock(return_value=connection_mock)


def test_ping_worker_sends_to_default_queue_and_returns_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = MagicMock()
    result.get.return_value = "pong"
    apply_async = MagicMock(return_value=result)
    connection_for_write = fake_connection_for_write()
    monkeypatch.setattr(ping.app, "connection_for_write", connection_for_write)
    monkeypatch.setattr(ping, "apply_async", apply_async)

    assert taskqueue.ping_worker(5) == "pong"

    kwargs = apply_async.call_args.kwargs
    assert kwargs["queue"] == "default"
    assert kwargs["expires"] == 5
    assert kwargs["retry"] is False
    assert kwargs["connection"] is connection_for_write.return_value
    assert 0 < result.get.call_args.kwargs["timeout"] <= 5
    result.forget.assert_called_once()


def test_ping_worker_bounds_the_broker_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    result = MagicMock()
    result.get.return_value = "pong"
    connection_for_write = fake_connection_for_write()
    monkeypatch.setattr(ping.app, "connection_for_write", connection_for_write)
    monkeypatch.setattr(ping, "apply_async", MagicMock(return_value=result))

    taskqueue.ping_worker(5)

    options = connection_for_write.call_args.kwargs["transport_options"]
    assert options == {"socket_connect_timeout": 5, "socket_timeout": 5}
    connection = connection_for_write.return_value
    connection.ensure_connection.assert_called_once_with(max_retries=0, timeout=5)


def test_socket_timeouts_reach_the_connection_but_not_the_app_settings() -> None:
    options = taskqueue.broker_transport_options(5)

    # Building a kombu connection opens no socket.
    with ping.app.connection_for_write(transport_options=options) as connection:
        transport_options = connection.transport_options or {}
        assert transport_options["socket_connect_timeout"] == 5
        assert transport_options["socket_timeout"] == 5

    # The worker reads its broker options from the app settings; they stay untouched.
    assert "socket_timeout" not in ping.app.conf.broker_transport_options
    assert "socket_connect_timeout" not in ping.app.conf.broker_transport_options


def test_ping_worker_turns_result_timeout_into_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = MagicMock()
    result.get.side_effect = CeleryTimeoutError("The operation timed out.")
    monkeypatch.setattr(ping.app, "connection_for_write", fake_connection_for_write())
    monkeypatch.setattr(ping, "apply_async", MagicMock(return_value=result))

    with pytest.raises(taskqueue.WorkerTimeoutError) as caught:
        taskqueue.ping_worker(5)

    assert str(caught.value) == "no result from a worker within 5 seconds"
    result.forget.assert_called_once()


def test_ping_worker_turns_broker_error_into_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refuse = MagicMock(
        side_effect=KombuOperationalError(f"Error 111 connecting to {UNREACHABLE_BROKER}")
    )
    monkeypatch.setattr(ping.app, "connection_for_write", fake_connection_for_write())
    monkeypatch.setattr(ping, "apply_async", refuse)

    with pytest.raises(taskqueue.BrokerUnavailableError) as caught:
        taskqueue.ping_worker(5)

    assert str(caught.value) == "message broker not reachable"
    assert_no_internals(str(caught.value))


def test_schema_contains_selftest_path_and_fields() -> None:
    schema, stderr = generate_schema()

    assert stderr == ""
    operation = schema["paths"]["/api/v1/selftest/"]["get"]
    assert operation["operationId"] == "selftest_retrieve"
    assert operation.get("security", [{}]) == [{}]
    response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert response_ref == "#/components/schemas/Selftest"

    components = schema["components"]["schemas"]
    selftest_schema = components["Selftest"]
    assert set(selftest_schema["properties"]) == {"database", "worker"}
    assert sorted(selftest_schema["required"]) == ["database", "worker"]
    assert set(components["DatabaseCheck"]["properties"]) == {"ok", "server_version", "error"}
    assert set(components["WorkerCheck"]["properties"]) == {
        "ok",
        "result",
        "duration_ms",
        "error",
    }
    assert components["WorkerCheck"]["properties"]["duration_ms"]["type"] == "integer"
    assert components["DatabaseCheck"]["properties"]["ok"]["type"] == "boolean"


@pytest.mark.worker
@pytest.mark.django_db
def test_selftest_against_running_worker() -> None:
    body = get_selftest()

    assert body["database"]["ok"] is True
    worker = body["worker"]
    assert worker["ok"] is True, (
        f"Celery worker not reachable through the self-test: {worker['error']!r}. "
        "Start it with `docker compose up -d --wait worker`."
    )
    assert worker["result"] == "pong"
    assert worker["error"] == ""
