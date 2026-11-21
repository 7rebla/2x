"""The one place where the API talks to the task queue.

Callers get plain values or a :class:`TaskQueueError` with a short message that
is safe to show to users: it never contains broker addresses, credentials or
tracebacks. The original exception is chained for server-side logging only.
"""

import contextlib
import math
import time

from celery.exceptions import TimeoutError as CeleryTimeoutError
from kombu.exceptions import OperationalError

from twox.config.tasks import ping

DEFAULT_QUEUE = "default"


class TaskQueueError(Exception):
    """The queue or the worker failed; ``str(error)`` is safe to show."""


class BrokerUnavailableError(TaskQueueError):
    """The message broker could not be reached."""


class WorkerTimeoutError(TaskQueueError):
    """No worker delivered a result in time."""


def ping_worker(timeout_seconds: float) -> str:
    """Send ``ping`` to the queue ``default`` and return the worker's answer.

    Publishing and waiting together take at most about ``timeout_seconds``.
    Raises :class:`TaskQueueError` (or a subclass) on any failure.
    """
    deadline = time.monotonic() + timeout_seconds
    try:
        with ping.app.connection_for_write() as connection:
            # Without this, kombu keeps retrying an unreachable broker for a
            # long time; here a single attempt is enough (0 retries).
            connection.ensure_connection(max_retries=0, timeout=math.ceil(timeout_seconds))
            # expires: a ping nobody picked up in time must not linger in the queue.
            result = ping.apply_async(
                queue=DEFAULT_QUEUE,
                expires=timeout_seconds,
                retry=False,
                # Documented option of apply_async, missing in celery-types.
                connection=connection,  # type: ignore[call-arg]
            )
    except OperationalError as error:
        raise BrokerUnavailableError("message broker not reachable") from error

    remaining = max(deadline - time.monotonic(), 0.1)
    try:
        value = result.get(timeout=remaining)
    except CeleryTimeoutError as error:
        raise WorkerTimeoutError(
            f"no result from a worker within {timeout_seconds:g} seconds"
        ) from error
    except OperationalError as error:
        raise BrokerUnavailableError("result store not reachable") from error
    finally:
        # The result is read (or abandoned); do not keep it in the result store.
        # Cleanup only: a failure here must not hide the actual outcome.
        with contextlib.suppress(Exception):
            result.forget()

    if not isinstance(value, str):
        raise TaskQueueError("unexpected result from the worker")
    return value
