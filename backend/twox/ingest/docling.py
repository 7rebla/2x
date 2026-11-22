"""Convert documents with docling-serve, asynchronously and without holding files in memory.

The only way the backend talks to docling-serve. Three steps, each its own call
so that a queue task (work order 046) can run them separately:

1. :meth:`DocumentConverter.submit` uploads the file to
   ``POST /v1/convert/file/async`` (``multipart/form-data``, streamed in blocks)
   and returns the task ID.
2. :meth:`DocumentConverter.poll` asks ``GET /v1/status/poll/{task_id}``.
3. :meth:`DocumentConverter.fetch` streams ``GET /v1/result/{task_id}`` into a
   binary sink. docling-serve hands out a result once and removes the task
   ``DOCLING_SERVE_RESULT_REMOVAL_DELAY`` seconds after the first fetch, so the
   answer goes straight to durable storage; :func:`load_result` reads it from
   there.

Every request asks for the DoclingDocument JSON, with RapidOCR (E-31, never
EasyOCR, never ``auto``) and image placeholders instead of embedded images.

Errors come as subclasses of :class:`DoclingError` with short English messages
that name neither addresses, paths nor file contents. The original exception
stays attached (``__cause__``) for the server log.

Measured against docling-serve 1.38.2 (work order 041): an unknown task ID
answers ``404 {"detail": "Task not found."}`` on both poll and result, also
after a restart of the service; a result asked for before the task finished
answers ``404 {"detail": "Task result not found. Please wait for a completion
status."}``.
"""

import json
import mimetypes
import re
import socket
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from http.client import HTTPException, HTTPResponse
from typing import Any, BinaryIO, Final, Protocol
from urllib.parse import quote, urlsplit

from django.conf import settings

# E-31: the only OCR engine the backend ever asks for. docling-serve is
# configured to reject every other preset (deploy/compose/compose.yaml).
OCR_PRESET: Final = "rapidocr"
# Images stay out of the JSON; only their position is kept.
IMAGE_EXPORT_MODE: Final = "placeholder"
# The backend builds its sections from the DoclingDocument JSON (E-55).
TO_FORMAT: Final = "json"
# Upper limit per document, equal to DOCLING_SERVE_MAX_DOCUMENT_TIMEOUT (E-55).
DEFAULT_DOCUMENT_TIMEOUT_SECONDS: Final = 2 * 60 * 60.0
# Socket time limit of one HTTP request (connect, and each read or write).
DEFAULT_REQUEST_TIMEOUT_SECONDS: Final = 60.0
# Block size for uploading and for writing the result.
CHUNK_SIZE: Final = 1024 * 1024
# Status and error answers are small; protects against an endless answer.
MAX_SMALL_ANSWER_BYTES: Final = 64 * 1024

SUBMIT_PATH: Final = "/v1/convert/file/async"
POLL_PATH: Final = "/v1/status/poll/"
RESULT_PATH: Final = "/v1/result/"

# docling-serve 1.38.2 answers 404 with this detail while a task exists but has
# no result yet. Every other 404 on poll or result means the task is unknown.
_RESULT_NOT_READY_PREFIX: Final = "Task result not found"
# The caller chooses a neutral name (046: ``version-<id><suffix>``); it ends up
# in a multipart header, so only plain characters are accepted.
_FILENAME_RE: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}")
_TASK_ID_RE: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_CONTENT_TYPE_RE: Final = re.compile(r"[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*")


class DoclingError(Exception):
    """Base class of all errors of the docling-serve interface."""


class DoclingUnavailableError(DoclingError):
    """No connection, time limit, HTTP 5xx or an unusable answer. Retrying makes sense."""


class DoclingTaskLostError(DoclingError):
    """docling-serve no longer knows the task. Submitting the file again makes sense.

    Happens after a restart of docling-serve (tasks live in its memory), after
    a result was fetched and removed, and when a result was never fetched
    within the removal delay.
    """


class DoclingRejectedError(DoclingError):
    """docling-serve refused the request (HTTP 4xx). Retrying does not help."""


class DoclingConversionError(DoclingError):
    """The conversion failed, or its result holds no usable document."""


class TaskStatus(StrEnum):
    """Values of ``task_status`` in docling-serve 1.38.2 (schema ``ConversionStatus``)."""

    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    SKIPPED = "skipped"

    @property
    def finished(self) -> bool:
        """Whether the task has ended and its result can be fetched."""
        return self not in {TaskStatus.PENDING, TaskStatus.STARTED}


@dataclass(frozen=True)
class ConversionStatus:
    """State of a conversion task as reported by :meth:`DocumentConverter.poll`."""

    task_id: str
    status: TaskStatus
    # Place in docling-serve's queue while pending; None otherwise.
    position: int | None

    @property
    def finished(self) -> bool:
        return self.status.finished


@dataclass(frozen=True)
class ConversionErrorItem:
    """One entry of ``errors`` in a conversion result (schema ``ErrorItem``)."""

    component_type: str
    module_name: str
    error_message: str
    page_no: int | None


@dataclass(frozen=True)
class ConversionResult:
    """A stored answer of ``GET /v1/result/{task_id}``, read by :func:`load_result`."""

    status: TaskStatus
    errors: tuple[ConversionErrorItem, ...]
    # Seconds docling-serve spent on the task.
    processing_time: float
    # The DoclingDocument (``document.json_content``) as parsed JSON.
    document: dict[str, Any]


class DocumentConverter(Protocol):
    """Asynchronous document conversion; :class:`DoclingClient` talks to docling-serve."""

    def submit(
        self,
        stream: BinaryIO,
        filename: str,
        content_type: str,
        *,
        page_range: tuple[int, int] | None = None,
        document_timeout: float = DEFAULT_DOCUMENT_TIMEOUT_SECONDS,
    ) -> str:
        """Upload ``stream`` (read in blocks) for conversion; return the task ID."""
        ...

    def poll(self, task_id: str, *, wait: float = 0.0) -> ConversionStatus:
        """Return the state of the task; ``wait`` lets the service hold the answer."""
        ...

    def fetch(self, task_id: str, sink: BinaryIO) -> int:
        """Write the result of a finished task to ``sink`` in blocks; return the byte count.

        On an error, ``sink`` may hold part of the answer and must be discarded.
        """
        ...


def _is_timeout(error: BaseException) -> bool:
    """Return whether ``error`` is a time limit, also when urllib wrapped it."""
    if isinstance(error, TimeoutError):
        return True
    return isinstance(error, urllib.error.URLError) and isinstance(error.reason, TimeoutError)


def _unavailable(error: BaseException) -> DoclingUnavailableError:
    """Turn a transport error into a short message without address or path."""
    if _is_timeout(error):
        return DoclingUnavailableError("docling-serve did not answer within the time limit")
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, ConnectionRefusedError):
        return DoclingUnavailableError("docling-serve refused the connection")
    if isinstance(reason, socket.gaierror):
        return DoclingUnavailableError("the host name of docling-serve does not resolve")
    return DoclingUnavailableError(f"no valid answer from docling-serve ({type(reason).__name__})")


def _read_error_body(error: urllib.error.HTTPError) -> bytes:
    """Read and close an error answer, at most :data:`MAX_SMALL_ANSWER_BYTES`."""
    try:
        return error.read(MAX_SMALL_ANSWER_BYTES)
    except HTTPException, OSError, ValueError:
        return b""
    finally:
        error.close()


def _read_answer(response: HTTPResponse) -> bytes:
    """Read and close a status answer, at most :data:`MAX_SMALL_ANSWER_BYTES`."""
    with response:
        try:
            return response.read(MAX_SMALL_ANSWER_BYTES)
        except (HTTPException, OSError) as error:
            raise _unavailable(error) from error


def _error_detail(body: bytes) -> str:
    """Return ``detail`` of an error answer if it is a plain text, else ``""``."""
    try:
        answer = json.loads(body)
    except ValueError:
        return ""
    detail = answer.get("detail") if isinstance(answer, dict) else None
    return detail if isinstance(detail, str) else ""


def _rejected_fields(body: bytes) -> list[str]:
    """Names of the form fields a validation error (HTTP 422) points at."""
    try:
        answer = json.loads(body)
    except ValueError:
        return []
    details = answer.get("detail") if isinstance(answer, dict) else None
    if not isinstance(details, list):
        return []
    fields: list[str] = []
    for item in details:
        location = item.get("loc") if isinstance(item, dict) else None
        if isinstance(location, list) and location and isinstance(location[-1], str):
            name = location[-1]
            if _FILENAME_RE.fullmatch(name) and name not in fields:
                fields.append(name)
    return fields[:5]


def _rejected(code: int, body: bytes) -> DoclingRejectedError:
    fields = _rejected_fields(body) if code == 422 else []
    suffix = f", fields: {', '.join(fields)}" if fields else ""
    return DoclingRejectedError(f"docling-serve rejected the request (HTTP {code}{suffix})")


def _form_field(boundary: str, name: str, value: str) -> bytes:
    return (
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
    ).encode()


def _multipart_body(
    boundary: str,
    fields: list[tuple[str, str]],
    stream: BinaryIO,
    filename: str,
    content_type: str,
) -> Iterator[bytes]:
    """Yield a ``multipart/form-data`` body; the file is read in blocks of :data:`CHUNK_SIZE`."""
    for name, value in fields:
        yield _form_field(boundary, name, value)
    yield (
        f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{filename}"'
        f"\r\nContent-Type: {content_type}\r\n\r\n"
    ).encode()
    while block := stream.read(CHUNK_SIZE):
        yield block
    yield f"\r\n--{boundary}--\r\n".encode()


def _check_task_id(task_id: str) -> str:
    if not isinstance(task_id, str) or not _TASK_ID_RE.fullmatch(task_id):
        raise ValueError("invalid task ID")
    return task_id


def _parse_status(body: bytes) -> ConversionStatus:
    """Read ``TaskStatusResponse``; anything else counts as an unusable answer."""
    try:
        answer = json.loads(body)
        task_id = answer["task_id"]
        status = TaskStatus(answer["task_status"])
        position = answer.get("task_position")
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise DoclingUnavailableError("unexpected answer from docling-serve") from error
    if not isinstance(task_id, str) or not _TASK_ID_RE.fullmatch(task_id):
        raise DoclingUnavailableError("unexpected answer from docling-serve")
    if position is not None and (not isinstance(position, int) or isinstance(position, bool)):
        position = None
    return ConversionStatus(task_id=task_id, status=status, position=position)


class DoclingClient:
    """:class:`DocumentConverter` for docling-serve at ``settings.TWOX_DOCLING_URL``.

    Standard library only (``urllib``), no proxy: the client always talks to
    the configured address itself.
    """

    def __init__(self, *, timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS) -> None:
        base_url: str = settings.TWOX_DOCLING_URL
        parts = urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("TWOX_DOCLING_URL must look like http://host:port")
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _open(self, request: urllib.request.Request) -> HTTPResponse:
        """Send ``request``; HTTP errors stay ``HTTPError``, transport errors become ours."""
        try:
            response: HTTPResponse = self._opener.open(request, timeout=self._timeout)
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, HTTPException, OSError) as error:
            raise _unavailable(error) from error
        return response

    def _get_or_lost(self, path: str) -> HTTPResponse:
        """``GET`` a task path; map 404 to :class:`DoclingTaskLostError`."""
        request = urllib.request.Request(
            self._base + path, headers={"Accept": "application/json"}, method="GET"
        )
        try:
            return self._open(request)
        except urllib.error.HTTPError as error:
            body = _read_error_body(error)
            if error.code == 404:
                if _error_detail(body).startswith(_RESULT_NOT_READY_PREFIX):
                    raise DoclingRejectedError(
                        "the task has no result yet - wait for a finished status"
                    ) from error
                raise DoclingTaskLostError("docling-serve does not know the task") from error
            if error.code >= 500:
                raise DoclingUnavailableError(
                    f"docling-serve answered with HTTP {error.code}"
                ) from error
            raise _rejected(error.code, body) from error

    def submit(
        self,
        stream: BinaryIO,
        filename: str,
        content_type: str,
        *,
        page_range: tuple[int, int] | None = None,
        document_timeout: float = DEFAULT_DOCUMENT_TIMEOUT_SECONDS,
    ) -> str:
        if not isinstance(filename, str) or not _FILENAME_RE.fullmatch(filename):
            raise ValueError("filename must be a plain name such as version-12.pdf")
        if not _CONTENT_TYPE_RE.fullmatch(content_type):
            raise ValueError("invalid content type")
        if not 0 < document_timeout <= DEFAULT_DOCUMENT_TIMEOUT_SECONDS:
            raise ValueError("document_timeout must be between 0 and 2 hours")
        fields = [
            ("to_formats", TO_FORMAT),
            ("ocr_preset", OCR_PRESET),
            ("image_export_mode", IMAGE_EXPORT_MODE),
            ("document_timeout", f"{document_timeout:g}"),
        ]
        if page_range is not None:
            first, last = page_range
            if not 1 <= first <= last:
                raise ValueError("page_range must be (first, last) with 1 <= first <= last")
            fields += [("page_range", str(first)), ("page_range", str(last))]

        boundary = f"twox-{uuid.uuid4().hex}"
        # An iterable body without Content-Length goes out with chunked
        # transfer encoding: the file is never held in memory as a whole.
        request = urllib.request.Request(
            self._base + SUBMIT_PATH,
            data=_multipart_body(boundary, fields, stream, filename, content_type),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            response = self._open(request)
        except urllib.error.HTTPError as error:
            body = _read_error_body(error)
            if error.code >= 500:
                raise DoclingUnavailableError(
                    f"docling-serve answered with HTTP {error.code}"
                ) from error
            raise _rejected(error.code, body) from error
        return _parse_status(_read_answer(response)).task_id

    def poll(self, task_id: str, *, wait: float = 0.0) -> ConversionStatus:
        _check_task_id(task_id)
        if not 0 <= wait < self._timeout:
            raise ValueError("wait must be at least 0 and below the request time limit")
        path = f"{POLL_PATH}{quote(task_id, safe='')}"
        if wait:
            path += f"?wait={wait:g}"
        return _parse_status(_read_answer(self._get_or_lost(path)))

    def fetch(self, task_id: str, sink: BinaryIO) -> int:
        _check_task_id(task_id)
        written = 0
        with self._get_or_lost(f"{RESULT_PATH}{quote(task_id, safe='')}") as response:
            try:
                while block := response.read(CHUNK_SIZE):
                    sink.write(block)
                    written += len(block)
            except (HTTPException, OSError) as error:
                raise _unavailable(error) from error
        return written


def guess_content_type(filename: str) -> str:
    """Media type for ``filename`` from its suffix; ``application/octet-stream`` if unknown."""
    guessed, _encoding = mimetypes.guess_type(filename, strict=False)
    return guessed or "application/octet-stream"


def _error_items(raw: object) -> tuple[ConversionErrorItem, ...]:
    if not isinstance(raw, list):
        return ()
    items = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        page_no = entry.get("page_no")
        items.append(
            ConversionErrorItem(
                component_type=str(entry.get("component_type", "")),
                module_name=str(entry.get("module_name", "")),
                error_message=str(entry.get("error_message", "")),
                page_no=page_no if isinstance(page_no, int) else None,
            )
        )
    return tuple(items)


def load_result(stream: BinaryIO) -> ConversionResult:
    """Read a stored answer of ``GET /v1/result/{task_id}``.

    Holds the answer in memory once (the known limit, measured in 057). Raises
    :class:`DoclingConversionError` for a failed task, a failed or skipped
    conversion and an answer without DoclingDocument. ``partial_success`` is
    returned with its error list; the caller decides what to keep.
    """
    try:
        answer = json.load(stream)
    except ValueError as error:
        raise DoclingConversionError("the stored result is not valid JSON") from error
    if not isinstance(answer, dict):
        raise DoclingConversionError("the stored result is not a conversion result")
    if answer.get("kind") == "TaskFailureResult":
        failure = answer.get("failure")
        category = failure.get("category") if isinstance(failure, dict) else None
        label = category if isinstance(category, str) and category.isidentifier() else "unknown"
        raise DoclingConversionError(f"the conversion task failed ({label})")
    try:
        status = TaskStatus(str(answer.get("status")))
    except ValueError as error:
        raise DoclingConversionError("the stored result has no valid status") from error
    if status not in {TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS}:
        raise DoclingConversionError(f"the conversion ended with status {status.value}")
    container = answer.get("document")
    document = container.get("json_content") if isinstance(container, dict) else None
    if not isinstance(document, dict) or document.get("schema_name") != "DoclingDocument":
        raise DoclingConversionError("the stored result holds no DoclingDocument")
    processing_time = answer.get("processing_time")
    if not isinstance(processing_time, int | float) or isinstance(processing_time, bool):
        processing_time = 0.0
    return ConversionResult(
        status=status,
        errors=_error_items(answer.get("errors")),
        processing_time=float(processing_time),
        document=document,
    )


def get_document_converter() -> DocumentConverter:
    """The converter the application uses; tests replace this function."""
    return DoclingClient()
