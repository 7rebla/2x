"""Keyword and exact search in PostgreSQL (047).

All texts are written for these tests; none comes from a manufacturer's
manual.
"""

import dataclasses
import hashlib
import itertools
import socket
from collections.abc import Iterator, Sequence

import pytest
from django.contrib.postgres.search import SearchQuery
from django.db import connection
from pytest_django import DjangoAssertNumQueries
from pytest_django.fixtures import Settings

from tests.search.fake_embedder import FakeEmbedder, install
from twox.assets.models import Area, Device, Plant, Site
from twox.files.models import Document, DocumentKind, DocumentVersion
from twox.files.storage import key_for_sha256
from twox.ingest.models import EMBEDDING_DIMENSIONS, IngestJob, IngestStatus, Section
from twox.search.interface import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MAX_QUERY_LENGTH,
    HitLocation,
    MatchKind,
    SearchHit,
    SearchRequest,
    SearchResult,
    get_search_backend,
)
from twox.search.postgres import (
    ELLIPSIS,
    SNIPPET_MAX_LENGTH,
    PostgresSearchBackend,
    make_snippet,
    marked_spans,
)

pytestmark = pytest.mark.django_db

_numbers = itertools.count(1)


# --- Helpers ---------------------------------------------------------------


def make_plant(key: str = "line-a") -> Plant:
    site, _ = Site.objects.get_or_create(name="Search site")
    area, _ = Area.objects.get_or_create(site=site, name="Search area")
    return Plant.objects.create(area=area, key=key, name=f"Plant {key}")


def make_device(plant: Plant, key: str) -> Device:
    return Device.objects.create(plant=plant, key=key, name=f"Device {key}")


def sha256_of(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def add_version(
    document: Document, number: int | None = None, sha256: str | None = None
) -> DocumentVersion:
    """A new version of ``document``; its bytes are not needed for the search."""
    if number is None:
        number = document.versions.count() + 1
    sha256 = sha256 or sha256_of(f"content {next(_numbers)}")
    return DocumentVersion.objects.create(
        document=document,
        number=number,
        blob_key=key_for_sha256(sha256),
        sha256=sha256,
        size=10,
        content_type="application/pdf",
        original_filename="manual.pdf",
    )


def make_document(
    device: Device,
    title: str = "Operating manual",
    kind: str = DocumentKind.DOCUMENT,
    sha256: str | None = None,
) -> DocumentVersion:
    """A document of ``device`` with one version; returns the version."""
    document = Document.objects.create(device=device, title=title, kind=kind)
    return add_version(document, sha256=sha256)


def add_sections(
    version: DocumentVersion,
    *texts: str,
    headings: Sequence[str] = ("Operation",),
    page: int | None = 1,
    status: str = IngestStatus.DONE,
) -> list[Section]:
    """Sections with ``texts`` from a finished ingest job of ``version``."""
    job = IngestJob.objects.create(document_version=version, status=status)
    first = version.sections.count()
    return [
        Section.objects.create(
            document_version=version,
            ingest_job=job,
            ordinal=first + index,
            page_start=page,
            page_end=page,
            heading_path=list(headings),
            text=text,
        )
        for index, text in enumerate(texts)
    ]


def search(
    query: str,
    device_ids: Sequence[int] = (),
    plant_ids: Sequence[int] = (),
    limit: int = DEFAULT_LIMIT,
) -> SearchResult:
    request = SearchRequest(query=query, device_ids=device_ids, plant_ids=plant_ids, limit=limit)
    return PostgresSearchBackend().search(request)


def found_texts(result: SearchResult) -> set[str]:
    return {Section.objects.get(pk=hit.section_id).text for hit in result.hits}


def highlighted(hit: SearchHit) -> list[str]:
    return [hit.snippet[h.start : h.end] for h in hit.highlights]


@pytest.fixture
def plant() -> Plant:
    return make_plant()


@pytest.fixture
def device(plant: Plant) -> Device:
    return make_device(plant, "plc-01")


@pytest.fixture
def version(device: Device) -> DocumentVersion:
    return make_document(device)


# --- Identifiers -----------------------------------------------------------


def test_ip_address_finds_exactly_its_section(version: DocumentVersion) -> None:
    add_sections(
        version,
        "The controller listens on 192.168.0.5 for the panel.",
        "The panel itself has the address 192.168.0.50 in the cell.",
        "The gateway is 10.192.168.0.5 in the old plan.",
    )

    five = search("192.168.0.5")
    fifty = search("192.168.0.50")

    assert found_texts(five) == {"The controller listens on 192.168.0.5 for the panel."}
    assert five.hits[0].match_kinds == [MatchKind.EXACT, MatchKind.KEYWORD]
    assert highlighted(five.hits[0]) == ["192.168.0.5"]
    assert found_texts(fifty) == {"The panel itself has the address 192.168.0.50 in the cell."}


def test_ip_address_in_a_table_row_is_found(version: DocumentVersion) -> None:
    row = "| Station | Address | Mask |\n| PLC-01 | 192.168.0.7 | 255.255.255.0 |"
    add_sections(version, row, "| PLC-02 | 192.168.0.70 | 255.255.255.0 |")

    result = search("192.168.0.7")

    assert found_texts(result) == {row}
    assert highlighted(result.hits[0]) == ["192.168.0.7"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("10.0.0.1/24", "Route 10.0.0.1/24 leads to the cell."),
        ("fe80::1", "The link-local address fe80::1 answers."),
        ("00:1B:1B:AA:BB:CC", "The interface 00:1b:1b:aa:bb:cc is the first port."),
        ("PLC-01", "The station PLC-01 starts the conveyor."),
        ("E1234", "Fault E1234: the door is open."),
    ],
)
def test_identifiers_are_found_word_for_word(
    version: DocumentVersion, query: str, expected: str
) -> None:
    add_sections(
        version,
        expected,
        "Route 10.0.0.1/240 is a typing error.",
        "The address fe80::10 answers as well.",
        "The interface 00:1b:1b:aa:bb:cd is the second port.",
        "The station PLC-010 starts the second conveyor.",
        "Fault E12345: the door is closed.",
    )

    result = search(query)

    assert found_texts(result) == {expected}
    assert MatchKind.EXACT in result.hits[0].match_kinds
    assert [text.casefold() for text in highlighted(result.hits[0])] == [query.casefold()]


def test_exact_hits_come_first(version: DocumentVersion) -> None:
    # The address only in the heading: found by the full-text search only.
    (in_heading,) = add_sections(
        version, "Settings of the network card.", headings=["Address 192.168.0.5"]
    )
    (in_text,) = add_sections(version, "The card uses 192.168.0.5 as its address.", page=2)

    result = search("192.168.0.5")

    assert [hit.section_id for hit in result.hits] == [in_text.pk, in_heading.pk]
    assert result.hits[0].match_kinds == [MatchKind.EXACT, MatchKind.KEYWORD]
    assert result.hits[1].match_kinds == [MatchKind.KEYWORD]
    assert result.hits[0].score >= 1 > result.hits[1].score > 0


def test_identifier_alone_is_found_next_to_other_words(version: DocumentVersion) -> None:
    add_sections(
        version,
        "The pump of station PLC-01 runs.",
        "Station PLC-01 has no motor.",
        "The pump of station PLC-02 runs.",
    )

    result = search("pump PLC-01")

    # Both words: exact and keyword; the identifier alone: exact only, after it.
    assert [Section.objects.get(pk=hit.section_id).text for hit in result.hits] == [
        "The pump of station PLC-01 runs.",
        "Station PLC-01 has no motor.",
    ]
    assert result.hits[1].match_kinds == [MatchKind.EXACT]


# --- Word forms ------------------------------------------------------------


def test_german_word_forms_are_found(version: DocumentVersion) -> None:
    add_sections(version, "Die Steuerung startet den Motor.", "Das Band läuft an.")

    result = search("Steuerungen")

    assert found_texts(result) == {"Die Steuerung startet den Motor."}
    assert result.hits[0].match_kinds == [MatchKind.KEYWORD]
    assert highlighted(result.hits[0]) == ["Steuerung"]


def test_english_word_forms_are_found(version: DocumentVersion) -> None:
    add_sections(version, "The pumps are running at full speed.", "The valve is closed.")

    result = search("pump runs")

    assert found_texts(result) == {"The pumps are running at full speed."}
    assert highlighted(result.hits[0]) == ["pumps", "running"]


def test_words_in_heading_and_text_together(version: DocumentVersion) -> None:
    add_sections(version, "Close the valve before you start.", headings=["Safety", "Valves"])

    result = search("safety valve")

    assert len(result.hits) == 1
    assert result.hits[0].heading_path == ["Safety", "Valves"]
    assert highlighted(result.hits[0]) == ["valve"]


def test_heading_matches_rank_above_text_matches(version: DocumentVersion) -> None:
    (text_only,) = add_sections(version, "Check the conveyor belt every week.")
    (heading,) = add_sections(version, "Check the belt every week.", headings=["Conveyor"], page=2)

    result = search("conveyor")

    assert [hit.section_id for hit in result.hits] == [heading.pk, text_only.pk]


# --- Phrases across the joined search vectors ------------------------------


def test_phrase_matches_in_order_only(version: DocumentVersion) -> None:
    (section,) = add_sections(version, "Ventil öffnen")

    # The joined vector has "öffnen" (simple copy) right before "Ventil"
    # (german copy); the check per configuration rejects that seam.
    seam = SearchQuery('"öffnen Ventil"', search_type="websearch", config="simple")
    assert Section.objects.filter(pk=section.pk, search_vector=seam).exists()
    assert search('"öffnen Ventil"').hits == []
    assert [hit.section_id for hit in search('"Ventil öffnen"').hits] == [section.pk]


def test_phrase_does_not_match_across_the_seam_of_configurations(
    version: DocumentVersion,
) -> None:
    add_sections(version, "stop", headings=[])

    # simple, german and english copy: "stop" three times in a row.
    assert search('"stop stop"').hits == []
    assert len(search("stop").hits) == 1


def test_phrase_with_word_forms(version: DocumentVersion) -> None:
    add_sections(version, "Die Pumpen laufen langsam an.", "Laufen die Pumpen?")

    result = search('"Pumpe laufen"')

    # German stems: "pump" <-> "lauf"; only the first text has this order.
    assert found_texts(result) == {"Die Pumpen laufen langsam an."}


def test_phrase_stays_within_heading_or_text(version: DocumentVersion) -> None:
    add_sections(version, "valve opens slowly.", headings=["Safety"])

    # Between the heading and the text of one configuration lie the other two
    # heading copies; a phrase does not span them.
    assert search('"safety valve"').hits == []
    assert len(search("safety valve").hits) == 1
    assert len(search('"valve opens" safety').hits) == 1


def test_phrase_does_not_span_heading_and_text_with_unchanged_stems(
    version: DocumentVersion,
) -> None:
    # "motor" and "start" keep their form in every configuration, so without
    # the gap the last heading word would stand right before the first text word.
    add_sections(version, "Start the drive.", headings=["Motor"])

    assert search('"motor start"').hits == []
    assert len(search("motor start").hits) == 1


# --- Documents, versions, ingest state -------------------------------------


def test_configuration_documents_are_not_searched(device: Device) -> None:
    document = make_document(device, title="Manual")
    configuration = make_document(device, title="Backup", kind=DocumentKind.CONFIGURATION)
    add_sections(document, "The router forwards port 502.")
    add_sections(configuration, "The router forwards port 503.")

    assert found_texts(search("router forwards")) == {"The router forwards port 502."}


def test_newest_version_with_sections_is_searched(version: DocumentVersion) -> None:
    add_sections(version, "Old text mentions the alpha belt.")
    newer = add_version(version.document)
    add_sections(newer, "New text mentions the beta belt.")

    assert search("alpha").hits == []
    result = search("beta")
    assert len(result.hits) == 1
    (location,) = result.hits[0].locations
    assert location.version_id == newer.pk
    assert location.version_number == 2
    assert location.is_latest_version is True


@pytest.mark.parametrize(
    "newer_status",
    [None, IngestStatus.QUEUED, IngestStatus.RUNNING, IngestStatus.FAILED, IngestStatus.SKIPPED],
)
def test_older_version_is_found_while_the_newer_has_no_sections(
    version: DocumentVersion, newer_status: str | None
) -> None:
    add_sections(version, "The gamma belt stops at night.")
    newer = add_version(version.document)
    if newer_status is not None:
        IngestJob.objects.create(document_version=newer, status=newer_status)

    result = search("gamma")

    assert len(result.hits) == 1
    (location,) = result.hits[0].locations
    assert location.version_id == version.pk
    assert location.version_number == 1
    assert location.is_latest_version is False


def test_sections_are_found_while_the_same_version_is_ingested_again(
    version: DocumentVersion,
) -> None:
    add_sections(version, "The delta belt starts in the morning.")
    job = IngestJob.objects.create(document_version=version, status=IngestStatus.QUEUED)

    assert len(search("delta").hits) == 1
    job.status = IngestStatus.RUNNING
    job.save()
    assert len(search("delta").hits) == 1
    assert search("delta").hits[0].locations[0].is_latest_version is True


@pytest.mark.parametrize("status", [IngestStatus.FAILED, IngestStatus.DONE])
def test_sections_without_embedding_are_found(version: DocumentVersion, status: str) -> None:
    # Embedding failed (job failed in step "embed") or AI features off (done).
    (section,) = add_sections(version, "The epsilon sensor reads the level.", status=status)
    assert section.embedding is None

    assert [hit.section_id for hit in search("epsilon").hits] == [section.pk]


def test_sections_with_embedding_are_found_as_well(version: DocumentVersion) -> None:
    (section,) = add_sections(version, "The zeta sensor reads the level.")
    Section.objects.filter(pk=section.pk).update(
        embedding=[0.1] * EMBEDDING_DIMENSIONS, embedding_model="test-model"
    )

    assert [hit.section_id for hit in search("zeta").hits] == [section.pk]


# --- Filters and locations -------------------------------------------------


def test_filter_by_device_and_plant(plant: Plant) -> None:
    other_plant = make_plant("line-b")
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    third = make_device(other_plant, "plc-03")
    for device in (first, second, third):
        add_sections(make_document(device), f"The eta drive of {device.key} is ready.")

    def devices(device_ids: Sequence[int] = (), plant_ids: Sequence[int] = ()) -> set[str]:
        result = search("eta drive", device_ids=device_ids, plant_ids=plant_ids)
        return {location.device_key for hit in result.hits for location in hit.locations}

    assert devices() == {"plc-01", "plc-02", "plc-03"}
    assert devices(device_ids=[second.pk]) == {"plc-02"}
    assert devices(device_ids=[first.pk, third.pk]) == {"plc-01", "plc-03"}
    assert devices(plant_ids=[other_plant.pk]) == {"plc-03"}
    assert devices(plant_ids=[plant.pk]) == {"plc-01", "plc-02"}
    assert devices(plant_ids=[plant.pk], device_ids=[third.pk]) == set()
    assert devices(plant_ids=[plant.pk], device_ids=[first.pk, third.pk]) == {"plc-01"}


def test_location_names_document_version_device_and_plant(
    plant: Plant, device: Device, version: DocumentVersion
) -> None:
    (section,) = add_sections(version, "The theta lamp is green.")

    (hit,) = search("theta").hits

    assert hit.locations == [
        HitLocation(
            section_id=section.pk,
            document_id=version.document_id,
            document_title="Operating manual",
            version_id=version.pk,
            version_number=1,
            is_latest_version=True,
            device_id=device.pk,
            device_key="plc-01",
            device_name="Device plc-01",
            plant_id=plant.pk,
            plant_key="line-a",
            plant_name="Plant line-a",
        )
    ]
    assert hit.page_start == 1
    assert hit.page_end == 1
    assert hit.heading_path == ["Operation"]


def test_same_file_on_two_devices_is_one_hit(plant: Plant) -> None:
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    shared = sha256_of("shared manual")
    one = make_document(first, title="Manual A", sha256=shared)
    two = make_document(second, title="Manual B", sha256=shared)
    add_sections(one, "The iota valve opens at 3 bar.")
    add_sections(two, "The iota valve opens at 3 bar.")

    (hit,) = search("iota").hits
    (filtered,) = search("iota", device_ids=[second.pk]).hits

    assert [location.device_key for location in hit.locations] == ["plc-01", "plc-02"]
    assert {location.section_id for location in hit.locations} == {
        hit.section_id,
        *(s.pk for s in two.sections.all()),
    }
    assert [location.device_key for location in filtered.locations] == ["plc-02"]
    assert filtered.section_id == two.sections.get().pk


def test_same_file_but_other_page_or_text_stays_apart(plant: Plant) -> None:
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    shared = sha256_of("shared manual")
    add_sections(make_document(first, sha256=shared), "The kappa valve opens.", page=1)
    add_sections(make_document(second, sha256=shared), "The kappa valve opens.", page=2)
    add_sections(make_document(second, sha256=shared), "The kappa valve opens!", page=1)

    assert len(search("kappa").hits) == 3


def test_same_text_without_pages_merges_by_headings(plant: Plant) -> None:
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    shared = sha256_of("shared notes")
    one = make_document(first, sha256=shared)
    two = make_document(second, sha256=shared)
    add_sections(one, "The lambda switch is on.", page=None, headings=["Start"])
    add_sections(two, "The lambda switch is on.", page=None, headings=["Start"])
    add_sections(two, "The lambda switch is on.", page=None, headings=["Stop"])

    result = search("lambda")

    assert sorted(len(hit.locations) for hit in result.hits) == [1, 2]
    assert all(hit.page_start is None for hit in result.hits)


def test_different_files_with_same_text_stay_apart(plant: Plant) -> None:
    add_sections(make_document(make_device(plant, "plc-01")), "The mu lamp blinks.")
    add_sections(make_document(make_device(plant, "plc-02")), "The mu lamp blinks.")

    assert len(search("lamp blinks").hits) == 2


def test_limit_counts_merged_hits(plant: Plant) -> None:
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    shared = sha256_of("shared manual")
    one = make_document(first, sha256=shared)
    two = make_document(second, sha256=shared)
    texts = [f"The nu belt number {index} runs." for index in range(5)]
    add_sections(one, *texts)
    add_sections(two, *texts)

    result = search("nu belt", limit=2)

    assert len(result.hits) == 2
    assert all(len(hit.locations) == 2 for hit in result.hits)


# --- Robustness --------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "",
        "   ",
        "'",
        "\\",
        "(",
        ")",
        '"',
        "'; DROP TABLE ingest_section; --",
        "a & b | !c",
        "<-> :* <2>",
        "\x00",
        "pump\x00valve",
        "-",
        "-pump",
        "der die das",
        "%(query)s",
        "%s",
        "[[:alnum:]]",
        ".*",
    ],
)
def test_empty_and_special_queries_do_not_fail(version: DocumentVersion, query: str) -> None:
    add_sections(version, "The pump and the valve.")

    result = search(query)

    assert isinstance(result, SearchResult)
    assert result.semantic_used is False


def test_empty_query_runs_no_sql(django_assert_num_queries: DjangoAssertNumQueries) -> None:
    with django_assert_num_queries(0):
        assert search("  ").hits == []


def test_special_characters_around_words_still_find(version: DocumentVersion) -> None:
    add_sections(version, "The xi pump (left) starts.")

    assert len(search("(xi) 'pump'").hits) == 1
    assert len(search("xi\\").hits) == 1


def test_regular_expression_characters_are_taken_literally(version: DocumentVersion) -> None:
    add_sections(version, "Address 192.168.0.5 is set.", "Address 192x168y0z5 is set.")

    assert found_texts(search("192.168.0.5")) == {"Address 192.168.0.5 is set."}


def test_query_and_limit_are_checked() -> None:
    with pytest.raises(ValueError, match="limit"):
        SearchRequest(query="pump", limit=0)
    with pytest.raises(ValueError, match="limit"):
        SearchRequest(query="pump", limit=MAX_LIMIT + 1)
    with pytest.raises(ValueError, match="query"):
        SearchRequest(query="x" * (MAX_QUERY_LENGTH + 1))
    assert SearchRequest(query="x" * MAX_QUERY_LENGTH, limit=MAX_LIMIT).limit == MAX_LIMIT


# --- Snippet and highlights ------------------------------------------------


def test_highlights_lie_on_the_found_place_in_a_long_text(version: DocumentVersion) -> None:
    before = " ".join(f"word{index}" for index in range(200))
    after = " ".join(f"tail{index}" for index in range(200))
    add_sections(version, f"{before} The omicron valve is at 192.168.0.5 now. {after}")

    (hit,) = search("omicron 192.168.0.5").hits

    assert highlighted(hit) == ["omicron", "192.168.0.5"]
    assert hit.snippet.startswith(ELLIPSIS)
    assert hit.snippet.endswith(ELLIPSIS)
    assert len(hit.snippet) <= SNIPPET_MAX_LENGTH + 2 * len(ELLIPSIS)


def test_match_in_heading_only_gives_the_start_of_the_text(version: DocumentVersion) -> None:
    add_sections(version, "Close all doors first.", headings=["Pi procedure"])

    (hit,) = search("pi").hits

    assert hit.snippet == "Close all doors first."
    assert hit.highlights == []


def test_make_snippet_short_text() -> None:
    snippet, highlights = make_snippet("The rho pump.", [(4, 7)])

    assert snippet == "The rho pump."
    assert [snippet[h.start : h.end] for h in highlights] == ["rho"]


def test_make_snippet_cuts_at_white_space() -> None:
    text = "alpha " * 30 + "target " + "omega " * 80
    start = text.index("target")

    snippet, highlights = make_snippet(text, [(start, start + 6)])

    assert snippet.startswith(ELLIPSIS + "alpha ")
    assert snippet.endswith("omega" + ELLIPSIS)
    assert len(snippet) <= SNIPPET_MAX_LENGTH + 2
    assert [snippet[h.start : h.end] for h in highlights] == ["target"]


def test_make_snippet_merges_overlapping_spans_and_drops_far_ones() -> None:
    text = "sigma tau " + "filler " * 100 + "upsilon"
    far = text.index("upsilon")

    snippet, highlights = make_snippet(text, [(0, 5), (2, 9), (far, far + 7)])

    assert [snippet[h.start : h.end] for h in highlights] == ["sigma tau"]


def test_make_snippet_with_a_very_long_word() -> None:
    text = "x " + "y" * 500

    snippet, highlights = make_snippet(text, [(2, 502)])

    assert snippet == "…" + "y" * SNIPPET_MAX_LENGTH + "…"
    assert [snippet[h.start : h.end] for h in highlights] == ["y" * SNIPPET_MAX_LENGTH]


def test_marked_spans_follow_the_original_text() -> None:
    original = "Die  Steuerung startet. Steuerungen laufen."
    marked = "Die \x01Steuerung\x02 startet. \x01Steuerungen\x02 laufen."

    spans = marked_spans(original, marked, "\x01", "\x02")

    assert [original[start:end] for start, end in spans] == ["Steuerung", "Steuerungen"]


def test_markers_in_the_text_do_not_break_highlights(version: DocumentVersion) -> None:
    add_sections(version, "Control \x01chi\x02 pump \x03  runs.")

    (hit,) = search("chi pump").hits

    assert highlighted(hit) == ["chi", "pump"]


# --- Interface and AI switch (E-59) ----------------------------------------


def test_get_search_backend_returns_the_postgres_backend() -> None:
    assert isinstance(get_search_backend(), PostgresSearchBackend)


def _plain_values(value: object) -> Iterator[object]:
    """Every value inside ``value``, dataclasses and lists unpacked."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        for item in dataclasses.fields(value):
            yield from _plain_values(getattr(value, item.name))
    elif isinstance(value, list):
        for item in value:
            yield from _plain_values(item)
    else:
        yield value


def test_result_holds_plain_data_only(version: DocumentVersion) -> None:
    add_sections(version, "The phi pump has the address 192.168.0.5.")

    result = get_search_backend().search(SearchRequest(query="phi 192.168.0.5"))

    assert result.hits
    for value in _plain_values(result):
        assert value is None or isinstance(value, (str, int, float, bool))


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail on any network connection from Python (the database driver is libpq in C)."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the search opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.mark.parametrize("ai_enabled", [False, True])
def test_keyword_search_works_with_and_without_ai(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    version: DocumentVersion,
    no_network: None,
    ai_enabled: bool,
) -> None:
    # "On" with the stand-in embedder (050); the section has no embedding.
    if ai_enabled:
        install(monkeypatch, settings, FakeEmbedder())
    (section,) = add_sections(version, "The psi pump at 192.168.0.5 is ready.")

    result = search("psi 192.168.0.5")

    assert [hit.section_id for hit in result.hits] == [section.pk]
    assert result.hits[0].match_kinds == [MatchKind.EXACT, MatchKind.KEYWORD]
    assert result.semantic_used is ai_enabled


def test_search_needs_three_queries(
    version: DocumentVersion, django_assert_num_queries: DjangoAssertNumQueries
) -> None:
    add_sections(version, *(f"The chi belt {index} runs." for index in range(10)))

    # Parse the query, search, find the highlights: independent of the hits.
    with django_assert_num_queries(3):
        assert len(search("chi belt").hits) == 10


def test_connection_is_usable_after_a_search(version: DocumentVersion) -> None:
    add_sections(version, "The omega pump.")
    search('"')
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)
