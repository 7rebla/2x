"""Search in PostgreSQL: keyword search over the sections (047).

What is searched (E-57): per document of kind ``document``, the sections of
the newest version that has sections. The state of the last ingest job does
not matter, so a document stays findable while it is ingested again or after
embedding failed. When the document has a newer version without sections,
the location says ``is_latest_version = False``.

How a section matches, either way:

* **keyword:** the full-text search with ``websearch_to_tsquery`` in the
  configurations ``simple``, ``german`` and ``english``, joined with OR, on
  :attr:`~twox.ingest.models.Section.search_vector`. ``simple`` keeps words
  and numbers as typed, the languages find word forms (``Steuerungen`` finds
  ``Steuerung``).
* **exact:** every identifier of the query (:mod:`twox.search.identifiers`)
  occurs word for word in the text, checked with a case-insensitive regular
  expression; the trigram index on the text speeds this up.

Score: the number of identifiers found exactly plus, for keyword matches,
``ts_rank`` with normalisation 32 (``rank / (rank + 1)``, below 1). Exact
hits therefore come first. ``ts_rank`` weighs headings (A, 1.0) above text
(B, 0.4).

Phrases: the search vector joins six vectors (headings and text, three
configurations each); joining shifts positions, so the last word of one copy
stands right before the first word of the next. A phrase query (``"open
valve"``, but also ``PLC-01``) could match across that seam, for example
``"öffnen Ventil"`` in a text "Ventil öffnen". For phrase queries a match is
therefore checked again per configuration, on headings and text of that
configuration only. A phrase matches within the headings or within the text,
not from the headings into the text. Positions in a tsvector end at 16383; in
very long sections (several thousand words) phrases near the end of the
later copies are no longer found.

Same content for several devices (E-55): sections with the same checksum of
the version, the same pages (or, without pages, the same headings) and the
same text are one hit with all locations; they are ranked once.

The snippet is plain text, cut in Python around the first found place. The
found words of the keyword search are located with ``ts_headline`` and
private markers that do not occur in the text; its output is never passed
on.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from django.db import connection
from django.db.backends.utils import CursorWrapper

from twox.files.models import DocumentKind
from twox.ingest.models import SEARCH_CONFIGS
from twox.search.identifiers import (
    Identifier,
    find_identifiers,
    postgres_pattern,
    python_pattern,
)
from twox.search.interface import (
    Highlight,
    HitLocation,
    MatchKind,
    SearchHit,
    SearchRequest,
    SearchResult,
)

#: Longest snippet, without the "…" at its ends.
SNIPPET_MAX_LENGTH = 300
#: Characters of context before the first found place.
SNIPPET_LEAD = 80
ELLIPSIS = "…"

#: ``ts_rank`` normalisation: ``rank / (rank + 1)``, so a keyword rank stays below 1.
RANK_NORMALIZATION = 32

#: Pairs of markers for ``ts_headline``; the first pair that occurs in none of
#: the texts is used. Neither ``"`` nor ``,`` (they end an option value).
_MARKER_CANDIDATES = (
    ("\x01", "\x02"),
    ("\x03", "\x04"),
    ("\x05", "\x06"),
    ("", ""),
    ("", ""),
)

_CONFIG_NAME = re.compile(r"[a-z]+")


@dataclass(frozen=True, slots=True)
class _Queries:
    """The parsed full-text queries of one search."""

    #: Configuration -> text of its ``tsquery``; configurations whose query
    #: has no lexemes (only stop words or special characters) are left out.
    per_config: dict[str, str]

    @property
    def combined(self) -> str:
        """All queries joined with OR, as ``tsquery`` text; empty if there is none."""
        return " | ".join(f"( {query} )" for query in self.per_config.values())

    @property
    def has_phrase(self) -> bool:
        """Whether a query uses the phrase operator ``<->`` (positions matter)."""
        return any("<" in query for query in self.per_config.values())


def _configs() -> tuple[str, ...]:
    """The text search configurations; plain names, so they may go into SQL."""
    for config in SEARCH_CONFIGS:
        if _CONFIG_NAME.fullmatch(config) is None:
            raise ValueError(f"unexpected text search configuration: {config!r}")
    return SEARCH_CONFIGS


def _parse_queries(cursor: CursorWrapper, query: str) -> _Queries:
    """Let PostgreSQL turn ``query`` into one ``tsquery`` per configuration."""
    columns = ", ".join(
        f"websearch_to_tsquery('{config}', %(query)s)::text" for config in _configs()
    )
    cursor.execute(f"SELECT {columns}", {"query": query})
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("websearch_to_tsquery returned no row")
    return _Queries(
        per_config={config: text for config, text in zip(_configs(), row, strict=True) if text}
    )


def _keyword_condition(queries: _Queries) -> str:
    """SQL for "the section matches the full-text search", or ``FALSE``."""
    if not queries.per_config:
        return "FALSE"
    condition = "s.search_vector @@ %(tsquery)s::tsquery"
    if queries.has_phrase:
        recheck = " OR ".join(
            f"(to_tsvector('{config}', s.heading_text) || to_tsvector('{config}', s.text))"
            f" @@ %(query_{config})s::tsquery"
            for config in queries.per_config
        )
        condition = f"({condition} AND ({recheck}))"
    return condition


def _search_sql(
    queries: _Queries, identifier_count: int, *, filter_devices: bool, filter_plants: bool
) -> str:
    """The search query; user input goes in only as named parameters."""
    keyword = _keyword_condition(queries)
    exact = [f"(s.text ~* %(pattern_{index})s)" for index in range(identifier_count)]
    exact_count = " + ".join(f"{condition}::int" for condition in exact) or "0"
    rank = (
        f"ts_rank(s.search_vector, %(tsquery)s::tsquery, {RANK_NORMALIZATION})"
        if queries.per_config
        else "0.0"
    )
    where = " OR ".join([keyword, *exact])
    document_filters = ""
    if filter_devices:
        document_filters += " AND d.device_id = ANY(%(device_ids)s)"
    if filter_plants:
        document_filters += " AND dev.plant_id = ANY(%(plant_ids)s)"
    return f"""
WITH latest AS (
    SELECT d.id AS document_id, MAX(v.number) AS latest_number
    FROM files_document d
    JOIN files_documentversion v ON v.document_id = d.id
    JOIN assets_device dev ON dev.id = d.device_id
    WHERE d.kind = %(kind)s{document_filters}
    GROUP BY d.id
),
searchable AS (
    SELECT DISTINCT ON (v.document_id)
        v.id AS version_id, v.sha256, v.number = l.latest_number AS is_latest
    FROM latest l
    JOIN files_documentversion v ON v.document_id = l.document_id
    WHERE EXISTS (SELECT 1 FROM ingest_section x WHERE x.document_version_id = v.id)
    ORDER BY v.document_id, v.number DESC
),
candidates AS (
    SELECT
        s.id AS section_id,
        sv.version_id,
        sv.sha256,
        sv.is_latest,
        COALESCE(s.page_start, 0) AS page_start_key,
        COALESCE(s.page_end, 0) AS page_end_key,
        CASE WHEN s.page_start IS NULL THEN s.heading_text ELSE '' END AS heading_key,
        md5(s.text) AS text_key,
        {exact_count} AS exact_count,
        {keyword} AS keyword_match,
        {rank} AS rank
    FROM ingest_section s
    JOIN searchable sv ON sv.version_id = s.document_version_id
    WHERE {where}
),
matched AS (
    SELECT c.*, c.exact_count + CASE WHEN c.keyword_match THEN c.rank ELSE 0 END AS score
    FROM candidates c
),
grouped AS (
    SELECT
        sha256, page_start_key, page_end_key, heading_key, text_key,
        MAX(score) AS score, MIN(section_id) AS representative_id
    FROM matched
    GROUP BY sha256, page_start_key, page_end_key, heading_key, text_key
    ORDER BY score DESC, representative_id
    LIMIT %(limit)s
)
SELECT
    g.representative_id, g.score,
    rs.text, rs.heading_path, rs.page_start, rs.page_end,
    m.section_id, m.exact_count > 0, m.keyword_match, m.is_latest,
    v.id, v.number, d.id, d.title,
    dev.id, dev.key, dev.name, p.id, p.key, p.name
FROM grouped g
JOIN matched m
    ON m.sha256 = g.sha256
    AND m.page_start_key = g.page_start_key
    AND m.page_end_key = g.page_end_key
    AND m.heading_key = g.heading_key
    AND m.text_key = g.text_key
JOIN ingest_section rs ON rs.id = g.representative_id
JOIN files_documentversion v ON v.id = m.version_id
JOIN files_document d ON d.id = v.document_id
JOIN assets_device dev ON dev.id = d.device_id
JOIN assets_plant p ON p.id = dev.plant_id
ORDER BY g.score DESC, g.representative_id, p.key, dev.key, d.title, v.number, m.section_id
"""


def _search_params(
    request: SearchRequest, queries: _Queries, identifiers: Sequence[Identifier]
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "kind": DocumentKind.DOCUMENT.value,
        "tsquery": queries.combined,
        "limit": request.limit,
        "device_ids": list(request.device_ids),
        "plant_ids": list(request.plant_ids),
    }
    for config, query in queries.per_config.items():
        params[f"query_{config}"] = query
    for index, identifier in enumerate(identifiers):
        params[f"pattern_{index}"] = postgres_pattern(identifier)
    return params


@dataclass(slots=True)
class _HitDraft:
    """A hit while the rows of its locations are read."""

    section_id: int
    score: float
    text: str
    heading_path: list[str]
    page_start: int | None
    page_end: int | None
    exact: bool
    keyword: bool
    locations: list[HitLocation]


def _collect_hits(rows: Iterable[Sequence[Any]]) -> list[_HitDraft]:
    """Group the rows (one per location) into hits, in the order of the rows."""
    drafts: dict[int, _HitDraft] = {}
    seen_versions: dict[int, set[int]] = {}
    for row in rows:
        (
            representative_id,
            score,
            text,
            heading_path,
            page_start,
            page_end,
            section_id,
            exact,
            keyword,
            is_latest,
            version_id,
            version_number,
            document_id,
            document_title,
            device_id,
            device_key,
            device_name,
            plant_id,
            plant_key,
            plant_name,
        ) = row
        draft = drafts.get(representative_id)
        if draft is None:
            draft = _HitDraft(
                section_id=representative_id,
                score=float(score),
                text=text,
                heading_path=list(heading_path),
                page_start=page_start,
                page_end=page_end,
                exact=False,
                keyword=False,
                locations=[],
            )
            drafts[representative_id] = draft
            seen_versions[representative_id] = set()
        draft.exact = draft.exact or exact
        draft.keyword = draft.keyword or keyword
        # The same text twice on one page of one version: one location.
        if version_id in seen_versions[representative_id]:
            continue
        seen_versions[representative_id].add(version_id)
        draft.locations.append(
            HitLocation(
                section_id=section_id,
                document_id=document_id,
                document_title=document_title,
                version_id=version_id,
                version_number=version_number,
                is_latest_version=is_latest,
                device_id=device_id,
                device_key=device_key,
                device_name=device_name,
                plant_id=plant_id,
                plant_key=plant_key,
                plant_name=plant_name,
            )
        )
    return list(drafts.values())


def _choose_markers(texts: Iterable[str]) -> tuple[str, str] | None:
    """A pair of markers that occurs in none of ``texts``."""
    texts = list(texts)
    for start, stop in _MARKER_CANDIDATES:
        if not any(start in text or stop in text for text in texts):
            return start, stop
    return None


def marked_spans(original: str, marked: str, start: str, stop: str) -> list[tuple[int, int]]:
    """Places in ``original`` of the words between ``start`` and ``stop`` in ``marked``.

    ``marked`` is ``original`` with markers around found words (the output
    of ``ts_headline``). Each marked word is looked up in ``original`` from
    the end of the previous one, so a change of white space in ``marked``
    does not shift the places.
    """
    spans: list[tuple[int, int]] = []
    cursor = 0
    position = 0
    while True:
        opening = marked.find(start, position)
        if opening < 0:
            break
        closing = marked.find(stop, opening + len(start))
        if closing < 0:
            break
        word = marked[opening + len(start) : closing]
        position = closing + len(stop)
        if not word:
            continue
        found = original.find(word, cursor)
        if found < 0:
            continue
        spans.append((found, found + len(word)))
        cursor = found + len(word)
    return spans


def _keyword_spans(
    cursor: CursorWrapper, queries: _Queries, drafts: Sequence[_HitDraft]
) -> dict[int, list[tuple[int, int]]]:
    """Section ID -> places of the words the full-text search found, per hit."""
    spans: dict[int, list[tuple[int, int]]] = {draft.section_id: [] for draft in drafts}
    markers = _choose_markers(draft.text for draft in drafts)
    if not queries.per_config or not drafts or markers is None:
        return spans
    start, stop = markers
    columns = ", ".join(
        f"ts_headline('{config}', text, %(query_{config})s::tsquery, %(options)s)"
        for config in queries.per_config
    )
    params: dict[str, Any] = {
        "ids": [draft.section_id for draft in drafts],
        "options": f'HighlightAll=true, StartSel="{start}", StopSel="{stop}"',
    }
    for config, query in queries.per_config.items():
        params[f"query_{config}"] = query
    cursor.execute(f"SELECT id, {columns} FROM ingest_section WHERE id = ANY(%(ids)s)", params)
    texts = {draft.section_id: draft.text for draft in drafts}
    for section_id, *headlines in cursor.fetchall():
        for headline in headlines:
            spans[section_id].extend(marked_spans(texts[section_id], headline, start, stop))
    return spans


def _exact_spans(text: str, identifiers: Sequence[Identifier]) -> list[tuple[int, int]]:
    """Places of the identifiers in ``text``."""
    return [
        match.span()
        for identifier in identifiers
        for match in python_pattern(identifier).finditer(text)
    ]


def _merge_spans(spans: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """``spans`` sorted, with overlapping ones joined."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def make_snippet(text: str, spans: Iterable[tuple[int, int]]) -> tuple[str, list[Highlight]]:
    """Plain-text snippet of ``text`` around the first span, with the highlights in it.

    At most :data:`SNIPPET_MAX_LENGTH` characters of ``text``, starting about
    :data:`SNIPPET_LEAD` characters before the first span, cut at white space
    where possible; "…" marks a cut. Highlights are positions in the
    returned snippet.
    """
    merged = _merge_spans(spans)
    start = 0
    if merged:
        first_start, first_end = merged[0]
        start = max(0, first_start - SNIPPET_LEAD)
        if first_end - start > SNIPPET_MAX_LENGTH:
            start = first_start
        elif start > 0 and not text[start - 1].isspace():
            # Begin with a whole word: after the next white space before the span.
            gap = re.search(r"\s", text[start:first_start])
            if gap is not None:
                start += gap.end()
    end = min(len(text), start + SNIPPET_MAX_LENGTH)
    if end < len(text) and not text[end].isspace():
        # End with a whole word: at the last white space after the first span.
        floor = merged[0][1] if merged else start
        last_gap = max((m.start() for m in re.finditer(r"\s", text[floor:end])), default=None)
        if last_gap is not None:
            end = floor + last_gap
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    prefix = ELLIPSIS if start > 0 else ""
    suffix = ELLIPSIS if end < len(text) else ""
    offset = len(prefix) - start
    highlights = [
        Highlight(start=max(span_start, start) + offset, end=min(span_end, end) + offset)
        for span_start, span_end in merged
        if span_start < end and span_end > start
    ]
    return f"{prefix}{text[start:end]}{suffix}", highlights


class PostgresSearchBackend:
    """Keyword and exact search over the sections in PostgreSQL."""

    def search(self, request: SearchRequest) -> SearchResult:
        """The hits for ``request``, best first, at most ``request.limit``."""
        # PostgreSQL text cannot hold NUL; it carries no meaning in a query.
        query = request.query.replace("\x00", " ").strip()
        if not query:
            return SearchResult()
        identifiers = find_identifiers(query)
        with connection.cursor() as cursor:
            queries = _parse_queries(cursor, query)
            if not queries.per_config and not identifiers:
                return SearchResult()
            sql = _search_sql(
                queries,
                len(identifiers),
                filter_devices=bool(request.device_ids),
                filter_plants=bool(request.plant_ids),
            )
            cursor.execute(sql, _search_params(request, queries, identifiers))
            drafts = _collect_hits(cursor.fetchall())
            keyword_spans = _keyword_spans(cursor, queries, drafts)
        hits = []
        for draft in drafts:
            spans = keyword_spans[draft.section_id] + _exact_spans(draft.text, identifiers)
            snippet, highlights = make_snippet(draft.text, spans)
            match_kinds = [
                kind
                for kind, found in (
                    (MatchKind.EXACT, draft.exact),
                    (MatchKind.KEYWORD, draft.keyword),
                )
                if found
            ]
            hits.append(
                SearchHit(
                    section_id=draft.section_id,
                    score=draft.score,
                    match_kinds=match_kinds,
                    snippet=snippet,
                    highlights=highlights,
                    page_start=draft.page_start,
                    page_end=draft.page_end,
                    heading_path=draft.heading_path,
                    locations=draft.locations,
                )
            )
        return SearchResult(hits=hits, semantic_used=False)
