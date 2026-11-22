"""Creating documents and versions: the one way for API, acceptance and ingestion.

:func:`create_document` and :func:`add_version` check the upload, write its
bytes through the blob storage interface (``twox.files.storage``) and create
the rows in one database transaction. Once that transaction is committed, the
new version of a ``document`` is handed to the ingestion
(:func:`twox.ingest.services.request_ingest`, work order 049): an explicit
call, no signal. A failure there is logged and never fails the upload; a
transaction that rolls back starts no ingestion.

Rules (E-37, E-42):

- Only ``kind=document`` is accepted in M1. Configurations may hold access
  data, which is only redacted from M5 on (guard rail 5); they are rejected
  with :class:`ConfigurationNotAcceptedError` before anything is stored.
- The same content as the newest version of the same document is rejected
  with :class:`DuplicateVersionError`. The same content anywhere else is
  accepted; :attr:`UploadResult.duplicates` names the other places. The bytes
  are stored once in any case (content-addressed storage).
- An upload larger than ``settings.TWOX_UPLOAD_MAX_BYTES`` is rejected with
  :class:`UploadTooLargeError`, by its declared size and while reading.

Known limit: if the database transaction fails after the blob was written, the
blob stays in the storage without a version. It is harmless (same content,
same key) and there is no deletion in M1.
"""

import logging
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from functools import partial
from typing import Protocol

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext

from twox.accounts.models import User
from twox.assets.models import Device
from twox.files.models import (
    CONTENT_TYPE_MAX_LENGTH,
    CONTENT_TYPE_PATTERN,
    FILENAME_MAX_LENGTH,
    TITLE_MAX_LENGTH,
    Document,
    DocumentKind,
    DocumentVersion,
)
from twox.files.storage import StoredBlob, get_blob_storage

logger = logging.getLogger(__name__)

#: Replacement for a file name that is empty after cleaning.
FALLBACK_FILENAME = "unnamed"

#: Content type when the upload declares none or an invalid one.
FALLBACK_CONTENT_TYPE = "application/octet-stream"

#: An extension up to this length is kept when a long file name is shortened.
_MAX_KEPT_EXTENSION = 20

#: Unicode categories removed from names: control (Cc) and format (Cf)
#: characters, for example NUL, line breaks and right-to-left overrides.
_REMOVED_CATEGORIES = frozenset({"Cc", "Cf"})

_CONTENT_TYPE_RE = re.compile(CONTENT_TYPE_PATTERN)


class Upload(Protocol):
    """What the services read from an upload; Django's ``UploadedFile`` fits."""

    @property
    def name(self) -> str | None: ...

    @property
    def size(self) -> int | None: ...

    @property
    def content_type(self) -> str | None: ...

    def chunks(self, chunk_size: int | None = None) -> Iterator[bytes]: ...


class UploadError(Exception):
    """Base class of all errors of the upload services; the message is translated."""


class UploadTooLargeError(UploadError):
    """The upload is larger than ``TWOX_UPLOAD_MAX_BYTES``."""

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes
        super().__init__(
            gettext("The file is larger than the limit of %(max_bytes)d bytes.")
            % {"max_bytes": max_bytes}
        )


class ConfigurationNotAcceptedError(UploadError):
    """Configuration files are not accepted before redaction exists (M5)."""

    def __init__(self) -> None:
        super().__init__(
            gettext(
                "Configuration files are not accepted yet: access data in them "
                "cannot be redacted before a later version."
            )
        )


class DuplicateVersionError(UploadError):
    """The content equals the newest version of the same document."""

    def __init__(self, version: DocumentVersion) -> None:
        self.version = version
        super().__init__(
            gettext("The file is identical to the newest version %(number)d of this document.")
            % {"number": version.number}
        )


@dataclass(frozen=True, slots=True)
class DuplicateLocation:
    """Another place where the same content is stored."""

    document: Document
    version: DocumentVersion
    device: Device


@dataclass(frozen=True, slots=True)
class UploadResult:
    """The created version, its document and the other places of its content."""

    document: Document
    version: DocumentVersion
    duplicates: tuple[DuplicateLocation, ...]


class _LimitedStream:
    """Turns the chunks of an upload into ``read(size)`` and enforces the limit."""

    def __init__(self, chunks: Iterator[bytes], max_bytes: int) -> None:
        self._chunks = chunks
        self._max_bytes = max_bytes
        self._buffer = b""
        self._total = 0

    def _fill(self) -> bool:
        for chunk in self._chunks:
            if chunk:
                self._total += len(chunk)
                if self._total > self._max_bytes:
                    raise UploadTooLargeError(self._max_bytes)
                self._buffer += chunk
                return True
        return False

    def read(self, size: int = -1, /) -> bytes:
        if size < 0:
            while self._fill():
                pass
        while (size < 0 or len(self._buffer) < size) and self._fill():
            pass
        if size < 0:
            data, self._buffer = self._buffer, b""
        else:
            data, self._buffer = self._buffer[:size], self._buffer[size:]
        return data


def _remove_control_characters(value: str) -> str:
    return "".join(ch for ch in value if unicodedata.category(ch) not in _REMOVED_CATEGORIES)


def clean_filename(name: str | None) -> str:
    """Make an uploaded file name safe to store and show.

    Removes every path part (up to the last ``/`` or ``\\``), control and
    format characters and surrounding white space, and shortens the name to
    the field length, keeping a short extension. An empty result, ``.`` and
    ``..`` become :data:`FALLBACK_FILENAME`.
    """
    value = name or ""
    value = re.split(r"[/\\]", value)[-1]
    value = _remove_control_characters(value).strip()
    if value in {"", ".", ".."}:
        return FALLBACK_FILENAME
    if len(value) > FILENAME_MAX_LENGTH:
        stem, dot, extension = value.rpartition(".")
        if dot and stem and len(extension) <= _MAX_KEPT_EXTENSION:
            keep = FILENAME_MAX_LENGTH - len(extension) - 1
            value = f"{stem[:keep].rstrip()}.{extension}"
        else:
            value = value[:FILENAME_MAX_LENGTH].rstrip()
    return value


def clean_title(title: str | None, fallback: str) -> str:
    """Clean a title: control characters out, white space collapsed, field length.

    Slashes stay; a title like ``S7-1200 / ET 200SP`` is no path. An empty
    title becomes ``fallback`` (the cleaned file name).
    """
    # Line breaks and tabs become spaces first, the other controls go.
    spaced = " ".join((title or "").split())
    value = " ".join(_remove_control_characters(spaced).split())
    if not value:
        value = fallback
    return value[:TITLE_MAX_LENGTH].rstrip() or FALLBACK_FILENAME


def clean_content_type(content_type: str | None) -> str:
    """Return ``type/subtype`` in lower case, without parameters, or the fallback."""
    value = (content_type or "").split(";", 1)[0].strip().lower()
    if len(value) > CONTENT_TYPE_MAX_LENGTH or not _CONTENT_TYPE_RE.fullmatch(value):
        return FALLBACK_CONTENT_TYPE
    return value


def _check_declared_size(upload: Upload) -> int:
    max_bytes: int = settings.TWOX_UPLOAD_MAX_BYTES
    if upload.size is not None and upload.size > max_bytes:
        raise UploadTooLargeError(max_bytes)
    return max_bytes


def _store(upload: Upload, max_bytes: int) -> StoredBlob:
    stream = _LimitedStream(upload.chunks(), max_bytes)
    return get_blob_storage().store_blob(stream)


def _create_version(
    document: Document, number: int, blob: StoredBlob, upload: Upload, user: User | None
) -> DocumentVersion:
    version = DocumentVersion(
        document=document,
        number=number,
        blob_key=blob.key,
        sha256=blob.sha256,
        size=blob.size,
        content_type=clean_content_type(upload.content_type),
        original_filename=clean_filename(upload.name),
        uploaded_by=user,
    )
    version.full_clean()
    version.save()
    return version


def _duplicates(version: DocumentVersion) -> tuple[DuplicateLocation, ...]:
    others = (
        DocumentVersion.objects.filter(sha256=version.sha256)
        .exclude(pk=version.pk)
        .select_related("document__device")
        .order_by("pk")
    )
    return tuple(
        DuplicateLocation(document=other.document, version=other, device=other.document.device)
        for other in others
    )


def _request_ingest(version: DocumentVersion, user: User | None) -> None:
    """Hand the committed version to the ingestion; any error is logged only."""
    # Imported here: the ingestion builds on the files app, not the other way round.
    from twox.ingest.services import request_ingest

    try:
        request_ingest(version, user)
    except Exception:
        logger.exception("files: the ingestion of version %s could not be requested", version.pk)


def _ingest_after_commit(version: DocumentVersion, user: User | None) -> None:
    """Request the ingestion of a new ``document`` version once the upload is committed."""
    if version.document.kind == DocumentKind.DOCUMENT:
        transaction.on_commit(partial(_request_ingest, version, user))


def create_document(
    device: Device,
    upload: Upload,
    title: str | None,
    kind: DocumentKind | str,
    user: User | None,
) -> UploadResult:
    """Create a document of the device with the upload as version 1.

    Raises :class:`ConfigurationNotAcceptedError`, :class:`UploadTooLargeError`
    or ``ValueError`` (unknown kind); nothing is stored then.
    """
    document_kind = DocumentKind(kind)
    if document_kind is not DocumentKind.DOCUMENT:
        raise ConfigurationNotAcceptedError
    max_bytes = _check_declared_size(upload)
    filename = clean_filename(upload.name)

    with transaction.atomic():
        blob = _store(upload, max_bytes)
        document = Document(
            device=device,
            title=clean_title(title, fallback=filename),
            kind=document_kind,
            created_by=user,
        )
        document.full_clean()
        document.save()
        version = _create_version(document, 1, blob, upload, user)
        _ingest_after_commit(version, user)
        return UploadResult(document=document, version=version, duplicates=_duplicates(version))


def add_version(document: Document, upload: Upload, user: User | None) -> UploadResult:
    """Add the upload as the next version of the document.

    The document row is locked while the number is chosen, so concurrent
    uploads get consecutive numbers. Raises :class:`DuplicateVersionError`
    when the content equals the newest version, and the errors of
    :func:`create_document`.
    """
    if document.kind != DocumentKind.DOCUMENT:
        raise ConfigurationNotAcceptedError
    max_bytes = _check_declared_size(upload)

    with transaction.atomic():
        # Written before the lock: a long upload must not block other writers.
        blob = _store(upload, max_bytes)
        locked = Document.objects.select_for_update().get(pk=document.pk)
        newest = locked.versions.order_by("-number").first()
        if newest is not None and newest.sha256 == blob.sha256:
            raise DuplicateVersionError(newest)
        number = 1 if newest is None else newest.number + 1
        version = _create_version(locked, number, blob, upload, user)
        _ingest_after_commit(version, user)
        return UploadResult(document=locked, version=version, duplicates=_duplicates(version))
