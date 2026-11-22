"""Self-test endpoint: proves the path API -> database and API -> broker -> worker.

It is the data source of the test page in the web interface. Partial failures
never become a server error: the affected part reports ``ok: false`` with a
short message that holds no internal details (no addresses, no credentials,
no traceback). Details go to the server log only.

The part ``ai`` shows the optional AI features (E-59, work order 048). Off,
it reports ``enabled: false`` only, a neutral state and no error; the model
service is not contacted. On, it embeds a short fixed test sentence with the
configured model and reports the model, the vector length and, on failure, a
cleaned error.
"""

import logging
import time
from typing import NotRequired, TypedDict

from django.conf import settings
from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from twox.answers.embeddings import Embedder, EmbeddingError, OpenAICompatibleEmbedder
from twox.config import taskqueue
from twox.ingest.checks import embedding_dimension_problem
from twox.ingest.pipeline import sanitize_error_detail

logger = logging.getLogger(__name__)

WORKER_TIMEOUT_SECONDS = 5.0
EXPECTED_WORKER_RESULT = "pong"
# Socket time limit of each request of the AI check (model list, one
# embedding); short, so that the page answers within its own limit.
AI_TIMEOUT_SECONDS = 4.0
# A fixed sentence without any document content.
AI_TEST_TEXT = "Self-test of the embedding model."
AI_FAILED_DETAIL = "AI check failed"


class DatabaseCheck(TypedDict):
    ok: bool
    server_version: str
    error: str


class WorkerCheck(TypedDict):
    ok: bool
    result: str
    duration_ms: int
    error: str


class AiCheck(TypedDict):
    enabled: bool
    ok: NotRequired[bool]
    model: NotRequired[str]
    dimensions: NotRequired[int]
    error: NotRequired[str]


class Selftest(TypedDict):
    database: DatabaseCheck
    worker: WorkerCheck
    ai: AiCheck


class DatabaseCheckSerializer(serializers.Serializer[DatabaseCheck]):
    ok = serializers.BooleanField()
    server_version = serializers.CharField(allow_blank=True)
    error = serializers.CharField(allow_blank=True)


class WorkerCheckSerializer(serializers.Serializer[WorkerCheck]):
    ok = serializers.BooleanField()
    result = serializers.CharField(allow_blank=True)
    duration_ms = serializers.IntegerField(min_value=0)
    error = serializers.CharField(allow_blank=True)


class AiCheckSerializer(serializers.Serializer[AiCheck]):
    """``enabled`` always; the other fields only with the AI features on."""

    enabled = serializers.BooleanField()
    ok = serializers.BooleanField(required=False)
    model = serializers.CharField(required=False, allow_blank=True)
    dimensions = serializers.IntegerField(required=False, min_value=0)
    error = serializers.CharField(required=False, allow_blank=True)


class SelftestSerializer(serializers.Serializer[Selftest]):
    database = DatabaseCheckSerializer()
    worker = WorkerCheckSerializer()
    ai = AiCheckSerializer()


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


def selftest_embedder() -> Embedder:
    """The embedder of the AI check: the configured model with a short time limit."""
    return OpenAICompatibleEmbedder(
        base_url=settings.TWOX_LLM_BASE_URL,
        model=settings.TWOX_EMBED_MODEL,
        dimensions=settings.TWOX_EMBED_DIMENSIONS,
        batch_size=1,
        query_prefix=settings.TWOX_EMBED_QUERY_PREFIX,
        timeout=AI_TIMEOUT_SECONDS,
    )


def check_ai() -> AiCheck:
    """Report the AI features; with them off, nothing is contacted (E-59)."""
    if not settings.TWOX_AI_ENABLED:
        return {"enabled": False}
    model: str = settings.TWOX_EMBED_MODEL
    dimensions: int = settings.TWOX_EMBED_DIMENSIONS
    problem = embedding_dimension_problem()
    if problem is not None:
        return {
            "enabled": True,
            "ok": False,
            "model": model,
            "dimensions": dimensions,
            "error": problem,
        }
    try:
        selftest_embedder().embed_documents([AI_TEST_TEXT])
    except EmbeddingError as error:
        logger.warning("Self-test: AI check failed", exc_info=True)
        # The messages of the embedding interface name neither addresses nor
        # texts; cleaned once more all the same.
        detail = sanitize_error_detail(str(error))
        return {
            "enabled": True,
            "ok": False,
            "model": model,
            "dimensions": dimensions,
            "error": detail,
        }
    except Exception:
        logger.exception("Self-test: AI check failed unexpectedly")
        return {
            "enabled": True,
            "ok": False,
            "model": model,
            "dimensions": dimensions,
            "error": AI_FAILED_DETAIL,
        }
    return {"enabled": True, "ok": True, "model": model, "dimensions": dimensions, "error": ""}


class SelftestView(APIView):
    """Read-only self-test for signed-in users with a role.

    Every call queues a task for the worker, so anonymous requests and users
    without a role get 403 (work order 027). The view states no permission of
    its own: the defaults apply, that is the Django session
    (``SessionAuthentication``) and ``CanRead`` (role ``read`` or ``manage``).
    """

    @extend_schema(operation_id="selftest_retrieve", responses=SelftestSerializer)
    def get(self, request: Request) -> Response:
        body: Selftest = {
            "database": check_database(),
            "worker": check_worker(),
            "ai": check_ai(),
        }
        return Response(SelftestSerializer(body).data)
