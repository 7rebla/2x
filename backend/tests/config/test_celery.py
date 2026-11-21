"""Celery configuration and the ping task; none of these tests needs a broker."""

import json

import pytest
from django.conf import settings

from tests.config.test_settings import run_python
from twox.config import celery_app
from twox.config.tasks import ping

DUMP_CELERY_SETTINGS = """
import json
import django
from django.conf import settings

django.setup()
print(json.dumps({
    "broker": settings.CELERY_BROKER_URL,
    "backend": settings.CELERY_RESULT_BACKEND,
}))
"""


def test_ping_returns_pong() -> None:
    assert ping() == "pong"


def test_ping_is_registered_under_its_name() -> None:
    assert ping.name == "twox.config.ping"
    assert "twox.config.ping" in celery_app.tasks


def test_three_queues_are_configured() -> None:
    queues = celery_app.conf.task_queues

    assert sorted(queue.name for queue in queues) == ["default", "embed", "ingest"]
    assert sorted(celery_app.amqp.queues) == ["default", "embed", "ingest"]


def test_queues_do_not_share_exchange_or_routing_key() -> None:
    for queue in celery_app.conf.task_queues:
        assert queue.exchange.name == queue.name
        assert queue.routing_key == queue.name


def test_default_queue_is_default() -> None:
    assert celery_app.conf.task_default_queue == "default"


def test_task_without_queue_is_routed_to_default() -> None:
    route = celery_app.amqp.router.route({}, ping.name)

    assert route["queue"].name == "default"


@pytest.mark.parametrize("queue_name", ["ingest", "embed"])
def test_task_can_be_sent_to_a_named_queue(queue_name: str) -> None:
    route = celery_app.amqp.router.route({"queue": queue_name}, ping.name)

    assert route["queue"].name == queue_name


def test_unknown_queue_is_not_created_silently() -> None:
    assert celery_app.conf.task_create_missing_queues is False


def test_only_json_is_serialized_and_accepted() -> None:
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert list(celery_app.conf.accept_content) == ["json"]
    assert list(celery_app.conf.result_accept_content) == ["json"]


def test_app_uses_the_django_settings() -> None:
    assert celery_app.conf.broker_url == settings.CELERY_BROKER_URL
    assert celery_app.conf.result_backend == settings.CELERY_RESULT_BACKEND


def test_broker_settings_have_defaults_for_valkey() -> None:
    result = run_python(
        DUMP_CELERY_SETTINGS,
        {"TWOX_CELERY_BROKER_URL": None, "TWOX_CELERY_RESULT_BACKEND": None},
    )

    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["broker"] == "redis://valkey:6379/0"
    assert values["backend"] == "redis://valkey:6379/1"


def test_broker_settings_read_twox_variables() -> None:
    result = run_python(
        DUMP_CELERY_SETTINGS,
        {
            "TWOX_CELERY_BROKER_URL": "redis://broker.invalid:6380/3",
            "TWOX_CELERY_RESULT_BACKEND": "redis://results.invalid:6381/4",
        },
    )

    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["broker"] == "redis://broker.invalid:6380/3"
    assert values["backend"] == "redis://results.invalid:6381/4"
