"""A field of its own for partial conversions (E-62, work order 068).

Until now a job that Docling converted only in part (``partial_success``) was
recognised by the start of its ``error_detail``: ``converted with <n> errors``
(work orders 046, 048, 051, 061). This migration adds
``conversion_error_count`` and fills it from that text: the number in it, at
least 1, so that every job marked as partly converted before stays marked
(Docling may report ``partial_success`` without listing an error). Every other
job keeps the default 0. The text stays in ``error_detail`` for people.

The prefix and the pattern are fixed here on purpose and not imported: a
migration must keep doing what it did when it was written. Going back drops
the column; the notes in ``error_detail`` are left as they are.
"""

import re
from collections import defaultdict

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

#: Start of the note on a partial conversion before this migration.
PARTIAL_DETAIL_PREFIX = "converted with "
#: The number of errors right after the prefix.
ERROR_COUNT_RE = re.compile(r"converted with (\d+) errors")
#: Largest value of a PositiveIntegerField in PostgreSQL.
MAX_COUNT = 2_147_483_647
BATCH_SIZE = 500


def error_count_from_detail(detail: str) -> int:
    """The number of conversion errors that a note in ``error_detail`` names.

    0 for any text that is not such a note; at least 1 for a note, also for
    ``converted with 0 errors`` and for a note without a readable number.
    """
    if not detail.startswith(PARTIAL_DETAIL_PREFIX):
        return 0
    match = ERROR_COUNT_RE.match(detail)
    if match is None:
        return 1
    return min(max(int(match.group(1)), 1), MAX_COUNT)


def fill_conversion_error_count(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Set the count of every job whose ``error_detail`` is a partial-conversion note.

    One ``UPDATE`` per distinct count; ``updated_at`` stays as it was.
    """
    job_model = apps.get_model("ingest", "IngestJob")
    notes = job_model.objects.filter(error_detail__startswith=PARTIAL_DETAIL_PREFIX).values_list(
        "pk", "error_detail"
    )
    by_count: dict[int, list[int]] = defaultdict(list)
    for pk, detail in notes.iterator(chunk_size=BATCH_SIZE):
        by_count[error_count_from_detail(detail)].append(pk)
    for count, pks in by_count.items():
        for start in range(0, len(pks), BATCH_SIZE):
            job_model.objects.filter(pk__in=pks[start : start + BATCH_SIZE]).update(
                conversion_error_count=count
            )


class Migration(migrations.Migration):
    dependencies = [
        ("ingest", "0002_ingest_job_section"),
    ]

    operations = [
        migrations.AddField(
            model_name="ingestjob",
            name="conversion_error_count",
            field=models.PositiveIntegerField(default=0, verbose_name="conversion errors"),
        ),
        migrations.RunPython(fill_conversion_error_count, migrations.RunPython.noop),
    ]
