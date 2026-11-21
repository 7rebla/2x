"""Safe delivery of stored files.

A download is always an attachment: the browser saves the file and never shows
it as a page of the application's origin. Every response carries

- ``Content-Disposition: attachment`` with the cleaned original file name,
  encoded after RFC 6266 and RFC 5987 (Django's ``FileResponse``),
- ``Content-Type`` from :data:`SAFE_CONTENT_TYPES` only, anything else as
  ``application/octet-stream`` - HTML, SVG, XML and scripts never keep their
  type, whatever the uploader declared,
- ``X-Content-Type-Options: nosniff`` and ``Content-Security-Policy: sandbox``,
  so that even a response opened directly runs no script.
"""

from collections.abc import AsyncIterator, Iterator
from typing import IO

from asgiref.sync import sync_to_async
from django.http import FileResponse

from twox.files.services import FALLBACK_CONTENT_TYPE, clean_filename

#: Media types delivered as they are, for the kinds of documents of the
#: project (PDF, Office, Markdown and text, images with text). SVG is an
#: image that can hold scripts and is therefore missing on purpose.
SAFE_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        # PDF
        "application/pdf",
        # Microsoft Office, old and Office Open XML formats
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        # OpenDocument
        "application/vnd.oasis.opendocument.text",
        "application/vnd.oasis.opendocument.spreadsheet",
        "application/vnd.oasis.opendocument.presentation",
        # Markdown and plain text
        "text/markdown",
        "text/plain",
        # Raster images
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "image/tiff",
        "image/bmp",
    }
)

#: Read and send blocks of this size (instead of the 4 KiB of FileResponse).
DOWNLOAD_BLOCK_SIZE = 64 * 1024


def download_content_type(stored: str) -> str:
    """The ``Content-Type`` of a download: the stored type if it is safe, else the fallback."""
    value = stored.split(";", 1)[0].strip().lower()
    return value if value in SAFE_CONTENT_TYPES else FALLBACK_CONTENT_TYPE


class BlobDownloadResponse(FileResponse):
    """A stored blob as an attachment, streamed block by block.

    Under ASGI Django would collect a synchronous file iterator into one list
    before sending, that is the whole file in memory. :meth:`__aiter__` reads
    one block at a time in a worker thread instead. Under WSGI and in the test
    client the normal synchronous iteration applies.
    """

    block_size = DOWNLOAD_BLOCK_SIZE

    def __init__(self, blob: IO[bytes], *, filename: str, content_type: str) -> None:
        super().__init__(
            blob,
            as_attachment=True,
            filename=clean_filename(filename),
            content_type=download_content_type(content_type),
        )
        self.headers["X-Content-Type-Options"] = "nosniff"
        self.headers["Content-Security-Policy"] = "sandbox"

    async def __aiter__(self) -> AsyncIterator[bytes]:
        content = self.streaming_content
        if not isinstance(content, Iterator):
            async for part in content:
                yield part
            return
        read_block = sync_to_async(_next_block, thread_sensitive=False)
        while (block := await read_block(content)) is not None:
            yield block


def _next_block(blocks: Iterator[bytes]) -> bytes | None:
    return next(blocks, None)
