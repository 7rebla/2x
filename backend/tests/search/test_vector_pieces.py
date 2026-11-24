"""The vector search over the pieces of the sections (work order 150, E-75).

A section is as near as its nearest piece; the section stays the hit, the
source and the unit of citation. Every vector is hand-made
(:func:`~tests.search.fake_embedder.at_angle`): a piece at ``θ`` degrees has
the cosine distance ``1 - cos θ`` to every query. All texts are written for
these tests.
"""

from collections.abc import Sequence

import pytest
from django.db import connection

from tests.search.fake_embedder import (
    FAKE_MODEL,
    FakeEmbedder,
    at_angle,
    cosine_distance,
    embed,
    embed_pieces,
)
from tests.search.test_keyword_search import (
    add_sections,
    make_device,
    make_document,
    make_plant,
    search,
    sha256_of,
)
from twox.assets.models import Device, Plant
from twox.ingest.models import Section
from twox.ingest.pieces import Span
from twox.search.interface import MAX_LIMIT, MatchKind, SearchRequest
from twox.search.postgres import (
    VECTOR_CANDIDATES,
    PostgresSearchBackend,
    _Queries,
    nearest_sections_with_distance,
)

pytestmark = pytest.mark.django_db

#: A question that shares no word with the sections below.
QUESTION = "How do I change the lubricant?"
#: A section of three pieces; the answer stands in the last one.
LONG = (
    "General notes on the housing and its paint. "
    "The cover is fixed with four screws. "
    "Drain the gear oil and fill in fresh oil up to the mark."
)


def thirds(text: str) -> list[Span]:
    """Three spans of ``text``, cut at the sentence ends."""
    first = text.index(". ") + 1
    second = text.index(". ", first + 1) + 1
    return [(0, first), (first + 1, second), (second + 1, len(text))]


@pytest.fixture
def plant() -> Plant:
    return make_plant()


@pytest.fixture
def device(plant: Plant) -> Device:
    return make_device(plant, "plc-01")


def nearest(
    request: SearchRequest, exclusions: _Queries | None = None
) -> list[tuple[int, int, float]]:
    with connection.cursor() as cursor:
        return nearest_sections_with_distance(cursor, request, FAKE_MODEL, at_angle(0), exclusions)


def near(degrees: float) -> object:
    return pytest.approx(cosine_distance(degrees), rel=1e-3)


def add_long(device: Device, angles: Sequence[float], *, sha256: str | None = None) -> Section:
    """:data:`LONG` with one piece per angle; the section vector is the mean (30 degrees)."""
    (section,) = add_sections(make_document(device, sha256=sha256), LONG)
    embed(section, at_angle(30))
    embed_pieces(section, list(zip(thirds(LONG), (at_angle(a) for a in angles), strict=True)))
    return section


def test_a_section_with_one_near_piece_beats_one_with_a_middling_whole(device: Device) -> None:
    long = add_long(device, [60, 50, 5])
    (middle,) = add_sections(make_document(device, title="Other"), "Oil change in general.")
    embed(middle, at_angle(20))

    rows = nearest(SearchRequest(query=QUESTION))

    # Before 150 the section vector (30 degrees) ranked behind the 20 degrees.
    assert rows == [(long.pk, 1, near(5)), (middle.pk, 2, near(20))]


def test_the_hit_carries_the_smallest_piece_distance_and_the_whole_section(
    device: Device, fake_embedder: FakeEmbedder
) -> None:
    long = add_long(device, [60, 12, 40])

    result = PostgresSearchBackend().search(SearchRequest(query=QUESTION, include_text=True))

    (hit,) = result.hits
    assert hit.section_id == long.pk
    assert hit.match_kinds == [MatchKind.SEMANTIC]
    assert hit.semantic_distance == near(12)
    # Source and context stay the section: its whole text, its pages.
    assert hit.text == LONG
    assert (hit.page_start, hit.page_end) == (long.page_start, long.page_end)


def test_copies_of_a_content_share_rank_and_distance_and_keep_every_location(
    plant: Plant, fake_embedder: FakeEmbedder
) -> None:
    devices = [make_device(plant, f"plc-{index:02d}") for index in range(3)]
    shared = sha256_of("shared manual")
    copies = [add_long(device, [70, 8, 45], sha256=shared) for device in devices]
    (single,) = add_sections(make_document(devices[0], title="Other"), "Spare part list.")
    embed(single, at_angle(15))

    rows = nearest(SearchRequest(query=QUESTION))
    hits = search(QUESTION).hits

    assert sorted(rows) == sorted(
        [(copy.pk, 1, near(8)) for copy in copies] + [(single.pk, 2, near(15))]
    )
    assert [hit.section_id for hit in hits] == [copies[0].pk, single.pk]
    assert [location.device_key for location in hits[0].locations] == [d.key for d in devices]


def test_the_list_counts_contents_not_pieces(device: Device) -> None:
    # 60 contents of three pieces each: 180 pieces, 50 contents in the list.
    sections = add_sections(
        make_document(device),
        *(f"Part {index}. Its fitting. Its torque." for index in range(60)),
    )
    for index, section in enumerate(sections):
        embed_pieces(
            section,
            list(
                zip(
                    thirds(section.text),
                    (at_angle(10 + index + offset) for offset in (0.1, 0.2, 0.3)),
                    strict=True,
                )
            ),
        )

    rows = nearest(SearchRequest(query=QUESTION))

    assert [section_id for section_id, _, _ in rows] == [s.pk for s in sections[:VECTOR_CANDIDATES]]
    assert [rank for _, rank, _ in rows] == list(range(1, VECTOR_CANDIDATES + 1))
    assert [distance for _, _, distance in rows] == [
        near(10.1 + index) for index in range(VECTOR_CANDIDATES)
    ]


def test_device_and_plant_filters_apply_to_the_pieces(plant: Plant) -> None:
    inside = make_device(plant, "plc-01")
    outside = make_device(make_plant("line-b"), "plc-02")
    near_outside = add_long(outside, [60, 50, 1])
    in_scope = add_long(inside, [60, 50, 9])

    by_device = nearest(SearchRequest(query=QUESTION, device_ids=(inside.pk,)))
    by_plant = nearest(SearchRequest(query=QUESTION, plant_ids=(plant.pk,)))
    everything = nearest(SearchRequest(query=QUESTION))

    assert by_device == by_plant == [(in_scope.pk, 1, near(9))]
    assert [section_id for section_id, _, _ in everything] == [near_outside.pk, in_scope.pk]


def test_an_excluded_word_anywhere_in_the_section_leaves_out_all_its_pieces(
    device: Device, fake_embedder: FakeEmbedder
) -> None:
    # "housing" stands in the first piece only; the near piece is the last.
    long = add_long(device, [60, 50, 2])
    (other,) = add_sections(make_document(device, title="Other"), "Oil change in general.")
    embed(other, at_angle(25))

    rows = nearest(
        SearchRequest(query=f"{QUESTION} -housing"), _Queries(per_config={"simple": "'housing'"})
    )
    hits = search(f"{QUESTION} -housing").hits

    assert rows == [(other.pk, 1, near(25))]
    assert long.pk not in [hit.section_id for hit in hits]


def test_pieces_of_another_model_do_not_count(device: Device) -> None:
    long = add_long(device, [60, 50, 3])
    embed_pieces(long, [((0, len(LONG)), at_angle(3))], model="other-embed")
    (current,) = add_sections(make_document(device, title="Other"), "Oil change in general.")
    embed(current, at_angle(40))

    assert nearest(SearchRequest(query=QUESTION)) == [(current.pk, 1, near(40))]


def test_without_pieces_a_section_is_found_by_keyword_only(
    device: Device, fake_embedder: FakeEmbedder
) -> None:
    # An embedding of the section alone, as before the embed step of 150
    # has run: no fallback to it (see the report of 150).
    (section,) = add_sections(make_document(device), "Lubricant change of the gear.")
    Section.objects.filter(pk=section.pk).update(embedding=at_angle(1), embedding_model=FAKE_MODEL)

    assert nearest(SearchRequest(query=QUESTION)) == []
    (hit,) = search("lubricant").hits
    assert hit.section_id == section.pk
    assert hit.match_kinds == [MatchKind.KEYWORD]
    assert hit.semantic_distance is None


def test_many_pieces_of_few_contents_still_give_every_content(
    device: Device, fake_embedder: FakeEmbedder
) -> None:
    # The pieces nearest to the query belong to a few long sections: the
    # index rows hold fewer contents than wanted, the exact branch fills the list.
    long_sections = [add_long(device, [1 + index, 2 + index, 3 + index]) for index in range(30)]
    singles = add_sections(
        make_document(device, title="Spare parts"),
        *(f"Spare part number {index}." for index in range(40)),
    )
    for index, section in enumerate(singles):
        embed(section, at_angle(40 + index / 10))

    rows = nearest(SearchRequest(query=QUESTION))
    hits = search(QUESTION, limit=MAX_LIMIT).hits

    assert len({rank for _, rank, _ in rows}) == VECTOR_CANDIDATES
    expected = [s.pk for s in long_sections] + [s.pk for s in singles[: VECTOR_CANDIDATES - 30]]
    assert [section_id for section_id, _, _ in rows] == expected
    assert len(hits) == VECTOR_CANDIDATES
