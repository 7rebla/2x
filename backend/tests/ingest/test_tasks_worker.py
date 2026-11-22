"""The Celery tasks of the ingestion (work order 046).

Most tests call the tasks in-process and record what they schedule; they need
the database, not a broker. The test marked ``worker`` sends ``convert`` with
an unknown job ID through Valkey to the running worker (``pytest -m
worker``). The worker reads the main database while the tests use the test
database, so no worker test depends on database state.
"""

from dataclasses import dataclass, field
from typing import Any

import pytest
from billiard.einfo import ExceptionInfo
from billiard.exceptions import WorkerLostError
from celery import Task
from celery.contrib.testing.mocks import TaskMessage
from celery.exceptions import TimeoutError as CeleryTimeoutError
from celery.worker.request import Request
from django.conf import settings
from pytest_django.fixtures import Settings

from tests.ingest.fake_converter import (
    FakeConverter,
    UnexpectedServiceCallError,
    isolated_services,
    make_job,
    make_version,
)
from twox.config import celery_app
from twox.ingest import pipeline, tasks
from twox.ingest.docling import TaskStatus
from twox.ingest.models import IngestStatus, Section

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]

INGEST_TASKS = [
    pytest.param(tasks.convert, id="convert"),
    pytest.param(tasks.poll, id="poll"),
]
TIMEOUT_SECONDS = 10
# Far above every job the main database will ever hold, below the bigint limit.
UNKNOWN_JOB_ID = 9_000_000_000_000_000_000


@dataclass
class Scheduled:
    """Calls of ``poll.apply_async`` and other sends, recorded instead of sent."""

    polls: list[tuple[tuple[object, ...], dict[str, object]]] = field(default_factory=list)


@pytest.fixture
def scheduled(monkeypatch: pytest.MonkeyPatch) -> Scheduled:
    """Record what the tasks schedule; any other message to the broker fails the test."""
    record = Scheduled()

    def apply_async(args: tuple[object, ...], **options: object) -> None:
        record.polls.append((args, options))

    def send_task(name: str, *args: object, **kwargs: object) -> None:
        raise UnexpectedServiceCallError(f"a task was sent to the broker: {name}")

    monkeypatch.setattr(tasks.poll, "apply_async", apply_async)
    monkeypatch.setattr(celery_app, "send_task", send_task)
    return record


def use_converter(monkeypatch: pytest.MonkeyPatch, converter: FakeConverter) -> None:
    monkeypatch.setattr(pipeline, "get_document_converter", lambda: converter)


# --- Registration and options ---------------------------------------------------------


def test_tasks_are_registered_under_the_routed_names() -> None:
    assert tasks.convert.name == "twox.ingest.convert"
    assert tasks.poll.name == "twox.ingest.poll"
    for name in ("twox.ingest.convert", "twox.ingest.poll"):
        assert name in celery_app.tasks
        assert celery_app.amqp.router.route({}, name)["queue"].name == "ingest"


@pytest.mark.parametrize("task", INGEST_TASKS)
def test_tasks_acknowledge_late_and_go_back_when_the_worker_is_lost(task: Task[Any, Any]) -> None:
    assert task.acks_late is True
    assert task.reject_on_worker_lost is True
    # Only these idempotent tasks; the default for all others stays early.
    assert celery_app.conf.task_acks_late is False


@pytest.mark.parametrize("task", INGEST_TASKS)
def test_tasks_keep_the_time_limits_of_045(task: Task[Any, Any]) -> None:
    assert task.soft_time_limit == settings.TWOX_TASK_SOFT_TIME_LIMIT == 300
    assert task.time_limit == settings.TWOX_TASK_TIME_LIMIT == 360
    # A hard time limit acknowledges the message: no endless redelivery.
    assert task.acks_on_failure_or_timeout is True
    # Read by Celery 5.7 on a hard time limit; not in the type stubs yet.
    assert getattr(task, "acks_on_timeout") is True  # noqa: B009


@pytest.mark.parametrize("task", INGEST_TASKS)
def test_message_of_a_lost_worker_process_is_requeued(
    task: Task[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Celery's own handling of a worker process that died (killed, out of
    # memory, cancelled on cold shutdown) for exactly these task options.
    rejected: list[bool] = []
    acknowledged: list[bool] = []
    request = Request(
        TaskMessage(task.name, args=(1,)),
        app=celery_app,
        task=task,
        on_ack=lambda *args: acknowledged.append(True),
        on_reject=lambda logger, errors, requeue: rejected.append(requeue),
    )
    # Would ask the result store whether the task stored a success before.
    monkeypatch.setattr(request, "_success_was_stored", lambda: False)
    try:
        raise WorkerLostError("Worker exited prematurely: signal 9 (SIGKILL).")
    except WorkerLostError:
        info = ExceptionInfo()

    request.on_failure(info)

    assert rejected == [True]
    assert acknowledged == []


# --- In-process runs ------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("isolated_services")
def test_convert_schedules_the_first_poll_on_its_own(
    scheduled: Scheduled, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = make_job(make_version())
    use_converter(monkeypatch, FakeConverter())

    assert tasks.convert(job.pk) == "polling"

    assert scheduled.polls == [((job.pk,), {"countdown": settings.TWOX_INGEST_POLL_MIN_SECONDS})]


@pytest.mark.django_db
@pytest.mark.usefixtures("isolated_services")
@pytest.mark.parametrize("ai_enabled", [True, False], ids=["ai-on", "ai-off"])
def test_tasks_run_a_job_to_done_without_embedding(
    ai_enabled: bool,
    settings: Settings,
    scheduled: Scheduled,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # E-59: in both states the job ends after the sections; no other task is
    # sent (send_task fails the test) and the model service is never asked.
    settings.TWOX_AI_ENABLED = ai_enabled
    version = make_version()
    job = make_job(version)
    use_converter(monkeypatch, FakeConverter(statuses=[TaskStatus.STARTED, TaskStatus.SUCCESS]))

    outcomes = [tasks.convert(job.pk)]
    while len(scheduled.polls) >= len(outcomes):
        args, _options = scheduled.polls[len(outcomes) - 1]
        assert args == (job.pk,)
        outcomes.append(tasks.poll(job.pk))

    job.refresh_from_db()
    assert outcomes == ["polling", "polling", "done"]
    assert len(scheduled.polls) == 2
    assert (job.status, job.step) == (IngestStatus.DONE, "sections")
    assert Section.objects.filter(document_version=version, embedding__isnull=False).count() == 0
    assert Section.objects.filter(document_version=version).count() == job.section_count


@pytest.mark.django_db
@pytest.mark.usefixtures("isolated_services")
def test_task_for_an_unknown_job_ends_without_exception(scheduled: Scheduled) -> None:
    assert tasks.convert(UNKNOWN_JOB_ID) == "missing"
    assert tasks.poll(UNKNOWN_JOB_ID) == "missing"
    assert scheduled.polls == []


@pytest.mark.django_db
@pytest.mark.usefixtures("isolated_services")
def test_failed_job_schedules_nothing(
    scheduled: Scheduled, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = make_job(make_version())
    use_converter(monkeypatch, FakeConverter(statuses=[TaskStatus.FAILURE]))

    assert tasks.convert(job.pk) == "polling"
    assert tasks.poll(job.pk) == "failed"
    assert len(scheduled.polls) == 1


# --- Real worker ----------------------------------------------------------------------


@pytest.mark.worker
def test_convert_of_an_unknown_job_runs_on_the_worker_and_ends_without_exception() -> None:
    assert celery_app.amqp.router.route({}, tasks.convert.name)["queue"].name == "ingest"
    try:
        # No queue given: the route of CELERY_TASK_ROUTES sends it to ingest.
        result = tasks.convert.apply_async((UNKNOWN_JOB_ID,), expires=TIMEOUT_SECONDS, retry=False)
        value = result.get(timeout=TIMEOUT_SECONDS)
    except CeleryTimeoutError:
        pytest.fail(
            f"No result for 'twox.ingest.convert' within {TIMEOUT_SECONDS} seconds: is the "
            "worker running with the current code (`docker compose up -d --build worker`)?"
        )

    assert value == "missing"
    assert result.successful()
    result.forget()
