"""The search probes and the command ``evaluate_search`` (056).

All section texts are written for these tests; none comes from a
manufacturer's manual. The model interface is :class:`FakeEmbedder`; no test
talks to a real model service (E-59).
"""

import io
import itertools
import json
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pytest_django.fixtures import Settings

from tests.search.fake_embedder import FakeEmbedder, at_angle, embed
from tests.search.test_keyword_search import (
    add_sections,
    make_device,
    make_document,
    make_plant,
    sha256_of,
)
from twox.answers import embeddings
from twox.answers.embeddings import EmbeddingUnavailableError
from twox.assets.models import Device
from twox.files.models import DocumentVersion
from twox.ingest.models import Section
from twox.search.evaluation import (
    AI_DISABLED_NOTE,
    DEPTH,
    MODEL_FAILED_NOTE,
    ExpectedPlace,
    KindResult,
    Place,
    Probe,
    ProbeFormatError,
    ProbeStatus,
    Report,
    SearchKind,
    evaluate,
    judge,
    load_probes,
    summarise,
)
from twox.search.management.commands.evaluate_search import BYTE_ORDER_MARK, read_input

SHA_A = sha256_of("evaluation manual A")
SHA_B = sha256_of("evaluation manual B")
SHA_MISSING = sha256_of("evaluation manual not ingested")
QUERY = "10.0.0.7"

#: Own texts; the distinctive words must never appear in the output.
TEXT_PAGE_1 = "Zebrafinch lamp test: the lamp blinks during start."
TEXT_PAGE_2 = "Marmalade valve: close the valve before maintenance."
TEXT_PAGE_3 = "Reset the quokka controller at 10.0.0.7 after a stop."
TEXT_OTHER = "Pelican conveyor belt speed is set in the menu."
SECRET_WORDS = ("Zebrafinch", "Marmalade", "quokka", "Pelican", "lamp", "valve", "conveyor")


# --- Helpers ---------------------------------------------------------------


def place(sha256: str, page: int | None, device_key: str = "plc-01") -> Place:
    return Place(sha256=sha256, page_start=page, page_end=page, device_key=device_key)


def expected(*pages: int, sha256: str = SHA_A, device: str | None = None) -> ExpectedPlace:
    return ExpectedPlace(
        manifest_id="manual-a", sha256=sha256, pages=frozenset(pages), device=device
    )


def probe_json(*probes: dict[str, Any]) -> str:
    return json.dumps({"schema_version": 1, "probes": list(probes)}, ensure_ascii=False)


def probe_data(
    probe_id: str = "p1",
    query: str = QUERY,
    places: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if places is None:
        places = [{"manifest_id": "manual-a", "sha256": SHA_A, "pages": [2, 3]}]
    return {"id": probe_id, "query": query, "expected": list(places)}


def run_command(text: str, *args: str) -> str:
    out = io.StringIO()
    call_command("evaluate_search", *args, stdin=io.StringIO(text), stdout=out)
    return out.getvalue()


def ticking_clock(step: float = 0.01) -> Callable[[], float]:
    """A clock that moves ``step`` seconds with every reading."""
    ticks: Iterator[int] = itertools.count()
    return lambda: next(ticks) * step


def kind_result(report: Report, probe_id: str, kind: SearchKind) -> KindResult:
    (probe,) = [probe for probe in report.probes if probe.probe_id == probe_id]
    (result,) = [result for result in probe.kinds if result.kind is kind]
    return result


@pytest.fixture
def device() -> Device:
    return make_device(make_plant(), "plc-01")


@pytest.fixture
def manual(device: Device) -> list[Section]:
    """Manual A with one section on each of the pages 1 to 3, and manual B."""
    version_a = make_document(device, title="Manual A", sha256=SHA_A)
    sections = [
        add_sections(version_a, text, page=page)[0]
        for page, text in ((1, TEXT_PAGE_1), (2, TEXT_PAGE_2), (3, TEXT_PAGE_3))
    ]
    version_b = make_document(device, title="Manual B", sha256=SHA_B)
    sections += add_sections(version_b, TEXT_OTHER, page=1)
    return sections


@pytest.fixture
def embedded_manual(manual: list[Section], fake_embedder: FakeEmbedder) -> list[Section]:
    """Vector order: manual B, then pages 1, 2, 3 of manual A."""
    page_1, page_2, page_3, other = manual
    embed(other, at_angle(5))
    embed(page_1, at_angle(10))
    embed(page_2, at_angle(20))
    embed(page_3, at_angle(30))
    return manual


# --- Rank, Recall and MRR, computed by hand ----------------------------------


def test_judge_finds_rank_counts_and_reciprocal_rank() -> None:
    entries = [
        [place(SHA_B, 3)],  # 1: other file
        [place(SHA_A, 5)],  # 2: other page
        [place(SHA_A, 3)],  # 3: correct
        [place(SHA_A, None)],  # 4: no page
        [place(SHA_B, 9), place(SHA_A, 2)],  # 5: correct through its second place
        [place(SHA_A, 1)],  # 6
        [place(SHA_A, 3)],  # 7: correct
        [place(SHA_A, 8)],  # 8
        [place(SHA_A, 8)],  # 9
        [place(SHA_A, 8)],  # 10
        [place(SHA_A, 2)],  # 11: correct, after the first 10
    ]

    result = judge(SearchKind.KEYWORD, entries, [expected(2, 3)], seconds=0.5)

    assert result.measured is True
    assert result.first_rank == 3
    assert result.correct_in_top_5 == 2
    assert result.correct_in_top_10 == 3
    assert result.reciprocal_rank == pytest.approx(1 / 3)
    assert result.first_manifest_id == "manual-a"
    assert result.first_pages == "3"
    assert result.seconds == 0.5


def test_judge_page_ranges_and_devices() -> None:
    spanning = Place(sha256=SHA_A, page_start=4, page_end=6, device_key="plc-01")

    assert judge(SearchKind.VECTOR, [[spanning]], [expected(5)], 0).first_rank == 1
    assert judge(SearchKind.VECTOR, [[spanning]], [expected(5)], 0).first_pages == "4-6"
    assert judge(SearchKind.VECTOR, [[spanning]], [expected(7)], 0).first_rank is None
    # The expected device must be one of the places.
    assert (
        judge(SearchKind.VECTOR, [[spanning]], [expected(5, device="plc-02")], 0).first_rank is None
    )
    assert judge(SearchKind.VECTOR, [[spanning]], [expected(5, device="plc-01")], 0).first_rank == 1


def test_judge_without_correct_entry() -> None:
    result = judge(SearchKind.COMBINED, [[place(SHA_B, 2)]], [expected(2)], 0.1)

    assert (result.first_rank, result.reciprocal_rank) == (None, 0.0)
    assert (result.correct_in_top_5, result.correct_in_top_10) == (0, 0)
    assert result.first_manifest_id is None


def test_judge_looks_at_the_first_entries_only() -> None:
    entries = [[place(SHA_B, 1)]] * DEPTH + [[place(SHA_A, 2)]]

    assert judge(SearchKind.KEYWORD, entries, [expected(2)], 0).first_rank is None


def test_summary_recall_and_mrr_by_hand() -> None:
    def measured(rank: int | None, seconds: float) -> KindResult:
        return KindResult(
            kind=SearchKind.KEYWORD,
            measured=True,
            first_rank=rank,
            reciprocal_rank=0.0 if rank is None else 1 / rank,
            seconds=seconds,
        )

    results = [
        measured(1, 0.1),
        measured(7, 0.2),
        measured(None, 0.3),
        KindResult(kind=SearchKind.KEYWORD, measured=False, note=AI_DISABLED_NOTE),
        KindResult(kind=SearchKind.VECTOR, measured=True, first_rank=1, reciprocal_rank=1.0),
    ]

    summary = summarise(SearchKind.KEYWORD, results)

    assert summary.measured == 3
    assert summary.not_measured == 1
    # Rank 1 within 5; ranks 1 and 7 within 10; of three measured probes.
    assert summary.recall_at_5 == pytest.approx(1 / 3)
    assert summary.recall_at_10 == pytest.approx(2 / 3)
    # (1/1 + 1/7 + 0) / 3
    assert summary.mrr == pytest.approx(8 / 21)
    assert summary.total_seconds == pytest.approx(0.6)
    assert summary.mean_seconds == pytest.approx(0.2)


def test_summary_without_measured_probes() -> None:
    summary = summarise(SearchKind.VECTOR, [])

    assert (summary.recall_at_5, summary.recall_at_10, summary.mrr) == (None, None, None)
    assert summary.mean_seconds is None


# --- Against the database ----------------------------------------------------


@pytest.mark.django_db
def test_ai_off_measures_the_keyword_search_only(
    manual: list[Section], monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_model() -> None:
        raise AssertionError("the model service must not be asked")

    monkeypatch.setattr(embeddings, "get_embedder", no_model)

    report = evaluate(load_probes(probe_json(probe_data())), clock=ticking_clock())

    assert report.ai_enabled is False
    assert report.model is None
    keyword = kind_result(report, "p1", SearchKind.KEYWORD)
    # Only page 3 holds the address.
    assert (keyword.first_rank, keyword.correct_in_top_5, keyword.correct_in_top_10) == (1, 1, 1)
    assert keyword.first_pages == "3"
    assert keyword.seconds == pytest.approx(0.01)
    for kind in (SearchKind.VECTOR, SearchKind.COMBINED):
        result = kind_result(report, "p1", kind)
        assert (result.measured, result.note) == (False, AI_DISABLED_NOTE)
    vector_summary = report.summaries[1]
    assert (vector_summary.kind, vector_summary.measured) == (SearchKind.VECTOR, 0)


@pytest.mark.django_db
def test_ai_on_measures_all_three_lists(
    embedded_manual: list[Section], fake_embedder: FakeEmbedder
) -> None:
    report = evaluate(load_probes(probe_json(probe_data())), clock=ticking_clock())

    assert report.ai_enabled is True
    assert report.model == "fake-embed"
    # Keyword: page 3 only.
    keyword = kind_result(report, "p1", SearchKind.KEYWORD)
    assert (keyword.first_rank, keyword.correct_in_top_5) == (1, 1)
    # Vector: manual B, page 1, page 2 (correct), page 3 (correct).
    vector = kind_result(report, "p1", SearchKind.VECTOR)
    assert (vector.first_rank, vector.correct_in_top_5, vector.correct_in_top_10) == (3, 2, 2)
    assert vector.reciprocal_rank == pytest.approx(1 / 3)
    assert vector.first_pages == "2"
    # Combined: the exact hit (page 3) first, then by vector rank: B, page 1, page 2.
    combined = kind_result(report, "p1", SearchKind.COMBINED)
    assert (combined.first_rank, combined.correct_in_top_5) == (1, 2)
    assert combined.first_pages == "3"
    # The keyword list does not ask the model; vector and combined ask once each.
    assert fake_embedder.calls == [QUERY, QUERY]
    summaries = {summary.kind: summary for summary in report.summaries}
    assert summaries[SearchKind.VECTOR].mrr == pytest.approx(1 / 3)
    assert summaries[SearchKind.COMBINED].recall_at_5 == 1.0


@pytest.mark.django_db
def test_model_failure_leaves_vector_and_combined_unmeasured(
    embedded_manual: list[Section], fake_embedder: FakeEmbedder
) -> None:
    fake_embedder.error = EmbeddingUnavailableError("model service not reachable")

    report = evaluate(load_probes(probe_json(probe_data())))

    assert kind_result(report, "p1", SearchKind.KEYWORD).first_rank == 1
    for kind in (SearchKind.VECTOR, SearchKind.COMBINED):
        result = kind_result(report, "p1", kind)
        assert (result.measured, result.note) == (False, MODEL_FAILED_NOTE)


@pytest.mark.django_db
def test_probe_without_ingested_file_is_not_ingested(
    manual: list[Section], fake_embedder: FakeEmbedder
) -> None:
    missing = probe_data(
        "missing", places=[{"manifest_id": "manual-x", "sha256": SHA_MISSING, "pages": [1]}]
    )
    partly = probe_data(
        "partly",
        places=[
            {"manifest_id": "manual-x", "sha256": SHA_MISSING, "pages": [1]},
            {"manifest_id": "manual-a", "sha256": SHA_A, "pages": [3]},
        ],
    )

    report = evaluate(load_probes(probe_json(missing, partly)))

    (not_ingested, measured) = report.probes
    assert not_ingested.status is ProbeStatus.NOT_INGESTED
    assert not_ingested.not_ingested == ["manual-x"]
    assert not_ingested.kinds == []
    assert measured.status is ProbeStatus.MEASURED
    assert measured.not_ingested == ["manual-x"]
    assert kind_result(report, "partly", SearchKind.KEYWORD).first_rank == 1
    assert report.not_ingested_count == 1
    # A probe that is not ingested is neither searched nor counted against the search.
    assert fake_embedder.calls == [QUERY, QUERY]
    assert report.summaries[0].measured == 1


@pytest.mark.django_db
def test_file_without_sections_is_not_ingested(device: Device) -> None:
    make_document(device, sha256=SHA_A)

    report = evaluate(load_probes(probe_json(probe_data())))

    assert report.probes[0].status is ProbeStatus.NOT_INGESTED
    assert DocumentVersion.objects.filter(sha256=SHA_A).exists()


# --- The command ---------------------------------------------------------------


@pytest.mark.django_db
def test_command_on_an_empty_database_reports_not_ingested() -> None:
    output = run_command(probe_json(probe_data("p1"), probe_data("p2")))

    assert "p1" in output
    assert output.count("not ingested") >= 2
    assert "Not ingested: 2 of 2 probes" in output
    assert "AI features are not enabled" in output


@pytest.mark.django_db
def test_command_table_names_model_and_section_size(
    embedded_manual: list[Section], settings: Settings
) -> None:
    settings.TWOX_SECTION_MAX_CHARS = 1234

    output = run_command(probe_json(probe_data()))

    assert "embedding model fake-embed" in output
    assert "TWOX_SECTION_MAX_CHARS 1234" in output
    assert "Recall@5" in output
    assert "MRR" in output
    assert "manual-a p. 3" in output


@pytest.mark.django_db
def test_command_json(embedded_manual: list[Section]) -> None:
    data = json.loads(run_command(probe_json(probe_data()), "--json"))

    assert data["ai_enabled"] is True
    assert data["model"] == "fake-embed"
    assert data["not_ingested_count"] == 0
    kinds = {kind["kind"]: kind for kind in data["probes"][0]["kinds"]}
    assert kinds["vector"]["first_rank"] == 3
    assert [summary["kind"] for summary in data["summaries"]] == ["keyword", "vector", "combined"]


@pytest.mark.django_db
@pytest.mark.parametrize("as_json", [False, True])
def test_output_holds_no_section_text(embedded_manual: list[Section], as_json: bool) -> None:
    probes = probe_json(probe_data(), probe_data("p2", query="lamp valve conveyor"))

    output = run_command(probes, *(["--json"] if as_json else []))

    for section in embedded_manual:
        assert section.text not in output
    for word in SECRET_WORDS:
        assert word.lower() not in output.lower()
    # Not even the queries.
    assert QUERY not in output


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "the input is empty"),
        ("{not json", "not valid JSON (line 1, column 2"),
        ("[]", "probe list: expected an object"),
        ('{"schema_version": 2, "probes": []}', "schema_version: expected 1"),
        ('{"schema_version": 1, "probes": []}', "probes: expected a non-empty list"),
        (probe_json({"id": "p", "expected": []}), "probes[0].query: expected non-empty text"),
        (probe_json(probe_data(places=[])), "probes[0].expected: expected a non-empty list"),
        (
            probe_json(probe_data(places=[{"manifest_id": "m", "sha256": "abc", "pages": [1]}])),
            "probes[0].expected[0].sha256: expected 64 lower-case hexadecimal characters",
        ),
        (
            probe_json(probe_data(places=[{"manifest_id": "m", "sha256": SHA_A, "pages": [0]}])),
            "probes[0].expected[0].pages[0]: expected a page number from 1",
        ),
        (
            probe_json(probe_data(places=[{"manifest_id": "m", "sha256": SHA_A, "pages": []}])),
            "probes[0].expected[0].pages: expected a non-empty list",
        ),
        (
            probe_json(probe_data(), {**probe_data(), "colour": "red"}),
            "probes[1]: unknown key(s): colour",
        ),
        (probe_json(probe_data(), probe_data()), "the id 'p1' occurs twice"),
    ],
)
def test_invalid_probe_list_gives_a_clear_message(text: str, message: str) -> None:
    with pytest.raises(ProbeFormatError, match=None) as raised:
        load_probes(text)
    assert message in str(raised.value)

    with pytest.raises(CommandError) as command_error:
        run_command(text)
    assert str(command_error.value) == f"Invalid probe list: {raised.value}"


def test_probe_list_with_umlauts() -> None:
    (probe,) = load_probes(probe_json(probe_data(query="Größte Nutzlast")))

    assert probe == Probe(id="p1", query="Größte Nutzlast", expected=(expected(2, 3),))


def test_standard_input_is_read_as_utf8_bytes() -> None:
    text = probe_json(probe_data(query="Größte Nutzlast"))
    stream = io.TextIOWrapper(io.BytesIO(b"\xef\xbb\xbf" + text.encode()), encoding="latin-1")

    assert read_input(stream) == text


def test_standard_input_that_is_not_utf8_gives_a_clear_message() -> None:
    stream = io.TextIOWrapper(io.BytesIO("Größte".encode("latin-1")))

    with pytest.raises(CommandError, match="standard input is not UTF-8"):
        read_input(stream)


@pytest.mark.django_db
def test_command_drops_a_byte_order_mark() -> None:
    output = run_command(BYTE_ORDER_MARK + probe_json(probe_data(query="Größte Nutzlast")))

    assert "Not ingested: 1 of 1 probes" in output
