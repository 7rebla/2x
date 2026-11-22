"""Reciprocal Rank Fusion of keyword and vector list (050) and of the exact hits (063).

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
from twox.answers.embeddings import EmbeddingUnavailableError
from twox.assets.models import Device, Plant
from twox.files.models import DocumentVersion
from twox.ingest.models import Section
from twox.search.identifiers import find_identifiers
from twox.search.interface import MatchKind
from twox.search.postgres import (
    EXACT_FIRST_MAX_OTHER_WORDS,
    RRF_K,
    exact_hits_first,
    other_words,
)

pytestmark = pytest.mark.django_db

KEYWORD = [MatchKind.KEYWORD]
SEMANTIC = [MatchKind.SEMANTIC]
BOTH = [MatchKind.KEYWORD, MatchKind.SEMANTIC]
EXACT = [MatchKind.EXACT]
EXACT_SEMANTIC = [MatchKind.EXACT, MatchKind.SEMANTIC]
ALL_THREE = [MatchKind.EXACT, MatchKind.KEYWORD, MatchKind.SEMANTIC]


def rrf(*ranks: float) -> float:
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


# --- Exact hits: first, or a third list of the fusion (063) -----------------


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("192.168.0.5", True),
        ("E1234", True),
        ("Fehler E1234", True),
        ("PLC-01 PLC-02", True),
        ("Adresse 192.168.0.5 -alt", True),
        ('"XR7" & Öl', True),
        ("XR7 Getriebeöl wechseln", False),
        ("Wie tausche ich beim XR7 das Getriebeöl?", False),
        ("Wie viel trägt der UR5e?", False),
    ],
)
def test_rule_exact_hits_first_for_queries_of_identifiers(query: str, expected: bool) -> None:
    identifiers = find_identifiers(query)

    assert exact_hits_first(query, identifiers, vector_list=True) is expected
    # Without a vector list exact hits always come first, as before 063.
    assert exact_hits_first(query, identifiers, vector_list=False) is True


def test_other_words_are_the_words_beside_the_identifiers() -> None:
    assert EXACT_FIRST_MAX_OTHER_WORDS == 1
    assert other_words("Wie viel trägt der UR5e?") == ["Wie", "viel", "trägt", "der"]
    # Exclusions and tokens without a letter or digit are not words.
    assert other_words('Adresse 192.168.0.5 -alt -"zwei Wörter" &') == ["Adresse"]
    assert other_words('"Fehler E1234" -"altes Gerät"') == ['"Fehler']
    assert other_words("(E1234).") == []
    # A query without identifiers has nothing to put first.
    assert exact_hits_first("Getriebeöl wechseln", [], vector_list=True) is True


@pytest.fixture
def xr7(version: DocumentVersion) -> dict[str, Section]:
    """Five sections for the query "XR7 Getriebeöl wechseln" (two words beside XR7: fused).

    keyword (every word, XR7 also in a heading): A 1 (XR7 in the heading,
    weight A), B 2; exact (XR7 in the text): B, C, D; vector: B 1, A 2, C 3,
    E 4 (D has no embedding).
    """
    a, b, c, d, e = add_sections(
        version,
        "Getriebeöl wechseln: die Ablassschraube lösen und das Öl auffangen.",
        "Beim XR7 das Getriebeöl alle zwei Jahre wechseln.",
        "Der XR7 wiegt 40 kg.",
        "Das Typenschild des XR7 sitzt hinten.",
        "Öl nur bei Stillstand nachfüllen.",
    )
    Section.objects.filter(pk=a.pk).update(heading_path=["XR7"], heading_text="XR7")
    for section, degrees in ((b, 10), (a, 20), (c, 30), (e, 40)):
        embed(section, at_angle(degrees))
    return {"A": a, "B": b, "C": c, "D": d, "E": e}


def test_exact_list_fused_worked_out_by_hand(
    xr7: dict[str, Section], fake_embedder: FakeEmbedder
) -> None:
    # Exact list, ranked by the number of identifiers, then by keyword rank:
    # B (1 identifier, keyword rank 2) place 1; C and D (1 identifier, no
    # keyword rank) tie for places 2 and 3 and share their mean, rank 2.5.
    # A = keyword 1 + vector 2           = 1/61 + 1/62          = 0.032522
    # B = exact 1 + keyword 2 + vector 1 = 1/61 + 1/62 + 1/61   = 0.048916
    # C = exact 2.5 + vector 3           = 1/62.5 + 1/63        = 0.031873
    # D = exact 2.5                      = 1/62.5               = 0.016000
    # E = vector 4                       = 1/64                 = 0.015625
    result = search("XR7 Getriebeöl wechseln")

    assert result.semantic_used is True
    assert names(xr7, [hit.section_id for hit in result.hits]) == ["B", "A", "C", "D", "E"]
    assert [hit.score for hit in result.hits] == pytest.approx(
        [0.048916, 0.032522, 0.031873, 0.016000, 0.015625], abs=1e-6
    )
    assert [hit.score for hit in result.hits] == pytest.approx(
        [rrf(1, 2, 1), rrf(1, 2), rrf(2.5, 3), rrf(2.5), rrf(4)]
    )
    assert [hit.match_kinds for hit in result.hits] == [
        ALL_THREE,
        BOTH,
        EXACT_SEMANTIC,
        EXACT,
        SEMANTIC,
    ]
    # No score reaches 1: no hit comes first just for naming XR7.
    assert all(hit.score < 1 for hit in result.hits)


def test_exact_hits_still_come_first_with_ai_off(xr7: dict[str, Section]) -> None:
    # Unchanged keyword and exact search: identifiers found + 1/(60 + keyword rank).
    # B = 1 + 1/62, C = 1, D = 1 (C before D by ID), A = 1/61; E is no hit.
    result = search("XR7 Getriebeöl wechseln")

    assert result.semantic_used is False
    assert names(xr7, [hit.section_id for hit in result.hits]) == ["B", "C", "D", "A"]
    assert [hit.score for hit in result.hits] == pytest.approx([1 + rrf(2), 1, 1, rrf(1)])


def test_exact_hits_come_first_when_the_model_service_fails(
    xr7: dict[str, Section], fake_embedder: FakeEmbedder
) -> None:
    fake_embedder.error = EmbeddingUnavailableError("model service not reachable")

    result = search("XR7 Getriebeöl wechseln")

    assert result.semantic_used is False
    assert names(xr7, [hit.section_id for hit in result.hits]) == ["B", "C", "D", "A"]
    assert [hit.score for hit in result.hits] == pytest.approx([1 + rrf(2), 1, 1, rrf(1)])


@pytest.mark.parametrize(
    ("query", "text", "exact_score"),
    [
        # Only the identifier: found exactly and by keyword (rank 1).
        ("192.168.0.5", "The card answers on 192.168.0.5 after the start.", 1 + rrf(1)),
        ("E1234", "Fault E1234: the door is open.", 1 + rrf(1)),
        # One more word: still a lookup; "Fehler" is not in the text, so no keyword hit.
        ("Fehler E1234", "Fault E1234: the door is open.", 1),
    ],
)
def test_queries_of_identifiers_keep_exact_hits_first(
    version: DocumentVersion,
    fake_embedder: FakeEmbedder,
    query: str,
    text: str,
    exact_score: float,
) -> None:
    exact, near, other = add_sections(
        version, text, "Close the door before the start.", "The belt runs slowly."
    )
    # The exact hit is the farthest by meaning; another section is the nearest.
    embed(near, at_angle(0))
    embed(other, at_angle(30))
    embed(exact, at_angle(80))

    result = search(query)

    assert [hit.section_id for hit in result.hits][:3] == [exact.pk, near.pk, other.pk]
    assert MatchKind.EXACT in result.hits[0].match_kinds
    # exact: identifiers found + keyword part + vector rank 3.
    assert result.hits[0].score == pytest.approx(exact_score + rrf(3))
    assert result.hits[1].score == pytest.approx(rrf(1))
    assert result.hits[0].score >= 1 > result.hits[1].score


def test_tie_between_exact_list_and_vector_list_goes_to_the_meaning(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    # Three words beside E1234: fused. The only exact hit has exact rank 1, the
    # nearest section vector rank 1: both 1/61. The nearer in meaning comes first.
    exact, near = add_sections(
        version, "Fault E1234: the door is open.", "Close the door before the start."
    )
    embed(near, at_angle(0))

    hits = search("Was bedeutet Fehler E1234?").hits

    assert [hit.section_id for hit in hits] == [near.pk, exact.pk]
    assert [hit.score for hit in hits] == pytest.approx([rrf(1), rrf(1)])
    assert [hit.match_kinds for hit in hits] == [SEMANTIC, EXACT]


def test_same_content_counts_once_in_the_exact_list(
    plant: Plant, fake_embedder: FakeEmbedder
) -> None:
    # The same manual on two devices: its exact hit is one place of the exact
    # list, not two. Exact list: the shared section and the note tie for places
    # 1 and 2 (rank 1.5 each); counted per row, it would be 2 for all three.
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    shared = sha256_of("shared manual")
    (one,) = add_sections(make_document(first, sha256=shared), "The XR7 weighs 40 kg.")
    (two,) = add_sections(make_document(second, sha256=shared), "The XR7 weighs 40 kg.")
    (note,) = add_sections(make_document(first, title="Notes"), "Mount the XR7 on a wall.")
    (near,) = add_sections(make_document(first, title="Care"), "Keep the gear oil clean.")
    embed(near, at_angle(0))

    hits = search("How heavy is the XR7?").hits

    assert [hit.section_id for hit in hits] == [near.pk, one.pk, note.pk]
    assert [hit.score for hit in hits] == pytest.approx([rrf(1), rrf(1.5), rrf(1.5)])
    assert [location.section_id for location in hits[1].locations] == [one.pk, two.pk]
