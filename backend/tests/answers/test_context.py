"""The context selection of the answers (work order 125).

The search is the real PostgreSQL search with :class:`FakeEmbedder` (its
distances follow the angles of :func:`at_angle`), unless a test puts a
stand-in backend in place. No test reaches a real model service or the
internet. All texts are written for these tests.
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import pytest
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test.utils import CaptureQueriesContext
from pytest_django import DjangoAssertNumQueries
from pytest_django.fixtures import Settings

from tests.config.test_settings import run_python
from tests.search.fake_embedder import FakeEmbedder, at_angle, cosine_distance, embed
from tests.search.test_keyword_search import (
    add_sections,
    make_device,
    make_document,
    make_plant,
    sha256_of,
)
from twox.answers import context
from twox.answers.context import (
    ContextDisabledError,
    ContextSelection,
    ContextUnavailableError,
    select_context,
)
from twox.answers.embeddings import EmbeddingUnavailableError
from twox.answers.types import ContextSource
from twox.assets.models import Device, Plant
from twox.config import settings as settings_module
from twox.files.models import DocumentVersion
from twox.ingest.models import Section
from twox.search.interface import (
    HitLocation,
    MatchKind,
    SearchHit,
    SearchRequest,
    SearchResult,
    SemanticState,
)

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("no_real_model_service")]

#: A question that shares no word with any section text below.
QUESTION = "How do I change the lubricant?"


@pytest.fixture
def plant() -> Plant:
    return make_plant()


@pytest.fixture
def device(plant: Plant) -> Device:
    return make_device(plant, "plc-01")


@pytest.fixture
def version(device: Device) -> DocumentVersion:
    return make_document(device)


def text_of(length: int, letter: str = "a") -> str:
    """A text of exactly ``length`` characters."""
    return (letter * length)[:length]


def ordinals(selection: ContextSelection) -> list[int]:
    return [source.ordinal for source in selection.sources]


def section_ids(selection: ContextSelection) -> list[int]:
    return [source.section_id for source in selection.sources]


def device_ids_of(source: ContextSource) -> set[int]:
    return {location.device_id for location in source.locations}


def assert_numbered(selection: ContextSelection) -> None:
    """Numbers 1..n without gaps; each (version, ordinal) once."""
    assert [source.n for source in selection.sources] == list(range(1, len(selection.sources) + 1))
    keys = [(source.version_id, source.ordinal) for source in selection.sources]
    assert len(keys) == len(set(keys))


# --- Scope -------------------------------------------------------------------


def test_device_scope_gives_only_sources_of_that_device(
    plant: Plant, fake_embedder: FakeEmbedder
) -> None:
    device_a = make_device(plant, "plc-a")
    device_b = make_device(plant, "plc-b")
    (section_a,) = add_sections(make_document(device_a), "Grease the axle of the conveyor.")
    (section_b,) = add_sections(make_document(device_b), "Grease the axle of the lift.")
    embed(section_a, at_angle(20, axis=1))
    embed(section_b, at_angle(10, axis=2))

    unscoped = select_context(QUESTION)
    scoped = select_context(QUESTION, device_ids=[device_a.pk])

    assert section_ids(unscoped) == [section_b.pk, section_a.pk]
    assert section_ids(scoped) == [section_a.pk]
    assert all(device_a.pk in device_ids_of(source) for source in scoped.sources)


def test_plant_scope_gives_only_sources_of_that_plant(fake_embedder: FakeEmbedder) -> None:
    plant_p = make_plant("line-p")
    plant_q = make_plant("line-q")
    (section_p,) = add_sections(make_document(make_device(plant_p, "p-1")), "Grease the axle.")
    (section_q,) = add_sections(make_document(make_device(plant_q, "q-1")), "Grease the gear.")
    embed(section_p, at_angle(20, axis=1))
    embed(section_q, at_angle(10, axis=2))

    selection = select_context(QUESTION, plant_ids=[plant_p.pk])

    assert section_ids(selection) == [section_p.pk]
    assert all(
        location.plant_id == plant_p.pk
        for source in selection.sources
        for location in source.locations
    )


# --- Copies of a file at several devices -----------------------------------------


def test_three_copies_of_a_file_are_one_source_with_all_locations(
    plant: Plant, fake_embedder: FakeEmbedder
) -> None:
    devices = [make_device(plant, f"copy-{index}") for index in range(3)]
    sha256 = sha256_of("one file at three devices")
    copies = []
    for device in devices:
        version = make_document(device, sha256=sha256)
        (copy,) = add_sections(version, "Grease the axle every week.")
        embed(copy, at_angle(10, axis=1))
        copies.append(copy)
    (other,) = add_sections(make_document(devices[0]), "Check the belt tension.")
    # Far enough from the copies not to count as another language edition.
    embed(other, at_angle(40, axis=2))

    selection = select_context(QUESTION, max_sources=2)

    assert len(selection.sources) == 2
    first = selection.sources[0]
    assert first.section_id in {copy.pk for copy in copies}
    assert device_ids_of(first) == {device.pk for device in devices}
    assert {location.section_id for location in first.locations} == {c.pk for c in copies}
    assert selection.sources[1].section_id == other.pk

    scoped = select_context(QUESTION, device_ids=[devices[1].pk])
    assert section_ids(scoped) == [copies[1].pk]
    assert [location.device_id for location in scoped.sources[0].locations] == [devices[1].pk]


def location_of(section: Section) -> HitLocation:
    version = section.document_version
    document = version.document
    device = document.device
    return HitLocation(
        section_id=section.pk,
        document_id=document.pk,
        document_title=document.title,
        version_id=version.pk,
        version_number=version.number,
        version_filename=version.original_filename,
        is_latest_version=True,
        device_id=device.pk,
        device_key=device.key,
        device_name=device.name,
        plant_id=device.plant.pk,
        plant_key=device.plant.key,
        plant_name=device.plant.name,
    )


def hit_of(
    section: Section, distance: float | None, kinds: Sequence[MatchKind] = (MatchKind.SEMANTIC,)
) -> SearchHit:
    section.refresh_from_db()
    return SearchHit(
        section_id=section.pk,
        score=1.0,
        match_kinds=list(kinds),
        snippet=section.text[:300],
        highlights=[],
        page_start=section.page_start,
        page_end=section.page_end,
        heading_path=list(section.heading_path),
        locations=[location_of(section)],
        semantic_distance=distance,
        text=section.text,
    )


@dataclass
class StandInBackend:
    """A search backend that returns fixed hits and records the requests."""

    result: SearchResult
    requests: list[SearchRequest] = field(default_factory=list)

    def search(self, request: SearchRequest) -> SearchResult:
        self.requests.append(request)
        return self.result


def use_backend(monkeypatch: pytest.MonkeyPatch, backend: StandInBackend) -> None:
    monkeypatch.setattr(context, "get_search_backend", lambda: backend)


def test_copies_found_as_separate_hits_are_merged_before_counting(
    plant: Plant, fake_embedder: FakeEmbedder, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The search bundles identical content itself (E-55); copies that reach
    # the selection as separate hits (measured in 120) still become one source.
    devices = [make_device(plant, f"dup-{index}") for index in range(3)]
    sha256 = sha256_of("a file with copies")
    copies = []
    for device in devices:
        (copy,) = add_sections(make_document(device, sha256=sha256), "Grease the axle.")
        copies.append(copy)
    (other,) = add_sections(make_document(devices[0]), "Check the belt.")
    hits = [hit_of(copy, 0.2 + index / 100) for index, copy in enumerate(copies)]
    backend = StandInBackend(SearchResult([*hits, hit_of(other, 0.3)], SemanticState.USED))
    use_backend(monkeypatch, backend)

    selection = select_context(QUESTION, max_sources=2)

    assert section_ids(selection) == [copies[0].pk, other.pk]
    assert device_ids_of(selection.sources[0]) == {device.pk for device in devices}
    assert selection.hit_count == 4
    assert selection.best_distance == pytest.approx(0.2)
    (request,) = backend.requests
    assert request.include_text is True
    assert request.limit == 4
    assert request.query == QUESTION


def test_same_checksum_and_ordinal_with_another_text_stay_two_sources(
    plant: Plant, fake_embedder: FakeEmbedder, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The same file cut into sections with other settings: same ordinal, other text.
    sha256 = sha256_of("a file cut twice")
    (first,) = add_sections(
        make_document(make_device(plant, "cut-a"), sha256=sha256), "Grease the axle."
    )
    (second,) = add_sections(
        make_document(make_device(plant, "cut-b"), sha256=sha256), "Grease the axle weekly."
    )
    assert first.ordinal == second.ordinal
    hits = [hit_of(first, 0.2), hit_of(second, 0.21)]
    use_backend(monkeypatch, StandInBackend(SearchResult(hits, SemanticState.USED)))

    selection = select_context(QUESTION)

    assert section_ids(selection) == [first.pk, second.pk]
    assert_numbered(selection)


# --- Language editions (E-61) ------------------------------------------------------


def test_same_place_in_another_document_of_the_device_appears_once(
    device: Device, fake_embedder: FakeEmbedder
) -> None:
    (german,) = add_sections(make_document(device, "Handbuch"), "Achse wöchentlich fetten.")
    (english,) = add_sections(make_document(device, "Manual"), "Grease the axle weekly.")
    (other,) = add_sections(make_document(device, "Manual 2"), "Check the belt tension.")
    embed(german, at_angle(12, axis=1))
    embed(english, at_angle(10, axis=1))
    embed(other, at_angle(50, axis=2))

    selection = select_context(QUESTION)

    # The better placed edition stays, the other one is left out.
    assert section_ids(selection) == [english.pk, other.pk]


def test_similar_sections_of_one_document_both_stay(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    first, second = add_sections(version, "Grease the axle weekly.", "Grease the axle monthly.")
    embed(first, at_angle(10, axis=1))
    embed(second, at_angle(12, axis=1))

    assert section_ids(select_context(QUESTION)) == [first.pk, second.pk]


def test_similar_sections_of_different_devices_both_stay(
    plant: Plant, fake_embedder: FakeEmbedder
) -> None:
    (first,) = add_sections(make_document(make_device(plant, "a")), "Grease the axle weekly.")
    (second,) = add_sections(make_document(make_device(plant, "b")), "Grease the axle daily.")
    embed(first, at_angle(10, axis=1))
    embed(second, at_angle(12, axis=1))

    assert section_ids(select_context(QUESTION)) == [first.pk, second.pk]


def test_sections_without_an_embedding_of_the_current_model_are_not_merged(
    device: Device, fake_embedder: FakeEmbedder, settings: Settings
) -> None:
    (german,) = add_sections(make_document(device, "Handbuch"), "Achse wöchentlich fetten.")
    (english,) = add_sections(make_document(device, "Manual"), "Grease the axle weekly.")
    embed(german, at_angle(12, axis=1))
    embed(english, at_angle(10, axis=1))
    # The search embeds with the stand-in, the stored vectors are of another model.
    settings.TWOX_EMBED_MODEL = "another-model"

    assert section_ids(select_context(QUESTION)) == [english.pk, german.pk]


def test_keyword_hit_without_embedding_is_not_merged(
    device: Device, fake_embedder: FakeEmbedder
) -> None:
    (german,) = add_sections(make_document(device, "Handbuch"), "Achse wöchentlich fetten.")
    (english,) = add_sections(make_document(device, "Manual"), "Change the lubricant weekly.")
    embed(german, at_angle(10, axis=1))

    selection = select_context(QUESTION)

    assert set(section_ids(selection)) == {german.pk, english.pk}


def test_translation_distance_decides(
    device: Device, fake_embedder: FakeEmbedder, settings: Settings
) -> None:
    (german,) = add_sections(make_document(device, "Handbuch"), "Achse wöchentlich fetten.")
    (english,) = add_sections(make_document(device, "Manual"), "Grease the axle weekly.")
    embed(english, at_angle(10, axis=1))
    embed(german, at_angle(10, axis=2))
    # Distance of the two stored vectors: 1 - cos²(10°), about 0.030.
    settings.TWOX_ANSWER_TRANSLATION_DISTANCE = 0.02
    assert len(select_context(QUESTION).sources) == 2
    settings.TWOX_ANSWER_TRANSLATION_DISTANCE = 0.04
    assert len(select_context(QUESTION).sources) == 1


# --- Character budget ----------------------------------------------------------


def test_too_long_section_is_skipped_and_a_later_shorter_one_taken(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    first, long, short = add_sections(version, text_of(60, "a"), text_of(50, "b"), text_of(30, "c"))
    embed(first, at_angle(10, axis=1))
    embed(long, at_angle(12, axis=2))
    embed(short, at_angle(14, axis=3))

    selection = select_context(QUESTION, context_chars=100)

    assert section_ids(selection) == [first.pk, short.pk]
    assert sum(len(source.text) for source in selection.sources) <= 100
    stored = dict(Section.objects.values_list("pk", "text"))
    assert all(source.text == stored[source.section_id] for source in selection.sources)


def test_budget_holds_with_neighbours(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    sections = add_sections(version, *(text_of(40, letter) for letter in "abcdefg"))
    embed(sections[1], at_angle(10, axis=1))
    embed(sections[5], at_angle(12, axis=2))

    for budget in (40, 80, 100, 120, 160, 200, 1000):
        selection = select_context(QUESTION, context_chars=budget, neighbours=True)
        assert sum(len(source.text) for source in selection.sources) <= budget
        assert_numbered(selection)

    # Main sources first, then the neighbours as far as the budget allows.
    selection = select_context(QUESTION, context_chars=120, neighbours=True)
    assert ordinals(selection) == [1, 0, 5]


def test_main_sources_are_limited_but_neighbours_do_not_count(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    sections = add_sections(version, *(f"Text number {index}." for index in range(9)))
    for index, angle in ((1, 10), (4, 12), (7, 14)):
        embed(sections[index], at_angle(angle, axis=index + 1))

    assert ordinals(select_context(QUESTION, max_sources=2)) == [1, 4]
    with_neighbours = select_context(QUESTION, max_sources=2, neighbours=True)
    assert ordinals(with_neighbours) == [1, 0, 2, 4, 3, 5]


# --- Neighbours ----------------------------------------------------------------


def test_without_neighbours_only_hits_appear(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    sections = add_sections(version, *(f"Text number {index}." for index in range(5)))
    embed(sections[2], at_angle(10, axis=1))

    assert ordinals(select_context(QUESTION, neighbours=False)) == [2]


def test_neighbours_follow_their_main_source(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    sections = add_sections(version, *(f"Text number {index}." for index in range(5)))
    embed(sections[2], at_angle(10, axis=1))

    selection = select_context(QUESTION, neighbours=True)

    assert ordinals(selection) == [2, 1, 3]
    assert section_ids(selection) == [sections[2].pk, sections[1].pk, sections[3].pk]
    main, before, after = selection.sources
    assert before.text == sections[1].text
    assert before.version_id == after.version_id == main.version_id
    assert before.sha256 == main.sha256 == version.sha256
    assert [location.section_id for location in before.locations] == [sections[1].pk]
    assert [location.device_id for location in before.locations] == [
        location.device_id for location in main.locations
    ]
    assert_numbered(selection)


def test_neighbour_that_is_a_hit_itself_appears_once(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    sections = add_sections(version, *(f"Text number {index}." for index in range(5)))
    embed(sections[2], at_angle(10, axis=1))
    embed(sections[3], at_angle(12, axis=2))

    selection = select_context(QUESTION, neighbours=True)

    assert ordinals(selection) == [2, 1, 3, 4]
    assert_numbered(selection)


def test_neighbours_come_from_the_same_version_only(
    device: Device, fake_embedder: FakeEmbedder
) -> None:
    version = make_document(device)
    other = make_document(device, "Other manual")
    sections = add_sections(version, "Text zero.", "Text one.")
    others = add_sections(other, "Other zero.", "Other one.", "Other two.")
    embed(sections[1], at_angle(10, axis=1))

    selection = select_context(QUESTION, neighbours=True)

    assert section_ids(selection) == [sections[1].pk, sections[0].pk]
    assert not {source.section_id for source in selection.sources} & {s.pk for s in others}


# --- Threshold -------------------------------------------------------------------


def test_nothing_near_enough_means_no_sources(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    first, second = add_sections(version, "Grease the axle.", "Check the belt.")
    embed(first, at_angle(80, axis=1))
    embed(second, at_angle(85, axis=2))

    selection = select_context(QUESTION)

    assert selection.sources == []
    assert selection.below_threshold is True
    assert selection.best_distance == pytest.approx(cosine_distance(80))
    assert selection.hit_count == 2


def test_threshold_is_inclusive_and_can_be_given(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    (section,) = add_sections(version, "Grease the axle.")
    embed(section, at_angle(60, axis=1))
    distance = cosine_distance(60)

    assert select_context(QUESTION, max_distance=distance + 1e-6).below_threshold is False
    assert select_context(QUESTION, max_distance=distance - 1e-3).below_threshold is True


def test_exact_hit_lifts_the_threshold(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    question = "Which gateway uses 192.168.40.17?"
    (exact, far) = add_sections(version, "The gateway has the address 192.168.40.17.", "Belt.")
    embed(exact, at_angle(80, axis=1))
    embed(far, at_angle(85, axis=2))

    selection = select_context(question)

    assert selection.below_threshold is False
    assert selection.sources[0].section_id == exact.pk


def test_keyword_hits_without_distance_do_not_lift_the_threshold(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    _keyword, far = add_sections(version, "Change the lubricant of the pump.", "Belt.")
    embed(far, at_angle(85, axis=1))

    selection = select_context(QUESTION)

    assert selection.below_threshold is True
    assert selection.sources == []
    assert selection.hit_count == 2


def test_empty_question_does_not_search(
    fake_embedder: FakeEmbedder, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_search() -> None:
        raise AssertionError("searched")

    monkeypatch.setattr(context, "get_search_backend", no_search)

    assert select_context("  \n ") == ContextSelection(
        [], below_threshold=True, best_distance=None, hit_count=0
    )
    assert fake_embedder.calls == []


# --- Numbers and several sections of a document -------------------------------------


def test_two_places_of_one_document_on_different_pages_both_appear(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    (page_34,) = add_sections(version, "Grease the axle.", page=34)
    (page_36,) = add_sections(version, "Use the grease of class two.", page=36)
    embed(page_34, at_angle(10, axis=1))
    embed(page_36, at_angle(15, axis=2))

    selection = select_context(QUESTION)

    assert section_ids(selection) == [page_34.pk, page_36.pk]
    assert [source.page_start for source in selection.sources] == [34, 36]
    assert_numbered(selection)


def test_source_fields_come_from_the_section(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    (section,) = add_sections(version, "Grease the axle.", headings=("Care", "Axle"), page=7)
    embed(section, at_angle(10, axis=1))

    (source,) = select_context(QUESTION).sources

    assert source.n == 1
    assert source.section_id == section.pk
    assert source.version_id == version.pk
    assert source.ordinal == section.ordinal
    assert source.sha256 == version.sha256
    assert (source.page_start, source.page_end) == (7, 7)
    assert source.heading_path == ["Care", "Axle"]
    assert source.text == section.text


def test_section_without_page_is_a_source(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    (section,) = add_sections(version, "Grease the axle.", page=None)
    embed(section, at_angle(10, axis=1))

    (source,) = select_context(QUESTION).sources

    assert (source.page_start, source.page_end) == (None, None)


# --- Locations (E-55) ----------------------------------------------------------------


def test_same_content_at_two_devices_keeps_both_locations(
    plant: Plant, fake_embedder: FakeEmbedder
) -> None:
    device_a = make_device(plant, "twin-a")
    device_b = make_device(plant, "twin-b")
    sha256 = sha256_of("shared manual")
    for device in (device_a, device_b):
        (section,) = add_sections(make_document(device, sha256=sha256), "Grease the axle.")
        embed(section, at_angle(10, axis=1))

    (source,) = select_context(QUESTION).sources

    assert device_ids_of(source) == {device_a.pk, device_b.pk}


# --- AI off and vector search failing ---------------------------------------------------


def test_ai_off_raises_without_search_or_embedding(
    fake_embedder: FakeEmbedder, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def spy() -> None:
        calls.append("search")
        raise AssertionError("searched")

    monkeypatch.setattr(context, "get_search_backend", spy)
    settings.TWOX_AI_ENABLED = False

    with pytest.raises(ContextDisabledError):
        select_context(QUESTION)
    with pytest.raises(ContextDisabledError):
        select_context("")
    assert calls == []
    assert fake_embedder.calls == []


def test_failing_vector_search_raises(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    (section,) = add_sections(version, "Change the lubricant.")
    embed(section, at_angle(10, axis=1))
    fake_embedder.error = EmbeddingUnavailableError("the model service refused the connection")

    with pytest.raises(ContextUnavailableError):
        select_context(QUESTION)


@pytest.mark.parametrize("state", [SemanticState.UNAVAILABLE, SemanticState.DISABLED])
def test_search_without_vector_list_raises(
    fake_embedder: FakeEmbedder, monkeypatch: pytest.MonkeyPatch, state: SemanticState
) -> None:
    use_backend(monkeypatch, StandInBackend(SearchResult([], state)))

    with pytest.raises(ContextUnavailableError):
        select_context(QUESTION)


# --- Queries ------------------------------------------------------------------------


def count_queries(call: Callable[[], ContextSelection]) -> int:
    with CaptureQueriesContext(connection) as queries:
        call()
    return len(queries.captured_queries)


#: Queries of one selection with neighbours: the search itself, the stored
#: fields of all hits and all neighbours.
MAX_QUERIES = 8


def test_number_of_queries_does_not_grow_with_the_hits(
    plant: Plant,
    fake_embedder: FakeEmbedder,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    def select() -> ContextSelection:
        return select_context(QUESTION, max_sources=10, neighbours=True)

    sections = add_sections(make_document(make_device(plant, "few")), "One.", "Two.", "Three.")
    embed(sections[1], at_angle(10, axis=1))
    few = count_queries(select)

    # One device each: close vectors of one device would count as language editions.
    for index in range(9):
        more = add_sections(
            make_document(make_device(plant, f"more-{index}")), "One.", "Two.", "Three."
        )
        embed(more[1], at_angle(12 + index, axis=index + 2))
    selection = select()
    assert len(selection.sources) == 30
    many = count_queries(select)

    assert few == many
    with django_assert_max_num_queries(MAX_QUERIES):
        select()


# --- Logging -------------------------------------------------------------------------


def test_logs_hold_neither_question_nor_text_nor_headings(
    version: DocumentVersion, fake_embedder: FakeEmbedder, caplog: pytest.LogCaptureFixture
) -> None:
    question = "Where does the quokkafrage lead?"
    (section,) = add_sections(
        version, "The wombattext is here.", headings=("Numbatkapitel", "Bilbyteil")
    )
    embed(section, at_angle(10, axis=1))
    # Every logger at DEBUG: the root and the project logger (INFO in the settings).
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="twox")

    select_context(question, neighbours=True)
    select_context(question, max_distance=1e-6)

    messages = [record.getMessage() for record in caplog.records]
    assert any(message.startswith("Context: ") for message in messages)
    for forbidden in ("quokkafrage", "wombattext", "Numbatkapitel", "Bilbyteil"):
        assert forbidden not in caplog.text
        assert all(forbidden not in message for message in messages)


# --- Settings --------------------------------------------------------------------------

DUMP_ANSWER_SETTINGS = """
import django
from django.conf import settings
django.setup()
print(
    settings.TWOX_ANSWER_MAX_SOURCES,
    settings.TWOX_ANSWER_CONTEXT_CHARS,
    settings.TWOX_ANSWER_NEIGHBOURS,
    settings.TWOX_ANSWER_MAX_DISTANCE,
    settings.TWOX_ANSWER_TRANSLATION_DISTANCE,
)
"""


def test_answer_settings_have_their_starting_values() -> None:
    result = run_python(DUMP_ANSWER_SETTINGS, {})

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["8", "20000", "False", "0.6", "0.15"]


def test_answer_settings_read_the_variables() -> None:
    result = run_python(
        DUMP_ANSWER_SETTINGS,
        {
            "TWOX_ANSWER_MAX_SOURCES": "5",
            "TWOX_ANSWER_CONTEXT_CHARS": "12000",
            "TWOX_ANSWER_NEIGHBOURS": "true",
            "TWOX_ANSWER_MAX_DISTANCE": "2",
            "TWOX_ANSWER_TRANSLATION_DISTANCE": "0.1",
        },
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["5", "12000", "True", "2.0", "0.1"]


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("TWOX_ANSWER_MAX_SOURCES", "0", "must be a whole number greater than zero"),
        ("TWOX_ANSWER_MAX_SOURCES", "-3", "must be a whole number greater than zero"),
        ("TWOX_ANSWER_CONTEXT_CHARS", "0", "must be a whole number greater than zero"),
        ("TWOX_ANSWER_NEIGHBOURS", "maybe", "must be true or false"),
        ("TWOX_ANSWER_MAX_DISTANCE", "0", "must be a number greater than 0 and at most 2"),
        ("TWOX_ANSWER_MAX_DISTANCE", "-0.5", "must be a number greater than 0 and at most 2"),
        ("TWOX_ANSWER_MAX_DISTANCE", "2.5", "must be a number greater than 0 and at most 2"),
        ("TWOX_ANSWER_MAX_DISTANCE", "near", "must be a number greater than 0 and at most 2"),
        ("TWOX_ANSWER_TRANSLATION_DISTANCE", "0", "must be a number greater than 0"),
        ("TWOX_ANSWER_TRANSLATION_DISTANCE", "-1", "must be a number greater than 0"),
    ],
)
def test_answer_settings_reject_invalid_values(name: str, value: str, message: str) -> None:
    result = run_python(DUMP_ANSWER_SETTINGS, {name: value})

    assert result.returncode != 0
    assert f"Environment variable {name} {message}" in result.stderr


@pytest.mark.parametrize("value", ["0.6", "0.7"])
def test_translation_distance_must_be_below_the_threshold(value: str) -> None:
    result = run_python(DUMP_ANSWER_SETTINGS, {"TWOX_ANSWER_TRANSLATION_DISTANCE": value})

    assert result.returncode != 0
    assert (
        f"TWOX_ANSWER_TRANSLATION_DISTANCE ({float(value):g}) must be less than "
        "TWOX_ANSWER_MAX_DISTANCE (0.6)"
    ) in result.stderr


def test_answer_check_accepts_values_that_fit() -> None:
    settings_module.check_answer_settings(max_distance=0.6, translation_distance=0.59)
    settings_module.check_answer_settings(
        max_distance=django_settings.TWOX_ANSWER_MAX_DISTANCE,
        translation_distance=django_settings.TWOX_ANSWER_TRANSLATION_DISTANCE,
    )
    with pytest.raises(ImproperlyConfigured):
        settings_module.check_answer_settings(max_distance=0.3, translation_distance=0.3)


@pytest.mark.parametrize(
    "call",
    [
        lambda: select_context(QUESTION, max_sources=0),
        lambda: select_context(QUESTION, context_chars=0),
        lambda: select_context(QUESTION, max_distance=0.0),
        lambda: select_context(QUESTION, max_distance=2.1),
    ],
)
def test_invalid_arguments_are_refused(
    fake_embedder: FakeEmbedder, call: Callable[[], ContextSelection]
) -> None:
    with pytest.raises(ValueError, match="must be"):
        call()
