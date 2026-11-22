"""Logging helpers: keep query strings and client addresses out of the access log.

uvicorn writes one line per request to the logger ``uvicorn.access``, with
the client address and port and the path with its query string
(``127.0.0.1:50000 - "GET /api/v1/search/?q=... HTTP/1.1" 200``). A search
text in ``q`` must not land in any log (work order 052, E-57), and neither
should other query parts (filters). The client address is not logged either,
also not for failed sign-ins (work order 069, E-62).

:class:`DropQueryString` cuts the query string off the path of every such
record; :class:`DropClientAddress` replaces the client address with ``-``.
``LOGGING`` in :mod:`twox.config.settings` puts both on ``uvicorn.access``
and gives that logger a format without the client address.

uvicorn (0.54) logs an access line as ``'%s - "%s %s HTTP/%s" %d'`` with the
arguments client address, method, path with query string, HTTP version and
status code; :class:`uvicorn.logging.AccessFormatter` reads them in this
order. The filters change the first or the third argument only and keep the
number of arguments, so any formatter still gets a record of that shape.
"""

import logging
from typing import Final

#: Position of the client address (``host:port``) in the arguments of an access record.
CLIENT_ARGUMENT: Final = 0
#: Position of the path (with query string) in the arguments of an access record.
PATH_ARGUMENT: Final = 2
#: Number of arguments of an access record.
ACCESS_ARGUMENTS: Final = 5
#: Stands in for the client address in an access record.
NO_CLIENT_ADDRESS: Final = "-"


def without_query_string(path: str) -> str:
    """``path`` without its query string (``?`` and everything after it)."""
    return path.partition("?")[0]


class DropQueryString(logging.Filter):
    """Remove the query string from the path of uvicorn's access log records.

    Records of another shape pass unchanged. No record is dropped: the
    access log still names method, path and status.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Cut the query string off the path argument of ``record``; always keep the record."""
        args = record.args
        if isinstance(args, tuple) and len(args) > PATH_ARGUMENT:
            path = args[PATH_ARGUMENT]
            if isinstance(path, str) and "?" in path:
                record.args = (
                    *args[:PATH_ARGUMENT],
                    without_query_string(path),
                    *args[PATH_ARGUMENT + 1 :],
                )
        return True


class DropClientAddress(logging.Filter):
    """Replace the client address in uvicorn's access log records with ``-``.

    Only records with the five arguments of an access line and a text as
    first argument are changed; others pass unchanged. No record is dropped.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Put ``-`` in place of the client address of ``record``; always keep the record."""
        args = record.args
        if (
            isinstance(args, tuple)
            and len(args) == ACCESS_ARGUMENTS
            and isinstance(args[CLIENT_ARGUMENT], str)
        ):
            record.args = (
                *args[:CLIENT_ARGUMENT],
                NO_CLIENT_ADDRESS,
                *args[CLIENT_ARGUMENT + 1 :],
            )
        return True
