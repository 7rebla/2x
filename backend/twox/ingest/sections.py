"""Sections of a converted document, built from the DoclingDocument JSON (E-55).

:func:`build_sections` turns the JSON that docling-serve returns (work order
041) into :class:`SectionDraft` objects: a piece of text with its heading path
and the pages it comes from. The page is the source of every later answer, so
it is taken from the provenance of the elements a section contains and never
guessed. The function is pure: no database, no network, no settings, and the
same document always gives the same sections. It works the same with and
without the AI features (E-59); embeddings are a later, optional step.

Document contents are data, not instructions: the text is cleaned and cut,
never interpreted.

Rules, in the order of the JSON:

- The reading order is ``body.children``; references (``$ref``) to ``texts``,
  ``tables``, ``groups`` and ``pictures`` are resolved recursively.
- ``title`` (level 0) and ``section_header`` (its ``level``) start a new
  section and set the heading path: a heading replaces every heading of the
  same or a deeper level. The heading is not repeated in the text. A heading
  that is replaced before any text followed it would otherwise be lost (PDFs
  often give every heading level 1); its text becomes the first paragraph of
  the next section instead.
- Page headers and footers (``page_header``, ``page_footer`` and the layers
  ``furniture`` and ``background``) are left out; captions and footnotes stay.
- Paragraphs are separated by a blank line. List items keep their marker and
  stand on lines of their own; the parts of an ``inline`` group form one
  paragraph. A table becomes one line per row with the cells joined by
  ``" | "``; values stay word for word.
- A section longer than ``max_chars`` is cut at paragraph and line
  boundaries; a paragraph or row that is too long on its own is cut at
  sentence ends and then at white space. Nothing is ever cut inside a
  sequence without white space, so a single such sequence longer than
  ``max_chars`` is the only thing that exceeds the limit.
- Pieces are filled greedily: small paragraphs, list items, rows and the
  rest of a cut paragraph join the following pieces of the same heading as
  long as the total stays within ``max_chars``.
- ``page_start`` and ``page_end`` are the smallest and largest ``page_no`` in
  the provenance of the contained elements. Without provenance (Markdown,
  for example) both stay ``None``.
- Control characters, NUL, lone surrogates and a few invisible characters are
  removed; white space is collapsed to one space. Code blocks keep their line
  breaks.
- A document whose ``schema_name`` is not ``DoclingDocument`` or whose
  ``version`` is not ``1.x.y`` raises :class:`UnsupportedDocumentError`, as
  does a document with a broken structure.
"""

import re
import unicodedata
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

SCHEMA_NAME: Final = "DoclingDocument"
#: Major version of the DoclingDocument schema the rules were written for.
#: Measured with version 1.10.0 (docling-serve 1.38.2, work order 041).
SUPPORTED_SCHEMA_MAJOR: Final = 1

PARAGRAPH_SEPARATOR: Final = "\n\n"
LINE_SEPARATOR: Final = "\n"
CELL_SEPARATOR: Final = " | "
#: Joins the parts of an ``inline`` group (text with code or links inside).
INLINE_SEPARATOR: Final = " "

#: Content layers that never belong to a section (page decoration).
SKIPPED_LAYERS: Final = frozenset({"furniture", "background"})
#: Labels that never belong to a section, whatever their layer.
SKIPPED_LABELS: Final = frozenset({"page_header", "page_footer"})
TITLE_LABEL: Final = "title"
SECTION_HEADER_LABEL: Final = "section_header"
LIST_ITEM_LABEL: Final = "list_item"
#: Text labels whose line breaks are kept.
MULTILINE_LABELS: Final = frozenset({"code"})
LIST_GROUP_LABELS: Final = frozenset({"list", "ordered_list"})
INLINE_GROUP_LABELS: Final = frozenset({"inline"})
#: Marker of a list item that has none in the JSON.
DEFAULT_LIST_MARKER: Final = "-"

#: Nesting depth of references; deeper documents are rejected, not followed.
MAX_DEPTH: Final = 200

_REFERENCE = re.compile(r"#/(?P<kind>[a-z_]+)/(?P<index>0|[1-9][0-9]*)")
_SCHEMA_VERSION = re.compile(r"(?P<major>0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
_WHITESPACE = re.compile(r"\s+")
# Invisible format characters that only get in the way of searching: soft
# hyphen, zero width space, word joiner and byte order mark.
_INVISIBLE = frozenset(
    {
        "\N{SOFT HYPHEN}",
        "\N{ZERO WIDTH SPACE}",
        "\N{WORD JOINER}",
        "\N{ZERO WIDTH NO-BREAK SPACE}",
    }
)
# Sentence ends, and the closing quotes and brackets that may follow them.
_STOPS = ".!?\N{HORIZONTAL ELLIPSIS}"
_CLOSERS = re.escape(
    "\"')]\N{LEFT-POINTING DOUBLE ANGLE QUOTATION MARK}"
    "\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK}"
    "\N{LEFT SINGLE QUOTATION MARK}\N{RIGHT SINGLE QUOTATION MARK}"
    "\N{LEFT DOUBLE QUOTATION MARK}\N{RIGHT DOUBLE QUOTATION MARK}"
)
# Where an overlong paragraph may be cut, from the best to the last resort:
# line breaks, sentence ends (white space after a stop, also behind a closing
# quote or bracket), any white space. Each pattern captures the separator so
# that the pieces can be joined again exactly.
_CUT_PATTERNS: Final = (
    re.compile(r"(\n+)"),
    re.compile(rf"((?<=[{_STOPS}])\s+|(?<=[{_STOPS}][{_CLOSERS}])\s+)"),
    re.compile(r"(\s+)"),
)

type _Pages = tuple[int, int] | None


class UnsupportedDocumentError(ValueError):
    """The JSON is not a DoclingDocument this module can read."""


@dataclass(frozen=True, slots=True)
class SectionDraft:
    """One section of a document, not yet stored (046 stores it, 042)."""

    #: Position in the document, counted from 0 without gaps.
    ordinal: int
    #: Headings from the outermost to the innermost; empty before the first.
    heading_path: tuple[str, ...]
    #: Never empty.
    text: str
    #: Both set or both ``None``; ``page_start <= page_end``, counted from 1.
    page_start: int | None
    page_end: int | None


def build_sections(document: Mapping[str, object], *, max_chars: int) -> list[SectionDraft]:
    """The sections of a DoclingDocument, in reading order.

    ``max_chars`` is the largest section length in characters (setting
    ``TWOX_SECTION_MAX_CHARS``, work order 045). Raises
    :class:`UnsupportedDocumentError` for a document of an unknown schema or
    with a broken structure, :class:`ValueError` for ``max_chars`` below 1.
    """
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise ValueError("max_chars must be a positive integer.")
    _check_schema(document)
    builder = _SectionBuilder(max_chars)
    _Walker(document, builder).walk()
    return builder.finish()


def clean_text(value: str, *, keep_line_breaks: bool = False) -> str:
    """``value`` without control characters, with white space collapsed.

    With ``keep_line_breaks`` every line is cleaned on its own and empty lines
    are dropped, so the result has single line breaks between lines.
    """
    if keep_line_breaks:
        lines = (clean_text(line) for line in value.splitlines())
        return LINE_SEPARATOR.join(line for line in lines if line)
    kept = "".join(
        char
        for char in value
        if char.isspace()
        or (unicodedata.category(char) not in ("Cc", "Cs") and char not in _INVISIBLE)
    )
    return _WHITESPACE.sub(" ", kept).strip()


def _check_schema(document: Mapping[str, object]) -> None:
    if not isinstance(document, Mapping):
        raise UnsupportedDocumentError("The Docling result is not a JSON object.")
    if document.get("schema_name") != SCHEMA_NAME:
        raise UnsupportedDocumentError("The Docling result is not a DoclingDocument.")
    version = document.get("version")
    match = _SCHEMA_VERSION.fullmatch(version) if isinstance(version, str) else None
    if match is None or int(match["major"]) != SUPPORTED_SCHEMA_MAJOR:
        raise UnsupportedDocumentError("The DoclingDocument schema version is not supported.")


def _merge_pages(first: _Pages, second: _Pages) -> _Pages:
    if first is None:
        return second
    if second is None:
        return first
    return (min(first[0], second[0]), max(first[1], second[1]))


def _item_pages(item: Mapping[str, object]) -> _Pages:
    """Smallest and largest ``prov[].page_no`` of an element, if any."""
    pages: _Pages = None
    for entry in _sequence(item.get("prov")):
        if not isinstance(entry, Mapping):
            continue
        page = entry.get("page_no")
        if isinstance(page, int) and not isinstance(page, bool) and page >= 1:
            pages = _merge_pages(pages, (page, page))
    return pages


def _sequence(value: object) -> Sequence[object]:
    """``value`` if it is a JSON list, else an empty list."""
    return value if isinstance(value, list) else []


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _header_level(value: object) -> int:
    """``level`` of a ``section_header``; 1 if it is missing or invalid."""
    if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
        return value
    return 1


def _cut(text: str, level: int, max_chars: int) -> list[tuple[str, str]]:
    """``text`` as ``(separator before, piece)``; cut where needed, see the module doc."""
    if len(text) <= max_chars or level >= len(_CUT_PATTERNS):
        return [("", text)]
    parts = _CUT_PATTERNS[level].split(text)
    if len(parts) == 1:
        return _cut(text, level + 1, max_chars)
    pieces: list[tuple[str, str]] = []
    separator = ""
    for index in range(0, len(parts), 2):
        segment = parts[index]
        following = parts[index + 1] if index + 1 < len(parts) else ""
        if segment:
            first, *rest = _cut(segment, level + 1, max_chars)
            pieces.append((separator, first[1]))
            pieces.extend(rest)
            separator = following
        else:
            separator += following
    return pieces


@dataclass(frozen=True, slots=True)
class _Piece:
    """Smallest unit of a section: never cut further, packed greedily."""

    separator: str
    text: str
    pages: _Pages


@dataclass(slots=True)
class _Heading:
    level: int
    text: str
    pages: _Pages
    # True once a section with this heading in its path was emitted.
    used: bool = False


class _SectionBuilder:
    """Collects headings and paragraphs and packs them into sections."""

    def __init__(self, max_chars: int) -> None:
        self._max_chars = max_chars
        self._headings: list[_Heading] = []
        self._pieces: list[_Piece] = []
        # Paragraphs from headings that were replaced before any text.
        self._carried: list[_Piece] = []
        self._drafts: list[SectionDraft] = []

    def heading(self, level: int, text: str, pages: _Pages) -> None:
        if not text:
            return
        self._close_section()
        while self._headings and self._headings[-1].level >= level:
            self._drop_heading()
        self._headings.append(_Heading(level, text, pages))

    def paragraph(self, text: str, pages: _Pages, separator: str) -> None:
        if not text:
            return
        if self._carried:
            self._pieces.extend(self._carried)
            self._carried.clear()
        cut = _cut(text, 0, self._max_chars)
        for index, (inner_separator, piece) in enumerate(cut):
            self._pieces.append(_Piece(separator if index == 0 else inner_separator, piece, pages))

    def finish(self) -> list[SectionDraft]:
        self._close_section()
        path = self._path()
        while self._headings:
            self._drop_heading()
        if self._carried:
            self._pieces = list(self._carried)
            self._carried.clear()
            self._close_section(path)
        return self._drafts

    def _path(self) -> tuple[str, ...]:
        return tuple(heading.text for heading in self._headings)

    def _drop_heading(self) -> None:
        heading = self._headings.pop()
        if not heading.used:
            # The heading was replaced before any text: keep its words.
            self._carried.append(_Piece(PARAGRAPH_SEPARATOR, heading.text, heading.pages))

    def _close_section(self, path: tuple[str, ...] | None = None) -> None:
        if not self._pieces:
            return
        heading_path = self._path() if path is None else path
        for heading in self._headings:
            heading.used = True
        for group in self._pack(self._pieces):
            pages: _Pages = None
            for piece in group:
                pages = _merge_pages(pages, piece.pages)
            text = group[0].text + "".join(piece.separator + piece.text for piece in group[1:])
            self._drafts.append(
                SectionDraft(
                    ordinal=len(self._drafts),
                    heading_path=heading_path,
                    text=text,
                    page_start=None if pages is None else pages[0],
                    page_end=None if pages is None else pages[1],
                )
            )
        self._pieces = []

    def _pack(self, pieces: Sequence[_Piece]) -> Iterator[list[_Piece]]:
        group: list[_Piece] = []
        length = 0
        for piece in pieces:
            added = len(piece.separator) + len(piece.text)
            if group and length + added <= self._max_chars:
                group.append(piece)
                length += added
                continue
            if group:
                yield group
            group = [piece]
            length = len(piece.text)
        if group:
            yield group


class _Walker:
    """Follows the reading order of ``body`` and feeds the builder."""

    def __init__(self, document: Mapping[str, object], builder: _SectionBuilder) -> None:
        self._document = document
        self._builder = builder
        self._visited: set[str] = set()

    def walk(self) -> None:
        body = self._document.get("body")
        if not isinstance(body, Mapping):
            raise UnsupportedDocumentError("The DoclingDocument has no body.")
        self._visited.add("#/body")
        self._children(body, 0, PARAGRAPH_SEPARATOR, PARAGRAPH_SEPARATOR)

    def _resolve(self, reference: object) -> tuple[str, str, Mapping[str, object]]:
        """Kind, reference and element of a ``{"$ref": "#/kind/N"}``."""
        target = reference.get("$ref") if isinstance(reference, Mapping) else None
        match = _REFERENCE.fullmatch(target) if isinstance(target, str) else None
        if match is None or not isinstance(target, str):
            raise UnsupportedDocumentError("The DoclingDocument has an invalid reference.")
        items = self._document.get(match["kind"])
        index = int(match["index"])
        if not isinstance(items, list) or index >= len(items):
            raise UnsupportedDocumentError("The DoclingDocument has an invalid reference.")
        item = items[index]
        if not isinstance(item, Mapping):
            raise UnsupportedDocumentError("The DoclingDocument has an invalid element.")
        return match["kind"], target, item

    def _children(self, item: Mapping[str, object], depth: int, first: str, following: str) -> None:
        """Visit the children: the first with separator ``first``, the rest ``following``."""
        for index, child in enumerate(_sequence(item.get("children"))):
            self._visit(child, depth + 1, first if index == 0 else following)

    def _references(self, item: Mapping[str, object], key: str, depth: int) -> None:
        for reference in _sequence(item.get(key)):
            self._visit(reference, depth + 1, PARAGRAPH_SEPARATOR)

    def _visit(self, reference: object, depth: int, separator: str) -> None:
        if depth > MAX_DEPTH:
            raise UnsupportedDocumentError("The DoclingDocument is nested too deeply.")
        kind, target, item = self._resolve(reference)
        if target in self._visited:
            return
        self._visited.add(target)
        if item.get("content_layer") in SKIPPED_LAYERS or item.get("label") in SKIPPED_LABELS:
            return
        label = _string(item.get("label"))
        if kind == "texts":
            self._text(item, label, separator)
            self._children(item, depth, LINE_SEPARATOR, LINE_SEPARATOR)
        elif kind == "tables":
            self._references(item, "captions", depth)
            self._table(item, separator)
            self._children(item, depth, PARAGRAPH_SEPARATOR, PARAGRAPH_SEPARATOR)
            self._references(item, "footnotes", depth)
        elif kind == "groups" and label in INLINE_GROUP_LABELS:
            parts: list[str] = []
            pages = self._inline(item, depth, parts)
            self._builder.paragraph(INLINE_SEPARATOR.join(parts), pages, separator)
        elif kind == "groups" and label in LIST_GROUP_LABELS:
            self._children(item, depth, separator, LINE_SEPARATOR)
        else:
            # Other groups (chapters, slides, sheets ...) and pictures: the
            # element has no text of its own; its captions and children do.
            self._references(item, "captions", depth)
            self._children(item, depth, separator, PARAGRAPH_SEPARATOR)
            self._references(item, "footnotes", depth)

    def _text(self, item: Mapping[str, object], label: str, separator: str) -> None:
        raw = _string(item.get("text"))
        pages = _item_pages(item)
        if label == TITLE_LABEL:
            self._builder.heading(0, clean_text(raw), pages)
            return
        if label == SECTION_HEADER_LABEL:
            self._builder.heading(_header_level(item.get("level")), clean_text(raw), pages)
            return
        text = clean_text(raw, keep_line_breaks=label in MULTILINE_LABELS)
        if text and label == LIST_ITEM_LABEL:
            marker = clean_text(_string(item.get("marker"))) or DEFAULT_LIST_MARKER
            text = f"{marker} {text}"
        self._builder.paragraph(text, pages, separator)

    def _inline(self, item: Mapping[str, object], depth: int, parts: list[str]) -> _Pages:
        """Collect the text of an ``inline`` group into ``parts``; return its pages."""
        pages = _item_pages(item)
        for reference in _sequence(item.get("children")):
            if depth + 1 > MAX_DEPTH:
                raise UnsupportedDocumentError("The DoclingDocument is nested too deeply.")
            kind, target, child = self._resolve(reference)
            if target in self._visited:
                continue
            self._visited.add(target)
            if child.get("content_layer") in SKIPPED_LAYERS or child.get("label") in SKIPPED_LABELS:
                continue
            if kind == "texts":
                text = clean_text(_string(child.get("text")))
                if text:
                    parts.append(text)
                pages = _merge_pages(pages, _item_pages(child))
            pages = _merge_pages(pages, self._inline(child, depth + 1, parts))
        return pages

    def _table(self, item: Mapping[str, object], separator: str) -> None:
        """One paragraph per row, cells joined with :data:`CELL_SEPARATOR`."""
        data = item.get("data")
        if not isinstance(data, Mapping):
            return
        rows: dict[int, dict[int, list[str]]] = {}
        for cell in _sequence(data.get("table_cells")):
            if not isinstance(cell, Mapping):
                continue
            row = cell.get("start_row_offset_idx")
            column = cell.get("start_col_offset_idx")
            if not isinstance(row, int) or not isinstance(column, int):
                continue
            # A cell spanning several rows or columns appears once, at its start.
            rows.setdefault(row, {}).setdefault(column, []).append(
                clean_text(_string(cell.get("text")))
            )
        pages = _item_pages(item)
        first = True
        for row_index in sorted(rows):
            columns = rows[row_index]
            cells = [" ".join(columns[column]).strip() for column in sorted(columns)]
            line = CELL_SEPARATOR.join(cells).strip()
            if not any(cells):
                continue
            self._builder.paragraph(line, pages, separator if first else LINE_SEPARATOR)
            first = False
