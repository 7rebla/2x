"""The Django admin below /admin/ admits active superusers only (E-39)."""

import json

import pytest
from django.conf import settings
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


# Since work order 030 the admin has no sign-in form of its own: /admin/login/
# sends the browser to the sign-in page of the web UI (allauth, rate limited).

ALLAUTH_LOGIN_URL = "/_allauth/browser/v1/auth/login"


def is_signed_in(client: Client) -> bool:
    return "_auth_user_id" in client.session


def test_admin_login_redirects_to_the_web_ui_sign_in() -> None:
    response = Client().get("/admin/login/")

    assert response.status_code == 302
    assert response["Location"] == "/login?next=%2Fadmin%2F"


def test_anonymous_admin_request_ends_at_the_web_ui_sign_in() -> None:
    response = Client().get("/admin/accounts/user/", follow=True)

    assert response.redirect_chain[-1] == ("/login?next=%2Fadmin%2Faccounts%2Fuser%2F", 302)


@pytest.mark.parametrize(
    "next_value",
    [
        "https://example.test/admin/",
        "//example.test/admin/",
        "/api/v1/me/",
        "/login",
        "javascript:alert(1)",
        "",
    ],
)
def test_admin_login_passes_only_admin_paths_on(next_value: str) -> None:
    response = Client().get("/admin/login/", {"next": next_value})

    assert response["Location"] == "/login?next=%2Fadmin%2F"


def test_admin_login_keeps_an_admin_path_with_query() -> None:
    response = Client().get("/admin/login/", {"next": "/admin/accounts/user/?q=a&o=1"})

    assert response["Location"] == "/login?next=%2Fadmin%2Faccounts%2Fuser%2F%3Fq%3Da%26o%3D1"


@pytest.mark.parametrize("csrf_checks", [False, True], ids=["no-csrf-check", "csrf-check"])
def test_post_to_the_old_admin_form_signs_nobody_in(csrf_checks: bool) -> None:
    User.objects.create_superuser(username="root", password=TEST_PASSWORD)
    client = Client(enforce_csrf_checks=csrf_checks)

    response = client.post(
        "/admin/login/?next=/admin/", {"username": "root", "password": TEST_PASSWORD}
    )

    assert not is_signed_in(client)
    if csrf_checks:
        assert response.status_code == 403
    else:
        assert response.status_code == 302
        assert response["Location"] == "/login?next=%2Fadmin%2F"
    index = client.get("/admin/")
    assert index.status_code == 302
    assert "2x administration" not in index.content.decode()


def test_superuser_signed_in_through_allauth_reaches_the_admin() -> None:
    User.objects.create_superuser(username="root", password=TEST_PASSWORD)
    client = Client(enforce_csrf_checks=True)
    client.get("/")  # sets the CSRF cookie, as the web UI does
    token = client.cookies[settings.CSRF_COOKIE_NAME].value

    sign_in = client.post(
        ALLAUTH_LOGIN_URL,
        data=json.dumps({"username": "root", "password": TEST_PASSWORD}),
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    index = client.get("/admin/")

    assert sign_in.status_code == 200
    assert index.status_code == 200
    assert "2x administration" in index.content.decode()


def test_signed_in_superuser_at_admin_login_goes_on_to_the_admin() -> None:
    user = User.objects.create_superuser(username="root", password=TEST_PASSWORD)

    response = signed_in_client(user).get("/admin/login/", {"next": "/admin/accounts/user/"})

    assert response.status_code == 302
    assert response["Location"] == "/admin/accounts/user/"


@pytest.mark.parametrize("is_staff", [True, False], ids=["staff", "plain"])
def test_signed_in_user_without_access_gets_403_not_a_sign_in_loop(is_staff: bool) -> None:
    user = User.objects.create_user(username="someone", password=TEST_PASSWORD, is_staff=is_staff)
    client = signed_in_client(user)

    response = client.get("/admin/", follow=True)

    # /admin/ -> /admin/login/ -> 403; never back to the sign-in page.
    assert response.status_code == 403
    assert response.redirect_chain == [("/admin/login/?next=/admin/", 302)]
    assert is_signed_in(client)
