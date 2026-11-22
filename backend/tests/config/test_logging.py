"""Query strings stay out of uvicorn's access log (work order 052, E-57)."""

import io
import logging
import logging.config
from collections.abc import Iterator
from typing import Any

import pytest
from django.conf import settings
from uvicorn.config import LOGGING_CONFIG as UVICORN_LOGGING
from uvicorn.logging import AccessFormatter

from twox.config.logging import DropQueryString, without_query_string

ACCESS = "uvicorn.access"
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", ACCESS)
#: uvicorn's format of an access line and its arguments (0.54, h11_impl.py).
ACCESS_FORMAT = '%s - "%s %s HTTP/%s" %d'


def access_record(path: str, args: Any = None) -> logging.LogRecord:  # noqa: ANN401 - any args
    """A record as uvicorn logs it for one request."""
    if args is None:
        args = ("127.0.0.1:50000", "GET", path, "1.1", 200)
    return logging.LogRecord(ACCESS, logging.INFO, __file__, 1, ACCESS_FORMAT, args, None)


def formatted(record: logging.LogRecord) -> str:
    return AccessFormatter(
        fmt='%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        use_colors=False,
    ).format(record)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/v1/search/?q=zzprobe", "/api/v1/search/"),
        ("/api/v1/search/?q=a?b&device=1", "/api/v1/search/"),
        ("/api/v1/search/?", "/api/v1/search/"),
        ("/api/v1/health/", "/api/v1/health/"),
        ("/", "/"),
    ],
)
def test_without_query_string(path: str, expected: str) -> None:
    assert without_query_string(path) == expected


def test_filter_removes_the_query_string_and_keeps_the_record() -> None:
    record = access_record("/api/v1/search/?q=zzprobe&device=3")

    assert DropQueryString().filter(record) is True

    line = formatted(record)
    assert "zzprobe" not in line
    assert "device" not in line
    assert '"GET /api/v1/search/ HTTP/1.1" 200 OK' in line
    assert "127.0.0.1:50000" in line


def test_filter_leaves_a_path_without_query_string_unchanged() -> None:
    record = access_record("/api/v1/health/")

    DropQueryString().filter(record)

    assert record.args == ("127.0.0.1:50000", "GET", "/api/v1/health/", "1.1", 200)


@pytest.mark.parametrize(
    "args",
    [(), ("only", "two"), ("a", "GET", 5, "1.1", 200), ({"path": "/x?q=1"},)],
    ids=["empty", "short", "not text", "mapping"],
)
def test_filter_leaves_other_records_alone(args: Any) -> None:  # noqa: ANN401 - any args
    record = logging.LogRecord(ACCESS, logging.INFO, __file__, 1, "message", args, None)
    before = record.args

    assert DropQueryString().filter(record) is True
    assert record.args == before


@pytest.fixture
def restored_uvicorn_loggers() -> Iterator[None]:
    """Put the uvicorn loggers back as they were after the test."""
    loggers = [logging.getLogger(name) for name in UVICORN_LOGGERS]
    saved = [
        (logger.handlers[:], logger.filters[:], logger.propagate, logger.level)
        for logger in loggers
    ]
    yield
    for logger, (handlers, filters, propagate, level) in zip(loggers, saved, strict=True):
        logger.handlers = handlers
        logger.filters = filters
        logger.propagate = propagate
        logger.level = level


def test_django_logging_after_uvicorn_keeps_an_access_log_without_query_strings(
    restored_uvicorn_loggers: None,
) -> None:
    # The order at start: uvicorn configures its loggers, then loads the
    # application, and Django configures LOGGING.
    logging.config.dictConfig(UVICORN_LOGGING)
    logging.config.dictConfig(settings.LOGGING)
    logger = logging.getLogger(ACCESS)

    # uvicorn writes access lines only if the logger has a handler.
    assert logger.hasHandlers()
    assert logger.propagate is False
    assert logger.getEffectiveLevel() == logging.INFO
    assert any(isinstance(item, DropQueryString) for item in logger.filters)
    (handler,) = logger.handlers
    assert isinstance(handler, logging.StreamHandler)
    assert isinstance(handler.formatter, AccessFormatter)

    stream = io.StringIO()
    handler.setStream(stream)
    logger.info(ACCESS_FORMAT, "127.0.0.1:50000", "GET", "/api/v1/search/?q=zzprobe", "1.1", 200)

    line = stream.getvalue()
    assert "/api/v1/search/" in line
    assert "zzprobe" not in line
