"""Migration ``ingest.0004``: the table of the section pieces (work order 150, E-75).

The migration creates an empty table with its HNSW index; sections and their
embeddings stay exactly as they were. Going back drops the table.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from django.apps.registry import Apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from tests.ingest.fake_converter import isolated_services, make_version, vector_for
from twox.ingest.models import Section, SectionPiece
from twox.ingest.pipeline import needs_embedding

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]

BEFORE = [("ingest", "0003_ingestjob_conversion_error_count")]
AFTER = [("ingest", "0004_sectionpiece")]
TABLE = "ingest_sectionpiece"


def migrate(target: list[tuple[str, str]]) -> Apps:
    """Migrate the test database to ``target``; the models of that state."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(target)
    return executor.loader.project_state(target).apps


@pytest.fixture
def at_0003(isolated_services: Path) -> Iterator[Apps]:
    """The database before the migration; afterwards back at the newest state."""
    try:
        yield migrate(BEFORE)
    finally:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())


def tables() -> set[str]:
    with connection.cursor() as cursor:
        return set(connection.introspection.table_names(cursor))


def section_rows() -> list[tuple[Any, ...]]:
    """Every column of every section, embedding and search vector as text."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, document_version_id, ingest_job_id, ordinal, page_start, page_end,"
            " heading_path, heading_text, text, search_vector::text, embedding::text,"
            " embedding_model, created_at FROM ingest_section ORDER BY id"
        )
        rows: list[tuple[Any, ...]] = cursor.fetchall()
        return rows


def piece_indexes() -> dict[str, str]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = %s", [TABLE])
        return dict(cursor.fetchall())


@pytest.mark.django_db(transaction=True)
def test_forward_keeps_every_section_and_backward_drops_the_table(at_0003: Apps) -> None:
    version = make_version()
    job = at_0003.get_model("ingest", "IngestJob").objects.create(
        document_version_id=version.pk, status="done", step="sections"
    )
    old_section = at_0003.get_model("ingest", "Section")
    for ordinal in range(3):
        old_section.objects.create(
            document_version_id=version.pk,
            ingest_job_id=job.pk,
            ordinal=ordinal,
            page_start=ordinal + 1,
            page_end=ordinal + 1,
            heading_path=["Chapter", f"Part {ordinal}"],
            heading_text=f"Chapter > Part {ordinal}",
            text=f"Text {ordinal} " + "word " * 300,
            embedding=vector_for(ordinal) if ordinal else None,
            embedding_model="bge-m3" if ordinal else "",
        )
    assert TABLE not in tables()
    before = section_rows()

    migrate(AFTER)

    assert section_rows() == before
    assert len(before) == 3
    assert SectionPiece.objects.count() == 0
    indexes = piece_indexes()
    assert "USING hnsw (embedding vector_cosine_ops)" in indexes["ingest_sectionpiece_hnsw"]
    # Until the embed step has run, every section needs embedding again.
    assert Section.objects.filter(needs_embedding("bge-m3")).count() == 3

    migrate(BEFORE)

    assert TABLE not in tables()
    assert section_rows() == before
