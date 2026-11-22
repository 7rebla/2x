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

With the AI features on, the part ``ai`` also reports the chat model of
``TWOX_CHAT_MODEL`` (work order 129) in the fields ``chat_model``, ``chat_ok``
and ``chat_error``. The chat model generates nothing here: the check reads the
local model list ``GET /api/tags`` only and applies the shared checks of
:mod:`twox.answers.llm_guard` - no cloud model by name, listed locally without
``remote_host``/``remote_model``, capability ``completion``. A server without
``/api/tags`` gets the name check only, an entry without ``capabilities`` no
capability check (both logged); ``POST /api/show`` is not asked, so the check
stays within one request. Without a configured chat model nothing is asked at
all and ``chat_error`` says so.

Time budget: the web page waits at most 15 s. The worker part takes up to
5 s, every request of the AI part up to :data:`AI_TIMEOUT_SECONDS`. The model
list is therefore asked at most once per self-test and serves both the
embedding and the chat check (:class:`SelftestEmbedder` keeps its answer), so
the AI part makes at most two requests: 5 + 2 x 4 = 13 s.
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

from twox.answers.chat import (
    ChatError,
    ChatRejectedError,
    ChatRemoteModelError,
    ChatUnavailableError,
)
from twox.answers.embeddings import EmbeddingError, OpenAICompatibleEmbedder
from twox.answers.llm_guard import (
    TAGS_PATH,
    ModelListError,
    ModelNotLoadedError,
    NoCompletionError,
    RemoteModelError,
    check_chat_model,
    model_capabilities,
    ollama_root,
    require_local_name,
)
from twox.config import taskqueue
from twox.ingest.checks import embedding_dimension_problem
from twox.ingest.pipeline import sanitize_error_detail

logger = logging.getLogger(__name__)

WORKER_TIMEOUT_SECONDS = 5.0
EXPECTED_WORKER_RESULT = "pong"
# Socket time limit of each request of the AI check (model list, one
# embedding); short, so that the page answers within its own limit.
AI_TIMEOUT_SECONDS = 4.0
# The most requests the AI part sends: the model list and one embedding.
AI_MAX_REQUESTS = 2
# A fixed sentence without any document content.
AI_TEST_TEXT = "Self-test of the embedding model."
AI_FAILED_DETAIL = "AI check failed"
CHAT_NOT_CONFIGURED = "chat model not configured"
CHAT_FAILED_DETAIL = "chat model check failed"


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
    chat_model: NotRequired[str]
    chat_ok: NotRequired[bool]
    chat_error: NotRequired[str]


class ChatCheck(TypedDict):
    chat_model: str
    chat_ok: bool
    chat_error: str


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
    """``enabled`` always; the other fields only with the AI features on.

    ``ok``, ``model``, ``dimensions`` and ``error`` describe the embedding
    model, the ``chat_*`` fields the chat model (empty ``chat_model``: none
    configured).
    """

    enabled = serializers.BooleanField()
    ok = serializers.BooleanField(required=False)
    model = serializers.CharField(required=False, allow_blank=True)
    dimensions = serializers.IntegerField(required=False, min_value=0)
    error = serializers.CharField(required=False, allow_blank=True)
    chat_model = serializers.CharField(required=False, allow_blank=True)
    chat_ok = serializers.BooleanField(required=False)
    chat_error = serializers.CharField(required=False, allow_blank=True)


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


class SelftestEmbedder(OpenAICompatibleEmbedder):
    """The embedder of the AI check; it keeps its answer to the model list.

    The chat check reads the same answer (:meth:`model_list`), so the
    self-test asks ``GET /api/tags`` at most once (see the module docstring).
    The checks of the embedder itself stay those of its base class.
    """

    #: The answer to ``GET /api/tags`` (status and body) or the error it ended in.
    _model_list_answer: tuple[int, bytes] | EmbeddingError | None = None

    def _request(self, method: str, url: str, payload: object) -> tuple[int, bytes]:
        is_model_list = method == "GET" and url == self._model_list_url()
        try:
            answer = super()._request(method, url, payload)
        except EmbeddingError as error:
            if is_model_list:
                self._model_list_answer = error
            raise
        if is_model_list:
            self._model_list_answer = answer
        return answer

    def _model_list_url(self) -> str:
        return ollama_root(self._base_url) + TAGS_PATH

    def model_list(self) -> tuple[int, bytes]:
        """Return status and body of ``GET /api/tags``; asked only if not done yet.

        Raises the :class:`EmbeddingError` the request ended in, also when the
        embedding check already ran into it (no second request).
        """
        answer = self._model_list_answer
        if answer is None:
            return self._request("GET", self._model_list_url(), None)
        if isinstance(answer, EmbeddingError):
            raise answer
        return answer


def selftest_embedder() -> SelftestEmbedder:
    """The embedder of the AI check: the configured model with a short time limit."""
    return SelftestEmbedder(
        base_url=settings.TWOX_LLM_BASE_URL,
        model=settings.TWOX_EMBED_MODEL,
        dimensions=settings.TWOX_EMBED_DIMENSIONS,
        batch_size=1,
        query_prefix=settings.TWOX_EMBED_QUERY_PREFIX,
        timeout=AI_TIMEOUT_SECONDS,
    )


def check_chat_model_list(status: int, body: bytes, model: str) -> None:
    """Check ``model`` against the answer of ``GET /api/tags``; raise a :class:`ChatError`.

    The shared check of the chat client (:func:`twox.answers.llm_guard.check_chat_model`),
    without ``POST /api/show``: a server without the list (status other than
    200) and an entry without ``capabilities`` are logged and pass.
    """
    try:
        entry = check_chat_model(status, body, model)
    except ModelListError as error:
        raise ChatUnavailableError(str(error)) from error
    except RemoteModelError as error:
        raise ChatRemoteModelError(str(error)) from error
    except (ModelNotLoadedError, NoCompletionError) as error:
        raise ChatRejectedError(str(error)) from error
    if entry is None:
        logger.info(
            "Self-test: no Ollama model list (HTTP %s); checked the chat model name only", status
        )
    elif model_capabilities(entry) is None:
        logger.info("Self-test: the model list names no capabilities of the chat model")


def check_chat(embedder: SelftestEmbedder | None) -> ChatCheck:
    """Check the chat model of ``TWOX_CHAT_MODEL`` without letting it generate anything.

    ``embedder`` is the one of the embedding check, if it was built: its answer
    to the model list is reused. Call only with the AI features on.
    """
    model: str = settings.TWOX_CHAT_MODEL
    if not model:
        # The expected state until the chat model is chosen; nothing is asked.
        return {"chat_model": "", "chat_ok": False, "chat_error": CHAT_NOT_CONFIGURED}
    try:
        try:
            require_local_name(model)
        except RemoteModelError as error:
            raise ChatRemoteModelError(str(error)) from None
        source = embedder if embedder is not None else selftest_embedder()
        status, body = source.model_list()
        check_chat_model_list(status, body, model)
    except (ChatError, EmbeddingError) as error:
        logger.warning("Self-test: chat model check failed", exc_info=True)
        # These messages name neither addresses nor texts; cleaned once more.
        return {
            "chat_model": model,
            "chat_ok": False,
            "chat_error": sanitize_error_detail(str(error)),
        }
    except Exception:
        logger.exception("Self-test: chat model check failed unexpectedly")
        return {"chat_model": model, "chat_ok": False, "chat_error": CHAT_FAILED_DETAIL}
    return {"chat_model": model, "chat_ok": True, "chat_error": ""}


def check_ai() -> AiCheck:
    """Report the AI features; with them off, nothing is contacted (E-59)."""
    if not settings.TWOX_AI_ENABLED:
        return {"enabled": False}
    embedding, embedder = check_embedding()
    chat = check_chat(embedder)
    return {
        **embedding,
        "chat_model": chat["chat_model"],
        "chat_ok": chat["chat_ok"],
        "chat_error": chat["chat_error"],
    }


def check_embedding() -> tuple[AiCheck, SelftestEmbedder | None]:
    """The embedding part of :func:`check_ai`; also returns the embedder, if one was built."""
    model: str = settings.TWOX_EMBED_MODEL
    dimensions: int = settings.TWOX_EMBED_DIMENSIONS

    def failed(error: str) -> AiCheck:
        return {
            "enabled": True,
            "ok": False,
            "model": model,
            "dimensions": dimensions,
            "error": error,
        }

    problem = embedding_dimension_problem()
    if problem is not None:
        return failed(problem), None
    embedder: SelftestEmbedder | None = None
    try:
        embedder = selftest_embedder()
        embedder.embed_documents([AI_TEST_TEXT])
    except EmbeddingError as error:
        logger.warning("Self-test: AI check failed", exc_info=True)
        # The messages of the embedding interface name neither addresses nor
        # texts; cleaned once more all the same.
        return failed(sanitize_error_detail(str(error))), embedder
    except Exception:
        logger.exception("Self-test: AI check failed unexpectedly")
        return failed(AI_FAILED_DETAIL), embedder
    ok: AiCheck = {
        "enabled": True,
        "ok": True,
        "model": model,
        "dimensions": dimensions,
        "error": "",
    }
    return ok, embedder


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
