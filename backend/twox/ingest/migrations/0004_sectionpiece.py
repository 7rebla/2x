"""Pieces of sections with embeddings of their own (work order 150, E-75).

Creates the empty table ``ingest_sectionpiece`` with its HNSW index; sections
are not touched. Existing sections get their pieces from the embed step:
``embed_sections --missing`` takes every section without pieces of the
current model (README, "Embedding again"). Going back drops the table.
"""

import django.db.models.deletion
import pgvector.django.indexes
import pgvector.django.vector
from django.db import migrations, models

import twox.ingest.models


class Migration(migrations.Migration):
    dependencies = [
        ("ingest", "0003_ingestjob_conversion_error_count"),
    ]

    operations = [
        migrations.CreateModel(
            name="SectionPiece",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("ordinal", models.PositiveIntegerField(verbose_name="ordinal")),
                ("char_start", models.PositiveIntegerField()),
                ("char_end", models.PositiveIntegerField()),
                (
                    "embedding",
                    pgvector.django.vector.VectorField(
                        dimensions=1024,
                        validators=[twox.ingest.models.validate_embedding_dimensions],
                        verbose_name="embedding",
                    ),
                ),
                (
                    "embedding_model",
                    models.CharField(max_length=200, verbose_name="embedding model"),
                ),
                (
                    "section",
                    models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pieces",
                        to="ingest.section",
                        verbose_name="section",
                    ),
                ),
            ],
            options={
                "ordering": ("section_id", "ordinal"),
                "indexes": [
                    pgvector.django.indexes.HnswIndex(
                        fields=["embedding"],
                        name="ingest_sectionpiece_hnsw",
                        opclasses=["vector_cosine_ops"],
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("section", "ordinal"),
                        name="ingest_sectionpiece_section_ordinal_unique",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("char_end__gte", models.F("char_start"))),
                        name="ingest_sectionpiece_span_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("embedding_model", ""), _negated=True),
                        name="ingest_sectionpiece_has_model",
                    ),
                ],
            },
        ),
    ]
