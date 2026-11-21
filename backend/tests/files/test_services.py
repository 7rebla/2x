"""Document and version services (twox.files.services) and their models."""

import hashlib
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.models import ProtectedError
from pytest_django.fixtures import Settings

from twox.accounts.models import User
from twox.assets.models import Area, Device, Plant, Site
from twox.files.models import Document, DocumentKind, DocumentVersion, VersionImmutableError
from twox.files.services import (
    FALLBACK_CONTENT_TYPE,
    FALLBACK_FILENAME,
    ConfigurationNotAcceptedError,
    DuplicateVersionError,
    UploadError,
    UploadTooLargeError,
    add_version,
    clean_content_type,
    clean_filename,
    clean_title,
    create_document,
)
from twox.files.storage import key_for_sha256

pytestmark = pytest.mark.django_db


@pytest.fixture
def media_root(tmp_path: Path, settings: Settings) -> Path:
    """A fresh storage root per test; nothing touches the media volume."""
    root = tmp_path / "media"
    root.mkdir()
    settings.TWOX_MEDIA_ROOT = root
    return root


def make_device(key: str = "dps-plc") -> Device:
    site, _ = Site.objects.get_or_create(name="Test site")
    area, _ = Area.objects.get_or_create(site=site, name="Production line")
    plant, _ = Plant.objects.get_or_create(area=area, key="aps-dps", name="Goods in and out")
    return Device.objects.create(plant=plant, key=key, name=f"Device {key}")


def upload(
    content: bytes, name: str = "manual.pdf", content_type: str = "application/pdf"
) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type=content_type)


def stored_files(root: Path) -> list[Path]:
    return sorted(p for p in (root / "sha256").rglob("*") if p.is_file())


def leftover_tmp_files(root: Path) -> list[Path]:
    tmp_dir = root / "tmp"
    return sorted(tmp_dir.iterdir()) if tmp_dir.exists() else []


class RawUpload:
    """An upload without Django's own name handling; size and chunks as given.

    Used to pass raw file names and to declare a size that does not match.
    """

    def __init__(
        self, chunks: list[bytes], declared_size: int | None, name: str | None = "big.bin"
    ) -> None:
        self._chunks = chunks
        self.name: str | None = name
        self.size: int | None = declared_size
        self.content_type: str | None = None

    def chunks(self, chunk_size: int | None = None) -> Iterator[bytes]:
        yield from self._chunks


# --- versions --------------------------------------------------------------


def test_two_versions_get_numbers_one_and_two(media_root: Path) -> None:
    user = User.objects.create_user("uploader")
    device = make_device()

    first = create_document(device, upload(b"edition 1"), "Manual", DocumentKind.DOCUMENT, user)
    second = add_version(first.document, upload(b"edition 2", name="manual-2.pdf"), None)

    assert first.version.number == 1
    assert second.version.number == 2
    assert second.document.pk == first.document.pk
    assert list(first.document.versions.values_list("number", flat=True)) == [1, 2]
    assert first.duplicates == ()
    assert second.duplicates == ()

    document = Document.objects.get(pk=first.document.pk)
    assert document.device == device
    assert document.title == "Manual"
    assert document.kind == DocumentKind.DOCUMENT
    assert document.created_by == user
    assert document.created_at is not None

    version = DocumentVersion.objects.get(pk=second.version.pk)
    assert version.sha256 == hashlib.sha256(b"edition 2").hexdigest()
    assert version.blob_key == key_for_sha256(version.sha256)
    assert version.size == len(b"edition 2")
    assert version.content_type == "application/pdf"
    assert version.original_filename == "manual-2.pdf"
    assert version.uploaded_by is None
    assert version.created_at is not None
    assert str(version) == "Manual v2"


def test_stored_content_matches_upload(media_root: Path) -> None:
    content = bytes(range(256)) * 1000
    result = create_document(make_device(), upload(content), "Manual", "document", None)

    stored = media_root / result.version.blob_key
    assert stored.read_bytes() == content
    assert leftover_tmp_files(media_root) == []


def test_same_bytes_as_newest_version_are_rejected(media_root: Path) -> None:
    result = create_document(make_device(), upload(b"same"), "Manual", DocumentKind.DOCUMENT, None)

    with pytest.raises(DuplicateVersionError) as excinfo:
        add_version(result.document, upload(b"same", name="again.pdf"), None)

    assert excinfo.value.version == result.version
    assert "1" in str(excinfo.value)
    assert result.document.versions.count() == 1


def test_same_bytes_as_an_older_version_are_accepted(media_root: Path) -> None:
    result = create_document(make_device(), upload(b"A"), "Manual", DocumentKind.DOCUMENT, None)
    add_version(result.document, upload(b"B"), None)

    third = add_version(result.document, upload(b"A"), None)

    assert third.version.number == 3
    assert [d.version for d in third.duplicates] == [result.version]


def test_same_bytes_on_another_device_are_created_and_reported(media_root: Path) -> None:
    first_device = make_device("dps-plc")
    second_device = make_device("hbw-plc")
    first = create_document(first_device, upload(b"shared"), "Manual", "document", None)

    second = create_document(second_device, upload(b"shared"), "Manual", "document", None)

    assert second.version.number == 1
    assert second.document.device == second_device
    assert len(second.duplicates) == 1
    location = second.duplicates[0]
    assert location.document == first.document
    assert location.version == first.version
    assert location.device == first_device
    assert second.version.blob_key == first.version.blob_key
    assert stored_files(media_root) == [media_root / first.version.blob_key]


# --- immutability and protection ----------------------------------------


def test_version_is_immutable(media_root: Path) -> None:
    result = create_document(make_device(), upload(b"x"), "Manual", "document", None)
    version = DocumentVersion.objects.get(pk=result.version.pk)

    version.original_filename = "changed.pdf"
    with pytest.raises(VersionImmutableError):
        version.save()
    with pytest.raises(VersionImmutableError):
        version.save(update_fields=["original_filename"])

    assert DocumentVersion.objects.get(pk=version.pk).original_filename == "manual.pdf"


def test_protect_prevents_deleting_a_device_with_files(media_root: Path) -> None:
    device = make_device()
    result = create_document(device, upload(b"x"), "Manual", "document", None)

    with pytest.raises(ProtectedError):
        device.delete()
    with pytest.raises(ProtectedError):
        result.document.delete()

    assert Device.objects.filter(pk=device.pk).exists()
    assert DocumentVersion.objects.filter(pk=result.version.pk).exists()


def test_protect_prevents_deleting_a_user_with_uploads(media_root: Path) -> None:
    user = User.objects.create_user("uploader")
    create_document(make_device(), upload(b"x"), "Manual", "document", user)

    with pytest.raises(ProtectedError):
        user.delete()


# --- limits and rejections -----------------------------------------------


def test_too_large_file_is_rejected(media_root: Path, settings: Settings) -> None:
    settings.TWOX_UPLOAD_MAX_BYTES = 10
    device = make_device()

    with pytest.raises(UploadTooLargeError) as excinfo:
        create_document(device, upload(b"x" * 11), "Manual", "document", None)

    assert excinfo.value.max_bytes == 10
    assert isinstance(excinfo.value, UploadError)
    assert not Document.objects.exists()
    assert not (media_root / "sha256").exists()


def test_file_at_the_limit_is_accepted(media_root: Path, settings: Settings) -> None:
    settings.TWOX_UPLOAD_MAX_BYTES = 10

    result = create_document(make_device(), upload(b"x" * 10), "Manual", "document", None)

    assert result.version.size == 10


def test_too_large_file_with_wrong_declared_size_is_rejected_while_reading(
    media_root: Path, settings: Settings
) -> None:
    settings.TWOX_UPLOAD_MAX_BYTES = 10
    lying = RawUpload([b"x" * 6, b"x" * 6], declared_size=5)
    document = create_document(make_device(), upload(b"v1"), "Manual", "document", None).document

    with pytest.raises(UploadTooLargeError):
        add_version(document, lying, None)
    with pytest.raises(UploadTooLargeError):
        create_document(make_device("hbw-plc"), lying, "Big", "document", None)

    assert Document.objects.count() == 1
    assert DocumentVersion.objects.count() == 1
    assert len(stored_files(media_root)) == 1
    assert leftover_tmp_files(media_root) == []


def test_configuration_is_rejected(media_root: Path) -> None:
    device = make_device()

    with pytest.raises(ConfigurationNotAcceptedError):
        create_document(device, upload(b"user=admin"), "Config", DocumentKind.CONFIGURATION, None)
    with pytest.raises(ConfigurationNotAcceptedError):
        create_document(device, upload(b"user=admin"), "Config", "configuration", None)

    assert not Document.objects.exists()
    assert not (media_root / "sha256").exists()
    assert not (media_root / "tmp").exists()


def test_configuration_document_takes_no_new_version(media_root: Path) -> None:
    # No service creates one in M1; a row made otherwise is still protected.
    document = Document.objects.create(
        device=make_device(), title="Config", kind=DocumentKind.CONFIGURATION
    )

    with pytest.raises(ConfigurationNotAcceptedError):
        add_version(document, upload(b"user=admin"), None)

    assert not document.versions.exists()
    assert not (media_root / "sha256").exists()


def test_unknown_kind_is_rejected(media_root: Path) -> None:
    with pytest.raises(ValueError, match="kind"):
        create_document(make_device(), upload(b"x"), "Manual", "kind-unknown", None)

    assert not Document.objects.exists()


# --- cleaning of names -----------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd", "passwd"),
        ("C:\\x\\y.pdf", "y.pdf"),
        ("dir/sub\\mixed/name.txt", "name.txt"),
        ("ma\x00nu\x1fal\x7f.pdf", "manual.pdf"),
        ("line\nbreak\r.pdf", "linebreak.pdf"),
        ("evil\u202efdp.exe", "evilfdp.exe"),
        ("  spaced.pdf  ", "spaced.pdf"),
        ("", FALLBACK_FILENAME),
        (None, FALLBACK_FILENAME),
        ("../", FALLBACK_FILENAME),
        ("..", FALLBACK_FILENAME),
        ("\x00\x01", FALLBACK_FILENAME),
        ("Handbuch Größe Ü.pdf", "Handbuch Größe Ü.pdf"),
    ],
)
def test_filename_is_cleaned(raw: str | None, expected: str) -> None:
    assert clean_filename(raw) == expected


def test_long_filename_is_shortened_and_keeps_its_extension() -> None:
    cleaned = clean_filename("a" * 300 + ".pdf")

    assert len(cleaned) == 255
    assert cleaned.endswith("a.pdf")


def test_long_filename_without_extension_is_shortened() -> None:
    assert clean_filename("b" * 300) == "b" * 255


def test_dirty_filename_is_stored_cleaned(media_root: Path) -> None:
    name = "C:\\x\\../../" + "\x07" + "x" * 300 + ".pdf"
    raw = RawUpload([b"x"], declared_size=None, name=name)

    result = create_document(make_device(), raw, "", "document", None)

    version = DocumentVersion.objects.get(pk=result.version.pk)
    assert len(version.original_filename) == 255
    assert "/" not in version.original_filename
    assert "\x07" not in version.original_filename
    assert version.original_filename.endswith(".pdf")
    # An empty title falls back to the cleaned file name, shortened to 200.
    assert result.document.title == version.original_filename[:200]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Manual S7-1200 / ET 200SP", "Manual S7-1200 / ET 200SP"),
        ("Two\nlines\tand\x00 nul", "Two lines and nul"),
        ("  padded  ", "padded"),
        ("t" * 250, "t" * 200),
        ("", "fallback.pdf"),
        (None, "fallback.pdf"),
        ("\x00\u200b", "fallback.pdf"),
    ],
)
def test_title_is_cleaned(raw: str | None, expected: str) -> None:
    assert clean_title(raw, fallback="fallback.pdf") == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("application/pdf", "application/pdf"),
        ("Text/Plain; charset=utf-8", "text/plain"),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", None),
        ("", FALLBACK_CONTENT_TYPE),
        (None, FALLBACK_CONTENT_TYPE),
        ("pdf", FALLBACK_CONTENT_TYPE),
        ("text/plain\r\nX-Evil: 1", FALLBACK_CONTENT_TYPE),
        ("a/" + "b" * 100, FALLBACK_CONTENT_TYPE),
    ],
)
def test_content_type_is_checked(raw: str | None, expected: str | None) -> None:
    assert clean_content_type(raw) == (raw if expected is None else expected)


def test_model_rejects_invalid_content_type_and_checksum(media_root: Path) -> None:
    result = create_document(make_device(), upload(b"x"), "Manual", "document", None)
    version = DocumentVersion(
        document=result.document,
        number=2,
        blob_key=result.version.blob_key,
        sha256="NOT-HEX",
        size=1,
        content_type="pdf",
        original_filename="x.pdf",
    )

    with pytest.raises(ValidationError) as excinfo:
        version.full_clean()

    assert set(excinfo.value.message_dict) == {"sha256", "content_type"}


def test_verbose_names_are_set() -> None:
    assert str(Document._meta.verbose_name) == "document"
    assert str(DocumentVersion._meta.verbose_name) == "document version"
    assert str(DocumentVersion._meta.verbose_name_plural) == "document versions"


# --- concurrency -----------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_concurrent_versions_get_consecutive_numbers(media_root: Path) -> None:
    document = create_document(make_device(), upload(b"v1"), "Manual", "document", None).document
    workers = 4
    barrier = threading.Barrier(workers)
    numbers: list[int] = []
    errors: list[BaseException] = []

    def run(index: int) -> None:
        try:
            barrier.wait()
            result = add_version(document, upload(f"content {index}".encode()), None)
            numbers.append(result.version.number)
        except BaseException as error:  # reported below
            errors.append(error)
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(i,)) for i in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert sorted(numbers) == [2, 3, 4, 5]
