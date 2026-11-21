"""Self-test endpoint: proves the path API -> database and API -> broker -> worker.

It is the data source of the test page in the web interface. Partial failures
never become a server error: the affected part reports ``ok: false`` with a
short message that holds no internal details (no addresses, no credentials,
no traceback). Details go to the server log only.
"""

import logging
import time
from typing import TypedDict

from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from twox.config import taskqueue

logger = logging.getLogger(__name__)

WORKER_TIMEOUT_SECONDS = 5.0
EXPECTED_WORKER_RESULT = "pong"


class DatabaseCheck(TypedDict):
    ok: bool
    server_version: str
    error: str


class WorkerCheck(TypedDict):
    ok: bool
    result: str
    duration_ms: int
    error: str


class Selftest(TypedDict):
    database: DatabaseCheck
    worker: WorkerCheck


class DatabaseCheckSerializer(serializers.Serializer[DatabaseCheck]):
    ok = serializers.BooleanField()
    server_version = serializers.CharField(allow_blank=True)
    error = serializers.CharField(allow_blank=True)


class WorkerCheckSerializer(serializers.Serializer[WorkerCheck]):
    ok = serializers.BooleanField()
    result = serializers.CharField(allow_blank=True)
    duration_ms = serializers.IntegerField(min_value=0)
    error = serializers.CharField(allow_blank=True)


class SelftestSerializer(serializers.Serializer[Selftest]):
    database = DatabaseCheckSerializer()
    worker = WorkerCheckSerializer()


def check_database() -> DatabaseCheck:
    """Read the server version from PostgreSQL; no table is involved."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW server_version")
            row = cursor.fetchone()
    except DatabaseError:
        logger.warning("Self-test: database check failed", exc_info=True)
        return {"ok": False, "server_version": "", "error": "database not reachable"}
    if row is None or not isinstance(row[0], str):
        return {"ok": False, "server_version": "", "error": "unexpected database answer"}
    return {"ok": True, "server_version": row[0], "error": ""}


def check_worker(timeout_seconds: float = WORKER_TIMEOUT_SECONDS) -> WorkerCheck:
    """Send ``ping`` through the task queue and wait for ``pong``."""
    started = time.monotonic()

    def elapsed_ms() -> int:
        return round((time.monotonic() - started) * 1000)

    try:
        value = taskqueue.ping_worker(timeout_seconds)
    except taskqueue.TaskQueueError as error:
        logger.warning("Self-test: worker check failed", exc_info=True)
        # TaskQueueError messages are written to be safe to show.
        return {"ok": False, "result": "", "duration_ms": elapsed_ms(), "error": str(error)}
    except Exception:
        # Any other failure (for example of the result store client) stays a
        # partial failure; its text may hold addresses, so it is not passed on.
        logger.exception("Self-test: worker check failed unexpectedly")
        return {
            "ok": False,
            "result": "",
            "duration_ms": elapsed_ms(),
            "error": "worker check failed",
        }
    if value != EXPECTED_WORKER_RESULT:
        return {
            "ok": False,
            "result": "",
            "duration_ms": elapsed_ms(),
            "error": "unexpected result from the worker",
        }
    return {"ok": True, "result": value, "duration_ms": elapsed_ms(), "error": ""}


class SelftestView(APIView):
    """Read-only self-test.

    Open to everyone in milestone M0 on purpose (decided by a7): there is no
    login yet, and the answer holds only the database version and ``pong``.
    Every call queues a task, so M1 restricts this to signed-in users.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(operation_id="selftest_retrieve", responses=SelftestSerializer)
    def get(self, request: Request) -> Response:
        body: Selftest = {"database": check_database(), "worker": check_worker()}
        return Response(SelftestSerializer(body).data)
