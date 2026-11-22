"""The search probes and the command ``evaluate_search`` (056).

All section texts are written for these tests; none comes from a
manufacturer's manual. The model interface is :class:`FakeEmbedder`; no test
talks to a real model service (E-59).
"""

import inspect
import io
import itertools
import json
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import pytest
from django.conf import settings as django_settings
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
from twox.search import evaluation
from twox.search.evaluation import (
    AI_DISABLED_NOTE,
    CONTROL_ENTRIES,
    DEPTH,
    MODEL_FAILED_NOTE,
    PROBE_LISTS,
    ExpectedPlace,
    KindResult,
    Place,
    PlaceRank,
    Probe,
    ProbeFormatError,
    ProbeStatus,
    Report,
    SearchKind,
    control_list,
    evaluate,
    format_json,
    format_table,
    judge,
    load_probes,
    matching_place,
    parse_cutoffs,
    summarise,
)
from twox.search.interface import SearchRequest, SearchResult, get_search_backend
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
    monkeypatch.setattr(embeddings, "get_query_embedder", no_model)

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


class RecordingBackend:
    """The real search backend that also records every request and the AI switch."""

    def __init__(self) -> None:
        self.requests: list[tuple[SearchRequest, bool]] = []

    def search(self, request: SearchRequest) -> SearchResult:
        self.requests.append((request, bool(django_settings.TWOX_AI_ENABLED)))
        return get_search_backend().search(request)


@pytest.mark.django_db
def test_keyword_list_asks_for_the_keyword_search_without_touching_the_settings(
    embedded_manual: list[Section], fake_embedder: FakeEmbedder
) -> None:
    backend = RecordingBackend()

    evaluate(load_probes(probe_json(probe_data())), backend=backend)

    # Keyword list, then combined; the AI switch stays on for both (no
    # override_settings, which is not thread-safe).
    assert [(request.keyword_only, ai) for request, ai in backend.requests] == [
        (True, True),
        (False, True),
    ]
    assert {request.query for request, _ in backend.requests} == {QUERY}
    assert "override_settings" not in inspect.getsource(evaluation)


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


# --- Work order 120: output without cut-offs as before ----------------------------


def golden_probes() -> str:
    """Probes of every kind the output of 056 knows, with two editions (E-61)."""
    return probe_json(
        probe_data("p1"),
        {
            **probe_data(
                "two-editions",
                query="Marmalade valve maintenance",
                places=[
                    {"manifest_id": "manual-a", "sha256": SHA_A, "pages": [1, 2]},
                    {"manifest_id": "manual-b", "sha256": SHA_B, "pages": [1, 2]},
                ],
            ),
            "basis": {"question": 3, "other_language_edition": {"manual-b": "manual-a"}},
        },
        probe_data(
            "missing", places=[{"manifest_id": "manual-x", "sha256": SHA_MISSING, "pages": [1]}]
        ),
        probe_data(
            "partly",
            places=[
                {"manifest_id": "manual-x", "sha256": SHA_MISSING, "pages": [1]},
                {"manifest_id": "manual-a", "sha256": SHA_A, "pages": [3]},
            ],
        ),
    )


#: The text output of the code before work order 120 for :func:`golden_probes`.
GOLDEN_TEXT_AI_ON = """\
Search probes: 4; AI features on; embedding model fake-embed; TWOX_SECTION_MAX_CHARS 2000; list depth 50

probe         kind      status               rank  top 5  top 10  RR     ms  first correct place
p1            keyword   measured             1     1      1       1.000  10  manual-a p. 3
p1            vector    measured             3     2      2       0.333  10  manual-a p. 2
p1            combined  measured             1     2      2       1.000  10  manual-a p. 3
two-editions  keyword   measured             1     1      1       1.000  10  manual-a p. 2
two-editions  vector    measured             1     3      3       1.000  10  manual-b p. 1
two-editions  combined  measured             1     3      3       1.000  10  manual-a p. 2
missing       -         not ingested         -     -      -       -      -   manual-x
partly        keyword   measured             1     1      1       1.000  10  manual-a p. 3
partly        vector    measured             4     1      1       0.250  10  manual-a p. 3
partly        combined  measured             1     1      1       1.000  10  manual-a p. 3
partly        -         partly not ingested  -     -      -       -      -   manual-x

kind      measured  not measured  Recall@5  Recall@10  MRR    total ms  mean ms
keyword   3         0             1.000     1.000      1.000  30        10
vector    3         0             1.000     1.000      0.528  30        10
combined  3         0             1.000     1.000      1.000  30        10

Not ingested: 1 of 4 probes
"""  # noqa: E501

GOLDEN_TEXT_AI_OFF = """\
Search probes: 4; AI features off; embedding model -; TWOX_SECTION_MAX_CHARS 2000; list depth 50
AI features are not enabled (TWOX_AI_ENABLED is false): only the keyword search is measured; vector and combined are not measured.

probe         kind      status                                 rank  top 5  top 10  RR     ms  first correct place
p1            keyword   measured                               1     1      1       1.000  10  manual-a p. 3
p1            vector    not measured: AI features not enabled  -     -      -       -      -
p1            combined  not measured: AI features not enabled  -     -      -       -      -
two-editions  keyword   measured                               1     1      1       1.000  10  manual-a p. 2
two-editions  vector    not measured: AI features not enabled  -     -      -       -      -
two-editions  combined  not measured: AI features not enabled  -     -      -       -      -
missing       -         not ingested                           -     -      -       -      -   manual-x
partly        keyword   measured                               1     1      1       1.000  10  manual-a p. 3
partly        vector    not measured: AI features not enabled  -     -      -       -      -
partly        combined  not measured: AI features not enabled  -     -      -       -      -
partly        -         partly not ingested                    -     -      -       -      -   manual-x

kind      measured  not measured  Recall@5  Recall@10  MRR    total ms  mean ms
keyword   3         0             1.000     1.000      1.000  30        10
vector    0         3             -         -          -      0         -
combined  0         3             -         -          -      0         -

Not ingested: 1 of 4 probes
"""  # noqa: E501

#: Keys of the JSON output before work order 120, in their order.
GOLDEN_REPORT_KEYS = [
    "ai_enabled",
    "model",
    "section_max_chars",
    "depth",
    "probes",
    "summaries",
    "not_ingested_count",
]
GOLDEN_PROBE_KEYS = ["probe_id", "status", "not_ingested", "kinds"]
GOLDEN_KIND_KEYS = [
    "kind",
    "measured",
    "note",
    "first_rank",
    "correct_in_top_5",
    "correct_in_top_10",
    "reciprocal_rank",
    "first_manifest_id",
    "first_pages",
    "seconds",
]
GOLDEN_SUMMARY_KEYS = [
    "kind",
    "measured",
    "not_measured",
    "recall_at_5",
    "recall_at_10",
    "mrr",
    "total_seconds",
    "mean_seconds",
]


def golden_kind(
    kind: str, rank: int, top_5: int, top_10: int, manifest_id: str, pages: str
) -> dict[str, Any]:
    return {
        "kind": kind,
        "measured": True,
        "note": None,
        "first_rank": rank,
        "correct_in_top_5": top_5,
        "correct_in_top_10": top_10,
        "reciprocal_rank": pytest.approx(1 / rank),
        "first_manifest_id": manifest_id,
        "first_pages": pages,
        "seconds": pytest.approx(0.01),
    }


def golden_summary(kind: str, mrr: float) -> dict[str, Any]:
    return {
        "kind": kind,
        "measured": 3,
        "not_measured": 0,
        "recall_at_5": 1.0,
        "recall_at_10": 1.0,
        "mrr": pytest.approx(mrr),
        "total_seconds": pytest.approx(0.03),
        "mean_seconds": pytest.approx(0.01),
    }


#: The JSON output of the code before work order 120 for :func:`golden_probes`, AI on.
GOLDEN_JSON_AI_ON: dict[str, Any] = {
    "ai_enabled": True,
    "model": "fake-embed",
    "section_max_chars": 2000,
    "depth": 50,
    "probes": [
        {
            "probe_id": "p1",
            "status": "measured",
            "not_ingested": [],
            "kinds": [
                golden_kind("keyword", 1, 1, 1, "manual-a", "3"),
                golden_kind("vector", 3, 2, 2, "manual-a", "2"),
                golden_kind("combined", 1, 2, 2, "manual-a", "3"),
            ],
        },
        {
            "probe_id": "two-editions",
            "status": "measured",
            "not_ingested": [],
            "kinds": [
                golden_kind("keyword", 1, 1, 1, "manual-a", "2"),
                golden_kind("vector", 1, 3, 3, "manual-b", "1"),
                golden_kind("combined", 1, 3, 3, "manual-a", "2"),
            ],
        },
        {
            "probe_id": "missing",
            "status": "not_ingested",
            "not_ingested": ["manual-x"],
            "kinds": [],
        },
        {
            "probe_id": "partly",
            "status": "measured",
            "not_ingested": ["manual-x"],
            "kinds": [
                golden_kind("keyword", 1, 1, 1, "manual-a", "3"),
                golden_kind("vector", 4, 1, 1, "manual-a", "3"),
                golden_kind("combined", 1, 1, 1, "manual-a", "3"),
            ],
        },
    ],
    "summaries": [
        golden_summary("keyword", 1.0),
        golden_summary("vector", (1 / 3 + 1 + 1 / 4) / 3),
        golden_summary("combined", 1.0),
    ],
    "not_ingested_count": 1,
}


def assert_golden_keys(data: dict[str, Any]) -> None:
    assert list(data) == GOLDEN_REPORT_KEYS
    for probe in data["probes"]:
        assert list(probe) == GOLDEN_PROBE_KEYS
        for kind in probe["kinds"]:
            assert list(kind) == GOLDEN_KIND_KEYS
    for summary in data["summaries"]:
        assert list(summary) == GOLDEN_SUMMARY_KEYS


@pytest.mark.django_db
def test_output_without_cutoffs_is_unchanged_with_ai(
    embedded_manual: list[Section], fake_embedder: FakeEmbedder
) -> None:
    report = evaluate(load_probes(golden_probes()), clock=ticking_clock())

    assert format_table(report) == GOLDEN_TEXT_AI_ON
    data = json.loads(format_json(report))
    assert_golden_keys(data)
    assert data == GOLDEN_JSON_AI_ON


@pytest.mark.django_db
def test_output_without_cutoffs_is_unchanged_without_ai(manual: list[Section]) -> None:
    report = evaluate(load_probes(golden_probes()), clock=ticking_clock())

    assert format_table(report) == GOLDEN_TEXT_AI_OFF
    assert_golden_keys(json.loads(format_json(report)))


@pytest.mark.django_db
def test_probe_list_m2_by_name_is_the_list_on_standard_input() -> None:
    text = (PROBE_LISTS / "m2.json").read_text(encoding="utf-8")

    assert run_command("", "--probes", "m2") == run_command(text)
    assert run_command(text).endswith("Not ingested: 7 of 7 probes\n")


# --- Work order 120: Recall@k at chosen cut-offs ----------------------------------


def test_correct_entries_at_chosen_cutoffs_by_hand() -> None:
    entries = [[place(SHA_A, 3 if rank in (3, 7, 9, 12, 15) else 9)] for rank in range(1, 20)]

    result = judge(SearchKind.VECTOR, entries, [expected(3)], 0, cutoffs=(5, 8, 10, 12))

    # Correct at ranks 3, 7, 9, 12 and 15.
    assert result.correct_in_top == {"5": 1, "8": 2, "10": 3, "12": 4}
    # The fields of 056 stay at 5 and 10.
    assert (result.correct_in_top_5, result.correct_in_top_10) == (1, 3)


def test_recall_at_chosen_cutoffs_and_mrr_by_hand() -> None:
    def measured(rank: int | None) -> KindResult:
        return KindResult(
            kind=SearchKind.COMBINED,
            measured=True,
            first_rank=rank,
            reciprocal_rank=0.0 if rank is None else 1 / rank,
        )

    results = [measured(1), measured(6), measured(9), measured(12), measured(None)]

    summary = summarise(SearchKind.COMBINED, results, cutoffs=(5, 8, 10, 12))

    # Of five probes: rank 1 within 5; 1 and 6 within 8; 1, 6, 9 within 10; four within 12.
    assert summary.recall_at == {
        "5": pytest.approx(1 / 5),
        "8": pytest.approx(2 / 5),
        "10": pytest.approx(3 / 5),
        "12": pytest.approx(4 / 5),
    }
    # (1 + 1/6 + 1/9 + 1/12 + 0) / 5 = 49/180
    assert summary.mrr == pytest.approx(49 / 180)
    assert summary.recall_at_5 == pytest.approx(0.2)
    assert summary.recall_at_10 == pytest.approx(0.6)


@pytest.mark.parametrize(
    ("text", "cutoffs"),
    [("5,8,10,12", (5, 8, 10, 12)), ("1", (1,)), (f"3, {DEPTH}", (3, DEPTH))],
)
def test_valid_cutoffs(text: str, cutoffs: tuple[int, ...]) -> None:
    assert parse_cutoffs(text) == cutoffs


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("0,5", "0 is not between 1 and 50"),
        ("5,51", "51 is not between 1 and 50"),
        ("5,8,8", "8 occurs twice"),
        ("10,5", "5 comes after 10; expected ascending numbers"),
        ("5,eight", "'eight' is not a whole number"),
        ("5,-3", "'-3' is not a whole number"),
        ("", "'' is not a whole number"),
    ],
)
def test_invalid_cutoffs_end_with_a_message_and_exit_code_1(text: str, message: str) -> None:
    with pytest.raises(CommandError) as raised:
        run_command(probe_json(probe_data()), "--cutoffs", text)

    assert str(raised.value) == f"Invalid --cutoffs: {message}"
    assert raised.value.returncode == 1


@pytest.mark.django_db
def test_command_with_cutoffs_prints_every_cutoff(
    embedded_manual: list[Section], fake_embedder: FakeEmbedder
) -> None:
    output = run_command(probe_json(probe_data()), "--cutoffs", "5,8,10,12")

    for cutoff in (5, 8, 10, 12):
        assert f"top {cutoff}" in output
        assert f"Recall@{cutoff}" in output
    data = json.loads(run_command(probe_json(probe_data()), "--cutoffs", "5,8,10,12", "--json"))
    assert data["cutoffs"] == [5, 8, 10, 12]
    combined = data["summaries"][2]
    assert combined["recall_at"] == {"5": 1.0, "8": 1.0, "10": 1.0, "12": 1.0}
    # The fields of 056 are still there.
    assert combined["recall_at_5"] == 1.0
    vector = {kind["kind"]: kind for kind in data["probes"][0]["kinds"]}["vector"]
    assert vector["correct_in_top"] == {"5": 2, "8": 2, "10": 2, "12": 2}


# --- Work order 120: first rank per expected place --------------------------------


def test_first_rank_per_expected_place_counts_the_other_edition() -> None:
    places = [
        expected(2, 3),
        ExpectedPlace(manifest_id="manual-b", sha256=SHA_B, pages=frozenset({2, 3})),
    ]
    entries = [
        [place(SHA_A, 9)],  # 1
        [place(SHA_B, 3)],  # 2: page 3 in the other edition
        [place(SHA_A, 9)],  # 3
        [place(SHA_A, 2)],  # 4: page 2
        [place(SHA_A, 3)],  # 5: page 3 again
    ]

    result = judge(SearchKind.COMBINED, entries, places, 0, editions={"manual-b": "manual-a"})

    assert result.first_rank == 2
    assert result.place_ranks == [
        PlaceRank(manifest_id="manual-a", page=2, heading_path=None, first_rank=4),
        PlaceRank(manifest_id="manual-a", page=3, heading_path=None, first_rank=2),
    ]
    # Without the mapping each edition is a place of its own.
    alone = judge(SearchKind.COMBINED, entries, places, 0)
    assert [(rank.manifest_id, rank.page, rank.first_rank) for rank in alone.place_ranks] == [
        ("manual-a", 2, 4),
        ("manual-a", 3, 5),
        ("manual-b", 2, None),
        ("manual-b", 3, 2),
    ]


def test_an_entry_over_several_pages_stands_for_each_of_them() -> None:
    spanning = Place(sha256=SHA_A, page_start=2, page_end=4, device_key="plc-01")

    result = judge(SearchKind.KEYWORD, [[place(SHA_B, 1)], [spanning]], [expected(3, 4, 7)], 0)

    assert [(rank.page, rank.first_rank) for rank in result.place_ranks] == [
        (3, 2),
        (4, 2),
        (7, None),
    ]


@pytest.mark.django_db
def test_ranks_per_place_of_a_probe_with_two_pages(
    embedded_manual: list[Section], fake_embedder: FakeEmbedder
) -> None:
    probe = {
        **probe_data(
            "two-pages", places=[{"manifest_id": "manual-a", "sha256": SHA_A, "pages": [1, 3]}]
        ),
        "basis": {"question": 7},
    }

    report = evaluate(load_probes(probe_json(probe)), cutoffs=(5, 8, 10, 12))

    # Vector order: manual B, page 1, page 2, page 3.
    vector = kind_result(report, "two-pages", SearchKind.VECTOR)
    assert vector.first_rank == 2
    assert [(rank.page, rank.first_rank) for rank in vector.place_ranks] == [(1, 2), (3, 4)]
    text = format_table(report)
    assert "First rank per expected place" in text
    assert "manual-a p. 3" in text
    data = json.loads(format_json(report))
    ranks = data["probes"][0]["kinds"][1]["place_ranks"]
    assert ranks == [
        {"manifest_id": "manual-a", "page": 1, "heading_path": None, "first_rank": 2},
        {"manifest_id": "manual-a", "page": 3, "heading_path": None, "first_rank": 4},
    ]


# --- Work order 120: places in Markdown, by heading path (E-55) --------------------

SHA_NOTES = sha256_of("evaluation notes in markdown")
TEXT_NOTES = "Wombat module publishes its state every second."


def heading_place(*headings: str, sha256: str = SHA_NOTES) -> Place:
    return Place(
        sha256=sha256,
        page_start=None,
        page_end=None,
        device_key="plc-01",
        heading_path=tuple(headings),
    )


def expected_heading(*headings: str, sha256: str = SHA_NOTES) -> ExpectedPlace:
    return ExpectedPlace(
        manifest_id="notes-repo",
        sha256=sha256,
        pages=frozenset(),
        heading_path=tuple(headings),
        path="docs/wombat.md",
    )


def test_heading_path_matches_as_a_prefix() -> None:
    section = heading_place("Modules", "Wombat  module", "Topics")
    wanted_paths = [
        ("Modules",),
        ("modules", "Wombat module"),
        ("Modules", "WOMBAT module", "topics"),
    ]

    for wanted in wanted_paths:
        assert matching_place(section, [expected_heading(*wanted)]) is not None, wanted
    # Another path, a longer path, another file.
    longer = expected_heading("Modules", "Wombat module", "Topics", "Retained")
    assert matching_place(section, [expected_heading("Modules", "Koala module")]) is None
    assert matching_place(section, [longer]) is None
    assert matching_place(section, [expected_heading("Modules", sha256=SHA_A)]) is None
    # A place by pages never matches a section without pages.
    assert matching_place(section, [expected(1, sha256=SHA_NOTES)]) is None


def heading_data(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "manifest_id": "notes-repo",
        "sha256": SHA_NOTES,
        "heading_path": ["Modules"],
        "path": "docs/wombat.md",
    }
    data.update(changes)
    return {key: value for key, value in data.items() if value is not None}


def test_heading_path_in_the_probe_list() -> None:
    place_data = heading_data(heading_path=["Modules", "Wombat module"], path="docs/m/wombat.md")

    (probe,) = load_probes(probe_json(probe_data(places=[place_data])))

    (found,) = probe.expected
    assert found.heading_path == ("Modules", "Wombat module")
    assert found.path == "docs/m/wombat.md"
    assert found.pages == frozenset()


@pytest.mark.parametrize(
    ("place_data", "message"),
    [
        (heading_data(pages=[1]), "expected[0]: expected exactly one of pages and heading_path"),
        (
            {"manifest_id": "m", "sha256": SHA_A},
            "expected[0]: expected exactly one of pages and heading_path",
        ),
        (heading_data(path=None), "expected[0].path: required with heading_path"),
        (
            {"manifest_id": "m", "sha256": SHA_A, "pages": [1], "path": "docs/a.md"},
            "expected[0].path: only with heading_path, not with pages",
        ),
        (
            heading_data(heading_path=["Modules", "x" * 121]),
            "expected[0].heading_path[1]: longer than 120 characters",
        ),
        (heading_data(heading_path=["h"] * 9), "expected[0].heading_path: at most 8 headings"),
        (heading_data(heading_path=[]), "expected[0].heading_path: expected a non-empty list"),
        (heading_data(heading_path=["Modules", " "]), "heading_path[1]: expected non-empty text"),
        (heading_data(path="docs/../secret.md"), "expected[0].path: expected a relative path"),
        (heading_data(path="/docs/wombat.md"), "expected[0].path: expected a relative path"),
        (heading_data(path="docs\\wombat.md"), "expected[0].path: expected a relative path"),
        (heading_data(path="d" * 201), "expected[0].path: longer than 200 characters"),
    ],
)
def test_invalid_heading_place(place_data: dict[str, Any], message: str) -> None:
    with pytest.raises(ProbeFormatError) as raised:
        load_probes(probe_json(probe_data(places=[place_data])))

    assert message in str(raised.value)


def test_a_heading_path_of_120_characters_and_8_levels_is_valid() -> None:
    headings = ["h"] * 7 + ["x" * 120]

    (probe,) = load_probes(probe_json(probe_data(places=[heading_data(heading_path=headings)])))

    assert probe.expected[0].heading_path == tuple(headings)


@pytest.mark.django_db
def test_markdown_place_found_by_heading_path(device: Device) -> None:
    notes = make_document(device, title="Notes", sha256=SHA_NOTES)
    add_sections(notes, TEXT_NOTES, headings=("Wombat module", "State"), page=None)
    found = heading_data(heading_path=["wombat module"])
    other = heading_data(heading_path=["Koala module"])
    probes = probe_json(
        probe_data("found", query="wombat", places=[found]),
        probe_data("other", query="wombat", places=[other]),
    )

    report = evaluate(load_probes(probes), cutoffs=(5, 10))

    keyword = kind_result(report, "found", SearchKind.KEYWORD)
    assert keyword.first_rank == 1
    assert keyword.first_pages is None
    assert keyword.place_ranks == [
        PlaceRank(manifest_id="notes-repo", page=None, heading_path=["wombat module"], first_rank=1)
    ]
    assert kind_result(report, "other", SearchKind.KEYWORD).first_rank is None


# --- Work order 120: control probe ------------------------------------------------

CONTROL_QUERY = "When was the milling station serviced last?"


def control_data(probe_id: str = "control-1", query: str = CONTROL_QUERY) -> dict[str, Any]:
    return {"id": probe_id, "query": query, "expected": [], "basis": {"question": 11}}


def test_control_probe_in_the_probe_list() -> None:
    (probe,) = load_probes(probe_json(control_data()))

    assert probe.is_control
    assert probe.expected == ()


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            {**control_data(), "expected": [{"manifest_id": "m", "sha256": SHA_A, "pages": [1]}]},
            "probes[0].expected: a control probe (id control-…) expects no place;"
            " expected an empty list",
        ),
        (
            control_data("p-11"),
            "probes[0].expected: expected a non-empty list of places (an empty list only for a"
            " control probe, whose id starts with 'control-')",
        ),
    ],
)
def test_only_a_control_probe_expects_no_place(data: dict[str, Any], message: str) -> None:
    with pytest.raises(ProbeFormatError) as raised:
        load_probes(probe_json(data))

    assert str(raised.value) == message


@pytest.mark.django_db
def test_control_probe_is_searched_but_not_judged(
    embedded_manual: list[Section], fake_embedder: FakeEmbedder
) -> None:
    page_1, page_2, page_3, other = embedded_manual

    report = evaluate(load_probes(probe_json(control_data(), probe_data())), cutoffs=(5, 10))

    control, measured = report.probes
    assert control.status is ProbeStatus.CONTROL
    assert control.kinds == []
    assert control.not_ingested == []
    assert [listed.kind for listed in control.controls] == list(SearchKind)
    vector = control.controls[1]
    assert vector.measured is True
    # Vector order: manual B, then pages 1, 2, 3 of manual A; identifiers only.
    assert [entry.rank for entry in vector.entries] == [1, 2, 3, 4]
    assert [entry.places[0].section_id for entry in vector.entries] == [
        other.pk,
        page_1.pk,
        page_2.pk,
        page_3.pk,
    ]
    first = vector.entries[1].places[0]
    assert (first.version_id, first.sha256, first.pages, first.device_key) == (
        page_1.document_version_id,
        SHA_A,
        "1",
        "plc-01",
    )
    # Recall and MRR count the measured probe only; the control probe is no failure.
    assert [summary.measured for summary in report.summaries] == [1, 1, 1]
    assert [summary.not_measured for summary in report.summaries] == [0, 0, 0]
    assert report.summaries[2].recall_at_5 == 1.0
    assert measured.status is ProbeStatus.MEASURED
    assert report.not_ingested_count == 0
    # The control query is embedded once for the vector and once for the combined list.
    assert fake_embedder.calls == [CONTROL_QUERY, CONTROL_QUERY, QUERY, QUERY]


@pytest.mark.django_db
@pytest.mark.parametrize("as_json", [False, True])
def test_control_probe_output_holds_identifiers_only(
    embedded_manual: list[Section], fake_embedder: FakeEmbedder, as_json: bool
) -> None:
    probes = probe_json(control_data(query="lamp valve conveyor quokka"), probe_data())

    output = run_command(probes, *(["--json"] if as_json else []))

    for section in embedded_manual:
        assert section.text not in output
    for word in SECRET_WORDS:
        assert word.lower() not in output.lower()
    assert "Manual A" not in output
    assert "Manual B" not in output
    if as_json:
        data = json.loads(output)
        control = data["probes"][0]
        assert control["status"] == "control"
        for listed in control["controls"]:
            assert set(listed) == {"kind", "measured", "note", "entries"}
            assert len(listed["entries"]) <= CONTROL_ENTRIES
            for entry in listed["entries"]:
                assert set(entry) == {"rank", "places"}
                for found in entry["places"]:
                    assert set(found) == {
                        "section_id",
                        "version_id",
                        "sha256",
                        "pages",
                        "device_key",
                    }
        # The vector list has all four sections.
        assert [entry["rank"] for entry in control["controls"][1]["entries"]] == [1, 2, 3, 4]
        # A probe that is no control probe has no list of entries.
        assert "controls" not in data["probes"][1]
    else:
        assert "control, not judged" in output
        assert "Control probes (not judged): first 10 entries, identifiers only:" in output
        assert SHA_A in output


def test_control_list_has_the_first_ten_entries_only() -> None:
    entries = [[place(SHA_A, rank)] for rank in range(1, 15)]

    listed = control_list(SearchKind.KEYWORD, entries)

    assert [entry.rank for entry in listed.entries] == list(range(1, CONTROL_ENTRIES + 1))
    assert listed.entries[-1].places[0].pages == "10"


@pytest.mark.django_db
def test_ai_off_control_probe_does_not_ask_the_model(
    manual: list[Section], monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_model() -> None:
        raise AssertionError("the model service must not be asked")

    monkeypatch.setattr(embeddings, "get_embedder", no_model)
    monkeypatch.setattr(embeddings, "get_query_embedder", no_model)

    report = evaluate(load_probes(probe_json(control_data(), probe_data())))
    output = run_command(probe_json(control_data(), probe_data()), "--cutoffs", "5,8")

    control = report.probes[0]
    keyword, vector, combined = control.controls
    assert keyword.measured is True
    assert (vector.measured, vector.note) == (False, AI_DISABLED_NOTE)
    assert (combined.measured, combined.note) == (False, AI_DISABLED_NOTE)
    assert "not measured: AI features not enabled" in output


@pytest.mark.django_db
def test_model_failure_leaves_the_control_lists_unmeasured(
    embedded_manual: list[Section], fake_embedder: FakeEmbedder
) -> None:
    fake_embedder.error = EmbeddingUnavailableError("model service not reachable")

    (control,) = evaluate(load_probes(probe_json(control_data()))).probes

    assert [(listed.measured, listed.note) for listed in control.controls[1:]] == [
        (False, MODEL_FAILED_NOTE),
        (False, MODEL_FAILED_NOTE),
    ]


# --- Work order 120: probe lists by name ------------------------------------------


@pytest.mark.django_db
def test_probe_list_m3_by_name() -> None:
    output = run_command("", "--probes", "m3", "--cutoffs", "5,8,10,12")

    assert output.startswith("Search probes: 13;")
    assert "control-11" in output
    assert "control, not judged" in output
    # The keyword list of the control probe is empty; the output says so.
    assert "no entries" in output
    # Nothing is ingested in the test database; the control probe is searched anyway.
    assert output.endswith("Not ingested: 12 of 13 probes\n")


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("M3", "Invalid --probes: 'M3' is not a probe list name"),
        ("../m2", "Invalid --probes: '../m2' is not a probe list name"),
        ("m2.json", "Invalid --probes: 'm2.json' is not a probe list name"),
        ("", "Invalid --probes: '' is not a probe list name"),
        ("m9", "Invalid --probes: there is no probe list 'm9' (known: m2, m3)"),
    ],
)
def test_invalid_probe_list_name(name: str, message: str) -> None:
    with pytest.raises(CommandError) as raised:
        run_command("", "--probes", name)

    assert str(raised.value).startswith(message)
    assert raised.value.returncode == 1
