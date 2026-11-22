"""Migration ``ingest.0003``: the count of conversion errors from the old note (work order 068).

Before E-62 a partial conversion was recognised by ``error_detail`` starting
with ``converted with ``. The migration adds ``conversion_error_count`` and
fills it from that text; every other job keeps 0. Going back drops the field
and leaves ``error_detail`` as it is.
"""

import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.apps.registry import Apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from tests.ingest.fake_converter import isolated_services, make_version
from twox.files.models import DocumentVersion
from twox.ingest.models import IngestJob

# Imported for its side effect: pytest finds the fixture in this module.
__all__ = ["isolated_services"]

MIGRATION = importlib.import_module("twox.ingest.migrations.0003_ingestjob_conversion_error_count")
BEFORE = [("ingest", "0002_ingest_job_section")]
AFTER = [("ingest", "0003_ingestjob_conversion_error_count")]

#: error_detail before the migration, and the count it must give.
OLD_JOBS = [
    ("converted with 2 errors on pages 3, 7", "done", 2),
    ("converted with 1 errors", "done", 1),
    # Docling listed no error; the job was marked as partly converted all the same.
    ("converted with 0 errors", "done", 1),
    # An embedding job of embed_sections (061) carried the note while queued.
    ("converted with 4 errors on pages 1", "queued", 4),
    ("", "done", 0),
    ("docling-serve refused the connection (gave up after 5 retries)", "failed", 0),
    ("the conversion ended with status failure: converted with 9 errors", "failed", 0),
]


def migrate(target: list[tuple[str, str]]) -> Apps:
    """Migrate the test database to ``target``; the models of that state."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(target)
    return executor.loader.project_state(target).apps


@pytest.fixture
def at_0002(isolated_services: Path) -> Iterator[Apps]:
    """The database before the migration; afterwards back at the newest state."""
    try:
        yield migrate(BEFORE)
    finally:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())


def ingest_column_names() -> set[str]:
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, "ingest_ingestjob")
    return {column.name for column in description}


def old_job(apps: Apps, version: DocumentVersion, index: int) -> int:
    """Job number ``index`` of :data:`OLD_JOBS` for ``version``, with the old models."""
    detail, status, _count = OLD_JOBS[index]
    job = apps.get_model("ingest", "IngestJob").objects.create(
        document_version_id=version.pk, status=status, error_detail=detail
    )
    pk: int = job.pk
    return pk


@pytest.mark.django_db(transaction=True)
def test_forward_takes_the_count_from_the_note_and_backward_drops_it(at_0002: Apps) -> None:
    # One version per job: at most one queued job per version.
    versions = [
        make_version(f"content {n}".encode(), device=f"dev-{n}") for n in range(len(OLD_JOBS))
    ]
    pks = [old_job(at_0002, version, index) for index, version in enumerate(versions)]
    assert "conversion_error_count" not in ingest_column_names()
    updated_before = dict(IngestJob.objects.filter(pk__in=pks).values_list("pk", "updated_at"))

    migrate(AFTER)

    jobs = {job.pk: job for job in IngestJob.objects.filter(pk__in=pks)}
    for pk, (detail, _status, count) in zip(pks, OLD_JOBS, strict=True):
        assert (jobs[pk].conversion_error_count, jobs[pk].error_detail) == (count, detail)
        assert jobs[pk].updated_at == updated_before[pk]

    migrate(BEFORE)

    assert "conversion_error_count" not in ingest_column_names()
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, error_detail FROM ingest_ingestjob ORDER BY id")
        rows = cursor.fetchall()
    assert rows == [(pk, detail) for pk, (detail, _s, _c) in zip(pks, OLD_JOBS, strict=True)]


@pytest.mark.django_db(transaction=True)
def test_forward_without_any_note_leaves_every_count_at_zero(at_0002: Apps) -> None:
    version = make_version()
    job_model = at_0002.get_model("ingest", "IngestJob")
    job_model.objects.create(document_version_id=version.pk, status="done")
    job_model.objects.create(
        document_version_id=version.pk,
        status="failed",
        error_detail="the stored content is missing",
    )

    migrate(AFTER)

    assert list(IngestJob.objects.values_list("conversion_error_count", flat=True)) == [0, 0]


@pytest.mark.parametrize(
    ("detail", "count"),
    [
        ("", 0),
        ("docling-serve refused the connection", 0),
        ("Converted with 2 errors", 0),
        ("converted with 2 errors on pages 3, 7", 2),
        ("converted with 0 errors", 1),
        ("converted with errors: page 3", 1),
        ("converted with 99999999999 errors", 2_147_483_647),
    ],
)
def test_count_from_the_note(detail: str, count: int) -> None:
    assert MIGRATION.error_count_from_detail(detail) == count
