"""Celery tasks of the ingestion: thin wrappers around :mod:`twox.ingest.pipeline`.

Both run on the queue ``ingest`` (``CELERY_TASK_ROUTES``). A task does one
short step and, if Docling is still working, schedules :func:`poll` again with
a countdown; it never waits.

Both tasks are idempotent (the pipeline only acts on a job in the expected
state and locks it for the last step), so they acknowledge their message late
(``acks_late``) and give it back to the queue when the worker process dies
(``reject_on_worker_lost``). On a cold shutdown of the worker (``docker
stop``, see ``deploy/compose/compose.yaml``) Celery 5.7 cancels running
tasks after the soft shutdown; only tasks with ``acks_late`` return to the
queue then, all others are lost. A hard time limit acknowledges the message
(no endless redelivery). The time limits are those of work order 045.

A task returns the outcome as a short text (``missing``, ``ignored``,
``polling``, ``done``, ``failed``); it ends without an exception for every
job state, an unknown job ID included.
"""

from django.conf import settings

from twox.config.celery import app
from twox.ingest import pipeline

CONVERT_TASK_NAME = "twox.ingest.convert"
POLL_TASK_NAME = "twox.ingest.poll"


@app.task(
    name=CONVERT_TASK_NAME,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=settings.TWOX_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.TWOX_TASK_TIME_LIMIT,
)
def convert(job_id: int) -> str:
    """Start the ingest job ``job_id``; see :func:`twox.ingest.pipeline.convert`."""
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
    return _schedule(job_id, pipeline.poll(job_id))


def _schedule(job_id: int, result: pipeline.StepResult) -> str:
    """Schedule the next status query if the step asks for one; return the outcome."""
    if result.poll_after is not None:
        poll.apply_async((job_id,), countdown=result.poll_after)
    return result.outcome.value
