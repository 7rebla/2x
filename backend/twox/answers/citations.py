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
    (``z. B.``, ``S. 34``, ``Nr.`` ...), inside numbers, IP addresses and
    versions (``1.5``, ``192.168.0.5``, ``V2.3.1``: the full stop is not
    followed by white space), nor after an ordinal number (``3.``) followed by
    a digit or a lower-case letter. Source numbers right after the
    punctuation (``... 24 V. [2]``) belong to the sentence before. Sentences
    with neither letters nor digits besides source numbers are skipped.

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
    letters and digits (``S7-1200``, ``1512SP``, ``UR5e``, ``1.5``). Addresses
    and type designations come from :func:`twox.search.identifiers.find_identifiers`.
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
    spaces, a decimal comma between two digits to a full stop, then white
    space and ``-`` removed. ``5 kg``/``5kg``, ``S7-1200``/``S7 1200`` and
    ``0,5 bar``/``0.5 bar`` are therefore equal. A value is found if it occurs
    in the normalised text of at least one source that the same sentence
    cites validly, and the occurrence is not lengthened: no letter or digit
    directly before or after it, nor a ``.`` (and for IPv6 and MAC addresses
    a ``:``) joining it to one, unless white space or ``-`` stood in between
    in the original. ``192.168.0.5`` does not match ``192.168.0.50`` and
    ``5 kg`` does not match ``25 kg``. A version may be preceded by ``v``, a
    number with a unit followed by ``AC`` or ``DC`` (``24 V`` in ``24VDC``).
    Each source text is normalised once per call.

Sentence verdict
    A sentence is ``unknown_citation`` if it carries source numbers but no
    valid one, ``no_citation`` if it carries none, ``unsupported_value`` if a
    check value is found in none of its valid sources, and supported
    otherwise. Invalid numbers in a supported sentence (``[2][9]`` with five
    sources) are removed from it; the sentence stays and is listed in
    ``removed_sentences`` with reason ``unknown_citation`` and the numbers in
    ``invalid_numbers``. The refusal sentence never needs a number; a
    sentence that consists only of :data:`CONTRADICTION_PHRASE` needs none
    either. Both are neither supported nor listed.

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
    if the answer contains :data:`CONTRADICTION_PHRASE` and the supported
    sentences cite at least two different valid numbers. ``answered``
    otherwise; a refusal sentence next to supported sentences (a partial
    answer) stays in the text.
"""

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal

from twox.search.identifiers import IdentifierKind, find_identifiers

#: The fixed refusal (guard rail 3). Placeholder until merged with ``types.py`` (122).
NO_EVIDENCE_TEXT: Final = "Dazu finde ich nichts in den Unterlagen."
#: The phrase that marks contradicting sources (question 6 of the test factory).
CONTRADICTION_PHRASE: Final = "Die Unterlagen widersprechen sich"

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

_CIT: Final = r"\[[ \t]*\d{1,6}(?:[ \t]*[,;][ \t]*\d{1,6})*[ \t]*\]"
_CITATION: Final = re.compile(_CIT)
_CITATION_RUN: Final = re.compile(rf"[ \t]*{_CIT}(?:[ \t]*{_CIT})*")
_NUMBER: Final = re.compile(r"\d+")
_SENTENCE_END: Final = re.compile(rf"[.!?]+[{re.escape(_QUOTE_CHARS)})]*(?:[ \t]*{_CIT})*(?=\s|$)")
_LIST_MARKER: Final = re.compile(rf"[ \t]*(?:[-*{_BULLET}]|\d{{1,3}}[.)])[ \t]+")
_ABBREVIATION: Final = re.compile(
    r"(?<!\w)(?:" + "|".join(re.escape(a).replace(r"\ ", r"\s?") for a in ABBREVIATIONS) + r")",
    re.IGNORECASE,
)
_NEXT_CHAR: Final = re.compile(r"[ \t]*(\S)")
_DECIMAL_COMMA: Final = re.compile(r"(?<=\d),(?=\d)")
_NOT_ALNUM: Final = re.compile(r"[\W_]+")

_UNIT_VALUE: Final = re.compile(
    r"(?<![\w.,])\d{1,9}(?:[.,]\d{1,9})?[ \t]?(?:"
    + "|".join(
        re.escape(unit)
        for unit in sorted({unicodedata.normalize("NFKC", u) for u in UNITS}, key=len, reverse=True)
    )
    + r")(?![\w%°])"
)
_PORT_WORD: Final = re.compile(
    r"(?<!\w)ports?[ \t]*(?:nr\.|no\.)?[ \t]*(\d{1,5})(?!\d)", re.IGNORECASE
)
_IPV4_PORT: Final = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})(?!\d)")
_VERSION_WORD: Final = re.compile(
    r"(?<!\w)(?:version|firmware|fw|release|rev\.?)[ \t]*v?(\d++(?:\.\d++)*+)(?![\w])",
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


@dataclass(frozen=True, slots=True)
class Verdict:
    """The result of :func:`verify`."""

    status: VerdictStatus
    cited: tuple[int, ...]  # valid source numbers used in kept sentences, ascending, unique
    removed_sentences: tuple[SentenceIssue, ...]  # dropped or flagged sentences
    cleaned_text: str  # final text for done.final_text


@dataclass(frozen=True, slots=True)
class _Sentence:
    """A sentence as a span of the answer: line number and columns in that line."""

    line: int
    start: int
    end: int
    bare: str  # letters and digits of the normalised sentence without source numbers


@dataclass(frozen=True, slots=True)
class _Value:
    """A check value: as written, and its normalised key."""

    display: str
    key: str
    colon_joins: bool = False
    version: bool = False
    unit: bool = False


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
    return _DECIMAL_COMMA.sub(".", folded)


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
            _add_sentence(sentences, number, line, segment_start, match.end())
            segment_start = match.end()
        _add_sentence(sentences, number, line, segment_start, len(line))
    return sentences


def _ends_with_ordinal(line: str, end: int) -> bool:
    """Whether ``line[:end]`` ends with a number of one to four digits standing alone."""
    start = end
    while start > 0 and end - start < 5 and line[start - 1].isdigit():
        start -= 1
    return 0 < end - start <= 4 and (start == 0 or line[start - 1].isspace())


def _add_sentence(
    sentences: list[_Sentence], line_number: int, line: str, start: int, end: int
) -> None:
    """Append the span ``line[start:end]`` without outer white space, unless it is empty."""
    while start < end and line[start].isspace():
        start += 1
    while end > start and line[end - 1].isspace():
        end -= 1
    text = line[start:end]
    bare = _bare(_CITATION.sub(" ", text) if "[" in text else text)
    if bare:
        sentences.append(_Sentence(line=line_number, start=start, end=end, bare=bare))


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
    found: dict[str, _Value] = {}

    def add(display: str, **flags: bool) -> None:
        key = _compact(display).text
        if key and key not in found:
            found[key] = _Value(display=display, key=key, **flags)

    for match in _UNIT_VALUE.finditer(text):
        add(match.group(), unit=True)
    for match in _PORT_WORD.finditer(text):
        add(match.group(1))
    for match in _IPV4_PORT.finditer(text):
        add(match.group(2))
    for match in _VERSION_WORD.finditer(text):
        add(match.group(1), version=True)
    for match in _VERSION_TOKEN.finditer(text):
        add(match.group(1), version=True)
    for identifier in find_identifiers(_IPV4_PORT.sub(r"\1 \2", text)):
        if identifier.kind is IdentifierKind.GENERIC and _VERSION_IDENTIFIER.fullmatch(
            identifier.value
        ):
            continue
        add(
            identifier.value,
            colon_joins=identifier.kind in {IdentifierKind.IPV6, IdentifierKind.MAC},
        )
    return list(found.values())


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


def verify(
    answer_text: str,
    sources: Mapping[int, str],
    *,
    drop_unsupported: bool,
) -> Verdict:
    """Check every sentence of ``answer_text`` against the numbered ``sources``.

    ``sources`` maps the source number ``n`` to the section text the model was
    shown. The rules are described in the module docstring.
    """
    refusal = _bare(NO_EVIDENCE_TEXT)
    contradiction = _bare(CONTRADICTION_PHRASE)
    answer_bare = _bare(answer_text)
    if not answer_bare or answer_bare == refusal:
        return Verdict(
            status="no_evidence", cited=(), removed_sentences=(), cleaned_text=NO_EVIDENCE_TEXT
        )

    lines = answer_text.split("\n")
    sentences = _split_sentences(lines)
    compact: dict[int, _Compact] = {}
    issues: list[SentenceIssue] = []
    dropped: set[int] = set()
    replaced: dict[int, str] = {}
    cited: set[int] = set()
    supported = 0

    for index, span in enumerate(sentences):
        text = lines[span.line][span.start : span.end]
        numbers = _extract_citations(text) if "[" in text else []
        if span.bare == refusal or (span.bare == contradiction and not numbers):
            continue
        valid = sorted({n for n in numbers if n in sources})
        invalid = tuple(sorted({n for n in numbers if n not in sources}))
        if not numbers or not valid:
            reason: IssueReason = "no_citation" if not numbers else "unknown_citation"
            issues.append(
                SentenceIssue(index=index, reason=reason, values=(), invalid_numbers=invalid)
            )
            dropped.add(index)
            continue
        for n in valid:
            if n not in compact:
                compact[n] = _compact(sources[n])
        missing = tuple(
            value.display
            for value in _check_values(_CITATION.sub(" ", text))
            if not any(_occurs(value, compact[n]) for n in valid)
        )
        if missing:
            issues.append(
                SentenceIssue(
                    index=index, reason="unsupported_value", values=missing, invalid_numbers=invalid
                )
            )
            dropped.add(index)
            continue
        supported += 1
        cited.update(valid)
        if invalid:
            issues.append(
                SentenceIssue(
                    index=index, reason="unknown_citation", values=(), invalid_numbers=invalid
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
    status: VerdictStatus = (
        "contradiction" if contradiction in answer_bare and len(cited) >= 2 else "answered"
    )
    return Verdict(
        status=status,
        cited=tuple(sorted(cited)),
        removed_sentences=tuple(issues),
        cleaned_text=cleaned,
    )
