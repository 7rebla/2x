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
embedder makes sure that its model is not a cloud model of Ollama:

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
"""

import json
import logging
import math
import urllib.error
import urllib.request
from collections.abc import Sequence
from http.client import HTTPException
from typing import Final, Protocol
from urllib.parse import urlsplit

from django.conf import settings

logger = logging.getLogger(__name__)

EMBEDDINGS_PATH: Final = "/embeddings"
# Ollama's own list of the models on this machine (not part of /v1).
TAGS_PATH: Final = "/api/tags"
# One batch of 16 vectors with 1024 values is about 350 kB of JSON; the model
# list is small. Protects against an endless answer.
MAX_ANSWER_BYTES: Final = 64 * 1024 * 1024
# Ollama's cloud models: "gpt-oss:120b-cloud", "minimax-m2:cloud".
_CLOUD_TAG: Final = "cloud"
_CLOUD_TAG_SUFFIX: Final = "-cloud"
_OLLAMA_API_SUFFIX: Final = "/v1"


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


def is_cloud_model_name(model: str) -> bool:
    """Return whether ``model`` is named like an Ollama cloud model."""
    tag = model.rpartition(":")[2] if ":" in model else model
    tag = tag.strip().lower()
    return tag == _CLOUD_TAG or tag.endswith(_CLOUD_TAG_SUFFIX)


def _ollama_root(base_url: str) -> str:
    """Return the address of Ollama's own API for an OpenAI-compatible base URL."""
    root = base_url.rstrip("/")
    if root.endswith(_OLLAMA_API_SUFFIX):
        root = root[: -len(_OLLAMA_API_SUFFIX)]
    return root


def _full_model_name(model: str) -> str:
    """Return ``model`` with Ollama's default tag, as /api/tags lists it."""
    return model if ":" in model else f"{model}:latest"


def _is_timeout(error: BaseException) -> bool:
    """Return whether ``error`` is a time limit, also when urllib wrapped it."""
    if isinstance(error, TimeoutError):
        return True
    return isinstance(error, urllib.error.URLError) and isinstance(error.reason, TimeoutError)


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
    ) -> None:
        parts = urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("base_url must look like http://host:port/v1")
        if not model.strip():
            raise ValueError("model must not be empty")
        if dimensions < 1 or batch_size < 1:
            raise ValueError("dimensions and batch_size must be greater than zero")
        if not 0 < timeout < math.inf:
            raise ValueError("timeout must be a positive number of seconds")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._query_prefix = query_prefix
        self._timeout = timeout
        self._model_checked = False
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
        """Refuse cloud models; once per embedder (see the module docstring)."""
        if self._model_checked:
            return
        if is_cloud_model_name(self._model):
            raise EmbeddingRemoteModelError(
                f"model {self._model!r} is an Ollama cloud model; only local models are allowed"
            )
        status, body = self._request("GET", _ollama_root(self._base_url) + TAGS_PATH, None)
        if status == 200:
            self._check_model_list(body)
        else:
            # Not Ollama (another OpenAI-compatible server in the own network,
            # Startunterlage 5.2): there is no model list to check against.
            logger.info("No Ollama model list (HTTP %s); checked the model name only", status)
        self._model_checked = True

    def _check_model_list(self, body: bytes) -> None:
        try:
            listing = json.loads(body)
        except ValueError as error:
            raise EmbeddingUnavailableError("unexpected answer to the model list") from error
        models = listing.get("models") if isinstance(listing, dict) else None
        if not isinstance(models, list):
            raise EmbeddingUnavailableError("unexpected answer to the model list")
        wanted = _full_model_name(self._model)
        for entry in models:
            if not isinstance(entry, dict):
                continue
            names = {entry.get("name"), entry.get("model")}
            if wanted not in names and self._model not in names:
                continue
            if entry.get("remote_host") or entry.get("remote_model"):
                raise EmbeddingRemoteModelError(
                    f"model {self._model!r} runs remotely (Ollama cloud model);"
                    " only local models are allowed"
                )
            return
        raise EmbeddingRejectedError(
            f"model {self._model!r} is not loaded in Ollama;"
            f" load it with: ollama pull {self._model}"
        )

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
            if _is_timeout(error):
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
