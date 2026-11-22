"""uvicorn's access log keeps no query strings (work order 052, E-57) and no
client addresses (work order 069, E-62)."""

import io
import json
import logging
import logging.config
from collections.abc import Iterator
from typing import Any

import pytest
from django.conf import settings
from django.test import Client
from uvicorn.config import LOGGING_CONFIG as UVICORN_LOGGING
from uvicorn.logging import AccessFormatter

from twox.config.logging import (
    NO_CLIENT_ADDRESS,
    DropClientAddress,
    DropQueryString,
    without_query_string,
)

ACCESS = "uvicorn.access"
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", ACCESS)
#: uvicorn's format of an access line and its arguments (0.54, h11_impl.py).
ACCESS_FORMAT = '%s - "%s %s HTTP/%s" %d'
#: uvicorn's default format of the access log, which shows the client address.
UVICORN_ACCESS_FMT = '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
#: A client address from a documentation range (RFC 5737) and a port.
CLIENT_HOST = "198.51.100.23"
CLIENT_ADDRESS = f"{CLIENT_HOST}:50000"
LOGIN_URL = "/_allauth/browser/v1/auth/login"


def access_record(path: str, args: Any = None) -> logging.LogRecord:  # noqa: ANN401 - any args
    """A record as uvicorn logs it for one request."""
    if args is None:
        args = (CLIENT_ADDRESS, "GET", path, "1.1", 200)
    return logging.LogRecord(ACCESS, logging.INFO, __file__, 1, ACCESS_FORMAT, args, None)


def formatted(record: logging.LogRecord, fmt: str = UVICORN_ACCESS_FMT) -> str:
    """``record`` as uvicorn's access formatter writes it, by default with uvicorn's format."""
    return AccessFormatter(fmt=fmt, use_colors=False).format(record)


def project_fmt() -> str:
    """The format of the access log in ``LOGGING``."""
    fmt: str = settings.LOGGING["formatters"]["uvicorn_access"]["fmt"]
    return fmt


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


def test_filter_leaves_a_path_without_query_string_unchanged() -> None:
    record = access_record("/api/v1/health/")

    DropQueryString().filter(record)

    assert record.args == (CLIENT_ADDRESS, "GET", "/api/v1/health/", "1.1", 200)


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


@pytest.mark.parametrize("address", [CLIENT_ADDRESS, "[2001:db8::1]:443", ""])
def test_client_address_filter_replaces_the_address_and_keeps_the_record(address: str) -> None:
    record = access_record("/api/v1/health/", (address, "GET", "/api/v1/health/", "1.1", 200))

    assert DropClientAddress().filter(record) is True

    assert record.args == (NO_CLIENT_ADDRESS, "GET", "/api/v1/health/", "1.1", 200)
    # Also uvicorn's default format, which has a place for the address, shows none.
    line = formatted(record)
    assert line == 'INFO:     - - "GET /api/v1/health/ HTTP/1.1" 200 OK'
    # And a plain formatter on the message alone.
    assert record.getMessage() == '- - "GET /api/v1/health/ HTTP/1.1" 200'


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("only", "two"),
        (CLIENT_ADDRESS, "GET", "/x", "1.1"),
        (CLIENT_ADDRESS, "GET", "/x", "1.1", 200, "extra"),
        (("198.51.100.23", 50000), "GET", "/x", "1.1", 200),
        ({"client": CLIENT_ADDRESS},),
    ],
    ids=["empty", "short", "four", "six", "not text", "mapping"],
)
def test_client_address_filter_leaves_other_records_alone(args: Any) -> None:  # noqa: ANN401
    record = logging.LogRecord(ACCESS, logging.INFO, __file__, 1, "message", args, None)
    before = record.args

    assert DropClientAddress().filter(record) is True
    assert record.args == before


def test_project_format_has_no_client_address() -> None:
    assert "client_addr" not in project_fmt()
    record = access_record("/api/v1/health/")

    line = formatted(record, project_fmt())

    assert line == 'INFO:     "GET /api/v1/health/ HTTP/1.1" 200 OK'


def test_both_filters_leave_method_path_and_status() -> None:
    record = access_record("/api/v1/search/?q=zzprobe&device=3")

    DropClientAddress().filter(record)
    DropQueryString().filter(record)

    for line in (formatted(record), formatted(record, project_fmt()), record.getMessage()):
        assert '"GET /api/v1/search/ HTTP/1.1" 200' in line
        assert CLIENT_HOST not in line
        assert "50000" not in line
        assert "zzprobe" not in line
        assert "device" not in line


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


def configured_access_log() -> tuple[logging.Logger, io.StringIO]:
    """Configure logging as at start and return the access logger and its output.

    The order at start: uvicorn configures its loggers, then loads the
    application, and Django configures LOGGING.
    """
    logging.config.dictConfig(UVICORN_LOGGING)
    logging.config.dictConfig(settings.LOGGING)
    logger = logging.getLogger(ACCESS)
    (handler,) = logger.handlers
    assert isinstance(handler, logging.StreamHandler)
    stream = io.StringIO()
    handler.setStream(stream)
    return logger, stream


def test_django_logging_after_uvicorn_keeps_an_access_log_without_query_strings_and_addresses(
    restored_uvicorn_loggers: None,
) -> None:
    logger, stream = configured_access_log()

    # uvicorn writes access lines only if the logger has a handler.
    assert logger.hasHandlers()
    assert logger.propagate is False
    assert logger.getEffectiveLevel() == logging.INFO
    assert any(isinstance(item, DropQueryString) for item in logger.filters)
    assert any(isinstance(item, DropClientAddress) for item in logger.filters)
    (handler,) = logger.handlers
    assert isinstance(handler.formatter, AccessFormatter)

    logger.info(ACCESS_FORMAT, CLIENT_ADDRESS, "GET", "/api/v1/search/?q=zzprobe", "1.1", 200)

    line = stream.getvalue()
    assert '"GET /api/v1/search/ HTTP/1.1" 200 OK' in line
    assert "zzprobe" not in line
    assert CLIENT_HOST not in line
    assert "50000" not in line


@pytest.mark.django_db
def test_failed_sign_in_logs_no_client_address(
    restored_uvicorn_loggers: None, caplog: pytest.LogCaptureFixture
) -> None:
    logger, stream = configured_access_log()
    caplog.set_level(logging.DEBUG)

    response = Client().post(
        LOGIN_URL,
        data=json.dumps({"username": "test-nobody", "password": "test-only-wrong-pw-2"}),
        content_type="application/json",
        REMOTE_ADDR=CLIENT_HOST,
    )
    # The access line uvicorn writes for this request.
    logger.info(ACCESS_FORMAT, CLIENT_ADDRESS, "POST", LOGIN_URL, "1.1", response.status_code)

    assert response.status_code == 400
    assert "Failed sign-in for username 'test-nobody'." in caplog.messages
    assert CLIENT_HOST not in caplog.text
    line = stream.getvalue()
    assert f'"POST {LOGIN_URL} HTTP/1.1" 400 Bad Request' in line
    assert CLIENT_HOST not in line
    assert "50000" not in line
