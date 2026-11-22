"""System check of the ingestion: the embedding length must fit the vector column.

``TWOX_EMBED_DIMENSIONS`` (work order 044) names the length of the vectors the
model gives; the column ``Section.embedding`` has a fixed length (042). If
they differ, every write of an embedding fails in the database. The check
reports this once at start instead: ``manage.py check``, ``migrate`` and every
other management command stop with a clear message.

With the AI features off (E-59) nothing is embedded; then a difference is
only a warning, so that the product still starts without them.

Registered in :meth:`twox.ingest.apps.IngestConfig.ready`.
"""

from collections.abc import Sequence

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import CheckMessage, Error
from django.core.checks import Warning as CheckWarning
from pgvector.django import VectorField

from twox.ingest.models import Section

#: ID of the check message with the AI features on (an error) and off (a warning).
DIMENSION_ERROR_ID = "twox.ingest.E001"
DIMENSION_WARNING_ID = "twox.ingest.W001"


def embedding_column_dimensions() -> int:
    """The length of the vector column ``Section.embedding``."""
    field = Section._meta.get_field("embedding")
    if not isinstance(field, VectorField) or field.dimensions is None:
        raise TypeError("Section.embedding must be a vector column with a fixed length")
    return field.dimensions


def embedding_dimension_problem() -> str | None:
    """A clear message if ``TWOX_EMBED_DIMENSIONS`` does not fit the column, else ``None``."""
    configured: int = settings.TWOX_EMBED_DIMENSIONS
    column = embedding_column_dimensions()
    if configured == column:
        return None
    return (
        f"TWOX_EMBED_DIMENSIONS is {configured}, but the embedding column of the sections"
        f" has {column} dimensions; no embedding could be stored"
    )


def check_embedding_dimensions(
    app_configs: Sequence[AppConfig] | None = None, **kwargs: object
) -> list[CheckMessage]:
    """Report a difference between ``TWOX_EMBED_DIMENSIONS`` and the vector column."""
    problem = embedding_dimension_problem()
    if problem is None:
        return []
    column = embedding_column_dimensions()
    hint = (
        f"Set TWOX_EMBED_DIMENSIONS={column} and use an embedding model with {column}"
        " dimensions (bge-m3, E-56)."
    )
    if settings.TWOX_AI_ENABLED:
        return [Error(problem, hint=hint, id=DIMENSION_ERROR_ID)]
    return [
        CheckWarning(
            f"{problem} (AI features are off, so nothing is embedded now)",
            hint=hint,
            id=DIMENSION_WARNING_ID,
        )
    ]
