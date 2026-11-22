"""Reciprocal Rank Fusion of keyword and vector list (050).

The expected orders and scores are worked out by hand in the comments, with
``k = 60``: a list adds ``1 / (60 + rank)``. All texts are written for these
tests; none comes from a manufacturer's manual.
"""

import pytest
from pytest_django.fixtures import Settings

from tests.search.fake_embedder import FakeEmbedder, at_angle, embed
from tests.search.test_keyword_search import (
    add_sections,
    make_device,
    make_document,
    make_plant,
    search,
    sha256_of,
)
from twox.assets.models import Device, Plant
from twox.files.models import DocumentVersion
from twox.ingest.models import Section
from twox.search.interface import MatchKind
from twox.search.postgres import RRF_K

pytestmark = pytest.mark.django_db

KEYWORD = [MatchKind.KEYWORD]
SEMANTIC = [MatchKind.SEMANTIC]
BOTH = [MatchKind.KEYWORD, MatchKind.SEMANTIC]


def rrf(*ranks: int) -> float:
    return sum(1 / (RRF_K + rank) for rank in ranks)


@pytest.fixture
def plant() -> Plant:
    return make_plant()


@pytest.fixture
def device(plant: Plant) -> Device:
    return make_device(plant, "plc-01")


@pytest.fixture
def version(device: Device) -> DocumentVersion:
    return make_document(device)


@pytest.fixture
def gearbox(version: DocumentVersion) -> dict[str, Section]:
    """Four sections: keyword order A, B, C (D lacks the word); vector order C, D, B, A."""
    a, b, c, d = add_sections(
        version,
        "The gearbox needs oil.",
        "Check the gearbox. Clean the gearbox.",
        "Look at the gearbox now and then, together with the belt.",
        "Change the lubricant every year.",
    )
    # Heading "Gearbox" (weight A) puts A first, two mentions put B before C.
    Section.objects.filter(pk=a.pk).update(heading_path=["Gearbox"], heading_text="Gearbox")
    for section, degrees in ((c, 10), (d, 20), (b, 30), (a, 40)):
        embed(section, at_angle(degrees))
    return {"A": a, "B": b, "C": c, "D": d}


def names(sections: dict[str, Section], section_ids: list[int]) -> list[str]:
    by_id = {section.pk: name for name, section in sections.items()}
    return [by_id[section_id] for section_id in section_ids]


def test_keyword_list_alone_keeps_its_order(gearbox: dict[str, Section]) -> None:
    # AI features off: one list, ranks 1, 2, 3.
    result = search("gearbox")

    assert result.semantic_used is False
    assert names(gearbox, [hit.section_id for hit in result.hits]) == ["A", "B", "C"]
    assert [hit.score for hit in result.hits] == pytest.approx([rrf(1), rrf(2), rrf(3)])
    assert all(hit.match_kinds == KEYWORD for hit in result.hits)


def test_fusion_order_worked_out_by_hand(
    gearbox: dict[str, Section], fake_embedder: FakeEmbedder
) -> None:
    # keyword ranks: A 1, B 2, C 3;  vector ranks: C 1, D 2, B 3, A 4
    # C = 1/63 + 1/61 = 0.032266
    # A = 1/61 + 1/64 = 0.032018
    # B = 1/62 + 1/63 = 0.032002
    # D = 1/62        = 0.016129
    result = search("gearbox")

    assert result.semantic_used is True
    assert names(gearbox, [hit.section_id for hit in result.hits]) == ["C", "A", "B", "D"]
    assert [hit.score for hit in result.hits] == pytest.approx(
        [0.032266, 0.032018, 0.032002, 0.016129], abs=1e-6
    )
    assert [hit.score for hit in result.hits] == pytest.approx(
        [rrf(3, 1), rrf(1, 4), rrf(2, 3), rrf(2)]
    )
    assert [hit.match_kinds for hit in result.hits] == [BOTH, BOTH, BOTH, SEMANTIC]
    assert fake_embedder.calls == ["gearbox"]


def test_exact_hits_stay_on_top(version: DocumentVersion, fake_embedder: FakeEmbedder) -> None:
    exact, nearest, other = add_sections(
        version,
        "Set PLC-07 to run mode before the test.",
        "Switch the controller into operation first.",
        "The belt runs slowly.",
    )
    # The section with the identifier has no embedding; another one is the
    # nearest by vector. exact = 1 + 1/61 (keyword rank 1); nearest = 1/61.
    embed(nearest, at_angle(0))
    embed(other, at_angle(60))

    result = search("PLC-07")

    assert [hit.section_id for hit in result.hits] == [exact.pk, nearest.pk, other.pk]
    assert result.hits[0].match_kinds == [MatchKind.EXACT, MatchKind.KEYWORD]
    assert result.hits[0].score == pytest.approx(1 + rrf(1))
    assert result.hits[1].score == pytest.approx(rrf(1))
    assert result.hits[2].score == pytest.approx(rrf(2))
    assert result.hits[0].score >= 1 > result.hits[1].score


def test_same_content_is_merged_after_the_fusion(plant: Plant, fake_embedder: FakeEmbedder) -> None:
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    shared = sha256_of("shared manual")
    (one,) = add_sections(make_document(first, sha256=shared), "Grease the chain.")
    (two,) = add_sections(make_document(second, sha256=shared), "Grease the chain.")
    (other,) = add_sections(make_document(first, title="Notes"), "Grease the hinge.")
    embed(one, at_angle(10))
    embed(two, at_angle(10))
    embed(other, at_angle(30))

    hits = search("grease").hits

    # All three have the same ts_rank (one mention, same weight): keyword rank 1.
    # Both copies have the same distance: vector rank 1, the hinge rank 2.
    # Equal values share a rank, so the copies do not push the hinge down.
    assert [hit.section_id for hit in hits] == [one.pk, other.pk]
    assert [location.device_key for location in hits[0].locations] == ["plc-01", "plc-02"]
    assert hits[0].match_kinds == BOTH
    assert hits[0].score == pytest.approx(rrf(1, 1))
    assert hits[1].score == pytest.approx(rrf(1, 2))


def test_fusion_without_keyword_match_uses_the_vector_rank_only(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    near, far = add_sections(version, "Tighten the screws.", "Clean the filter.")
    embed(near, at_angle(5))
    embed(far, at_angle(50))

    hits = search("fasten bolts").hits

    assert [hit.section_id for hit in hits] == [near.pk, far.pk]
    assert [hit.score for hit in hits] == pytest.approx([rrf(1), rrf(2)])
    assert all(hit.match_kinds == SEMANTIC for hit in hits)


@pytest.mark.parametrize("ai_enabled", [False, True])
def test_switch_decides_whether_the_vector_list_takes_part(
    settings: Settings,
    gearbox: dict[str, Section],
    fake_embedder: FakeEmbedder,
    ai_enabled: bool,
) -> None:
    settings.TWOX_AI_ENABLED = ai_enabled

    result = search("gearbox")

    expected = ["C", "A", "B", "D"] if ai_enabled else ["A", "B", "C"]
    assert names(gearbox, [hit.section_id for hit in result.hits]) == expected
    assert result.semantic_used is ai_enabled
    assert fake_embedder.calls == (["gearbox"] if ai_enabled else [])
