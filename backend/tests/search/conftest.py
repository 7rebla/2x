"""Fixtures for the search tests: no test reaches a real model service (E-59)."""

from collections.abc import Iterator

import pytest
from pytest_django.fixtures import Settings

from tests.search.fake_embedder import CLOSED_MODEL_SERVICE, FakeEmbedder, install
from twox.answers.embeddings import forget_query_embedder


@pytest.fixture(autouse=True)
def no_real_model_service(settings: Settings) -> Iterator[None]:
    """AI features off and the model service on a closed port, unless a test says otherwise.

    The containers get ``TWOX_AI_ENABLED=true`` from the development template
    (``.env.example``); each search test sets the state it tests itself and
    uses :class:`FakeEmbedder` for "on". The query embedder of the process
    (and its check of the model list) starts afresh in every test.
    """
    settings.TWOX_AI_ENABLED = False
    settings.TWOX_LLM_BASE_URL = CLOSED_MODEL_SERVICE
    forget_query_embedder()
    yield
    forget_query_embedder()


@pytest.fixture
def fake_embedder(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> FakeEmbedder:
    """AI features on, with :class:`FakeEmbedder` behind the embedding interface."""
    return install(monkeypatch, settings, FakeEmbedder())
