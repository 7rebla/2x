"""Accounts and role groups are managed in the admin, by superusers only."""

import pytest
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.test import Client

from tests.accounts.users import UserFactory
from twox.accounts.models import User


def test_user_model_is_registered_with_user_admin() -> None:
    assert isinstance(admin.site.get_model_admin(User), UserAdmin)


@pytest.mark.parametrize(
    "path", ["/admin/accounts/user/", "/admin/accounts/user/add/", "/admin/auth/group/"]
)
def test_superuser_reaches_user_and_group_pages(user_factory: UserFactory, path: str) -> None:
    client = Client()
    superuser = user_factory("superuser")
    assert superuser is not None
    client.force_login(superuser)

    response = client.get(path)

    assert response.status_code == 200


@pytest.mark.parametrize("kind", ["no_role", "read", "manage"])
def test_role_does_not_open_the_admin(user_factory: UserFactory, kind: str) -> None:
    client = Client()
    user = user_factory(kind)
    assert user is not None
    client.force_login(user)

    response = client.get("/admin/accounts/user/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")
