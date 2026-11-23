"""Vector search in PostgreSQL and its fallback to the keyword search (050).

The model interface is always a stand-in (:mod:`tests.search.fake_embedder`
or the HTTP stand-in of 044); no test talks to a real model service. All
texts are written for these tests; none comes from a manufacturer's manual.
"""

import logging
import re
import socket
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from pytest_django.fixtures import Settings

from tests.answers.fake_ollama import LOCAL_MODEL, FakeOllama, fake_ollama, vector_for
from tests.search.fake_embedder import (
    FAKE_MODEL,
    FakeEmbedder,
    at_angle,
    cosine_distance,
    embed,
    unit,
)
from tests.search.test_keyword_search import (
    add_sections,
    add_version,
    make_device,
    make_document,
    make_plant,
    search,
    sha256_of,
)
from twox.answers import embeddings
from twox.answers.embeddings import (
    EmbeddingDimensionError,
    EmbeddingError,
    EmbeddingRejectedError,
    EmbeddingRemoteModelError,
    EmbeddingUnavailableError,
)
from twox.assets.models import Device, Plant
from twox.files.models import DocumentKind, DocumentVersion
from twox.ingest.models import EMBEDDING_DIMENSIONS
from twox.search.interface import MAX_LIMIT, MatchKind, SearchRequest, SemanticState
from twox.search.postgres import (
    HNSW_EF_SEARCH,
    HNSW_ITERATIVE_SCAN,
    VECTOR_CANDIDATES,
    _Queries,
    _scope_params,
    nearest_sections,
    vector_literal,
    vector_sql,
)

pytestmark = pytest.mark.django_db

#: A question that shares no word with the section that answers it.
QUESTION = "How do I change the lubricant?"
ANSWER = "Replace the oil of the gearbox every 500 hours."


@pytest.fixture
def plant() -> Plant:
    return make_plant()


@pytest.fixture
def device(plant: Plant) -> Device:
    return make_device(plant, "plc-01")


@pytest.fixture
def version(device: Device) -> DocumentVersion:
    return make_document(device)


def section_ids(
    query: str, device_ids: Sequence[int] = (), plant_ids: Sequence[int] = ()
) -> list[int]:
    result = search(query, device_ids=device_ids, plant_ids=plant_ids)
    return [hit.section_id for hit in result.hits]


# --- Found by meaning ---------------------------------------------------------


def test_question_without_common_words_is_found_by_vector_only(
    settings: Settings, version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    answer, unrelated = add_sections(version, ANSWER, "The lamp turns green when ready.")
    embed(answer, at_angle(15))
    embed(unrelated, at_angle(80))

    result = search(QUESTION)

    assert result.semantic_used is True
    assert [hit.section_id for hit in result.hits] == [answer.pk, unrelated.pk]
    assert result.hits[0].match_kinds == [MatchKind.SEMANTIC]
    # The snippet is the start of the text, without highlights.
    assert result.hits[0].snippet == ANSWER
    assert result.hits[0].highlights == []
    assert fake_embedder.calls == [QUESTION]

    # The keyword search alone does not find it.
    settings.TWOX_AI_ENABLED = False
    keyword_only = search(QUESTION)
    assert keyword_only.hits == []
    assert keyword_only.semantic_used is False


def test_question_naming_a_product_puts_the_best_meaning_first(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    # A question in plain words that names a product on the side. Before 063,
    # every section with "XR7" scored 1 and came before the answer. With the
    # exact list of 063, a section that names XR7 and is also among the nearest
    # was in two lists and still came first (test question 9 in the acceptance
    # run 060). Since 067 (E-61) the name counts only through the keyword and
    # the vector list. No keyword hit here (the keyword search needs every word).
    answer, near_naming, level = add_sections(
        version,
        "Zum Wechsel des Getriebeöls die Ablassschraube lösen und das alte Öl auffangen.",
        "Der XR7 wiegt 40 kg.",
        "Den Ölstand jeden Monat prüfen.",
    )
    naming = add_sections(
        version,
        "Den XR7 nur mit Schutzbrille bedienen.",
        "Das Typenschild des XR7 sitzt hinten.",
    )
    embed(answer, at_angle(10))
    embed(near_naming, at_angle(20))
    embed(level, at_angle(30))

    result = search("Wie tausche ich beim XR7 das Getriebeöl?")

    hits = result.hits
    assert result.semantic is SemanticState.USED
    # vector: answer 1 = 1/61, near_naming 2 = 1/62, level 3 = 1/63; the two
    # sections that only name XR7 are in no list: 0, last, still "exact".
    # With 063 the three sections naming XR7 tied for places 1 to 3 of the
    # exact list (rank 2 each): near_naming = 1/62 + 1/62 = 0.032258, before
    # the answer (0.016393).
    assert [hit.section_id for hit in hits] == [answer.pk, near_naming.pk, level.pk] + [
        s.pk for s in naming
    ]
    assert [hit.match_kinds for hit in hits] == [
        [MatchKind.SEMANTIC],
        [MatchKind.EXACT, MatchKind.SEMANTIC],
        [MatchKind.SEMANTIC],
        [MatchKind.EXACT],
        [MatchKind.EXACT],
    ]
    assert [hit.score for hit in hits] == pytest.approx([1 / 61, 1 / 62, 1 / 63, 0.0, 0.0])


def test_vector_list_holds_the_50_nearest_sections(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    sections = add_sections(version, *(f"Spare part number {index}." for index in range(60)))
    for index, section in enumerate(sections):
        embed(section, at_angle(1 + index))

    hits = search("which spare is nearest", limit=MAX_LIMIT).hits

    assert VECTOR_CANDIDATES == 50
    assert [hit.section_id for hit in hits] == [s.pk for s in sections[:VECTOR_CANDIDATES]]


def test_query_goes_through_the_embedding_interface_with_its_prefix(
    settings: Settings, version: DocumentVersion
) -> None:
    # The real client of 044 against the HTTP stand-in: prefix and model as set.
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_EMBED_DIMENSIONS = EMBEDDING_DIMENSIONS
    settings.TWOX_EMBED_MODEL = "bge-m3"
    settings.TWOX_EMBED_QUERY_PREFIX = "query: "
    (section,) = add_sections(version, ANSWER)
    embed(section, vector_for("query: " + QUESTION, EMBEDDING_DIMENSIONS), model="bge-m3")

    with fake_ollama(FakeOllama(dimensions=EMBEDDING_DIMENSIONS)) as (base_url, stand_in):
        settings.TWOX_LLM_BASE_URL = base_url
        result = search(QUESTION)

    assert [request.body["input"] for request in stand_in.embed_requests] == [
        ["query: " + QUESTION]
    ]
    assert result.semantic_used is True
    assert [hit.section_id for hit in result.hits] == [section.pk]
    assert result.hits[0].match_kinds == [MatchKind.SEMANTIC]


# --- Model service fails -------------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        EmbeddingUnavailableError("the model service refused the connection"),
        EmbeddingRejectedError("model 'bge-m3' is not loaded in Ollama"),
        EmbeddingRemoteModelError("model 'x:cloud' is an Ollama cloud model"),
        EmbeddingDimensionError("model 'bge-m3' returned 768 values, expected 1024"),
    ],
    ids=lambda error: type(error).__name__,
)
def test_failing_model_gives_keyword_hits_only(
    version: DocumentVersion,
    fake_embedder: FakeEmbedder,
    caplog: pytest.LogCaptureFixture,
    error: EmbeddingError,
) -> None:
    query = "secret gearbox question 4711"
    keyword, semantic = add_sections(version, "The gearbox runs.", "Replace the oil.")
    embed(semantic, at_angle(0))
    fake_embedder.error = error
    caplog.set_level(logging.WARNING, logger="twox.search.postgres")

    result = search(query.replace("secret ", "").replace(" question 4711", ""))
    search(query)

    assert result.semantic_used is False
    assert [hit.section_id for hit in result.hits] == [keyword.pk]
    assert result.hits[0].match_kinds == [MatchKind.KEYWORD]
    records = [r for r in caplog.records if r.name == "twox.search.postgres"]
    assert len(records) == 2
    assert all(record.levelno == logging.WARNING for record in records)
    assert type(error).__name__ in records[0].getMessage()
    assert "keyword search only" in records[0].getMessage()
    # Never the query in the server log.
    assert "secret" not in caplog.text
    assert "4711" not in caplog.text
    assert "gearbox" not in caplog.text


def test_unreachable_model_service_gives_keyword_hits_only(
    settings: Settings, version: DocumentVersion, caplog: pytest.LogCaptureFixture
) -> None:
    # The real client of 044 against a closed port: connection refused.
    settings.TWOX_AI_ENABLED = True
    (section,) = add_sections(version, "The gearbox runs.")
    caplog.set_level(logging.WARNING, logger="twox.search.postgres")

    result = search("gearbox")

    assert result.semantic_used is False
    assert [hit.section_id for hit in result.hits] == [section.pk]
    assert "EmbeddingUnavailableError" in caplog.text
    assert "gearbox" not in caplog.text


def test_vector_of_wrong_length_gives_keyword_hits_only(
    version: DocumentVersion, fake_embedder: FakeEmbedder, caplog: pytest.LogCaptureFixture
) -> None:
    (section,) = add_sections(version, "The gearbox runs.")
    fake_embedder.queries["gearbox"] = [1.0, 0.0, 0.0]
    caplog.set_level(logging.WARNING, logger="twox.search.postgres")

    result = search("gearbox")

    assert result.semantic_used is False
    assert [hit.section_id for hit in result.hits] == [section.pk]
    assert "returned 3 values" in caplog.text


def test_semantic_state_tells_failure_from_switched_off(
    settings: Settings, version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    (section,) = add_sections(version, "The gearbox runs.")

    assert search("gearbox").semantic is SemanticState.USED
    fake_embedder.error = EmbeddingUnavailableError("no answer from the model service within 20s")
    failed = search("gearbox")
    settings.TWOX_AI_ENABLED = False
    switched_off = search("gearbox")

    assert failed.semantic is SemanticState.UNAVAILABLE
    assert switched_off.semantic is SemanticState.DISABLED
    for result in (failed, switched_off):
        assert result.semantic_used is False
        assert [hit.section_id for hit in result.hits] == [section.pk]
    # Off: the model was not asked again.
    assert fake_embedder.calls == ["gearbox", "gearbox"]


# --- The query embedder: short time limit, model list once per process -----------


def test_query_embedder_has_the_search_time_limit(settings: Settings) -> None:
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_EMBED_TIMEOUT_SECONDS = 120
    settings.TWOX_SEARCH_EMBED_TIMEOUT_SECONDS = 7

    embedder = embeddings.get_query_embedder()

    assert isinstance(embedder, embeddings.OpenAICompatibleEmbedder)
    assert embedder.timeout == 7.0
    assert embedder.model_name == settings.TWOX_EMBED_MODEL
    # One per process while the settings stay the same.
    assert embeddings.get_query_embedder() is embedder
    settings.TWOX_SEARCH_EMBED_TIMEOUT_SECONDS = 9
    assert embeddings.get_query_embedder() is not embedder
    # The embedder of the ingestion keeps its own, longer limit.
    ingest = embeddings.get_embedder()
    assert isinstance(ingest, embeddings.OpenAICompatibleEmbedder)
    assert ingest.timeout == 120.0


def test_query_embedder_refuses_when_ai_is_off(settings: Settings) -> None:
    with pytest.raises(embeddings.EmbeddingDisabledError):
        embeddings.get_query_embedder()


def _real_client_settings(settings: Settings, base_url: str) -> None:
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_EMBED_DIMENSIONS = EMBEDDING_DIMENSIONS
    settings.TWOX_EMBED_MODEL = "bge-m3"
    settings.TWOX_EMBED_QUERY_PREFIX = ""
    settings.TWOX_LLM_BASE_URL = base_url


def test_model_list_is_asked_once_for_several_searches(
    settings: Settings, version: DocumentVersion
) -> None:
    add_sections(version, "The gearbox runs.")

    with fake_ollama(FakeOllama(dimensions=EMBEDDING_DIMENSIONS)) as (base_url, stand_in):
        _real_client_settings(settings, base_url)
        states = [search(query).semantic for query in ("gearbox", "oil", "belt")]

    assert states == [SemanticState.USED] * 3
    assert [request.path for request in stand_in.requests] == [
        "/api/tags",
        "/v1/embeddings",
        "/v1/embeddings",
        "/v1/embeddings",
    ]


def test_model_list_is_asked_again_after_the_check_time(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, version: DocumentVersion
) -> None:
    add_sections(version, "The gearbox runs.")
    now = [1000.0]
    monkeypatch.setattr(embeddings, "monotonic", lambda: now[0])

    with fake_ollama(FakeOllama(dimensions=EMBEDDING_DIMENSIONS)) as (base_url, stand_in):
        _real_client_settings(settings, base_url)
        search("gearbox")
        now[0] += embeddings.QUERY_MODEL_CHECK_SECONDS - 1
        search("gearbox")
        now[0] += 2
        # Meanwhile the model became a cloud model: the next check refuses it.
        stand_in.models = [{"name": "bge-m3:latest", "remote_host": "https://ollama.com:443"}]
        result = search("gearbox")

    assert [request.path for request in stand_in.requests] == [
        "/api/tags",
        "/v1/embeddings",
        "/v1/embeddings",
        "/api/tags",
    ]
    assert result.semantic is SemanticState.UNAVAILABLE


def test_failed_model_list_check_is_not_kept(settings: Settings, version: DocumentVersion) -> None:
    add_sections(version, "The gearbox runs.")

    with fake_ollama(FakeOllama(dimensions=EMBEDDING_DIMENSIONS, models=[])) as (
        base_url,
        stand_in,
    ):
        _real_client_settings(settings, base_url)
        first = search("gearbox")
        stand_in.models = [dict(LOCAL_MODEL)]
        second = search("gearbox")

    assert (first.semantic, second.semantic) == (SemanticState.UNAVAILABLE, SemanticState.USED)
    assert [request.path for request in stand_in.requests] == [
        "/api/tags",
        "/api/tags",
        "/v1/embeddings",
    ]


@contextmanager
def silent_model_service() -> Iterator[str]:
    """A port that accepts connections but never answers; yields its base URL."""
    with socket.create_server(("127.0.0.1", 0)) as server:
        yield f"http://127.0.0.1:{server.getsockname()[1]}/v1"


def test_hanging_model_service_holds_a_search_up_only_briefly(
    settings: Settings, version: DocumentVersion, caplog: pytest.LogCaptureFixture
) -> None:
    (section,) = add_sections(version, "The gearbox runs.")
    caplog.set_level(logging.WARNING, logger="twox.search.postgres")

    with silent_model_service() as base_url:
        _real_client_settings(settings, base_url)
        settings.TWOX_EMBED_TIMEOUT_SECONDS = 120
        settings.TWOX_SEARCH_EMBED_TIMEOUT_SECONDS = 1
        started = time.monotonic()
        result = search("gearbox")
        seconds = time.monotonic() - started

    assert result.semantic is SemanticState.UNAVAILABLE
    assert [hit.section_id for hit in result.hits] == [section.pk]
    assert seconds < 10
    assert "within 1s" in caplog.text


# --- AI features off (E-59) -----------------------------------------------------


def test_ai_off_never_asks_the_model(
    monkeypatch: pytest.MonkeyPatch, version: DocumentVersion, caplog: pytest.LogCaptureFixture
) -> None:
    def refuse() -> None:
        raise AssertionError("the search asked for an embedder with AI features off")

    monkeypatch.setattr(embeddings, "get_embedder", refuse)
    monkeypatch.setattr(embeddings, "get_query_embedder", refuse)
    answer, keyword = add_sections(version, ANSWER, "The pump runs.")
    embed(answer, at_angle(0))
    caplog.set_level(logging.DEBUG, logger="twox.search.postgres")

    assert search(QUESTION).hits == []
    result = search("pump")

    assert result.semantic_used is False
    assert [hit.section_id for hit in result.hits] == [keyword.pk]
    # Off is a normal state, not an error: the search logs nothing.
    assert [r for r in caplog.records if r.name == "twox.search.postgres"] == []


# --- Which sections take part -----------------------------------------------------


def test_sections_without_embedding_or_of_another_model_come_by_keyword_only(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    current, other_model, without = add_sections(
        version,
        "The gearbox of the current model.",
        "The gearbox of another model.",
        "The gearbox without embedding.",
    )
    embed(current, at_angle(40))
    embed(other_model, at_angle(0), model="other-embed")

    hits = {hit.section_id: hit for hit in search("gearbox").hits}
    nearest = search("unrelated words here").hits

    assert hits[current.pk].match_kinds == [MatchKind.KEYWORD, MatchKind.SEMANTIC]
    assert hits[other_model.pk].match_kinds == [MatchKind.KEYWORD]
    assert hits[without.pk].match_kinds == [MatchKind.KEYWORD]
    assert [hit.section_id for hit in nearest] == [current.pk]


def test_filters_work_in_the_vector_list(plant: Plant, fake_embedder: FakeEmbedder) -> None:
    other_plant = make_plant("line-b")
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    third = make_device(other_plant, "plc-03")
    found: dict[str, int] = {}
    for degrees, device in ((10, first), (20, second), (30, third)):
        (section,) = add_sections(make_document(device), f"Notes for {device.key}.")
        embed(section, at_angle(degrees))
        found[device.key] = section.pk

    def keys(device_ids: Sequence[int] = (), plant_ids: Sequence[int] = ()) -> list[str]:
        by_id = {pk: key for key, pk in found.items()}
        return [by_id[pk] for pk in section_ids(QUESTION, device_ids, plant_ids)]

    assert keys() == ["plc-01", "plc-02", "plc-03"]
    assert keys(device_ids=[second.pk]) == ["plc-02"]
    assert keys(device_ids=[third.pk, first.pk]) == ["plc-01", "plc-03"]
    assert keys(plant_ids=[other_plant.pk]) == ["plc-03"]
    assert keys(plant_ids=[plant.pk], device_ids=[third.pk]) == []


def test_exclusion_holds_for_vector_hits(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    answer, other = add_sections(version, ANSWER, "Top up the grease of the bearing.")
    embed(answer, at_angle(10))
    embed(other, at_angle(30))

    # The answer is nearest, but it holds the excluded word ("hours" -> "hour").
    result = search(f"{QUESTION} -hour")

    assert result.semantic is SemanticState.USED
    assert [hit.section_id for hit in result.hits] == [other.pk]
    assert result.hits[0].match_kinds == [MatchKind.SEMANTIC]
    assert section_ids(QUESTION) == [answer.pk, other.pk]


def test_excluded_sections_do_not_shorten_the_vector_list(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    excluded = add_sections(version, *(f"Spare belt number {index}." for index in range(10)))
    kept = add_sections(version, *(f"Spare part number {index}." for index in range(60)))
    for index, section in enumerate(excluded):
        embed(section, at_angle(0.5 + index / 100))
    for index, section in enumerate(kept):
        embed(section, at_angle(1 + index))

    hits = search("which spare is nearest -belt", limit=MAX_LIMIT).hits

    assert [hit.section_id for hit in hits] == [s.pk for s in kept[:VECTOR_CANDIDATES]]


def test_vector_query_leaves_out_excluded_sections_itself(version: DocumentVersion) -> None:
    answer, other = add_sections(version, ANSWER, "Top up the grease.")
    embed(answer, at_angle(10))
    embed(other, at_angle(30))
    request = SearchRequest(query="x -gearbox")
    exclusions = _Queries(per_config={"simple": "'gearbox'"})

    with connection.cursor() as cursor:
        nearest = nearest_sections(cursor, request, FAKE_MODEL, unit(0), exclusions)
        everything = nearest_sections(cursor, request, FAKE_MODEL, unit(0))

    assert nearest == [(other.pk, 1)]
    assert everything == [(answer.pk, 1), (other.pk, 2)]


def test_configuration_documents_are_not_in_the_vector_list(
    device: Device, fake_embedder: FakeEmbedder
) -> None:
    (config,) = add_sections(
        make_document(device, title="Backup", kind=DocumentKind.CONFIGURATION), "hostname plc"
    )
    (manual,) = add_sections(make_document(device), "The pump starts.")
    embed(config, at_angle(0))
    embed(manual, at_angle(45))

    assert section_ids(QUESTION) == [manual.pk]


def test_version_rule_works_in_the_vector_list(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    (old,) = add_sections(version, "Old wording of the oil change.")
    embed(old, at_angle(0))

    # The newer version has sections, not embedded yet: the old one is not
    # searched any more, neither by keyword nor by vector.
    newer = add_version(version.document)
    (new,) = add_sections(newer, "New wording of the oil change.")
    assert section_ids(QUESTION) == []
    assert section_ids("wording") == [new.pk]

    embed(new, at_angle(30))
    hits = search(QUESTION).hits
    assert [hit.section_id for hit in hits] == [new.pk]
    assert hits[0].locations[0].version_number == 2
    assert hits[0].locations[0].is_latest_version is True


def test_older_version_by_vector_while_the_newer_has_no_sections(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    (old,) = add_sections(version, "Old wording of the oil change.")
    embed(old, at_angle(0))
    add_version(version.document)

    (hit,) = search(QUESTION).hits

    assert hit.section_id == old.pk
    assert hit.locations[0].is_latest_version is False


def test_same_content_on_two_devices_is_one_semantic_hit(
    plant: Plant, fake_embedder: FakeEmbedder
) -> None:
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    shared = sha256_of("shared manual")
    (one,) = add_sections(make_document(first, sha256=shared), ANSWER)
    (two,) = add_sections(make_document(second, sha256=shared), ANSWER)
    embed(one, at_angle(10))
    embed(two, at_angle(10))

    (hit,) = search(QUESTION).hits
    (filtered,) = search(QUESTION, device_ids=[second.pk]).hits

    assert hit.match_kinds == [MatchKind.SEMANTIC]
    assert [location.device_key for location in hit.locations] == ["plc-01", "plc-02"]
    assert [location.device_key for location in filtered.locations] == ["plc-02"]
    assert filtered.section_id == two.pk


# --- Database side --------------------------------------------------------------


def test_vector_query_sets_the_hnsw_options_first(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    (section,) = add_sections(version, ANSWER)
    embed(section, at_angle(0))

    with CaptureQueriesContext(connection) as queries:
        assert section_ids(QUESTION) == [section.pk]

    statements = [query["sql"] for query in queries.captured_queries]
    settings_at = next(i for i, sql in enumerate(statements) if "set_config" in sql)
    vector_at = next(i for i, sql in enumerate(statements) if "<=>" in sql)
    assert settings_at < vector_at
    assert "'hnsw.iterative_scan', 'relaxed_order', true" in statements[settings_at]
    assert f"'hnsw.ef_search', '{HNSW_EF_SEARCH}', true" in statements[settings_at]
    assert HNSW_ITERATIVE_SCAN == "relaxed_order"
    assert HNSW_EF_SEARCH >= VECTOR_CANDIDATES


@pytest.mark.django_db(transaction=True)
def test_hnsw_options_end_with_the_vector_query(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    (section,) = add_sections(version, ANSWER)
    embed(section, at_angle(0))

    assert section_ids(QUESTION) == [section.pk]

    with connection.cursor() as cursor:
        cursor.execute("SHOW hnsw.ef_search")
        assert cursor.fetchone() == ("40",)
        cursor.execute("SHOW hnsw.iterative_scan")
        assert cursor.fetchone() == ("off",)


def test_distance_is_the_cosine_distance(version: DocumentVersion) -> None:
    (section,) = add_sections(version, ANSWER)
    embed(section, at_angle(60))

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT embedding <=> %s::vector FROM ingest_section WHERE id = %s",
            [vector_literal(unit(0)), section.pk],
        )
        (distance,) = cursor.fetchone() or (None,)

    assert distance == pytest.approx(cosine_distance(60))


def test_vector_literal_is_the_text_form_of_pgvector() -> None:
    assert vector_literal([1, 0.5, -2.25e-7]) == "[1.0,0.5,-2.25e-07]"


def test_search_with_vector_needs_five_queries_and_a_savepoint(
    version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    add_sections(version, *(f"The chi belt {index} runs." for index in range(10)))

    with CaptureQueriesContext(connection) as queries:
        assert len(search("chi belt").hits) == 10

    statements = [query["sql"] for query in queries.captured_queries]
    work = [sql for sql in statements if "SAVEPOINT" not in sql]
    # Parse, HNSW options, vector search, search, highlights.
    assert len(work) == 5
    assert len(statements) - len(work) == 2
    assert FAKE_MODEL in statements[statements.index(work[2])]


def test_vector_ranks_are_sorted_again_after_the_index() -> None:
    # With relaxed_order the index may return rows slightly out of order;
    # PostgreSQL 17+ would take the order of the CTE as given unless the sort
    # key is an expression (pgvector README: "distance + 0").
    request = SearchRequest(query="pump", device_ids=(), plant_ids=(), limit=10)
    params = {
        **_scope_params(request),
        "embedding": vector_literal(unit(0)),
        "model": FAKE_MODEL,
        "vector_limit": VECTOR_CANDIDATES,
    }
    sql = vector_sql(filter_devices=False, filter_plants=False)
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN " + sql, params)
        plan = "\n".join(row[0] for row in cursor.fetchall())

    # A full sort on the distance expression above the CTE scan (not a sort
    # that relies on the CTE being presorted by the plain distance).
    full_sort = re.compile(r"->  Sort .*\n\s+Sort Key: \(\(nearest\.distance \+ '0'")
    assert full_sort.search(plan), plan
