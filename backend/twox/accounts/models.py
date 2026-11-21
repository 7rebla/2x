"""User model of the project."""

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Unchanged ``AbstractUser``.

    It exists so that ``AUTH_USER_MODEL`` points to a project model from the
    first migration on. Fields and roles are added by later milestones.
    """
