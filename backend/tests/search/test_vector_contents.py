"""The vector list counts contents, not section rows (149).

The same manual stored for several devices is one content with a section per
copy (E-55). Before 149 the vector list held the 50 nearest section rows, so
copies took up the list and it held only a few contents. Now it holds the
sections of the :data:`~twox.search.postgres.VECTOR_CANDIDATES` nearest
contents, with every copy. All texts are written for these tests.
"""

from collections.abc import Sequence

import pytest
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext

from tests.search.fake_embedder import FAKE_MODEL, FakeEmbedder, at_angle, cosine_distance, embed
from tests.search.test_keyword_search import (
    add_sections,
    make_device,
    make_document,
    make_plant,
    search,
    sha256_of,
)
from twox.assets.models import Device, Plant
from twox.files.models import DocumentVersion
from twox.ingest.models import Section, SectionPiece
from twox.search import postgres
from twox.search.interface import MAX_LIMIT, SearchRequest
from twox.search.postgres import (
    HNSW_EF_SEARCH,
    HNSW_ITERATIVE_SCAN,
    VECTOR_CANDIDATES,
    _Queries,
    _scope_params,
    nearest_sections_with_distance,
    vector_literal,
    vector_sql,
)

pytestmark = pytest.mark.django_db

#: A question that shares no word with the sections below.
QUESTION = "How do I change the lubricant?"
#: Devices that hold a copy of the shared manual.
COPIES = 20
#: Sections of the shared manual; with every copy more rows than the index scan reads.
SHARED_SECTIONS = 12
#: Contents that exist once.
SINGLE_CONTENTS = 60


@pytest.fixture
def plant() -> Plant:
    return make_plant()


@pytest.fixture
def devices(plant: Plant) -> list[Device]:
    return [make_device(plant, f"plc-{index:02d}") for index in range(COPIES)]


def add_shared_manual(
    devices: Sequence[Device], texts: Sequence[str], first_angle: float = 0.5
) -> list[list[Section]]:
    """The same manual (same checksum, same sections) for every device.

    Returns the sections per content: one list per text, one section per device.
    Section ``i`` of every copy lies at ``first_angle + i / 10`` degrees.
    """
    shared = sha256_of("shared manual")
    contents: list[list[Section]] = [[] for _ in texts]
    for device in devices:
        sections = add_sections(make_document(device, sha256=shared), *texts)
        for index, section in enumerate(sections):
            embed(section, at_angle(first_angle + index / 10))
            contents[index].append(section)
    return contents


def add_single_contents(version: DocumentVersion, count: int) -> list[Section]:
    """``count`` contents that exist once, the first at 10 degrees, then one degree apart."""
    sections = add_sections(version, *(f"Spare part number {index}." for index in range(count)))
    for index, section in enumerate(sections):
        embed(section, at_angle(10 + index))
    return sections


def nearest(
    request: SearchRequest, exclusions: _Queries | None = None
) -> list[tuple[int, int, float]]:
    with connection.cursor() as cursor:
        return nearest_sections_with_distance(cursor, request, FAKE_MODEL, at_angle(0), exclusions)


def near(degrees: float) -> object:
    """The distance of :func:`at_angle` (``degrees``), as exact as stored ``float4`` values are."""
    return pytest.approx(cosine_distance(degrees), rel=1e-3)


def ranks_of(rows: Sequence[tuple[int, int, float]]) -> dict[int, int]:
    return {section_id: rank for section_id, rank, _ in rows}


def test_copies_count_once_and_the_list_holds_50_contents(devices: list[Device]) -> None:
    shared = add_shared_manual(
        devices, [f"Belt tension, step {index}." for index in range(SHARED_SECTIONS)]
    )
    single = add_single_contents(make_document(devices[0], title="Spare parts"), SINGLE_CONTENTS)
    # The copies alone fill more rows than the index scan reads.
    assert SHARED_SECTIONS * COPIES > VECTOR_CANDIDATES

    rows = nearest(SearchRequest(query=QUESTION))

    wanted_single = single[: VECTOR_CANDIDATES - SHARED_SECTIONS]
    expected_ids = [s.pk for content in shared for s in content] + [s.pk for s in wanted_single]
    assert sorted(section_id for section_id, _, _ in rows) == sorted(expected_ids)
    # Exactly VECTOR_CANDIDATES contents: one rank per content, 1 to 50.
    assert sorted({rank for _, rank, _ in rows}) == list(range(1, VECTOR_CANDIDATES + 1))
    ranks = ranks_of(rows)
    distances = {section_id: distance for section_id, _, distance in rows}
    for index, content in enumerate(shared):
        # Every copy carries the rank and the distance of its content.
        assert {ranks[s.pk] for s in content} == {index + 1}
        assert [distances[s.pk] for s in content] == [near(0.5 + index / 10)] * COPIES
    assert [ranks[s.pk] for s in wanted_single] == list(
        range(SHARED_SECTIONS + 1, VECTOR_CANDIDATES + 1)
    )
    # Nearest first, copies of a content side by side.
    assert [rank for _, rank, _ in rows] == sorted(rank for _, rank, _ in rows)


def test_search_keeps_every_location_of_the_copies(
    devices: list[Device], fake_embedder: FakeEmbedder
) -> None:
    add_shared_manual(devices, [f"Belt tension, step {index}." for index in range(SHARED_SECTIONS)])
    single = add_single_contents(make_document(devices[0], title="Spare parts"), SINGLE_CONTENTS)

    hits = search(QUESTION, limit=MAX_LIMIT).hits

    assert len(hits) == VECTOR_CANDIDATES
    for hit in hits[:SHARED_SECTIONS]:
        assert [location.device_key for location in hit.locations] == [d.key for d in devices]
    assert [hit.section_id for hit in hits[SHARED_SECTIONS:]] == [
        s.pk for s in single[: VECTOR_CANDIDATES - SHARED_SECTIONS]
    ]


def exact_branch_ran(request: SearchRequest) -> bool | None:
    """Whether the vector query took the exact branch; ``None`` without rows."""
    sql = vector_sql(filter_devices=bool(request.device_ids), filter_plants=bool(request.plant_ids))
    params = {
        **_scope_params(request),
        "embedding": vector_literal(at_angle(0)),
        "model": FAKE_MODEL,
        "vector_limit": postgres.VECTOR_CANDIDATES,
        "piece_limit": postgres.PIECE_CANDIDATES,
    }
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('hnsw.iterative_scan', %s, true),"
            " set_config('hnsw.ef_search', %s, true)",
            [HNSW_ITERATIVE_SCAN, str(HNSW_EF_SEARCH)],
        )
        cursor.execute(sql, params)
        flags = {bool(row[3]) for row in cursor.fetchall()}
    assert len(flags) <= 1
    return flags.pop() if flags else None


def vector_statements(request: SearchRequest) -> tuple[list[tuple[int, int, float]], list[str]]:
    """The vector list for ``request`` and the vector queries it took."""
    with CaptureQueriesContext(connection) as captured:
        rows = nearest(request)
    return rows, [query["sql"] for query in captured.captured_queries if "<=>" in query["sql"]]


def test_copies_the_index_scan_did_not_read_still_take_part(
    monkeypatch: pytest.MonkeyPatch, devices: list[Device]
) -> None:
    # One content wanted: the index scan reads one copy of the nearest
    # content, which is enough; every other copy comes through the content key.
    monkeypatch.setattr(postgres, "VECTOR_CANDIDATES", 1)
    (shared,) = add_shared_manual(devices, ["Belt tension."])
    add_single_contents(make_document(devices[0], title="Spare parts"), 3)

    rows, statements = vector_statements(SearchRequest(query=QUESTION))

    assert len(statements) == 1
    assert exact_branch_ran(SearchRequest(query=QUESTION)) is False
    assert sorted(section_id for section_id, _, _ in rows) == sorted(s.pk for s in shared)
    assert {rank for _, rank, _ in rows} == {1}


def test_copies_in_the_index_rows_lead_to_the_exact_branch(devices: list[Device]) -> None:
    add_shared_manual(devices, [f"Belt tension, step {index}." for index in range(SHARED_SECTIONS)])
    add_single_contents(make_document(devices[0], title="Spare parts"), SINGLE_CONTENTS)

    rows, statements = vector_statements(SearchRequest(query=QUESTION))

    # The 50 nearest rows are copies of three contents: the same query goes
    # on exactly; still one query.
    assert len(statements) == 1
    assert exact_branch_ran(SearchRequest(query=QUESTION)) is True
    assert len({rank for _, rank, _ in rows}) == VECTOR_CANDIDATES


def test_without_copies_the_index_is_enough(plant: Plant) -> None:
    add_single_contents(make_document(make_device(plant, "plc-01")), SINGLE_CONTENTS)

    rows, statements = vector_statements(SearchRequest(query=QUESTION))

    assert len(statements) == 1
    assert len(rows) == VECTOR_CANDIDATES


def test_nothing_embedded_finds_nothing(plant: Plant) -> None:
    add_sections(make_document(make_device(plant, "plc-01")), "Belt tension.")

    rows, statements = vector_statements(SearchRequest(query=QUESTION))

    assert (rows, len(statements)) == ([], 1)


def test_fewer_contents_than_wanted_are_all_found(devices: list[Device]) -> None:
    shared = add_shared_manual(devices, ["Belt tension.", "Belt wear."])
    single = add_single_contents(make_document(devices[0], title="Spare parts"), 3)

    rows = nearest(SearchRequest(query=QUESTION))

    assert sorted(section_id for section_id, _, _ in rows) == sorted(
        [s.pk for content in shared for s in content] + [s.pk for s in single]
    )
    assert sorted({rank for _, rank, _ in rows}) == [1, 2, 3, 4, 5]
    # Fewer contents than wanted in the index rows: the exact branch made sure.
    assert exact_branch_ran(SearchRequest(query=QUESTION)) is True


def test_exact_branch_runs_only_when_needed() -> None:
    # The branch not taken is behind a one-time filter: PostgreSQL never runs it.
    request = SearchRequest(query=QUESTION)
    params = {
        **_scope_params(request),
        "embedding": vector_literal(at_angle(0)),
        "model": FAKE_MODEL,
        "vector_limit": VECTOR_CANDIDATES,
        "piece_limit": postgres.PIECE_CANDIDATES,
    }
    sql = vector_sql(filter_devices=False, filter_plants=False)
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN " + sql, params)
        plan = "\n".join(row[0] for row in cursor.fetchall())

    assert plan.count("One-Time Filter") >= 2, plan


def test_device_filter_applies_before_the_contents_are_counted(
    plant: Plant, devices: list[Device]
) -> None:
    shared = add_shared_manual(
        devices, [f"Belt tension, step {index}." for index in range(SHARED_SECTIONS)]
    )
    other = make_device(plant, "plc-99")
    single = add_single_contents(make_document(other, title="Spare parts"), SINGLE_CONTENTS)
    # Nearer than every shared section, but on a device outside the filter.
    (outside,) = add_sections(make_document(devices[1], title="Other"), "Belt guard.")
    embed(outside, at_angle(0.1))

    rows = nearest(SearchRequest(query=QUESTION, device_ids=(devices[0].pk, other.pk)))

    # One copy per shared content (the one of plc-00), then single contents
    # up to 50 contents; plc-01 takes no place.
    assert [section_id for section_id, _, _ in rows] == [content[0].pk for content in shared] + [
        s.pk for s in single[: VECTOR_CANDIDATES - SHARED_SECTIONS]
    ]
    assert [rank for _, rank, _ in rows] == list(range(1, VECTOR_CANDIDATES + 1))


def test_plant_filter_applies_before_the_contents_are_counted(
    plant: Plant, devices: list[Device]
) -> None:
    add_shared_manual(devices, [f"Belt tension, step {index}." for index in range(SHARED_SECTIONS)])
    other_plant = make_plant("line-b")
    single = add_single_contents(
        make_document(make_device(other_plant, "plc-50"), title="Spare parts"), SINGLE_CONTENTS
    )

    rows = nearest(SearchRequest(query=QUESTION, plant_ids=(other_plant.pk,)))

    assert [section_id for section_id, _, _ in rows] == [s.pk for s in single[:VECTOR_CANDIDATES]]


def test_excluded_contents_take_no_place(devices: list[Device]) -> None:
    add_shared_manual(devices, [f"Belt tension, step {index}." for index in range(SHARED_SECTIONS)])
    single = add_single_contents(make_document(devices[0], title="Spare parts"), SINGLE_CONTENTS)

    rows = nearest(
        SearchRequest(query=f"{QUESTION} -belt"), _Queries(per_config={"simple": "'belt'"})
    )

    assert [section_id for section_id, _, _ in rows] == [s.pk for s in single[:VECTOR_CANDIDATES]]
    assert [rank for _, rank, _ in rows] == list(range(1, VECTOR_CANDIDATES + 1))


def test_copies_of_another_model_or_without_embedding_stay_out(devices: list[Device]) -> None:
    (shared,) = add_shared_manual(devices[:3], ["Belt tension."])
    embed(shared[1], at_angle(0.5), model="other-embed")
    # Since 150 the vector list reads pieces: without an embedding a section
    # has no pieces either (the embed step writes both).
    Section.objects.filter(pk=shared[2].pk).update(embedding=None, embedding_model="")
    SectionPiece.objects.filter(section=shared[2]).delete()

    rows = nearest(SearchRequest(query=QUESTION))

    assert rows == [(shared[0].pk, 1, near(0.5))]


def test_without_copies_the_list_is_the_50_nearest_sections(plant: Plant) -> None:
    single = add_single_contents(make_document(make_device(plant, "plc-01")), SINGLE_CONTENTS)

    rows = nearest(SearchRequest(query=QUESTION))

    assert rows == [
        (s.pk, index + 1, near(10 + index)) for index, s in enumerate(single[:VECTOR_CANDIDATES])
    ]
