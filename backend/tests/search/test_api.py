"""Search API: rights, parameters, shape of the answer (work order 052).

The model interface is always :class:`FakeEmbedder` or switched off; no test
talks to a real model service (E-59). All texts are written for these tests.
"""

import logging
from typing import Any

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from pytest_django.fixtures import Settings
from rest_framework.test import APIClient

from tests.config.test_api import generate_schema
from tests.files.helpers import client_for
from tests.search.fake_embedder import FakeEmbedder, at_angle, embed
from tests.search.test_keyword_search import (
    add_sections,
    add_version,
    make_device,
    make_document,
    make_plant,
    sha256_of,
)
from twox.answers.embeddings import EmbeddingUnavailableError
from twox.assets.models import Device, Plant
from twox.files.models import Document, DocumentVersion
from twox.search import api
from twox.search.api import DEFAULT_HITS, MAX_FILTER_IDS, MAX_HITS, MAX_QUERY_CHARS
from twox.search.interface import (
    Highlight,
    HitLocation,
    MatchKind,
    SearchHit,
    SearchRequest,
    SearchResult,
    SemanticState,
)

pytestmark = pytest.mark.django_db

URL = "/api/v1/search/"

HIT_FIELDS = {
    "section_id",
    "score",
    "match_kinds",
    "snippet",
    "highlights",
    "page_start",
    "page_end",
    "heading_path",
    "locations",
}


class StandInBackend:
    """A search backend that records its requests and answers with a fixed result."""

    def __init__(self, result: SearchResult | None = None) -> None:
        self.result = result or SearchResult()
        self.requests: list[SearchRequest] = []

    def search(self, request: SearchRequest) -> SearchResult:
        self.requests.append(request)
        return self.result


@pytest.fixture
def stand_in(monkeypatch: pytest.MonkeyPatch) -> StandInBackend:
    backend = StandInBackend()
    monkeypatch.setattr(api, "get_search_backend", lambda: backend)
    return backend


@pytest.fixture
def reader() -> APIClient:
    return client_for("read")


def get(client: APIClient, params: dict[str, Any] | list[tuple[str, Any]]) -> dict[str, Any]:
    response = client.get(URL, params)
    assert response.status_code == 200, response.content
    answer: dict[str, Any] = response.json()
    return answer


# --- Rights ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("anonymous", 403), ("no_role", 403), ("read", 200), ("manage", 200), ("superuser", 200)],
)
def test_search_needs_a_role(kind: str, expected: int, stand_in: StandInBackend) -> None:
    response = client_for(kind).get(URL, {"q": "pump"})

    assert response.status_code == expected
    assert len(stand_in.requests) == (1 if expected == 200 else 0)


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_search_is_read_only(method: str, stand_in: StandInBackend) -> None:
    response = getattr(client_for("manage"), method)(URL + "?q=pump")

    assert response.status_code == 405
    assert stand_in.requests == []


# --- Parameters ---------------------------------------------------------------


def test_parameters_reach_the_search_interface(reader: APIClient, stand_in: StandInBackend) -> None:
    get(reader, [("q", "  pump 192.168.0.5  "), ("device", 3), ("device", 7), ("plant", 2)])
    get(reader, {"q": "valve", "limit": MAX_HITS})

    assert stand_in.requests == [
        SearchRequest(query="pump 192.168.0.5", device_ids=(3, 7), plant_ids=(2,), limit=20),
        SearchRequest(query="valve", device_ids=(), plant_ids=(), limit=MAX_HITS),
    ]
    assert DEFAULT_HITS == 20
    assert MAX_HITS == 50
    # The API never asks for the keyword search only.
    assert not any(request.keyword_only for request in stand_in.requests)


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({}, "q"),
        ({"q": ""}, "q"),
        ({"q": "   "}, "q"),
        ({"q": "x" * (MAX_QUERY_CHARS + 1)}, "q"),
        ({"q": "a\x00b"}, "q"),
        ({"q": "pump", "device": "abc"}, "device"),
        ({"q": "pump", "device": "0"}, "device"),
        ({"q": "pump", "device": ""}, "device"),
        ({"q": "pump", "device": str(2**63)}, "device"),
        ({"q": "pump", "plant": "-1"}, "plant"),
        ({"q": "pump", "plant": "1.5"}, "plant"),
        ({"q": "pump", "limit": "0"}, "limit"),
        ({"q": "pump", "limit": str(MAX_HITS + 1)}, "limit"),
        ({"q": "pump", "limit": "many"}, "limit"),
        ({"q": "pump", "device": [str(i) for i in range(1, MAX_FILTER_IDS + 2)]}, "device"),
    ],
)
def test_invalid_parameters_give_400_at_the_field(
    reader: APIClient, stand_in: StandInBackend, params: dict[str, Any], field: str
) -> None:
    response = reader.get(URL, params)

    assert response.status_code == 400
    assert set(response.json()) == {field}
    assert stand_in.requests == []


def test_query_length_counts_after_trimming(reader: APIClient, stand_in: StandInBackend) -> None:
    query = "x" * MAX_QUERY_CHARS

    get(reader, {"q": f"   {query}   "})

    assert stand_in.requests[0].query == query


def test_field_errors_are_translated(stand_in: StandInBackend) -> None:
    client = client_for("read")

    response = client.get(URL, {"limit": "0"}, headers={"Accept-Language": "de"})

    assert response.status_code == 400
    assert response.json()["q"] == ["Dieses Feld ist zwingend erforderlich."]


# --- Shape of the answer ----------------------------------------------------------


def stand_in_hit() -> SearchHit:
    return SearchHit(
        section_id=11,
        score=1.25,
        match_kinds=[MatchKind.EXACT, MatchKind.SEMANTIC],
        snippet="…set 10.0.0.9 here",
        highlights=[Highlight(start=5, end=13)],
        page_start=4,
        page_end=5,
        heading_path=["Network", "Addresses"],
        locations=[
            HitLocation(
                section_id=11,
                document_id=21,
                document_title="Manual",
                version_id=31,
                version_number=2,
                version_filename="manual v2.pdf",
                is_latest_version=False,
                device_id=41,
                device_key="plc-01",
                device_name="Press control",
                plant_id=51,
                plant_key="line-a",
                plant_name="Line A",
            )
        ],
    )


@pytest.mark.parametrize("state", list(SemanticState))
def test_answer_shape(reader: APIClient, stand_in: StandInBackend, state: SemanticState) -> None:
    stand_in.result = SearchResult(hits=[stand_in_hit()], semantic=state)

    answer = get(reader, {"q": "10.0.0.9"})

    assert answer == {
        "semantic": state.value,
        "hits": [
            {
                "section_id": 11,
                "score": 1.25,
                "match_kinds": ["exact", "semantic"],
                "snippet": "…set 10.0.0.9 here",
                "highlights": [{"start": 5, "end": 13}],
                "page_start": 4,
                "page_end": 5,
                "heading_path": ["Network", "Addresses"],
                "locations": [
                    {
                        "document": {"id": 21, "title": "Manual"},
                        "version": {
                            "id": 31,
                            "number": 2,
                            "original_filename": "manual v2.pdf",
                            "is_latest": False,
                        },
                        "device": {"id": 41, "key": "plc-01", "name": "Press control"},
                        "plant": {"id": 51, "key": "line-a", "name": "Line A"},
                    }
                ],
            }
        ],
    }
    # The highlight lies on the found place.
    assert answer["hits"][0]["snippet"][5:13] == "10.0.0.9"


def test_answer_without_hits(reader: APIClient, stand_in: StandInBackend) -> None:
    assert get(reader, {"q": "pump"}) == {"semantic": "disabled", "hits": []}


def test_snippet_with_markup_stays_plain_text(reader: APIClient, version: DocumentVersion) -> None:
    add_sections(version, "The sigma <b>valve</b> & <script>x</script> opens.")

    response = reader.get(URL, {"q": "sigma"})

    assert response["Content-Type"] == "application/json"
    (hit,) = response.json()["hits"]
    assert hit["snippet"] == "The sigma <b>valve</b> & <script>x</script> opens."
    assert hit["snippet"][hit["highlights"][0]["start"] : hit["highlights"][0]["end"]] == "sigma"


# --- With the database ------------------------------------------------------------


@pytest.fixture
def plant() -> Plant:
    return make_plant()


@pytest.fixture
def device(plant: Plant) -> Device:
    return make_device(plant, "plc-01")


@pytest.fixture
def version(device: Device) -> DocumentVersion:
    return make_document(device)


def test_ip_search_names_page_and_device(
    reader: APIClient, plant: Plant, device: Device, version: DocumentVersion
) -> None:
    add_sections(version, "The panel has the address 192.168.0.50.", page=3)
    (section,) = add_sections(version, "The controller listens on 192.168.0.5.", page=7)

    answer = get(reader, {"q": "192.168.0.5"})

    (hit,) = answer["hits"]
    assert set(hit) == HIT_FIELDS
    assert hit["section_id"] == section.pk
    assert (hit["page_start"], hit["page_end"]) == (7, 7)
    assert "exact" in hit["match_kinds"]
    snippet = hit["snippet"]
    assert [snippet[h["start"] : h["end"]] for h in hit["highlights"]] == ["192.168.0.5"]
    assert hit["locations"] == [
        {
            "document": {"id": version.document_id, "title": "Operating manual"},
            "version": {
                "id": version.pk,
                "number": 1,
                "original_filename": "manual.pdf",
                "is_latest": True,
            },
            "device": {"id": device.pk, "key": "plc-01", "name": "Device plc-01"},
            "plant": {"id": plant.pk, "key": "line-a", "name": "Plant line-a"},
        }
    ]


def test_same_content_on_two_devices_is_one_hit_with_two_places(
    reader: APIClient, plant: Plant
) -> None:
    first = make_device(plant, "plc-01")
    second = make_device(plant, "plc-02")
    shared = sha256_of("shared manual for the API")
    add_sections(make_document(first, title="Manual A", sha256=shared), "The tau valve opens.")
    add_sections(
        add_version(
            Document.objects.create(device=second, title="Manual B"),
            sha256=shared,
            filename="copy.pdf",
        ),
        "The tau valve opens.",
    )

    (hit,) = get(reader, {"q": "tau"})["hits"]
    (filtered,) = get(reader, {"q": "tau", "device": second.pk})["hits"]

    assert [
        (place["device"]["key"], place["document"]["title"], place["version"]["original_filename"])
        for place in hit["locations"]
    ] == [("plc-01", "Manual A", "manual.pdf"), ("plc-02", "Manual B", "copy.pdf")]
    assert [place["device"]["key"] for place in filtered["locations"]] == ["plc-02"]


def test_filter_by_plant(reader: APIClient, plant: Plant) -> None:
    other = make_plant("line-b")
    add_sections(make_document(make_device(plant, "plc-01")), "The chi lamp is on.")
    add_sections(make_document(make_device(other, "plc-02")), "The chi lamp is off.")

    hits = get(reader, [("q", "chi"), ("plant", other.pk)])["hits"]
    both = get(reader, [("q", "chi"), ("plant", other.pk), ("plant", plant.pk)])["hits"]

    assert [hit["locations"][0]["plant"]["key"] for hit in hits] == ["line-b"]
    assert len(both) == 2


def test_limit_bounds_the_hits(reader: APIClient, version: DocumentVersion) -> None:
    add_sections(version, *(f"The psi belt {index} runs." for index in range(MAX_HITS + 5)))

    assert len(get(reader, {"q": "psi"})["hits"]) == DEFAULT_HITS
    assert len(get(reader, {"q": "psi", "limit": 3})["hits"]) == 3
    assert len(get(reader, {"q": "psi", "limit": MAX_HITS})["hits"]) == MAX_HITS


def test_semantic_disabled_with_ai_off(
    reader: APIClient, settings: Settings, version: DocumentVersion
) -> None:
    (section,) = add_sections(version, "The omega pump runs.")
    settings.TWOX_AI_ENABLED = False

    answer = get(reader, {"q": "omega"})

    assert answer["semantic"] == "disabled"
    assert [hit["section_id"] for hit in answer["hits"]] == [section.pk]


def test_semantic_used_with_the_model(
    reader: APIClient, version: DocumentVersion, fake_embedder: FakeEmbedder
) -> None:
    answer_section, other = add_sections(version, "Replace the oil every year.", "The lamp.")
    embed(answer_section, at_angle(10))
    embed(other, at_angle(60))

    answer = get(reader, {"q": "How do I change the lubricant?"})

    assert answer["semantic"] == "used"
    assert [hit["section_id"] for hit in answer["hits"]] == [answer_section.pk, other.pk]
    assert answer["hits"][0]["match_kinds"] == ["semantic"]
    assert answer["hits"][0]["highlights"] == []
    assert fake_embedder.calls == ["How do I change the lubricant?"]


def test_semantic_false_when_the_model_fails(
    reader: APIClient,
    version: DocumentVersion,
    fake_embedder: FakeEmbedder,
    caplog: pytest.LogCaptureFixture,
) -> None:
    (section,) = add_sections(version, "The zzprobe pump runs.")
    fake_embedder.error = EmbeddingUnavailableError("no answer from the model service within 20s")
    caplog.set_level(logging.DEBUG)

    answer = get(reader, {"q": "zzprobe"})

    assert answer["semantic"] == "unavailable"
    assert [hit["section_id"] for hit in answer["hits"]] == [section.pk]
    assert answer["hits"][0]["match_kinds"] == ["keyword"]
    # The failure is logged, the search text is not.
    assert "EmbeddingUnavailableError" in caplog.text
    assert "zzprobe" not in caplog.text


def test_search_writes_nothing(reader: APIClient, version: DocumentVersion) -> None:
    add_sections(version, "The kappa pump runs.")

    with CaptureQueriesContext(connection) as queries:
        get(reader, {"q": "kappa 192.168.0.5"})

    writes = [
        query["sql"]
        for query in queries.captured_queries
        if query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
    # At most the session of the signed-in user; never the search text.
    assert all("kappa" not in sql for sql in writes)
    assert all("search" not in sql.lower() for sql in writes)


# --- Schema -----------------------------------------------------------------------


def test_schema_describes_the_search() -> None:
    schema, stderr = generate_schema()
    operation = schema["paths"][URL]
    components: dict[str, Any] = schema["components"]["schemas"]

    assert stderr == ""
    assert set(operation) == {"get"}
    get_operation = operation["get"]
    assert get_operation["operationId"] == "search"
    assert set(get_operation["responses"]) == {"200", "400", "403"}
    parameters = {parameter["name"]: parameter for parameter in get_operation["parameters"]}
    assert set(parameters) == {"q", "device", "plant", "limit"}
    assert parameters["q"]["required"] is True
    assert parameters["q"]["schema"]["maxLength"] == MAX_QUERY_CHARS
    for name in ("device", "plant"):
        assert parameters[name]["schema"]["type"] == "array"
        assert parameters[name]["schema"]["items"]["type"] == "integer"
    assert parameters["limit"]["schema"]["maximum"] == MAX_HITS
    result = components["SearchResult"]["properties"]
    assert set(result) == {"semantic", "hits"}
    assert set(components["SearchHit"]["properties"]) == HIT_FIELDS
    assert set(components["SearchVersion"]["properties"]) == {
        "id",
        "number",
        "original_filename",
        "is_latest",
    }
    (reference,) = result["semantic"]["allOf"]
    semantic = components[reference["$ref"].rsplit("/", 1)[1]]
    assert semantic["enum"] == ["used", "disabled", "unavailable"]
    assert components["MatchKindsEnum"]["enum"] == ["exact", "keyword", "semantic"]
