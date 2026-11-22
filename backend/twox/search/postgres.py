"""Search in PostgreSQL: keyword search (047) and vector search (050) over the sections.

What is searched (E-57): per document of kind ``document``, the sections of
the newest version that has sections. The state of the last ingest job does
not matter, so a document stays findable while it is ingested again or after
embedding failed. When the document has a newer version without sections,
the location says ``is_latest_version = False``. The same rule and the same
device and plant filters apply to every way a section is found.

How a section matches, in any of these ways:

* **keyword:** the full-text search with ``websearch_to_tsquery`` in the
  configurations ``simple``, ``german`` and ``english``, joined with OR, on
  :attr:`~twox.ingest.models.Section.search_vector`. ``simple`` keeps words
  and numbers as typed, the languages find word forms (``Steuerungen`` finds
  ``Steuerung``).
* **exact:** every identifier of the query (:mod:`twox.search.identifiers`)
  occurs word for word in the text, checked with a case-insensitive regular
  expression; the trigram index on the text speeds this up.
* **semantic** (AI features only, E-59): the query is embedded through the
  model interface (:func:`twox.answers.embeddings.get_query_embedder`, with
  ``TWOX_EMBED_QUERY_PREFIX`` and the short time limit
  ``TWOX_SEARCH_EMBED_TIMEOUT_SECONDS``); the :data:`VECTOR_CANDIDATES` sections nearest
  by cosine distance (``<=>``, the operator of pgvector's ``CosineDistance``)
  take part. Only sections embedded with the current model count; sections
  without an embedding or with another model are found by keyword only.
  The HNSW index is searched with ``hnsw.iterative_scan = relaxed_order``
  and ``hnsw.ef_search =`` :data:`HNSW_EF_SEARCH`, set locally for the
  transaction of the vector query, so a filter does not leave the list short.

Exclusions (``-word``, ``-"two words"``): ``websearch_to_tsquery`` turns
them into negated parts of the ``tsquery`` (``!'word'``). These parts are
taken from the parsed query (:func:`negated_parts`) and checked on every
candidate, so a section with an excluded word is found neither exactly, nor
by keyword, nor by meaning; the vector search leaves such sections out
before it takes the nearest ones.

With AI features off (or a request for the keyword search only), the model
service is never asked and the search is keyword and exact only
(``semantic = disabled``). When the model service fails (not reachable, too
slow, model refused or a cloud model), the search falls back to keyword and
exact only and says so with ``semantic = unavailable``; the server log gets
the kind of error, never the query.

Score (Reciprocal Rank Fusion, Cormack et al. 2009): ``1 / (RRF_K + rank)``
for each list the section is in. The keyword list is ranked by ``ts_rank``
(headings, weight A 1.0, above text, weight B 0.4), the vector list by
distance; equal values share a rank (``DENSE_RANK``), so the same content
stored for several devices does not push other sections down. Exact hits
count in one of two ways (:func:`exact_hits_first`, 063 and 067):

* **first:** the number of identifiers found exactly is added to the fused
  part, which stays below 1, so exact hits always come first. This holds
  when the query is essentially identifiers (an address, an error code, a
  part number, with at most :data:`EXACT_FIRST_MAX_OTHER_WORDS` other word)
  and whenever there is no vector list (AI features off, model service
  failed, nothing embedded): the keyword and exact search alone keep the
  order they had before 063.
* **not counted (E-61):** for any other query with a vector list (a
  question), exact hits add nothing of their own: the score is only
  ``1 / (RRF_K + keyword rank) + 1 / (RRF_K + vector rank)``. An identifier
  in a question acts only through the keyword and the vector list, like
  any other word. A question in plain words that names a product (``Wie
  tausche ich beim XR7 das Getriebeöl?``) then ranks the sections by
  meaning: a section that merely names the product and is also among the
  nearest by meaning no longer gets a second list on top and so no longer
  passes the section that answers the question. Sections that contain an
  identifier but are in neither list still take part, with score 0, after
  every other hit; they keep the match kind ``exact``. At equal score the
  hit nearer in meaning comes first. Work order 063 made the exact hits a
  third list of the fusion here; with the manuals, a section that named the
  product was then in two lists and stayed ahead of the best section by
  meaning (acceptance run 060, test question 9).

Phrases: the search vector joins six vectors (headings and text, three
configurations each); joining shifts positions, so the last word of one copy
stands right before the first word of the next. A phrase query (``"open
valve"``, but also ``PLC-01``) could match across that seam, for example
``"öffnen Ventil"`` in a text "Ventil öffnen". For phrase queries a match is
therefore checked again per configuration, on headings and text of that
configuration only, with a one-position gap between headings and text. A
phrase matches within the headings or within the text, not from the headings
into the text. Positions in a tsvector end at 16383; in
very long sections (several thousand words) phrases near the end of the
later copies are no longer found.

Same content for several devices (E-55): sections with the same checksum of
the version, the same pages (or, without pages, the same headings) and the
same text are one hit with all locations, after the fusion; the hit gets the
best score of its sections.

The snippet is plain text, cut in Python around the first found place. The
found words of the keyword search are located with ``ts_headline`` and
private markers that do not occur in the text; its output is never passed
on.
"""

import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.db import connection, transaction
from django.db.backends.utils import CursorWrapper

from twox.answers import embeddings
from twox.files.models import DocumentKind
from twox.ingest.models import EMBEDDING_DIMENSIONS, SEARCH_CONFIGS
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
    SemanticState,
)

#: Longest snippet, without the "…" at its ends.
SNIPPET_MAX_LENGTH = 300
#: Characters of context before the first found place.
SNIPPET_LEAD = 80
ELLIPSIS = "…"

logger = logging.getLogger(__name__)

#: ``ts_rank`` normalisation: ``rank / (rank + 1)``; it only orders the keyword list.
RANK_NORMALIZATION = 32

#: Reciprocal Rank Fusion: a list adds ``1 / (RRF_K + rank)``, rank 1 first.
#: 60 is the usual value (Cormack et al. 2009); the measurement in 057 checks it.
RRF_K = 60
#: A query is "essentially identifiers" (exact hits first, :func:`exact_hits_first`)
#: when it has, besides its identifiers, at most this many other words.
EXACT_FIRST_MAX_OTHER_WORDS = 1
#: Nearest sections the vector search contributes.
VECTOR_CANDIDATES = 50
#: ``hnsw.ef_search`` of the vector search (pgvector default 40): the size of
#: the candidate list of the HNSW index, at least :data:`VECTOR_CANDIDATES`.
HNSW_EF_SEARCH = 100
#: ``hnsw.iterative_scan`` (pgvector 0.8.0 and later): when filters drop
#: candidates, the index scan goes on until the list is full (or until
#: ``hnsw.max_scan_tuples``, default 20000). ``relaxed_order`` may return
#: slightly out of order; the query sorts by distance again.
HNSW_ITERATIVE_SCAN = "relaxed_order"

#: Placeholder lexeme between headings and text in the phrase recheck; the
#: parser never produces a lexeme with a space, so it cannot match real text.
_GAP_LEXEME = "twox gap"

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

    def exclusions(self) -> _Queries:
        """The excluded parts (``-word``), per configuration, joined with OR."""
        per_config = {}
        for config, query in self.per_config.items():
            parts = negated_parts(query)
            if parts:
                per_config[config] = " | ".join(parts)
        return _Queries(per_config=per_config)


#: Tokens of the text form of a ``tsquery``: a quoted lexeme (``''`` inside
#: is a quote) with optional weights or prefix mark, a phrase operator, one
#: of ``& | ! ( )``, or white space.
_TSQUERY_TOKEN = re.compile(r"'(?:[^']|'')*'(?::[*A-Da-d]+)?|<->|<\d+>|[&|!()]|\s+")


def _tsquery_tokens(text: str) -> list[str]:
    """``text`` (a ``tsquery`` as PostgreSQL prints it) split into tokens, without white space."""
    tokens: list[str] = []
    position = 0
    while position < len(text):
        match = _TSQUERY_TOKEN.match(text, position)
        if match is None:
            raise ValueError(f"unexpected tsquery text at position {position}")
        if not match.group().isspace():
            tokens.append(match.group())
        position = match.end()
    return tokens


def _operand_end(tokens: Sequence[str], start: int) -> int:
    """Index after the operand that begins at ``tokens[start]``: a lexeme or a group."""
    if start >= len(tokens):
        raise ValueError("tsquery operator without operand")
    if tokens[start] == "!":
        return _operand_end(tokens, start + 1)
    if tokens[start] != "(":
        return start + 1
    depth = 0
    for index in range(start, len(tokens)):
        if tokens[index] == "(":
            depth += 1
        elif tokens[index] == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("unbalanced parentheses in tsquery text")


def negated_parts(tsquery_text: str) -> list[str]:
    """The operands of ``!`` in ``tsquery_text``, each as ``tsquery`` text.

    ``websearch_to_tsquery`` turns ``-word`` into ``!'word'`` and ``-"two
    words"`` into ``!( 'two' <-> 'word' )``. A double negation (``!!'word'``,
    from ``--word``) excludes nothing, and negations inside an excluded part
    are not looked at.
    """
    tokens = _tsquery_tokens(tsquery_text)
    parts: list[str] = []
    index = 0
    while index < len(tokens):
        if tokens[index] != "!":
            index += 1
            continue
        bangs = 0
        while index < len(tokens) and tokens[index] == "!":
            bangs += 1
            index += 1
        if bangs % 2 == 0:
            continue
        end = _operand_end(tokens, index)
        parts.append(" ".join(tokens[index:end]))
        index = end
    return parts


#: Quotes and brackets in front of a token; ``-`` after them makes an exclusion
#: (the same characters :mod:`twox.search.identifiers` strips).
_TOKEN_PUNCTUATION = "\"'()[]{}<>,;!?"
#: An excluded phrase of the web search syntax: ``-"two words"`` (open at the end).
_EXCLUDED_PHRASE = re.compile(r'(?:^|(?<=\s))-+"[^"]*(?:"|$)')


def other_words(query: str) -> list[str]:
    """The words of ``query`` that are not identifiers, as typed.

    Tokens are separated by white space like in
    :func:`~twox.search.identifiers.find_identifiers`. Exclusions (``-word``,
    ``-"two words"``) and tokens without a letter or digit (``&``, ``"``)
    are not words.
    """
    words: list[str] = []
    for raw in _EXCLUDED_PHRASE.sub(" ", query).split():
        if raw.lstrip(_TOKEN_PUNCTUATION).startswith("-"):
            continue
        if not any(char.isalnum() for char in raw):
            continue
        if not find_identifiers(raw):
            words.append(raw)
    return words


def exact_hits_first(query: str, identifiers: Sequence[Identifier], *, vector_list: bool) -> bool:
    """Whether exact hits come before all other hits (``True``) or add nothing (``False``).

    Exact hits come first when the query is essentially identifiers: at least
    one identifier and at most :data:`EXACT_FIRST_MAX_OTHER_WORDS` other
    word (``192.168.0.5``, ``E1234``, ``Fehler E1234``, ``PLC-01 Adresse``).
    Who types an address or a code wants the places where it stands. One word
    beside it is allowed because that is how short lookups are written
    (``Fehler E1234``); a second word already makes a question, and a question
    that names a product on the side (``Wie viel trägt der UR5e?``) is
    answered by the sections that are near in meaning, not by every section
    that names the product. For such a question (``False``) the exact hits
    have no list of their own in the fusion (E-61): the identifier counts
    only through the keyword and the vector list.

    Without a vector list (``vector_list`` false: AI features off, the model
    service failed or nothing is embedded) exact hits always come first: the
    keyword and exact search keep the order they had before.
    """
    if not vector_list or not identifiers:
        return True
    return len(other_words(query)) <= EXACT_FIRST_MAX_OTHER_WORDS


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


#: Parameter prefix of the excluded parts (:meth:`_Queries.exclusions`).
_EXCLUDE = "exclude_"


def _keyword_condition(queries: _Queries, prefix: str = "") -> str:
    """SQL for "the section matches the full-text search", or ``FALSE``.

    The parameters are ``{prefix}tsquery`` and ``{prefix}query_<config>``.
    """
    if not queries.per_config:
        return "FALSE"
    condition = f"s.search_vector @@ %({prefix}tsquery)s::tsquery"
    if queries.has_phrase:
        # The gap lexeme (a space never appears in a parsed lexeme) moves the
        # text one position away from the headings and is deleted again, so a
        # phrase does not span the last heading word and the first text word.
        recheck = " OR ".join(
            f"(to_tsvector('{config}', s.heading_text) || ts_delete("
            f"'''{_GAP_LEXEME}'':1'::tsvector || to_tsvector('{config}', s.text),"
            f" '{_GAP_LEXEME}'::text))"
            f" @@ %({prefix}query_{config})s::tsquery"
            for config in queries.per_config
        )
        condition = f"({condition} AND ({recheck}))"
    return condition


def _exclusion_condition(exclusions: _Queries) -> str:
    """SQL for "the section has none of the excluded parts", or ``TRUE``.

    An excluded part counts in any of the configurations, like a word of the
    keyword search; for an excluded phrase only within headings or text.
    """
    if not exclusions.per_config:
        return "TRUE"
    return f"NOT ({_keyword_condition(exclusions, _EXCLUDE)})"


def _query_params(queries: _Queries, prefix: str = "") -> dict[str, str]:
    """The parameters of :func:`_keyword_condition`."""
    params = {f"{prefix}tsquery": queries.combined}
    for config, query in queries.per_config.items():
        params[f"{prefix}query_{config}"] = query
    return params


def _scope_sql(*, filter_devices: bool, filter_plants: bool) -> str:
    """The CTEs ``latest`` and ``searchable``: the versions that are searched.

    ``searchable`` holds, per document of kind ``document`` within the
    filters, the newest version that has sections (E-57). Both the keyword
    and the vector search start from it.
    """
    document_filters = ""
    if filter_devices:
        document_filters += " AND d.device_id = ANY(%(device_ids)s)"
    if filter_plants:
        document_filters += " AND dev.plant_id = ANY(%(plant_ids)s)"
    return f"""
latest AS (
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
)"""


def _scope_params(request: SearchRequest) -> dict[str, Any]:
    return {
        "kind": DocumentKind.DOCUMENT.value,
        "device_ids": list(request.device_ids),
        "plant_ids": list(request.plant_ids),
    }


def vector_sql(
    *, filter_devices: bool, filter_plants: bool, exclusions: _Queries | None = None
) -> str:
    """The vector search: the nearest sections and their rank by distance.

    Parameters: those of the scope, ``embedding`` (pgvector text form),
    ``model`` and ``vector_limit``, and those of ``exclusions``
    (:func:`_query_params` with the prefix ``exclude_``): sections with an
    excluded part do not take part, so the list stays full. The inner query
    is the form the HNSW index serves (``ORDER BY embedding <=> query LIMIT
    n``); with ``relaxed_order`` its rows may come slightly out of order, so
    the materialised result is sorted again (pgvector README). ``distance +
    0`` keeps PostgreSQL 17 and later from taking the order of the CTE as
    given and skipping that sort.
    """
    scope = _scope_sql(filter_devices=filter_devices, filter_plants=filter_plants)
    exclude = _exclusion_condition(exclusions or _Queries(per_config={}))
    return f"""
WITH {scope},
nearest AS MATERIALIZED (
    SELECT s.id, s.embedding <=> %(embedding)s::vector AS distance
    FROM ingest_section s
    WHERE s.embedding_model = %(model)s
        AND s.embedding IS NOT NULL
        AND s.document_version_id IN (SELECT version_id FROM searchable)
        AND {exclude}
    ORDER BY s.embedding <=> %(embedding)s::vector
    LIMIT %(vector_limit)s
)
SELECT id, DENSE_RANK() OVER (ORDER BY distance + 0) AS rank
FROM nearest
ORDER BY distance + 0, id
"""


def _search_sql(
    queries: _Queries,
    identifier_count: int,
    *,
    semantic: bool,
    filter_devices: bool,
    filter_plants: bool,
    exact_first: bool = True,
) -> str:
    """The search query; user input goes in only as named parameters.

    With ``semantic``, the sections of the vector search come in as the
    arrays ``semantic_ids`` and ``semantic_ranks``. The excluded parts of
    the query apply to every way a section is found. ``exact_first``
    (:func:`exact_hits_first`) adds the number of identifiers found to the
    score; otherwise exact hits add nothing of their own, the score is the
    fusion of the keyword and the vector list, and at equal score the hit
    nearer in meaning comes first (see :data:`EXACT_FIRST_MAX_OTHER_WORDS`
    and the module docstring). Sections that contain an identifier stay
    candidates either way, so the match kind ``exact`` is still reported.
    """
    keyword = _keyword_condition(queries)
    exclude = _exclusion_condition(queries.exclusions())
    exact = [f"(s.text ~* %(pattern_{index})s)" for index in range(identifier_count)]
    exact_count = " + ".join(f"{condition}::int" for condition in exact) or "0"
    rank = (
        f"ts_rank(s.search_vector, %(tsquery)s::tsquery, {RANK_NORMALIZATION})"
        if queries.per_config
        else "0.0"
    )
    conditions = [keyword, *exact]
    semantic_join = ""
    semantic_rank = "NULL::bigint"
    if semantic:
        # ANY on the primary key keeps the OR of index conditions (BitmapOr).
        conditions.append("s.id = ANY(%(semantic_ids)s::bigint[])")
        semantic_join = (
            "LEFT JOIN unnest(%(semantic_ids)s::bigint[], %(semantic_ranks)s::bigint[])"
            " AS sem(section_id, rank) ON sem.section_id = s.id"
        )
        semantic_rank = "sem.rank"
    where = " OR ".join(conditions)
    scope = _scope_sql(filter_devices=filter_devices, filter_plants=filter_plants)
    content_key = "sha256, page_start_key, page_end_key, heading_key, text_key"
    if exact_first:
        exact_part = "r.exact_count"
        tie_break = ""
    else:
        # A question (E-61): no list of its own for the exact hits; at equal
        # score the hit nearer in meaning comes first.
        exact_part = "0.0::float8"
        tie_break = "semantic_key ASC NULLS LAST, "
    return f"""
WITH {scope},
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
        {rank} AS rank,
        {semantic_rank} AS semantic_rank
    FROM ingest_section s
    JOIN searchable sv ON sv.version_id = s.document_version_id
    {semantic_join}
    WHERE ({where}) AND {exclude}
),
ranked AS (
    SELECT c.*,
        CASE WHEN c.keyword_match
            THEN DENSE_RANK() OVER (PARTITION BY c.keyword_match ORDER BY c.rank DESC)
        END AS keyword_rank
    FROM candidates c
),
matched AS (
    SELECT r.*,
        {exact_part}
        + COALESCE(1.0::float8 / (%(rrf_k)s + r.keyword_rank), 0.0)
        + COALESCE(1.0::float8 / (%(rrf_k)s + r.semantic_rank), 0.0) AS score
    FROM ranked r
),
grouped AS (
    SELECT
        {content_key},
        MAX(score) AS score, MIN(semantic_rank) AS semantic_key,
        MIN(section_id) AS representative_id
    FROM matched
    GROUP BY {content_key}
    ORDER BY score DESC, {tie_break}representative_id
    LIMIT %(limit)s
)
SELECT
    g.representative_id, g.score,
    rs.text, rs.heading_path, rs.page_start, rs.page_end,
    m.section_id, m.exact_count > 0, m.keyword_match, m.semantic_rank IS NOT NULL,
    m.is_latest, v.id, v.number, v.original_filename, d.id, d.title,
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
ORDER BY g.score DESC, {tie_break}g.representative_id,
    p.key, dev.key, d.title, v.number, m.section_id
"""


def _search_params(
    request: SearchRequest,
    queries: _Queries,
    identifiers: Sequence[Identifier],
    semantic: Sequence[tuple[int, int]],
) -> dict[str, Any]:
    params: dict[str, Any] = {
        **_scope_params(request),
        **_query_params(queries),
        **_query_params(queries.exclusions(), _EXCLUDE),
        "limit": request.limit,
        "rrf_k": RRF_K,
        "semantic_ids": [section_id for section_id, _ in semantic],
        "semantic_ranks": [rank for _, rank in semantic],
    }
    for index, identifier in enumerate(identifiers):
        params[f"pattern_{index}"] = postgres_pattern(identifier)
    return params


def vector_literal(vector: Sequence[float]) -> str:
    """``vector`` in the text form of pgvector (``[1.0,2.5,…]``)."""
    return "[" + ",".join(repr(float(value)) for value in vector) + "]"


def embed_query(query: str) -> tuple[str, list[float]] | None:
    """Model name and vector of ``query``, or ``None`` without vector search.

    ``None`` when AI features are off (the model service is not asked) or
    when the model service fails; a failure is logged with its kind and
    message, which name neither the query nor an address (044). The query
    embedder has the short time limit ``TWOX_SEARCH_EMBED_TIMEOUT_SECONDS``.
    """
    if not settings.TWOX_AI_ENABLED:
        return None
    try:
        embedder = embeddings.get_query_embedder()
        vector = embedder.embed_query(query)
    except embeddings.EmbeddingDisabledError:
        return None
    except embeddings.EmbeddingError as error:
        # Unavailable, rejected, remote (cloud) model or a wrong vector length.
        logger.warning(
            "Vector search not available, keyword search only: %s: %s",
            type(error).__name__,
            error,
        )
        return None
    if len(vector) != EMBEDDING_DIMENSIONS:
        logger.warning(
            "Vector search not available, keyword search only: the model returned"
            " %d values, the database holds %d",
            len(vector),
            EMBEDDING_DIMENSIONS,
        )
        return None
    return embedder.model_name, vector


def nearest_sections(
    cursor: CursorWrapper,
    request: SearchRequest,
    model: str,
    vector: Sequence[float],
    exclusions: _Queries | None = None,
) -> list[tuple[int, int]]:
    """``(section ID, rank)`` of the sections nearest to ``vector``, nearest first.

    Sections with one of the ``exclusions`` (the excluded parts of the query)
    do not take part.

    Runs in a transaction of its own; the HNSW settings are local to it and
    end with it. Inside an outer transaction (a savepoint) they last until the
    outer transaction ends; they only change how HNSW index scans run.
    """
    exclusions = exclusions or _Queries(per_config={})
    sql = vector_sql(
        filter_devices=bool(request.device_ids),
        filter_plants=bool(request.plant_ids),
        exclusions=exclusions,
    )
    params = {
        **_scope_params(request),
        **_query_params(exclusions, _EXCLUDE),
        "embedding": vector_literal(vector),
        "model": model,
        "vector_limit": VECTOR_CANDIDATES,
    }
    with transaction.atomic():
        # set_config(..., true) is SET LOCAL as a function, with parameters.
        cursor.execute(
            "SELECT set_config('hnsw.iterative_scan', %(scan)s, true),"
            " set_config('hnsw.ef_search', %(ef_search)s, true)",
            {"scan": HNSW_ITERATIVE_SCAN, "ef_search": str(HNSW_EF_SEARCH)},
        )
        cursor.execute(sql, params)
        return [(int(section_id), int(rank)) for section_id, rank in cursor.fetchall()]


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
    semantic: bool
    locations: list[HitLocation]

    @property
    def match_kinds(self) -> list[MatchKind]:
        """How the hit was found, in the order exact, keyword, semantic."""
        return [
            kind
            for kind, found in (
                (MatchKind.EXACT, self.exact),
                (MatchKind.KEYWORD, self.keyword),
                (MatchKind.SEMANTIC, self.semantic),
            )
            if found
        ]


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
            semantic,
            is_latest,
            version_id,
            version_number,
            version_filename,
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
                semantic=False,
                locations=[],
            )
            drafts[representative_id] = draft
            seen_versions[representative_id] = set()
        draft.exact = draft.exact or exact
        draft.keyword = draft.keyword or keyword
        draft.semantic = draft.semantic or semantic
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
                version_filename=version_filename,
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
    """Keyword, exact and (with AI features) vector search over the sections in PostgreSQL."""

    def search(self, request: SearchRequest) -> SearchResult:
        """The hits for ``request``, best first, at most ``request.limit``."""
        wanted = not request.keyword_only and bool(settings.TWOX_AI_ENABLED)
        # The state while the model is not needed (nothing to search for).
        idle = SemanticState.USED if wanted else SemanticState.DISABLED
        # PostgreSQL text cannot hold NUL; it carries no meaning in a query.
        query = request.query.replace("\x00", " ").strip()
        if not query:
            return SearchResult(semantic=idle)
        identifiers = find_identifiers(query)
        with connection.cursor() as cursor:
            queries = _parse_queries(cursor, query)
        # A query without a word or identifier (only stop words or special
        # characters) finds nothing, also without asking the model.
        if not queries.per_config and not identifiers:
            return SearchResult(semantic=idle)
        # Outside a cursor: the model may take a while to answer.
        embedded = embed_query(query) if wanted else None
        state = SemanticState.DISABLED
        if wanted:
            state = SemanticState.UNAVAILABLE if embedded is None else SemanticState.USED
        with connection.cursor() as cursor:
            semantic: list[tuple[int, int]] = []
            if embedded is not None:
                model, vector = embedded
                semantic = nearest_sections(cursor, request, model, vector, queries.exclusions())
            sql = _search_sql(
                queries,
                len(identifiers),
                semantic=bool(semantic),
                filter_devices=bool(request.device_ids),
                filter_plants=bool(request.plant_ids),
                exact_first=exact_hits_first(query, identifiers, vector_list=bool(semantic)),
            )
            cursor.execute(sql, _search_params(request, queries, identifiers, semantic))
            drafts = _collect_hits(cursor.fetchall())
            # A hit found by meaning only gets no highlights: single words of
            # the query in it (such as "the") would mark nothing that matters.
            keyword_spans = _keyword_spans(
                cursor, queries, [draft for draft in drafts if draft.keyword]
            )
        hits = []
        for draft in drafts:
            spans = keyword_spans.get(draft.section_id, []) + _exact_spans(draft.text, identifiers)
            snippet, highlights = make_snippet(draft.text, spans)
            hits.append(
                SearchHit(
                    section_id=draft.section_id,
                    score=draft.score,
                    match_kinds=draft.match_kinds,
                    snippet=snippet,
                    highlights=highlights,
                    page_start=draft.page_start,
                    page_end=draft.page_end,
                    heading_path=draft.heading_path,
                    locations=draft.locations,
                )
            )
        return SearchResult(hits=hits, semantic=state)
