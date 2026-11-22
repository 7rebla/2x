"""Sections from the DoclingDocument JSON (work order 043): real Docling output and small pieces.

The small JSON pieces below are written by hand. They copy the field names of
the real output in ``fixtures/`` but describe no plant and contain no vendor
text.
"""

import ast
import itertools
import json
from pathlib import Path
from typing import Any

import pytest
from pytest_django import Settings

from tests.ingest.fake_docling import BETRSICHV_FIXTURE, MARKDOWN_FIXTURE, fixture_document
from twox.ingest import sections
from twox.ingest.sections import (
    SectionDraft,
    UnsupportedDocumentError,
    build_sections,
    clean_text,
)

MAX_CHARS_VALUES = (1000, 2000)
MARKDOWN_TITLE = "Backups via secure copy (sftp)"


# --- helpers -------------------------------------------------------------------------------


def joined_tokens(drafts: list[SectionDraft]) -> list[str]:
    """All words of all sections, in order."""
    return " ".join(draft.text for draft in drafts).split()


def assert_within_limit(drafts: list[SectionDraft], max_chars: int) -> None:
    """Only a single sequence without white space may exceed ``max_chars``."""
    for draft in drafts:
        assert len(draft.text) <= max_chars or len(draft.text.split()) == 1, draft


def assert_valid_rows(drafts: list[SectionDraft]) -> None:
    """What the section model of 042 accepts: text, pages both set or both empty."""
    assert [draft.ordinal for draft in drafts] == list(range(len(drafts)))
    for draft in drafts:
        assert draft.text
        assert draft.text == draft.text.strip()
        assert "\x00" not in draft.text
        assert all(heading and "\x00" not in heading for heading in draft.heading_path)
        assert (draft.page_start is None) == (draft.page_end is None)
        if draft.page_start is not None and draft.page_end is not None:
            assert 1 <= draft.page_start <= draft.page_end


def prov(page: int, *more: int) -> list[dict[str, Any]]:
    """Provenance on the given pages, as Docling writes it (bbox shortened)."""
    return [
        {"page_no": number, "bbox": {"l": 0, "t": 10, "r": 10, "b": 0}, "charspan": [0, 1]}
        for number in (page, *more)
    ]


class DocumentBuilder:
    """A small DoclingDocument, built element by element in reading order."""

    def __init__(self) -> None:
        self.texts: list[dict[str, Any]] = []
        self.tables: list[dict[str, Any]] = []
        self.groups: list[dict[str, Any]] = []
        self.pictures: list[dict[str, Any]] = []
        self.body_children: list[dict[str, str]] = []

    def add(self, kind: str, item: dict[str, Any], parent: dict[str, Any] | None) -> dict[str, Any]:
        items: list[dict[str, Any]] = getattr(self, kind)
        reference = {"$ref": f"#/{kind}/{len(items)}"}
        item = {
            "self_ref": reference["$ref"],
            "parent": {"$ref": parent["self_ref"]} if parent else {"$ref": "#/body"},
            "children": [],
            "content_layer": "body",
            **item,
        }
        items.append(item)
        if parent is None:
            self.body_children.append(reference)
        else:
            parent["children"].append(reference)
        return item

    def text(
        self,
        text: str,
        *,
        label: str = "text",
        pages: list[dict[str, Any]] | None = None,
        parent: dict[str, Any] | None = None,
        **extra: object,
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "label": label,
            "prov": pages or [],
            "orig": text,
            "text": text,
            **extra,
        }
        return self.add("texts", item, parent)

    def heading(
        self, text: str, level: int = 1, pages: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        return self.text(text, label="section_header", level=level, pages=pages)

    def group(self, label: str, parent: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.add("groups", {"label": label, "name": label}, parent)

    def table(
        self,
        rows: list[list[str]],
        *,
        pages: list[dict[str, Any]] | None = None,
        spans: dict[tuple[int, int], int] | None = None,
    ) -> dict[str, Any]:
        """A table; ``spans`` maps (row, column) of a cell to its column span."""
        cells = []
        for row_index, row in enumerate(rows):
            column = 0
            for text in row:
                span = (spans or {}).get((row_index, column), 1)
                cells.append(
                    {
                        "text": text,
                        "row_span": 1,
                        "col_span": span,
                        "start_row_offset_idx": row_index,
                        "end_row_offset_idx": row_index + 1,
                        "start_col_offset_idx": column,
                        "end_col_offset_idx": column + span,
                        "column_header": row_index == 0,
                        "row_header": False,
                    }
                )
                column += span
        item = {
            "label": "table",
            "prov": pages or [],
            "captions": [],
            "footnotes": [],
            "references": [],
            "data": {
                "table_cells": cells,
                "num_rows": len(rows),
                "num_cols": max((len(row) for row in rows), default=0),
            },
        }
        return self.add("tables", item, None)

    def document(self, *, version: str = "1.10.0") -> dict[str, Any]:
        return {
            "schema_name": "DoclingDocument",
            "version": version,
            "name": "sample",
            "furniture": {"self_ref": "#/furniture", "children": [], "label": "unspecified"},
            "body": {
                "self_ref": "#/body",
                "children": self.body_children,
                "content_layer": "body",
                "name": "_root_",
                "label": "unspecified",
            },
            "groups": self.groups,
            "texts": self.texts,
            "pictures": self.pictures,
            "tables": self.tables,
            "key_value_items": [],
            "form_items": [],
            "pages": {},
        }


# --- real Docling output: BetrSichV, pages 1 to 5 -----------------------------------------


@pytest.fixture(scope="module")
def betrsichv() -> dict[str, Any]:
    return fixture_document(BETRSICHV_FIXTURE)


@pytest.mark.parametrize("max_chars", MAX_CHARS_VALUES)
def test_pdf_pages_are_between_1_and_5_and_never_fall(
    betrsichv: dict[str, Any], max_chars: int
) -> None:
    drafts = build_sections(betrsichv, max_chars=max_chars)

    assert len(drafts) > 5
    assert_valid_rows(drafts)
    starts = [draft.page_start for draft in drafts]
    ends = [draft.page_end for draft in drafts]
    assert all(page is not None and 1 <= page <= 5 for page in starts + ends)
    assert starts == sorted(starts, key=lambda page: page or 0)
    assert ends == sorted(ends, key=lambda page: page or 0)
    assert drafts[0].page_start == 1
    assert drafts[-1].page_end == 5


@pytest.mark.parametrize("max_chars", (*MAX_CHARS_VALUES, 300, 120))
def test_pdf_sections_stay_within_max_chars_and_lose_no_word(
    betrsichv: dict[str, Any], max_chars: int
) -> None:
    drafts = build_sections(betrsichv, max_chars=max_chars)
    whole = build_sections(betrsichv, max_chars=10**9)

    assert_within_limit(drafts, max_chars)
    assert_valid_rows(drafts)
    # Cut only at white space: no word is lost, doubled or split.
    assert joined_tokens(drafts) == joined_tokens(whole)


@pytest.mark.parametrize("max_chars", MAX_CHARS_VALUES)
def test_pdf_small_pieces_of_one_heading_are_joined(
    betrsichv: dict[str, Any], max_chars: int
) -> None:
    drafts = build_sections(betrsichv, max_chars=max_chars)

    for before, after in itertools.pairwise(drafts):
        if before.heading_path == after.heading_path:
            # The next piece did not fit, otherwise they would be one section.
            assert len(before.text) + 1 + len(after.text) > max_chars


@pytest.mark.parametrize("max_chars", MAX_CHARS_VALUES)
def test_pdf_has_no_page_header_or_footer(betrsichv: dict[str, Any], max_chars: int) -> None:
    furniture = [item for item in betrsichv["texts"] if item["content_layer"] == "furniture"]
    assert {item["label"] for item in furniture} == {"page_header", "page_footer"}

    drafts = build_sections(betrsichv, max_chars=max_chars)

    everything = "\n".join(draft.text for draft in drafts)
    for item in furniture:
        assert clean_text(item["text"]) not in everything
    assert "Seite 1 von 60" not in everything


@pytest.mark.parametrize("max_chars", MAX_CHARS_VALUES)
def test_pdf_text_from_the_json_is_in_the_section_of_its_page(
    betrsichv: dict[str, Any], max_chars: int
) -> None:
    # Looked up in the JSON: the first paragraph of § 1 is #/texts/17 on page 2.
    item = next(
        entry
        for entry in betrsichv["texts"]
        if entry["text"].startswith("(1) Diese Verordnung gilt für die Verwendung")
    )
    assert item["self_ref"] == "#/texts/17"
    assert [entry["page_no"] for entry in item["prov"]] == [2]

    drafts = build_sections(betrsichv, max_chars=max_chars)

    found = [draft for draft in drafts if item["text"] in draft.text]
    assert len(found) == 1
    assert found[0].page_start == 2
    assert found[0].heading_path == ("§ 1 Anwendungsbereich und Zielsetzung",)


@pytest.mark.parametrize("max_chars", MAX_CHARS_VALUES)
def test_pdf_every_body_text_lies_in_a_section_with_its_pages(
    betrsichv: dict[str, Any], max_chars: int
) -> None:
    drafts = build_sections(betrsichv, max_chars=max_chars)

    for item in betrsichv["texts"]:
        text = clean_text(item["text"])
        if item["content_layer"] != "body" or len(text) > max_chars:
            continue
        pages = [entry["page_no"] for entry in item["prov"]]
        found = [draft for draft in drafts if text in draft.text]
        if item["label"] == "section_header":
            # Headings are in the path; a heading without own text moves into the next section.
            assert found or any(text in draft.heading_path for draft in drafts), text
            continue
        assert found, text
        assert any(
            draft.page_start is not None
            and draft.page_end is not None
            and draft.page_start <= min(pages)
            and max(pages) <= draft.page_end
            for draft in found
        ), text


def test_pdf_paragraph_over_two_pages_gives_both_pages(betrsichv: dict[str, Any]) -> None:
    item = betrsichv["texts"][65]
    assert [entry["page_no"] for entry in item["prov"]] == [4, 5]

    drafts = build_sections(betrsichv, max_chars=2000)

    (found,) = [draft for draft in drafts if item["text"] in draft.text]
    assert (found.page_start, found.page_end) == (4, 5)


def test_pdf_heading_paths_lists_and_tables(betrsichv: dict[str, Any]) -> None:
    drafts = build_sections(betrsichv, max_chars=2000)

    paths = list(dict.fromkeys(draft.heading_path for draft in drafts))
    assert paths[-3:] == [
        ("§ 2 Begriffsbestimmungen",),
        ("§ 3 Gefährdungsbeurteilung",),
        ("§ 4 Grundpflichten des Arbeitgebers",),
    ]
    text = "\n".join(draft.text for draft in drafts)
    # List items keep their marker, one per line.
    assert "1. die Auswahl geeigneter Arbeitsmittel und deren sichere Verwendung,\n2. die " in text
    # Table of contents: one line per row, cells joined with " | ".
    assert "\n§ 1 | Anwendungsbereich und Zielsetzung\n§ 2 | Begriffsbestimmungen" in text
    # A heading followed directly by another heading moves into the next section.
    (first_of_section_1,) = [
        draft
        for draft in drafts
        if draft.heading_path == ("§ 1 Anwendungsbereich und Zielsetzung",)
    ][:1]
    assert first_of_section_1.text.startswith(
        "Abschnitt 1 Anwendungsbereich und Begriffsbestimmungen\n\n(1) Diese Verordnung"
    )


def test_pdf_sections_are_the_same_on_every_run(betrsichv: dict[str, Any]) -> None:
    copy = json.loads(json.dumps(betrsichv))

    assert build_sections(betrsichv, max_chars=1000) == build_sections(copy, max_chars=1000)


# --- real Docling output: Markdown ---------------------------------------------------------


@pytest.fixture(scope="module")
def markdown() -> dict[str, Any]:
    return fixture_document(MARKDOWN_FIXTURE)


@pytest.mark.parametrize("max_chars", MAX_CHARS_VALUES)
def test_markdown_heading_path_without_pages(markdown: dict[str, Any], max_chars: int) -> None:
    drafts = build_sections(markdown, max_chars=max_chars)

    assert_valid_rows(drafts)
    assert_within_limit(drafts, max_chars)
    assert all(draft.page_start is None and draft.page_end is None for draft in drafts)
    assert list(dict.fromkeys(draft.heading_path for draft in drafts)) == [
        (MARKDOWN_TITLE,),
        (MARKDOWN_TITLE, "Preparation"),
        (MARKDOWN_TITLE, "Initial setup"),
        (MARKDOWN_TITLE, "Finish and test"),
    ]


def test_markdown_inline_text_code_and_table(markdown: dict[str, Any]) -> None:
    drafts = build_sections(markdown, max_chars=2000)

    by_path = {draft.heading_path[-1]: draft.text for draft in drafts}
    # The parts of an inline group form one paragraph.
    assert "(in System->Firmware->Plugins search for os-sftp-backup)." in by_path[MARKDOWN_TITLE]
    # Code keeps its line breaks.
    assert (
        "Enter passphrase (empty for no passphrase):\nEnter same passphrase again:"
        in (by_path["Preparation"])
    )
    # The table row keeps the address word for word; the empty header row is gone.
    assert (
        "\nURL | Target location, which defines protocol, user and path. This may look like: "
        '<span class="title-ref">sftp://opnsense@192.168.1.10//home/opnsense/config_backups</span>'
        in by_path["Initial setup"]
    )
    assert "\n | " not in by_path["Initial setup"]


# --- small hand-written pieces ---------------------------------------------------------------


def test_table_rows_cells_spans_caption_and_footnote() -> None:
    doc = DocumentBuilder()
    doc.heading("Network", pages=prov(1))
    table = doc.table(
        [
            ["Device", "Address", "Port"],
            ["", "", ""],
            ["Controller", "10.0.0.20", "502"],
            ["Spare unit", ""],
            ["Note spanning two columns", "x"],
        ],
        pages=prov(2, 3),
        spans={(3, 1): 2, (4, 0): 2},
    )
    caption = doc.text("Table 1: addresses", label="caption", pages=prov(2), parent=table)
    footnote = doc.text("Values as delivered.", label="footnote", pages=prov(3), parent=table)
    table["captions"] = [{"$ref": caption["self_ref"]}]
    table["footnotes"] = [{"$ref": footnote["self_ref"]}]

    (draft,) = build_sections(doc.document(), max_chars=2000)

    assert draft.heading_path == ("Network",)
    assert draft.text == (
        "Table 1: addresses\n\n"
        "Device | Address | Port\n"
        "Controller | 10.0.0.20 | 502\n"
        "Spare unit |\n"
        "Note spanning two columns | x\n\n"
        "Values as delivered."
    )
    assert (draft.page_start, draft.page_end) == (2, 3)


def test_nested_groups_keep_reading_order() -> None:
    doc = DocumentBuilder()
    doc.heading("Steps")
    chapter = doc.group("chapter")
    doc.text("Before you start:", parent=chapter)
    outer = doc.group("list", parent=chapter)
    first = doc.text("Switch off", label="list_item", marker="1.", parent=outer)
    doc.text("Open the cover", label="list_item", marker="2.", parent=outer)
    inner = doc.group("list", parent=first)
    doc.text("main switch", label="list_item", marker="", parent=inner)
    doc.text("lock it", label="list_item", marker="•", parent=inner)
    inline = doc.group("inline", parent=chapter)
    doc.text("Run", parent=inline)
    doc.text("check --all", label="code", parent=inline)
    nested_inline = doc.group("inline", parent=inline)
    doc.text("afterwards.", parent=nested_inline)

    (draft,) = build_sections(doc.document(), max_chars=2000)

    assert draft.text == (
        "Before you start:\n\n"
        "1. Switch off\n"
        "- main switch\n"
        "• lock it\n"
        "2. Open the cover\n\n"
        "Run check --all afterwards."
    )


def test_headings_set_the_path_by_level() -> None:
    doc = DocumentBuilder()
    doc.text("Manual", label="title")
    doc.text("Intro text.")
    doc.heading("Install", level=1)
    doc.heading("Mounting", level=2)
    doc.text("Mount it.")
    doc.heading("Wiring", level=2)
    doc.text("Wire it.")
    doc.heading("Operate", level=1)
    doc.text("Run it.")
    doc.heading("Odd level", level=0)  # invalid: counts as level 1
    doc.text("Odd.")

    drafts = build_sections(doc.document(), max_chars=2000)

    assert [(draft.heading_path, draft.text) for draft in drafts] == [
        (("Manual",), "Intro text."),
        (("Manual", "Install", "Mounting"), "Mount it."),
        (("Manual", "Install", "Wiring"), "Wire it."),
        (("Manual", "Operate"), "Run it."),
        (("Manual", "Odd level"), "Odd."),
    ]


def test_heading_without_text_moves_into_the_next_section() -> None:
    doc = DocumentBuilder()
    doc.text("Text before any heading.", pages=prov(1))
    doc.heading("Part 1", pages=prov(1))
    doc.heading("Chapter 1", pages=prov(2))
    doc.text("Chapter text.", pages=prov(2))
    doc.heading("Appendix", pages=prov(9))

    drafts = build_sections(doc.document(), max_chars=2000)

    assert [
        (draft.heading_path, draft.text, draft.page_start, draft.page_end) for draft in drafts
    ] == [
        ((), "Text before any heading.", 1, 1),
        (("Chapter 1",), "Part 1\n\nChapter text.", 1, 2),
        (("Appendix",), "Appendix", 9, 9),
    ]


def test_missing_provenance_leaves_the_pages_empty() -> None:
    doc = DocumentBuilder()
    doc.heading("Without pages")
    doc.text("No provenance at all.")
    doc.heading("Mixed")
    doc.text("No provenance.")
    doc.text("On page 4.", pages=prov(4))
    doc.text("Invalid page numbers.", pages=[{"page_no": 0}, {"page_no": "5"}, {"page_no": True}])

    drafts = build_sections(doc.document(), max_chars=2000)

    assert [(draft.page_start, draft.page_end) for draft in drafts] == [(None, None), (4, 4)]
    assert_valid_rows(drafts)


def test_empty_texts_give_no_section() -> None:
    doc = DocumentBuilder()
    doc.heading("")
    doc.text("")
    doc.text(" \t\n ")
    doc.text("\x00\x07")
    doc.text("", label="list_item", marker="1.")
    doc.table([["", ""], [" ", "\x00"]])
    doc.group("inline")

    assert build_sections(doc.document(), max_chars=2000) == []


def test_nul_and_control_characters_are_removed() -> None:
    doc = DocumentBuilder()
    doc.heading("Pump\x00 P-101\x1b")
    doc.text(
        "Pressure\x00 is\x07 6\tbar,\r\n  flow \N{SOFT HYPHEN}\N{ZERO WIDTH NO-BREAK SPACE}is"
        "\N{ZERO WIDTH SPACE} ok.\ud800"
    )
    doc.table([["Va\x00lve", "V-7\x08"]])
    doc.text("line\x00 1\n\n\tline  2\x0c", label="code")

    (draft,) = build_sections(doc.document(), max_chars=2000)

    assert draft.heading_path == ("Pump P-101",)
    assert draft.text == "Pressure is 6 bar, flow is ok.\n\nValve | V-7\n\nline 1\nline 2"


def test_page_header_and_footer_are_left_out_captions_and_footnotes_stay() -> None:
    doc = DocumentBuilder()
    doc.text("Header text", label="page_header", content_layer="furniture", pages=prov(1))
    doc.text("Footer in the body layer", label="page_footer", pages=prov(1))
    doc.text("Decoration", content_layer="background", pages=prov(1))
    doc.text("Body text.", pages=prov(2))
    picture = {"label": "picture", "prov": prov(3), "captions": [], "footnotes": []}
    picture = doc.add("pictures", picture, None)
    caption = doc.text("Figure 1: front view", label="caption", pages=prov(3), parent=picture)
    picture["captions"] = [{"$ref": caption["self_ref"]}]
    doc.text("1) Footnote text.", label="footnote", pages=prov(3))

    (draft,) = build_sections(doc.document(), max_chars=2000)

    assert draft.text == "Body text.\n\nFigure 1: front view\n\n1) Footnote text."
    assert (draft.page_start, draft.page_end) == (2, 3)


@pytest.mark.parametrize(
    ("schema_name", "version"),
    [
        ("DoclingDocument", None),
        ("DoclingDocument", ""),
        ("DoclingDocument", "2.0.0"),
        ("DoclingDocument", "0.9.0"),
        ("DoclingDocument", "1.10"),
        ("DoclingDocument", "1.10.0-beta"),
        ("DoclingDocument", 1),
        (None, "1.10.0"),
        ("OtherDocument", "1.10.0"),
    ],
)
def test_unknown_or_missing_schema_version_is_rejected(
    schema_name: str | None, version: object
) -> None:
    document = DocumentBuilder().document()
    for key, value in (("schema_name", schema_name), ("version", version)):
        if value is None:
            del document[key]
        else:
            document[key] = value

    with pytest.raises(UnsupportedDocumentError):
        build_sections(document, max_chars=2000)


@pytest.mark.parametrize("version", ["1.0.0", "1.10.0", "1.11.2"])
def test_schema_version_1_is_accepted(version: str) -> None:
    doc = DocumentBuilder()
    doc.text("Text.")

    assert len(build_sections(doc.document(version=version), max_chars=2000)) == 1


@pytest.mark.parametrize(
    "reference",
    [
        {"$ref": "#/texts/7"},
        {"$ref": "#/unknown/0"},
        {"$ref": "#/texts/-1"},
        {"$ref": "#/texts/01"},
        {"$ref": "texts/0"},
        {"ref": "#/texts/0"},
        "#/texts/0",
    ],
)
def test_broken_reference_is_rejected(reference: object) -> None:
    doc = DocumentBuilder()
    doc.text("Text.")
    document = doc.document()
    document["body"]["children"].append(reference)

    with pytest.raises(UnsupportedDocumentError):
        build_sections(document, max_chars=2000)


def test_missing_body_and_too_deep_nesting_are_rejected() -> None:
    document = DocumentBuilder().document()
    del document["body"]
    with pytest.raises(UnsupportedDocumentError):
        build_sections(document, max_chars=2000)

    doc = DocumentBuilder()
    parent = doc.group("chapter")
    for _ in range(sections.MAX_DEPTH + 1):
        parent = doc.group("chapter", parent=parent)
    doc.text("Deep.", parent=parent)
    with pytest.raises(UnsupportedDocumentError):
        build_sections(doc.document(), max_chars=2000)


def test_element_referenced_twice_appears_once() -> None:
    doc = DocumentBuilder()
    item = doc.text("Only once.")
    document = doc.document()
    document["body"]["children"].append({"$ref": item["self_ref"]})
    item["children"].append({"$ref": item["self_ref"]})

    assert [draft.text for draft in build_sections(document, max_chars=2000)] == ["Only once."]


def test_overlong_table_row_keeps_the_ip_address_in_one_section() -> None:
    address = "192.168.100.200"
    description = " ".join(
        [*["word"] * 30, f"reachable at {address}.", "Then", *["more"] * 30, "end."]
    )
    doc = DocumentBuilder()
    doc.heading("Addresses")
    doc.table([["Name", "Description"], ["Gateway", description]], pages=prov(7))

    drafts = build_sections(doc.document(), max_chars=60)

    assert len(drafts) > 4
    assert_within_limit(drafts, 60)
    assert [draft for draft in drafts if address in draft.text] == [
        draft for draft in drafts if "192.168" in draft.text
    ]
    assert sum(address in draft.text for draft in drafts) == 1
    assert joined_tokens(drafts) == [
        "Name",
        "|",
        "Description",
        "Gateway",
        "|",
        *description.split(),
    ]
    assert all((draft.page_start, draft.page_end) == (7, 7) for draft in drafts)
    assert all(draft.heading_path == ("Addresses",) for draft in drafts)


def test_overlong_paragraph_is_cut_at_sentence_ends() -> None:
    sentences = [f"Sentence number {index} says something useful." for index in range(12)]
    doc = DocumentBuilder()
    doc.text(" ".join(sentences), pages=prov(3))

    drafts = build_sections(doc.document(), max_chars=100)

    assert_within_limit(drafts, 100)
    assert [draft.text for draft in drafts] == [
        " ".join(sentences[index : index + 2]) for index in range(0, 12, 2)
    ]
    assert all((draft.page_start, draft.page_end) == (3, 3) for draft in drafts)


def test_sentence_end_behind_a_closing_quote_or_bracket() -> None:
    text = (
        'The panel shows "Ready." (Wait for it.) '
        "\N{LEFT-POINTING DOUBLE ANGLE QUOTATION MARK}Then start\N{HORIZONTAL ELLIPSIS}"
        "\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK} Done."
    )
    doc = DocumentBuilder()
    doc.text(text)

    drafts = build_sections(doc.document(), max_chars=25)

    assert [draft.text for draft in drafts] == [
        'The panel shows "Ready."',
        "(Wait for it.)",
        "\N{LEFT-POINTING DOUBLE ANGLE QUOTATION MARK}Then start\N{HORIZONTAL ELLIPSIS}"
        "\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK} Done.",
    ]


def test_overlong_paragraph_without_sentence_ends_is_cut_at_white_space() -> None:
    words = [f"token{index}" for index in range(40)]
    doc = DocumentBuilder()
    doc.text(" ".join(words))

    drafts = build_sections(doc.document(), max_chars=50)

    assert len(drafts) > 1
    assert_within_limit(drafts, 50)
    assert joined_tokens(drafts) == words
    # Greedy: every section but the last is full up to the next word.
    for before, after in itertools.pairwise(drafts):
        assert len(before.text) + 1 + len(after.text.split()[0]) > 50


def test_a_single_sequence_longer_than_max_chars_stands_alone() -> None:
    blob = "A" * 150
    doc = DocumentBuilder()
    doc.text(f"Short start {blob} short end.")

    drafts = build_sections(doc.document(), max_chars=100)

    assert [draft.text for draft in drafts] == ["Short start", blob, "short end."]


def test_small_paragraphs_of_one_heading_are_joined_up_to_max_chars() -> None:
    doc = DocumentBuilder()
    doc.heading("A")
    for index in range(6):
        doc.text(f"Paragraph {index}.", pages=prov(index + 1))
    doc.heading("B")
    doc.text("Other heading.")

    drafts = build_sections(doc.document(), max_chars=30)

    assert [(draft.heading_path, draft.text) for draft in drafts] == [
        (("A",), "Paragraph 0.\n\nParagraph 1."),
        (("A",), "Paragraph 2.\n\nParagraph 3."),
        (("A",), "Paragraph 4.\n\nParagraph 5."),
        (("B",), "Other heading."),
    ]
    assert [(draft.page_start, draft.page_end) for draft in drafts[:3]] == [
        (1, 2),
        (3, 4),
        (5, 6),
    ]


@pytest.mark.parametrize("max_chars", [0, -1, True])
def test_max_chars_must_be_positive(max_chars: int) -> None:
    with pytest.raises(ValueError, match="max_chars"):
        build_sections(DocumentBuilder().document(), max_chars=max_chars)


# --- E-59: no dependency on the AI features --------------------------------------------------


@pytest.mark.parametrize("ai_enabled", [False, True])
def test_sections_do_not_depend_on_the_ai_switch(
    settings: Settings, betrsichv: dict[str, Any], ai_enabled: bool
) -> None:
    settings.TWOX_AI_ENABLED = ai_enabled

    drafts = build_sections(betrsichv, max_chars=2000)

    assert drafts == build_sections(json.loads(json.dumps(betrsichv)), max_chars=2000)
    assert len(drafts) == 13


def test_module_uses_the_standard_library_only() -> None:
    """Pure function: no Django, no database, no network, no model."""
    tree = ast.parse(Path(sections.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert imported == {"re", "unicodedata", "collections", "dataclasses", "typing"}
