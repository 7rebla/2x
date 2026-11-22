"""Select the numbered sources an answer is built from (M3, work order 125).

:func:`select_context` turns a question and an optional scope (devices,
plants) into the list of :class:`~twox.answers.types.ContextSource` the prompt
gets. It knows neither HTTP nor the language model; the answer service calls
it, the calibration (work order 128) calls it with its own values.

The steps, in this order:

1. AI features off (E-59): :class:`ContextDisabledError` at once, without a
   search, an embedding or any connection.
2. An empty question gives an empty selection below the threshold.
3. One search through :func:`~twox.search.interface.get_search_backend` with
   the whole section texts (``include_text``) and ``2 * max_sources`` hits.
4. Without the vector search (:attr:`SemanticState.UNAVAILABLE`, or
   :attr:`SemanticState.DISABLED` although the AI features are on):
   :class:`ContextUnavailableError`; "nothing found" would be misleading.
5. Threshold: a hit is relevant when its cosine distance is at most
   ``max_distance`` or when it was found exactly (an identifier such as an IP
   address). Without a relevant hit the selection is empty and
   ``below_threshold`` is true, so the model is not asked. Keyword hits
   without a distance are not relevant on their own. The threshold is a gate:
   once it is passed, the hits are taken in the order of the search.
6. Selection, in the order of the search:

   - copies of the same file (same ``sha256``, ``ordinal`` and text, the key
     of the search as well) at several devices are one source with the
     locations of all copies;
   - the same place in another language (E-61) is left out: a hit from
     another document of the same device whose stored embedding is at most
     ``TWOX_ANSWER_TRANSLATION_DISTANCE`` from a source taken before;
   - several sections of one document are allowed;
   - texts are never cut (the citation check looks for marks in the whole
     section); a section that does not fit into the rest of the character
     budget is skipped, and a later, shorter one may still fit;
   - at most ``max_sources`` main sources; with ``neighbours`` the sections
     right before and after each main source in the same document version
     follow it (they count against the budget, not against ``max_sources``).

7. The sources are numbered 1..n in their final order; each
   ``(version_id, ordinal)`` occurs once.

Database: one query for ordinal, checksum and embedding of all hits, one for
all neighbours; never one per hit. Search goes through the search interface
only; reading :class:`~twox.ingest.models.Section` for these fields is
storage, not search (E-03).

Logging: never the question, a section text or a heading (E-62). Only the
number of hits and sources, the best distance and the threshold result, on
DEBUG.
"""

import logging
import math
import operator
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from functools import reduce

from django.conf import settings
from django.db.models import Q

from twox.answers.types import ContextSource
from twox.ingest.models import Section
from twox.search.interface import (
    MAX_LIMIT,
    HitLocation,
    MatchKind,
    SearchHit,
    SearchRequest,
    SemanticState,
    get_search_backend,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ContextSelection:
    """The sources of an answer, or the finding that nothing is relevant enough."""

    #: Numbered 1..len(sources) without gaps, in the order of the prompt.
    sources: list[ContextSource]
    #: True: no hit is relevant enough; the model is not to be asked.
    below_threshold: bool
    #: The smallest cosine distance of all hits (for measuring and logging);
    #: ``None`` when no hit has one.
    best_distance: float | None
    #: Number of hits of the search before the selection.
    hit_count: int


class ContextDisabledError(Exception):
    """The AI features are off (E-59); nothing was searched."""


class ContextUnavailableError(Exception):
    """The vector search did not take part in the search; no reliable selection."""


@dataclass(slots=True)
class _Candidate:
    """A hit with the stored fields of its section, before numbering."""

    section_id: int
    version_id: int
    ordinal: int
    sha256: str
    page_start: int | None
    page_end: int | None
    heading_path: list[str]
    text: str
    locations: list[HitLocation]
    #: Stored embedding of the current model, otherwise ``None``.
    embedding: list[float] | None
    document_ids: set[int] = field(default_factory=set)
    device_ids: set[int] = field(default_factory=set)

    @property
    def key(self) -> tuple[int, int]:
        return (self.version_id, self.ordinal)

    def add_locations(self, locations: Sequence[HitLocation]) -> None:
        for location in locations:
            if location not in self.locations:
                self.locations.append(location)
        self.document_ids = {location.document_id for location in self.locations}
        self.device_ids = {location.device_id for location in self.locations}


@dataclass(frozen=True, slots=True)
class _StoredSection:
    version_id: int
    ordinal: int
    sha256: str
    embedding: list[float] | None


@dataclass(frozen=True, slots=True)
class _Neighbour:
    section_id: int
    page_start: int | None
    page_end: int | None
    heading_path: list[str]
    text: str


def select_context(
    question: str,
    *,
    device_ids: Sequence[int] = (),
    plant_ids: Sequence[int] = (),
    max_sources: int | None = None,
    context_chars: int | None = None,
    max_distance: float | None = None,
    neighbours: bool | None = None,
) -> ContextSelection:
    """The numbered sources for ``question`` within the devices and plants given.

    Parameters left at ``None`` take their value from the settings
    ``TWOX_ANSWER_*``. Raises :class:`ContextDisabledError` with the AI
    features off and :class:`ContextUnavailableError` when the vector search
    did not take part.
    """
    if not settings.TWOX_AI_ENABLED:
        raise ContextDisabledError("the AI features are off")
    k = settings.TWOX_ANSWER_MAX_SOURCES if max_sources is None else max_sources
    budget = settings.TWOX_ANSWER_CONTEXT_CHARS if context_chars is None else context_chars
    threshold = settings.TWOX_ANSWER_MAX_DISTANCE if max_distance is None else max_distance
    with_neighbours = settings.TWOX_ANSWER_NEIGHBOURS if neighbours is None else neighbours
    if k < 1:
        raise ValueError(f"max_sources must be at least 1, not {k}")
    if budget < 1:
        raise ValueError(f"context_chars must be at least 1, not {budget}")
    if not 0 < threshold <= 2:
        raise ValueError(f"max_distance must be greater than 0 and at most 2, not {threshold}")

    if not question.strip():
        return _finish(ContextSelection([], below_threshold=True, best_distance=None, hit_count=0))

    request = SearchRequest(
        query=question,
        device_ids=tuple(device_ids),
        plant_ids=tuple(plant_ids),
        limit=min(MAX_LIMIT, 2 * k),
        include_text=True,
    )
    result = get_search_backend().search(request)
    if result.semantic is not SemanticState.USED:
        raise ContextUnavailableError(f"the vector search did not take part ({result.semantic})")

    hits = result.hits
    distances = [hit.semantic_distance for hit in hits if hit.semantic_distance is not None]
    best_distance = min(distances, default=None)
    if not any(_is_relevant(hit, threshold) for hit in hits):
        return _finish(
            ContextSelection(
                [], below_threshold=True, best_distance=best_distance, hit_count=len(hits)
            )
        )

    candidates = _merge_copies(_candidates(hits, device_ids=device_ids, plant_ids=plant_ids))
    mains, remaining = _select_mains(candidates, max_sources=k, budget=budget)
    ordered = _with_neighbours(mains, remaining) if with_neighbours else mains
    sources = [_to_source(number, candidate) for number, candidate in enumerate(ordered, 1)]
    return _finish(
        ContextSelection(
            sources, below_threshold=False, best_distance=best_distance, hit_count=len(hits)
        )
    )


def _finish(selection: ContextSelection) -> ContextSelection:
    logger.debug(
        "Context: %d hits, %d sources, best distance %s, below threshold %s",
        selection.hit_count,
        len(selection.sources),
        "none" if selection.best_distance is None else f"{selection.best_distance:.4f}",
        selection.below_threshold,
    )
    return selection


def _is_relevant(hit: SearchHit, max_distance: float) -> bool:
    if hit.semantic_distance is not None and hit.semantic_distance <= max_distance:
        return True
    return MatchKind.EXACT in hit.match_kinds


def _in_scope(location: HitLocation, device_ids: Sequence[int], plant_ids: Sequence[int]) -> bool:
    if device_ids and location.device_id not in device_ids:
        return False
    return not plant_ids or location.plant_id in plant_ids


def _candidates(
    hits: Sequence[SearchHit], *, device_ids: Sequence[int], plant_ids: Sequence[int]
) -> list[_Candidate]:
    """The hits with ordinal, checksum and embedding of their sections (one query)."""
    stored = _stored_sections([hit.section_id for hit in hits])
    candidates: list[_Candidate] = []
    for hit in hits:
        section = stored.get(hit.section_id)
        locations = [
            location for location in hit.locations if _in_scope(location, device_ids, plant_ids)
        ]
        if section is None or hit.text is None or not locations:
            continue
        candidate = _Candidate(
            section_id=hit.section_id,
            version_id=section.version_id,
            ordinal=section.ordinal,
            sha256=section.sha256,
            page_start=hit.page_start,
            page_end=hit.page_end,
            heading_path=list(hit.heading_path),
            text=hit.text,
            locations=[],
            embedding=section.embedding,
        )
        candidate.add_locations(locations)
        candidates.append(candidate)
    return candidates


def _stored_sections(section_ids: Sequence[int]) -> dict[int, _StoredSection]:
    if not section_ids:
        return {}
    rows = Section.objects.filter(pk__in=section_ids).values_list(
        "pk",
        "ordinal",
        "document_version_id",
        "document_version__sha256",
        "embedding",
        "embedding_model",
    )
    model = settings.TWOX_EMBED_MODEL
    stored: dict[int, _StoredSection] = {}
    for pk, ordinal, version_id, sha256, embedding, embedding_model in rows:
        vector = None
        if embedding is not None and embedding_model == model:
            vector = [float(value) for value in embedding]
        stored[pk] = _StoredSection(
            version_id=version_id, ordinal=ordinal, sha256=sha256, embedding=vector
        )
    return stored


def _merge_copies(candidates: Sequence[_Candidate]) -> list[_Candidate]:
    """One candidate per content: copies of a file at several devices become one.

    Same checksum, same ordinal and same text means the same section of the
    same file (the text differs when a copy was cut into sections with other
    settings). The best placed copy stays; the locations of the others are
    added to it.
    """
    merged: dict[tuple[str, int, str], _Candidate] = {}
    for candidate in candidates:
        content = (candidate.sha256, candidate.ordinal, candidate.text)
        first = merged.get(content)
        if first is None:
            merged[content] = candidate
        else:
            first.add_locations(candidate.locations)
    return list(merged.values())


def _is_translation(candidate: _Candidate, other: _Candidate) -> bool:
    """Whether ``candidate`` is the same place as ``other`` in another language (E-61)."""
    if candidate.embedding is None or other.embedding is None:
        return False
    if not candidate.document_ids.isdisjoint(other.document_ids):
        return False
    if candidate.device_ids.isdisjoint(other.device_ids):
        return False
    distance = _cosine_distance(candidate.embedding, other.embedding)
    return distance <= settings.TWOX_ANSWER_TRANSLATION_DISTANCE


def _cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
    norms = math.hypot(*a) * math.hypot(*b)
    if norms == 0:
        return 1.0
    return 1.0 - math.sumprod(a, b) / norms


def _select_mains(
    candidates: Sequence[_Candidate], *, max_sources: int, budget: int
) -> tuple[list[_Candidate], int]:
    """The main sources in the order of the search, and the budget left after them."""
    mains: list[_Candidate] = []
    keys: set[tuple[int, int]] = set()
    remaining = budget
    for candidate in candidates:
        if len(mains) == max_sources:
            break
        if candidate.key in keys or len(candidate.text) > remaining:
            continue
        if any(_is_translation(candidate, main) for main in mains):
            continue
        mains.append(candidate)
        keys.add(candidate.key)
        remaining -= len(candidate.text)
    return mains, remaining


def _with_neighbours(mains: Sequence[_Candidate], remaining: int) -> list[_Candidate]:
    """``mains`` with the sections before and after each one, as far as the budget allows."""
    if not mains:
        return []
    wanted = reduce(
        operator.or_,
        (
            Q(document_version_id=main.version_id, ordinal__in=(main.ordinal - 1, main.ordinal + 1))
            for main in mains
        ),
    )
    rows = Section.objects.filter(wanted).values_list(
        "pk", "document_version_id", "ordinal", "page_start", "page_end", "heading_path", "text"
    )
    found = {
        (version_id, ordinal): _Neighbour(
            section_id=pk,
            page_start=page_start,
            page_end=page_end,
            heading_path=list(heading_path),
            text=text,
        )
        for pk, version_id, ordinal, page_start, page_end, heading_path, text in rows
    }
    keys = {main.key for main in mains}
    ordered: list[_Candidate] = []
    for main in mains:
        ordered.append(main)
        for ordinal in (main.ordinal - 1, main.ordinal + 1):
            key = (main.version_id, ordinal)
            neighbour = found.get(key)
            if neighbour is None or key in keys or len(neighbour.text) > remaining:
                continue
            locations = [
                replace(location, section_id=neighbour.section_id)
                for location in main.locations
                if location.version_id == main.version_id
            ]
            if not locations:
                continue
            ordered.append(
                _Candidate(
                    section_id=neighbour.section_id,
                    version_id=main.version_id,
                    ordinal=ordinal,
                    sha256=main.sha256,
                    page_start=neighbour.page_start,
                    page_end=neighbour.page_end,
                    heading_path=neighbour.heading_path,
                    text=neighbour.text,
                    locations=locations,
                    embedding=None,
                )
            )
            keys.add(key)
            remaining -= len(neighbour.text)
    return ordered


def _to_source(number: int, candidate: _Candidate) -> ContextSource:
    return ContextSource(
        n=number,
        section_id=candidate.section_id,
        version_id=candidate.version_id,
        ordinal=candidate.ordinal,
        sha256=candidate.sha256,
        page_start=candidate.page_start,
        page_end=candidate.page_end,
        heading_path=list(candidate.heading_path),
        text=candidate.text,
        locations=list(candidate.locations),
    )
