"""The shared check "local models only" of the embedding and the chat client.

No text may leave the house (Leitplanke 6). Ollama can list cloud models next
to local ones; a request to such a model sends the text to ollama.com. Both
clients therefore refuse a model

1. by name - Ollama names its cloud models ``<name>:<size>-cloud`` or
   ``<name>:cloud`` (:func:`is_cloud_model_name`);
2. by the local model list ``GET /api/tags`` - the model has to be listed
   there, and its entry must not carry ``remote_host`` or ``remote_model``
   (:func:`find_local_model`).

The functions here are pure: they open no connection. The clients send the
requests themselves and turn the neutral errors of this module into their own
error classes. The messages name neither addresses nor texts.
"""

import json
import urllib.error
from collections.abc import Mapping
from typing import Final

# Ollama's own list of the models on this machine (not part of /v1).
TAGS_PATH: Final = "/api/tags"
# Ollama's cloud models: "gpt-oss:120b-cloud", "minimax-m2:cloud".
_CLOUD_TAG: Final = "cloud"
_CLOUD_TAG_SUFFIX: Final = "-cloud"
_OLLAMA_API_SUFFIX: Final = "/v1"


class ModelListError(Exception):
    """The answer to the model list could not be read."""


class ModelNotLoadedError(Exception):
    """The model is not in the local model list."""


class RemoteModelError(Exception):
    """The model is listed, but runs remotely (an Ollama cloud model)."""


def is_cloud_model_name(model: str) -> bool:
    """Return whether ``model`` is named like an Ollama cloud model."""
    tag = model.rpartition(":")[2] if ":" in model else model
    tag = tag.strip().lower()
    return tag == _CLOUD_TAG or tag.endswith(_CLOUD_TAG_SUFFIX)


def ollama_root(base_url: str) -> str:
    """Return the address of Ollama's own API for an OpenAI-compatible base URL."""
    root = base_url.rstrip("/")
    if root.endswith(_OLLAMA_API_SUFFIX):
        root = root[: -len(_OLLAMA_API_SUFFIX)]
    return root


def full_model_name(model: str) -> str:
    """Return ``model`` with Ollama's default tag, as /api/tags lists it."""
    return model if ":" in model else f"{model}:latest"


def is_timeout(error: BaseException) -> bool:
    """Return whether ``error`` is a time limit, also when urllib wrapped it."""
    if isinstance(error, TimeoutError):
        return True
    return isinstance(error, urllib.error.URLError) and isinstance(error.reason, TimeoutError)


def find_local_model(body: bytes, model: str) -> Mapping[str, object]:
    """Return the entry of ``model`` in the answer ``body`` of ``GET /api/tags``.

    Raises :class:`ModelListError` if the answer is no model list,
    :class:`ModelNotLoadedError` if the model is not listed and
    :class:`RemoteModelError` if its entry says it runs remotely.
    """
    try:
        listing = json.loads(body)
    except ValueError as error:
        raise ModelListError("unexpected answer to the model list") from error
    models = listing.get("models") if isinstance(listing, dict) else None
    if not isinstance(models, list):
        raise ModelListError("unexpected answer to the model list")
    wanted = full_model_name(model)
    for entry in models:
        if not isinstance(entry, dict):
            continue
        names = {entry.get("name"), entry.get("model")}
        if wanted not in names and model not in names:
            continue
        if entry.get("remote_host") or entry.get("remote_model"):
            raise RemoteModelError(
                f"model {model!r} runs remotely (Ollama cloud model); only local models are allowed"
            )
        return entry
    raise ModelNotLoadedError(
        f"model {model!r} is not loaded in Ollama; load it with: ollama pull {model}"
    )
