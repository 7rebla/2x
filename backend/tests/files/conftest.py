"""Fixtures of the files tests (test_services.py keeps its own copies)."""

from pathlib import Path

import pytest
from pytest_django.fixtures import Settings


@pytest.fixture
def media_root(tmp_path: Path, settings: Settings) -> Path:
    """A fresh storage root per test; nothing touches the media volume."""
    root = tmp_path / "media"
    root.mkdir()
    settings.TWOX_MEDIA_ROOT = root
    return root
