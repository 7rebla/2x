"""Round trip through the broker to a running worker and back.

Runs only with ``pytest -m worker``. Without a reachable worker the test
fails; it is never skipped.
"""

import pytest
from celery.exceptions import TimeoutError as CeleryTimeoutError
from django.conf import settings
from kombu.exceptions import OperationalError

from twox.config import celery_app
from twox.config.tasks import ping

TIMEOUT_SECONDS = 10

# ingest and default; embed only with the AI features on (E-59).
QUEUE_NAMES = [queue.name for queue in settings.CELERY_TASK_QUEUES]


@pytest.mark.worker
@pytest.mark.parametrize("queue_name", QUEUE_NAMES)
def test_ping_round_trip_through_running_worker(queue_name: str) -> None:
    try:
        # expires: a ping nobody picked up must not linger in the queue.
        result = ping.apply_async(queue=queue_name, expires=TIMEOUT_SECONDS, retry=False)
        value = result.get(timeout=TIMEOUT_SECONDS)
    except CeleryTimeoutError:
        pytest.fail(
            f"Celery worker not reachable: no result for 'ping' from queue '{queue_name}' "
            f"within {TIMEOUT_SECONDS} seconds. "
            "Start it with `docker compose up -d --wait worker`."
        )
    except OperationalError as error:
        pytest.fail(
            f"Celery worker not reachable: the broker (Valkey) refused the connection ({error}). "
            "Start it with `docker compose up -d --wait worker`."
        )

    assert value == "pong"


@pytest.mark.worker
def test_running_worker_consumes_the_configured_queues_with_four_processes() -> None:
    inspect = celery_app.control.inspect(timeout=TIMEOUT_SECONDS)
    active_queues = inspect.active_queues()
    stats = inspect.stats()

    assert active_queues, "Celery worker not reachable: no answer to inspect active_queues."
    assert stats, "Celery worker not reachable: no answer to inspect stats."
    for queues in active_queues.values():
        assert sorted(queue["name"] for queue in queues) == sorted(QUEUE_NAMES)
    for worker_stats in stats.values():
        # --concurrency 4 in deploy/compose/compose.yaml (E-55).
        assert worker_stats["pool"]["max-concurrency"] == 4
        # Prefetch 1 x 4 processes; Celery raises the count for every reserved
        # message with a countdown (polls of running ingest jobs, 046).
        assert worker_stats["prefetch_count"] >= 4
