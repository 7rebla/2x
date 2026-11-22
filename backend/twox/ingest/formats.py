"""Which uploaded files are ingested: a fixed list of formats, checked by name and content.

Ingested in M2 (E-57): PDF, DOCX, XLSX, PPTX, Markdown and the images PNG,
JPEG, TIFF, BMP and WEBP. Every other file is skipped visibly until M5, above
all text formats that may hold a configuration with access data (plain text,
JSON, XML, YAML, ``.conf``, ``.rst``), as well as HTML and ZIP archives
(guard rail 5).

A format counts only if both agree:

- the extension of the original file name (lower case) names it, and
- the content starts with its signature (PDF ``%PDF-``, the image
  signatures), is a ZIP archive with the entry ``[Content_Types].xml``
  (DOCX, XLSX, PPTX), or is UTF-8 text without NUL (Markdown).

The content type the browser declared is never used: it is whatever the
client claims.

Known limit: Markdown is recognised by its extension and a text check only,
and a PDF by its signature; a configuration uploaded as ``.md`` or wrapped in
a PDF is ingested. The format list does not replace the redaction of M5.

Document contents are data, not instructions: nothing here interprets them.
"""

import codecs
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import IO, Final

#: Bytes read per step when a whole file is checked (Markdown).
READ_CHUNK_BYTES: Final = 1024 * 1024
#: Bytes read from the start of a file for the signature checks.
HEAD_BYTES: Final = 16
#: The entry every Office Open XML package has (ECMA-376 part 2).
OOXML_CONTENT_TYPES_ENTRY: Final = "[Content_Types].xml"


class IngestFormat(StrEnum):
    """A format that is ingested in M2."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    MARKDOWN = "markdown"
    PNG = "png"
    JPEG = "jpeg"
    TIFF = "tiff"
    BMP = "bmp"
    WEBP = "webp"


#: The extensions of each format (lower case, with the dot).
EXTENSIONS: Final[dict[str, IngestFormat]] = {
    ".pdf": IngestFormat.PDF,
    ".docx": IngestFormat.DOCX,
    ".xlsx": IngestFormat.XLSX,
    ".pptx": IngestFormat.PPTX,
    ".md": IngestFormat.MARKDOWN,
    ".png": IngestFormat.PNG,
    ".jpg": IngestFormat.JPEG,
    ".jpeg": IngestFormat.JPEG,
    ".tif": IngestFormat.TIFF,
    ".tiff": IngestFormat.TIFF,
    ".bmp": IngestFormat.BMP,
    ".webp": IngestFormat.WEBP,
}

#: The ingested formats in one line, for messages and help texts.
SUPPORTED_FORMATS_TEXT: Final = (
    "PDF, DOCX, XLSX, PPTX, Markdown (.md) and images (PNG, JPEG, TIFF, BMP, WEBP)"
)

#: Office Open XML formats: a ZIP archive with ``[Content_Types].xml``.
OOXML_FORMATS: Final = frozenset({IngestFormat.DOCX, IngestFormat.XLSX, IngestFormat.PPTX})

#: An extension is named in a reason only in this short, plain form.
_SHOWN_EXTENSION_RE: Final = re.compile(r"\.[a-z0-9]{1,10}")

_PNG_SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"
_ZIP_SIGNATURE: Final = b"PK\x03\x04"


def _webp(head: bytes) -> bool:
    return head[:4] == b"RIFF" and head[8:12] == b"WEBP"


#: Signature checks on the first :data:`HEAD_BYTES` bytes.
_SIGNATURES: Final[dict[IngestFormat, Callable[[bytes], bool]]] = {
    IngestFormat.PDF: lambda head: head.startswith(b"%PDF-"),
    IngestFormat.PNG: lambda head: head.startswith(_PNG_SIGNATURE),
    IngestFormat.JPEG: lambda head: head.startswith(b"\xff\xd8\xff"),
    IngestFormat.TIFF: lambda head: head[:4] in {b"II*\x00", b"MM\x00*"},
    IngestFormat.BMP: lambda head: head.startswith(b"BM"),
    IngestFormat.WEBP: _webp,
}


@dataclass(frozen=True, slots=True)
class FormatCheck:
    """Result of :func:`check_format`: the format, or why the file is skipped."""

    #: ``None``: not ingested.
    format: IngestFormat | None
    #: Short English reason when the file is skipped; never contains the file name.
    reason: str = ""

    @property
    def supported(self) -> bool:
        return self.format is not None


def extension_of(filename: str) -> str:
    """The extension of the last part of ``filename`` in lower case, with the dot, or ``""``."""
    base = PurePosixPath(PureWindowsPath(filename).name).name
    suffix = PurePosixPath(base).suffix.lower()
    # Python 3.14 reports a trailing dot as the suffix "."; that is no extension.
    return "" if suffix == "." else suffix


def _is_ooxml_package(stream: IO[bytes]) -> bool:
    """A ZIP archive whose central directory lists ``[Content_Types].xml``.

    Only the directory is read; no entry is unpacked.
    """
    stream.seek(0)
    if stream.read(len(_ZIP_SIGNATURE)) != _ZIP_SIGNATURE:
        return False
    stream.seek(0)
    try:
        with zipfile.ZipFile(stream) as archive:
            return OOXML_CONTENT_TYPES_ENTRY in archive.namelist()
    except zipfile.BadZipFile, zipfile.LargeZipFile, ValueError, EOFError, OSError:
        return False


def _is_utf8_text(stream: IO[bytes]) -> bool:
    """The whole content is valid UTF-8 and contains no NUL character."""
    stream.seek(0)
    decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
    try:
        while chunk := stream.read(READ_CHUNK_BYTES):
            if b"\x00" in chunk:
                return False
            decoder.decode(chunk)
        decoder.decode(b"", final=True)
    except UnicodeDecodeError:
        return False
    return True


def check_format(filename: str, stream: IO[bytes]) -> FormatCheck:
    """Decide from the original file name and the content whether a file is ingested.

    ``stream`` must be readable and seekable (a file of the blob storage); it
    is read from the start, its position afterwards is undefined.
    """
    extension = extension_of(filename)
    expected = EXTENSIONS.get(extension)
    if expected is None:
        if not extension:
            return FormatCheck(None, "the file name has no extension")
        if not _SHOWN_EXTENSION_RE.fullmatch(extension):
            return FormatCheck(None, "files with this extension are not ingested")
        return FormatCheck(None, f"files with the extension {extension} are not ingested")

    if expected in OOXML_FORMATS:
        matches = _is_ooxml_package(stream)
    elif expected is IngestFormat.MARKDOWN:
        matches = _is_utf8_text(stream)
    else:
        stream.seek(0)
        matches = _SIGNATURES[expected](stream.read(HEAD_BYTES))

    if not matches:
        return FormatCheck(None, f"the content does not match the extension {extension}")
    return FormatCheck(expected)
