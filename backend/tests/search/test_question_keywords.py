"""Keyword search for questions (143, D12 b): any word, no stop words, every word first.

All texts are written for these tests; none comes from a manufacturer's
manual. Scores are worked out by hand in the comments, with ``k = 60``.
"""

import hashlib

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from pytest_django import DjangoAssertNumQueries

from tests.search.fake_embedder import FakeEmbedder, at_angle, embed
from tests.search.test_keyword_search import (
    add_sections,
    highlighted,
    make_device,
    make_document,
    make_plant,
    search,
)
from twox.assets.models import Device, Plant
from twox.files.models import DocumentVersion
from twox.ingest.models import Section
from twox.search.interface import MatchKind
from twox.search.postgres import (
    QUESTION_RANK_WEIGHTS,
    RRF_K,
    _build_question,
    _parse_question,
    is_question,
    query_units,
)

pytestmark = pytest.mark.django_db

#: A question in the pattern of test question 3, in words of its own.
QUESTION = "Über welches Protokoll tauschen die Roboter Daten mit dem Leitrechner aus?"


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


def ids(sections: list[Section]) -> list[int]:
    return [section.pk for section in sections]


def hit_ids(query: str) -> list[int]:
    return [hit.section_id for hit in search(query).hits]


def matches_every_word(section: Section, query: str) -> bool:
    """Whether the full-text search of 047 (every word, per configuration) matches."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT bool_or(s.search_vector @@ websearch_to_tsquery(c::regconfig, %(q)s))"
            " FROM ingest_section s, unnest(ARRAY['simple', 'german', 'english']) AS c"
            " WHERE s.id = %(id)s",
            {"q": query, "id": section.pk},
        )
        row = cursor.fetchone()
    assert row is not None
    return bool(row[0])


# --- Which queries are questions, and their words ----------------------------


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("192.168.0.100", False),
        ("E1234", False),
        ("Fehler E1234", False),
        ("PLC-01 Adresse", False),
        ("Pumpe", False),
        ("pump -valve -gear", False),
        ("safety valve", True),
        ('"Ventil öffnen"', True),
        (QUESTION, True),
        ("Was bedeutet Fehler E1234?", True),
    ],
)
def test_question_rule_is_the_rule_of_e61(query: str, expected: bool) -> None:
    assert is_question(query) is expected


def test_query_units_keep_phrases_and_leave_out_exclusions() -> None:
    assert query_units('Wie "Ventil öffnen" -Heizung -"Filter wechseln" PLC-01? &') == [
        "Wie",
        '"Ventil öffnen"',
        "PLC-01?",
    ]
    assert query_units('offen "am Ende') == ["offen", '"am Ende']
    assert query_units("( ) ? -") == []


def test_question_without_stop_words_built_from_the_parsed_units() -> None:
    units = ["Wie", "tauscht", "man", "XR7", "Öl", "a&b", "x"]
    parsed = {
        "simple": ["'wie'", "'tauscht'", "'man'", "'xr7'", "'öl'", "'a' & 'b'", "!'x'"],
        "german": ["", "'tauscht'", "", "'xr7'", "'ol'", "'a' & 'b'", "!'x'"],
        "english": ["'wie'", "'tauscht'", "'man'", "'xr7'", "'öl'", "'b'", "!'x'"],
    }

    question = _build_question(units, parsed)

    # "Wie" and "man" are German stop words: gone in every configuration.
    # A unit with a negation is never a positive word. XR7 is an identifier:
    # not a matching word, but in "every" and in the ranking.
    assert question.matching.per_config == {
        "simple": "( 'tauscht' ) | ( 'öl' ) | ( 'a' & 'b' )",
        "german": "( 'tauscht' ) | ( 'ol' ) | ( 'a' & 'b' )",
        "english": "( 'tauscht' ) | ( 'öl' ) | ( 'b' )",
    }
    assert question.every.per_config["german"] == (
        "( 'tauscht' ) & ( 'xr7' ) & ( 'ol' ) & ( 'a' & 'b' )"
    )
    assert question.ranking.per_config["english"] == (
        "( 'tauscht' ) | ( 'xr7' ) | ( 'öl' ) | ( 'b' )"
    )


def test_question_of_identifiers_and_stop_words_matches_by_its_identifiers() -> None:
    question = _build_question(
        ["Was", "ist", "E1234?"],
        {
            "simple": ["'was'", "'ist'", "'e1234'"],
            "german": ["", "", "'e1234'"],
            "english": ["", "", "'e1234'"],
        },
    )

    assert question.matching.per_config == {
        "simple": "( 'e1234' )",
        "german": "( 'e1234' )",
        "english": "( 'e1234' )",
    }


def test_question_ranking_weights_put_headings_first() -> None:
    # {D, C, B, A}: a heading (A) counts five times a word of the text (B).
    assert QUESTION_RANK_WEIGHTS == (0.1, 0.2, 0.2, 1.0)


# --- A question finds sections with part of its words --------------------------


def test_question_finds_a_section_with_part_of_its_words(version: DocumentVersion) -> None:
    (part,) = add_sections(
        version, "Die Roboter senden ihre Messwerte an den Broker.", headings=["Kommunikation"]
    )
    add_sections(version, "Die Lampe leuchtet grün.", page=2)

    result = search(QUESTION)

    # Before 143 every word had to match in one configuration: nothing.
    assert matches_every_word(part, QUESTION) is False
    assert [hit.section_id for hit in result.hits] == [part.pk]
    assert result.hits[0].match_kinds == [MatchKind.KEYWORD]
    assert highlighted(result.hits[0]) == ["Roboter"]


def test_every_word_comes_before_part_of_the_words(version: DocumentVersion) -> None:
    # "every": Protokoll, Roboter, Daten, Leitrechner, tauschen (word forms).
    (part_in_heading,) = add_sections(
        version, "Die Roboter melden Daten.", headings=["Protokoll und Roboter"]
    )
    (every,) = add_sections(
        version,
        "Mit dem Leitrechner tauschen die Roboter Daten über ein Protokoll aus.",
        headings=["Netz"],
        page=2,
    )
    (one_word,) = add_sections(version, "Der Leitrechner steht im Schrank.", page=3)

    assert matches_every_word(every, QUESTION) is True
    # The headings rank part_in_heading above every by ts_rank alone; the
    # sections with every word still come first.
    assert hit_ids(QUESTION) == [every.pk, part_in_heading.pk, one_word.pk]


def test_words_in_the_heading_come_before_the_same_words_in_the_text(
    version: DocumentVersion,
) -> None:
    (in_text,) = add_sections(
        version, "Das Protokoll der Roboter ist dokumentiert.", headings=["Allgemein"]
    )
    (in_heading,) = add_sections(
        version, "Ist dokumentiert.", headings=["Protokoll der Roboter"], page=2
    )

    assert hit_ids(QUESTION) == [in_heading.pk, in_text.pk]


def test_heading_word_outranks_more_words_in_the_text(version: DocumentVersion) -> None:
    # One word of the question in the heading against three in the text:
    # with PostgreSQL's default weights (B 0.4) the text wins (rank 0.141
    # against 0.120), with QUESTION_RANK_WEIGHTS (B 0.2) the heading (0.076
    # against 0.120).
    (in_text,) = add_sections(
        version, "Die Roboter senden Daten an den Leitrechner.", headings=["Allgemein"]
    )
    (in_heading,) = add_sections(version, "Siehe Anhang.", headings=["Roboter"], page=2)

    with connection.cursor() as cursor:
        _, question = _parse_question(cursor, QUESTION)
        cursor.execute(
            "SELECT s.id FROM ingest_section s WHERE s.id = ANY(%(ids)s) ORDER BY"
            " ts_rank(s.search_vector, %(query)s::tsquery, 32) DESC",
            {"ids": [in_text.pk, in_heading.pk], "query": question.ranking.combined},
        )
        default_order = [row[0] for row in cursor.fetchall()]

    assert default_order == [in_text.pk, in_heading.pk]
    assert hit_ids(QUESTION) == [in_heading.pk, in_text.pk]


# --- Stop words ------------------------------------------------------------------


def test_stop_words_alone_find_nothing_and_mark_nothing(version: DocumentVersion) -> None:
    question = "Mit welchem Schlüssel öffnet man der Schaltschrank, the key?"
    (stop_words,) = add_sections(version, "Mit der Zange und welchem Draht: the end.")
    (content,) = add_sections(version, "Der Schaltschrank hat ein Schloss.", page=2)

    result = search(question)

    assert [hit.section_id for hit in result.hits] == [content.pk]
    assert stop_words.pk not in [hit.section_id for hit in result.hits]
    # "Der" is a word of the question as well, but a stop word: not marked.
    assert highlighted(result.hits[0]) == ["Schaltschrank"]


def test_english_stop_word_that_is_a_german_word_is_left_out(version: DocumentVersion) -> None:
    # "Not" (emergency) is a German noun, but an English stop word: a
    # question drops it in every configuration, so it finds nothing alone.
    add_sections(version, "Im Not-Fall den Raum verlassen. Not tut weh.")
    (cabinet,) = add_sections(version, "Der Schaltschrank hat ein Schloss.", page=2)

    assert hit_ids("Was tun bei Not am Schaltschrank?") == [cabinet.pk]


def test_question_of_stop_words_only_finds_nothing_by_keyword(version: DocumentVersion) -> None:
    add_sections(version, "Der die das, mit dem the.")

    assert search("der die das").hits == []
    assert search("Was ist das?").hits == []


# --- Exclusions and phrases --------------------------------------------------------


def test_exclusion_holds_in_a_question(version: DocumentVersion) -> None:
    keller, heizung, other = add_sections(
        version,
        "Die Pumpe im Keller wird über das Ventil entlüftet.",
        "Die Pumpe der Heizung wird über das Ventil entlüftet.",
        "Die Heizung läuft im Winter.",
    )

    # The excluded word is never a positive word of the question.
    assert hit_ids("Wie wird die Pumpe entlüftet -Heizung") == [keller.pk]
    assert other.pk not in hit_ids("Pumpe entlüften -Heizung")
    assert set(hit_ids("Wie wird die Pumpe entlüftet")) == {keller.pk, heizung.pk}


def test_excluded_phrase_holds_in_a_question(version: DocumentVersion) -> None:
    clean, change = add_sections(
        version,
        "Den Filter mit Druckluft reinigen.",
        "Filter wechseln und mit Druckluft reinigen.",
    )

    assert hit_ids('Wie reinigt man den Filter -"Filter wechseln"') == [clean.pk]
    assert set(hit_ids("Wie reinigt man den Filter")) == {clean.pk, change.pk}


def test_phrase_stays_a_phrase_in_a_question(version: DocumentVersion) -> None:
    reversed_order, in_order, other_word = add_sections(
        version,
        "Öffnen Sie zuerst das Ventil.",
        "Ventil öffnen, dann warten.",
        "Der Kühlkreis ist leer.",
    )

    # Three words beside no identifier: a question. "Ventil öffnen" matches
    # in this order only; "Kühlkreis" is a word of its own.
    result = hit_ids('"Ventil öffnen" Kühlkreis')

    assert set(result) == {in_order.pk, other_word.pk}
    assert reversed_order.pk not in result


def test_phrase_in_a_question_does_not_match_across_the_seam(version: DocumentVersion) -> None:
    (section,) = add_sections(version, "Ventil öffnen")

    # The joined vector has "öffnen" (simple) right before "Ventil" (german);
    # the check per configuration still rejects that seam.
    assert search('"öffnen Ventil" Kühlkreis').hits == []
    assert hit_ids('"Ventil öffnen" Kühlkreis') == [section.pk]


# --- Queries that are no questions stay as they were -------------------------------

#: SHA-256 of the SQL (parameters filled in) of the parse and the search query,
#: recorded with the code before 143 (AI features off).
UNCHANGED_SQL = {
    "192.168.0.100": "ac1c76b8f665b86ed0eef4e9dc396a55f3f11e0ad238454f294927bc0eaebd6f",
    "E1234": "1b2ea9a8808e3d22986aa827e3906e04993c8657437dd03fe7fc0b0876a45819",
    "Fehler E1234": "1277f2e373980a9a59e4576983fb3f0eb5e5dc654ae659f0fd0f884386f54d68",
    "PLC-01 Adresse": "3a019f3aea7b55bd3a8cce2f5708cde0e9f8dd25eadec6734898f9260301189b",
    "Pumpe": "9c0167ae74cd31b6558047aa39ecdfa60bb6b1957fed8b00948b0f60d77d52b0",
    "pump -valve": "ae582929992ab75c0167eeeb0fb0b7a4dc38cce1e6a56d6a4802510869dcd256",
}


def sql_digest(query: str) -> str:
    with CaptureQueriesContext(connection) as captured:
        search(query)
    parse_and_search = [item["sql"] for item in captured.captured_queries[:2]]
    return hashlib.sha256("\n;\n".join(parse_and_search).encode()).hexdigest()


@pytest.fixture
def corpus(version: DocumentVersion) -> dict[str, Section]:
    texts = {
        "ccu": ("Die Zentrale hat die Adresse 192.168.0.100.", ["Netz"]),
        "ccu-table": ("| CCU | 192.168.0.100 | 255.255.255.0 |", ["Adressen"]),
        "ccu-other": ("Die Adresse 192.168.0.101 gehört zum Bohrer.", ["Netz"]),
        "fault": ("Fehler E1234: die Tür ist offen.", ["Fehler"]),
        "fault-en": ("Fault E1234 means the door is open.", ["Faults"]),
        "plc": ("Die Adresse von PLC-01 steht im Plan.", ["PLC-01"]),
        "plc-pump": ("PLC-01 steuert die Pumpe.", ["Steuerung"]),
        "pump": ("Die Pumpe läuft. Pumpen brauchen Öl.", ["Pumpe"]),
        "pump-valve": ("The pump opens the valve.", ["Pumps"]),
        "pump-en": ("The pump runs quietly.", ["Pumps"]),
    }
    sections = {}
    for page, (name, (text, headings)) in enumerate(texts.items(), start=1):
        (sections[name],) = add_sections(version, text, headings=headings, page=page)
    return sections


#: Hits of each query on :func:`corpus`, best first, recorded with the code before 143.
UNCHANGED_HITS = {
    "192.168.0.100": ["ccu", "ccu-table"],
    "E1234": ["fault", "fault-en"],
    "Fehler E1234": ["fault", "fault-en"],
    "PLC-01 Adresse": ["plc", "plc-pump"],
    "Pumpe": ["pump", "pump-valve", "pump-en", "plc-pump"],
    "pump -valve": ["pump", "pump-en", "plc-pump"],
}


@pytest.mark.parametrize("query", list(UNCHANGED_HITS))
def test_queries_that_are_no_questions_keep_hits_and_order(
    corpus: dict[str, Section], query: str
) -> None:
    by_id = {section.pk: name for name, section in corpus.items()}
    hits = search(query).hits

    assert [by_id[hit.section_id] for hit in hits] == UNCHANGED_HITS[query]


@pytest.mark.parametrize("query", list(UNCHANGED_SQL))
def test_queries_that_are_no_questions_keep_their_sql(version: DocumentVersion, query: str) -> None:
    add_sections(version, "Die Pumpe an 192.168.0.100 meldet E1234.")

    assert sql_digest(query) == UNCHANGED_SQL[query]


# --- Number of queries and fusion ----------------------------------------------------


def test_question_needs_three_queries(
    version: DocumentVersion, django_assert_num_queries: DjangoAssertNumQueries
) -> None:
    add_sections(version, *(f"Die Roboter senden Daten {index}." for index in range(5)))

    # Parse the question and its words, search, find the highlights.
    with django_assert_num_queries(3):
        assert len(search(QUESTION).hits) == 5


def test_question_rises_in_the_fusion_by_its_keyword_rank(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    near, second, evidence = add_sections(
        version,
        "Die Lampe leuchtet grün.",
        "Das Band stoppt am Ende.",
        "Jede Station sendet ihre Messwerte per MQTT an den Broker.",
    )
    Section.objects.filter(pk=evidence.pk).update(
        heading_path=["Protokolle der Roboter"], heading_text="Protokolle der Roboter"
    )
    for section, degrees in ((near, 10), (second, 20), (evidence, 30)):
        embed(section, at_angle(degrees))

    hits = search(QUESTION).hits

    # vector: near 1, second 2, evidence 3; keyword (headings): evidence 1.
    # evidence = 1/61 + 1/63 = 0.032266 (vector only, before 143: 1/63, rank 3)
    # near     = 1/61        = 0.016393
    # second   = 1/62        = 0.016129
    assert [hit.section_id for hit in hits] == [evidence.pk, near.pk, second.pk]
    assert [hit.score for hit in hits] == pytest.approx([rrf(1, 3), rrf(1), rrf(2)])
    assert [hit.score for hit in hits] == pytest.approx([0.032266, 0.016393, 0.016129], abs=1e-6)
    assert hits[0].match_kinds == [MatchKind.KEYWORD, MatchKind.SEMANTIC]


def test_section_naming_only_the_product_of_a_question_gets_no_keyword_rank(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    # E-61: the identifier of a question counts only through the keyword and
    # the vector list. A section that only names XR7 is no keyword hit of the
    # question, so it does not pass the best section by meaning.
    answer, naming = add_sections(
        version, "Die Traglast beträgt 5 kg.", "Der XR7 hat ein graues Gehäuse."
    )
    embed(answer, at_angle(10))
    embed(naming, at_angle(20))

    hits = search("Welche Traglast hat der XR7?").hits

    # answer = keyword 1 + vector 1 = 1/61 + 1/61; naming = vector 2 = 1/62.
    assert [hit.section_id for hit in hits] == [answer.pk, naming.pk]
    assert [hit.score for hit in hits] == pytest.approx([rrf(1, 1), rrf(2)])
    assert hits[1].match_kinds == [MatchKind.EXACT, MatchKind.SEMANTIC]
