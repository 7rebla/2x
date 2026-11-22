"""A stand-in for the embedding interface (044) in the search tests.

It returns hand-made vectors with 1024 values: the query vector points along
the first axis, a section vector at an angle ``θ`` to it has the cosine
distance ``1 - cos θ``. So a test decides the order of the vector list by
the angles alone. No test talks to a real model service (E-59).
"""

import math
from collections.abc import Sequence

import pytest
from pytest_django.fixtures import Settings

from twox.answers import embeddings
from twox.answers.embeddings import EmbeddingError
from twox.ingest.models import EMBEDDING_DIMENSIONS, Section

#: Model name the stand-in reports; sections embedded "with the current model" carry it.
FAKE_MODEL = "fake-embed"
#: Where the model service would be: a closed port on the container itself.
CLOSED_MODEL_SERVICE = "http://127.0.0.1:9/v1"


def unit(axis: int) -> list[float]:
    """The vector of length 1 along ``axis``."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[axis] = 1.0
    return vector


#: The vector of every query the stand-in does not know.
QUERY = unit(0)


def at_angle(degrees: float, axis: int = 1) -> list[float]:
    """A vector at ``degrees`` to :data:`QUERY`, turned towards ``axis``."""
    radians = math.radians(degrees)
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[0] = math.cos(radians)
    vector[axis] = math.sin(radians)
    return vector


def cosine_distance(degrees: float) -> float:
    """The cosine distance of :func:`at_angle` to :data:`QUERY`."""
    return 1.0 - math.cos(math.radians(degrees))


class FakeEmbedder:
    """Embeds queries only, with fixed vectors; records every query it was given."""

    def __init__(self, model_name: str = FAKE_MODEL) -> None:
        self._model_name = model_name
        #: Query text -> vector; other queries get :data:`QUERY`.
        self.queries: dict[str, list[float]] = {}
        #: When set, every call raises it (the model service failed).
        self.error: EmbeddingError | None = None
        self.calls: list[str] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return EMBEDDING_DIMENSIONS

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise AssertionError("the search embeds queries only")

    def embed_query(self, text: str) -> list[float]:
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return list(self.queries.get(text, QUERY))


def install(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, embedder: FakeEmbedder
) -> FakeEmbedder:
    """Switch AI features on; :func:`~twox.answers.embeddings.get_embedder` returns ``embedder``."""
    settings.TWOX_AI_ENABLED = True
    monkeypatch.setattr(embeddings, "get_embedder", lambda: embedder)
    return embedder


def embed(section: Section, vector: Sequence[float], model: str = FAKE_MODEL) -> None:
    """Store ``vector`` as the embedding of ``section``, as 048 would."""
    Section.objects.filter(pk=section.pk).update(embedding=list(vector), embedding_model=model)
