"""Load, validate and write test factory manifest files.

A manifest lists every document and configuration source of the test factory
together with its origin, software version, checksum and terms of use. The
file is called ``manifest.yaml`` but is kept in JSON notation (every JSON
document is valid YAML), so this module needs nothing but the Python standard
library. The format is described in ``testfactory/README.md``.

Command line::

    python -m testfactory.manifest_tools check [--complete] [PATH]
    python -m testfactory.manifest_tools format [--check] [PATH]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import stat
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final
from urllib.parse import urlsplit

SCHEMA_VERSION: Final = 1
DEFAULT_MANIFEST_PATH: Final = "testfactory/manifest.yaml"

KIND_FILE: Final = "file"
KIND_GIT_ARCHIVE: Final = "git-archive"
KIND_CONTAINER_IMAGE: Final = "container-image"
KIND_REFERENCE: Final = "reference"
KIND_LOCAL: Final = "local"
KINDS: Final = (
    KIND_FILE,
    KIND_GIT_ARCHIVE,
    KIND_CONTAINER_IMAGE,
    KIND_REFERENCE,
    KIND_LOCAL,
)

FETCH_AUTO: Final = "auto"
FETCH_MANUAL: Final = "manual"
FETCH_NONE: Final = "none"
FETCH_MODES: Final = (FETCH_AUTO, FETCH_MANUAL, FETCH_NONE)

LANGUAGES: Final = ("de", "en", "")

# License values that are not SPDX identifiers.
NON_SPDX_LICENSES: Final = ("proprietary", "none-stated", "public-domain")

# Which ``fetch`` modes each kind allows.
_FETCH_BY_KIND: Final[dict[str, tuple[str, ...]]] = {
    KIND_FILE: (FETCH_AUTO, FETCH_MANUAL),
    KIND_GIT_ARCHIVE: (FETCH_AUTO, FETCH_MANUAL),
    KIND_CONTAINER_IMAGE: (FETCH_NONE,),
    KIND_REFERENCE: (FETCH_NONE,),
    KIND_LOCAL: (FETCH_NONE,),
}

# Fields that must be set (not null) for each kind.
_REQUIRED_BY_KIND: Final[dict[str, tuple[str, ...]]] = {
    # ``url`` or ``landing_page`` in addition, depending on ``fetch``; see
    # ``_parse_entry``.
    KIND_FILE: ("target",),
    KIND_GIT_ARCHIVE: ("repository", "branch", "commit", "target"),
    KIND_CONTAINER_IMAGE: ("image", "tag", "digest"),
    KIND_REFERENCE: (),
    KIND_LOCAL: ("target", "sha256"),
}

# Fields that are only allowed for the listed kinds; null everywhere else.
_KINDS_BY_FIELD: Final[dict[str, tuple[str, ...]]] = {
    "url": (KIND_FILE, KIND_REFERENCE, KIND_LOCAL),
    "repository": (KIND_GIT_ARCHIVE, KIND_REFERENCE, KIND_LOCAL),
    "branch": (KIND_GIT_ARCHIVE, KIND_REFERENCE, KIND_LOCAL),
    "commit": (KIND_GIT_ARCHIVE, KIND_REFERENCE, KIND_LOCAL),
    "image": (KIND_CONTAINER_IMAGE,),
    "tag": (KIND_CONTAINER_IMAGE,),
    "digest": (KIND_CONTAINER_IMAGE,),
    "derived_from": (KIND_LOCAL,),
    "generated_by": (KIND_LOCAL,),
    "sha256": (KIND_FILE, KIND_LOCAL),
    "tree_sha256": (KIND_GIT_ARCHIVE,),
    "size_bytes": (KIND_FILE, KIND_GIT_ARCHIVE, KIND_REFERENCE, KIND_LOCAL),
    "target": (KIND_FILE, KIND_GIT_ARCHIVE, KIND_LOCAL),
}

_TOP_LEVEL_KEYS: Final = ("schema_version", "root", "entries")
_ENTRY_KEYS: Final = (
    "id",
    "title",
    "language",
    "kind",
    "fetch",
    "url",
    "landing_page",
    "repository",
    "branch",
    "commit",
    "image",
    "tag",
    "digest",
    "derived_from",
    "generated_by",
    "software_version",
    "document_version",
    "version_source",
    "sha256",
    "tree_sha256",
    "size_bytes",
    "target",
    "terms",
    "assigned_to",
    "retrieved_on",
    "notes",
)
_TERMS_KEYS: Final = (
    "holder",
    "license",
    "redistribution",
    "terms_url",
    "note",
    "checked_on",
    "verified",
)

_ID_RE: Final = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_COMMIT_RE: Final = re.compile(r"[0-9a-f]{40}")
_SHA256_RE: Final = re.compile(r"[0-9a-f]{64}")
_DIGEST_RE: Final = re.compile(r"sha256:[0-9a-f]{64}")
_DATE_RE: Final = re.compile(r"\d{4}-\d{2}-\d{2}")
_SPDX_RE: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*")
_LOOPBACK_HOSTS: Final = ("127.0.0.1", "localhost")


@dataclass(frozen=True)
class Terms:
    """Terms of use of one source."""

    holder: str
    license: str
    redistribution: bool
    note: str
    verified: bool
    terms_url: str | None = None
    checked_on: str | None = None


@dataclass(frozen=True)
class Entry:
    """One manifest entry. Fields that do not apply to the kind are ``None``."""

    id: str
    title: str
    kind: str
    fetch: str
    terms: Terms
    language: str = ""
    url: str | None = None
    landing_page: str | None = None
    repository: str | None = None
    branch: str | None = None
    commit: str | None = None
    image: str | None = None
    tag: str | None = None
    digest: str | None = None
    derived_from: str | None = None
    generated_by: str | None = None
    software_version: str | None = None
    document_version: str | None = None
    version_source: str | None = None
    sha256: str | None = None
    tree_sha256: str | None = None
    size_bytes: int | None = None
    target: str | None = None
    assigned_to: tuple[str, ...] = ()
    retrieved_on: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class Manifest:
    """A complete manifest file."""

    schema_version: int
    root: str
    entries: tuple[Entry, ...]


@dataclass(frozen=True)
class Problem:
    """One finding of the validation.

    ``entry`` is the entry ID, ``#<position>`` (starting at 1) for an entry
    without a usable ID, or ``None`` for the file itself.
    """

    entry: str | None
    field: str
    message: str

    def __str__(self) -> str:
        where = "manifest" if self.entry is None else f"entry '{self.entry}'"
        return f"{where}: field '{self.field}': {self.message}"


class ManifestError(Exception):
    """Raised when a manifest cannot be read or is not valid."""

    def __init__(self, problems: Sequence[Problem]) -> None:
        self.problems: tuple[Problem, ...] = tuple(problems)
        super().__init__("; ".join(str(problem) for problem in self.problems))


def address_problem(address: str, *, allow_insecure_loopback: bool = False) -> str | None:
    """Return why ``address`` is not allowed, or ``None`` if it is allowed.

    This is the only place that decides which addresses a manifest may
    contain. Only ``https://`` is allowed. With ``allow_insecure_loopback``
    (for tests only) ``http://127.0.0.1`` and ``http://localhost`` are allowed
    as well.
    """
    if address != address.strip() or any(
        char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F for char in address
    ):
        return "address must not contain whitespace or control characters"
    try:
        parts = urlsplit(address)
        host = parts.hostname
        # Reading the port validates it.
        _ = parts.port
    except ValueError as error:
        return f"address is not valid: {error}"
    if parts.username is not None or parts.password is not None:
        return "address must not contain user name or password"
    if not host:
        return "address must be an absolute https:// address with a host name"
    if parts.scheme == "https":
        return None
    if allow_insecure_loopback and parts.scheme == "http" and host in _LOOPBACK_HOSTS:
        return None
    return "only https:// addresses are allowed"


def relative_path_problem(value: str, *, allow_current_dir: bool = False) -> str | None:
    """Return why ``value`` is not a clean relative POSIX path, or ``None``."""
    if allow_current_dir and value == ".":
        return None
    if value == "":
        return "path must not be empty"
    if "\\" in value or ":" in value:
        return "path must use forward slashes and must not contain ':' or '\\'"
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        return "path must not contain control characters"
    if value.startswith("/"):
        return "path must be relative"
    segments = value.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        return "path must not contain empty, '.' or '..' segments"
    return None


class _Collector:
    """Collects problems for one entry (or for the file itself)."""

    def __init__(self, problems: list[Problem], entry: str | None) -> None:
        self._problems = problems
        self.entry = entry

    def add(self, field: str, message: str) -> None:
        self._problems.append(Problem(self.entry, field, message))


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key '{key}'")
        result[key] = value
    return result


def _reject_constant(name: str) -> object:
    raise ValueError(f"'{name}' is not allowed")


def _check_keys(
    data: dict[str, object], allowed: Sequence[str], out: _Collector, prefix: str = ""
) -> None:
    for key in data:
        if key not in allowed:
            out.add(prefix + key, "unknown field")


def _required_str(
    data: dict[str, object], key: str, out: _Collector, prefix: str = ""
) -> str | None:
    """Read a mandatory, non-empty string. Reports a problem and returns ``None`` otherwise."""
    if key not in data or data[key] is None:
        out.add(prefix + key, "required field is missing")
        return None
    return _checked_str(data[key], prefix + key, out)


def _optional_str(
    data: dict[str, object], key: str, out: _Collector, prefix: str = ""
) -> str | None:
    """Read an optional string; a missing key and ``null`` both mean "not set"."""
    value = data.get(key)
    if value is None:
        return None
    return _checked_str(value, prefix + key, out)


def _checked_str(value: object, field: str, out: _Collector) -> str | None:
    if not isinstance(value, str):
        out.add(field, "must be a string")
        return None
    if value.strip() == "":
        out.add(field, "must not be empty (use null if not set)")
        return None
    if value != value.strip():
        out.add(field, "must not start or end with whitespace")
        return None
    return value


def _required_bool(
    data: dict[str, object], key: str, out: _Collector, prefix: str = ""
) -> bool | None:
    if key not in data or data[key] is None:
        out.add(prefix + key, "required field is missing")
        return None
    value = data[key]
    if not isinstance(value, bool):
        out.add(prefix + key, "must be true or false")
        return None
    return value


def _check_pattern(
    value: str | None, pattern: re.Pattern[str], field: str, message: str, out: _Collector
) -> None:
    if value is not None and pattern.fullmatch(value) is None:
        out.add(field, message)


def _check_date(value: str | None, field: str, out: _Collector) -> None:
    if value is None:
        return
    if _DATE_RE.fullmatch(value) is None:
        out.add(field, "must be a date in the form YYYY-MM-DD")
        return
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        out.add(field, "is not an existing calendar date")


def _check_address(
    value: str | None, field: str, out: _Collector, allow_insecure_loopback: bool
) -> None:
    if value is None:
        return
    message = address_problem(value, allow_insecure_loopback=allow_insecure_loopback)
    if message is not None:
        out.add(field, message)


def _parse_terms(
    data: dict[str, object], out: _Collector, allow_insecure_loopback: bool
) -> Terms | None:
    if "terms" not in data or data["terms"] is None:
        out.add("terms", "required field is missing")
        return None
    raw = data["terms"]
    if not isinstance(raw, dict):
        out.add("terms", "must be an object")
        return None
    prefix = "terms."
    _check_keys(raw, _TERMS_KEYS, out, prefix)
    holder = _required_str(raw, "holder", out, prefix)
    license_id = _required_str(raw, "license", out, prefix)
    redistribution = _required_bool(raw, "redistribution", out, prefix)
    note = _required_str(raw, "note", out, prefix)
    verified = _required_bool(raw, "verified", out, prefix)
    terms_url = _optional_str(raw, "terms_url", out, prefix)
    checked_on = _optional_str(raw, "checked_on", out, prefix)

    if license_id is not None and license_id not in NON_SPDX_LICENSES:
        _check_pattern(
            license_id,
            _SPDX_RE,
            prefix + "license",
            "must be an SPDX identifier or one of " + ", ".join(NON_SPDX_LICENSES),
            out,
        )
    _check_address(terms_url, prefix + "terms_url", out, allow_insecure_loopback)
    _check_date(checked_on, prefix + "checked_on", out)
    if verified is True and checked_on is None:
        out.add(prefix + "checked_on", "required when terms.verified is true")

    if (
        holder is None
        or license_id is None
        or redistribution is None
        or note is None
        or verified is None
    ):
        return None
    return Terms(
        holder=holder,
        license=license_id,
        redistribution=redistribution,
        note=note,
        verified=verified,
        terms_url=terms_url,
        checked_on=checked_on,
    )


def _parse_assigned_to(data: dict[str, object], out: _Collector) -> tuple[str, ...]:
    raw = data.get("assigned_to")
    if raw is None:
        return ()
    if not isinstance(raw, list):
        out.add("assigned_to", "must be a list")
        return ()
    result: list[str] = []
    for item in raw:
        checked = _checked_str(item, "assigned_to", out)
        if checked is None:
            continue
        if checked in result:
            out.add("assigned_to", f"'{checked}' is listed more than once")
            continue
        result.append(checked)
    return tuple(result)


def _parse_size(data: dict[str, object], out: _Collector) -> int | None:
    raw = data.get("size_bytes")
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        out.add("size_bytes", "must be a whole number of bytes, 0 or larger")
        return None
    return raw


def _parse_entry(
    raw: object, position: int, problems: list[Problem], allow_insecure_loopback: bool
) -> Entry | None:
    out = _Collector(problems, f"#{position}")
    if not isinstance(raw, dict):
        out.add("entries", "every entry must be an object")
        return None
    before = len(problems)

    entry_id = _required_str(raw, "id", out)
    if entry_id is not None and _ID_RE.fullmatch(entry_id) is None:
        out.add("id", "must consist of lower-case letters, digits and single hyphens")
        entry_id = None
    if entry_id is not None:
        # From here on problems are reported under the ID.
        out.entry = entry_id

    _check_keys(raw, _ENTRY_KEYS, out)
    title = _required_str(raw, "title", out)
    kind = _required_str(raw, "kind", out)
    fetch = _required_str(raw, "fetch", out)

    language = ""
    raw_language = raw.get("language")
    if raw_language is not None:
        if not isinstance(raw_language, str) or raw_language not in LANGUAGES:
            out.add("language", "must be 'de', 'en' or empty")
        else:
            language = raw_language

    if kind is not None and kind not in KINDS:
        out.add("kind", "must be one of " + ", ".join(KINDS))
        kind = None
    if fetch is not None and fetch not in FETCH_MODES:
        out.add("fetch", "must be one of " + ", ".join(FETCH_MODES))
        fetch = None

    strings: dict[str, str | None] = {
        key: _optional_str(raw, key, out)
        for key in (
            "url",
            "landing_page",
            "repository",
            "branch",
            "commit",
            "image",
            "tag",
            "digest",
            "derived_from",
            "generated_by",
            "software_version",
            "document_version",
            "version_source",
            "sha256",
            "tree_sha256",
            "target",
            "retrieved_on",
            "notes",
        )
    }
    size_bytes = _parse_size(raw, out)
    terms = _parse_terms(raw, out, allow_insecure_loopback)
    assigned_to = _parse_assigned_to(raw, out)

    for key in ("url", "landing_page", "repository"):
        _check_address(strings[key], key, out, allow_insecure_loopback)
    _check_pattern(
        strings["commit"],
        _COMMIT_RE,
        "commit",
        "must be a full commit ID (40 lower-case hexadecimal characters)",
        out,
    )
    for key in ("sha256", "tree_sha256"):
        _check_pattern(
            strings[key], _SHA256_RE, key, "must be 64 lower-case hexadecimal characters", out
        )
    _check_pattern(
        strings["digest"],
        _DIGEST_RE,
        "digest",
        "must be 'sha256:' followed by 64 lower-case hexadecimal characters",
        out,
    )
    _check_pattern(
        strings["derived_from"],
        _ID_RE,
        "derived_from",
        "must be an entry ID (lower-case letters, digits and single hyphens)",
        out,
    )
    if strings["derived_from"] is not None and strings["derived_from"] == entry_id:
        out.add("derived_from", "must not point to the entry itself")
    _check_date(strings["retrieved_on"], "retrieved_on", out)
    if strings["target"] is not None:
        message = relative_path_problem(strings["target"])
        if message is not None:
            out.add("target", message)
    if strings["commit"] is not None and strings["repository"] is None:
        out.add("repository", "required when commit is set")
    if strings["branch"] is not None and strings["repository"] is None:
        out.add("repository", "required when branch is set")

    if kind is not None:
        # A value that is present but malformed was reported above already.
        for key in _REQUIRED_BY_KIND[kind]:
            if raw.get(key) is None:
                out.add(key, f"required for kind '{kind}'")
        for key, kinds in _KINDS_BY_FIELD.items():
            if raw.get(key) is not None and kind not in kinds:
                out.add(key, f"not allowed for kind '{kind}'")
        if fetch is not None and fetch not in _FETCH_BY_KIND[kind]:
            out.add(
                "fetch",
                f"kind '{kind}' allows only: " + ", ".join(_FETCH_BY_KIND[kind]),
            )
        if kind == KIND_REFERENCE and all(
            raw.get(key) is None for key in ("url", "landing_page", "repository")
        ):
            out.add("url", "a reference needs url, landing_page or repository")
        if kind == KIND_FILE:
            # A file that a person fetches by hand (for example behind a
            # form) may have no direct address, but then it needs the page
            # on which it is offered.
            if fetch == FETCH_MANUAL:
                if raw.get("landing_page") is None:
                    out.add("landing_page", "required for kind 'file' with fetch 'manual'")
            elif raw.get("url") is None:
                out.add("url", "required for kind 'file' unless fetch is 'manual'")

    if (
        len(problems) > before
        or entry_id is None
        or title is None
        or kind is None
        or fetch is None
        or terms is None
    ):
        return None
    return Entry(
        id=entry_id,
        title=title,
        kind=kind,
        fetch=fetch,
        terms=terms,
        language=language,
        url=strings["url"],
        landing_page=strings["landing_page"],
        repository=strings["repository"],
        branch=strings["branch"],
        commit=strings["commit"],
        image=strings["image"],
        tag=strings["tag"],
        digest=strings["digest"],
        derived_from=strings["derived_from"],
        generated_by=strings["generated_by"],
        software_version=strings["software_version"],
        document_version=strings["document_version"],
        version_source=strings["version_source"],
        sha256=strings["sha256"],
        tree_sha256=strings["tree_sha256"],
        size_bytes=size_bytes,
        target=strings["target"],
        assigned_to=assigned_to,
        retrieved_on=strings["retrieved_on"],
        notes=strings["notes"],
    )


def parse_manifest(text: str, *, allow_insecure_loopback: bool = False) -> Manifest:
    """Parse and validate manifest text. Raises ``ManifestError`` with all findings."""
    try:
        data: object = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except ValueError as error:
        raise ManifestError([Problem(None, "file", f"not valid JSON notation: {error}")]) from error

    problems: list[Problem] = []
    out = _Collector(problems, None)
    if not isinstance(data, dict):
        raise ManifestError([Problem(None, "file", "top level must be an object")])
    _check_keys(data, _TOP_LEVEL_KEYS, out)

    version = data.get("schema_version")
    if version is None:
        out.add("schema_version", "required field is missing")
    elif type(version) is not int or version != SCHEMA_VERSION:
        # Deliberately strict: 1.0, "1" and true are not the integer 1.
        out.add("schema_version", f"must be the integer {SCHEMA_VERSION}")

    root = _required_str(data, "root", out)
    if root is not None:
        message = relative_path_problem(root, allow_current_dir=True)
        if message is not None:
            out.add("root", message)

    entries: list[Entry] = []
    raw_entries = data.get("entries")
    if raw_entries is None:
        out.add("entries", "required field is missing")
    elif not isinstance(raw_entries, list):
        out.add("entries", "must be a list")
    else:
        seen_ids: set[str] = set()
        seen_targets: dict[str, str] = {}
        for position, raw_entry in enumerate(raw_entries, start=1):
            # Duplicates are found on the raw values, so that they are also
            # reported for entries that have other problems.
            if isinstance(raw_entry, dict):
                raw_id = raw_entry.get("id")
                if isinstance(raw_id, str) and _ID_RE.fullmatch(raw_id) is not None:
                    if raw_id in seen_ids:
                        problems.append(
                            Problem(raw_id, "id", f"is used more than once (entry #{position})")
                        )
                    seen_ids.add(raw_id)
                    raw_target = raw_entry.get("target")
                    if isinstance(raw_target, str):
                        if raw_target in seen_targets:
                            problems.append(
                                Problem(
                                    raw_id,
                                    "target",
                                    f"is already used by entry '{seen_targets[raw_target]}'",
                                )
                            )
                        else:
                            seen_targets[raw_target] = raw_id
            entry = _parse_entry(raw_entry, position, problems, allow_insecure_loopback)
            if entry is not None:
                entries.append(entry)
        # No target may lie inside another target. Compared by path
        # segments, so "vendor/doc" and "vendor/doc-2" do not collide.
        for raw_target, owner in seen_targets.items():
            segments = raw_target.split("/")
            for length in range(1, len(segments)):
                other = seen_targets.get("/".join(segments[:length]))
                if other is not None:
                    problems.append(
                        Problem(owner, "target", f"lies inside the target of entry '{other}'")
                    )

    if problems or root is None:
        raise ManifestError(problems)
    return Manifest(schema_version=SCHEMA_VERSION, root=root, entries=tuple(entries))


def load_manifest(path: str | Path, *, allow_insecure_loopback: bool = False) -> Manifest:
    """Read and validate a manifest file.

    ``allow_insecure_loopback`` exists for tests that serve files from a local
    HTTP server. It can only be set in code; the command line never sets it.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ManifestError([Problem(None, "file", f"cannot be read: {error}")]) from error
    return parse_manifest(text, allow_insecure_loopback=allow_insecure_loopback)


def find_incomplete(manifest: Manifest) -> list[Problem]:
    """Return a problem for every entry that should have a checksum but has none.

    That is every entry with ``fetch: auto`` or ``kind: local``.
    """
    problems: list[Problem] = []
    for entry in manifest.entries:
        if entry.fetch != FETCH_AUTO and entry.kind != KIND_LOCAL:
            continue
        field = "tree_sha256" if entry.kind == KIND_GIT_ARCHIVE else "sha256"
        value = entry.tree_sha256 if entry.kind == KIND_GIT_ARCHIVE else entry.sha256
        if value is None:
            problems.append(Problem(entry.id, field, "checksum is missing"))
    return problems


def _terms_to_json(terms: Terms) -> dict[str, object]:
    return {
        "holder": terms.holder,
        "license": terms.license,
        "redistribution": terms.redistribution,
        "terms_url": terms.terms_url,
        "note": terms.note,
        "checked_on": terms.checked_on,
        "verified": terms.verified,
    }


def _entry_to_json(entry: Entry) -> dict[str, object]:
    # The order of the keys is the order in the file.
    return {
        "id": entry.id,
        "title": entry.title,
        "language": entry.language,
        "kind": entry.kind,
        "fetch": entry.fetch,
        "url": entry.url,
        "landing_page": entry.landing_page,
        "repository": entry.repository,
        "branch": entry.branch,
        "commit": entry.commit,
        "image": entry.image,
        "tag": entry.tag,
        "digest": entry.digest,
        "derived_from": entry.derived_from,
        "generated_by": entry.generated_by,
        "software_version": entry.software_version,
        "document_version": entry.document_version,
        "version_source": entry.version_source,
        "sha256": entry.sha256,
        "tree_sha256": entry.tree_sha256,
        "size_bytes": entry.size_bytes,
        "target": entry.target,
        "terms": _terms_to_json(entry.terms),
        "assigned_to": list(entry.assigned_to),
        "retrieved_on": entry.retrieved_on,
        "notes": entry.notes,
    }


def dump_manifest(manifest: Manifest) -> str:
    """Return the manifest as text in the one canonical form.

    Every field is written, in a fixed order, with two spaces of indentation,
    ``null`` for values that are not set, and a single newline at the end. The
    same manifest always gives the same text.
    """
    data: dict[str, object] = {
        "schema_version": manifest.schema_version,
        "root": manifest.root,
        "entries": [_entry_to_json(entry) for entry in manifest.entries],
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_manifest(path: str | Path, manifest: Manifest) -> None:
    """Write the manifest in canonical form (UTF-8, LF line endings)."""
    Path(path).write_bytes(dump_manifest(manifest).encode("utf-8"))


def target_path(manifest_path: str | Path, manifest: Manifest, entry: Entry) -> Path | None:
    """Return where the file or directory of ``entry`` lies, or ``None`` without target.

    ``target`` is relative to ``root``, and ``root`` is relative to the folder
    of the manifest file.
    """
    if entry.target is None:
        return None
    return root_path(manifest_path, manifest) / PurePosixPath(entry.target)


class UnsafePathError(ValueError):
    """Raised when a target would leave its root directory."""


def root_path(manifest_path: str | Path, manifest: Manifest) -> Path:
    """Return the directory that every ``target`` of ``manifest`` refers to."""
    return Path(manifest_path).parent / PurePosixPath(manifest.root)


def checked_target_path(root_dir: str | Path, target: str) -> Path:
    """Return ``root_dir / target`` after checking that it stays below ``root_dir``.

    Call this before writing to a target. Raises ``UnsafePathError`` if
    ``target`` is not a clean relative path, if any existing part of the chain
    below ``root_dir`` is a symbolic link (or a junction), or if the resolved
    path does not lie below the resolved ``root_dir``. ``root_dir`` itself is
    taken as given and resolved.
    """
    message = relative_path_problem(target)
    if message is not None:
        raise UnsafePathError(f"target '{target}': {message}")
    root = Path(root_dir)
    current = root
    for segment in target.split("/"):
        current = current / segment
        if current.is_symlink() or current.is_junction():
            raise UnsafePathError(
                f"target '{target}': '{current.relative_to(root).as_posix()}' is a symbolic link"
            )
    try:
        resolved_root = root.resolve()
        resolved = current.resolve()
    except (OSError, RuntimeError) as error:
        raise UnsafePathError(f"target '{target}': cannot be resolved: {error}") from error
    if resolved == resolved_root or not resolved.is_relative_to(resolved_root):
        raise UnsafePathError(f"target '{target}': leaves the root directory")
    return current


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 of a file as lower-case hexadecimal text."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _raise_walk_error(error: OSError) -> None:
    # os.walk skips directories it cannot list unless the error is raised.
    raise error


def tree_sha256(directory: str | Path) -> str:
    """Return the checksum of a directory tree (definition in the README).

    For every file below ``directory`` one record is built::

        <relative path, POSIX notation, UTF-8> NUL <SHA-256 of the content, hex> LF

    The records are sorted by the bytes of the path and hashed with SHA-256.
    Directories (also empty ones), time stamps and permissions do not count.
    Symbolic links are never followed; a link counts as a file whose content
    is the link target as UTF-8 text. A directory that cannot be read raises
    ``OSError``; it is never skipped silently.
    """
    base = Path(directory)
    if not base.is_dir():
        raise ValueError(f"not a directory: {base}")
    records: list[tuple[bytes, str]] = []
    for current, dir_names, file_names in os.walk(
        base, followlinks=False, onerror=_raise_walk_error
    ):
        current_path = Path(current)
        for name in [*dir_names, *file_names]:
            path = current_path / name
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                continue
            if stat.S_ISLNK(mode):
                content_hash = hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
            elif stat.S_ISREG(mode):
                content_hash = file_sha256(path)
            else:
                raise ValueError(f"not a regular file, directory or link: {path}")
            relative = path.relative_to(base).as_posix().encode("utf-8")
            records.append((relative, content_hash))
    records.sort()
    digest = hashlib.sha256()
    for relative, content_hash in records:
        digest.update(relative + b"\0" + content_hash.encode("ascii") + b"\n")
    return digest.hexdigest()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m testfactory.manifest_tools",
        description="Tools for test factory manifest files.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check the format of a manifest file")
    check.add_argument(
        "--complete",
        action="store_true",
        help="also fail if an entry with 'fetch: auto' or 'kind: local' has no checksum",
    )
    check.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_MANIFEST_PATH,
        help=f"manifest file (default: {DEFAULT_MANIFEST_PATH})",
    )
    formatter = commands.add_parser(
        "format",
        help="rewrite a manifest file in the canonical form (content unchanged)",
    )
    formatter.add_argument(
        "--check",
        action="store_true",
        help="do not write; fail if the file is not in the canonical form",
    )
    formatter.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_MANIFEST_PATH,
        help=f"manifest file (default: {DEFAULT_MANIFEST_PATH})",
    )
    return parser


def _report_invalid(path: str, error: ManifestError) -> int:
    for problem in error.problems:
        print(f"{path}: {problem}", file=sys.stderr)
    print(f"{path}: INVALID ({len(error.problems)} problem(s))", file=sys.stderr)
    return 1


def _format_command(path: str, check_only: bool) -> int:
    """Bring a manifest file into the canonical form. Returns the exit code."""
    try:
        # Read as bytes: the canonical form also fixes the line endings.
        # Deliberately without allow_insecure_loopback, as in ``check``.
        original = Path(path).read_bytes()
        manifest = parse_manifest(original.decode("utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        return _report_invalid(
            path, ManifestError([Problem(None, "file", f"cannot be read: {error}")])
        )
    except ManifestError as error:
        return _report_invalid(path, error)
    if dump_manifest(manifest).encode("utf-8") == original:
        print(f"{path}: already in canonical form")
        return 0
    if check_only:
        print(f"{path}: NOT in canonical form", file=sys.stderr)
        return 1
    write_manifest(path, manifest)
    print(f"{path}: rewritten in canonical form")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line. Returns the exit code."""
    arguments = _build_parser().parse_args(argv)
    path: str = arguments.path
    if arguments.command == "format":
        check_only: bool = arguments.check
        return _format_command(path, check_only)
    complete: bool = arguments.complete
    try:
        # Deliberately without allow_insecure_loopback: the command line
        # accepts https:// only.
        manifest = load_manifest(path)
    except ManifestError as error:
        return _report_invalid(path, error)
    if complete:
        incomplete = find_incomplete(manifest)
        if incomplete:
            for problem in incomplete:
                print(f"{path}: {problem}", file=sys.stderr)
            print(f"{path}: INCOMPLETE ({len(incomplete)} problem(s))", file=sys.stderr)
            return 1
    count = len(manifest.entries)
    print(f"{path}: OK ({count} {'entry' if count == 1 else 'entries'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
