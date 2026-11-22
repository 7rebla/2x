"""Turn on the PostgreSQL extensions vector (pgvector) and pg_trgm.

Both ship with the database image. pg_trgm is a trusted extension: any role
with CREATE on the database may install it. vector (pgvector 0.8.7) is not
trusted: CREATE EXTENSION vector needs a superuser, which the database user of
the compose setup is. Without a superuser, an administrator has to create the
extension before the first migration. Reversing the migration drops both
extensions again.
"""

from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        VectorExtension(),
        TrigramExtension(),
    ]
