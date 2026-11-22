"""App configuration for twox.ingest."""

from django.apps import AppConfig
from django.core import checks


class IngestConfig(AppConfig):
    name = "twox.ingest"

    def ready(self) -> None:
        """Register the system check of the embedding length (work order 048)."""
        # Imported here: the check reads the models, which load after this module.
        from twox.ingest.checks import check_embedding_dimensions

        checks.register(check_embedding_dimensions)
