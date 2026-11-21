"""Round trip through the broker to a running worker and back.

Runs only with ``pytest -m worker``. Without a reachable worker the test
fails; it is never skipped.
"""

import pytest
from celery.exceptions import TimeoutError as CeleryTimeoutError
from kombu.exceptions import OperationalError

from twox.config.tasks import ping

TIMEOUT_SECONDS = 10


@pytest.mark.worker
@pytest.mark.parametrize("queue_name", ["default", "ingest", "embed"])
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
