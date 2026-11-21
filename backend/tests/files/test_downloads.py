"""Safe delivery of stored files (twox.files.downloads)."""

import asyncio
import io
import os
import warnings

import pytest

from twox.files.downloads import (
    DOWNLOAD_BLOCK_SIZE,
    SAFE_CONTENT_TYPES,
    BlobDownloadResponse,
    download_content_type,
)


@pytest.mark.parametrize("content_type", sorted(SAFE_CONTENT_TYPES))
def test_safe_types_are_kept(content_type: str) -> None:
    assert download_content_type(content_type) == content_type


def test_safe_type_with_parameters_and_capitals_is_normalised() -> None:
    assert download_content_type("Text/Plain; charset=utf-8") == "text/plain"


@pytest.mark.parametrize(
    "content_type",
    [
        "text/html",
        "image/svg+xml",
        "application/xhtml+xml",
        "application/xml",
        "text/xml",
        "text/javascript",
        "application/javascript",
        "application/x-sh",
        "multipart/related",
        "application/octet-stream",
        "",
        "nonsense",
    ],
)
def test_other_types_become_octet_stream(content_type: str) -> None:
    assert download_content_type(content_type) == "application/octet-stream"


def test_no_markup_or_script_type_is_on_the_list() -> None:
    risky = {t for t in SAFE_CONTENT_TYPES if any(w in t for w in ("html", "svg", "xml", "script"))}
    # Office Open XML formats carry "xml" in their names but are packages,
    # not markup a browser would render.
    assert risky == {t for t in SAFE_CONTENT_TYPES if "openxmlformats" in t}


def test_response_headers() -> None:
    response = BlobDownloadResponse(
        io.BytesIO(b"abc"), filename="a/b/c.html", content_type="text/html"
    )

    assert response["Content-Disposition"] == 'attachment; filename="c.html"'
    assert response["Content-Type"] == "application/octet-stream"
    assert response["Content-Length"] == "3"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Content-Security-Policy"] == "sandbox"


def test_empty_name_gets_the_fallback() -> None:
    response = BlobDownloadResponse(io.BytesIO(b"abc"), filename="", content_type="text/plain")

    assert response["Content-Disposition"] == 'attachment; filename="unnamed"'


def test_asgi_iteration_streams_block_by_block_without_warning() -> None:
    content = os.urandom(3 * DOWNLOAD_BLOCK_SIZE + 17)
    response = BlobDownloadResponse(
        io.BytesIO(content), filename="x.bin", content_type="application/octet-stream"
    )

    async def collect() -> list[bytes]:
        return [part async for part in response]

    with warnings.catch_warnings():
        # Django warns when it has to collect a synchronous iterator in memory.
        warnings.simplefilter("error")
        parts = asyncio.run(collect())

    assert b"".join(parts) == content
    assert [len(p) for p in parts] == [DOWNLOAD_BLOCK_SIZE] * 3 + [17]


def test_sync_iteration_returns_the_content() -> None:
    content = os.urandom(DOWNLOAD_BLOCK_SIZE + 1)
    response = BlobDownloadResponse(
        io.BytesIO(content), filename="x.bin", content_type="application/pdf"
    )

    assert b"".join(response) == content
