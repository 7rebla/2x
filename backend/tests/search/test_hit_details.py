"""Whole section text and cosine distance in a search hit (124).

The model interface is :class:`FakeEmbedder`; no test talks to a real model
service (E-59). All texts are written for these tests; none comes from a
manufacturer's manual.
"""

from collections.abc import Sequence
from dataclasses import replace

import pytest
from django.db import connection
from pytest_django.fixtures import Settings

from tests.search.fake_embedder import (
    FAKE_MODEL,
    QUERY,
    FakeEmbedder,
    at_angle,
    cosine_distance,
    embed,
    unit,
)
from tests.search.test_keyword_search import (
    add_sections,
    make_device,
    make_document,
    make_plant,
    sha256_of,
)
from twox.answers.embeddings import EmbeddingUnavailableError
from twox.assets.models import Device, Plant
from twox.files.models import DocumentVersion
from twox.ingest.models import Section
from twox.search.interface import (
    MatchKind,
    SearchHit,
    SearchRequest,
    SearchResult,
    SemanticState,
)
from twox.search.postgres import (
    SNIPPET_MAX_LENGTH,
    PostgresSearchBackend,
    nearest_sections,
    nearest_sections_with_distance,
    vector_literal,
)

pytestmark = pytest.mark.django_db

QUESTION = "How do I change the lubricant?"
ANSWER = "Replace the oil of the gearbox every 500 hours."
#: Longer than a snippet; the found word sits in the middle.
LONG_TEXT = (
    "The capybara feeder runs in three steps. " * 6
    + "Clean the gearbox filter after each shift. "
    + "The capybara feeder stops when the hatch opens. " * 6
)


@pytest.fixture
def plant() -> Plant:
    return make_plant()


@pytest.fixture
def device(plant: Plant) -> Device:
    return make_device(plant, "plc-01")


@pytest.fixture
def version(device: Device) -> DocumentVersion:
    return make_document(device)


def run(
    query: str,
    *,
    include_text: bool = False,
    keyword_only: bool = False,
    device_ids: Sequence[int] = (),
    plant_ids: Sequence[int] = (),
) -> SearchResult:
    request = SearchRequest(
        query=query,
        include_text=include_text,
        keyword_only=keyword_only,
        device_ids=device_ids,
        plant_ids=plant_ids,
    )
    return PostgresSearchBackend().search(request)


def own_distance(section: Section, vector: Sequence[float] = QUERY) -> float:
    """The cosine distance of ``section`` to ``vector``, asked of the database itself."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT embedding <=> %s::vector FROM ingest_section WHERE id = %s",
            [vector_literal(vector), section.pk],
        )
        row = cursor.fetchone()
    assert row is not None
    return float(row[0])


def without_details(hits: Sequence[SearchHit]) -> list[SearchHit]:
    return [replace(hit, text=None) for hit in hits]


@pytest.fixture
def mixed(version: DocumentVersion, fake_embedder: FakeEmbedder) -> list[Section]:
    """An answer by meaning, a long keyword hit, an exact hit and a hit by both."""
    answer, long, exact, both = add_sections(
        version,
        ANSWER,
        LONG_TEXT,
        "Set the address 10.0.0.9 on the panel.",
        "The gearbox needs fresh oil.",
    )
    embed(answer, at_angle(10))
    embed(both, at_angle(25))
    return [answer, long, exact, both]


# --- Whole text --------------------------------------------------------------


@pytest.mark.parametrize("ai", [True, False])
def test_include_text_gives_the_whole_section_text(
    settings: Settings, mixed: list[Section], ai: bool
) -> None:
    settings.TWOX_AI_ENABLED = ai

    result = run("gearbox", include_text=True)

    assert len(LONG_TEXT) > SNIPPET_MAX_LENGTH
    assert len(result.hits) >= 2
    for hit in result.hits:
        assert hit.text == Section.objects.get(pk=hit.section_id).text
    long_hit = next(hit for hit in result.hits if hit.section_id == mixed[1].pk)
    assert long_hit.text == LONG_TEXT
    assert len(long_hit.snippet) < len(LONG_TEXT)


def test_without_include_text_there_is_no_text(mixed: list[Section]) -> None:
    result = run("gearbox")

    assert result.hits
    assert all(hit.text is None for hit in result.hits)
    assert SearchRequest(query="gearbox").include_text is False


@pytest.mark.parametrize("ai", [True, False])
@pytest.mark.parametrize("query", ["gearbox", QUESTION, "10.0.0.9", "gearbox oil 10.0.0.9"])
def test_include_text_changes_neither_order_nor_scores_nor_snippets(
    settings: Settings, mixed: list[Section], ai: bool, query: str
) -> None:
    settings.TWOX_AI_ENABLED = ai

    plain = run(query)
    detailed = run(query, include_text=True)

    assert plain.semantic is detailed.semantic
    assert without_details(detailed.hits) == plain.hits
    assert [hit.section_id for hit in detailed.hits] == [hit.section_id for hit in plain.hits]
    assert [hit.score for hit in detailed.hits] == [hit.score for hit in plain.hits]
    assert [(hit.snippet, hit.highlights) for hit in detailed.hits] == [
        (hit.snippet, hit.highlights) for hit in plain.hits
    ]


# --- Distance ----------------------------------------------------------------


def test_distance_of_vector_hits_is_the_cosine_distance(
    mixed: list[Section], fake_embedder: FakeEmbedder
) -> None:
    answer, long, _, both = mixed

    result = run("gearbox")

    assert result.semantic is SemanticState.USED
    hits = {hit.section_id: hit for hit in result.hits}
    assert set(hits) == {answer.pk, long.pk, both.pk}
    assert hits[answer.pk].semantic_distance == pytest.approx(own_distance(answer), abs=1e-6)
    assert hits[answer.pk].semantic_distance == pytest.approx(cosine_distance(10), abs=1e-6)
    assert hits[both.pk].semantic_distance == pytest.approx(own_distance(both), abs=1e-6)
    assert hits[both.pk].semantic_distance == pytest.approx(cosine_distance(25), abs=1e-6)
    assert hits[both.pk].match_kinds == [MatchKind.KEYWORD, MatchKind.SEMANTIC]
    # Found by keyword only: no distance.
    assert hits[long.pk].match_kinds == [MatchKind.KEYWORD]
    assert hits[long.pk].semantic_distance is None


def test_exact_hit_has_no_distance(mixed: list[Section], fake_embedder: FakeEmbedder) -> None:
    answer, _, exact, both = mixed

    result = run("10.0.0.9")

    assert result.semantic is SemanticState.USED
    hits = {hit.section_id: hit for hit in result.hits}
    assert MatchKind.EXACT in hits[exact.pk].match_kinds
    assert MatchKind.SEMANTIC not in hits[exact.pk].match_kinds
    assert hits[exact.pk].semantic_distance is None
    # The embedded sections are in the vector list and keep their distance.
    assert hits[answer.pk].semantic_distance == pytest.approx(own_distance(answer), abs=1e-6)
    assert hits[both.pk].semantic_distance == pytest.approx(own_distance(both), abs=1e-6)


def test_distance_with_a_query_vector_of_its_own(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    near, far = add_sections(version, ANSWER, "The lamp turns green when ready.")
    embed(near, at_angle(40, axis=2))
    embed(far, at_angle(70, axis=3))
    query_vector = at_angle(15, axis=2)
    fake_embedder.queries[QUESTION] = query_vector

    hits = run(QUESTION).hits

    assert [hit.section_id for hit in hits] == [near.pk, far.pk]
    for hit, section in zip(hits, (near, far), strict=True):
        assert hit.semantic_distance == pytest.approx(own_distance(section, query_vector), abs=1e-6)
    assert hits[0].semantic_distance == pytest.approx(cosine_distance(25), abs=1e-6)


def test_no_distance_with_ai_off(settings: Settings, mixed: list[Section]) -> None:
    settings.TWOX_AI_ENABLED = False

    result = run("gearbox oil 10.0.0.9")

    assert result.semantic is SemanticState.DISABLED
    assert result.hits
    assert all(hit.semantic_distance is None for hit in result.hits)


def test_no_distance_with_keyword_only(mixed: list[Section], fake_embedder: FakeEmbedder) -> None:
    result = run("gearbox oil 10.0.0.9", keyword_only=True)

    assert result.semantic is SemanticState.DISABLED
    assert result.hits
    assert all(hit.semantic_distance is None for hit in result.hits)
    assert fake_embedder.calls == []


def test_no_distance_when_the_model_service_fails(
    mixed: list[Section], fake_embedder: FakeEmbedder
) -> None:
    fake_embedder.error = EmbeddingUnavailableError("model service not reachable")

    result = run("gearbox oil 10.0.0.9")

    assert result.semantic is SemanticState.UNAVAILABLE
    assert result.hits
    assert all(hit.semantic_distance is None for hit in result.hits)


def test_same_content_on_two_devices_has_the_smaller_distance(
    plant: Plant, fake_embedder: FakeEmbedder
) -> None:
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    shared = sha256_of("shared manual with distances")
    (one,) = add_sections(make_document(first, sha256=shared), ANSWER)
    (two,) = add_sections(make_document(second, sha256=shared), ANSWER)
    # Same text, different vectors (for example embedded with different runs).
    embed(one, at_angle(30))
    embed(two, at_angle(12))

    (hit,) = run(QUESTION).hits
    (only_first,) = run(QUESTION, device_ids=[first.pk]).hits
    (only_second,) = run(QUESTION, device_ids=[second.pk]).hits

    assert [location.device_key for location in hit.locations] == ["plc-01", "plc-02"]
    assert hit.semantic_distance == pytest.approx(cosine_distance(12), abs=1e-6)
    assert hit.section_id == min(one.pk, two.pk)
    # A filter leaves only the distances within it.
    assert only_first.semantic_distance == pytest.approx(cosine_distance(30), abs=1e-6)
    assert only_second.semantic_distance == pytest.approx(cosine_distance(12), abs=1e-6)


def test_plant_filter_takes_distances_within_the_plant_only(
    fake_embedder: FakeEmbedder,
) -> None:
    near_plant = make_plant("line-near")
    far_plant = make_plant("line-far")
    shared = sha256_of("shared manual of two plants")
    (near,) = add_sections(make_document(make_device(near_plant, "plc-n"), sha256=shared), ANSWER)
    (far,) = add_sections(make_document(make_device(far_plant, "plc-f"), sha256=shared), ANSWER)
    embed(near, at_angle(8))
    embed(far, at_angle(33))

    (everywhere,) = run(QUESTION).hits
    (in_far,) = run(QUESTION, plant_ids=[far_plant.pk]).hits

    assert everywhere.semantic_distance == pytest.approx(cosine_distance(8), abs=1e-6)
    assert in_far.semantic_distance == pytest.approx(cosine_distance(33), abs=1e-6)
    assert [location.plant_key for location in in_far.locations] == ["line-far"]


def test_distance_changes_neither_order_nor_scores(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    sections = add_sections(version, *(f"Spare gearbox part {index}." for index in range(8)))
    for index, section in enumerate(sections):
        embed(section, at_angle(5 + 7 * index))

    hits = run("gearbox part").hits

    distances = [hit.semantic_distance for hit in hits if hit.semantic_distance is not None]
    assert len(distances) == len(hits) == len(sections)
    assert distances == sorted(distances)
    assert [hit.section_id for hit in hits] == [section.pk for section in sections]


# --- Nearest sections ----------------------------------------------------------


def test_nearest_sections_keeps_its_shape_and_the_new_list_adds_the_distance(
    version: DocumentVersion,
) -> None:
    first, second, third = add_sections(version, ANSWER, "Top up the grease.", "Check the belt.")
    embed(first, at_angle(50))
    embed(second, at_angle(10))
    embed(third, at_angle(30))
    request = SearchRequest(query="x")

    with connection.cursor() as cursor:
        plain = nearest_sections(cursor, request, FAKE_MODEL, unit(0))
        with_distance = nearest_sections_with_distance(cursor, request, FAKE_MODEL, unit(0))

    assert plain == [(second.pk, 1), (third.pk, 2), (first.pk, 3)]
    assert [(section_id, rank) for section_id, rank, _ in with_distance] == plain
    distances = [distance for _, _, distance in with_distance]
    assert distances == sorted(distances)
    assert distances == pytest.approx(
        [cosine_distance(10), cosine_distance(30), cosine_distance(50)], abs=1e-6
    )
    assert all(isinstance(distance, float) for distance in distances)
