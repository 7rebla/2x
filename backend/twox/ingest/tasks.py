"""Celery tasks of the ingestion: thin wrappers around :mod:`twox.ingest.pipeline`.

``convert`` and ``poll`` run on the queue ``ingest``, ``embed`` on the queue
``embed`` (``CELERY_TASK_ROUTES``; that queue exists only with the AI features
on, E-59). A task does one short step and, if there is more to do, schedules
the next one with a countdown; it never waits.

All tasks are idempotent (the pipeline only acts on a job in the expected
state and locks it for the last step), so they acknowledge their message late
(``acks_late``) and give it back to the queue when the worker process dies
(``reject_on_worker_lost``). On a cold shutdown of the worker (``docker
stop``, see ``deploy/compose/compose.yaml``) Celery 5.7 cancels running
tasks after the soft shutdown; only tasks with ``acks_late`` return to the
queue then, all others are lost. A hard time limit acknowledges the message
(no endless redelivery). A message that comes back too often ends its job
(:func:`twox.ingest.pipeline.count_redelivery`). The time limits are those of
work order 045.

A task returns the outcome as a short text (``missing``, ``ignored``,
``polling``, ``embedding``, ``done``, ``failed``); it ends without an
exception for every job state, an unknown job ID included.
"""

from typing import Any

from celery import Task
from django.conf import settings

from twox.config.celery import app
from twox.ingest import pipeline

CONVERT_TASK_NAME = "twox.ingest.convert"
POLL_TASK_NAME = "twox.ingest.poll"
EMBED_TASK_NAME = "twox.ingest.embed"


@app.task(
    name=CONVERT_TASK_NAME,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=settings.TWOX_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.TWOX_TASK_TIME_LIMIT,
)
def convert(job_id: int) -> str:
    """Start the ingest job ``job_id``; see :func:`twox.ingest.pipeline.convert`."""
    stopped = _redelivery(convert, job_id)
    if stopped is not None:
        return stopped
    return _schedule(job_id, pipeline.convert(job_id))


@app.task(
    name=POLL_TASK_NAME,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=settings.TWOX_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.TWOX_TASK_TIME_LIMIT,
)
def poll(job_id: int) -> str:
    """Ask Docling once about the job ``job_id``; see :func:`twox.ingest.pipeline.poll`."""
    stopped = _redelivery(poll, job_id)
    if stopped is not None:
        return stopped
    return _schedule(job_id, pipeline.poll(job_id))


@app.task(
    name=EMBED_TASK_NAME,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=settings.TWOX_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.TWOX_TASK_TIME_LIMIT,
)
def embed(job_id: int) -> str:
    """Embed the sections of the job ``job_id``; see :func:`twox.ingest.pipeline.embed`."""
    stopped = _redelivery(embed, job_id)
    if stopped is not None:
        return stopped
    return _schedule(job_id, pipeline.embed(job_id))


def _redelivery(task: Task[Any, Any], job_id: int) -> str | None:
    """If the broker delivers this message again, count it; the outcome if that ends the job."""
    delivery_info = task.request.delivery_info or {}
    if not delivery_info.get("redelivered"):
        return None
    result = pipeline.count_redelivery(job_id)
    return None if result is None else result.outcome.value


def _schedule(job_id: int, result: pipeline.StepResult) -> str:
    """Schedule the next step if the result asks for one; return the outcome."""
    if result.poll_after is not None:
        poll.apply_async((job_id,), countdown=result.poll_after)
    if result.embed_after is not None:
        embed.apply_async((job_id,), countdown=result.embed_after)
    return result.outcome.value
