"""Logging helpers: keep query strings, and with them search texts, out of the access log.

uvicorn writes one line per request to the logger ``uvicorn.access``, with
the path and its query string (``GET /api/v1/search/?q=... HTTP/1.1``). A
search text in ``q`` must not land in any log (work order 052, E-57), and
neither should other query parts (filters). :class:`DropQueryString` cuts the
query string off the path of every such record; ``LOGGING`` in
:mod:`twox.config.settings` puts it on ``uvicorn.access``.

uvicorn (0.54) logs an access line as ``'%s - "%s %s HTTP/%s" %d'`` with the
arguments client address, method, path with query string, HTTP version and
status code; :class:`uvicorn.logging.AccessFormatter` reads them in this
order. The filter changes the third argument only.
"""

import logging
from typing import Final

#: Position of the path (with query string) in the arguments of an access record.
PATH_ARGUMENT: Final = 2


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
