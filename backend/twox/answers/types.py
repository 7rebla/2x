"""The event contract of the answers (M3) and the fixed sentences.

An answer is a stream of events: one :class:`SourcesEvent`, then any number
of :class:`DeltaEvent`, then exactly one :class:`DoneEvent`; or, at any
point, one :class:`ErrorEvent` that ends the stream. The context selection
yields :class:`ContextSource` values; only their public view
(:class:`SourceRef`, built by :func:`to_source_ref`) leaves the server. The
full section text goes into the prompt and nowhere else.

The streamed deltas are provisional: :attr:`DoneEvent.final_text` is the
checked text that replaces them (D9 (a)).

:func:`to_json` and :func:`from_json` convert events to plain JSON values and
back, with ``snake_case`` field names; ``json.dumps(to_json(event))`` read
back through :func:`from_json` gives an equal event.

:data:`NO_EVIDENCE_TEXT` and :data:`CONTRADICTION_PHRASE` are defined here and
only here. The prompt imports them; the citation check (``citations.py``)
and the answer service are to import them from here as well (``citations.py``
still carries placeholders with the same wording until it is switched over).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import pairwise
from typing import Final, Literal

from twox.search.interface import HitLocation

#: The fixed answer when the documents do not contain the answer (E-04).
NO_EVIDENCE_TEXT: Final = "Dazu finde ich nichts in den Unterlagen."
#: The phrase an answer starts with when sections contradict each other
#: (provisional until D9; without a colon, the prompt adds one).
CONTRADICTION_PHRASE: Final = "Die Unterlagen widersprechen sich"

#: Longest :attr:`SourceRef.snippet`, including the "…" that marks a cut.
SNIPPET_MAX_LENGTH: Final = 300
ELLIPSIS: Final = "…"


class AnswerStatus(StrEnum):
    """How an answer ended."""

    #: The answer is backed by at least one valid citation.
    ANSWERED = "answered"
    #: Nothing in the documents; the final text is :data:`NO_EVIDENCE_TEXT`.
    NO_EVIDENCE = "no_evidence"
    #: The sections contradict each other; at least two places are cited.
    CONTRADICTION = "contradiction"


class ErrorCode(StrEnum):
    """Why an answer failed. Fixed list; extend it only in this module."""

    #: The AI features are off (E-59); no model was contacted.
    AI_DISABLED = "ai_disabled"
    #: The model service is not reachable or has no such model.
    MODEL_UNAVAILABLE = "model_unavailable"
    #: The model service refused the request.
    MODEL_REJECTED = "model_rejected"
    #: The model service took too long.
    TIMEOUT = "timeout"
    #: The search or the database failed while selecting the context.
    SEARCH_FAILED = "search_failed"
    #: Anything else.
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class ContextSource:
    """One numbered section for the prompt. Server-side only (holds the full text)."""

    #: Source number, 1-based, as it appears in the prompt as ``[n]``.
    n: int
    section_id: int
    version_id: int
    ordinal: int
    #: Checksum of the document version the section comes from.
    sha256: str
    page_start: int | None
    page_end: int | None
    heading_path: list[str]
    #: Full section text; goes into the prompt, never to the client.
    text: str
    #: Every place the section is stored at (E-55); at least one entry.
    locations: list[HitLocation]

    def __post_init__(self) -> None:
        _check_number_and_locations(self.n, self.locations)


@dataclass(frozen=True, slots=True)
class SourceRef:
    """The public view of a :class:`ContextSource`: no full text, no ordinal.

    Built only by :func:`to_source_ref`.
    """

    n: int
    section_id: int
    version_id: int
    sha256: str
    page_start: int | None
    page_end: int | None
    heading_path: list[str]
    #: At least one entry.
    locations: list[HitLocation]
    #: Start of the section text, at most :data:`SNIPPET_MAX_LENGTH`
    #: characters, cut at a word boundary; "…" marks a cut.
    snippet: str

    def __post_init__(self) -> None:
        _check_number_and_locations(self.n, self.locations)


@dataclass(frozen=True, slots=True)
class SourcesEvent:
    """The first event: the numbered sources the answer may cite."""

    sources: list[SourceRef]
    type: Literal["sources"] = field(default="sources", init=False)


@dataclass(frozen=True, slots=True)
class DeltaEvent:
    """A piece of the streamed answer text (provisional, see :class:`DoneEvent`)."""

    text: str
    type: Literal["delta"] = field(default="delta", init=False)


@dataclass(frozen=True, slots=True)
class DoneEvent:
    """The last event of a successful answer."""

    status: AnswerStatus
    #: Valid source numbers used in the answer, ascending, each once.
    cited: list[int]
    #: Number of sentences dropped or flagged by the citation check.
    removed_sentences: int
    #: The checked text; replaces the streamed deltas (D9 (a)).
    final_text: str
    type: Literal["done"] = field(default="done", init=False)

    def __post_init__(self) -> None:
        cited = list(self.cited)
        if any(a >= b for a, b in pairwise(cited)):
            raise ValueError("cited must be ascending and unique")
        if any(number < 1 for number in cited):
            raise ValueError("cited numbers must be at least 1")
        if self.removed_sentences < 0:
            raise ValueError("removed_sentences must not be negative")
        object.__setattr__(self, "cited", cited)


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    """The answer failed. Carries only a fixed code: no address, prompt or answer."""

    code: ErrorCode
    type: Literal["error"] = field(default="error", init=False)


AnswerEvent = SourcesEvent | DeltaEvent | DoneEvent | ErrorEvent


def _check_number_and_locations(n: int, locations: Sequence[HitLocation]) -> None:
    if n < 1:
        raise ValueError(f"source number must be at least 1, not {n}")
    if not locations:
        raise ValueError("a source needs at least one location")


def make_snippet(text: str) -> str:
    """The start of ``text``: at most :data:`SNIPPET_MAX_LENGTH` characters.

    Leading and trailing white space is dropped. A longer text is cut at the
    last white space before the limit (mid-word only when there is none) and
    ends with "…".
    """
    text = text.strip()
    if len(text) <= SNIPPET_MAX_LENGTH:
        return text
    limit = SNIPPET_MAX_LENGTH - len(ELLIPSIS)
    end = limit
    if not text[limit].isspace():
        gap = max((i for i in range(limit) if text[i].isspace()), default=None)
        if gap is not None:
            end = gap
    return text[:end].rstrip() + ELLIPSIS


def to_source_ref(source: ContextSource) -> SourceRef:
    """The public view of ``source``: everything but the full text and the ordinal."""
    return SourceRef(
        n=source.n,
        section_id=source.section_id,
        version_id=source.version_id,
        sha256=source.sha256,
        page_start=source.page_start,
        page_end=source.page_end,
        heading_path=list(source.heading_path),
        locations=list(source.locations),
        snippet=make_snippet(source.text),
    )


# --- JSON ---------------------------------------------------------------------


def _location_to_json(location: HitLocation) -> dict[str, object]:
    return {
        "section_id": location.section_id,
        "document_id": location.document_id,
        "document_title": location.document_title,
        "version_id": location.version_id,
        "version_number": location.version_number,
        "version_filename": location.version_filename,
        "is_latest_version": location.is_latest_version,
        "device_id": location.device_id,
        "device_key": location.device_key,
        "device_name": location.device_name,
        "plant_id": location.plant_id,
        "plant_key": location.plant_key,
        "plant_name": location.plant_name,
    }


def source_ref_to_json(source: SourceRef) -> dict[str, object]:
    """``source`` as plain JSON values."""
    return {
        "n": source.n,
        "section_id": source.section_id,
        "version_id": source.version_id,
        "sha256": source.sha256,
        "page_start": source.page_start,
        "page_end": source.page_end,
        "heading_path": list(source.heading_path),
        "locations": [_location_to_json(location) for location in source.locations],
        "snippet": source.snippet,
    }


def to_json(event: AnswerEvent) -> dict[str, object]:
    """``event`` as plain JSON values, with its ``type``."""
    match event:
        case SourcesEvent():
            return {
                "type": event.type,
                "sources": [source_ref_to_json(source) for source in event.sources],
            }
        case DeltaEvent():
            return {"type": event.type, "text": event.text}
        case DoneEvent():
            return {
                "type": event.type,
                "status": event.status.value,
                "cited": list(event.cited),
                "removed_sentences": event.removed_sentences,
                "final_text": event.final_text,
            }
        case ErrorEvent():
            return {"type": event.type, "code": event.code.value}


class EventFormatError(ValueError):
    """A JSON value is not a valid answer event."""


def _get(data: Mapping[str, object], key: str) -> object:
    if key not in data:
        raise EventFormatError(f"missing field {key!r}")
    return data[key]


def _int(data: Mapping[str, object], key: str) -> int:
    value = _get(data, key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise EventFormatError(f"field {key!r} must be an integer")
    return value


def _optional_int(data: Mapping[str, object], key: str) -> int | None:
    if _get(data, key) is None:
        return None
    return _int(data, key)


def _str(data: Mapping[str, object], key: str) -> str:
    value = _get(data, key)
    if not isinstance(value, str):
        raise EventFormatError(f"field {key!r} must be a string")
    return value


def _bool(data: Mapping[str, object], key: str) -> bool:
    value = _get(data, key)
    if not isinstance(value, bool):
        raise EventFormatError(f"field {key!r} must be a boolean")
    return value


def _list(data: Mapping[str, object], key: str) -> list[object]:
    value = _get(data, key)
    if not isinstance(value, list):
        raise EventFormatError(f"field {key!r} must be a list")
    return value


def _str_list(data: Mapping[str, object], key: str) -> list[str]:
    items = _list(data, key)
    if not all(isinstance(item, str) for item in items):
        raise EventFormatError(f"field {key!r} must be a list of strings")
    return [str(item) for item in items]


def _int_list(data: Mapping[str, object], key: str) -> list[int]:
    result: list[int] = []
    for item in _list(data, key):
        if not isinstance(item, int) or isinstance(item, bool):
            raise EventFormatError(f"field {key!r} must be a list of integers")
        result.append(item)
    return result


def _mapping_list(data: Mapping[str, object], key: str) -> list[Mapping[str, object]]:
    result: list[Mapping[str, object]] = []
    for item in _list(data, key):
        if not isinstance(item, Mapping):
            raise EventFormatError(f"field {key!r} must be a list of objects")
        result.append(item)
    return result


def _location_from_json(data: Mapping[str, object]) -> HitLocation:
    return HitLocation(
        section_id=_int(data, "section_id"),
        document_id=_int(data, "document_id"),
        document_title=_str(data, "document_title"),
        version_id=_int(data, "version_id"),
        version_number=_int(data, "version_number"),
        version_filename=_str(data, "version_filename"),
        is_latest_version=_bool(data, "is_latest_version"),
        device_id=_int(data, "device_id"),
        device_key=_str(data, "device_key"),
        device_name=_str(data, "device_name"),
        plant_id=_int(data, "plant_id"),
        plant_key=_str(data, "plant_key"),
        plant_name=_str(data, "plant_name"),
    )


def source_ref_from_json(data: Mapping[str, object]) -> SourceRef:
    """The :class:`SourceRef` that :func:`source_ref_to_json` turned into ``data``."""
    try:
        return SourceRef(
            n=_int(data, "n"),
            section_id=_int(data, "section_id"),
            version_id=_int(data, "version_id"),
            sha256=_str(data, "sha256"),
            page_start=_optional_int(data, "page_start"),
            page_end=_optional_int(data, "page_end"),
            heading_path=_str_list(data, "heading_path"),
            locations=[_location_from_json(item) for item in _mapping_list(data, "locations")],
            snippet=_str(data, "snippet"),
        )
    except EventFormatError:
        raise
    except ValueError as error:
        raise EventFormatError(str(error)) from error


def from_json(data: Mapping[str, object]) -> AnswerEvent:
    """The event that :func:`to_json` turned into ``data``.

    Raises :class:`EventFormatError` for anything else.
    """
    event_type = _str(data, "type")
    try:
        match event_type:
            case "sources":
                return SourcesEvent(
                    sources=[source_ref_from_json(item) for item in _mapping_list(data, "sources")]
                )
            case "delta":
                return DeltaEvent(text=_str(data, "text"))
            case "done":
                return DoneEvent(
                    status=AnswerStatus(_str(data, "status")),
                    cited=_int_list(data, "cited"),
                    removed_sentences=_int(data, "removed_sentences"),
                    final_text=_str(data, "final_text"),
                )
            case "error":
                return ErrorEvent(code=ErrorCode(_str(data, "code")))
    except EventFormatError:
        raise
    except ValueError as error:
        raise EventFormatError(str(error)) from error
    raise EventFormatError(f"unknown event type {event_type!r}")
