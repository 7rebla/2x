"""The project uses its own user model from the first migration on."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser

from twox.accounts.models import User


def test_auth_user_model_is_accounts_user() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model() is User


def test_user_adds_no_fields_to_abstract_user() -> None:
    own = {field.name for field in User._meta.get_fields()}
    inherited = {field.name for field in AbstractUser._meta.get_fields()}

    # The abstract base has no primary key; the concrete model gets the default one.
    assert own - inherited == {"id"}
    assert inherited - own == set()
    assert User._meta.db_table == "accounts_user"


@pytest.mark.django_db
def test_user_can_be_created() -> None:
    created = User.objects.create_user(username="probe", password="test-only")

    loaded = User.objects.get(pk=created.pk)
    assert loaded.username == "probe"
    assert loaded.check_password("test-only")
    assert loaded.is_active
    assert not loaded.is_staff
    assert not loaded.is_superuser
