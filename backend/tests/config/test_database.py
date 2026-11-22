"""The test suite runs against a real PostgreSQL that ships the needed extensions."""

import math

import pytest
from django.apps import apps
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


@pytest.mark.django_db
def test_vector_and_trigram_extensions_are_installed() -> None:
    # Installed by the migration ingest 0001_extensions, which the test
    # database runs like every other migration.
    with connection.cursor() as cursor:
        cursor.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm')")
        installed = {row[0] for row in cursor.fetchall()}

    assert installed == {"vector", "pg_trgm"}


@pytest.mark.django_db
def test_vector_cosine_distance_returns_a_number() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector")
        (distance,) = cursor.fetchone()

    assert isinstance(distance, float)
    assert 0.0 < distance < 1.0
    expected = 1 - (1 + 4 + 12) / (math.sqrt(14) * math.sqrt(21))
    assert distance == pytest.approx(expected)


@pytest.mark.django_db
def test_trigram_similarity_returns_a_number() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT similarity('abc', 'abd')")
        (similarity,) = cursor.fetchone()

    assert isinstance(similarity, float)
    assert 0.0 < similarity < 1.0


def test_postgres_contrib_app_is_installed() -> None:
    # Needed for TrigramExtension, GinIndex, OpClass and full-text search.
    assert apps.is_installed("django.contrib.postgres")
