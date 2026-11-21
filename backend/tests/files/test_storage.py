"""Content-addressed blob storage on the file system (twox.files.storage)."""

import hashlib
import io
import os
import threading
from pathlib import Path

import pytest
from pytest_django.fixtures import Settings

from twox.files.storage import (
    CHUNK_SIZE,
    TMP_DIR_NAME,
    BlobConflictError,
    BlobNotFoundError,
    BlobStorage,
    FileSystemBlobStorage,
    InvalidBlobKeyError,
    StoredBlob,
    get_blob_storage,
    key_for_sha256,
)

SHA256_2X = hashlib.sha256(b"2x").hexdigest()
KEY_2X = f"sha256/{SHA256_2X[0:2]}/{SHA256_2X[2:4]}/{SHA256_2X}"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A fresh storage root per test; no volume needed."""
    path = tmp_path / "media"
    path.mkdir()
    return path


@pytest.fixture
def storage(root: Path) -> FileSystemBlobStorage:
    return FileSystemBlobStorage(root)


def stored_files(root: Path) -> list[Path]:
    """All files below ``sha256/``."""
    return sorted(p for p in (root / "sha256").rglob("*") if p.is_file())


def tmp_files(root: Path) -> list[Path]:
    tmp_dir = root / TMP_DIR_NAME
    return sorted(tmp_dir.iterdir()) if tmp_dir.exists() else []


class RecordingStream:
    """Wraps a byte stream and records the size of every read call."""

    def __init__(self, data: bytes) -> None:
        self._inner = io.BytesIO(data)
        self.read_sizes: list[int] = []

    def read(self, size: int = -1, /) -> bytes:
        self.read_sizes.append(size)
        return self._inner.read(size)


class FailingStream:
    """Delivers some blocks, then fails like a dropped upload."""

    def __init__(self, good_blocks: int) -> None:
        self._good_blocks = good_blocks

    def read(self, size: int = -1, /) -> bytes:
        if self._good_blocks == 0:
            raise ConnectionResetError("client went away")
        self._good_blocks -= 1
        return b"a" * size


def test_store_returns_key_checksum_and_size(storage: FileSystemBlobStorage, root: Path) -> None:
    blob = storage.store_blob(io.BytesIO(b"2x"))

    assert blob == StoredBlob(key=KEY_2X, sha256=SHA256_2X, size=2)
    assert (root / KEY_2X).read_bytes() == b"2x"
    assert tmp_files(root) == []


def test_checksum_matches_hashlib(storage: FileSystemBlobStorage) -> None:
    data = os.urandom(3 * CHUNK_SIZE + 17)

    blob = storage.store_blob(io.BytesIO(data))

    assert blob.sha256 == hashlib.sha256(data).hexdigest()
    assert blob.size == len(data)
    with storage.open_blob(blob.key) as handle:
        assert handle.read() == data


def test_empty_stream_is_stored(storage: FileSystemBlobStorage) -> None:
    blob = storage.store_blob(io.BytesIO(b""))

    assert blob.sha256 == hashlib.sha256(b"").hexdigest()
    assert blob.size == 0
    assert storage.blob_exists(blob.key)


def test_same_bytes_give_same_key_and_are_written_once(
    storage: FileSystemBlobStorage, root: Path
) -> None:
    first = storage.store_blob(io.BytesIO(b"same content"))
    before = (root / first.key).stat()

    second = storage.store_blob(io.BytesIO(b"same content"))

    assert second == first
    assert stored_files(root) == [root / first.key]
    after = (root / first.key).stat()
    # Same file, untouched: neither replaced nor rewritten.
    assert (after.st_ino, after.st_mtime_ns, after.st_nlink) == (
        before.st_ino,
        before.st_mtime_ns,
        before.st_nlink,
    )
    assert tmp_files(root) == []


def test_different_bytes_give_different_keys(storage: FileSystemBlobStorage, root: Path) -> None:
    first = storage.store_blob(io.BytesIO(b"one"))
    second = storage.store_blob(io.BytesIO(b"two"))

    assert first.key != second.key
    assert len(stored_files(root)) == 2


def test_stored_blob_is_read_only(storage: FileSystemBlobStorage, root: Path) -> None:
    blob = storage.store_blob(io.BytesIO(b"immutable"))

    assert (root / blob.key).stat().st_mode & 0o777 == 0o440


def test_large_file_is_processed_in_blocks(storage: FileSystemBlobStorage, root: Path) -> None:
    data = os.urandom(20 * 1000 * 1000)
    stream = RecordingStream(data)

    blob = storage.store_blob(stream)

    assert blob.size == len(data)
    assert blob.sha256 == hashlib.sha256(data).hexdigest()
    # Never "read everything": every call asks for one block at most.
    assert stream.read_sizes
    assert all(0 < size <= CHUNK_SIZE for size in stream.read_sizes)
    assert len(stream.read_sizes) >= len(data) // CHUNK_SIZE
    assert (root / blob.key).stat().st_size == len(data)


def test_concurrent_stores_of_same_content_give_one_file(
    storage: FileSystemBlobStorage, root: Path
) -> None:
    data = os.urandom(4 * CHUNK_SIZE + 5)
    workers = 4
    barrier = threading.Barrier(workers)
    results: list[StoredBlob] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def store() -> None:
        try:
            barrier.wait()
            blob = storage.store_blob(io.BytesIO(data))
        except BaseException as exc:
            with lock:
                errors.append(exc)
        else:
            with lock:
                results.append(blob)

    threads = [threading.Thread(target=store) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(results) == workers
    assert {blob.key for blob in results} == {key_for_sha256(hashlib.sha256(data).hexdigest())}
    key = results[0].key
    assert stored_files(root) == [root / key]
    assert (root / key).read_bytes() == data
    assert tmp_files(root) == []


def test_aborted_write_leaves_nothing_behind(storage: FileSystemBlobStorage, root: Path) -> None:
    with pytest.raises(ConnectionResetError):
        storage.store_blob(FailingStream(good_blocks=3))

    assert not (root / "sha256").exists() or stored_files(root) == []
    assert tmp_files(root) == []


def test_failure_while_linking_leaves_nothing_behind(
    storage: FileSystemBlobStorage, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_link(src: object, dst: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("twox.files.storage.os.link", broken_link)

    with pytest.raises(OSError, match="disk full"):
        storage.store_blob(io.BytesIO(b"never stored"))

    assert stored_files(root) == []
    assert tmp_files(root) == []


def test_existing_file_with_wrong_size_is_a_conflict(
    storage: FileSystemBlobStorage, root: Path
) -> None:
    target = root / KEY_2X
    target.parent.mkdir(parents=True)
    target.write_bytes(b"truncated or foreign content")

    with pytest.raises(BlobConflictError):
        storage.store_blob(io.BytesIO(b"2x"))

    assert target.read_bytes() == b"truncated or foreign content"
    assert tmp_files(root) == []


def test_stored_name_is_always_the_key(storage: FileSystemBlobStorage, root: Path) -> None:
    """No renaming à la get_available_name: the second store finds the same name."""
    storage.store_blob(io.BytesIO(b"2x"))
    storage.store_blob(io.BytesIO(b"2x"))

    assert [p.relative_to(root).as_posix() for p in stored_files(root)] == [KEY_2X]


@pytest.mark.parametrize(
    "key",
    [
        "../x",
        "x",
        "",
        "/etc/passwd",
        f"sha256/zz/{SHA256_2X[2:4]}/{SHA256_2X}",
        f"sha256/{SHA256_2X[0:2]}/{SHA256_2X[2:4]}/{SHA256_2X.upper()}",
        f"sha256/{SHA256_2X[0:2]}/{SHA256_2X[2:4]}/{SHA256_2X}/",
        f"sha256/{SHA256_2X[0:2]}/{SHA256_2X[2:4]}/{SHA256_2X}\n",
        f"sha256/{SHA256_2X[0:2]}/{SHA256_2X[2:4]}/../../{SHA256_2X}",
        f"/sha256/{SHA256_2X[0:2]}/{SHA256_2X[2:4]}/{SHA256_2X}",
        f"tmp/{SHA256_2X}",
        f"sha256/{SHA256_2X[0:2]}/{SHA256_2X[2:4]}/{SHA256_2X[:-1]}",
        # Valid form, but the folders do not repeat the checksum.
        f"sha256/00/00/{SHA256_2X}",
    ],
)
def test_invalid_keys_are_rejected(storage: FileSystemBlobStorage, key: str) -> None:
    with pytest.raises(InvalidBlobKeyError):
        storage.open_blob(key)
    with pytest.raises(InvalidBlobKeyError):
        storage.blob_exists(key)


def test_non_string_key_is_rejected(storage: FileSystemBlobStorage) -> None:
    with pytest.raises(InvalidBlobKeyError):
        storage.blob_exists(Path(KEY_2X))  # type: ignore[arg-type]


def test_unknown_valid_key(storage: FileSystemBlobStorage) -> None:
    assert storage.blob_exists(KEY_2X) is False
    with pytest.raises(BlobNotFoundError):
        storage.open_blob(KEY_2X)


def test_temporary_files_are_not_readable_through_the_interface(
    storage: FileSystemBlobStorage, root: Path
) -> None:
    (root / TMP_DIR_NAME).mkdir()
    (root / TMP_DIR_NAME / SHA256_2X).write_bytes(b"2x")

    with pytest.raises(InvalidBlobKeyError):
        storage.open_blob(f"{TMP_DIR_NAME}/{SHA256_2X}")


def test_get_blob_storage_uses_media_root(settings: Settings, tmp_path: Path) -> None:
    settings.TWOX_MEDIA_ROOT = tmp_path / "configured"

    storage: BlobStorage = get_blob_storage()
    blob = storage.store_blob(io.BytesIO(b"2x"))

    assert isinstance(storage, FileSystemBlobStorage)
    assert storage.root == tmp_path / "configured"
    assert blob.key == KEY_2X
    assert (tmp_path / "configured" / KEY_2X).read_bytes() == b"2x"
    assert storage.blob_exists(KEY_2X)
