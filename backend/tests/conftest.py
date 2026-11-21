"""Fixtures for all backend tests."""

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.core.cache import cache
from django.test import override_settings
from pytest_django.fixtures import Settings

TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "twox-tests",
    }
}


def compile_catalogues(source: Path, target: Path) -> list[Path]:
    """Compile every ``.po`` file below ``source`` into the same layout below ``target``.

    Uses ``msgfmt --check`` from GNU gettext (dev image only, E-46). Returns
    the compiled files; fails if there is no catalogue at all.
    """
    msgfmt = shutil.which("msgfmt")
    if msgfmt is None:
        pytest.fail("msgfmt not found: the tests need GNU gettext (dev image).")
    compiled = []
    for po_file in sorted(source.rglob("*.po")):
        mo_file = target / po_file.relative_to(source).with_suffix(".mo")
        mo_file.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([msgfmt, "--check", "-o", str(mo_file), str(po_file)], check=True)
        compiled.append(mo_file)
    if not compiled:
        pytest.fail(f"No translation catalogue below {source}.")
    return compiled


@pytest.fixture(scope="session", autouse=True)
def compiled_catalogues(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """Translate the catalogues of ``LOCALE_PATHS`` once per test session.

    The ``.mo`` files go to a temporary directory outside the source tree, so
    plain ``pytest`` needs no preparatory step and the bind mount never gets a
    compiled catalogue (E-34). ``LOCALE_PATHS`` points there for all tests.
    """
    target = tmp_path_factory.mktemp("locale")
    for index, source in enumerate(django_settings.LOCALE_PATHS):
        compile_catalogues(Path(source), target / str(index))
    locale_paths = [str(target / str(index)) for index in range(len(django_settings.LOCALE_PATHS))]
    with override_settings(LOCALE_PATHS=locale_paths):
        yield target


@pytest.fixture(autouse=True)
def local_memory_cache(settings: Settings) -> Iterator[None]:
    """Use an in-process cache, so that plain ``pytest`` needs no Valkey.

    The cache is emptied after every test; nothing leaks from one to the next.
    """
    settings.CACHES = TEST_CACHES
    yield
    cache.clear()
