"""The format list of the ingestion (twox.ingest.formats, work order 049, E-57)."""

import io
import zipfile
from typing import NoReturn

import pytest

from twox.ingest import formats
from twox.ingest.formats import (
    EXTENSIONS,
    OOXML_CONTENT_TYPES_ENTRY,
    IngestFormat,
    check_format,
    extension_of,
)

PDF = b"%PDF-1.7\n%stand-in, never converted\n"
PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"
TIFF_LITTLE = b"II*\x00\x08\x00\x00\x00"
TIFF_BIG = b"MM\x00*\x00\x00\x00\x08"
BMP = b"BM\x3a\x00\x00\x00\x00\x00"
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 "
MARKDOWN = "# Wartung\n\nÖlwechsel alle 500 Stunden.\n".encode()


def ooxml_package(main_part: str = "word/document.xml") -> bytes:
    """A minimal Office Open XML package: a ZIP with ``[Content_Types].xml``."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(OOXML_CONTENT_TYPES_ENTRY, '<?xml version="1.0"?><Types/>')
        archive.writestr(main_part, "<document/>")
    return buffer.getvalue()


def plain_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("settings.conf", "option=1\n")
    return buffer.getvalue()


def check(filename: str, content: bytes) -> formats.FormatCheck:
    return check_format(filename, io.BytesIO(content))


# --- Supported ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "content", "expected"),
    [
        ("manual.pdf", PDF, IngestFormat.PDF),
        ("MANUAL.PDF", PDF, IngestFormat.PDF),
        ("manual.docx", ooxml_package(), IngestFormat.DOCX),
        ("parts.xlsx", ooxml_package("xl/workbook.xml"), IngestFormat.XLSX),
        ("slides.pptx", ooxml_package("ppt/presentation.xml"), IngestFormat.PPTX),
        ("backup.md", MARKDOWN, IngestFormat.MARKDOWN),
        ("empty.md", b"", IngestFormat.MARKDOWN),
        ("plate.png", PNG, IngestFormat.PNG),
        ("plate.jpg", JPEG, IngestFormat.JPEG),
        ("plate.jpeg", JPEG, IngestFormat.JPEG),
        ("scan.tif", TIFF_LITTLE, IngestFormat.TIFF),
        ("scan.tiff", TIFF_BIG, IngestFormat.TIFF),
        ("scan.bmp", BMP, IngestFormat.BMP),
        ("photo.webp", WEBP, IngestFormat.WEBP),
        ("C:\\Users\\x\\manual.pdf", PDF, IngestFormat.PDF),
        ("../dir/manual.pdf", PDF, IngestFormat.PDF),
    ],
)
def test_supported_format_needs_matching_name_and_content(
    filename: str, content: bytes, expected: IngestFormat
) -> None:
    result = check(filename, content)

    assert result.format is expected
    assert result.supported
    assert result.reason == ""


def test_every_format_of_e57_has_an_extension() -> None:
    assert set(EXTENSIONS.values()) == set(IngestFormat)


def test_markdown_is_checked_as_a_whole(monkeypatch: pytest.MonkeyPatch) -> None:
    # A character split across two reads is still valid UTF-8; a NUL in a
    # later read is still found.
    monkeypatch.setattr(formats, "READ_CHUNK_BYTES", 3)
    text = "Ölstand prüfen".encode()

    assert check("check.md", text).format is IngestFormat.MARKDOWN
    assert not check("check.md", text + b"\x00").supported
    assert not check("check.md", text + b"\xc3").supported


# --- Skipped ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("notes.txt", b"plain text"),
        ("export.json", b'{"user": "admin"}'),
        ("project.xml", b"<?xml version='1.0'?><project/>"),
        ("plant.yaml", b"key: value\n"),
        ("plant.yml", b"key: value\n"),
        ("router.conf", b"option=1\n"),
        ("settings.cfg", b"[section]\n"),
        ("settings.ini", b"[section]\n"),
        ("readme.rst", b"Title\n=====\n"),
        ("page.html", b"<html><body>x</body></html>"),
        ("page.htm", b"<html></html>"),
        ("archive.zip", plain_zip()),
        ("manual.doc", b"\xd0\xcf\x11\xe0"),
        ("backup.markdown", MARKDOWN),
    ],
)
def test_other_extensions_are_skipped(filename: str, content: bytes) -> None:
    result = check(filename, content)

    assert result.format is None
    assert not result.supported
    assert result.reason == f"files with the extension {extension_of(filename)} are not ingested"


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        pytest.param("manual.pdf", b"option=1\npassword=x\n", id="text-as-pdf"),
        pytest.param("manual.pdf", b" %PDF-1.7", id="pdf-signature-not-at-start"),
        pytest.param("manual.pdf", PNG, id="png-as-pdf"),
        pytest.param("manual.docx", plain_zip(), id="zip-without-content-types"),
        pytest.param("manual.docx", PDF, id="pdf-as-docx"),
        pytest.param("parts.xlsx", b"PK\x03\x04 broken archive", id="broken-zip"),
        pytest.param("slides.pptx", b"", id="empty-pptx"),
        pytest.param("backup.md", b"# x\x00", id="nul-in-markdown"),
        pytest.param("backup.md", b"\xff\xfe# x", id="not-utf8"),
        pytest.param("plate.png", JPEG, id="jpeg-as-png"),
        pytest.param("plate.jpg", PNG, id="png-as-jpg"),
        pytest.param("scan.tif", b"II+\x00", id="bigtiff-or-other"),
        pytest.param("scan.bmp", b"MB", id="not-bmp"),
        pytest.param("photo.webp", b"RIFF\x24\x00\x00\x00WAVEfmt ", id="wave-as-webp"),
    ],
)
def test_content_must_match_the_extension(filename: str, content: bytes) -> None:
    result = check(filename, content)

    assert result.format is None
    assert result.reason == f"the content does not match the extension {extension_of(filename)}"


@pytest.mark.parametrize("filename", ["README", "manual.", "", ".hidden"])
def test_name_without_extension_is_skipped(filename: str) -> None:
    result = check(filename, PDF)

    assert result.format is None
    assert result.reason == "the file name has no extension"


def test_reason_never_names_the_file() -> None:
    result = check("plant-7-secret-router.conf", b"x")

    assert "plant" not in result.reason
    assert "secret" not in result.reason


def test_unusual_extension_is_not_repeated_in_the_reason() -> None:
    result = check("x.<script>", b"x")

    assert result.reason == "files with this extension are not ingested"


def test_ooxml_check_reads_the_directory_only(monkeypatch: pytest.MonkeyPatch) -> None:
    # No entry is unpacked: a package with a huge compressed entry is cheap.
    package = ooxml_package()

    def no_unpacking(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("an entry of the archive was opened")

    monkeypatch.setattr(zipfile.ZipFile, "open", no_unpacking)
    monkeypatch.setattr(zipfile.ZipFile, "read", no_unpacking)

    assert check("manual.docx", package).format is IngestFormat.DOCX


@pytest.mark.parametrize(
    ("filename", "extension"),
    [
        ("manual.PDF", ".pdf"),
        ("C:\\x\\plan.Docx", ".docx"),
        ("dir/sub/archive.tar.gz", ".gz"),
        ("noextension", ""),
    ],
)
def test_extension_of(filename: str, extension: str) -> None:
    assert extension_of(filename) == extension
