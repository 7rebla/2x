"""The event contract of the answers: building source references and the JSON round trip."""

import json

import pytest

from twox.answers.types import (
    CONTRADICTION_PHRASE,
    ELLIPSIS,
    NO_EVIDENCE_TEXT,
    SNIPPET_MAX_LENGTH,
    AnswerEvent,
    AnswerStatus,
    ContextSource,
    DeltaEvent,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    EventFormatError,
    SourceRef,
    SourcesEvent,
    from_json,
    to_json,
    to_source_ref,
)
from twox.search.interface import HitLocation

SECTION_TEXT = "Das Testgerät startet nach dem Einschalten in etwa zehn Sekunden."


def location(section_id: int = 11, device_key: str = "dev-a") -> HitLocation:
    return HitLocation(
        section_id=section_id,
        document_id=3,
        document_title="Testhandbuch",
        version_id=5,
        version_number=2,
        version_filename="testhandbuch.pdf",
        is_latest_version=True,
        device_id=7,
        device_key=device_key,
        device_name="Testgerät A",
        plant_id=1,
        plant_key="plant-1",
        plant_name="Testanlage",
    )


def context_source(n: int = 1, text: str = SECTION_TEXT) -> ContextSource:
    return ContextSource(
        n=n,
        section_id=11,
        version_id=5,
        ordinal=4,
        sha256="ab" * 32,
        page_start=12,
        page_end=13,
        heading_path=["Inbetriebnahme", "Einschalten"],
        text=text,
        locations=[location(), location(section_id=12, device_key="dev-b")],
    )


def test_fixed_sentences() -> None:
    assert NO_EVIDENCE_TEXT == "Dazu finde ich nichts in den Unterlagen."
    assert CONTRADICTION_PHRASE == "Die Unterlagen widersprechen sich"


def test_to_source_ref_copies_all_public_fields() -> None:
    source = context_source(n=2)
    ref = to_source_ref(source)
    assert ref.n == 2
    assert ref.section_id == source.section_id
    assert ref.version_id == source.version_id
    assert ref.sha256 == source.sha256
    assert (ref.page_start, ref.page_end) == (12, 13)
    assert ref.heading_path == source.heading_path
    assert ref.locations == source.locations
    assert not hasattr(ref, "text")
    assert not hasattr(ref, "ordinal")


def test_short_section_is_the_whole_snippet() -> None:
    ref = to_source_ref(context_source())
    assert ref.snippet == SECTION_TEXT
    assert ELLIPSIS not in ref.snippet


def test_long_section_is_cut_at_a_word_boundary() -> None:
    words = "Wort " * 380  # 1900 characters
    marker = "SCHLUSSMARKE"
    text = (words + marker).ljust(2000, "x")
    assert len(text) == 2000
    snippet = to_source_ref(context_source(text=text)).snippet
    assert len(snippet) <= SNIPPET_MAX_LENGTH
    assert snippet.endswith(ELLIPSIS)
    body = snippet.removesuffix(ELLIPSIS)
    assert text.startswith(body)
    assert body.endswith("Wort")  # whole words only
    assert marker not in snippet
    assert text[len(body) :].strip() not in snippet


def test_long_word_without_space_is_cut_hard() -> None:
    snippet = to_source_ref(context_source(text="a" * 2000)).snippet
    assert snippet == "a" * (SNIPPET_MAX_LENGTH - 1) + ELLIPSIS


def test_source_needs_a_location_and_a_positive_number() -> None:
    with pytest.raises(ValueError, match="location"):
        ContextSource(
            n=1,
            section_id=1,
            version_id=1,
            ordinal=0,
            sha256="00",
            page_start=None,
            page_end=None,
            heading_path=[],
            text="x",
            locations=[],
        )
    with pytest.raises(ValueError, match="at least 1"):
        context_source(n=0)


def test_done_event_checks_its_numbers() -> None:
    with pytest.raises(ValueError, match="ascending"):
        DoneEvent(status=AnswerStatus.ANSWERED, cited=[2, 1], removed_sentences=0, final_text="")
    with pytest.raises(ValueError, match="ascending"):
        DoneEvent(status=AnswerStatus.ANSWERED, cited=[1, 1], removed_sentences=0, final_text="")
    with pytest.raises(ValueError, match="negative"):
        DoneEvent(status=AnswerStatus.ANSWERED, cited=[1], removed_sentences=-1, final_text="")


def all_events() -> list[AnswerEvent]:
    events: list[AnswerEvent] = [
        SourcesEvent(sources=[to_source_ref(context_source(1)), to_source_ref(context_source(2))]),
        SourcesEvent(sources=[]),
        DeltaEvent(text="Etwa zehn Sekunden [1]."),
        DoneEvent(
            status=AnswerStatus.ANSWERED,
            cited=[1, 2],
            removed_sentences=1,
            final_text="Etwa zehn Sekunden [1].",
        ),
        DoneEvent(
            status=AnswerStatus.NO_EVIDENCE,
            cited=[],
            removed_sentences=0,
            final_text=NO_EVIDENCE_TEXT,
        ),
        DoneEvent(
            status=AnswerStatus.CONTRADICTION,
            cited=[1, 2],
            removed_sentences=0,
            final_text=f"{CONTRADICTION_PHRASE}: zehn [1] oder zwanzig [2] Sekunden.",
        ),
    ]
    events.extend(ErrorEvent(code=code) for code in ErrorCode)
    return events


@pytest.mark.parametrize("event", all_events(), ids=lambda e: f"{e.type}")
def test_json_round_trip(event: AnswerEvent) -> None:
    data = json.loads(json.dumps(to_json(event)))
    assert data["type"] == event.type
    assert from_json(data) == event


def test_every_error_code_and_status_round_trips() -> None:
    codes = {from_json({"type": "error", "code": code.value}) for code in ErrorCode}
    assert codes == {ErrorEvent(code=code) for code in ErrorCode}
    assert {code.value for code in ErrorCode} >= {
        "ai_disabled",
        "model_unavailable",
        "model_rejected",
        "timeout",
        "search_failed",
        "internal",
    }
    assert [status.value for status in AnswerStatus] == ["answered", "no_evidence", "contradiction"]


def test_sources_event_json_has_no_section_text() -> None:
    text = "Anfang des Abschnitts. " + "Fülltext " * 60 + "NUR-AUF-DEM-SERVER am Ende."
    event = SourcesEvent(sources=[to_source_ref(context_source(text=text))])
    dumped = json.dumps(to_json(event), ensure_ascii=False)
    assert "Anfang des Abschnitts." in dumped  # the snippet
    assert "NUR-AUF-DEM-SERVER" not in dumped
    assert text not in dumped
    assert '"text"' not in dumped
    assert '"ordinal"' not in dumped
    source = to_json(event)["sources"]
    assert isinstance(source, list)
    assert set(source[0]) == {
        "n",
        "section_id",
        "version_id",
        "sha256",
        "page_start",
        "page_end",
        "heading_path",
        "locations",
        "snippet",
    }
    assert set(source[0]["locations"][0]) == set(HitLocation.__dataclass_fields__)


def test_removed_sentences_is_a_number_in_json() -> None:
    event = DoneEvent(status=AnswerStatus.ANSWERED, cited=[1], removed_sentences=3, final_text="x")
    data = json.loads(json.dumps(to_json(event)))
    assert data["removed_sentences"] == 3
    assert type(data["removed_sentences"]) is int
    assert data["status"] == "answered"
    assert data["cited"] == [1]


def test_done_event_accepts_a_tuple_of_numbers() -> None:
    event = DoneEvent(
        status=AnswerStatus.ANSWERED,
        cited=(1, 3),  # type: ignore[arg-type]
        removed_sentences=0,
        final_text="x",
    )
    assert event.cited == [1, 3]


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"type": "unknown"},
        {"type": "delta"},
        {"type": "delta", "text": 3},
        {"type": "error", "code": "no_such_code"},
        {
            "type": "done",
            "status": "answered",
            "cited": [1],
            "removed_sentences": True,
            "final_text": "",
        },
        {
            "type": "done",
            "status": "answered",
            "cited": ["1"],
            "removed_sentences": 0,
            "final_text": "",
        },
        {"type": "done", "status": "maybe", "cited": [], "removed_sentences": 0, "final_text": ""},
        {"type": "sources", "sources": [{"n": 1}]},
        {"type": "sources", "sources": "none"},
    ],
)
def test_invalid_json_is_rejected(data: dict[str, object]) -> None:
    with pytest.raises(EventFormatError):
        from_json(data)


def test_source_ref_without_location_is_rejected() -> None:
    data = to_json(SourcesEvent(sources=[to_source_ref(context_source())]))
    sources = data["sources"]
    assert isinstance(sources, list)
    sources[0]["locations"] = []
    with pytest.raises(EventFormatError, match="location"):
        from_json(data)


def test_source_ref_is_frozen() -> None:
    ref = to_source_ref(context_source())
    assert isinstance(ref, SourceRef)
    with pytest.raises(AttributeError):
        ref.n = 5  # type: ignore[misc]
