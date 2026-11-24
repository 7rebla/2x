"""Splitting a section into pieces for the vector search (work order 150, E-75).

A pure function: no database, no settings. The embed step
(:mod:`twox.ingest.pipeline`) embeds every piece with the heading path in
front (``embedding_text(heading_text, piece)``) and stores the positions in
:class:`~twox.ingest.models.SectionPiece`; the text of a piece is cut from the
section again whenever it is needed.
"""

from typing import Final

#: A piece as positions in the section text: ``text[start:end]``.
type Span = tuple[int, int]

#: Default of ``TWOX_PIECE_MAX_CHARS``: measured in work order 147 (variant V4a).
DEFAULT_PIECE_MAX_CHARS: Final = 1000


def split_pieces(text: str, max_chars: int) -> list[Span]:
    """``text`` cut into pieces of at most ``max_chars`` characters, as spans.

    * A text of at most ``max_chars`` characters (also an empty one) is one
      piece, the whole text ``(0, len(text))``; its embedding is the one of
      the section.
    * A longer text is cut at white space, from the front: each piece is as
      long as possible. The white space between two pieces belongs to
      neither, so pieces never overlap and never start or end with white
      space.
    * A word longer than ``max_chars`` (a long address, a table row without
      spaces) is cut hard after ``max_chars`` characters.

    Positions count Unicode code points, like Python and PostgreSQL text
    functions, so ``text[start:end]`` is the piece in both.
    """
    if max_chars < 1:
        raise ValueError(f"max_chars must be at least 1, not {max_chars}")
    length = len(text)
    if length <= max_chars:
        return [(0, length)]
    spans: list[Span] = []
    position = _skip_space(text, 0)
    while position < length:
        limit = position + max_chars
        if limit >= length:
            end = _trim_end(text, position, length)
            spans.append((position, end))
            break
        # A space right after the window still ends a piece of full length.
        cut = _last_space(text, position, limit)
        if cut is None:
            # One word longer than the window: cut it hard.
            spans.append((position, limit))
            position = limit
        else:
            spans.append((position, _trim_end(text, position, cut)))
            position = cut
        position = _skip_space(text, position)
    # Only white space, longer than a piece: one empty piece, so that the
    # section still has a piece (the heading path alone is embedded).
    return spans or [(0, 0)]


def _skip_space(text: str, position: int) -> int:
    """The first position at or after ``position`` that is not white space."""
    while position < len(text) and text[position].isspace():
        position += 1
    return position


def _trim_end(text: str, start: int, end: int) -> int:
    """``end`` moved back over white space, but not before ``start``."""
    while end > start and text[end - 1].isspace():
        end -= 1
    return end


def _last_space(text: str, start: int, limit: int) -> int | None:
    """The last white space in ``text[start + 1 : limit + 1]``, or ``None``.

    ``start`` itself is never white space (the caller skips it), so a cut
    there would give an empty piece.
    """
    for index in range(limit, start, -1):
        if text[index].isspace():
            return index
    return None
