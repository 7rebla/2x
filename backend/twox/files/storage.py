"""Blob storage for uploaded files: an interface and its file system implementation.

Every blob is content-addressed and immutable. Its key is derived from the
SHA-256 of its bytes (``sha256/ab/cd/<sha256>``), so the same content is
stored once, and a stored name never depends on device or document names.

Writes go to a temporary file below ``<root>/tmp/`` first, in the same file
system as the blobs. Checksum and size are computed block by block while
writing. Only the complete file is then linked under its key with
``os.link``, which never replaces an existing file. A failed or aborted write
removes the temporary file; a half-written file never appears under a key.

The rest of the code uses :func:`get_blob_storage` and the
:class:`BlobStorage` protocol only, so an S3-compatible implementation can be
added later without changes elsewhere. There are no public URLs and, in M1,
no way to delete a blob.
"""

import contextlib
import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Protocol

from django.conf import settings

#: Block size for reading the incoming stream (1 MiB).
CHUNK_SIZE = 1024 * 1024

#: Folder below the root for files that are still being written.
TMP_DIR_NAME = "tmp"

_KEY_PATTERN = re.compile(r"sha256/([0-9a-f]{2})/([0-9a-f]{2})/([0-9a-f]{64})")


class BlobStorageError(Exception):
    """Base class of all errors raised by a blob storage."""


class InvalidBlobKeyError(BlobStorageError, ValueError):
    """The key does not have the form ``sha256/ab/cd/<sha256>``."""


class BlobNotFoundError(BlobStorageError, LookupError):
    """No blob is stored under a valid key."""


class BlobConflictError(BlobStorageError):
    """A file already stored under the key does not match the new content."""


@dataclass(frozen=True, slots=True)
class StoredBlob:
    """Result of storing a blob."""

    key: str
    sha256: str
    size: int


class ReadableStream(Protocol):
    """Anything with a binary ``read(size)``, e.g. an open file or an upload."""

    def read(self, size: int = -1, /) -> bytes: ...


class BlobStorage(Protocol):
    """Interface of every blob storage (file system now, S3 later)."""

    def store_blob(self, stream: ReadableStream) -> StoredBlob:
        """Read the stream to its end and store its bytes under their key."""
        ...

    def open_blob(self, key: str) -> IO[bytes]:
        """Open a stored blob for reading; the caller closes it."""
        ...

    def blob_exists(self, key: str) -> bool:
        """Tell whether a blob is stored under the key."""
        ...


def key_for_sha256(sha256: str) -> str:
    """Build the storage key for a lower-case hexadecimal SHA-256."""
    return validate_key(f"sha256/{sha256[0:2]}/{sha256[2:4]}/{sha256}")


def validate_key(key: object) -> str:
    """Return the key unchanged if it is valid, else raise InvalidBlobKeyError.

    The two folder levels must repeat the first four characters of the
    checksum, so every valid key names exactly one place below the root.
    """
    if not isinstance(key, str):
        raise InvalidBlobKeyError("blob key must be a string")
    match = _KEY_PATTERN.fullmatch(key)
    if match is None:
        raise InvalidBlobKeyError(f"invalid blob key: {key!r}")
    first, second, digest = match.groups()
    if digest[0:2] != first or digest[2:4] != second:
        raise InvalidBlobKeyError(f"invalid blob key: {key!r}")
    return key


def _fsync_directory(path: Path) -> None:
    """Make a new directory entry durable (no-op where directories cannot be opened)."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


class FileSystemBlobStorage:
    """Blob storage in a local directory (in operation: the Docker volume ``media-data``)."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / validate_key(key)

    def store_blob(self, stream: ReadableStream) -> StoredBlob:
        tmp_dir = self.root / TMP_DIR_NAME
        tmp_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=tmp_dir, prefix="upload-", suffix=".part")
        tmp_path = Path(tmp_name)
        try:
            digest = hashlib.sha256()
            size = 0
            with os.fdopen(fd, "wb") as out:
                while chunk := stream.read(CHUNK_SIZE):
                    digest.update(chunk)
                    size += len(chunk)
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            # Blobs are immutable: read-only for owner and group.
            tmp_path.chmod(0o440)

            sha256 = digest.hexdigest()
            key = key_for_sha256(sha256)
            target = self.root / key
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                # Atomic and never replaces: of two concurrent writers of the
                # same content exactly one creates the entry.
                os.link(tmp_path, target)
            except FileExistsError:
                existing_size = target.stat().st_size
                if existing_size != size:
                    raise BlobConflictError(
                        f"stored blob {key} has {existing_size} bytes, expected {size}"
                    ) from None
            else:
                _fsync_directory(target.parent)
            return StoredBlob(key=key, sha256=sha256, size=size)
        finally:
            # The temporary name goes in every case: after a successful link
            # the blob lives on under its key, after an error nothing is left.
            with contextlib.suppress(FileNotFoundError):
                tmp_path.unlink()

    def open_blob(self, key: str) -> IO[bytes]:
        path = self._path(key)
        try:
            return path.open("rb")
        except FileNotFoundError:
            raise BlobNotFoundError(f"no blob stored under {key}") from None

    def blob_exists(self, key: str) -> bool:
        return self._path(key).is_file()


def get_blob_storage() -> BlobStorage:
    """Return the configured blob storage (the file system below TWOX_MEDIA_ROOT)."""
    return FileSystemBlobStorage(Path(settings.TWOX_MEDIA_ROOT))
