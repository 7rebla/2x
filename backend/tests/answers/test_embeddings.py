"""The embedding client, against a stand-in for Ollama; no test talks to a real model service."""

import json
import socket
from collections.abc import Iterator, Sequence
from contextlib import closing

import pytest
from pytest_django import Settings

from tests.answers.fake_ollama import FakeOllama, fake_ollama, vector_for
from twox.answers import embeddings
from twox.answers.embeddings import (
    Embedder,
    EmbeddingDimensionError,
    EmbeddingDisabledError,
    EmbeddingRejectedError,
    EmbeddingRemoteModelError,
    EmbeddingUnavailableError,
    OpenAICompatibleEmbedder,
    get_embedder,
    is_cloud_model_name,
)

DIMENSIONS = 4


@pytest.fixture(autouse=True)
def ai_enabled(settings: Settings) -> None:
    """AI features on, unless a test switches them off (E-59: both states are tested)."""
    settings.TWOX_AI_ENABLED = True


def make_embedder(
    base_url: str,
    *,
    model: str = "bge-m3",
    dimensions: int = DIMENSIONS,
    batch_size: int = 16,
    query_prefix: str = "",
    timeout: float = 5.0,
) -> OpenAICompatibleEmbedder:
    return OpenAICompatibleEmbedder(
        base_url=base_url,
        model=model,
        dimensions=dimensions,
        batch_size=batch_size,
        query_prefix=query_prefix,
        timeout=timeout,
    )


def unused_port() -> int:
    """Return a loopback port on which nothing listens."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
    return port


@pytest.fixture
def server() -> Iterator[tuple[str, FakeOllama]]:
    with fake_ollama() as running:
        yield running


# --- Batches, order, request body -------------------------------------------


def test_documents_are_sent_in_batches_and_come_back_in_order(
    server: tuple[str, FakeOllama],
) -> None:
    base_url, fake = server
    texts = [f"section {number} " * number for number in range(1, 8)]

    vectors = make_embedder(base_url, batch_size=3).embed_documents(texts)

    assert vectors == [vector_for(text, DIMENSIONS) for text in texts]
    assert [len(request.body["input"]) for request in fake.embed_requests] == [3, 3, 1]
    assert [text for request in fake.embed_requests for text in request.body["input"]] == texts


def test_order_follows_the_index_not_the_position(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server
    fake.reverse_order = True
    texts = ["first", "second text", "third, longer text"]

    vectors = make_embedder(base_url).embed_documents(texts)

    assert vectors == [vector_for(text, DIMENSIONS) for text in texts]


def test_request_has_model_and_input_list_only(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server
    embedder = make_embedder(base_url)

    embedder.embed_documents(["a text"])
    embedder.embed_query("a question")

    assert len(fake.embed_requests) == 2
    for request in fake.embed_requests:
        # No "user" field (Ollama does not support it), no "dimensions".
        assert set(request.body) == {"model", "input"}
        assert request.body["model"] == "bge-m3"
        assert isinstance(request.body["input"], list)


def test_query_prefix_only_for_queries(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server
    embedder = make_embedder(base_url, query_prefix="Query: ")

    query_vector = embedder.embed_query("oil level")
    embedder.embed_documents(["oil level"])

    assert [request.body["input"] for request in fake.embed_requests] == [
        ["Query: oil level"],
        ["oil level"],
    ]
    assert query_vector == vector_for("Query: oil level", DIMENSIONS)


def test_values_are_floats(server: tuple[str, FakeOllama]) -> None:
    base_url, _fake = server

    (vector,) = make_embedder(base_url).embed_documents(["abc"])

    assert all(type(value) is float for value in vector)


def test_no_texts_no_request(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server

    assert make_embedder(base_url).embed_documents([]) == []
    assert fake.requests == []


@pytest.mark.parametrize("texts", ["a plain string", [b"bytes"], ["ok", 1]])
def test_texts_must_be_strings(server: tuple[str, FakeOllama], texts: Sequence[object]) -> None:
    base_url, fake = server

    with pytest.raises(TypeError):
        make_embedder(base_url).embed_documents(texts)  # type: ignore[arg-type]
    assert fake.requests == []


# --- Model check: local models only ------------------------------------------


def test_model_list_is_asked_once_per_embedder(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server
    embedder = make_embedder(base_url)

    embedder.embed_documents(["one"])
    embedder.embed_query("two")

    assert [(request.method, request.path) for request in fake.requests] == [
        ("GET", "/api/tags"),
        ("POST", "/v1/embeddings"),
        ("POST", "/v1/embeddings"),
    ]


@pytest.mark.parametrize("model", ["bge-m3", "bge-m3:latest"])
def test_model_name_without_tag_matches_latest(server: tuple[str, FakeOllama], model: str) -> None:
    base_url, _fake = server

    assert make_embedder(base_url, model=model).embed_query("x") == vector_for("x", DIMENSIONS)


@pytest.mark.parametrize(
    "model", ["gpt-oss:120b-cloud", "minimax-m2:cloud", "Qwen3-Coder:480B-Cloud", "some-cloud"]
)
def test_cloud_model_is_refused_by_name_before_any_request(
    server: tuple[str, FakeOllama], model: str
) -> None:
    base_url, fake = server
    fake.models.append({"name": model, "model": model})

    with pytest.raises(EmbeddingRemoteModelError, match="cloud model"):
        make_embedder(base_url, model=model).embed_documents(["secret manual text"])
    assert fake.requests == []


@pytest.mark.parametrize("model", ["bge-m3", "qwen3-embedding:0.6b", "soundcloud", "cloudy:1b"])
def test_local_model_names_are_not_cloud_names(model: str) -> None:
    assert not is_cloud_model_name(model)


@pytest.mark.parametrize("marker", ["remote_host", "remote_model"])
def test_cloud_model_is_refused_by_the_model_list(
    server: tuple[str, FakeOllama], marker: str
) -> None:
    base_url, fake = server
    fake.models = [{"name": "mirror:latest", "model": "mirror:latest", marker: "remote"}]

    with pytest.raises(EmbeddingRemoteModelError, match="runs remotely"):
        make_embedder(base_url, model="mirror").embed_documents(["secret manual text"])
    assert fake.embed_requests == []


def test_model_missing_from_the_list_names_ollama_pull(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server
    fake.models = [{"name": "qwen3-embedding:0.6b", "model": "qwen3-embedding:0.6b"}]

    with pytest.raises(EmbeddingRejectedError, match="ollama pull bge-m3"):
        make_embedder(base_url).embed_documents(["text"])
    assert fake.embed_requests == []


def test_other_openai_compatible_server_without_model_list(
    server: tuple[str, FakeOllama],
) -> None:
    base_url, fake = server
    fake.tags_status = 404

    assert make_embedder(base_url).embed_query("x") == vector_for("x", DIMENSIONS)
    assert len(fake.embed_requests) == 1


@pytest.mark.parametrize("body", [b"not json", b"[]", b'{"tags": []}'])
def test_unusable_model_list_is_unavailable(server: tuple[str, FakeOllama], body: bytes) -> None:
    base_url, fake = server
    fake.tags_body = body

    with pytest.raises(EmbeddingUnavailableError, match="model list"):
        make_embedder(base_url).embed_query("x")


# --- Errors ------------------------------------------------------------------


def test_unknown_model_404_names_ollama_pull(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server
    fake.embed_status = 404

    with pytest.raises(EmbeddingRejectedError, match="ollama pull bge-m3"):
        make_embedder(base_url).embed_documents(["text"])


def test_other_4xx_is_rejected(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server
    fake.embed_status = 400

    with pytest.raises(EmbeddingRejectedError, match="HTTP 400"):
        make_embedder(base_url).embed_documents(["text"])


@pytest.mark.parametrize("status", [500, 502, 503])
def test_server_error_is_unavailable(server: tuple[str, FakeOllama], status: int) -> None:
    base_url, fake = server
    fake.embed_status = status

    with pytest.raises(EmbeddingUnavailableError, match=f"HTTP {status}"):
        make_embedder(base_url).embed_documents(["text"])


def test_wrong_dimension(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server
    fake.dimensions = 3

    with pytest.raises(EmbeddingDimensionError, match="returned 3 values, expected 4"):
        make_embedder(base_url).embed_documents(["text"])


def test_wrong_number_of_vectors(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server
    fake.drop_one = True

    with pytest.raises(EmbeddingUnavailableError, match="expected 2 vector"):
        make_embedder(base_url).embed_documents(["one", "two"])


@pytest.mark.parametrize(
    "data",
    [
        [{"embedding": [1, 2, 3, 4], "index": 0}, {"embedding": [1, 2, 3, 4], "index": 0}],
        [{"embedding": [1, 2, 3, 4], "index": 0}, {"embedding": [1, 2, 3, 4], "index": 5}],
        [{"embedding": [1, 2, 3, 4], "index": 0}, {"embedding": [1, 2, 3, "4"], "index": 1}],
        [{"embedding": [1, 2, 3, 4], "index": 0}, {"embedding": [1, 2, 3, True], "index": 1}],
        [{"embedding": [1, 2, 3, 4], "index": 0}, "not an object"],
    ],
)
def test_malformed_answer_is_unavailable(server: tuple[str, FakeOllama], data: object) -> None:
    base_url, fake = server
    fake.embed_body = json.dumps({"object": "list", "data": data}).encode()

    with pytest.raises(EmbeddingUnavailableError, match="unexpected answer"):
        make_embedder(base_url).embed_documents(["one", "two"])


def test_non_finite_value_is_unavailable(server: tuple[str, FakeOllama]) -> None:
    base_url, fake = server
    fake.embed_body = b'{"data": [{"embedding": [1, 2, 3, NaN], "index": 0}]}'

    with pytest.raises(EmbeddingUnavailableError, match="not a list of numbers"):
        make_embedder(base_url).embed_documents(["one"])


def test_connection_refused_is_unavailable() -> None:
    base_url = f"http://127.0.0.1:{unused_port()}/v1"

    with pytest.raises(EmbeddingUnavailableError, match="refused the connection") as caught:
        make_embedder(base_url).embed_documents(["text"])
    # No address in the message; the cause stays attached for the log.
    assert "127.0.0.1" not in str(caught.value)
    assert caught.value.__cause__ is not None


def test_timeout_is_unavailable() -> None:
    # The kernel completes the handshake, but nobody ever answers.
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as silent:
        silent.bind(("127.0.0.1", 0))
        silent.listen(1)
        base_url = f"http://127.0.0.1:{silent.getsockname()[1]}/v1"
        with pytest.raises(EmbeddingUnavailableError, match=r"within 0\.3s"):
            make_embedder(base_url, timeout=0.3).embed_documents(["text"])


def test_timeout_after_the_model_check_is_unavailable(
    server: tuple[str, FakeOllama], monkeypatch: pytest.MonkeyPatch
) -> None:
    base_url, _fake = server
    embedder = make_embedder(base_url)
    embedder.embed_query("warm up")

    def silent_open(*args: object, **kwargs: object) -> object:
        raise TimeoutError("timed out")

    monkeypatch.setattr(embedder._opener, "open", silent_open)
    with pytest.raises(EmbeddingUnavailableError, match="within 5s"):
        embedder.embed_documents(["text"])


# --- Construction and settings -----------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base_url": "host.docker.internal:11434"},
        {"base_url": "ftp://host/v1"},
        {"model": " "},
        {"dimensions": 0},
        {"batch_size": 0},
        {"timeout": 0.0},
        {"timeout": float("inf")},
    ],
)
def test_invalid_construction(kwargs: dict[str, object]) -> None:
    values: dict[str, object] = {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "bge-m3",
        "dimensions": 1024,
        "batch_size": 16,
        "query_prefix": "",
        "timeout": 5.0,
    } | kwargs
    with pytest.raises(ValueError):
        OpenAICompatibleEmbedder(**values)  # type: ignore[arg-type]


def test_get_embedder_builds_from_settings(settings: Settings) -> None:
    settings.TWOX_LLM_BASE_URL = "http://host.docker.internal:11434/v1/"
    settings.TWOX_EMBED_MODEL = "qwen3-embedding:0.6b"
    settings.TWOX_EMBED_DIMENSIONS = 1024
    settings.TWOX_EMBED_BATCH_SIZE = 8
    settings.TWOX_EMBED_QUERY_PREFIX = "Query: "
    settings.TWOX_EMBED_TIMEOUT_SECONDS = 30

    embedder = get_embedder()

    assert isinstance(embedder, OpenAICompatibleEmbedder)
    assert embedder.model_name == "qwen3-embedding:0.6b"
    assert embedder.dimensions == 1024
    assert embedder.embeddings_url == "http://host.docker.internal:11434/v1/embeddings"
    assert embedder._batch_size == 8
    assert embedder._query_prefix == "Query: "
    assert embedder._timeout == 30.0


def test_get_embedder_can_be_replaced_by_a_stand_in(monkeypatch: pytest.MonkeyPatch) -> None:
    class StandIn:
        model_name = "stand-in"
        dimensions = 2

        def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
            return [[1.0, 0.0] for _ in texts]

        def embed_query(self, text: str) -> list[float]:
            return [0.0, 1.0]

    stand_in: Embedder = StandIn()
    monkeypatch.setattr(embeddings, "get_embedder", lambda: stand_in)

    assert embeddings.get_embedder().embed_documents(["a", "b"]) == [[1.0, 0.0], [1.0, 0.0]]


# --- AI switched off (E-59) --------------------------------------------------


def test_get_embedder_refuses_when_ai_is_off(settings: Settings) -> None:
    settings.TWOX_AI_ENABLED = False

    with pytest.raises(EmbeddingDisabledError, match="TWOX_AI_ENABLED"):
        get_embedder()


def test_embedder_sends_nothing_when_ai_is_off(
    server: tuple[str, FakeOllama], settings: Settings
) -> None:
    base_url, fake = server
    embedder = make_embedder(base_url)
    settings.TWOX_AI_ENABLED = False

    with pytest.raises(EmbeddingDisabledError):
        embedder.embed_documents(["text"])
    with pytest.raises(EmbeddingDisabledError):
        embedder.embed_query("text")
    assert fake.requests == []


def test_switching_off_stops_an_embedder_that_was_already_used(
    server: tuple[str, FakeOllama], settings: Settings
) -> None:
    base_url, fake = server
    embedder = make_embedder(base_url)
    embedder.embed_query("while on")
    sent = len(fake.requests)
    settings.TWOX_AI_ENABLED = False

    with pytest.raises(EmbeddingDisabledError):
        embedder.embed_query("while off")
    assert len(fake.requests) == sent
