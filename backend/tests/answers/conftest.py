"""Fixtures for the tests of the answer context (125); used only where a test names them.

They follow ``tests/search/conftest.py``: no test reaches a real model service
(E-59). They are not ``autouse``, so the other tests of this package keep
their own set-up.
"""

from collections.abc import Iterator

import pytest
from pytest_django.fixtures import Settings

from tests.search.fake_embedder import CLOSED_MODEL_SERVICE, FAKE_MODEL, FakeEmbedder, install
from twox.answers.embeddings import forget_query_embedder


@pytest.fixture
def no_real_model_service(settings: Settings) -> Iterator[None]:
    """AI features off and the model service on a closed port, unless a test says otherwise."""
    settings.TWOX_AI_ENABLED = False
    settings.TWOX_LLM_BASE_URL = CLOSED_MODEL_SERVICE
    forget_query_embedder()
    yield
    forget_query_embedder()


@pytest.fixture
def every_text_a_source(settings: Settings) -> None:
    """Sections of a few words count as sources (``TWOX_ANSWER_MIN_SOURCE_CHARS`` 1).

    For tests whose texts are short on purpose and that test something else
    than the rule for short sections (work order 153, ``test_context.py``).
    """
    settings.TWOX_ANSWER_MIN_SOURCE_CHARS = 1


@pytest.fixture
def fake_embedder(
    no_real_model_service: None, monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> FakeEmbedder:
    """AI features on, with :class:`FakeEmbedder`; its model is the current embedding model."""
    settings.TWOX_EMBED_MODEL = FAKE_MODEL
    return install(monkeypatch, settings, FakeEmbedder())
