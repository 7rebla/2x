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


# Routes the ingestion tasks with Celery's own router in a fresh interpreter,
# so that both states of TWOX_AI_ENABLED can be tested in one run.
DUMP_ROUTES = """
import json
from twox.config import celery_app

routes = {}
for name in ("twox.ingest.convert", "twox.ingest.poll", "twox.ingest.embed", "twox.other"):
    try:
        routes[name] = celery_app.amqp.router.route({}, name)["queue"].name
    except KeyError as error:
        routes[name] = type(error).__name__
print(json.dumps({
    "queues": sorted(queue.name for queue in celery_app.conf.task_queues),
    "routes": routes,
}))
"""

AI_STATES = [pytest.param("true", id="ai-on"), pytest.param("false", id="ai-off")]


def expected_queue_names(*, ai_enabled: bool) -> list[str]:
    """Return the queue names, sorted, for one state of the AI switch."""
    return ["default", "embed", "ingest"] if ai_enabled else ["default", "ingest"]


def test_ping_returns_pong() -> None:
    assert ping() == "pong"


def test_ping_is_registered_under_its_name() -> None:
    assert ping.name == "twox.config.ping"
    assert "twox.config.ping" in celery_app.tasks


def test_queues_match_the_ai_switch() -> None:
    expected = expected_queue_names(ai_enabled=settings.TWOX_AI_ENABLED)

    assert sorted(queue.name for queue in celery_app.conf.task_queues) == expected
    assert sorted(celery_app.amqp.queues) == expected


@pytest.mark.parametrize("ai_enabled", AI_STATES)
def test_ingestion_tasks_are_routed_to_ingest(ai_enabled: str) -> None:
    result = run_python(DUMP_ROUTES, {"TWOX_AI_ENABLED": ai_enabled})

    assert result.returncode == 0, result.stderr
    routes = json.loads(result.stdout)["routes"]
    assert routes["twox.ingest.convert"] == "ingest"
    assert routes["twox.ingest.poll"] == "ingest"
    assert routes["twox.other"] == "default"


def test_with_ai_on_embedding_is_routed_to_embed() -> None:
    result = run_python(DUMP_ROUTES, {"TWOX_AI_ENABLED": "true"})

    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["queues"] == expected_queue_names(ai_enabled=True)
    assert values["routes"]["twox.ingest.embed"] == "embed"


def test_with_ai_off_no_embedding_task_can_be_scheduled() -> None:
    # E-59: without the queue embed the router refuses the task, so it never
    # reaches the broker and no worker waits for it.
    result = run_python(DUMP_ROUTES, {"TWOX_AI_ENABLED": "false"})

    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["queues"] == expected_queue_names(ai_enabled=False)
    assert values["routes"]["twox.ingest.embed"] == "QueueNotFound"


def test_task_routes_name_the_ingestion_tasks() -> None:
    assert celery_app.conf.task_routes == {
        "twox.ingest.convert": {"queue": "ingest"},
        "twox.ingest.poll": {"queue": "ingest"},
        "twox.ingest.embed": {"queue": "embed"},
    }


def test_each_worker_process_reserves_one_message() -> None:
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_visibility_timeout_is_explicit() -> None:
    assert celery_app.conf.broker_transport_options == {"visibility_timeout": 3600}


def test_time_limits_stay_below_the_visibility_timeout() -> None:
    visibility_timeout = celery_app.conf.broker_transport_options["visibility_timeout"]

    assert celery_app.conf.task_soft_time_limit == settings.TWOX_TASK_SOFT_TIME_LIMIT == 300
    assert celery_app.conf.task_time_limit == settings.TWOX_TASK_TIME_LIMIT == 360
    assert (
        settings.TWOX_EMBED_TASK_MAX_SECONDS
        < celery_app.conf.task_soft_time_limit
        < celery_app.conf.task_time_limit
        < visibility_timeout
    )


def test_soft_shutdown_is_enabled() -> None:
    assert celery_app.conf.worker_soft_shutdown_timeout == 60


def test_queues_do_not_share_exchange_or_routing_key() -> None:
    for queue in celery_app.conf.task_queues:
        assert queue.exchange.name == queue.name
        assert queue.routing_key == queue.name


def test_default_queue_is_default() -> None:
    assert celery_app.conf.task_default_queue == "default"


def test_task_without_queue_is_routed_to_default() -> None:
    route = celery_app.amqp.router.route({}, ping.name)

    assert route["queue"].name == "default"


@pytest.mark.parametrize(
    "queue_name", [queue.name for queue in settings.CELERY_TASK_QUEUES if queue.name != "default"]
)
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
