"""The context selection with section pieces (work order 150, E-75).

The search measures a section by its nearest piece; the context still takes
the whole section, the threshold reads the distance of the piece, and the
merging of language editions (E-61) still compares the stored vectors of the
sections. Vectors are hand-made (:func:`~tests.search.fake_embedder.at_angle`);
all texts are written for these tests.
"""

import pytest
from pytest_django.fixtures import Settings

from tests.search.fake_embedder import (
    FakeEmbedder,
    at_angle,
    cosine_distance,
    embed,
    embed_pieces,
)
from tests.search.test_keyword_search import add_sections, make_device, make_document, make_plant
from twox.answers.context import select_context
from twox.assets.models import Device
from twox.ingest.models import Section

pytestmark = [
    pytest.mark.django_db,
    # Short texts on purpose (work order 153).
    pytest.mark.usefixtures("no_real_model_service", "every_text_a_source"),
]

#: A question that shares no word with the sections below.
QUESTION = "How do I change the lubricant?"
#: Three pieces, cut at the sentence ends; the answer stands in the last one.
LONG = (
    "General notes on the housing and its paint. "
    "The cover is fixed with four screws. "
    "Drain the gear oil and fill in fresh oil up to the mark."
)
SPANS = [(0, 43), (44, 80), (81, len(LONG))]


@pytest.fixture
def device() -> Device:
    return make_device(make_plant(), "plc-01")


def add_long(
    device: Device, title: str, section_vector: list[float], piece_vectors: list[list[float]]
) -> Section:
    """:data:`LONG` with a vector of its own and one vector per piece."""
    (section,) = add_sections(make_document(device, title), LONG)
    embed(section, section_vector)
    embed_pieces(section, list(zip(SPANS, piece_vectors, strict=True)))
    return section


def test_spans_are_the_three_sentences() -> None:
    assert [LONG[a:b] for a, b in SPANS] == [
        "General notes on the housing and its paint.",
        "The cover is fixed with four screws.",
        "Drain the gear oil and fill in fresh oil up to the mark.",
    ]


def test_a_near_piece_brings_the_whole_section_past_the_threshold(
    device: Device, fake_embedder: FakeEmbedder
) -> None:
    # The section vector (80 degrees, distance about 0.83) is far beyond the
    # threshold; the last piece (8 degrees) is near.
    long = add_long(device, "Manual", at_angle(80), [at_angle(70), at_angle(65), at_angle(8)])

    selection = select_context(QUESTION, max_distance=0.3)

    assert selection.below_threshold is False
    assert selection.best_distance == pytest.approx(cosine_distance(8), rel=1e-3)
    (source,) = selection.sources
    # The source is the whole section, not the piece.
    assert source.section_id == long.pk
    assert source.text == LONG
    assert (source.page_start, source.page_end) == (long.page_start, long.page_end)


def test_the_threshold_reads_the_piece_not_the_section_vector(
    device: Device, fake_embedder: FakeEmbedder
) -> None:
    # The other way round: a near section vector does not help when every
    # piece is far.
    add_long(device, "Manual", at_angle(5), [at_angle(75), at_angle(80), at_angle(85)])

    selection = select_context(QUESTION, max_distance=0.3)

    assert selection.below_threshold is True
    assert selection.sources == []
    assert selection.best_distance == pytest.approx(cosine_distance(75), rel=1e-3)


def test_language_editions_are_merged_by_their_section_vectors(
    device: Device, fake_embedder: FakeEmbedder, settings: Settings
) -> None:
    settings.TWOX_ANSWER_TRANSLATION_DISTANCE = 0.1
    # Different near pieces, but the same stored section vector: one place in
    # two languages (E-61); the better placed edition stays.
    english = add_long(
        device, "Manual", at_angle(30, axis=3), [at_angle(70), at_angle(65), at_angle(8)]
    )
    add_long(
        device, "Handbuch", at_angle(30, axis=3), [at_angle(70, axis=2), at_angle(65), at_angle(12)]
    )

    selection = select_context(QUESTION, max_distance=0.5)

    assert [source.section_id for source in selection.sources] == [english.pk]


def test_near_pieces_alone_do_not_merge_language_editions(
    device: Device, fake_embedder: FakeEmbedder, settings: Settings
) -> None:
    settings.TWOX_ANSWER_TRANSLATION_DISTANCE = 0.1
    # Identical near pieces, but section vectors 0.25 apart (axes 3 and 4 at
    # 30 degrees): two sources, because the merge reads the section vectors.
    first = add_long(device, "Manual", at_angle(30, axis=3), [at_angle(70)] * 2 + [at_angle(8)])
    second = add_long(device, "Handbuch", at_angle(30, axis=4), [at_angle(70)] * 2 + [at_angle(8)])

    selection = select_context(QUESTION, max_distance=0.5)

    assert {source.section_id for source in selection.sources} == {first.pk, second.pk}
