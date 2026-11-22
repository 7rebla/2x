"""The shared check "local models only"; pure functions, no connection."""

import json
import urllib.error

import pytest

from twox.answers import embeddings
from twox.answers.llm_guard import (
    TAGS_PATH,
    ModelListError,
    ModelNotLoadedError,
    RemoteModelError,
    find_local_model,
    full_model_name,
    is_cloud_model_name,
    is_timeout,
    ollama_root,
)


def tags(*entries: object) -> bytes:
    return json.dumps({"models": list(entries)}).encode()


@pytest.mark.parametrize(
    "model",
    ["gpt-oss:120b-cloud", "minimax-m2:cloud", "some-model:CLOUD", "deep:7b-Cloud ", "cloud"],
)
def test_cloud_names(model: str) -> None:
    assert is_cloud_model_name(model)


@pytest.mark.parametrize(
    "model", ["bge-m3", "bge-m3:latest", "qwen3:8b", "cloudy:7b", "my-cloud-model:latest"]
)
def test_local_names(model: str) -> None:
    assert not is_cloud_model_name(model)


def test_embeddings_reexports_the_same_function() -> None:
    assert embeddings.is_cloud_model_name is is_cloud_model_name


def test_tags_path() -> None:
    assert TAGS_PATH == "/api/tags"


@pytest.mark.parametrize(
    ("base_url", "root"),
    [
        ("http://ollama.test:11434/v1", "http://ollama.test:11434"),
        ("http://ollama.test:11434/v1/", "http://ollama.test:11434"),
        ("http://ollama.test:11434", "http://ollama.test:11434"),
        ("http://models.test/openai", "http://models.test/openai"),
    ],
)
def test_ollama_root(base_url: str, root: str) -> None:
    assert ollama_root(base_url) == root


@pytest.mark.parametrize(
    ("model", "full"),
    [("bge-m3", "bge-m3:latest"), ("bge-m3:latest", "bge-m3:latest"), ("qwen3:8b", "qwen3:8b")],
)
def test_full_model_name(model: str, full: str) -> None:
    assert full_model_name(model) == full


def test_model_found_by_full_name() -> None:
    entry = {"name": "bge-m3:latest", "model": "bge-m3:latest", "size": 1}

    assert find_local_model(tags({"name": "other:1b"}, "junk", entry), "bge-m3") == entry


def test_model_found_by_name_as_written() -> None:
    entry = {"model": "qwen3:8b", "capabilities": ["completion"]}

    assert find_local_model(tags(entry), "qwen3:8b") == entry


def test_model_not_listed() -> None:
    with pytest.raises(ModelNotLoadedError) as error:
        find_local_model(tags({"name": "bge-m3:latest"}), "qwen3:8b")

    assert str(error.value) == (
        "model 'qwen3:8b' is not loaded in Ollama; load it with: ollama pull qwen3:8b"
    )


@pytest.mark.parametrize("field", ["remote_host", "remote_model"])
def test_model_runs_remotely(field: str) -> None:
    entry = {"name": "big:latest", field: "somewhere"}

    with pytest.raises(RemoteModelError, match="runs remotely"):
        find_local_model(tags(entry), "big")


@pytest.mark.parametrize(
    "body", [b"not json", b"[]", b'{"models": "none"}', b"{}", b'{"models": null}']
)
def test_unreadable_list(body: bytes) -> None:
    with pytest.raises(ModelListError) as error:
        find_local_model(body, "bge-m3")

    assert str(error.value) == "unexpected answer to the model list"


def test_is_timeout() -> None:
    assert is_timeout(TimeoutError())
    assert is_timeout(urllib.error.URLError(TimeoutError()))
    assert not is_timeout(urllib.error.URLError(ConnectionRefusedError()))
    assert not is_timeout(OSError())
