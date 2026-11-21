"""The Django admin below /admin/ admits active superusers only (E-39)."""

import pytest
from django.contrib import admin
from django.test import Client

from twox.accounts.models import User
from twox.config.admin_site import TwoxAdminSite

pytestmark = pytest.mark.django_db

# Long enough for the password validators; only ever used in this test file.
TEST_PASSWORD = "admin-test-only-password"


def signed_in_client(user: User) -> Client:
    """Return a test client with a session for ``user``."""
    client = Client()
    client.force_login(user)
    return client


def test_default_admin_site_is_the_project_site() -> None:
    assert isinstance(admin.site, TwoxAdminSite)


def test_anonymous_request_is_sent_to_the_admin_login() -> None:
    response = Client().get("/admin/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


def test_superuser_gets_the_admin_index() -> None:
    user = User.objects.create_superuser(username="root", password=TEST_PASSWORD)

    response = signed_in_client(user).get("/admin/")

    assert response.status_code == 200
    assert "2x administration" in response.content.decode()


def test_inactive_superuser_gets_no_access() -> None:
    user = User.objects.create_superuser(username="root", password=TEST_PASSWORD, is_active=False)

    response = signed_in_client(user).get("/admin/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


@pytest.mark.parametrize("is_staff", [True, False], ids=["staff", "plain"])
def test_user_without_superuser_flag_gets_no_access(is_staff: bool) -> None:
    user = User.objects.create_user(username="someone", password=TEST_PASSWORD, is_staff=is_staff)
    client = signed_in_client(user)

    index = client.get("/admin/")
    user_list = client.get("/admin/accounts/user/")

    # Redirected to the login page, never the index or a model page.
    assert index.status_code == 302
    assert index["Location"].startswith("/admin/login/")
    assert user_list.status_code in {302, 404}
    assert "2x administration" not in user_list.content.decode()


def test_staff_user_cannot_sign_in_through_the_admin_form() -> None:
    User.objects.create_user(username="staff", password=TEST_PASSWORD, is_staff=True)
    client = Client()

    client.post("/admin/login/", {"username": "staff", "password": TEST_PASSWORD})
    response = client.get("/admin/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


def test_admin_without_trailing_slash_redirects() -> None:
    response = Client().get("/admin")

    assert response.status_code == 301
    assert response["Location"] == "/admin/"
