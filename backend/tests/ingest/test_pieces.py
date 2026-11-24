"""Splitting a section into pieces for the vector search (work order 150, E-75)."""

import pytest

from twox.ingest.pieces import DEFAULT_PIECE_MAX_CHARS, Span, split_pieces


def texts(text: str, spans: list[Span]) -> list[str]:
    return [text[start:end] for start, end in spans]


def assert_well_formed(text: str, spans: list[Span], max_chars: int) -> None:
    """In order, without overlap, at most ``max_chars``, no white space at the ends,
    and nothing but white space between and around them."""
    position = 0
    for start, end in spans:
        assert position <= start < end <= len(text)
        assert end - start <= max_chars
        assert not text[start].isspace()
        assert not text[end - 1].isspace()
        assert text[position:start].strip() == ""
        position = end
    assert text[position:].strip() == ""


def test_default_size_is_the_measured_one() -> None:
    # Diagnosis 147, variant V4a. The setting itself may differ in a local .env.
    assert DEFAULT_PIECE_MAX_CHARS == 1000


@pytest.mark.parametrize("text", ["", "x", "Short section.", "a" * 10, "  padded  "])
def test_a_short_section_is_one_piece_its_whole_text(text: str) -> None:
    assert split_pieces(text, 20) == [(0, len(text))]


def test_a_text_of_exactly_the_limit_is_one_piece() -> None:
    text = "abcd efghi"
    assert split_pieces(text, len(text)) == [(0, len(text))]


def test_pieces_are_cut_at_white_space_as_long_as_possible() -> None:
    text = "one two three four five six"

    spans = split_pieces(text, 9)

    assert texts(text, spans) == ["one two", "three", "four five", "six"]
    assert_well_formed(text, spans, 9)


def test_a_space_right_after_the_limit_still_gives_a_piece_of_full_length() -> None:
    text = "abcd efgh ijkl"

    assert texts(text, split_pieces(text, 9)) == ["abcd efgh", "ijkl"]


def test_white_space_between_pieces_belongs_to_neither() -> None:
    text = "alpha  \n\n  beta\t\tgamma   delta"

    spans = split_pieces(text, 12)

    assert texts(text, spans) == ["alpha", "beta\t\tgamma", "delta"]
    assert_well_formed(text, spans, 12)


def test_a_word_longer_than_the_limit_is_cut_hard() -> None:
    text = "start " + "x" * 25 + " end"

    spans = split_pieces(text, 10)

    # The rest after the cut fits into one piece again.
    assert texts(text, spans) == ["start", "x" * 10, "x" * 10, "xxxxx end"]
    assert_well_formed(text, spans, 10)


def test_a_text_without_any_space_is_cut_into_full_pieces() -> None:
    text = "y" * 23

    assert split_pieces(text, 10) == [(0, 10), (10, 20), (20, 23)]


def test_leading_and_trailing_white_space_of_a_long_text_is_left_out() -> None:
    text = "   first second third   "

    spans = split_pieces(text, 12)

    assert texts(text, spans) == ["first second", "third"]
    assert_well_formed(text, spans, 12)


def test_only_white_space_longer_than_a_piece_gives_one_empty_piece() -> None:
    assert split_pieces(" " * 30, 10) == [(0, 0)]


def test_unicode_positions_are_code_points() -> None:
    # Umlauts, a character outside the BMP and a non-breaking space (white space).
    text = "Prüfung der Überdruckventile 𝄞 Öl\u00a0wechseln größer"

    spans = split_pieces(text, 12)

    assert texts(text, spans) == ["Prüfung der", "Überdruckven", "tile 𝄞 Öl", "wechseln", "größer"]
    assert_well_formed(text, spans, 12)


def test_a_section_of_2000_characters_gives_pieces_of_at_most_1000() -> None:
    words = [f"word{index:03d}" for index in range(260)]
    text = " ".join(words)
    assert 2000 < len(text) < 2100

    spans = split_pieces(text, DEFAULT_PIECE_MAX_CHARS)

    assert len(spans) == 3
    assert_well_formed(text, spans, DEFAULT_PIECE_MAX_CHARS)
    # No word is lost or cut.
    assert " ".join(texts(text, spans)).split() == words


@pytest.mark.parametrize("max_chars", [0, -1])
def test_a_limit_below_one_is_refused(max_chars: int) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        split_pieces("text", max_chars)
