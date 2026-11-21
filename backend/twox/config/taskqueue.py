"""The one place where the API talks to the task queue.

Callers get plain values or a :class:`TaskQueueError` with a short message that
is safe to show to users: it never contains broker addresses, credentials or
tracebacks. The original exception is chained for server-side logging only.
"""

import contextlib
import math
import time
import uuid
from typing import Any

from celery import Celery
from celery.backends.redis import RedisBackend
from celery.exceptions import TimeoutError as CeleryTimeoutError
from kombu.exceptions import OperationalError

from twox.config.tasks import ping

DEFAULT_QUEUE = "default"

RESULT_STORE_NOT_REACHABLE = "result store not reachable"

# Where the app in twox.config.celery reads its settings from; a test checks
# that both apps end up with the same broker and result store settings.
CELERY_CONFIG_SOURCE = "django.conf:settings"
CELERY_NAMESPACE = "CELERY"


class TaskQueueError(Exception):
    """The queue or the worker failed; ``str(error)`` is safe to show."""


class BrokerUnavailableError(TaskQueueError):
    """The message broker could not be reached."""


class ResultStoreUnavailableError(TaskQueueError):
    """The result store could not be reached or did not answer in time."""


class WorkerTimeoutError(TaskQueueError):
    """No worker delivered a result in time."""


def broker_transport_options(timeout_seconds: float) -> dict[str, float]:
    """Socket timeouts for a broker connection of the API (Redis transport)."""
    return {"socket_connect_timeout": timeout_seconds, "socket_timeout": timeout_seconds}


def result_store_settings(timeout_seconds: float) -> dict[str, Any]:
    """Celery settings for the result store of one call of the API.

    Short socket timeouts (connect and read/write) and no retries: Celery's
    defaults wait up to 120 seconds per socket operation and retry a lost
    connection up to 20 times.
    """
    transport_options = dict(ping.app.conf.result_backend_transport_options or {})
    transport_options["retry_policy"] = {"max_retries": 0}
    return {
        "redis_socket_timeout": timeout_seconds,
        "redis_socket_connect_timeout": timeout_seconds,
        "redis_retry_on_timeout": False,
        "result_backend_always_retry": False,
        "result_backend_transport_options": transport_options,
    }


def bounded_app(timeout_seconds: float) -> Celery:
    """A Celery app for one call of the API, with its own result store instance.

    It reads its settings from the same source as the app in
    ``twox.config.celery`` (Django settings, prefix ``CELERY_``), plus
    :func:`result_store_settings` on top. The settings of that app, and thus of
    the worker, stay untouched: the extra values live in this app only.

    A second app is needed because Celery subscribes to the result channel
    through the backend of the app that sends the task; a task cannot be sent
    with a different backend. The app registers no tasks, is not made the
    current app and installs no Django fix-up (that is the worker's business).
    """
    app = Celery(
        ping.app.main,
        set_as_current=False,
        fixups=[],
        config_source=CELERY_CONFIG_SOURCE,
        namespace=CELERY_NAMESPACE,
    )
    app.conf.update(result_store_settings(timeout_seconds))
    return app


def result_store(app: Celery) -> RedisBackend:
    """The result store instance of ``app`` (Valkey through Celery's Redis backend)."""
    backend = app.backend
    if not isinstance(backend, RedisBackend):
        raise TaskQueueError("unsupported result store")
    return backend


def result_store_errors(backend: RedisBackend) -> tuple[type[BaseException], ...]:
    """Errors of the result store client.

    redis-py errors, socket errors, the ``RuntimeError`` Celery raises when it
    gives up reconnecting the result channel, and kombu's ``OperationalError``
    (caught here before 017 as well).
    """
    return (backend.redis.RedisError, OSError, RuntimeError, OperationalError)


def watch_result(backend: RedisBackend, task_id: str) -> None:
    """Check the result store and subscribe to the result of ``task_id``.

    Runs before the task is sent, so a failure here is clearly one of the
    result store, and no ping is left in the queue. Sending the task then finds
    the channel subscribed and does not talk to the result store again.
    """
    try:
        # One request with one connection attempt, bounded by the socket timeouts.
        backend.client.ping()
        backend.on_task_call(None, task_id)
    except result_store_errors(backend) as error:
        raise ResultStoreUnavailableError(RESULT_STORE_NOT_REACHABLE) from error


def close_result_store(app: Celery) -> None:
    """Close the connections of ``app``; cleanup only, failures are ignored."""
    with contextlib.suppress(Exception):
        # Also closes the connection of the result channel (it is in use).
        result_store(app).client.connection_pool.disconnect()
    with contextlib.suppress(Exception):
        app.close()


def ping_worker(timeout_seconds: float) -> str:
    """Send ``ping`` to the queue ``default`` and return the worker's answer.

    Every step is bounded by ``timeout_seconds``:

    - The broker connection of this call gets socket timeouts (connect and
      read/write) of that length and a single connection attempt, so a broker
      that does not answer at all (dropped packets, paused container) cannot
      block the caller. Without these options kombu's Redis transport has no
      socket timeouts, and Celery's ``broker_connection_timeout`` does not
      apply to it.
    - The result store is used through an own instance (:func:`bounded_app`)
      with socket timeouts of that length and no retries. This covers the
      subscription to the result channel, reading the result and deleting it.
    - Waiting for the result ends after ``timeout_seconds`` in total.

    If the result store stops answering in the middle of a call, deleting the
    result can add up to one more socket timeout.

    Raises :class:`TaskQueueError` (or a subclass) on any failure.
    """
    deadline = time.monotonic() + timeout_seconds
    app = bounded_app(timeout_seconds)
    try:
        return _ping(app, timeout_seconds, deadline)
    finally:
        close_result_store(app)


def _ping(app: Celery, timeout_seconds: float, deadline: float) -> str:
    backend = result_store(app)
    task_id = str(uuid.uuid4())
    try:
        # The options apply to this one write connection only, never to the worker.
        with app.connection_for_write(
            transport_options=broker_transport_options(timeout_seconds)
        ) as connection:
            # Without this, kombu keeps retrying an unreachable broker for a
            # long time; here a single attempt is enough (0 retries).
            connection.ensure_connection(max_retries=0, timeout=math.ceil(timeout_seconds))
            watch_result(backend, task_id)
            # expires: a ping nobody picked up in time must not linger in the queue.
            result = app.send_task(
                ping.name,
                task_id=task_id,
                queue=DEFAULT_QUEUE,
                expires=timeout_seconds,
                retry=False,
                connection=connection,
            )
    except OperationalError as error:
        raise BrokerUnavailableError("message broker not reachable") from error

    remaining = max(deadline - time.monotonic(), 0.1)
    store_failed = False
    try:
        value = result.get(timeout=remaining)
    except CeleryTimeoutError as error:
        raise WorkerTimeoutError(
            f"no result from a worker within {timeout_seconds:g} seconds"
        ) from error
    except result_store_errors(backend) as error:
        store_failed = True
        raise ResultStoreUnavailableError(RESULT_STORE_NOT_REACHABLE) from error
    finally:
        # The result is read (or abandoned); do not keep it in the result store.
        # Cleanup only: a failure here must not hide the actual outcome. Skipped
        # when the result store just failed, so it adds no second wait.
        if not store_failed:
            with contextlib.suppress(Exception):
                result.forget()

    if not isinstance(value, str):
        raise TaskQueueError("unexpected result from the worker")
    return value
