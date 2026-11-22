"""Self-test endpoint: database part, worker part, AI part, failures and schema.

Plain ``pytest`` needs the database only; the worker part is replaced or made
to fail on purpose. The success case against a running worker carries the
marker ``worker``. The AI part (E-59, work order 048) talks to a stand-in of
Ollama in the test process, never to a real model service.
"""

import re
import socket
import time
from collections.abc import Iterator
from io import StringIO
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml
from celery import Celery
from celery.backends.redis import RedisBackend
from celery.exceptions import TimeoutError as CeleryTimeoutError
from django.conf import settings
from django.core.management import call_command
from django.db import OperationalError as DjangoOperationalError
from django.db import connection
from kombu.exceptions import OperationalError as KombuOperationalError
from pytest_django.fixtures import Settings
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework.test import APIClient

from tests.accounts.users import make_user
from tests.answers.fake_ollama import FakeOllama, fake_ollama
from twox.answers.embeddings import OpenAICompatibleEmbedder
from twox.config import selftest, taskqueue
from twox.config.tasks import ping

URL = "/api/v1/selftest/"
# Stands in for a real secret inside fake error messages.
FAKE_PASSWORD = "fake-secret-for-test-only"
UNREACHABLE_BROKER = f"redis://:{FAKE_PASSWORD}@broker.invalid:6379/0"
UNREACHABLE_RESULT_STORE = f"redis://:{FAKE_PASSWORD}@results.invalid:6379/1"


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
        "results.invalid",
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


def client_for(kind: str) -> APIClient:
    """An API client signed in as a user of ``kind`` (see tests.accounts.users)."""
    client = APIClient()
    user = make_user(kind)
    if user is not None:
        client.force_login(user)
    return client


def get_selftest() -> dict[str, Any]:
    """Call the self-test as a signed-in user with the role ``read``."""
    response = client_for("read").get(URL)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    body: dict[str, Any] = response.json()
    return body


@pytest.fixture
def worker_answers_pong(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(taskqueue, "ping_worker", lambda timeout_seconds: "pong")


@pytest.fixture(autouse=True)
def ai_off(settings: Settings) -> None:
    """The AI features are off unless a test switches them on (E-59).

    The containers get ``TWOX_AI_ENABLED=true`` from the development
    template; no test here may reach a real model service.
    """
    settings.TWOX_AI_ENABLED = False
    settings.TWOX_LLM_BASE_URL = "http://ollama.invalid:11434/v1"


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_response_has_exactly_the_agreed_fields() -> None:
    body = get_selftest()

    assert set(body) == {"database", "worker", "ai"}
    assert set(body["database"]) == {"ok", "server_version", "error"}
    assert set(body["worker"]) == {"ok", "result", "duration_ms", "error"}
    assert body["ai"] == {"enabled": False}


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
    monkeypatch.setattr(settings, "CELERY_BROKER_URL", UNREACHABLE_BROKER)

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
@pytest.mark.parametrize(("kind", "status"), [("anonymous", 403), ("no_role", 403), ("read", 200)])
def test_selftest_needs_a_signed_in_user_with_role(
    monkeypatch: pytest.MonkeyPatch, kind: str, status: int
) -> None:
    ping_worker = MagicMock(return_value="pong")
    monkeypatch.setattr(taskqueue, "ping_worker", ping_worker)

    response = client_for(kind).get(URL)

    assert response.status_code == status
    # A refused request queues no task for the worker.
    assert ping_worker.call_count == (1 if status == 200 else 0)


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_selftest_rejects_writes() -> None:
    response = client_for("read").post(URL, {}, format="json")

    assert response.status_code == 405


def fake_connection_for_write() -> MagicMock:
    """Replaces ``connection_for_write``: the broker connects fine, nothing is sent."""
    connection_mock = MagicMock()
    connection_mock.__enter__.return_value = connection_mock
    return MagicMock(return_value=connection_mock)


class FakeQueue:
    """Hands ``ping_worker`` a real bounded app whose broker side is faked.

    ``send_task`` is a mock; the result store is not touched unless
    ``watch_result`` is kept (``keep_result_store=True``).
    """

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        send_task: MagicMock,
        *,
        keep_result_store: bool = False,
    ) -> None:
        self.send_task = send_task
        self.connection_for_write = fake_connection_for_write()
        self.watch_result = MagicMock()
        self.apps: list[Celery] = []
        self._monkeypatch = monkeypatch
        self._bounded_app = taskqueue.bounded_app
        monkeypatch.setattr(taskqueue, "bounded_app", self.make_app)
        if not keep_result_store:
            monkeypatch.setattr(taskqueue, "watch_result", self.watch_result)

    def make_app(self, timeout_seconds: float) -> Celery:
        app = self._bounded_app(timeout_seconds)
        self._monkeypatch.setattr(app, "connection_for_write", self.connection_for_write)
        self._monkeypatch.setattr(app, "send_task", self.send_task)
        self.apps.append(app)
        return app


def fake_send_task(result: MagicMock) -> MagicMock:
    return MagicMock(return_value=result)


def test_ping_worker_sends_to_default_queue_and_returns_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = MagicMock()
    result.get.return_value = "pong"
    queue = FakeQueue(monkeypatch, fake_send_task(result))

    assert taskqueue.ping_worker(5) == "pong"

    assert queue.send_task.call_args.args == (ping.name,)
    kwargs = queue.send_task.call_args.kwargs
    assert kwargs["queue"] == "default"
    assert kwargs["expires"] == 5
    assert kwargs["retry"] is False
    assert kwargs["connection"] is queue.connection_for_write.return_value
    # The result channel is watched (through the bounded instance) before sending.
    (app,) = queue.apps
    queue.watch_result.assert_called_once_with(taskqueue.result_store(app), kwargs["task_id"])
    assert 0 < result.get.call_args.kwargs["timeout"] <= 5
    result.forget.assert_called_once()


def test_ping_worker_bounds_the_broker_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    result = MagicMock()
    result.get.return_value = "pong"
    queue = FakeQueue(monkeypatch, fake_send_task(result))

    taskqueue.ping_worker(5)

    options = queue.connection_for_write.call_args.kwargs["transport_options"]
    assert options == {"socket_connect_timeout": 5, "socket_timeout": 5}
    connection = queue.connection_for_write.return_value
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


def test_result_store_timeouts_reach_the_api_instance_but_not_the_app_settings() -> None:
    # Building the app and its backend opens no socket.
    app = taskqueue.bounded_app(5)
    try:
        backend = taskqueue.result_store(app)
        # connparams and always_retry are instance attributes missing in celery-types.
        attributes = vars(backend)

        assert backend is not ping.app.backend
        assert attributes["connparams"]["socket_timeout"] == 5
        assert attributes["connparams"]["socket_connect_timeout"] == 5
        assert attributes["connparams"]["retry_on_timeout"] is False
        assert backend.retry_policy["max_retries"] == 0
        assert attributes["always_retry"] is False
        # Same broker, result store and serialization as the worker's app.
        for name in (
            "broker_url",
            "result_backend",
            "accept_content",
            "result_accept_content",
            "task_serializer",
            "result_serializer",
            "task_default_queue",
        ):
            assert app.conf[name] == ping.app.conf[name], name
    finally:
        taskqueue.close_result_store(app)

    # The worker reads its result store settings from the app; they stay untouched.
    assert ping.app.conf.redis_socket_timeout != 5
    assert ping.app.conf.redis_socket_connect_timeout != 5
    assert "retry_policy" not in (ping.app.conf.result_backend_transport_options or {})
    worker_backend = ping.app.backend
    assert isinstance(worker_backend, RedisBackend)
    assert vars(worker_backend)["connparams"]["socket_timeout"] != 5
    assert worker_backend.retry_policy["max_retries"] != 0


def test_ping_worker_turns_result_timeout_into_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = MagicMock()
    result.get.side_effect = CeleryTimeoutError("The operation timed out.")
    FakeQueue(monkeypatch, fake_send_task(result))

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
    FakeQueue(monkeypatch, refuse)

    with pytest.raises(taskqueue.BrokerUnavailableError) as caught:
        taskqueue.ping_worker(5)

    assert str(caught.value) == "message broker not reachable"
    assert_no_internals(str(caught.value))


def test_ping_worker_turns_result_store_error_into_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = MagicMock()
    result.get.side_effect = RedisConnectionError(
        f"Error 111 connecting to {UNREACHABLE_RESULT_STORE}"
    )
    FakeQueue(monkeypatch, fake_send_task(result))

    with pytest.raises(taskqueue.ResultStoreUnavailableError) as caught:
        taskqueue.ping_worker(5)

    assert isinstance(caught.value, taskqueue.TaskQueueError)
    assert not isinstance(caught.value, taskqueue.BrokerUnavailableError)
    assert str(caught.value) == "result store not reachable"
    assert_no_internals(str(caught.value))
    # The store just failed: deleting the result would only add a second wait.
    result.forget.assert_not_called()


@pytest.fixture
def silent_result_store(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A result store that accepts connections but never answers.

    A listening socket that nobody accepts from: the kernel completes the TCP
    handshake, but no byte ever comes back. The URL holds a fake password.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(8)
        port = server.getsockname()[1]
        monkeypatch.setattr(
            settings, "CELERY_RESULT_BACKEND", f"redis://:{FAKE_PASSWORD}@127.0.0.1:{port}/1"
        )
        yield


@pytest.mark.usefixtures("silent_result_store")
def test_silent_result_store_is_a_partial_failure_within_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The broker connects fine; the result store is real and does not answer.
    queue = FakeQueue(monkeypatch, fake_send_task(MagicMock()), keep_result_store=True)
    timeout_seconds = 1.0

    started = time.monotonic()
    worker = selftest.check_worker(timeout_seconds)
    elapsed = time.monotonic() - started

    assert worker["ok"] is False
    assert worker["result"] == ""
    assert worker["error"] == "result store not reachable"
    assert_no_internals(worker["error"])
    assert "127.0.0.1" not in worker["error"]
    assert elapsed < timeout_seconds + 1
    # Nothing was sent: no ping is left in the queue.
    queue.send_task.assert_not_called()


def test_schema_contains_selftest_path_and_fields() -> None:
    schema, stderr = generate_schema()

    assert stderr == ""
    operation = schema["paths"]["/api/v1/selftest/"]["get"]
    assert operation["operationId"] == "selftest_retrieve"
    # Only the Django session; no "no credentials" entry any more.
    assert operation["security"] == [{"cookieAuth": []}]
    response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert response_ref == "#/components/schemas/Selftest"

    components = schema["components"]["schemas"]
    selftest_schema = components["Selftest"]
    assert set(selftest_schema["properties"]) == {"database", "worker", "ai"}
    assert sorted(selftest_schema["required"]) == ["ai", "database", "worker"]
    ai_schema = components["AiCheck"]
    assert set(ai_schema["properties"]) == {"enabled", "ok", "model", "dimensions", "error"}
    # Only "enabled" is always there; the rest only with the AI features on.
    assert ai_schema["required"] == ["enabled"]
    assert ai_schema["properties"]["dimensions"]["type"] == "integer"
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


# --- AI part (E-59, work order 048) ----------------------------------------------------


@pytest.fixture
def ai_on(settings: Settings) -> Iterator[FakeOllama]:
    """AI features on, Ollama replaced by the stand-in with 1024 dimensions and bge-m3."""
    with fake_ollama(FakeOllama(dimensions=1024)) as (base_url, state):
        settings.TWOX_AI_ENABLED = True
        settings.TWOX_LLM_BASE_URL = base_url
        settings.TWOX_EMBED_MODEL = "bge-m3"
        settings.TWOX_EMBED_DIMENSIONS = 1024
        yield state


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_ai_part_is_neutral_and_contacts_nothing_when_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_model_service() -> object:
        raise AssertionError("the model service was contacted with AI off")

    monkeypatch.setattr(selftest, "selftest_embedder", no_model_service)

    body = get_selftest()

    assert body["ai"] == {"enabled": False}
    assert body["database"]["ok"] is True
    assert body["worker"]["ok"] is True


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_ai_part_reports_model_and_dimensions_when_on(ai_on: FakeOllama) -> None:
    body = get_selftest()

    assert body["ai"] == {
        "enabled": True,
        "ok": True,
        "model": "bge-m3",
        "dimensions": 1024,
        "error": "",
    }
    # The model list, then one embedding of the fixed sentence.
    assert [(request.method, request.path) for request in ai_on.requests] == [
        ("GET", "/api/tags"),
        ("POST", "/v1/embeddings"),
    ]
    assert ai_on.embed_requests[0].body == {
        "model": "bge-m3",
        "input": [selftest.AI_TEST_TEXT],
    }


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_ai_part_reports_a_model_that_is_not_loaded(ai_on: FakeOllama) -> None:
    ai_on.models = []

    ai = get_selftest()["ai"]

    assert ai == {
        "enabled": True,
        "ok": False,
        "model": "bge-m3",
        "dimensions": 1024,
        "error": "model 'bge-m3' is not loaded in Ollama; load it with: ollama pull bge-m3",
    }
    assert ai_on.embed_requests == []


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_ai_part_reports_an_unreachable_model_service_without_its_address(
    settings: Settings,
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as unused:
        unused.bind(("127.0.0.1", 0))
        port = unused.getsockname()[1]
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_LLM_BASE_URL = f"http://127.0.0.1:{port}/v1"

    started = time.monotonic()
    ai = get_selftest()["ai"]
    elapsed = time.monotonic() - started

    assert ai["enabled"] is True
    assert ai["ok"] is False
    assert ai["error"] == "the model service refused the connection (is Ollama running?)"
    assert "127.0.0.1" not in ai["error"]
    assert str(port) not in ai["error"]
    assert elapsed < selftest.AI_TIMEOUT_SECONDS + 1


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_ai_part_reports_wrong_dimensions(ai_on: FakeOllama, settings: Settings) -> None:
    settings.TWOX_EMBED_DIMENSIONS = 768

    ai = get_selftest()["ai"]

    assert ai["ok"] is False
    assert ai["dimensions"] == 768
    assert ai["error"].startswith("TWOX_EMBED_DIMENSIONS is 768")
    # The setting does not fit the column: the model is not asked at all.
    assert ai_on.requests == []


@pytest.mark.django_db
@pytest.mark.usefixtures("worker_answers_pong")
def test_ai_part_hides_unexpected_errors(
    ai_on: FakeOllama, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode() -> object:
        raise RuntimeError(f"cannot open {UNREACHABLE_BROKER}")

    monkeypatch.setattr(selftest, "selftest_embedder", explode)

    ai = get_selftest()["ai"]

    assert (ai["ok"], ai["error"]) == (False, "AI check failed")
    assert_no_internals(ai["error"])


def test_ai_check_uses_a_short_time_limit(settings: Settings) -> None:
    settings.TWOX_LLM_BASE_URL = "http://host.docker.internal:11434/v1"
    settings.TWOX_EMBED_TIMEOUT_SECONDS = 120

    embedder = selftest.selftest_embedder()

    assert isinstance(embedder, OpenAICompatibleEmbedder)
    assert vars(embedder)["_timeout"] == selftest.AI_TIMEOUT_SECONDS
    # Worker part and AI part together stay below the limit of the web page (15 s).
    assert selftest.WORKER_TIMEOUT_SECONDS + 2 * selftest.AI_TIMEOUT_SECONDS < 15
