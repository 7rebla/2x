"""The search interface of 2x (E-03).

Everything outside this app searches through :class:`SearchBackend` and gets
plain data back: :class:`SearchResult` holds no Django querysets or model
instances, so the PostgreSQL backend (:mod:`twox.search.postgres`) can later
be replaced by OpenSearch or Qdrant without touching its callers.

A hit is one piece of text. When the same content is stored for several
devices (same checksum, page and text, E-55), it is one hit with all its
locations. Without the AI features (E-59) the search is a keyword search
only, and :attr:`SearchResult.semantic_used` is ``False``.

Permissions: in M2, whoever has the role ``read`` may search everything
(E-40); the API checks the role. Permissions per device are not part of M2;
they would come as a further field of :class:`SearchRequest`.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

#: Hits per request when the caller names no limit.
DEFAULT_LIMIT = 20
#: Largest accepted limit.
MAX_LIMIT = 100
#: Longest accepted query, in characters.
MAX_QUERY_LENGTH = 1000


class MatchKind(StrEnum):
    """How a hit was found."""

    #: An identifier of the query occurs word for word (IP address, part number).
    EXACT = "exact"
    #: The full-text search found the words, in German or English forms.
    KEYWORD = "keyword"
    #: The vector search found similar meaning (050, AI features only).
    SEMANTIC = "semantic"


@dataclass(frozen=True, slots=True)
class SearchRequest:
    """What to search for and where.

    Empty ``device_ids`` or ``plant_ids`` mean "no filter"; when both are
    given, a location must match both. ``query`` may be empty or consist of
    special characters only; the result is then empty, not an error.
    """

    query: str
    device_ids: Sequence[int] = ()
    plant_ids: Sequence[int] = ()
    limit: int = DEFAULT_LIMIT

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_LIMIT}, not {self.limit}")
        if len(self.query) > MAX_QUERY_LENGTH:
            raise ValueError(f"query must not be longer than {MAX_QUERY_LENGTH} characters")


@dataclass(frozen=True, slots=True)
class HitLocation:
    """Where a hit is stored: section, document version, document, device, plant."""

    section_id: int
    document_id: int
    document_title: str
    version_id: int
    version_number: int
    #: ``False`` when the document has a newer version that has no sections
    #: yet (not ingested yet, or ingesting it failed).
    is_latest_version: bool
    device_id: int
    device_key: str
    device_name: str
    plant_id: int
    plant_key: str
    plant_name: str


@dataclass(frozen=True, slots=True)
class Highlight:
    """A found place in :attr:`SearchHit.snippet`: ``snippet[start:end]``."""

    start: int
    end: int


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One found piece of text with all places it is stored at."""

    #: The section the snippet, pages and headings come from; one of the
    #: sections in :attr:`locations`.
    section_id: int
    #: Higher is better. Exact hits score at least 1 per identifier found,
    #: keyword-only hits less than 1.
    score: float
    match_kinds: list[MatchKind]
    #: Plain text around the first found place, about 300 characters at most;
    #: "…" marks a cut.
    snippet: str
    highlights: list[Highlight]
    page_start: int | None
    page_end: int | None
    heading_path: list[str]
    #: At least one entry.
    locations: list[HitLocation]


@dataclass(frozen=True, slots=True)
class SearchResult:
    """The hits of a search, best first."""

    hits: list[SearchHit] = field(default_factory=list)
    #: Whether the vector search took part (never without AI features, E-59).
    semantic_used: bool = False


class SearchBackend(Protocol):
    """A search engine behind the search interface."""

    def search(self, request: SearchRequest) -> SearchResult:
        """The hits for ``request``, best first, at most ``request.limit``."""
        ...


def get_search_backend() -> SearchBackend:
    """The search backend in use: PostgreSQL (E-03)."""
    # Imported here: the backend module imports this one.
    from twox.search.postgres import PostgresSearchBackend

    return PostgresSearchBackend()
