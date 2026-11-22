"""Search probes: how well the search finds the places a question expects (056).

A probe is a query in own words and the places that answer it: the manifest
entry of the test factory (``manifest_id``), the SHA-256 of the file and the
pages, optionally the key of the device the place must be stored at. A probe
list holds references only, never text from a document
(``twox/search/probes/m2.json``).

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
:data:`DEPTH` entries, the number of correct entries among the first 5 and
10, the reciprocal rank and the time taken. An entry is correct when one of
its places has the expected checksum, a page in the expected pages and, if
the probe names one, the expected device. Per kind: Recall@5 and Recall@10
(share of measured probes with a correct entry among the first 5 or 10), MRR
(mean reciprocal rank, 0 for a probe without a correct entry) and the times.

A probe whose files are not ingested (no document version with the expected
checksum has sections) counts as "not ingested", not as a failure of the
search; it is not searched at all. When only some of its files are ingested,
the probe is measured against those, and the others are named.

The report holds ranks, pages, checksums and identifiers only, never the
text of a section or a snippet.
"""

import json
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
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
#: The cut-offs of Recall@k and of the counts per probe.
CUTOFFS = (5, 10)

#: Why a kind was not measured.
AI_DISABLED_NOTE = "AI features not enabled"
MODEL_FAILED_NOTE = "model service not available, keyword search only"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_TOP_KEYS = frozenset({"schema_version", "notes", "probes"})
_PROBE_KEYS = frozenset({"id", "query", "expected", "basis", "notes"})
_EXPECTED_KEYS = frozenset({"manifest_id", "sha256", "pages", "device"})


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


@dataclass(frozen=True, slots=True)
class ExpectedPlace:
    """A place that answers a probe."""

    manifest_id: str
    sha256: str
    pages: frozenset[int]
    #: Key of the device the place must be stored at; ``None`` for any device.
    device: str | None = None


@dataclass(frozen=True, slots=True)
class Probe:
    """A query and the places that answer it."""

    id: str
    query: str
    expected: tuple[ExpectedPlace, ...]


@dataclass(frozen=True, slots=True)
class Place:
    """Where an entry of a result list is stored."""

    sha256: str
    page_start: int | None
    page_end: int | None
    device_key: str


#: One entry of a result list: the places it is stored at.
Entry = Sequence[Place]


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


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """The outcome of one probe."""

    probe_id: str
    status: ProbeStatus
    #: Manifest entries of expected places whose file is not ingested.
    not_ingested: list[str] = field(default_factory=list)
    kinds: list[KindResult] = field(default_factory=list)


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

    @property
    def not_ingested_count(self) -> int:
        """Probes that were not searched because none of their files is ingested."""
        return sum(probe.status is ProbeStatus.NOT_INGESTED for probe in self.probes)

    def as_dict(self) -> dict[str, Any]:
        """The report as plain data for JSON."""
        data = asdict(self)
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


def _expected_place(value: object, where: str) -> ExpectedPlace:
    data = _object(value, where, _EXPECTED_KEYS)
    sha256 = _text(data.get("sha256"), f"{where}.sha256")
    if _SHA256.fullmatch(sha256) is None:
        raise ProbeFormatError(f"{where}.sha256: expected 64 lower-case hexadecimal characters")
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ProbeFormatError(f"{where}.pages: expected a non-empty list of page numbers")
    for index, page in enumerate(pages):
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ProbeFormatError(f"{where}.pages[{index}]: expected a page number from 1")
    device = data.get("device")
    return ExpectedPlace(
        manifest_id=_text(data.get("manifest_id"), f"{where}.manifest_id"),
        sha256=sha256,
        pages=frozenset(pages),
        device=None if device is None else _text(device, f"{where}.device"),
    )


def _probe(value: object, where: str) -> Probe:
    data = _object(value, where, _PROBE_KEYS)
    query = _text(data.get("query"), f"{where}.query")
    if len(query) > MAX_QUERY_LENGTH:
        raise ProbeFormatError(f"{where}.query: longer than {MAX_QUERY_LENGTH} characters")
    expected = data.get("expected")
    if not isinstance(expected, list) or not expected:
        raise ProbeFormatError(f"{where}.expected: expected a non-empty list of places")
    return Probe(
        id=_text(data.get("id"), f"{where}.id"),
        query=query,
        expected=tuple(
            _expected_place(place, f"{where}.expected[{index}]")
            for index, place in enumerate(expected)
        ),
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


# --- Judging a result list --------------------------------------------------


def _pages_text(start: int | None, end: int | None) -> str | None:
    if start is None:
        return None
    return str(start) if end is None or end == start else f"{start}-{end}"


def matching_place(place: Place, expected: Iterable[ExpectedPlace]) -> ExpectedPlace | None:
    """The expected place ``place`` stands for, or ``None``."""
    if place.page_start is None:
        return None
    page_end = place.page_end if place.page_end is not None else place.page_start
    for candidate in expected:
        if candidate.sha256 != place.sha256:
            continue
        if candidate.device is not None and candidate.device != place.device_key:
            continue
        if any(place.page_start <= page <= page_end for page in candidate.pages):
            return candidate
    return None


def judge(
    kind: SearchKind, entries: Sequence[Entry], expected: Sequence[ExpectedPlace], seconds: float
) -> KindResult:
    """Rank, counts and reciprocal rank of ``entries`` (best first) against ``expected``."""
    first_rank: int | None = None
    first_manifest_id: str | None = None
    first_pages: str | None = None
    correct_ranks: list[int] = []
    for rank, entry in enumerate(entries[:DEPTH], start=1):
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
    )


def summarise(kind: SearchKind, results: Iterable[KindResult]) -> KindSummary:
    """Recall@5, Recall@10, MRR and times of ``kind`` over the measured results."""
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
        "document_version__sha256",
        "document_version__document__device__key",
    )
    places = {
        pk: Place(sha256=sha256, page_start=start, page_end=end, device_key=device_key)
        for pk, start, end, sha256, device_key in rows
    }
    entries: dict[int, list[Place]] = {}
    for section_id, rank in nearest:
        place = places.get(section_id)
        if place is not None:
            entries.setdefault(rank, []).append(place)
    return [entries[rank] for rank in sorted(entries)]


def _not_measured(kind: SearchKind, note: str) -> KindResult:
    return KindResult(kind=kind, measured=False, note=note)


class _Runner:
    """Measures the probes one after the other."""

    def __init__(self, backend: SearchBackend, clock: Callable[[], float]) -> None:
        self.backend = backend
        self.clock = clock
        self.ai_enabled = bool(settings.TWOX_AI_ENABLED)
        self.model: str | None = None

    def keyword(self, request: SearchRequest, expected: Sequence[ExpectedPlace]) -> KindResult:
        started = self.clock()
        # This one request without the vector search; the model is not asked.
        result = self.backend.search(replace(request, keyword_only=True))
        return judge(SearchKind.KEYWORD, hit_entries(result), expected, self.clock() - started)

    def vector(self, request: SearchRequest, expected: Sequence[ExpectedPlace]) -> KindResult:
        started = self.clock()
        embedded = embed_query(request.query)
        if embedded is None:
            return _not_measured(SearchKind.VECTOR, MODEL_FAILED_NOTE)
        model, vector = embedded
        self.model = model
        with connection.cursor() as cursor:
            nearest = nearest_sections(cursor, request, model, vector)
        return judge(SearchKind.VECTOR, vector_entries(nearest), expected, self.clock() - started)

    def combined(self, request: SearchRequest, expected: Sequence[ExpectedPlace]) -> KindResult:
        started = self.clock()
        result = self.backend.search(request)
        seconds = self.clock() - started
        if not result.semantic_used:
            return _not_measured(SearchKind.COMBINED, MODEL_FAILED_NOTE)
        return judge(SearchKind.COMBINED, hit_entries(result), expected, seconds)

    def probe(self, probe: Probe, ingested: set[str]) -> ProbeResult:
        present = [place for place in probe.expected if place.sha256 in ingested]
        missing = sorted(
            {place.manifest_id for place in probe.expected if place.sha256 not in ingested}
        )
        if not present:
            return ProbeResult(
                probe_id=probe.id, status=ProbeStatus.NOT_INGESTED, not_ingested=missing
            )
        request = SearchRequest(query=probe.query, limit=DEPTH)
        kinds = [self.keyword(request, present)]
        if self.ai_enabled:
            kinds += [self.vector(request, present), self.combined(request, present)]
        else:
            kinds += [
                _not_measured(SearchKind.VECTOR, AI_DISABLED_NOTE),
                _not_measured(SearchKind.COMBINED, AI_DISABLED_NOTE),
            ]
        return ProbeResult(
            probe_id=probe.id, status=ProbeStatus.MEASURED, not_ingested=missing, kinds=kinds
        )


def evaluate(
    probes: Sequence[Probe],
    backend: SearchBackend | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> Report:
    """Measure ``probes`` against the ingested documents."""
    runner = _Runner(backend or get_search_backend(), clock)
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
        summaries=[summarise(kind, all_kinds) for kind in SearchKind],
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
    rows: list[list[str]] = []
    for probe in report.probes:
        if probe.status is ProbeStatus.NOT_INGESTED:
            rows.append(
                [
                    probe.probe_id,
                    "-",
                    "not ingested",
                    "-",
                    "-",
                    "-",
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
                        "-",
                        "-",
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
                    str(result.correct_in_top_5),
                    str(result.correct_in_top_10),
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
                    "-",
                    "-",
                    "-",
                    "-",
                    ", ".join(probe.not_ingested),
                ]
            )
    lines += _table(
        ["probe", "kind", "status", "rank", "top 5", "top 10", "RR", "ms", "first correct place"],
        rows,
    )
    lines.append("")
    lines += _table(
        ["kind", "measured", "not measured", "Recall@5", "Recall@10", "MRR", "total ms", "mean ms"],
        [
            [
                summary.kind,
                str(summary.measured),
                str(summary.not_measured),
                _number(summary.recall_at_5),
                _number(summary.recall_at_10),
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
