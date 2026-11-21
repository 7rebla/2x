"""Size limit for uploads, enforced before and while the request body is read.

All checks compare with ``settings.TWOX_UPLOAD_MAX_BYTES`` (E-42) and answer
413. They work in layers:

1. :class:`RequestBodyLimitMiddleware` wraps the ASGI application
   (``twox/config/asgi.py``). Django's ASGI handler reads the complete body
   into a temporary file before any view runs, so a check in a view alone
   comes too late to protect the disk. The middleware refuses a request whose
   ``Content-Length`` is larger than :func:`max_request_bytes` before Django
   reads anything, and stops a body without that header as soon as it grows
   past the same bound.
2. :func:`check_content_length` makes the same comparison in the upload views
   before the body is parsed (also under WSGI and in the test client).
3. :class:`LimitedUploadHandler` counts the bytes of the uploaded files while
   Django's multipart parser streams them and aborts with ``StopUpload`` once
   they exceed the limit. Django then closes the files of the following
   handlers; a temporary file on disk is deleted with it.

The services (``twox.files.services``) check the size once more.

Django's own memory limits stay as they are: a file part above
``FILE_UPLOAD_MAX_MEMORY_SIZE`` goes to a temporary file in
``FILE_UPLOAD_TEMP_DIR`` (the system default), bounded per request by the
checks above.

:class:`LimitedUploadView` bundles 2 and 3 for DRF views with uploads; it is
meant for the CSV import (work order 031) as well.
"""

import json
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler, StopUpload, load_handler
from django.http import HttpRequest
from django.utils.translation import gettext
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.views import APIView

#: Room for the multipart framing and the form fields besides the file
#: (boundaries, part headers, title, kind) when the whole body is compared
#: with the file limit.
MULTIPART_OVERHEAD_BYTES = 64 * 1024

# As Django's ASGI handler declares them (django-stubs).
type Scope = dict[str, Any]
type Message = Mapping[str, Any]
type Receive = Callable[[], Awaitable[Message]]
type Send = Callable[[Message], Awaitable[None]]
type ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def max_upload_bytes() -> int:
    """The largest file accepted, in bytes (``TWOX_UPLOAD_MAX_BYTES``)."""
    value: int = settings.TWOX_UPLOAD_MAX_BYTES
    return value


def max_request_bytes() -> int:
    """The largest request body accepted: one file at the limit plus the form around it."""
    return max_upload_bytes() + MULTIPART_OVERHEAD_BYTES


def too_large_message() -> str:
    """The message of every 413 answer, marked for translation."""
    return gettext("The file is larger than the limit of %(max_bytes)d bytes.") % {
        "max_bytes": max_upload_bytes()
    }


class UploadTooLarge(APIException):
    """413: the upload exceeds ``TWOX_UPLOAD_MAX_BYTES``."""

    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_code = "upload_too_large"

    def __init__(self) -> None:
        super().__init__(detail=too_large_message(), code=self.default_code)


def declared_content_length(meta: Mapping[str, Any]) -> int | None:
    """The ``CONTENT_LENGTH`` of a request as a number; ``None`` if absent or invalid."""
    raw = meta.get("CONTENT_LENGTH")
    if not raw:
        return None
    try:
        value = int(raw)
    except TypeError, ValueError:
        return None
    return value if value >= 0 else None


def check_content_length(request: HttpRequest) -> None:
    """Raise :class:`UploadTooLarge` if the declared body is larger than allowed.

    Runs before the body is parsed. A missing or invalid header is left to the
    parser and to :class:`LimitedUploadHandler`.
    """
    length = declared_content_length(request.META)
    if length is not None and length > max_request_bytes():
        raise UploadTooLarge


class LimitedUploadHandler(FileUploadHandler):
    """First upload handler of a request: counts file bytes, aborts past the limit.

    It passes every chunk on to the next handler unchanged. Once the files of
    the request together exceed ``max_bytes`` it sets :attr:`exceeded` and
    raises ``StopUpload(connection_reset=True)``: Django's parser stops at
    once, reads no further and closes the files of the other handlers, which
    deletes a temporary file on disk.
    """

    def __init__(self, request: HttpRequest, max_bytes: int) -> None:
        super().__init__(request)
        self.max_bytes = max_bytes
        self.received = 0
        self.exceeded = False

    def receive_data_chunk(self, raw_data: bytes, start: int) -> bytes | None:
        self.received += len(raw_data)
        if self.received > self.max_bytes:
            self.exceeded = True
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size: int) -> None:
        # The next handler builds the file object.
        return None


def install_upload_limit(request: HttpRequest) -> LimitedUploadHandler:
    """Check the declared size and put :class:`LimitedUploadHandler` first.

    Call before anything reads ``request.POST`` or ``request.FILES``. The
    handlers of ``FILE_UPLOAD_HANDLERS`` follow unchanged.
    """
    check_content_length(request)
    limit = LimitedUploadHandler(request, max_upload_bytes())
    request.upload_handlers = [
        limit,
        *(load_handler(path, request) for path in settings.FILE_UPLOAD_HANDLERS),
    ]
    return limit


class LimitedUploadView(APIView):
    """Base class of DRF views that take ``multipart/form-data`` uploads.

    Only the multipart parser is used (the global setting stays JSON). Before
    authentication runs - the CSRF check of a session reads the form - every
    POST gets the size check and :class:`LimitedUploadHandler`. Read the form
    with :meth:`upload_data`, which answers 413 if the parser was stopped.
    """

    parser_classes = (MultiPartParser,)

    _upload_limit: LimitedUploadHandler | None = None

    def initial(self, request: Request, *args: object, **kwargs: object) -> None:
        if request.method == "POST":
            self._upload_limit = install_upload_limit(request._request)
        super().initial(request, *args, **kwargs)

    def upload_data(self, request: Request) -> dict[str, Any] | list[Any]:
        """Parse the form (if not done yet) and return it with the files."""
        data = request.data
        if self._upload_limit is not None and self._upload_limit.exceeded:
            raise UploadTooLarge
        return data


async def _send_too_large(send: Send) -> None:
    body = json.dumps({"detail": too_large_message()}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"x-content-type-options", b"nosniff"),
                (b"connection", b"close"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestBodyLimitMiddleware:
    """ASGI middleware: no request body larger than :func:`max_request_bytes`.

    A request with a larger ``Content-Length`` gets 413 before the
    application is called. A body without that header is counted while the
    application reads it; past the bound the application sees a disconnect
    (Django then stops reading and drops what it has) and the client gets 413.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = max_request_bytes()
        length = _header_content_length(scope)
        if length is not None and length > limit:
            await _send_too_large(send)
            return

        received = 0
        exceeded = False
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            if exceeded:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    return {"type": "http.disconnect"}
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        await self.app(scope, limited_receive, tracking_send)
        if exceeded and not response_started:
            await _send_too_large(send)


def _header_content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", ()):
        if name.lower() == b"content-length":
            return declared_content_length({"CONTENT_LENGTH": value.decode("latin-1")})
    return None
