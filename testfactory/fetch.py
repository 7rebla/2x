"""Load the material listed in a test factory manifest and verify it.

Every entry with ``fetch: auto`` is loaded over HTTPS into the ``root``
directory of the manifest (``testfactory/extern`` for the test factory) and
checked against its checksum before it is put in place. Entries that are
fetched by hand or checked in are only verified. Needs nothing but the Python
standard library. Usage and the meaning of the results are described in
``testfactory/README.md``.

Command line::

    python -m testfactory.fetch [--only ID [ID ...]] [--verify | --record]
                                [--dry-run] [--strict] [--manifest PATH]
                                [--dest PATH] [--max-size MIB]

Loaded content is data. It is stored and hashed, never imported or executed.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import hashlib
import http.client
import os
import shutil
import ssl
import stat
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from typing import IO, Final
from urllib.parse import urljoin, urlsplit

from testfactory import manifest_tools
from testfactory.manifest_tools import Entry, Manifest

# Fixed and neutral: no name, no e-mail address, no details of the machine.
USER_AGENT: Final = "twox-testfactory-fetch/1.0"

DEFAULT_MAX_SIZE_MIB: Final = 2048
MAX_REDIRECTS: Final = 5
MAX_ARCHIVE_MEMBERS: Final = 200_000
# An extracted archive may be this many times larger than the download limit.
EXTRACTED_SIZE_FACTOR: Final = 4
GITHUB_HOST: Final = "github.com"
# Working directory below the root; removed again after every entry.
PARTIAL_DIR_NAME: Final = ".fetch-partial"

_CHUNK_BYTES: Final = 1024 * 1024
_REDIRECT_STATUS: Final = (301, 302, 303, 307, 308)
_RETRY_STATUS: Final = (408, 425, 429, 500, 502, 503, 504)

# Results, as shown in the summary.
RESULT_LOADED: Final = "loaded"
RESULT_RECORDED: Final = "recorded"
RESULT_OK: Final = "ok"
RESULT_UNVERIFIED: Final = "unverified"
RESULT_MANUAL: Final = "manual"
RESULT_REFERENCE: Final = "reference-only"
RESULT_WOULD_LOAD: Final = "would-load"
RESULT_WOULD_RECORD: Final = "would-record"
RESULT_NO_CHECKSUM: Final = "no-checksum"
RESULT_MISSING: Final = "missing"
RESULT_MISMATCH: Final = "mismatch"
RESULT_FAILED: Final = "failed"

FAILURE_RESULTS: Final = (
    RESULT_NO_CHECKSUM,
    RESULT_MISSING,
    RESULT_MISMATCH,
    RESULT_FAILED,
)

EXIT_OK: Final = 0
EXIT_FAILED: Final = 1
EXIT_USAGE: Final = 2


@dataclass(frozen=True)
class Settings:
    """Limits of the downloads."""

    timeout: float = 60.0  # seconds without any data
    total_timeout: float = 3600.0  # seconds for one attempt as a whole
    attempts: int = 3
    retry_pause: float = 5.0  # seconds between attempts
    max_bytes: int = DEFAULT_MAX_SIZE_MIB * 1024 * 1024  # per download
    max_archive_members: int = MAX_ARCHIVE_MEMBERS


@dataclass(frozen=True)
class Options:
    """What a run does; mirrors the command line switches."""

    verify: bool = False
    record: bool = False
    dry_run: bool = False
    strict: bool = False


@dataclass(frozen=True)
class Outcome:
    """What happened to one entry."""

    entry_id: str
    result: str
    http_status: int | None = None
    size_bytes: int | None = None
    detail: str = ""
    # Set when --record computed values that go back into the manifest.
    updated_entry: Entry | None = None


@dataclass(frozen=True)
class Download:
    """Checksum and size of a downloaded file."""

    sha256: str
    size_bytes: int


class FetchError(Exception):
    """A download or an archive could not be used."""

    def __init__(
        self, message: str, *, http_status: int | None = None, retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.retryable = retryable


def _clean(text: object) -> str:
    """Make text from a server or an archive safe to print."""
    return "".join(char if char.isprintable() else "?" for char in str(text))[:300]


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never follows a redirect; ``_download_once`` checks and follows them itself."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> None:
        return None


def _build_opener() -> urllib.request.OpenerDirector:
    """Return an opener that can do plain GET requests and nothing else.

    No proxies from the environment, no cookies, no authentication, no
    ``file:`` or ``ftp:`` addresses, no automatic redirects. Certificates are
    verified against the system store.
    """
    opener = urllib.request.OpenerDirector()
    handlers: tuple[urllib.request.BaseHandler, ...] = (
        urllib.request.UnknownHandler(),
        urllib.request.HTTPHandler(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _NoRedirectHandler(),
        urllib.request.HTTPDefaultErrorHandler(),
        urllib.request.HTTPErrorProcessor(),
    )
    for handler in handlers:
        opener.add_handler(handler)
    return opener


def _download_once(
    url: str,
    handle: IO[bytes],
    settings: Settings,
    limit: int,
    *,
    allow_insecure_loopback: bool = False,
) -> Download:
    """Do one attempt: follow checked redirects and stream the body into ``handle``."""
    opener = _build_opener()
    deadline = time.monotonic() + settings.total_timeout
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        # Every address, also every redirect target, passes the one address
        # check of the manifest tools before it is opened.
        problem = manifest_tools.address_problem(
            current, allow_insecure_loopback=allow_insecure_loopback
        )
        if problem is not None:
            raise FetchError(f"address '{_clean(current)}' refused: {problem}")
        request = urllib.request.Request(
            current,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
                "Accept-Encoding": "identity",
            },
            method="GET",
        )
        try:
            response: http.client.HTTPResponse = opener.open(request, timeout=settings.timeout)
        except urllib.error.HTTPError as error:
            status = error.code
            location = error.headers.get("Location")
            error.close()
            if status in _REDIRECT_STATUS:
                if not location:
                    raise FetchError(
                        "redirect without Location header", http_status=status
                    ) from None
                current = urljoin(current, location)
                continue
            raise FetchError(
                f"server answered with HTTP status {status}",
                http_status=status,
                retryable=status in _RETRY_STATUS,
            ) from None
        except (OSError, http.client.HTTPException) as error:
            reason = error.reason if isinstance(error, urllib.error.URLError) else error
            raise FetchError(f"connection failed: {_clean(reason)}", retryable=True) from None
        with response:
            return _read_body(response, handle, limit, deadline)
    raise FetchError(f"more than {MAX_REDIRECTS} redirects")


def _read_body(
    response: http.client.HTTPResponse, handle: IO[bytes], limit: int, deadline: float
) -> Download:
    """Copy the body block by block, hashing it on the way."""
    announced: int | None = None
    length_header = response.headers.get("Content-Length")
    if length_header is not None and length_header.strip().isdecimal():
        announced = int(length_header.strip())
        if announced > limit:
            raise FetchError(f"file has {announced} bytes, allowed are {limit}")
    digest = hashlib.sha256()
    received = 0
    while True:
        if time.monotonic() > deadline:
            raise FetchError("download took too long", retryable=True)
        try:
            chunk = response.read(_CHUNK_BYTES)
        except (OSError, http.client.HTTPException) as error:
            raise FetchError(f"connection lost: {_clean(error)}", retryable=True) from None
        if not chunk:
            break
        received += len(chunk)
        if received > limit:
            raise FetchError(f"file has more than the allowed {limit} bytes")
        digest.update(chunk)
        handle.write(chunk)
    if announced is not None and received != announced:
        raise FetchError(
            f"incomplete: {received} of {announced} bytes received", retryable=True
        )
    return Download(digest.hexdigest(), received)


def download(
    url: str,
    destination: Path,
    *,
    settings: Settings = Settings(),
    expected_size: int | None = None,
    allow_insecure_loopback: bool = False,
) -> Download:
    """Load ``url`` into the file ``destination`` and return checksum and size.

    Only ``https://`` addresses are opened, redirects included. The file is
    written block by block and never grows beyond ``settings.max_bytes`` or
    ``expected_size``. Failed connections and overloaded servers are retried
    a few times with a pause. ``allow_insecure_loopback`` is for tests with a
    local server and can only be set in code.
    """
    limit = settings.max_bytes if expected_size is None else min(settings.max_bytes, expected_size)
    attempt = 1
    while True:
        try:
            with open(destination, "wb") as handle:
                return _download_once(
                    url, handle, settings, limit, allow_insecure_loopback=allow_insecure_loopback
                )
        except FetchError as error:
            if not error.retryable or attempt >= settings.attempts:
                raise
            print(f"  attempt {attempt} failed ({error}); trying again", flush=True)
        attempt += 1
        time.sleep(settings.retry_pause)


def archive_url(repository: str, commit: str) -> str:
    """Return the address of the tar archive of ``commit``.

    Follows the pattern that GitHub documents for the archive of a commit
    ("Downloading source code archives", checked 2026-11-21):
    ``https://github.com/OWNER/REPOSITORY/archive/COMMIT.tar.gz``.
    Other ``https://`` hosts are refused, because their pattern is not known.
    """
    parts = urlsplit(repository)
    if parts.scheme == "https" and parts.hostname != GITHUB_HOST:
        raise FetchError(f"only repositories on {GITHUB_HOST} can be loaded automatically")
    path = parts.path.rstrip("/").removesuffix(".git")
    segments = path.split("/")[1:]
    if len(segments) != 2 or not all(segments) or parts.query or parts.fragment:
        raise FetchError("repository address must have the form https://HOST/OWNER/REPOSITORY")
    return f"{parts.scheme}://{parts.netloc}/{segments[0]}/{segments[1]}/archive/{commit}.tar.gz"


def _member_segments(name: str) -> list[str]:
    """Split the name of an archive member; refuse anything but a clean relative path.

    The rule is the one for targets in the manifest: no backslash, no colon
    (drive letters), no control characters, not absolute, no empty, ``.`` or
    ``..`` segment.
    """
    problem = manifest_tools.relative_path_problem(name)
    if problem is not None:
        raise FetchError(f"archive member '{_clean(name)}': {problem}")
    return name.split("/")


def _member_path(destination: Path, segments: Sequence[str]) -> Path:
    """Return the path of a member below ``destination``; refuse anything outside.

    Second line of defence behind ``_member_segments``: the resolved path must
    lie below the resolved ``destination``, whatever the platform makes of the
    segments.
    """
    path = destination.joinpath(*segments)
    resolved_destination = destination.resolve()
    resolved = path.resolve()
    if resolved == resolved_destination or not resolved.is_relative_to(resolved_destination):
        raise FetchError(f"archive member '{_clean('/'.join(segments))}' leaves the target")
    return path


def extract_archive(
    archive: Path,
    destination: Path,
    *,
    max_bytes: int,
    max_members: int = MAX_ARCHIVE_MEMBERS,
) -> None:
    """Extract a gzip-compressed tar archive of a repository into ``destination``.

    ``destination`` must not exist yet. The archive must contain exactly one
    top-level directory (as archives of a commit do); it is left out, so the
    repository content lies directly in ``destination``.

    Nothing is ever written outside ``destination``: member names must be
    clean relative paths, and regular files and directories additionally go
    through the ``data`` filter of the standard library. No link is ever
    created. A symbolic link is stored as a small file that contains the link
    target, which is how ``tree_sha256`` counts links anyway. Hard links,
    devices, pipes and everything else are refused, as are archives with too
    many members or too much content.
    """
    destination.mkdir()
    total = 0
    count = 0
    top: str | None = None
    try:
        with tarfile.open(archive, mode="r:gz", errorlevel=1) as tar:
            for member in tar:
                count += 1
                if count > max_members:
                    raise FetchError(f"archive has more than {max_members} members")
                name = member.name.rstrip("/") if member.isdir() else member.name
                segments = _member_segments(name)
                if top is None:
                    top = segments[0]
                elif segments[0] != top:
                    raise FetchError("archive has more than one top-level directory")
                if len(segments) == 1:
                    if not member.isdir():
                        raise FetchError(
                            f"archive member '{_clean(name)}' lies outside the top-level directory"
                        )
                    continue
                relative = "/".join(segments[1:])
                if member.isdir():
                    tar.extract(member.replace(name=relative), path=destination, filter="data")
                elif member.isreg():
                    total += member.size
                    if total > max_bytes:
                        raise FetchError(f"archive content exceeds {max_bytes} bytes")
                    tar.extract(member.replace(name=relative), path=destination, filter="data")
                elif member.issym():
                    content = member.linkname.encode("utf-8")
                    total += len(content)
                    if total > max_bytes:
                        raise FetchError(f"archive content exceeds {max_bytes} bytes")
                    # Checked before anything is created and again afterwards.
                    path = _member_path(destination, segments[1:])
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path = _member_path(destination, segments[1:])
                    if path.is_symlink():
                        raise FetchError(f"archive member '{_clean(name)}' would replace a link")
                    path.write_bytes(content)
                else:
                    raise FetchError(
                        f"archive member '{_clean(name)}' is a hard link or a special file"
                    )
    except (tarfile.TarError, OSError, EOFError, zlib.error, ValueError) as error:
        raise FetchError(f"archive cannot be extracted: {_clean(error)}") from None
    if top is None:
        raise FetchError("archive is empty")


def _raise_walk_error(error: OSError) -> None:
    raise error


def tree_size(directory: Path) -> int:
    """Return the sum of the sizes of all files below ``directory``."""
    total = 0
    for current, dir_names, file_names in os.walk(directory, onerror=_raise_walk_error):
        for name in [*dir_names, *file_names]:
            status = os.lstat(os.path.join(current, name))
            if not stat.S_ISDIR(status.st_mode):
                total += status.st_size
    return total


def _measure(target: Path, is_tree: bool) -> Download | None:
    """Return checksum and size of what lies at ``target``, or ``None`` if nothing does."""
    try:
        mode = target.lstat().st_mode
    except FileNotFoundError:
        return None
    if is_tree:
        if not stat.S_ISDIR(mode):
            raise FetchError("target exists but is not a directory")
        return Download(manifest_tools.tree_sha256(target), tree_size(target))
    if not stat.S_ISREG(mode):
        raise FetchError("target exists but is not a regular file")
    return Download(manifest_tools.file_sha256(target), target.stat().st_size)


def _install(staged: Path, root: Path, target_text: str, is_tree: bool) -> None:
    """Move verified material from the working directory to its target."""
    target = manifest_tools.checked_target_path(root, target_text)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Checked again now that the chain of directories exists.
    target = manifest_tools.checked_target_path(root, target_text)
    try:
        mode: int | None = target.lstat().st_mode
    except FileNotFoundError:
        mode = None
    if mode is not None:
        if is_tree:
            if not stat.S_ISDIR(mode):
                raise FetchError("target exists but is not a directory")
            shutil.rmtree(target)
        elif not stat.S_ISREG(mode):
            raise FetchError("target exists but is not a regular file")
    os.replace(staged, target)


def _load(
    entry: Entry,
    root: Path,
    target_text: str,
    expected: str | None,
    settings: Settings,
    today: str,
    *,
    allow_insecure_loopback: bool = False,
) -> Outcome:
    """Download one entry, verify it and only then put it in place."""
    is_tree = entry.kind == manifest_tools.KIND_GIT_ARCHIVE
    if is_tree:
        if entry.repository is None or entry.commit is None:
            raise FetchError("repository and commit are required")
        url = archive_url(entry.repository, entry.commit)
    else:
        if entry.url is None:
            raise FetchError("url is required")
        url = entry.url
    print(f"{entry.id}: loading {url}", flush=True)

    partial = root / PARTIAL_DIR_NAME
    partial.mkdir(parents=True, exist_ok=True)
    if partial.is_symlink():
        raise FetchError(f"'{PARTIAL_DIR_NAME}' must not be a symbolic link")
    work = Path(tempfile.mkdtemp(prefix=f"{entry.id}-", dir=partial))
    try:
        if is_tree:
            archive = work / "archive.tar.gz"
            download(
                url, archive, settings=settings, allow_insecure_loopback=allow_insecure_loopback
            )
            staged = work / "tree"
            extract_archive(
                archive,
                staged,
                max_bytes=settings.max_bytes * EXTRACTED_SIZE_FACTOR,
                max_members=settings.max_archive_members,
            )
            measured = Download(manifest_tools.tree_sha256(staged), tree_size(staged))
        else:
            staged = work / "download"
            measured = download(
                url,
                staged,
                settings=settings,
                # Without a checksum the size in the manifest is only an
                # advance figure from research and must not cut the download.
                expected_size=None if expected is None else entry.size_bytes,
                allow_insecure_loopback=allow_insecure_loopback,
            )
        if expected is None:
            _install(staged, root, target_text, is_tree)
            return _recorded(entry, measured, today)
        if entry.size_bytes is not None and measured.size_bytes != entry.size_bytes:
            return Outcome(
                entry.id,
                RESULT_MISMATCH,
                size_bytes=measured.size_bytes,
                detail=f"size is {measured.size_bytes} bytes, manifest says {entry.size_bytes}; "
                "discarded",
            )
        if measured.sha256 != expected:
            return Outcome(
                entry.id,
                RESULT_MISMATCH,
                size_bytes=measured.size_bytes,
                detail=f"checksum of the download is {measured.sha256}, "
                f"manifest says {expected}; discarded",
            )
        _install(staged, root, target_text, is_tree)
        return Outcome(entry.id, RESULT_LOADED, size_bytes=measured.size_bytes)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        try:
            partial.rmdir()
        except OSError:
            pass


def _with_checksum(entry: Entry, measured: Download, today: str) -> Entry:
    """Return ``entry`` with checksum, size and date filled in."""
    if entry.kind == manifest_tools.KIND_GIT_ARCHIVE:
        return dataclasses.replace(
            entry,
            tree_sha256=measured.sha256,
            size_bytes=measured.size_bytes,
            retrieved_on=today,
        )
    return dataclasses.replace(
        entry, sha256=measured.sha256, size_bytes=measured.size_bytes, retrieved_on=today
    )


def _recorded(entry: Entry, measured: Download, today: str) -> Outcome:
    """Outcome of --record: the measured values go into the manifest.

    A size that was in the manifest before the first fetch is an advance
    figure. If the measured size differs, the measured one is recorded and
    the difference is reported, so that it can be looked into.
    """
    detail = ""
    if entry.size_bytes is not None and entry.size_bytes != measured.size_bytes:
        detail = (
            f"SIZE DIFFERS: measured {measured.size_bytes} bytes, the manifest said "
            f"{entry.size_bytes}; the measured size was recorded"
        )
    return Outcome(
        entry.id,
        RESULT_RECORDED,
        size_bytes=measured.size_bytes,
        detail=detail,
        updated_entry=_with_checksum(entry, measured, today),
    )


def _mismatch(entry: Entry, present: Download, expected: str) -> Outcome:
    return Outcome(
        entry.id,
        RESULT_MISMATCH,
        size_bytes=present.size_bytes,
        detail=f"checksum is {present.sha256}, manifest says {expected}",
    )


def _compare(entry: Entry, present: Download, expected: str) -> Outcome:
    """Compare what is there with the manifest: checksum first, then size."""
    if present.sha256 != expected:
        return _mismatch(entry, present, expected)
    if entry.size_bytes is not None and present.size_bytes != entry.size_bytes:
        return Outcome(
            entry.id,
            RESULT_MISMATCH,
            size_bytes=present.size_bytes,
            detail=f"checksum matches, but size is {present.size_bytes} bytes and the "
            f"manifest says {entry.size_bytes}",
        )
    return Outcome(entry.id, RESULT_OK, size_bytes=present.size_bytes)


def _process(
    entry: Entry,
    root: Path,
    options: Options,
    settings: Settings,
    today: str,
    *,
    allow_insecure_loopback: bool = False,
) -> Outcome:
    """Decide what to do with one entry and do it."""
    if entry.target is None or entry.kind in (
        manifest_tools.KIND_CONTAINER_IMAGE,
        manifest_tools.KIND_REFERENCE,
    ):
        return Outcome(entry.id, RESULT_REFERENCE, size_bytes=entry.size_bytes)
    if entry.target.split("/")[0] == PARTIAL_DIR_NAME:
        raise FetchError(f"target must not lie in '{PARTIAL_DIR_NAME}'")
    target = manifest_tools.checked_target_path(root, entry.target)
    is_tree = entry.kind == manifest_tools.KIND_GIT_ARCHIVE
    expected = entry.tree_sha256 if is_tree else entry.sha256
    present = _measure(target, is_tree)

    if entry.kind == manifest_tools.KIND_LOCAL:
        if present is None:
            return Outcome(entry.id, RESULT_MISSING, detail=f"{target.as_posix()} does not exist")
        if expected is None:
            return _mismatch(entry, present, "nothing")
        return _compare(entry, present, expected)

    if entry.fetch == manifest_tools.FETCH_MANUAL:
        if present is None:
            source = entry.landing_page or entry.url or entry.repository
            return Outcome(
                entry.id,
                RESULT_MANUAL,
                detail=f"fetch by hand from {source} and store as {target.as_posix()}",
            )
        if expected is None:
            if not options.record:
                return Outcome(
                    entry.id,
                    RESULT_UNVERIFIED,
                    size_bytes=present.size_bytes,
                    detail="present, but the manifest has no checksum; use --record",
                )
            if options.dry_run:
                return Outcome(entry.id, RESULT_WOULD_RECORD, size_bytes=present.size_bytes)
            return _recorded(entry, present, today)
        return _compare(entry, present, expected)

    # fetch: auto
    if expected is not None and present is not None and present.sha256 == expected:
        # Right content: ok, or a size in the manifest that contradicts it.
        return _compare(entry, present, expected)
    if options.verify:
        if present is None:
            return Outcome(entry.id, RESULT_MISSING, detail=f"{target.as_posix()} does not exist")
        if expected is None:
            return Outcome(
                entry.id,
                RESULT_NO_CHECKSUM,
                size_bytes=present.size_bytes,
                detail="the manifest has no checksum",
            )
        return _mismatch(entry, present, expected)
    if expected is None and not options.record:
        return Outcome(
            entry.id,
            RESULT_NO_CHECKSUM,
            detail="the manifest has no checksum; nothing loaded, use --record for the first fetch",
        )
    if options.dry_run:
        return Outcome(
            entry.id,
            RESULT_WOULD_RECORD if expected is None else RESULT_WOULD_LOAD,
            size_bytes=entry.size_bytes,
        )
    return _load(
        entry,
        root,
        entry.target,
        expected,
        settings,
        today,
        allow_insecure_loopback=allow_insecure_loopback,
    )


def process_entry(
    entry: Entry,
    root: Path,
    options: Options,
    settings: Settings,
    today: str,
    *,
    allow_insecure_loopback: bool = False,
) -> Outcome:
    """Handle one entry. Never raises for a problem of the entry; reports it instead."""
    try:
        return _process(
            entry, root, options, settings, today, allow_insecure_loopback=allow_insecure_loopback
        )
    except FetchError as error:
        return Outcome(
            entry.id, RESULT_FAILED, http_status=error.http_status, detail=_clean(error)
        )
    except (OSError, ValueError) as error:
        return Outcome(entry.id, RESULT_FAILED, detail=_clean(error))


def format_summary(outcomes: Sequence[Outcome]) -> str:
    """Return the summary table and the notes as text."""
    rows = [("ID", "RESULT", "HTTP", "SIZE")]
    for outcome in outcomes:
        rows.append(
            (
                outcome.entry_id,
                outcome.result,
                "-" if outcome.http_status is None else str(outcome.http_status),
                "-" if outcome.size_bytes is None else str(outcome.size_bytes),
            )
        )
    widths = [max(len(row[column]) for row in rows) for column in range(4)]
    lines = [
        f"{row[0]:<{widths[0]}}  {row[1]:<{widths[1]}}  {row[2]:>{widths[2]}}  {row[3]:>{widths[3]}}"
        for row in rows
    ]
    counts: dict[str, int] = {}
    for outcome in outcomes:
        counts[outcome.result] = counts.get(outcome.result, 0) + 1
    lines.append("")
    lines.append(
        f"{len(outcomes)} {'entry' if len(outcomes) == 1 else 'entries'}"
        + "".join(f", {count} {result}" for result, count in counts.items())
    )
    notes = [outcome for outcome in outcomes if outcome.detail]
    if notes:
        lines.append("")
        lines.extend(
            f"{outcome.entry_id}: {outcome.result}: {_clean(outcome.detail)}" for outcome in notes
        )
    return "\n".join(lines) + "\n"


def exit_code(outcomes: Sequence[Outcome], options: Options) -> int:
    """Return the exit code that belongs to ``outcomes``."""
    if options.dry_run:
        return EXIT_OK
    results = {outcome.result for outcome in outcomes}
    if results.intersection(FAILURE_RESULTS):
        return EXIT_FAILED
    if options.strict and RESULT_MANUAL in results:
        return EXIT_FAILED
    return EXIT_OK


def run(
    manifest_path: str | Path,
    *,
    dest: str | Path | None = None,
    only: Sequence[str] | None = None,
    options: Options = Options(),
    settings: Settings = Settings(),
    today: str | None = None,
    allow_insecure_loopback: bool = False,
) -> int:
    """Process a manifest, print the summary and return the exit code.

    ``allow_insecure_loopback`` exists for tests that serve files from a local
    HTTP server. It can only be set in code; the command line never sets it.
    """
    try:
        manifest: Manifest = manifest_tools.load_manifest(
            manifest_path, allow_insecure_loopback=allow_insecure_loopback
        )
    except manifest_tools.ManifestError as error:
        for problem in error.problems:
            print(f"{manifest_path}: {problem}", file=sys.stderr)
        print(f"{manifest_path}: INVALID, nothing done", file=sys.stderr)
        return EXIT_USAGE

    entries = list(manifest.entries)
    if only is not None:
        known = {entry.id for entry in entries}
        unknown = [entry_id for entry_id in only if entry_id not in known]
        if unknown:
            print(
                f"{manifest_path}: no entry with ID: " + ", ".join(map(_clean, unknown)),
                file=sys.stderr,
            )
            return EXIT_USAGE
        entries = [entry for entry in entries if entry.id in only]

    root = Path(dest) if dest is not None else manifest_tools.root_path(manifest_path, manifest)
    day = today if today is not None else datetime.date.today().isoformat()
    outcomes: list[Outcome] = []
    updated: dict[str, Entry] = {}
    try:
        # One after the other, never in parallel.
        for entry in entries:
            outcome = process_entry(
                entry, root, options, settings, day, allow_insecure_loopback=allow_insecure_loopback
            )
            outcomes.append(outcome)
            if outcome.updated_entry is not None:
                updated[entry.id] = outcome.updated_entry
    finally:
        # Also after an interruption: what was recorded so far is kept.
        if updated:
            manifest_tools.write_manifest(
                manifest_path,
                dataclasses.replace(
                    manifest,
                    entries=tuple(updated.get(entry.id, entry) for entry in manifest.entries),
                ),
            )
            print(f"{manifest_path}: {len(updated)} checksum(s) recorded", flush=True)

    print(format_summary(outcomes), end="", flush=True)
    code = exit_code(outcomes, options)
    if options.dry_run:
        print("Dry run: nothing was loaded or written.")
    elif code != EXIT_OK:
        print("FAILED: not everything is present and verified.", file=sys.stderr)
    elif any(outcome.result == RESULT_MANUAL for outcome in outcomes):
        print("WARNING: some material has to be fetched by hand, see above.", file=sys.stderr)
    return code


def _positive_int(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be larger than 0")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m testfactory.fetch",
        description=(
            "Load every manifest entry with 'fetch: auto' over HTTPS, verify the checksums "
            "and report what was loaded, what is already there, what has to be fetched by "
            "hand and what failed."
        ),
        epilog=(
            "Exit code 0: every requested 'auto' entry is present and verified. "
            "1: something is missing or wrong. 2: the manifest or the arguments are not usable."
        ),
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="ID",
        help="handle only the entries with these IDs",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--verify",
        action="store_true",
        help="load nothing; only check the files that are there against the manifest",
    )
    mode.add_argument(
        "--record",
        action="store_true",
        help=(
            "first fetch: for entries without checksum, load, compute checksum, size and "
            "date and write them into the manifest; existing checksums are never changed"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="only show what would be done; loads and writes nothing, exit code 0",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit with 1 if material that has to be fetched by hand is missing",
    )
    parser.add_argument(
        "--manifest",
        metavar="PATH",
        default=manifest_tools.DEFAULT_MANIFEST_PATH,
        help=f"manifest file (default: {manifest_tools.DEFAULT_MANIFEST_PATH})",
    )
    parser.add_argument(
        "--dest",
        metavar="PATH",
        default=None,
        help="directory to load into (default: the 'root' named in the manifest)",
    )
    parser.add_argument(
        "--max-size",
        metavar="MIB",
        type=_positive_int,
        default=DEFAULT_MAX_SIZE_MIB,
        help=f"largest allowed download in MiB (default: {DEFAULT_MAX_SIZE_MIB})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line. Returns the exit code."""
    arguments = _build_parser().parse_args(argv)
    manifest_path: str = arguments.manifest
    dest: str | None = arguments.dest
    only: list[str] | None = arguments.only
    max_size_mib: int = arguments.max_size
    options = Options(
        verify=arguments.verify,
        record=arguments.record,
        dry_run=arguments.dry_run,
        strict=arguments.strict,
    )
    # The switch for insecure local addresses is deliberately not passed:
    # the command line accepts https:// only.
    return run(
        manifest_path,
        dest=dest,
        only=only,
        options=options,
        settings=Settings(max_bytes=max_size_mib * 1024 * 1024),
        today=None,
    )


if __name__ == "__main__":
    sys.exit(main())
