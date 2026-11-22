"""Fixtures for the search tests: no test reaches a real model service (E-59)."""

import pytest
from pytest_django.fixtures import Settings

from tests.search.fake_embedder import CLOSED_MODEL_SERVICE, FakeEmbedder, install


@pytest.fixture(autouse=True)
def no_real_model_service(settings: Settings) -> None:
    """AI features off and the model service on a closed port, unless a test says otherwise.

    The containers get ``TWOX_AI_ENABLED=true`` from the development template
    (``.env.example``); each search test sets the state it tests itself and
    uses :class:`FakeEmbedder` for "on".
    """
    settings.TWOX_AI_ENABLED = False
    settings.TWOX_LLM_BASE_URL = CLOSED_MODEL_SERVICE


@pytest.fixture
def fake_embedder(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> FakeEmbedder:
    """AI features on, with :class:`FakeEmbedder` behind the embedding interface."""
    return install(monkeypatch, settings, FakeEmbedder())
