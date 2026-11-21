"""The test suite runs against a real PostgreSQL that ships the needed extensions."""

import pytest
from django.db import connection


@pytest.mark.django_db
def test_database_is_postgresql() -> None:
    assert connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        cursor.execute("SELECT version()")
        (version,) = cursor.fetchone()
    assert version.startswith("PostgreSQL ")


@pytest.mark.django_db
def test_vector_and_trigram_extensions_are_available() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM pg_available_extensions WHERE name IN ('vector', 'pg_trgm')"
        )
        available = {row[0] for row in cursor.fetchall()}

    assert available == {"vector", "pg_trgm"}
