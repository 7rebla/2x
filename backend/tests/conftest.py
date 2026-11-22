"""Fixtures for all backend tests."""

import shutil
import subprocess
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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

#: Tasks whose messages the fixture ingest_messages records instead of sending.
INGEST_TASK_PREFIX = "twox.ingest."


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


@dataclass
class IngestMessages:
    """Messages to the tasks ``twox.ingest.*``, recorded instead of sent to the broker.

    ``sent`` holds ``(task name, args)`` per message. While ``error`` is set,
    every send raises it instead, like a broker that is down.
    """

    sent: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)
    error: Exception | None = None

    def record(self, name: str, args: object) -> None:
        if self.error is not None:
            raise self.error
        self.sent.append((name, tuple(args) if isinstance(args, list | tuple) else ()))

    def names(self) -> list[str]:
        return [name for name, _args in self.sent]


@pytest.fixture(autouse=True)
def ingest_messages(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> IngestMessages:
    """Keep every message to ``twox.ingest.*`` away from the broker (work order 049).

    Since 049 every upload sends ``twox.ingest.convert`` after its commit, in
    tests with ``transaction=True`` as well. Outside the marker ``worker``,
    ``apply_async`` (and with it ``delay``) of each ingest task and
    ``send_task`` with an ingest task name only record the message, so plain
    ``pytest`` needs no Valkey. Tests with the marker ``worker`` send for real.
    """
    record = IngestMessages()
    if request.node.get_closest_marker("worker") is not None:
        return record

    # Imported here: Django is set up by now, and the tasks are registered.
    import twox.ingest.tasks  # noqa: F401
    from twox.config import celery_app

    for name, task in list(celery_app.tasks.items()):
        if name.startswith(INGEST_TASK_PREFIX):
            monkeypatch.setattr(task, "apply_async", _recording_apply_async(record, name))

    original_send_task: Callable[..., object] = celery_app.send_task

    def send_task(name: str, *args: object, **options: object) -> object:
        if name.startswith(INGEST_TASK_PREFIX):
            record.record(name, args[0] if args else options.get("args"))
            return None
        return original_send_task(name, *args, **options)

    monkeypatch.setattr(celery_app, "send_task", send_task)
    return record


def _recording_apply_async(record: IngestMessages, name: str) -> Callable[..., None]:
    def apply_async(args: object = None, kwargs: object = None, **options: object) -> None:
        record.record(name, args)

    return apply_async


@pytest.fixture(autouse=True)
def local_memory_cache(settings: Settings) -> Iterator[None]:
    """Use an in-process cache, so that plain ``pytest`` needs no Valkey.

    The cache is emptied after every test; nothing leaks from one to the next.
    """
    settings.CACHES = TEST_CACHES
    yield
    cache.clear()
