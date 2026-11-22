"""Paths the OpenAPI schema is expected to list, one module per app.

A work order that adds or removes endpoints changes only the module of its
app. The schema test compares with the union of all lists.
"""

from tests.config.expected_paths import accounts, answers, assets, config, files, ingest, search

ALL_EXPECTED_PATHS: list[str] = sorted(
    [
        *answers.EXPECTED_PATHS,
        *config.EXPECTED_PATHS,
        *accounts.EXPECTED_PATHS,
        *assets.EXPECTED_PATHS,
        *files.EXPECTED_PATHS,
        *ingest.EXPECTED_PATHS,
        *search.EXPECTED_PATHS,
    ]
)
