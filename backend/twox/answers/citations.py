"""Deterministic citation check of a generated answer (guard rail 3).

The answer service calls :func:`verify` once the chat model has finished. The
check needs no database, no network and no model: it compares the answer with
the section texts the model was shown, numbered ``1..k`` as in the context
selection. An answer without a valid source becomes the fixed refusal
:data:`NO_EVIDENCE_TEXT`. Section texts are data: they are only normalised and
searched as plain strings, never evaluated, and no value from an answer or a
source is ever built into a regular expression. Nothing is logged.

Sentences
    The answer is split into sentences without changing its wording. A
    sentence ends at ``.``, ``!`` or ``?`` followed by white space or the end
    of the text (closing quotes or brackets may come in between), and at every
    line break. A list item (``-``, ``*``, ``•``, ``1.`` or ``1)`` at the start
    of a line) is a sentence of its own; the marker is not part of it. There
    is no sentence end after the abbreviations in :data:`ABBREVIATIONS`
    (``z. B.``, ``S. 34``, ``Nr.`` ...; ``S.``, ``Nr.``, ``No.``, ``Abb.``,
    ``Tab.``, ``Kap.`` and ``Fig.`` only as written, so ``10 s.`` ends a
    sentence, the others in any case; lower-case ``s.`` (siehe) only after
    white space or ``(`` that does not follow a digit, so ``10 s.``,
    ``10s.`` and ``250 mm/s.`` end a sentence), inside numbers, IP addresses
    and versions (``1.5``, ``192.168.0.5``, ``V2.3.1``: the full stop is not
    followed by white space), nor after an ordinal number (``3.``) followed by
    a digit or a lower-case letter. Source numbers right after the
    punctuation (``... 24 V. [2]``) belong to the sentence before. If a
    further full stop follows them (``... 24 V. [1]. Weiter``), the sentence
    ends at that full stop and the numbers still belong to it. Sentences
    with neither letters nor digits besides source numbers are skipped.

    A list block is a run of list lines (indented, nested items included);
    empty lines between them do not end it, a line with other content does.
    Its introduction sentence is the last sentence of the last line with
    content before the block that is not a list line, if that sentence ends
    with ``:``; source numbers may stand before or after the colon
    (``Die Station nutzt diese Ports [1]:`` and ``... Ports: [1]``). A list
    at the start of the answer, or after a line that does not end with
    ``:``, has no introduction sentence.

Source numbers
    ``[n]``, ``[n, m]``, ``[n; m]`` and ``[n][m]`` with a positive integer
    ``n`` of at most six digits. Other forms (``[1-3]``, ``[Quelle 2]``,
    superscripts) are no citation. A number is valid only if it is a key of
    ``sources``.

Check values
    The values of a sentence that must appear in a cited source:
    numbers with a unit from :data:`UNITS` (``5 kg``, ``5kg``, ``0,5 bar``,
    ``24 V`` in ``24 V DC``, ``20 °C``, ``80 %``); IPv4 and IPv6 addresses
    with an optional prefix length and MAC addresses; ports (``Port 502``,
    ``:502`` after an IPv4 address); versions (``V18``, ``v2.3.1``,
    ``Version 4.1``, ``Firmware 5.12``), compared without the ``v`` so that
    ``Version 18`` and ``V18`` match; type designations and other tokens of
    letters and digits (``S7-1200``, ``1512SP``, ``UR5e``, ``1.5``). Ports
    are recognised after ``Port``, ``Ports``, ``Port:``, ``Port-Nr.``,
    ``Port Nr.`` and ``Portnummer``. Addresses
    and type designations come from :func:`twox.search.identifiers.find_identifiers`,
    called for each white-space token on its own, so that no value is skipped:
    there is no limit of ten, and a leading ``-`` (``-K7``) is removed before
    the token is classified. Markdown emphasis (asterisks, backticks, and
    underscores at the edge of a word) counts as white space, so ``**10.0.0.9**`` is
    checked. A token that is exactly a type designation
    (nothing cut off, no punctuation after it) directly followed by a token
    of digits only is one value (``S7 1500`` gives ``s71500``), unless the
    digits start a number with a unit; ``S7-1200, 2 Module``, ``Seite 34``
    and ``Port 502`` are not joined. Before a token is classified, ``-``
    parts at its end or start that are words (at least four letters in any
    script, at least one of them lower case) are cut off:
    ``S7-1200-Steuerung`` and ``S7-1200-Gerät`` check ``S7-1200``,
    ``Schütz-K3`` checks ``K3``; upper-case parts stay (``1756-ENBT``). If
    only digits remain, they are joined with a type designation directly
    before them (``S7 1500-Gerät`` checks ``S7 1500``) and otherwise are a
    plain number, which is not checked (``6-Achs-Roboter``,
    ``24-Volt-Versorgung``). A trailing hyphen (``G-12-`` in ``G-12- und
    G-14-Ausführung``) is dropped;
    a number and unit may be joined by ``-`` (``24-V-Versorgung`` checks
    ``24 V``). A minus sign belongs to the number (``-20 °C``).
    Source numbers are no check values. The units are: V, mV, kV, A, mA,
    kA, µA, W, kW, MW, VA, kVA, Hz, kHz, MHz, GHz, Ω, kΩ, MΩ, Ohm, bar,
    mbar, Pa, hPa, kPa, MPa, psi, N, kN, Nm, µm, mm, cm, dm, m, km, mg, g,
    kg, ns, µs, ms, s, min, h, °C, °F, K, %, rpm, U/min, 1/min, l, ml,
    l/min, m/s, mm/s, m/s², m³/h, dB, dBm, Bd, kBd, bit/s, kbit/s, Mbit/s,
    Gbit/s, kB, MB, GB, Byte (``in`` and ``t`` are left out, they are
    ordinary words too often).

Normalisation
    Sentence values and source texts are normalised alike: Unicode NFKC,
    ``casefold``, every dash variant to ``-`` and non-breaking spaces to
    spaces, a decimal comma between two digits to a full stop, a minus sign
    (``-`` before a digit, not joining it to a word or number) to U+2212,
    then white space and ``-`` removed (:func:`normalise_value`). A minus sign
    before an occurrence lengthens it: ``20 °C`` and ``-20 °C`` differ.
    ``5 kg``/``5kg``, ``S7-1200``/``S7 1200`` and ``0,5 bar``/``0.5 bar``
    are therefore equal. A value is found if it occurs
    in the normalised text of at least one source that the same sentence
    cites validly, and the occurrence is not lengthened: no letter or digit
    directly before or after it, nor a ``.`` (and for IPv6 and MAC addresses
    a ``:``) joining it to one, unless white space or ``-`` stood in between
    in the original. ``192.168.0.5`` does not match ``192.168.0.50`` and
    ``5 kg`` does not match ``25 kg``. A version may be preceded by ``v``, a
    number with a unit followed by ``AC`` or ``DC`` (``24 V`` in ``24VDC``).
    Each source text is normalised once per call.

Values from the question
    With ``question`` the check values of the question are determined once
    per call, by the same rules as for a sentence. Only type designations
    and other identifiers of letters and digits (``G-12``, ``S7 1500``,
    ``UR5e``, also ``E1234``, ``PLC-01``, ``IP67``) can be taken from it: a
    value of the sentence that is such a designation, with the key of one in
    the question, is not missing, but only if the sentence carries at least
    one further check value that is not such a designation and is found in
    one of its valid sources (``Der G-12 hat eine Nutzlast von 5 kg [1].``
    with ``5 kg`` in source 1). A sentence whose only value comes from the
    question is checked as without a question, so a false premise (``Was
    bedeutet Fehler E1234?`` with a source on ``E1235``) does not confirm
    itself. Numbers with a unit (also written as one token: ``10kg``,
    ``24VDC``), addresses, ports, versions and numbers without a letter
    (``1.5``) are never taken from the question: they are what a false
    premise would get wrong. The sentence still needs a valid source number.
    Only keys are compared; no expression is built from the question.

Sentence verdict
    A sentence is ``unknown_citation`` if it carries source numbers but no
    valid one, ``no_citation`` if it carries none, ``unsupported_value`` if a
    check value is found in none of its valid sources, and supported
    otherwise. Invalid numbers in a supported sentence (``[2][9]`` with five
    sources) are removed from it; the sentence stays and is listed in
    ``removed_sentences`` with reason ``unknown_citation`` and the numbers in
    ``invalid_numbers`` and ``kept=True``; unsupported sentences have
    ``kept=False``. ``len(removed_sentences)`` counts both (flagged or
    dropped, the count for the event ``done``), ``Verdict.dropped_count`` only
    the unsupported ones. The refusal sentence never needs a number; a
    sentence that consists only of :data:`CONTRADICTION_PHRASE` needs none
    either. Both are neither supported nor listed.

    A sentence in a list block without source numbers of its own inherits
    the valid numbers of the introduction sentence, if that sentence carries
    a valid number and is supported; its values are checked against those
    sources, and the inherited numbers count for ``cited`` like its own.
    Otherwise it stays ``no_citation``: a dropped introduction sentence
    passes nothing on. A list item with numbers of its own is checked
    against those only; with invalid numbers only it is
    ``unknown_citation``.

Cleaned text
    With ``drop_unsupported=True`` unsupported sentences are removed from
    ``cleaned_text`` together with the white space after them; a list item
    or line left empty is removed, paragraphs stay. With ``False`` they stay
    and are only listed. ``removed_sentences`` is the same in both cases.
    Supported sentences keep their wording except for removed invalid
    numbers; nothing is rephrased.

Overall verdict
    ``no_evidence`` if the answer is empty, is only the refusal (compared
    without punctuation and quotes) or has no supported sentence: ``cited`` is
    empty and ``cleaned_text`` is :data:`NO_EVIDENCE_TEXT`. ``contradiction``
    if the first sentence that is not unsupported starts with
    :data:`CONTRADICTION_PHRASE` (compared normalised, after leading
    punctuation) and no further word follows it before punctuation or the
    end (not ``... widersprechen sich nicht``), and the supported sentences
    cite at least two different valid numbers. ``answered``
    otherwise; a refusal sentence next to supported sentences (a partial
    answer) stays in the text.

Limits
    The check is a guard against invented values, not a proof of meaning.
    Callers (the answer service and the measurement) must not rely on it for:

    * words: variant or product names without digits (``Basic``,
      ``Comfort``, ``Edelstahl``), negations and statements are not checked;
    * plain numbers without a unit (``3 Finger``, ``Seite 34``), unless
      they belong to a type designation, version, port or address;
    * ports written without the word ``Port`` (``TCP 502``) or after an
      address other than IPv4;
    * units outside :data:`UNITS`, and the relation between a value and what
      it describes (a correct ``24 V`` in the wrong context passes);
    * different spellings of one address (``fe80::1`` and ``fe80:0::1``);
    * which source states a value when several are cited: one is enough;
    * a type designation from the question counts unchecked if the sentence
      carries a further supported value; whether the source is about that
      device is not checked. This holds for error codes and identifiers
      too: ``E1234 tritt ab 80 °C auf [1]`` passes if the source names
      ``80 °C`` only for ``E1235``;
    * a list item is only as well supported as the sources of its
      introduction sentence.
"""

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal

# The fixed refusal (guard rail 3) and the phrase that marks contradicting
# sources (question 6 of the test factory) are defined once, in types.py (122).
from twox.answers.types import CONTRADICTION_PHRASE as CONTRADICTION_PHRASE
from twox.answers.types import NO_EVIDENCE_TEXT as NO_EVIDENCE_TEXT
from twox.search.identifiers import IdentifierKind, find_identifiers

VerdictStatus = Literal["answered", "no_evidence", "contradiction"]
IssueReason = Literal["no_citation", "unknown_citation", "unsupported_value"]

#: Units after a number that make it a check value. Longer units come first in
#: the expression, so ``mm`` wins over ``m``. ``in`` and ``t`` are left out:
#: they are ordinary words too often.
UNITS: Final[tuple[str, ...]] = (
    "V", "mV", "kV", "A", "mA", "kA", "µA", "W", "kW", "MW", "VA", "kVA",
    "Hz", "kHz", "MHz", "GHz", "Ω", "kΩ", "MΩ", "Ohm",
    "bar", "mbar", "Pa", "hPa", "kPa", "MPa", "psi", "N", "kN", "Nm",
    "µm", "mm", "cm", "dm", "m", "km", "mg", "g", "kg",
    "ns", "µs", "ms", "s", "min", "h", "°C", "°F", "K", "%",
    "rpm", "U/min", "1/min", "l", "ml", "l/min", "m/s", "mm/s", "m/s²", "m³/h",
    "dB", "dBm", "Bd", "kBd", "bit/s", "kbit/s", "Mbit/s", "Gbit/s",
    "kB", "MB", "GB", "Byte",
)  # fmt: skip

#: No sentence ends at the final full stop of these (white space inside optional).
ABBREVIATIONS: Final[tuple[str, ...]] = (
    "z. B.", "d. h.", "u. a.", "o. ä.", "bzw.", "ca.", "ggf.", "vgl.", "usw.",
    "inkl.", "evtl.", "max.", "Nr.", "S.", "Abb.", "Tab.", "Kap.", "Fig.",
    "e. g.", "i. e.", "etc.", "approx.", "No.",
)  # fmt: skip

#: Hyphen, dash and minus variants (U+2010 to U+2015, U+2212) become ``-``;
#: non-breaking and figure spaces (U+00A0, U+2007, U+202F) become spaces.
_DASHES: Final = str.maketrans(
    {chr(code): "-" for code in (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212)}
    | {chr(code): " " for code in (0x00A0, 0x2007, 0x202F)}
)
#: Straight and typographic quotes (U+201A to U+201E, U+2018/U+2019, U+00AB/U+00BB).
_QUOTE_CHARS: Final = "\"'" + "".join(
    map(chr, (0x201A, 0x201C, 0x201D, 0x201E, 0x2018, 0x2019, 0x00AB, 0x00BB))
)
_QUOTES: Final = str.maketrans(dict.fromkeys(_QUOTE_CHARS, " "))
#: List markers at the start of a line: hyphen, asterisk, bullet (U+2022), ``1.``, ``1)``.
_BULLET: Final = chr(0x2022)

#: Possessive quantifiers throughout: white space is never given back, so long
#: runs of spaces cost linear time.
_CIT: Final = r"\[[ \t]*+\d{1,6}(?:[ \t]*+[,;][ \t]*+\d{1,6})*+[ \t]*+\]"
_CITATION: Final = re.compile(_CIT)
#: Starts only where a run of spaces starts (or at a bracket), so a long run
#: that is not followed by ``[`` is tried once.
_CITATION_RUN: Final = re.compile(rf"(?<![ \t])[ \t]*+{_CIT}(?:[ \t]*+{_CIT})*+")
_NUMBER: Final = re.compile(r"\d+")
#: A run of sentence punctuation is only tried where it starts, and possessive
#: quantifiers keep the scan linear (``"." * 20000 + "x"``).
_SENTENCE_END: Final = re.compile(
    rf"(?<![.!?])[.!?]++[{re.escape(_QUOTE_CHARS)})]*+(?:[ \t]*+{_CIT})*+(?=\s|$)"
)
_LIST_MARKER: Final = re.compile(rf"[ \t]*(?:[-*{_BULLET}]|\d{{1,3}}[.)])[ \t]+")
#: These abbreviations count only as written (``s.`` after a unit ends a sentence).
_CASE_SENSITIVE_ABBREVIATIONS: Final = frozenset(
    {"S.", "Nr.", "No.", "Abb.", "Tab.", "Kap.", "Fig."}
)


def _abbreviation_pattern(abbreviation: str) -> str:
    pattern = re.escape(abbreviation).replace(r"\ ", r"\s?")
    return pattern if abbreviation in _CASE_SENSITIVE_ABBREVIATIONS else f"(?i:{pattern})"


_ABBREVIATION: Final = re.compile(
    r"(?<!\w)(?:"
    + "|".join(_abbreviation_pattern(a) for a in ABBREVIATIONS)
    # Lower-case "s." (siehe) only after white space or "(" that does not
    # follow a digit: "10 s.", "10s." and "mm/s." are units.
    + r"|(?<![^\s(])(?<!\d\s)s\."
    + r")"
)
#: A minus sign: ``-`` before a digit that does not join it to a word or number.
_MINUS: Final = re.compile(r"(?<![\w.,])-(?=\d)")
#: Stands for a minus sign in normalised text, so that removing ``-`` keeps it.
_MINUS_MARK: Final = chr(0x2212)
_TOKEN: Final = re.compile(r"\S+")
#: Markdown emphasis counts as white space: asterisks and backticks always,
#: underscores at the edge of a word (``x86_64`` keeps its underscore). Each
#: run of underscores is tried once, where it starts.
_MARKDOWN: Final = str.maketrans({"*": " ", "`": " "})
_EDGE_UNDERSCORE: Final = re.compile(r"(?<!\w)_++|(?<!_)_++(?!\w)")
#: Leading characters removed from a token before it is classified.
_TOKEN_LEAD: Final = "\"'([{<"
_NEXT_CHAR: Final = re.compile(r"[ \t]*(\S)")
_DECIMAL_COMMA: Final = re.compile(r"(?<=\d),(?=\d)")
_NOT_ALNUM: Final = re.compile(r"[\W_]+")

_UNIT_ALTERNATION: Final = "|".join(
    re.escape(unit)
    for unit in sorted({unicodedata.normalize("NFKC", u) for u in UNITS}, key=len, reverse=True)
)
_UNIT_VALUE: Final = re.compile(
    r"(?<![\w.,])-?\d{1,9}(?:[.,]\d{1,9})?[ \t-]?(?:" + _UNIT_ALTERNATION + r")(?![\w%°])"
)
#: A whole token that is a number with a unit, optionally followed by ``AC`` or
#: ``DC`` (``24VDC``, ``230VAC``): never a type designation from the question.
_UNIT_TOKEN: Final = re.compile(
    r"-?\d{1,9}(?:[.,]\d{1,9})?[ \t-]?(?:" + _UNIT_ALTERNATION + r")(?:[-/]?(?i:ac|dc))?"
)
_PORT_WORD: Final = re.compile(
    # "Port 502", "Ports 502", "Port: 502", "Port-Nr. 502", "Portnummer 502".
    # Each repetition of the separator group consumes at least one character
    # and is possessive, so the scan stays linear.
    r"(?<!\w)port(?:s|nummer|nr\.?)?(?:[ \t:-]|nr\.?|no\.?)*+(\d{1,5})(?!\d)",
    re.IGNORECASE,
)
_IPV4_PORT: Final = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})(?!\d)")
_VERSION_WORD: Final = re.compile(
    r"(?<!\w)(?:version|firmware|fw|release|rev\.?)[ \t]*+v?(\d++(?:\.\d++)*+)(?![\w])",
    re.IGNORECASE,
)
_VERSION_TOKEN: Final = re.compile(r"(?<![\w.])v(\d++(?:\.\d++)*+)(?![\w])", re.IGNORECASE)
_VERSION_IDENTIFIER: Final = re.compile(r"v\d+(?:\.\d+)*", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class SentenceIssue:
    """A sentence that is not supported, or a supported one with invalid numbers."""

    index: int  # 0-based position of the sentence in the answer
    reason: IssueReason
    values: tuple[str, ...]  # check values not found (only for unsupported_value)
    invalid_numbers: tuple[int, ...]  # cited numbers outside the source set
    kept: bool  # supported sentence that stays (only invalid numbers removed)


@dataclass(frozen=True, slots=True)
class Verdict:
    """The result of :func:`verify`.

    ``removed_sentences`` lists every flagged sentence: unsupported ones
    (``kept`` false) and supported ones whose invalid numbers were removed
    (``kept`` true). ``len(removed_sentences)`` is the count for the event
    ``done``; :attr:`dropped_count` counts the unsupported ones only.
    """

    status: VerdictStatus
    cited: tuple[int, ...]  # valid source numbers used in kept sentences, ascending, unique
    removed_sentences: tuple[SentenceIssue, ...]  # dropped or flagged sentences
    cleaned_text: str  # final text for done.final_text

    @property
    def dropped_count(self) -> int:
        """Number of unsupported sentences (removed with ``drop_unsupported=True``)."""
        return sum(1 for issue in self.removed_sentences if not issue.kept)


@dataclass(frozen=True, slots=True)
class _Sentence:
    """A sentence as a span of the answer: line number and columns in that line."""

    line: int
    start: int
    end: int
    bare: str  # letters and digits of the normalised sentence without source numbers
    in_list: bool = False  # the sentence stands in a line with a list marker


@dataclass(frozen=True, slots=True)
class _Value:
    """A check value: as written, and its normalised key.

    ``designation`` marks a type designation or other identifier of letters
    and digits (``G-12``, ``S7 1500``, ``E1234``); only such a value may be
    taken from the question (see the module docstring).
    """

    display: str
    key: str
    colon_joins: bool = False
    version: bool = False
    unit: bool = False
    designation: bool = False


@dataclass(frozen=True, slots=True)
class _Compact:
    """Normalised text without white space and ``-``.

    ``gap[i]`` tells whether white space or ``-`` stood before ``text[i]``;
    ``gap[len(text)]`` is always true.
    """

    text: str
    gap: tuple[bool, ...]


def _normalise(text: str) -> str:
    """NFKC, casefold, dashes to ``-``, odd spaces to spaces, decimal comma to point."""
    folded = unicodedata.normalize("NFKC", text).casefold().translate(_DASHES)
    return _MINUS.sub(_MINUS_MARK, _DECIMAL_COMMA.sub(".", folded))


def normalise_value(text: str) -> str:
    """``text`` normalised as check values are compared (see the module docstring).

    NFKC, casefold, dashes unified, decimal comma to point, a minus sign kept
    as U+2212, then white space and ``-`` removed: ``"S7 1200"`` and
    ``"S7-1200"`` both give ``"s71200"``, ``"0,5 bar"`` gives ``"0.5bar"``.
    """
    return _compact(text).text


def _compact(text: str) -> _Compact:
    """The normalised ``text`` without white space and ``-``, with the gaps remembered."""
    chars: list[str] = []
    gap: list[bool] = []
    pending = False
    for char in _normalise(text):
        if char.isspace() or char == "-":
            pending = True
            continue
        chars.append(char)
        gap.append(pending)
        pending = False
    gap.append(True)
    return _Compact(text="".join(chars), gap=tuple(gap))


def _bare(text: str) -> str:
    """Only the letters and digits of the normalised ``text``."""
    return _NOT_ALNUM.sub("", _normalise(text))


def _is_word(char: str) -> bool:
    return char.isalnum() or char == "_"


def _bounded(source: _Compact, start: int, end: int, value: _Value) -> bool:
    """Whether the occurrence ``source.text[start:end]`` is not lengthened."""
    text, gap = source.text, source.gap
    joiners = ".:" if value.colon_joins else "."
    if start > 0 and not gap[start]:
        before = text[start - 1]
        if before == _MINUS_MARK:
            return False
        if _is_word(before):
            prefix_ok = (
                value.version
                and before == "v"
                and (start == 1 or gap[start - 1] or not _is_word(text[start - 2]))
            )
            if not prefix_ok:
                return False
        elif before in joiners and start >= 2 and not gap[start - 1] and _is_word(text[start - 2]):
            return False
    if end < len(text) and not gap[end]:
        after = text[end]
        if _is_word(after):
            suffix_ok = (
                value.unit
                and text.startswith(("ac", "dc"), end)
                and (end + 2 == len(text) or gap[end + 2] or not _is_word(text[end + 2]))
            )
            if not suffix_ok:
                return False
        elif (
            after in joiners
            and end + 1 < len(text)
            and not gap[end + 1]
            and _is_word(text[end + 1])
        ):
            return False
    return True


def _occurs(value: _Value, source: _Compact) -> bool:
    """Whether ``value`` occurs in ``source`` with boundaries."""
    position = source.text.find(value.key)
    while position != -1:
        if _bounded(source, position, position + len(value.key), value):
            return True
        position = source.text.find(value.key, position + 1)
    return False


def value_occurs(value: str, text: str) -> bool:
    """Whether ``value`` occurs in ``text`` as a whole value, as the check compares values.

    Both are normalised with :func:`normalise_value`; the occurrence must not
    be lengthened (same boundary rules as for check values, see the module
    docstring): ``"5 kg"`` occurs in ``"5kg"`` but not in ``"25 kg"`` or
    ``"12,5 kg"``, ``"V18"`` in ``"V 18"`` but not in ``"V180"``. For the
    measurement of the answers (127); :func:`verify` does not use it.
    """
    key = normalise_value(value)
    if not key:
        return False
    return _occurs(_Value(display=value, key=key), _compact(text))


def _split_sentences(lines: list[str]) -> list[_Sentence]:
    """The sentences of the answer, line by line, in order."""
    sentences: list[_Sentence] = []
    for number, line in enumerate(lines):
        marker = _LIST_MARKER.match(line)
        segment_start = marker.end() if marker else 0
        no_split = {
            position
            for match in _ABBREVIATION.finditer(line, segment_start)
            for position in range(match.start(), match.end())
            if line[position] == "."
        }
        for match in _SENTENCE_END.finditer(line, segment_start):
            punctuation = match.start()
            if match.group().startswith(".") and not match.group().startswith(".."):
                if punctuation in no_split:
                    continue
                following = _NEXT_CHAR.match(line, match.end())
                if (
                    following is not None
                    and (following.group(1).isdigit() or following.group(1).islower())
                    and _ends_with_ordinal(line, punctuation)
                ):
                    continue
            _add_sentence(sentences, number, line, segment_start, match.end(), marker is not None)
            segment_start = match.end()
        _add_sentence(sentences, number, line, segment_start, len(line), marker is not None)
    return sentences


def _list_intros(lines: list[str], sentences: list[_Sentence]) -> list[int | None]:
    """For each sentence in a list block, the index of its introduction sentence.

    One pass over the lines. The candidate is the last sentence of the last
    line with content that is not a list line, if that sentence ends with
    ``:`` (source numbers before or after it allowed). Empty lines keep the
    candidate; a list line takes it; any other line with content replaces it.
    Whether the candidate carries a valid number and is supported is decided
    by :func:`verify`.
    """
    intros: list[int | None] = [None] * len(sentences)
    candidate: int | None = None
    index = 0
    for number, line in enumerate(lines):
        first = index
        while index < len(sentences) and sentences[index].line == number:
            index += 1
        if not line.strip():
            continue
        if _LIST_MARKER.match(line):
            for position in range(first, index):
                intros[position] = candidate
            continue
        candidate = None
        if index > first:
            last = sentences[index - 1]
            text = line[last.start : last.end]
            if (_CITATION.sub(" ", text) if "[" in text else text).rstrip().endswith(":"):
                candidate = index - 1
    return intros


def _ends_with_ordinal(line: str, end: int) -> bool:
    """Whether ``line[:end]`` ends with a number of one to four digits standing alone."""
    start = end
    while start > 0 and end - start < 5 and line[start - 1].isdigit():
        start -= 1
    return 0 < end - start <= 4 and (start == 0 or line[start - 1].isspace())


def _add_sentence(
    sentences: list[_Sentence],
    line_number: int,
    line: str,
    start: int,
    end: int,
    in_list: bool = False,
) -> None:
    """Append the span ``line[start:end]`` without outer white space, unless it is empty."""
    while start < end and line[start].isspace():
        start += 1
    while end > start and line[end - 1].isspace():
        end -= 1
    text = line[start:end]
    bare = _bare(_CITATION.sub(" ", text) if "[" in text else text)
    if bare:
        sentences.append(
            _Sentence(line=line_number, start=start, end=end, bare=bare, in_list=in_list)
        )


def _extract_citations(sentence: str) -> list[int]:
    """The source numbers of ``sentence``, in order, as written."""
    return [
        int(number)
        for match in _CITATION.finditer(sentence)
        for number in _NUMBER.findall(match.group())
    ]


def _check_values(sentence: str) -> list[_Value]:
    """The check values of ``sentence`` (source numbers already removed), without duplicates."""
    text = unicodedata.normalize("NFKC", sentence).translate(_DASHES).translate(_QUOTES)
    text = _EDGE_UNDERSCORE.sub(lambda run: " " * len(run.group()), text.translate(_MARKDOWN))
    found: dict[str, _Value] = {}

    def add(display: str, **flags: bool) -> None:
        key = _compact(display).text
        if key and key not in found:
            found[key] = _Value(display=display, key=key, **flags)

    unit_starts: set[int] = set()
    for match in _UNIT_VALUE.finditer(text):
        add(match.group(), unit=True)
        unit_starts.add(match.start())
    for match in _PORT_WORD.finditer(text):
        add(match.group(1))
    for match in _IPV4_PORT.finditer(text):
        add(match.group(2))
    for match in _VERSION_WORD.finditer(text):
        add(match.group(1), version=True)
    for match in _VERSION_TOKEN.finditer(text):
        add(match.group(1), version=True)
    tokens = list(_TOKEN.finditer(_IPV4_PORT.sub(r"\1 \2", text)))
    skip_next = False
    for position, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        # One token at a time: find_identifiers stops after ten identifiers and
        # skips tokens with a leading "-" (an exclusion in the search syntax).
        core = token.group().lstrip(_TOKEN_LEAD).lstrip("-")
        trimmed = _trim_compound(core)
        identifiers = find_identifiers(trimmed)
        if not identifiers:
            continue
        identifier = identifiers[0]
        if identifier.kind is not IdentifierKind.GENERIC:
            add(
                identifier.value,
                colon_joins=identifier.kind in {IdentifierKind.IPV6, IdentifierKind.MAC},
            )
            continue
        if _VERSION_IDENTIFIER.fullmatch(identifier.value):
            continue
        value = identifier.value
        following = tokens[position + 1] if position + 1 < len(tokens) else None
        if (
            following is not None
            # Joined only if the token is exactly the designation: nothing cut
            # off, no punctuation after it ("S7-1200, 2 Module" stays apart).
            and core == value
            and any(char.isalpha() for char in value)
            and following.start() not in unit_starts
        ):
            # The next token counts if it is digits, also once word parts are
            # cut off ("S7 1500-Gerät" checks "S7 1500").
            digits = _trim_compound(following.group().lstrip(_TOKEN_LEAD).lstrip("-")).rstrip(
                ".,;:!?)]"
            )
        else:
            digits = ""
        if digits.isdigit():
            add(f"{value} {digits}", designation=_is_designation(value))
            skip_next = True
            continue
        add(value, designation=_is_designation(value))
    return list(found.values())


def _is_designation(value: str) -> bool:
    """Whether the generic identifier ``value`` is a type designation or code.

    It needs a letter and a digit and must not be a number with a unit
    written as one token (``10kg``, ``24VDC``). Plain numbers with a full
    stop (``1.5``) have no letter and are no designation.
    """
    return (
        any(char.isalpha() for char in value)
        and any(char.isdigit() for char in value)
        and _UNIT_TOKEN.fullmatch(value) is None
    )


def _is_word_part(part: str) -> bool:
    """Whether ``part`` is a word joined by ``-``: four letters or more, some lower case."""
    return len(part) >= 4 and part.isalpha() and any(char.islower() for char in part)


def _trim_compound(token: str) -> str:
    """``token`` without ``-`` parts at its ends that are words.

    ``S7-1200-Gerät`` gives ``S7-1200``, ``Schütz-K3`` gives ``K3``;
    upper-case parts (``1756-ENBT``) and short parts (``G-12-A``) stay. Only
    digits may remain (``1500-Gerät`` gives ``1500``); the caller joins them
    with a type designation before them or ignores them. Punctuation at the
    end is kept, a trailing hyphen (``G-12-``) dropped.
    """
    end = len(token)
    while end > 0 and not token[end - 1].isalnum():
        end -= 1
    tail = token[end:].replace("-", "")
    start = 0
    while True:
        cut = token.rfind("-", start, end)
        if cut <= start or not _is_word_part(token[cut + 1 : end]):
            break
        end = cut
    while True:
        cut = token.find("-", start, end)
        if cut <= start or not _is_word_part(token[start:cut]):
            break
        start = cut + 1
    return token[start:end] + tail


def _strip_invalid(sentence: str, valid: Mapping[int, str]) -> str:
    """``sentence`` without the source numbers that are not keys of ``valid``."""

    def rebuild_run(run: re.Match[str]) -> str:
        leading = run.group()[: len(run.group()) - len(run.group().lstrip(" \t"))]
        parts: list[str] = []
        position = run.start()
        for bracket in _CITATION.finditer(run.string, run.start(), run.end()):
            space = run.string[position : bracket.start()]
            position = bracket.end()
            numbers = [int(n) for n in _NUMBER.findall(bracket.group())]
            kept = [n for n in numbers if n in valid]
            if not kept:
                continue
            text = bracket.group() if kept == numbers else "[" + ", ".join(map(str, kept)) + "]"
            parts.append((space if parts else leading) + text)
        return "".join(parts)

    return _CITATION_RUN.sub(rebuild_run, sentence)


def _cleaned(
    lines: list[str],
    sentences: list[_Sentence],
    dropped: set[int],
    replaced: dict[int, str],
) -> str:
    """The answer without the dropped sentences and with the replaced ones."""
    by_line: dict[int, list[int]] = {}
    for index in dropped | replaced.keys():
        by_line.setdefault(sentences[index].line, []).append(index)
    output: list[str] = []
    for number, line in enumerate(lines):
        indices = sorted(by_line.get(number, []), key=lambda i: sentences[i].start)
        if not indices:
            output.append(line)
            continue
        pieces: list[str] = []
        position = 0
        for index in indices:
            sentence = sentences[index]
            pieces.append(line[position : sentence.start])
            position = sentence.end
            if index in dropped:
                while position < len(line) and line[position] in " \t":
                    position += 1
            else:
                pieces.append(replaced[index])
        pieces.append(line[position:])
        rebuilt = "".join(pieces)
        if rebuilt.strip() and _LIST_MARKER.fullmatch(rebuilt + " ") is None:
            output.append(rebuilt.rstrip())
    text = "\n".join(output)
    return re.sub(r"\n[ \t\r]*\n(?:[ \t\r]*\n)+", "\n\n", text).strip()


def _contradiction_pattern() -> re.Pattern[str]:
    """:data:`CONTRADICTION_PHRASE` at the start of a normalised sentence, no letter after it.

    Built from the constant only (never from answer or source text); ``re``
    caches the compiled expression.
    """
    words = _normalise(CONTRADICTION_PHRASE).split()
    return re.compile(r"[\W_]*" + r"\s+".join(map(re.escape, words)) + r"(?!\s*[^\W\d_])")


def _missing_values(
    values: list[_Value],
    valid: list[int],
    compact: Mapping[int, _Compact],
    from_question: frozenset[str],
) -> tuple[str, ...]:
    """The values of a sentence found in none of its ``valid`` sources, as written.

    A type designation whose key is in ``from_question`` is not missing, but
    only if the sentence carries a further value that is not such a
    designation and is found in a valid source; otherwise it is missing like
    any other value. Only keys are compared.
    """
    checked = [
        (value, value.designation and value.key in from_question, _found(value, valid, compact))
        for value in values
    ]
    anchored = any(found for _, from_q, found in checked if not from_q)
    return tuple(
        value.display for value, from_q, found in checked if not found and not (from_q and anchored)
    )


def _found(value: _Value, valid: list[int], compact: Mapping[int, _Compact]) -> bool:
    return any(_occurs(value, compact[n]) for n in valid)


def verify(
    answer_text: str,
    sources: Mapping[int, str],
    *,
    drop_unsupported: bool,
    question: str | None = None,
) -> Verdict:
    """Check every sentence of ``answer_text`` against the numbered ``sources``.

    ``sources`` maps the source number ``n`` to the section text the model was
    shown. ``question`` is the question the answer replies to: a type
    designation from it that a sentence repeats need not be in the cited
    source, if the sentence carries a further check value that is (see
    "Values from the question" in the module docstring). Without a question
    (``None`` or empty) nothing is taken from it. The rules are described in
    the module docstring.
    """
    refusal = _bare(NO_EVIDENCE_TEXT)
    contradiction = _bare(CONTRADICTION_PHRASE)
    answer_bare = _bare(answer_text)
    if not answer_bare or answer_bare == refusal:
        return Verdict(
            status="no_evidence", cited=(), removed_sentences=(), cleaned_text=NO_EVIDENCE_TEXT
        )

    # Determined once per call, with the same rules as for answer sentences.
    from_question = (
        frozenset(value.key for value in _check_values(question) if value.designation)
        if question
        else frozenset()
    )
    lines = answer_text.split("\n")
    sentences = _split_sentences(lines)
    intros = _list_intros(lines, sentences)
    compact: dict[int, _Compact] = {}
    issues: list[SentenceIssue] = []
    dropped: set[int] = set()
    replaced: dict[int, str] = {}
    cited: set[int] = set()
    supported_numbers: dict[int, list[int]] = {}
    supported = 0

    for index, span in enumerate(sentences):
        text = lines[span.line][span.start : span.end]
        numbers = _extract_citations(text) if "[" in text else []
        if span.bare == refusal or (span.bare == contradiction and not numbers):
            continue
        valid = sorted({n for n in numbers if n in sources})
        invalid = tuple(sorted({n for n in numbers if n not in sources}))
        intro = intros[index]
        if not numbers and span.in_list and intro is not None:
            # A list item without its own number inherits the valid numbers of
            # a supported introduction sentence (empty if it was dropped).
            valid = supported_numbers.get(intro, [])
        if not valid:
            reason: IssueReason = "no_citation" if not numbers else "unknown_citation"
            issues.append(
                SentenceIssue(
                    index=index, reason=reason, values=(), invalid_numbers=invalid, kept=False
                )
            )
            dropped.add(index)
            continue
        for n in valid:
            if n not in compact:
                compact[n] = _compact(sources[n])
        values = _check_values(_CITATION.sub(" ", text))
        missing = _missing_values(values, valid, compact, from_question)
        if missing:
            issues.append(
                SentenceIssue(
                    index=index,
                    reason="unsupported_value",
                    values=missing,
                    invalid_numbers=invalid,
                    kept=False,
                )
            )
            dropped.add(index)
            continue
        supported += 1
        supported_numbers[index] = valid
        cited.update(valid)
        if invalid:
            issues.append(
                SentenceIssue(
                    index=index,
                    reason="unknown_citation",
                    values=(),
                    invalid_numbers=invalid,
                    kept=True,
                )
            )
            replaced[index] = _strip_invalid(text, sources)

    unsupported = tuple(issue for issue in issues if issue.index in dropped)
    if supported == 0:
        return Verdict(
            status="no_evidence",
            cited=(),
            removed_sentences=unsupported,
            cleaned_text=NO_EVIDENCE_TEXT,
        )

    cleaned = _cleaned(lines, sentences, dropped if drop_unsupported else set(), replaced)
    first = next(span for index, span in enumerate(sentences) if index not in dropped)
    opens_with_phrase = (
        _contradiction_pattern().match(_normalise(lines[first.line][first.start : first.end]))
        is not None
    )
    status: VerdictStatus = "contradiction" if opens_with_phrase and len(cited) >= 2 else "answered"
    return Verdict(
        status=status,
        cited=tuple(sorted(cited)),
        removed_sentences=tuple(issues),
        cleaned_text=cleaned,
    )
