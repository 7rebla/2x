"""Compute embeddings with a local model service behind an OpenAI-compatible interface.

The only way the backend asks a model for embeddings (Startunterlage 5.2,
E-04): callers use the :class:`Embedder` protocol and get an instance from
:func:`get_embedder`, so the provider stays exchangeable and tests can put a
stand-in there.

:class:`OpenAICompatibleEmbedder` talks to ``POST {TWOX_LLM_BASE_URL}/embeddings``
(Ollama on the host by default, E-56: ``bge-m3`` with 1024 dimensions). It sends
``model`` and ``input`` (always a list) and nothing else: no ``user`` field, no
``dimensions`` (bge-m3 has a fixed size; the answer is checked instead).

AI features are optional (E-59). With ``TWOX_AI_ENABLED`` off, nothing here
opens a connection: :func:`get_embedder` and every request raise
:class:`EmbeddingDisabledError` first.

No text may leave the house (Leitplanke 6). Before the first request an
embedder makes sure that its model is not a cloud model of Ollama (the check
is shared with the chat client, :mod:`twox.answers.llm_guard`):

1. by name - Ollama names its cloud models ``<name>:<size>-cloud`` or
   ``<name>:cloud``;
2. by the local model list ``GET /api/tags`` - the model has to be listed
   there, and its entry must not carry ``remote_host`` or ``remote_model``
   (the fields Ollama sets for a cloud model that was added to the list).

Measured against Ollama 0.40.17 (work order 044): ``POST /api/show`` answers
200 for a cloud model that was never pulled, without ``remote_*`` fields, and
asks ollama.com for it. ``/api/tags`` lists only what is on the machine, so the
check uses that list and never ``/api/show``.

Errors come as subclasses of :class:`EmbeddingError` with short English messages
that name neither addresses nor texts; the original exception stays attached
(``__cause__``) for the server log.

Search queries (052) go through :func:`get_query_embedder`: it has its own,
short time limit (``TWOX_SEARCH_EMBED_TIMEOUT_SECONDS``), so a hanging model
service delays a search only briefly, and there is one per process, so the
model list is not asked for on every search. The check by name runs before
every request; the check against the model list is repeated after
:data:`QUERY_MODEL_CHECK_SECONDS`, so a model replaced in Ollama is noticed
without a restart.
"""

import json
import logging
import math
import threading
import urllib.error
import urllib.request
from collections.abc import Sequence
from http.client import HTTPException
from time import monotonic
from typing import Final, Protocol
from urllib.parse import urlsplit

from django.conf import settings

from twox.answers.llm_guard import (
    TAGS_PATH,
    ModelListError,
    ModelNotLoadedError,
    RemoteModelError,
    find_local_model,
    is_timeout,
    ollama_root,
)

# Kept importable from here (explicit re-export): callers and tests of the
# embedding client import it from this module.
from twox.answers.llm_guard import is_cloud_model_name as is_cloud_model_name

logger = logging.getLogger(__name__)

EMBEDDINGS_PATH: Final = "/embeddings"
# One batch of 16 vectors with 1024 values is about 350 kB of JSON; the model
# list is small. Protects against an endless answer.
MAX_ANSWER_BYTES: Final = 64 * 1024 * 1024
#: How long the query embedder trusts its check against the model list, in seconds.
QUERY_MODEL_CHECK_SECONDS: Final = 300.0


class EmbeddingError(Exception):
    """Base class of all errors of the embedding interface."""


class EmbeddingDisabledError(EmbeddingError):
    """AI features are switched off (``TWOX_AI_ENABLED``); nothing was sent (E-59)."""


class EmbeddingUnavailableError(EmbeddingError):
    """No connection, time limit, HTTP 5xx or an unusable answer. Retrying makes sense."""


class EmbeddingRejectedError(EmbeddingError):
    """The model service refused the request (HTTP 4xx), e.g. the model is not loaded."""


class EmbeddingDimensionError(EmbeddingError):
    """A vector does not have the configured number of values."""


class EmbeddingRemoteModelError(EmbeddingError):
    """The model runs remotely (an Ollama cloud model); texts would leave the house."""


class Embedder(Protocol):
    """Turns texts into vectors of a fixed length."""

    @property
    def model_name(self) -> str:
        """Name of the model as the model service knows it."""
        ...

    @property
    def dimensions(self) -> int:
        """Number of values in every vector."""
        ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per text, in the order of ``texts``."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Return the vector of a search query (with the query prefix, if any)."""
        ...


def _check_ai_enabled() -> None:
    if not settings.TWOX_AI_ENABLED:
        raise EmbeddingDisabledError("AI features are not enabled (TWOX_AI_ENABLED is false)")


class OpenAICompatibleEmbedder:
    """Embedder for ``POST /embeddings`` of an OpenAI-compatible server (Ollama)."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        dimensions: int,
        batch_size: int,
        query_prefix: str,
        timeout: float,
        model_check_seconds: float | None = None,
    ) -> None:
        """``model_check_seconds``: repeat the check against the model list after
        this many seconds; ``None`` checks once per embedder."""
        parts = urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("base_url must look like http://host:port/v1")
        if not model.strip():
            raise ValueError("model must not be empty")
        if dimensions < 1 or batch_size < 1:
            raise ValueError("dimensions and batch_size must be greater than zero")
        if not 0 < timeout < math.inf:
            raise ValueError("timeout must be a positive number of seconds")
        if model_check_seconds is not None and not 0 < model_check_seconds < math.inf:
            raise ValueError("model_check_seconds must be a positive number of seconds")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._query_prefix = query_prefix
        self._timeout = timeout
        self._model_check_seconds = model_check_seconds
        #: ``monotonic()`` of the last successful check against the model list.
        self._model_checked_at: float | None = None
        # No proxy on purpose: texts go to the configured address and nowhere else.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def from_settings(cls) -> OpenAICompatibleEmbedder:
        """Build an embedder from the ``TWOX_LLM_BASE_URL`` and ``TWOX_EMBED_*`` settings."""
        return cls(
            base_url=settings.TWOX_LLM_BASE_URL,
            model=settings.TWOX_EMBED_MODEL,
            dimensions=settings.TWOX_EMBED_DIMENSIONS,
            batch_size=settings.TWOX_EMBED_BATCH_SIZE,
            query_prefix=settings.TWOX_EMBED_QUERY_PREFIX,
            timeout=float(settings.TWOX_EMBED_TIMEOUT_SECONDS),
        )

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def timeout(self) -> float:
        """Socket time limit of one request, in seconds."""
        return self._timeout

    @property
    def embeddings_url(self) -> str:
        """The address every embedding request goes to."""
        return self._base_url + EMBEDDINGS_PATH

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if isinstance(texts, str) or not all(isinstance(text, str) for text in texts):
            raise TypeError("texts must be a sequence of strings")
        _check_ai_enabled()
        if not texts:
            return []
        self._ensure_local_model()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            vectors.extend(self._embed_batch(list(texts[start : start + self._batch_size])))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        _check_ai_enabled()
        self._ensure_local_model()
        (vector,) = self._embed_batch([self._query_prefix + text])
        return vector

    def _ensure_local_model(self) -> None:
        """Refuse cloud models (see the module docstring).

        The name is checked every time; the model list once per embedder, or
        again after ``model_check_seconds``.
        """
        if is_cloud_model_name(self._model):
            raise EmbeddingRemoteModelError(
                f"model {self._model!r} is an Ollama cloud model; only local models are allowed"
            )
        checked_at = self._model_checked_at
        if checked_at is not None and (
            self._model_check_seconds is None
            or monotonic() - checked_at < self._model_check_seconds
        ):
            return
        status, body = self._request("GET", ollama_root(self._base_url) + TAGS_PATH, None)
        if status == 200:
            self._check_model_list(body)
        else:
            # Not Ollama (another OpenAI-compatible server in the own network,
            # Startunterlage 5.2): there is no model list to check against.
            logger.info("No Ollama model list (HTTP %s); checked the model name only", status)
        self._model_checked_at = monotonic()

    def _check_model_list(self, body: bytes) -> None:
        try:
            find_local_model(body, self._model)
        except ModelListError as error:
            raise EmbeddingUnavailableError(str(error)) from error
        except RemoteModelError as error:
            raise EmbeddingRemoteModelError(str(error)) from error
        except ModelNotLoadedError as error:
            raise EmbeddingRejectedError(str(error)) from error

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        payload = {"model": self._model, "input": batch}
        status, body = self._request("POST", self.embeddings_url, payload)
        if status == 404:
            raise EmbeddingRejectedError(
                f"model {self._model!r} not found by the model service;"
                f" load it with: ollama pull {self._model}"
            )
        if 400 <= status < 500:
            raise EmbeddingRejectedError(f"the model service refused the request (HTTP {status})")
        if status != 200:
            raise EmbeddingUnavailableError(
                f"unexpected answer from the model service (HTTP {status})"
            )
        return self._parse_vectors(body, len(batch))

    def _parse_vectors(self, body: bytes, expected: int) -> list[list[float]]:
        try:
            answer = json.loads(body)
        except ValueError as error:
            raise EmbeddingUnavailableError("unexpected answer: not JSON") from error
        items = answer.get("data") if isinstance(answer, dict) else None
        if not isinstance(items, list) or len(items) != expected:
            raise EmbeddingUnavailableError(
                f"unexpected answer: expected {expected} vector(s),"
                f" got {len(items) if isinstance(items, list) else 'none'}"
            )
        by_index: dict[int, list[float]] = {}
        for position, item in enumerate(items):
            if not isinstance(item, dict):
                raise EmbeddingUnavailableError("unexpected answer: an entry is not an object")
            index = item.get("index", position)
            if type(index) is not int or not 0 <= index < expected or index in by_index:
                raise EmbeddingUnavailableError("unexpected answer: invalid or repeated index")
            by_index[index] = self._vector(item.get("embedding"))
        return [by_index[index] for index in range(expected)]

    def _vector(self, values: object) -> list[float]:
        if not isinstance(values, list) or not all(
            type(value) in {int, float} and math.isfinite(value) for value in values
        ):
            raise EmbeddingUnavailableError("unexpected answer: a vector is not a list of numbers")
        if len(values) != self._dimensions:
            raise EmbeddingDimensionError(
                f"model {self._model!r} returned {len(values)} values,"
                f" expected {self._dimensions} (TWOX_EMBED_DIMENSIONS)"
            )
        return [float(value) for value in values]

    def _request(self, method: str, url: str, payload: object) -> tuple[int, bytes]:
        """Send one request; return status and body. Network failures become errors."""
        _check_ai_enabled()
        data = None if payload is None else json.dumps(payload).encode()
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                status: int = response.status
                body: bytes = response.read(MAX_ANSWER_BYTES + 1)
        except urllib.error.HTTPError as error:
            error.close()
            if error.code >= 500:
                raise EmbeddingUnavailableError(
                    f"the model service failed (HTTP {error.code})"
                ) from error
            return error.code, b""
        except (urllib.error.URLError, HTTPException, OSError) as error:
            if is_timeout(error):
                raise EmbeddingUnavailableError(
                    f"no answer from the model service within {self._timeout:g}s"
                ) from error
            if isinstance(error, urllib.error.URLError) and isinstance(
                error.reason, ConnectionRefusedError
            ):
                raise EmbeddingUnavailableError(
                    "the model service refused the connection (is Ollama running?)"
                ) from error
            raise EmbeddingUnavailableError(
                f"cannot reach the model service ({type(error).__name__})"
            ) from error
        if len(body) > MAX_ANSWER_BYTES:
            raise EmbeddingUnavailableError("unexpected answer: too large")
        return status, body


def get_embedder() -> Embedder:
    """Return the configured embedder; tests replace this function with a stand-in.

    Raises :class:`EmbeddingDisabledError` when AI features are off (E-59).
    """
    _check_ai_enabled()
    return OpenAICompatibleEmbedder.from_settings()


_query_embedder: tuple[tuple[object, ...], OpenAICompatibleEmbedder] | None = None
_query_embedder_lock = threading.Lock()


def get_query_embedder() -> Embedder:
    """Return the embedder for search queries; tests replace this function with a stand-in.

    Time limit ``TWOX_SEARCH_EMBED_TIMEOUT_SECONDS``; the same instance for
    every search of this process while the settings stay the same, so its
    check against the model list is reused (see the module docstring).
    Raises :class:`EmbeddingDisabledError` when AI features are off (E-59).
    """
    global _query_embedder
    _check_ai_enabled()
    config: tuple[object, ...] = (
        settings.TWOX_LLM_BASE_URL,
        settings.TWOX_EMBED_MODEL,
        settings.TWOX_EMBED_DIMENSIONS,
        settings.TWOX_EMBED_QUERY_PREFIX,
        float(settings.TWOX_SEARCH_EMBED_TIMEOUT_SECONDS),
    )
    with _query_embedder_lock:
        if _query_embedder is None or _query_embedder[0] != config:
            embedder = OpenAICompatibleEmbedder(
                base_url=settings.TWOX_LLM_BASE_URL,
                model=settings.TWOX_EMBED_MODEL,
                dimensions=settings.TWOX_EMBED_DIMENSIONS,
                batch_size=1,
                query_prefix=settings.TWOX_EMBED_QUERY_PREFIX,
                timeout=float(settings.TWOX_SEARCH_EMBED_TIMEOUT_SECONDS),
                model_check_seconds=QUERY_MODEL_CHECK_SECONDS,
            )
            _query_embedder = (config, embedder)
        return _query_embedder[1]


def forget_query_embedder() -> None:
    """Drop the query embedder of this process; the next search builds a new one (tests)."""
    global _query_embedder
    with _query_embedder_lock:
        _query_embedder = None
