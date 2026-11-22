"""Search probes: how well the search finds the places a question expects (056, 120).

A probe is a query in own words and the places that answer it: the manifest
entry of the test factory (``manifest_id``), the SHA-256 of the file and
either the pages (a PDF or Office file) or the heading path (a Markdown file
of a repository, which has neither pages nor lines, E-55; then ``path`` names
the file in the repository), optionally the key of the device the place must
be stored at. A probe list holds references only, never text from a document
(``twox/search/probes/m2.json``, ``m3.json``).

Each probe is measured three ways, through the search interface:

* **keyword:** the search without the vector search for this one request
  (``SearchRequest.keyword_only``), i.e. full-text and exact search with
  their own ranking; the model is not asked;
* **vector:** the nearest sections only (:func:`~twox.search.postgres.embed_query`
  and :func:`~twox.search.postgres.nearest_sections`), with the AI features on;
* **combined:** the search as users get it (:func:`~twox.search.interface.get_search_backend`).

Without the AI features only the keyword search is measured; vector and
combined are reported as not measured, and the model service is never asked.
When the model service fails for a probe, its vector and combined results are
not measured either, since the search fell back to the keyword search.

Per probe and kind: the rank of the first correct entry within the first
:data:`DEPTH` entries, the number of correct entries among the first k for
every cut-off k (5 and 10 unless others are asked for), the reciprocal rank,
the time taken and, per expected place (a page or a heading path of a manual;
the other language edition of the manual counts for the same page, E-61), the
rank of the first entry that stands for it. An entry is correct when one of
its places has the expected checksum and, if the probe names one, the
expected device, and either a page in the expected pages or a heading path
that starts with the expected one (compared without regard to case and runs
of white space). Per kind: Recall@k for every cut-off (share of measured
probes with a correct entry among the first k), MRR (mean reciprocal rank, 0
for a probe without a correct entry) and the times.

A control probe (id ``control-…``, empty list of expected places) asks for
something no document answers. It is searched but not judged: it counts in
neither Recall nor MRR, and the report lists the identifiers of its first
:data:`CONTROL_ENTRIES` entries per kind instead.

A probe whose files are not ingested (no document version with the expected
checksum has sections) counts as "not ingested", not as a failure of the
search; it is not searched at all. When only some of its files are ingested,
the probe is measured against those, and the others are named.

The report holds ranks, pages, checksums and identifiers only, never the
text of a section or a snippet. Without other cut-offs it is the same as
before work order 120; asked for cut-offs (``evaluate(..., cutoffs=...)``),
it also holds the counts and Recall per cut-off and the ranks per expected
place.
"""

import json
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import connection

from twox.files.models import DocumentKind, DocumentVersion
from twox.ingest.models import Section
from twox.search.interface import (
    MAX_QUERY_LENGTH,
    SearchBackend,
    SearchRequest,
    SearchResult,
    get_search_backend,
)
from twox.search.postgres import VECTOR_CANDIDATES, embed_query, nearest_sections

#: Version of the probe list format.
SCHEMA_VERSION = 1
#: Entries per list that are looked at: as many as the vector search contributes.
DEPTH = VECTOR_CANDIDATES
#: The cut-offs of Recall@k and of the counts per probe, unless others are asked for.
CUTOFFS = (5, 10)
#: Entries per kind listed for a control probe.
CONTROL_ENTRIES = 10
#: Id prefix of a control probe, the only kind of probe without expected places.
CONTROL_PREFIX = "control-"
#: Limits of a heading path in a probe list, so that no text extract lands there.
MAX_HEADING_LEVELS = 8
MAX_HEADING_LENGTH = 120
#: Limit of the path of a file in a repository archive.
MAX_PATH_LENGTH = 200
#: Directory of the probe lists that ship with the application.
PROBE_LISTS = Path(__file__).resolve().parent / "probes"

#: Why a kind was not measured.
AI_DISABLED_NOTE = "AI features not enabled"
MODEL_FAILED_NOTE = "model service not available, keyword search only"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_PROBE_LIST_NAME = re.compile(r"[a-z0-9-]+")
_WHOLE_NUMBER = re.compile(r"[0-9]+")
_TOP_KEYS = frozenset({"schema_version", "notes", "probes"})
_PROBE_KEYS = frozenset({"id", "query", "expected", "basis", "notes"})
_EXPECTED_KEYS = frozenset({"manifest_id", "sha256", "pages", "heading_path", "path", "device"})
#: Basis key of places in the other language edition of a documented manual (E-61).
_OTHER_EDITION = "other_language_edition"


class ProbeFormatError(ValueError):
    """The probe list is not valid; the message names the place."""


class SearchKind(StrEnum):
    """Which list of the search is measured."""

    KEYWORD = "keyword"
    VECTOR = "vector"
    COMBINED = "combined"


class ProbeStatus(StrEnum):
    """Whether a probe was searched."""

    MEASURED = "measured"
    NOT_INGESTED = "not_ingested"
    #: A control probe: searched, not judged.
    CONTROL = "control"


@dataclass(frozen=True, slots=True)
class ExpectedPlace:
    """A place that answers a probe: pages of a file, or a heading path in a file."""

    manifest_id: str
    sha256: str
    #: Empty when the place is given by :attr:`heading_path`.
    pages: frozenset[int]
    #: Key of the device the place must be stored at; ``None`` for any device.
    device: str | None = None
    #: Headings from the top; a section matches when its path starts with these.
    heading_path: tuple[str, ...] | None = None
    #: Path of the file in the repository archive (with :attr:`heading_path` only).
    path: str | None = None


@dataclass(frozen=True, slots=True)
class Probe:
    """A query and the places that answer it; no places for a control probe."""

    id: str
    query: str
    expected: tuple[ExpectedPlace, ...]
    #: Manifest id of a place in another language edition -> id of the documented place.
    editions: tuple[tuple[str, str], ...] = ()

    @property
    def is_control(self) -> bool:
        """Whether the probe expects no place (a control probe)."""
        return not self.expected


@dataclass(frozen=True, slots=True)
class Place:
    """Where an entry of a result list is stored."""

    sha256: str
    page_start: int | None
    page_end: int | None
    device_key: str
    heading_path: tuple[str, ...] = ()
    section_id: int | None = None
    version_id: int | None = None


#: One entry of a result list: the places it is stored at.
Entry = Sequence[Place]


@dataclass(frozen=True, slots=True)
class PlaceRank:
    """The first rank of an entry that stands for one expected place."""

    #: The documented manual (the other language edition counts for it).
    manifest_id: str
    #: The page, or ``None`` for a place given by heading path.
    page: int | None
    heading_path: list[str] | None
    #: From 1; ``None`` when no entry within :data:`DEPTH` stands for the place.
    first_rank: int | None


@dataclass(frozen=True, slots=True)
class KindResult:
    """The outcome of one probe in one kind of search."""

    kind: SearchKind
    measured: bool
    #: Why it was not measured; ``None`` when measured.
    note: str | None = None
    #: Rank of the first correct entry, from 1; ``None`` when none is within :data:`DEPTH`.
    first_rank: int | None = None
    #: Correct entries among the first 5 and the first 10.
    correct_in_top_5: int = 0
    correct_in_top_10: int = 0
    #: ``1 / first_rank``, or 0.
    reciprocal_rank: float = 0.0
    #: Manifest entry and pages of the first correct entry.
    first_manifest_id: str | None = None
    first_pages: str | None = None
    seconds: float = 0.0
    #: Correct entries among the first k, per cut-off k (as text, for JSON).
    correct_in_top: dict[str, int] = field(default_factory=dict)
    #: The first rank per expected place.
    place_ranks: list[PlaceRank] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ControlPlace:
    """Identifiers of one place of an entry listed for a control probe."""

    section_id: int | None
    version_id: int | None
    sha256: str
    pages: str | None
    device_key: str


@dataclass(frozen=True, slots=True)
class ControlEntry:
    """One entry listed for a control probe: its rank and places."""

    rank: int
    places: list[ControlPlace]


@dataclass(frozen=True, slots=True)
class ControlList:
    """The first entries of one kind of search for a control probe."""

    kind: SearchKind
    measured: bool
    note: str | None = None
    entries: list[ControlEntry] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """The outcome of one probe."""

    probe_id: str
    status: ProbeStatus
    #: Manifest entries of expected places whose file is not ingested.
    not_ingested: list[str] = field(default_factory=list)
    kinds: list[KindResult] = field(default_factory=list)
    #: The first entries per kind, for a control probe only.
    controls: list[ControlList] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class KindSummary:
    """The totals of one kind over all measured probes."""

    kind: SearchKind
    measured: int
    not_measured: int
    #: ``None`` when no probe was measured.
    recall_at_5: float | None
    recall_at_10: float | None
    mrr: float | None
    total_seconds: float
    mean_seconds: float | None
    #: Recall@k per cut-off k (as text, for JSON).
    recall_at: dict[str, float | None] = field(default_factory=dict)


#: Keys of the report that appear only when cut-offs were asked for.
_EXTENDED_KIND_KEYS = ("correct_in_top", "place_ranks")
_EXTENDED_SUMMARY_KEYS = ("recall_at",)


@dataclass(frozen=True, slots=True)
class Report:
    """The outcome of a probe list."""

    ai_enabled: bool
    #: Embedding model of the vector search; ``None`` without AI features.
    model: str | None
    section_max_chars: int
    depth: int
    probes: list[ProbeResult]
    summaries: list[KindSummary]
    #: The cut-offs of the counts and of Recall.
    cutoffs: list[int] = field(default_factory=lambda: list(CUTOFFS))
    #: Whether cut-offs were asked for: then the report also holds counts and
    #: Recall per cut-off and the ranks per expected place.
    extended: bool = False

    @property
    def not_ingested_count(self) -> int:
        """Probes that were not searched because none of their files is ingested."""
        return sum(probe.status is ProbeStatus.NOT_INGESTED for probe in self.probes)

    def as_dict(self) -> dict[str, Any]:
        """The report as plain data for JSON; without cut-offs as before work order 120."""
        data = asdict(self)
        del data["extended"]
        if not self.extended:
            del data["cutoffs"]
            for summary in data["summaries"]:
                for key in _EXTENDED_SUMMARY_KEYS:
                    del summary[key]
        for probe in data["probes"]:
            if not probe["controls"]:
                del probe["controls"]
            if not self.extended:
                for kind in probe["kinds"]:
                    for key in _EXTENDED_KIND_KEYS:
                        del kind[key]
        data["not_ingested_count"] = self.not_ingested_count
        return data


# --- Reading the probe list -------------------------------------------------


def _object(value: object, where: str, allowed: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ProbeFormatError(f"{where}: expected an object")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ProbeFormatError(f"{where}: unknown key(s): {', '.join(unknown)}")
    return value


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProbeFormatError(f"{where}: expected non-empty text")
    return value


def _pages(value: object, where: str) -> frozenset[int]:
    if not isinstance(value, list) or not value:
        raise ProbeFormatError(f"{where}: expected a non-empty list of page numbers")
    for index, page in enumerate(value):
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ProbeFormatError(f"{where}[{index}]: expected a page number from 1")
    return frozenset(value)


def _heading_path(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ProbeFormatError(f"{where}: expected a non-empty list of headings")
    if len(value) > MAX_HEADING_LEVELS:
        raise ProbeFormatError(f"{where}: at most {MAX_HEADING_LEVELS} headings")
    headings = tuple(_text(heading, f"{where}[{index}]") for index, heading in enumerate(value))
    for index, heading in enumerate(headings):
        if len(heading) > MAX_HEADING_LENGTH:
            raise ProbeFormatError(f"{where}[{index}]: longer than {MAX_HEADING_LENGTH} characters")
    return headings


def _repository_path(value: object, where: str) -> str:
    path = _text(value, where)
    if len(path) > MAX_PATH_LENGTH:
        raise ProbeFormatError(f"{where}: longer than {MAX_PATH_LENGTH} characters")
    parts = path.split("/")
    if "\\" in path or any(part in ("", ".", "..") for part in parts):
        raise ProbeFormatError(
            f"{where}: expected a relative path with '/', without '..', '.' or empty parts"
        )
    return path


def _expected_place(value: object, where: str) -> ExpectedPlace:
    data = _object(value, where, _EXPECTED_KEYS)
    sha256 = _text(data.get("sha256"), f"{where}.sha256")
    if _SHA256.fullmatch(sha256) is None:
        raise ProbeFormatError(f"{where}.sha256: expected 64 lower-case hexadecimal characters")
    by_pages = "pages" in data
    if by_pages == ("heading_path" in data):
        raise ProbeFormatError(f"{where}: expected exactly one of pages and heading_path")
    heading_path: tuple[str, ...] | None = None
    path: str | None = None
    if by_pages:
        if "path" in data:
            raise ProbeFormatError(f"{where}.path: only with heading_path, not with pages")
        pages = _pages(data.get("pages"), f"{where}.pages")
    else:
        if "path" not in data:
            raise ProbeFormatError(f"{where}.path: required with heading_path")
        pages = frozenset()
        heading_path = _heading_path(data.get("heading_path"), f"{where}.heading_path")
        path = _repository_path(data.get("path"), f"{where}.path")
    device = data.get("device")
    return ExpectedPlace(
        manifest_id=_text(data.get("manifest_id"), f"{where}.manifest_id"),
        sha256=sha256,
        pages=pages,
        device=None if device is None else _text(device, f"{where}.device"),
        heading_path=heading_path,
        path=path,
    )


def _editions(value: object, where: str) -> tuple[tuple[str, str], ...]:
    """The mapping of other language editions in the basis of a probe, if any."""
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise ProbeFormatError(f"{where}: expected an object")
    editions = value.get(_OTHER_EDITION)
    if editions is None:
        return ()
    edition_where = f"{where}.{_OTHER_EDITION}"
    if not isinstance(editions, dict):
        raise ProbeFormatError(f"{edition_where}: expected an object of manifest ids")
    return tuple(
        (_text(edition, edition_where), _text(documented, f"{edition_where}.{edition}"))
        for edition, documented in editions.items()
    )


def _probe(value: object, where: str) -> Probe:
    data = _object(value, where, _PROBE_KEYS)
    query = _text(data.get("query"), f"{where}.query")
    if len(query) > MAX_QUERY_LENGTH:
        raise ProbeFormatError(f"{where}.query: longer than {MAX_QUERY_LENGTH} characters")
    probe_id = _text(data.get("id"), f"{where}.id")
    control = probe_id.startswith(CONTROL_PREFIX)
    expected = data.get("expected")
    if not isinstance(expected, list) or (not expected and not control):
        raise ProbeFormatError(
            f"{where}.expected: expected a non-empty list of places (an empty list only"
            f" for a control probe, whose id starts with {CONTROL_PREFIX!r})"
        )
    if control and expected:
        raise ProbeFormatError(
            f"{where}.expected: a control probe (id {CONTROL_PREFIX}…) expects no place;"
            " expected an empty list"
        )
    return Probe(
        id=probe_id,
        query=query,
        expected=tuple(
            _expected_place(place, f"{where}.expected[{index}]")
            for index, place in enumerate(expected)
        ),
        editions=_editions(data.get("basis"), f"{where}.basis"),
    )


def parse_probes(data: object) -> list[Probe]:
    """The probes of a probe list read from JSON; :class:`ProbeFormatError` if invalid."""
    top = _object(data, "probe list", _TOP_KEYS)
    if top.get("schema_version") != SCHEMA_VERSION:
        raise ProbeFormatError(f"schema_version: expected {SCHEMA_VERSION}")
    probes = top.get("probes")
    if not isinstance(probes, list) or not probes:
        raise ProbeFormatError("probes: expected a non-empty list of probes")
    parsed = [_probe(probe, f"probes[{index}]") for index, probe in enumerate(probes)]
    seen: set[str] = set()
    for probe in parsed:
        if probe.id in seen:
            raise ProbeFormatError(f"probes: the id {probe.id!r} occurs twice")
        seen.add(probe.id)
    return parsed


def load_probes(text: str) -> list[Probe]:
    """The probes of a probe list in JSON text; :class:`ProbeFormatError` if invalid."""
    if not text.strip():
        raise ProbeFormatError("the input is empty; expected a probe list in JSON")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProbeFormatError(
            f"not valid JSON (line {error.lineno}, column {error.colno}: {error.msg})"
        ) from None
    return parse_probes(data)


def probe_list_text(name: str) -> str:
    """The text of the probe list ``name`` of the application (``probes/<name>.json``).

    :class:`ValueError` when the name is not made of lower-case letters,
    digits and ``-``, or when there is no such list.
    """
    if _PROBE_LIST_NAME.fullmatch(name) is None:
        raise ValueError(
            f"{name!r} is not a probe list name (lower-case letters, digits and '-' only)"
        )
    path = PROBE_LISTS / f"{name}.json"
    if not path.is_file():
        known = ", ".join(sorted(file.stem for file in PROBE_LISTS.glob("*.json")))
        raise ValueError(f"there is no probe list {name!r} (known: {known})")
    return path.read_text(encoding="utf-8")


def parse_cutoffs(text: str) -> tuple[int, ...]:
    """The cut-offs in ``text`` ("5,8,10,12"): whole numbers from 1 to :data:`DEPTH`, ascending.

    :class:`ValueError` with a message otherwise.
    """
    cutoffs: list[int] = []
    for part in text.split(","):
        value = part.strip()
        if _WHOLE_NUMBER.fullmatch(value) is None:
            raise ValueError(f"{value!r} is not a whole number")
        cutoff = int(value)
        if not 1 <= cutoff <= DEPTH:
            raise ValueError(f"{cutoff} is not between 1 and {DEPTH}")
        if cutoff in cutoffs:
            raise ValueError(f"{cutoff} occurs twice")
        if cutoffs and cutoff < cutoffs[-1]:
            raise ValueError(f"{cutoff} comes after {cutoffs[-1]}; expected ascending numbers")
        cutoffs.append(cutoff)
    return tuple(cutoffs)


# --- Judging a result list --------------------------------------------------


#: An expected place as counted per place: manual, page or heading path.
_PlaceKey = tuple[str, int | None, tuple[str, ...] | None]


def _pages_text(start: int | None, end: int | None) -> str | None:
    if start is None:
        return None
    return str(start) if end is None or end == start else f"{start}-{end}"


def _normal_heading(heading: str) -> str:
    return " ".join(heading.split()).casefold()


def _starts_with(path: Sequence[str], prefix: Sequence[str]) -> bool:
    if len(prefix) > len(path):
        return False
    return all(
        _normal_heading(have) == _normal_heading(want)
        for have, want in zip(path, prefix, strict=False)
    )


def _matches(place: Place, candidate: ExpectedPlace) -> bool:
    if candidate.sha256 != place.sha256:
        return False
    if candidate.device is not None and candidate.device != place.device_key:
        return False
    if candidate.heading_path is not None:
        return _starts_with(place.heading_path, candidate.heading_path)
    if place.page_start is None:
        return False
    page_end = place.page_end if place.page_end is not None else place.page_start
    return any(place.page_start <= page <= page_end for page in candidate.pages)


def matching_place(place: Place, expected: Iterable[ExpectedPlace]) -> ExpectedPlace | None:
    """The expected place ``place`` stands for, or ``None``."""
    for candidate in expected:
        if _matches(place, candidate):
            return candidate
    return None


def _keys_of(candidate: ExpectedPlace, editions: Mapping[str, str]) -> list[_PlaceKey]:
    manifest_id = editions.get(candidate.manifest_id, candidate.manifest_id)
    if candidate.heading_path is not None:
        return [(manifest_id, None, candidate.heading_path)]
    return [(manifest_id, page, None) for page in sorted(candidate.pages)]


def _keys_covered(
    place: Place, candidate: ExpectedPlace, editions: Mapping[str, str]
) -> list[_PlaceKey]:
    """The expected places of ``candidate`` that ``place`` stands for."""
    if not _matches(place, candidate):
        return []
    keys = _keys_of(candidate, editions)
    if candidate.heading_path is not None or place.page_start is None:
        return keys
    page_end = place.page_end if place.page_end is not None else place.page_start
    return [key for key in keys if key[1] is not None and place.page_start <= key[1] <= page_end]


def judge(
    kind: SearchKind,
    entries: Sequence[Entry],
    expected: Sequence[ExpectedPlace],
    seconds: float,
    cutoffs: Sequence[int] = CUTOFFS,
    editions: Mapping[str, str] | None = None,
) -> KindResult:
    """Rank, counts and reciprocal rank of ``entries`` (best first) against ``expected``.

    ``editions`` maps the manifest id of another language edition to the
    documented one, so that both count for the same place in the ranks per place.
    """
    editions = editions or {}
    first_rank: int | None = None
    first_manifest_id: str | None = None
    first_pages: str | None = None
    correct_ranks: list[int] = []
    first_by_place: dict[_PlaceKey, int] = {}
    for rank, entry in enumerate(entries[:DEPTH], start=1):
        for place in entry:
            for candidate in expected:
                for key in _keys_covered(place, candidate, editions):
                    first_by_place.setdefault(key, rank)
        for place in entry:
            found = matching_place(place, expected)
            if found is None:
                continue
            correct_ranks.append(rank)
            if first_rank is None:
                first_rank = rank
                first_manifest_id = found.manifest_id
                first_pages = _pages_text(place.page_start, place.page_end)
            break
    top_5, top_10 = CUTOFFS
    places = dict.fromkeys(key for candidate in expected for key in _keys_of(candidate, editions))
    return KindResult(
        kind=kind,
        measured=True,
        first_rank=first_rank,
        correct_in_top_5=sum(rank <= top_5 for rank in correct_ranks),
        correct_in_top_10=sum(rank <= top_10 for rank in correct_ranks),
        reciprocal_rank=0.0 if first_rank is None else 1.0 / first_rank,
        first_manifest_id=first_manifest_id,
        first_pages=first_pages,
        seconds=seconds,
        correct_in_top={
            str(cutoff): sum(rank <= cutoff for rank in correct_ranks) for cutoff in cutoffs
        },
        place_ranks=[
            PlaceRank(
                manifest_id=manifest_id,
                page=page,
                heading_path=None if heading_path is None else list(heading_path),
                first_rank=first_by_place.get((manifest_id, page, heading_path)),
            )
            for manifest_id, page, heading_path in places
        ],
    )


def summarise(
    kind: SearchKind, results: Iterable[KindResult], cutoffs: Sequence[int] = CUTOFFS
) -> KindSummary:
    """Recall@k per cut-off, MRR and times of ``kind`` over the measured results."""
    of_kind = [result for result in results if result.kind is kind]
    measured = [result for result in of_kind if result.measured]
    count = len(measured)
    total_seconds = sum(result.seconds for result in measured)
    top_5, top_10 = CUTOFFS

    def share(cutoff: int) -> float | None:
        if not count:
            return None
        found = sum(r.first_rank is not None and r.first_rank <= cutoff for r in measured)
        return found / count

    return KindSummary(
        kind=kind,
        measured=count,
        not_measured=len(of_kind) - count,
        recall_at_5=share(top_5),
        recall_at_10=share(top_10),
        mrr=sum(result.reciprocal_rank for result in measured) / count if count else None,
        total_seconds=total_seconds,
        mean_seconds=total_seconds / count if count else None,
        recall_at={str(cutoff): share(cutoff) for cutoff in cutoffs},
    )


# --- Running the probes -----------------------------------------------------


def ingested_checksums(checksums: Iterable[str]) -> set[str]:
    """Those of ``checksums`` that a searchable document version with sections has."""
    return set(
        DocumentVersion.objects.filter(
            sha256__in=set(checksums),
            document__kind=DocumentKind.DOCUMENT,
            sections__isnull=False,
        )
        .values_list("sha256", flat=True)
        .distinct()
    )


def hit_entries(result: SearchResult) -> list[list[Place]]:
    """The hits of ``result`` as entries, best first."""
    version_ids = {location.version_id for hit in result.hits for location in hit.locations}
    checksums = dict(DocumentVersion.objects.filter(pk__in=version_ids).values_list("pk", "sha256"))
    return [
        [
            Place(
                sha256=checksums[location.version_id],
                page_start=hit.page_start,
                page_end=hit.page_end,
                device_key=location.device_key,
                heading_path=tuple(hit.heading_path),
                section_id=location.section_id,
                version_id=location.version_id,
            )
            for location in hit.locations
        ]
        for hit in result.hits
    ]


def vector_entries(nearest: Sequence[tuple[int, int]]) -> list[list[Place]]:
    """The nearest sections as entries; sections of equal rank (same distance) are one entry."""
    rows = Section.objects.filter(pk__in=[section_id for section_id, _ in nearest]).values_list(
        "pk",
        "page_start",
        "page_end",
        "heading_path",
        "document_version_id",
        "document_version__sha256",
        "document_version__document__device__key",
    )
    places = {
        pk: Place(
            sha256=sha256,
            page_start=start,
            page_end=end,
            device_key=device_key,
            heading_path=tuple(headings or ()),
            section_id=pk,
            version_id=version_id,
        )
        for pk, start, end, headings, version_id, sha256, device_key in rows
    }
    entries: dict[int, list[Place]] = {}
    for section_id, rank in nearest:
        place = places.get(section_id)
        if place is not None:
            entries.setdefault(rank, []).append(place)
    return [entries[rank] for rank in sorted(entries)]


def control_list(kind: SearchKind, entries: Sequence[Entry]) -> ControlList:
    """The identifiers of the first :data:`CONTROL_ENTRIES` entries, no text."""
    return ControlList(
        kind=kind,
        measured=True,
        entries=[
            ControlEntry(
                rank=rank,
                places=[
                    ControlPlace(
                        section_id=place.section_id,
                        version_id=place.version_id,
                        sha256=place.sha256,
                        pages=_pages_text(place.page_start, place.page_end),
                        device_key=place.device_key,
                    )
                    for place in entry
                ],
            )
            for rank, entry in enumerate(entries[:CONTROL_ENTRIES], start=1)
        ],
    )


def _not_measured(kind: SearchKind, note: str) -> KindResult:
    return KindResult(kind=kind, measured=False, note=note)


class _Runner:
    """Measures the probes one after the other."""

    def __init__(
        self, backend: SearchBackend, clock: Callable[[], float], cutoffs: Sequence[int]
    ) -> None:
        self.backend = backend
        self.clock = clock
        self.cutoffs = cutoffs
        self.ai_enabled = bool(settings.TWOX_AI_ENABLED)
        self.model: str | None = None

    def keyword_entries(self, request: SearchRequest) -> list[list[Place]]:
        # This one request without the vector search; the model is not asked.
        return hit_entries(self.backend.search(replace(request, keyword_only=True)))

    def vector_entries(self, request: SearchRequest) -> list[list[Place]] | None:
        """The nearest sections; ``None`` when the model service failed."""
        embedded = embed_query(request.query)
        if embedded is None:
            return None
        model, vector = embedded
        self.model = model
        with connection.cursor() as cursor:
            nearest = nearest_sections(cursor, request, model, vector)
        return vector_entries(nearest)

    def combined_entries(self, request: SearchRequest) -> list[list[Place]] | None:
        """The hits of the search; ``None`` when it fell back to the keyword search."""
        result = self.backend.search(request)
        if not result.semantic_used:
            return None
        return hit_entries(result)

    def judged(
        self,
        kind: SearchKind,
        entries: Sequence[Entry] | None,
        probe: Probe,
        expected: Sequence[ExpectedPlace],
        seconds: float,
    ) -> KindResult:
        if entries is None:
            return _not_measured(kind, MODEL_FAILED_NOTE)
        return judge(kind, entries, expected, seconds, self.cutoffs, dict(probe.editions))

    def probe(self, probe: Probe, ingested: set[str]) -> ProbeResult:
        if probe.is_control:
            return self.control(probe)
        present = [place for place in probe.expected if place.sha256 in ingested]
        missing = sorted(
            {place.manifest_id for place in probe.expected if place.sha256 not in ingested}
        )
        if not present:
            return ProbeResult(
                probe_id=probe.id, status=ProbeStatus.NOT_INGESTED, not_ingested=missing
            )
        request = SearchRequest(query=probe.query, limit=DEPTH)
        kinds: list[KindResult] = []
        started = self.clock()
        keyword = self.keyword_entries(request)
        kinds.append(
            self.judged(SearchKind.KEYWORD, keyword, probe, present, self.clock() - started)
        )
        if self.ai_enabled:
            started = self.clock()
            vector = self.vector_entries(request)
            kinds.append(
                self.judged(SearchKind.VECTOR, vector, probe, present, self.clock() - started)
            )
            started = self.clock()
            combined = self.combined_entries(request)
            kinds.append(
                self.judged(SearchKind.COMBINED, combined, probe, present, self.clock() - started)
            )
        else:
            kinds += [
                _not_measured(SearchKind.VECTOR, AI_DISABLED_NOTE),
                _not_measured(SearchKind.COMBINED, AI_DISABLED_NOTE),
            ]
        return ProbeResult(
            probe_id=probe.id, status=ProbeStatus.MEASURED, not_ingested=missing, kinds=kinds
        )

    def control(self, probe: Probe) -> ProbeResult:
        """Search a control probe and list the identifiers of its first entries."""
        request = SearchRequest(query=probe.query, limit=DEPTH)
        lists = [control_list(SearchKind.KEYWORD, self.keyword_entries(request))]
        if self.ai_enabled:
            for kind, entries in (
                (SearchKind.VECTOR, self.vector_entries(request)),
                (SearchKind.COMBINED, self.combined_entries(request)),
            ):
                lists.append(
                    ControlList(kind=kind, measured=False, note=MODEL_FAILED_NOTE)
                    if entries is None
                    else control_list(kind, entries)
                )
        else:
            lists += [
                ControlList(kind=SearchKind.VECTOR, measured=False, note=AI_DISABLED_NOTE),
                ControlList(kind=SearchKind.COMBINED, measured=False, note=AI_DISABLED_NOTE),
            ]
        return ProbeResult(probe_id=probe.id, status=ProbeStatus.CONTROL, controls=lists)


def evaluate(
    probes: Sequence[Probe],
    backend: SearchBackend | None = None,
    clock: Callable[[], float] = time.perf_counter,
    cutoffs: Sequence[int] | None = None,
) -> Report:
    """Measure ``probes`` against the ingested documents.

    ``cutoffs`` (see :func:`parse_cutoffs`) replaces 5 and 10 and adds the
    counts and Recall per cut-off and the ranks per expected place to the report.
    """
    used = tuple(cutoffs) if cutoffs is not None else CUTOFFS
    runner = _Runner(backend or get_search_backend(), clock, used)
    ingested = ingested_checksums(place.sha256 for probe in probes for place in probe.expected)
    results = [runner.probe(probe, ingested) for probe in probes]
    all_kinds = [kind for result in results for kind in result.kinds]
    model = runner.model
    if model is None and runner.ai_enabled:
        model = str(settings.TWOX_EMBED_MODEL)
    return Report(
        ai_enabled=runner.ai_enabled,
        model=model,
        section_max_chars=int(settings.TWOX_SECTION_MAX_CHARS),
        depth=DEPTH,
        probes=results,
        summaries=[summarise(kind, all_kinds, used) for kind in SearchKind],
        cutoffs=list(used),
        extended=cutoffs is not None,
    )


# --- Output -----------------------------------------------------------------


def _number(value: float | None, digits: int = 3) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _milliseconds(seconds: float | None) -> str:
    return "-" if seconds is None else f"{seconds * 1000:.0f}"


def _row(cells: Sequence[str], widths: Sequence[int]) -> str:
    return "  ".join(cell.ljust(width) for cell, width in zip(cells, widths, strict=True)).rstrip()


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    widths = [max(len(row[column]) for row in [header, *rows]) for column in range(len(header))]
    return [_row(header, widths), *(_row(row, widths) for row in rows)]


def _correct_counts(report: Report, result: KindResult) -> list[str]:
    if not report.extended:
        return [str(result.correct_in_top_5), str(result.correct_in_top_10)]
    return [str(result.correct_in_top[str(cutoff)]) for cutoff in report.cutoffs]


def _recalls(report: Report, summary: KindSummary) -> list[str]:
    if not report.extended:
        return [_number(summary.recall_at_5), _number(summary.recall_at_10)]
    return [_number(summary.recall_at[str(cutoff)]) for cutoff in report.cutoffs]


def _place_text(place: PlaceRank) -> str:
    if place.heading_path is not None:
        return f"{place.manifest_id}: {' > '.join(place.heading_path)}"
    return f"{place.manifest_id} p. {place.page}"


def _probe_rows(report: Report) -> list[list[str]]:
    blanks = ["-"] * len(report.cutoffs)
    rows: list[list[str]] = []
    for probe in report.probes:
        if probe.status is ProbeStatus.CONTROL:
            rows.append([probe.probe_id, "-", "control, not judged", "-", *blanks, "-", "-", ""])
            continue
        if probe.status is ProbeStatus.NOT_INGESTED:
            rows.append(
                [
                    probe.probe_id,
                    "-",
                    "not ingested",
                    "-",
                    *blanks,
                    "-",
                    "-",
                    ", ".join(probe.not_ingested),
                ]
            )
            continue
        for result in probe.kinds:
            if not result.measured:
                rows.append(
                    [
                        probe.probe_id,
                        result.kind,
                        f"not measured: {result.note}",
                        "-",
                        *blanks,
                        "-",
                        "-",
                        "",
                    ]
                )
                continue
            first = (
                f"{result.first_manifest_id} p. {result.first_pages}"
                if result.first_rank is not None
                else "none"
            )
            rows.append(
                [
                    probe.probe_id,
                    result.kind,
                    "measured",
                    "-" if result.first_rank is None else str(result.first_rank),
                    *_correct_counts(report, result),
                    _number(result.reciprocal_rank),
                    _milliseconds(result.seconds),
                    first,
                ]
            )
        if probe.not_ingested:
            rows.append(
                [
                    probe.probe_id,
                    "-",
                    "partly not ingested",
                    "-",
                    *blanks,
                    "-",
                    "-",
                    ", ".join(probe.not_ingested),
                ]
            )
    return rows


def _place_rank_lines(report: Report) -> list[str]:
    rows = [
        [
            probe.probe_id,
            result.kind,
            _place_text(place),
            "-" if place.first_rank is None else str(place.first_rank),
        ]
        for probe in report.probes
        for result in probe.kinds
        if result.measured and len(result.place_ranks) > 1
        for place in result.place_ranks
    ]
    if not rows:
        return []
    return [
        "",
        "First rank per expected place (probes with more than one place):",
        *_table(["probe", "kind", "expected place", "first rank"], rows),
    ]


def _control_lines(report: Report) -> list[str]:
    rows: list[list[str]] = []
    for probe in report.probes:
        for listed in probe.controls:
            if not listed.measured:
                rows.append(
                    [
                        probe.probe_id,
                        listed.kind,
                        "-",
                        f"not measured: {listed.note}",
                        "",
                        "",
                        "",
                        "",
                    ]
                )
                continue
            if not listed.entries:
                rows.append([probe.probe_id, listed.kind, "-", "no entries", "", "", "", ""])
            for entry in listed.entries:
                for place in entry.places:
                    rows.append(
                        [
                            probe.probe_id,
                            listed.kind,
                            str(entry.rank),
                            "-" if place.section_id is None else str(place.section_id),
                            "-" if place.version_id is None else str(place.version_id),
                            place.sha256,
                            place.pages or "-",
                            place.device_key,
                        ]
                    )
    if not rows:
        return []
    return [
        "",
        f"Control probes (not judged): first {CONTROL_ENTRIES} entries, identifiers only:",
        *_table(["probe", "kind", "rank", "section", "version", "sha256", "pages", "device"], rows),
    ]


def format_table(report: Report) -> str:
    """The report as text tables: one row per probe and kind, then the totals."""
    ai = "on" if report.ai_enabled else "off"
    lines = [
        f"Search probes: {len(report.probes)}; AI features {ai};"
        f" embedding model {report.model or '-'};"
        f" TWOX_SECTION_MAX_CHARS {report.section_max_chars}; list depth {report.depth}",
    ]
    if not report.ai_enabled:
        lines.append(
            "AI features are not enabled (TWOX_AI_ENABLED is false): only the keyword search"
            " is measured; vector and combined are not measured."
        )
    lines.append("")
    lines += _table(
        [
            "probe",
            "kind",
            "status",
            "rank",
            *(f"top {cutoff}" for cutoff in report.cutoffs),
            "RR",
            "ms",
            "first correct place",
        ],
        _probe_rows(report),
    )
    if report.extended:
        lines += _place_rank_lines(report)
    lines += _control_lines(report)
    lines.append("")
    lines += _table(
        [
            "kind",
            "measured",
            "not measured",
            *(f"Recall@{cutoff}" for cutoff in report.cutoffs),
            "MRR",
            "total ms",
            "mean ms",
        ],
        [
            [
                summary.kind,
                str(summary.measured),
                str(summary.not_measured),
                *_recalls(report, summary),
                _number(summary.mrr),
                _milliseconds(summary.total_seconds),
                _milliseconds(summary.mean_seconds),
            ]
            for summary in report.summaries
        ],
    )
    lines.append("")
    lines.append(f"Not ingested: {report.not_ingested_count} of {len(report.probes)} probes")
    return "\n".join(lines) + "\n"


def format_json(report: Report) -> str:
    """The report as JSON."""
    return json.dumps(report.as_dict(), ensure_ascii=False, indent=2) + "\n"
