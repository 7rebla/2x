"""Citation check of generated answers (123).

All texts are made up for a neutral example machine (gripper G-12); none is
taken from a manual.
"""

import time

import pytest

from twox.answers import citations
from twox.answers.citations import (
    CONTRADICTION_PHRASE,
    NO_EVIDENCE_TEXT,
    UNITS,
    SentenceIssue,
    Verdict,
    _split_sentences,
    normalise_value,
    verify,
)

SOURCES: dict[int, str] = {
    1: "Der Greifer G-12 wiegt 5 kg. Die Versorgung erfolgt mit 24 V DC.",
    2: "Die Steuerung hat die Adresse 10.0.0.7 und antwortet auf Port 502. Firmware V2.3.1.",
    3: "Der Arbeitsdruck betraegt 0,5 bar. Das Modul S7-1200 ist vorgesehen.",
    4: "Das Bediengeraet hat die Adresse 192.168.0.50. Die Last darf 25 kg betragen.",
    5: "Laut Blatt B betraegt die Versorgung 48 V.",
}

OPENING_QUOTE = chr(0x201E)
CLOSING_QUOTE = chr(0x201C)


def sentences_of(text: str) -> list[str]:
    lines = text.split("\n")
    return [lines[s.line][s.start : s.end] for s in _split_sentences(lines)]


def reasons(verdict: Verdict) -> list[tuple[int, str]]:
    return [(issue.index, issue.reason) for issue in verdict.removed_sentences]


# 1. Invented source numbers


def test_sentence_with_only_an_invented_number_is_unknown_citation() -> None:
    verdict = verify("Der Greifer wiegt 5 kg [9].", SOURCES, drop_unsupported=True)
    assert verdict.status == "no_evidence"
    assert verdict.cited == ()
    assert verdict.removed_sentences == (
        SentenceIssue(
            index=0, reason="unknown_citation", values=(), invalid_numbers=(9,), kept=False
        ),
    )
    assert verdict.cleaned_text == NO_EVIDENCE_TEXT


@pytest.mark.parametrize(
    ("sentence", "kept"),
    [
        ("Die Adresse ist 10.0.0.7 [2][9].", "Die Adresse ist 10.0.0.7 [2]."),
        ("Die Adresse ist 10.0.0.7 [9][2].", "Die Adresse ist 10.0.0.7 [2]."),
        ("Die Adresse ist 10.0.0.7 [2, 9].", "Die Adresse ist 10.0.0.7 [2]."),
        ("Die Adresse ist 10.0.0.7 [9; 2].", "Die Adresse ist 10.0.0.7 [2]."),
        ("Die Adresse ist 10.0.0.7 [9] [2].", "Die Adresse ist 10.0.0.7 [2]."),
    ],
)
def test_invented_number_is_removed_from_a_supported_sentence(sentence: str, kept: str) -> None:
    answer = f"{sentence} Der Greifer wiegt 5 kg [9]."
    verdict = verify(answer, SOURCES, drop_unsupported=True)
    assert verdict.status == "answered"
    assert verdict.cited == (2,)
    assert verdict.cleaned_text == kept
    assert verdict.removed_sentences == (
        SentenceIssue(
            index=0, reason="unknown_citation", values=(), invalid_numbers=(9,), kept=True
        ),
        SentenceIssue(
            index=1, reason="unknown_citation", values=(), invalid_numbers=(9,), kept=False
        ),
    )
    assert len(verdict.removed_sentences) == 2
    assert verdict.dropped_count == 1


def test_dropped_count_counts_unsupported_sentences_only() -> None:
    answer = "Die Adresse ist 10.0.0.7 [2][9]. Er wiegt 7 kg [1]. Er ist blau."
    for drop in (True, False):
        verdict = verify(answer, SOURCES, drop_unsupported=drop)
        assert [issue.kept for issue in verdict.removed_sentences] == [True, False, False]
        assert verdict.dropped_count == 2


# 2. Values that are not in a cited source


def test_no_identifier_is_skipped_after_ten() -> None:
    addresses = [f"10.0.1.{n}" for n in range(1, 12)]
    source = "Adressen: " + ", ".join(addresses[:10])
    answer = "Die Adressen sind " + ", ".join(addresses) + " [1]."
    verdict = verify(answer, {1: source}, drop_unsupported=True)
    assert verdict.status == "no_evidence"
    assert verdict.removed_sentences == (
        SentenceIssue(
            index=0,
            reason="unsupported_value",
            values=("10.0.1.11",),
            invalid_numbers=(),
            kept=False,
        ),
    )


def test_identifier_with_leading_dash_is_checked() -> None:
    verdict = verify(
        "Das Relais -K7 schaltet [1].", {1: "Das Relais -K3 schaltet."}, drop_unsupported=True
    )
    assert verdict.status == "no_evidence"
    assert verdict.removed_sentences[0].values == ("K7",)
    supported = verify(
        "Das Relais -K3 schaltet [1].", {1: "Das Relais -K3 schaltet."}, drop_unsupported=True
    )
    assert supported.status == "answered"


@pytest.mark.parametrize(
    ("answer", "source", "status"),
    [
        ("Vorgesehen ist S7 1500 [1].", "Das Modul S7-1200 ist vorgesehen.", "no_evidence"),
        ("Vorgesehen ist S7 1200 [1].", "Das Modul S7-1200 ist vorgesehen.", "answered"),
        ("Vorgesehen ist S7 1200. [1]", "Das Modul S7 1200 ist vorgesehen.", "answered"),
        # Words before a number are not joined with it.
        ("Siehe Seite 34 und Port 502 [1].", "Port 502 laut Handbuch.", "answered"),
        # Digits that start a number with a unit stay apart.
        ("Der Greifer G-12 traegt 5 kg [1].", "Greifer G-12, Last 5 kg.", "answered"),
        ("Greifer G-12 5 kg zulaessig [1].", "Greifer G-12, Last 5 kg.", "answered"),
    ],
)
def test_type_designation_with_separate_digits_is_one_value(
    answer: str, source: str, status: str
) -> None:
    assert verify(answer, {1: source}, drop_unsupported=True).status == status


@pytest.mark.parametrize(
    ("answer", "source", "status"),
    [
        ("Die Temperatur betraegt -20 °C [1].", "Die Temperatur betraegt 20 °C.", "no_evidence"),
        ("Die Temperatur betraegt 20 °C [1].", "Die Temperatur betraegt -20 °C.", "no_evidence"),
        ("Die Temperatur betraegt -20 °C [1].", "Die Temperatur betraegt -20 °C.", "answered"),
        ("Der Bereich ist 2-5 kg [1].", "Last 2-5 kg.", "answered"),
        ("Die S7-1200-Steuerung ist vorgesehen [1].", "Modul S7-1200.", "answered"),
        ("Die S7-1500-Steuerung ist vorgesehen [1].", "Modul S7-1200.", "no_evidence"),
        ("Die 24-V-Versorgung ist vorgesehen [1].", "Versorgung 24 V DC.", "answered"),
        ("Die 48-V-Versorgung ist vorgesehen [1].", "Versorgung 24 V DC.", "no_evidence"),
    ],
)
def test_signs_and_compound_words(answer: str, source: str, status: str) -> None:
    assert verify(answer, {1: source}, drop_unsupported=True).status == status


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("S7 1200", "s71200"),
        ("S7-1200", "s71200"),
        ("0,5 bar", "0.5bar"),
        ("5 KG", "5kg"),
        ("-20 °C", chr(0x2212) + "20°c"),
    ],
)
def test_normalise_value(text: str, key: str) -> None:
    assert normalise_value(text) == key


@pytest.mark.parametrize(
    ("answer", "missing"),
    [
        ("Die Steuerung hat die Adresse 10.0.0.8 [2].", ("10.0.0.8",)),
        # Only in source 4, which the sentence does not cite.
        ("Das Bediengeraet hat die Adresse 192.168.0.50 [2].", ("192.168.0.50",)),
        # Source 4 holds 192.168.0.50 only.
        ("Das Bediengeraet hat die Adresse 192.168.0.5 [4].", ("192.168.0.5",)),
        ("Die Steuerung hat die MAC-Adresse 00:1b:1b:aa:bb:cc [2].", ("00:1b:1b:aa:bb:cc",)),
        ("Die Steuerung antwortet auf Port 503 [2].", ("503",)),
        ("Der Greifer G-14 wiegt 5 kg [1].", ("G-14",)),
    ],
)
def test_value_missing_from_the_cited_sources_is_unsupported(
    answer: str, missing: tuple[str, ...]
) -> None:
    verdict = verify(answer, SOURCES, drop_unsupported=True)
    assert verdict.status == "no_evidence"
    assert verdict.removed_sentences == (
        SentenceIssue(
            index=0, reason="unsupported_value", values=missing, invalid_numbers=(), kept=False
        ),
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Die Steuerung hat die Adresse 10.0.0.7 [2].",
        "Das Bediengeraet hat die Adresse 192.168.0.50 [2][4].",
        "Die Steuerung antwortet auf Port 502 [2].",
        "Der Greifer G-12 wiegt 5 kg und braucht 24 V [1].",
        "Die Firmware ist V2.3.1 [2].",
        "Der Greifer ist leicht [1].",
    ],
)
def test_value_in_a_cited_source_is_supported(answer: str) -> None:
    verdict = verify(answer, SOURCES, drop_unsupported=True)
    assert verdict.status == "answered"
    assert verdict.removed_sentences == ()
    assert verdict.cleaned_text == answer


# 3. Normalisation and boundaries


@pytest.mark.parametrize(
    ("source", "value", "found"),
    [
        ("Gewicht 5 kg", "5kg", True),
        ("Gewicht 5kg", "5 kg", True),
        ("Druck 0,5 bar", "0.5 bar", True),
        ("Druck 0.5 bar", "0,5 bar", True),
        ("Typ S7-1200", "S7 1200", True),
        ("Typ S7 1200", "S7-1200", True),
        (f"Typ S7{chr(0x2011)}1200", "S7-1200", True),
        ("Typ S7-1200", f"S7{chr(0x2013)}1200", True),
        ("Laenge 1.5 mm", "1,5 mm", True),
        ("Temperatur 20 °C", "20°C", True),
        ("Versorgung 24 VDC", "24 V", True),
        ("Versorgung 24 V", "24 V DC", True),
        ("Version 18", "V18", True),
        ("V2.3.1", "Version 2.3.1", True),
        ("Adresse 10.0.0.7:502", "Port 502", True),
        ("Adresse 10.0.0.7:502", "10.0.0.7", True),
        ("Adresse 10.0.0.7.", "10.0.0.7", True),
        ("Adresse fe80::1/64", "fe80::1/64", True),
        ("Typ ur5e", "UR5e", True),
        ("Last 25 kg", "5 kg", False),
        ("Last 5.5 kg", "5 kg", False),
        ("Adresse 192.168.0.50", "192.168.0.5", False),
        ("Adresse 10.192.168.0.5", "192.168.0.5", False),
        ("Adresse 192.168.0.5.1", "192.168.0.5", False),
        ("Adresse fe80::1:5", "fe80::1", False),
        ("Port 502", "Port 5020", False),
        ("Typ S7-1500", "S7-1200", False),
        ("Typ 1512SPX", "1512SP", False),
        ("Strom 16 A", "6 A", False),
    ],
)
def test_values_are_compared_normalised_with_boundaries(
    source: str, value: str, found: bool
) -> None:
    verdict = verify(f"Der Wert ist {value} [1].", {1: source}, drop_unsupported=True)
    assert verdict.status == ("answered" if found else "no_evidence")


def test_module_docstring_names_every_unit() -> None:
    doc = " ".join((citations.__doc__ or "").split())
    for unit in UNITS:
        assert f" {unit}," in doc or f" {unit} " in doc, unit


def test_regex_characters_in_sources_and_answers_are_plain_text() -> None:
    source = "Muster (.*)+[ und G-12 mit 5 kg ^$ \\d"
    verdict = verify("Der Greifer G-12 (.*)+ wiegt 5 kg [1].", {1: source}, drop_unsupported=True)
    assert verdict.status == "answered"


# 4. and 12. The refusal and empty answers


@pytest.mark.parametrize(
    "answer",
    [
        NO_EVIDENCE_TEXT,
        "Dazu finde ich nichts in den Unterlagen",
        "  \n Dazu finde ich nichts in den Unterlagen. \n",
        '"Dazu finde ich nichts in den Unterlagen."',
        f"{OPENING_QUOTE}Dazu finde ich nichts in den Unterlagen.{CLOSING_QUOTE}",
        "dazu finde ich nichts in den unterlagen!",
        "",
        "   \n\t ",
    ],
)
def test_refusal_and_empty_answer_give_no_evidence(answer: str) -> None:
    for drop in (True, False):
        verdict = verify(answer, SOURCES, drop_unsupported=drop)
        assert verdict == Verdict(
            status="no_evidence", cited=(), removed_sentences=(), cleaned_text=NO_EVIDENCE_TEXT
        )


@pytest.mark.parametrize(
    "answer",
    [
        "Der Greifer wiegt 5 kg [1].",
        "Der Greifer wiegt 5 kg.",
        "Der Greifer ist leicht [1]. Dazu finde ich nichts in den Unterlagen.",
        "Die Unterlagen widersprechen sich: 24 V [1] und 48 V [2].",
    ],
)
def test_empty_sources_give_no_evidence(answer: str) -> None:
    verdict = verify(answer, {}, drop_unsupported=True)
    assert verdict.status == "no_evidence"
    assert verdict.cited == ()
    assert verdict.cleaned_text == NO_EVIDENCE_TEXT


# 5. and 6. Answers without a supported sentence


def test_answer_without_numbers_gives_no_evidence() -> None:
    verdict = verify("Der Greifer wiegt 5 kg. Er ist blau.", SOURCES, drop_unsupported=False)
    assert verdict.status == "no_evidence"
    assert verdict.cited == ()
    assert verdict.cleaned_text == NO_EVIDENCE_TEXT
    assert reasons(verdict) == [(0, "no_citation"), (1, "no_citation")]


def test_all_sentences_unsupported_lists_every_sentence_with_its_reason() -> None:
    answer = "Der Greifer wiegt 5 kg. Die Adresse ist 10.0.0.7 [9]. Die Adresse ist 10.0.0.9 [2]."
    verdict = verify(answer, SOURCES, drop_unsupported=True)
    assert verdict.status == "no_evidence"
    assert verdict.cited == ()
    assert verdict.cleaned_text == NO_EVIDENCE_TEXT
    assert verdict.removed_sentences == (
        SentenceIssue(index=0, reason="no_citation", values=(), invalid_numbers=(), kept=False),
        SentenceIssue(
            index=1, reason="unknown_citation", values=(), invalid_numbers=(9,), kept=False
        ),
        SentenceIssue(
            index=2,
            reason="unsupported_value",
            values=("10.0.0.9",),
            invalid_numbers=(),
            kept=False,
        ),
    )


# 7. Contradictions


@pytest.mark.parametrize(
    ("answer", "status", "cited"),
    [
        (
            "Die Unterlagen widersprechen sich: Blatt A nennt 24 V [1], Blatt B nennt 48 V [5].",
            "contradiction",
            (1, 5),
        ),
        (
            "Die Unterlagen widersprechen sich.\n- Blatt A: 24 V [1]\n- Blatt B: 48 V [5]",
            "contradiction",
            (1, 5),
        ),
        ("die unterlagen widersprechen sich: 24 V [1][5], 48 V [5].", "contradiction", (1, 5)),
        ("Die Unterlagen widersprechen sich. Die Versorgung betraegt 24 V [1].", "answered", (1,)),
        ("Die Unterlagen widersprechen sich: 24 V [1], 5 kg [1].", "answered", (1,)),
        ("Die Unterlagen widersprechen sich: 24 V [1], 96 V [5].", "no_evidence", ()),
        ("Blatt A nennt 24 V [1], Blatt B nennt 48 V [5].", "answered", (1, 5)),
        (
            "Die Unterlagen widersprechen sich nicht: 24 V [1] und 48 V [5].",
            "answered",
            (1, 5),
        ),
        (
            "Blatt A nennt 24 V [1]. Die Unterlagen widersprechen sich, Blatt B nennt 48 V [5].",
            "answered",
            (1, 5),
        ),
        (
            f"{OPENING_QUOTE}Die Unterlagen widersprechen sich{CLOSING_QUOTE}: 24 V [1], 48 V [5].",
            "contradiction",
            (1, 5),
        ),
        # The first sentence is unsupported and dropped; the phrase opens the next one.
        (
            "Der Greifer wiegt 9 kg [1]. Die Unterlagen widersprechen sich: 24 V [1], 48 V [5].",
            "contradiction",
            (1, 5),
        ),
    ],
)
def test_contradiction_needs_the_phrase_and_two_different_numbers(
    answer: str, status: str, cited: tuple[int, ...]
) -> None:
    verdict = verify(answer, SOURCES, drop_unsupported=True)
    assert verdict.status == status
    assert verdict.cited == cited


def test_contradiction_phrase_alone_is_not_evidence() -> None:
    verdict = verify(f"{CONTRADICTION_PHRASE}.", SOURCES, drop_unsupported=True)
    assert verdict.status == "no_evidence"
    assert verdict.removed_sentences == ()


# 8. Cleaned text


MIXED_ANSWER = (
    "Der Greifer wiegt 5 kg [1]. Er wiegt 7 kg [1]. Die Adresse ist 10.0.0.7 [2].\n"
    "\n"
    "Der Druck ist hoch.\n"
    "\n"
    "- Port 502 [2]\n"
    "- Port 503 [2]\n"
    "- Druck 0,5 bar [3]"
)


def test_drop_unsupported_removes_sentences_and_keeps_paragraphs() -> None:
    verdict = verify(MIXED_ANSWER, SOURCES, drop_unsupported=True)
    assert verdict.status == "answered"
    assert verdict.cited == (1, 2, 3)
    assert verdict.cleaned_text == (
        "Der Greifer wiegt 5 kg [1]. Die Adresse ist 10.0.0.7 [2].\n"
        "\n"
        "- Port 502 [2]\n"
        "- Druck 0,5 bar [3]"
    )


def test_keep_unsupported_leaves_the_text_and_lists_the_same_sentences() -> None:
    dropped = verify(MIXED_ANSWER, SOURCES, drop_unsupported=True)
    kept = verify(MIXED_ANSWER, SOURCES, drop_unsupported=False)
    assert kept.cleaned_text == MIXED_ANSWER
    assert kept.status == dropped.status
    assert kept.cited == dropped.cited
    assert kept.removed_sentences == dropped.removed_sentences
    assert reasons(kept) == [(1, "unsupported_value"), (3, "no_citation"), (5, "unsupported_value")]


def test_supported_sentences_stay_verbatim() -> None:
    answer = (
        "Laut Datenblatt wiegt der Greifer G-12   genau 5 kg [1]!  Die Firmware ist V2.3.1 [2]."
    )
    verdict = verify(answer, SOURCES, drop_unsupported=True)
    assert verdict.cleaned_text == answer


# 10. Sentence splitting


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Das gilt z. B. fuer den Greifer [1]. Siehe S. 34 im Kap. 3 [1].",
            ["Das gilt z. B. fuer den Greifer [1].", "Siehe S. 34 im Kap. 3 [1]."],
        ),
        (
            "Das gilt z.B. auch bzw. ggf. fuer Nr. 4 und Abb. 2 usw. [1]",
            ["Das gilt z.B. auch bzw. ggf. fuer Nr. 4 und Abb. 2 usw. [1]"],
        ),
        (
            "Die Firmware V2.3.1 ist aktuell [2]. Der Wert 1.5 auch.",
            ["Die Firmware V2.3.1 ist aktuell [2].", "Der Wert 1.5 auch."],
        ),
        (
            "Die Adresse ist 10.0.0.7. [2] Der Port ist 502 [2].",
            ["Die Adresse ist 10.0.0.7. [2]", "Der Port ist 502 [2]."],
        ),
        (
            "Der Greifer wiegt 5 kg.[1][2] Weiter geht es.",
            ["Der Greifer wiegt 5 kg.[1][2]", "Weiter geht es."],
        ),
        (
            "Nach Schritt 3. folgt Abschnitt 4. 2 Teile fehlen.",
            ["Nach Schritt 3. folgt Abschnitt 4. 2 Teile fehlen."],
        ),
        ("Das ist so! Wirklich? Ja.", ["Das ist so!", "Wirklich?", "Ja."]),
        (
            "- Erster Punkt [1]\n* Zweiter Punkt [2]\n1. Dritter Punkt\n2) Vierter Punkt",
            ["Erster Punkt [1]", "Zweiter Punkt [2]", "Dritter Punkt", "Vierter Punkt"],
        ),
        ("Erste Zeile\nzweite Zeile\n\n[2]\n  \n...", ["Erste Zeile", "zweite Zeile"]),
        ('Er sagte "Ja." Dann ging er.', ['Er sagte "Ja."', "Dann ging er."]),
        (
            "Die Zykluszeit betraegt 10 s. Der Greifer schliesst danach [1].",
            ["Die Zykluszeit betraegt 10 s.", "Der Greifer schliesst danach [1]."],
        ),
    ],
)
def test_sentence_splitting(text: str, expected: list[str]) -> None:
    assert sentences_of(text) == expected


def test_number_after_the_full_stop_supports_the_sentence_before() -> None:
    verdict = verify(
        "Die Steuerung hat die Adresse 10.0.0.7. [2] Mehr steht dort nicht [2].",
        SOURCES,
        drop_unsupported=True,
    )
    assert verdict.status == "answered"
    assert verdict.removed_sentences == ()


def test_ip_at_the_end_of_a_sentence_is_found() -> None:
    verdict = verify(
        "Die Adresse lautet 10.0.0.7 [2]. Mehr steht dort nicht [2].",
        SOURCES,
        drop_unsupported=True,
    )
    assert verdict.removed_sentences == ()


# 11. Partial answers


def test_partial_answer_keeps_the_refusal() -> None:
    answer = "Der Greifer wiegt 5 kg [1]. Dazu finde ich nichts in den Unterlagen."
    for drop in (True, False):
        verdict = verify(answer, SOURCES, drop_unsupported=drop)
        assert verdict.status == "answered"
        assert verdict.cited == (1,)
        assert verdict.removed_sentences == ()
        assert verdict.cleaned_text == answer


# 9. Run time


def _timed_mean(answer: str, sources: dict[int, str], runs: int = 20) -> float:
    total = 0.0
    for _ in range(runs):
        start = time.perf_counter()
        verify(answer, sources, drop_unsupported=True)
        total += time.perf_counter() - start
    return total / runs


def test_verify_is_fast_for_a_typical_answer() -> None:
    section = (
        "Der Greifer G-12 wiegt 5 kg und arbeitet mit 24 V DC bei 0,5 bar. "
        "Die Steuerung hat die Adresse 10.0.0.7, Port 502, Firmware V2.3.1. "
    )
    sources = dict.fromkeys(range(1, 9), (section * 20)[:2000])
    assert all(len(text) == 2000 for text in sources.values())
    sentence = (
        "Der Greifer G-12 wiegt 5 kg bei 24 V und 0,5 bar, Adresse 10.0.0.7, Port 502 [{n}]. "
    )
    answer = "".join(sentence.format(n=n % 8 + 1) for n in range(18))
    assert 1400 <= len(answer) <= 1600
    assert verify(answer, sources, drop_unsupported=True).status == "answered"
    assert _timed_mean(answer, sources) < 0.050


def _best_time(answer: str, sources: dict[int, str], runs: int = 3) -> float:
    best = float("inf")
    for _ in range(runs):
        start = time.perf_counter()
        verify(answer, sources, drop_unsupported=True)
        best = min(best, time.perf_counter() - start)
    return best


@pytest.mark.parametrize(
    ("pattern", "tail"),
    [
        ("wort ", ""),
        ("1. ", ""),
        ("[1 ", ""),
        ("[1][", ""),
        ("z. ", ""),
        ("5", ""),
        ("a.", ""),
        (".", "x"),
        ("!?", "x"),
        ("1.1.", ""),
        ("S7 1 ", ""),
        ("-", "5 kg [1]"),
        ("10.0.0.7 ", "[1]"),
        ("G-12 5 kg [1]. ", ""),
    ],
)
def test_verify_grows_linearly_for_unfavourable_input(pattern: str, tail: str) -> None:
    sources = dict.fromkeys(range(1, 9), "Der Greifer G-12 wiegt 5 kg. " * 70)

    def answer(length: int) -> str:
        return (pattern * (length // len(pattern) + 1))[:length] + tail

    small = _best_time(answer(5000), sources)
    large = _best_time(answer(20000), sources)
    assert large < 1.0
    # Four times the input may take at most eight times as long (linear with
    # room for noise); below one millisecond the clock is too coarse to compare.
    assert large / max(small, 0.001) < 8
