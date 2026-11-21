"""Fixtures for all backend tests."""

from collections.abc import Iterator

import pytest
from django.core.cache import cache
from pytest_django.fixtures import Settings

TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "twox-tests",
    }
}


@pytest.fixture(autouse=True)
def local_memory_cache(settings: Settings) -> Iterator[None]:
    """Use an in-process cache, so that plain ``pytest`` needs no Valkey.

    The cache is emptied after every test; nothing leaks from one to the next.
    """
    settings.CACHES = TEST_CACHES
    yield
    cache.clear()
