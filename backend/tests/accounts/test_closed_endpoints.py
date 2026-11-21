"""Endpoints of the allauth headless API that milestone M1 does not offer (E-38).

Apart from the existence check, these tests use the project's own URL configuration.
"""

import json

import pytest
from django.conf import settings
from django.test import Client
from django.urls import URLResolver, include, path, resolve
from pytest_django.fixtures import Settings

from twox.accounts.models import User

# Paths below /_allauth/<client>/v1/ as registered by allauth 65.22.1.
CLOSED_PATHS = [
    "account/password/change",
    "account/email",
    "auth/password/request",
    "auth/password/reset",
]
CLIENTS = ["browser", "app"]

USERNAME = "test-closed"
# Test value only; never a real password.
PASSWORD = "test-only-closed-pw-1"


# allauth alone, without the project's closures; used only by the existence test.
urlpatterns: list[URLResolver] = [path("_allauth/", include("allauth.headless.urls"))]


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fast_password_hasher(settings: Settings) -> None:
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def account() -> User:
    return User.objects.create_user(username=USERNAME, password=PASSWORD)


@pytest.mark.parametrize("endpoint", CLOSED_PATHS)
def test_closed_path_exists_in_allauth(endpoint: str) -> None:
    # Guards against a renamed path in a later allauth: the closure would then
    # miss it silently.
    match = resolve(f"/_allauth/browser/v1/{endpoint}", urlconf=__name__)
    assert match.func.__module__.startswith("allauth.")


@pytest.mark.parametrize("client_name", CLIENTS)
@pytest.mark.parametrize("endpoint", CLOSED_PATHS)
@pytest.mark.parametrize("signed_in", [False, True], ids=["anonymous", "signed-in"])
def test_closed_path_answers_404(
    account: User, client_name: str, endpoint: str, signed_in: bool
) -> None:
    client = Client()
    if signed_in:
        client.force_login(account)
    url = f"/_allauth/{client_name}/v1/{endpoint}"

    assert client.get(url).status_code == 404
    response = client.post(url, data="{}", content_type="application/json")
    assert response.status_code == 404


def test_sign_in_session_sign_out_and_config_still_work(account: User) -> None:
    client = Client(enforce_csrf_checks=True)
    client.get("/")
    base = "/_allauth/browser/v1"

    assert client.get(f"{base}/config").status_code == 200
    assert client.get(f"{base}/auth/session").status_code == 401

    login = client.post(
        f"{base}/auth/login",
        data=json.dumps({"username": USERNAME, "password": PASSWORD}),
        content_type="application/json",
        headers={"X-CSRFToken": client.cookies[settings.CSRF_COOKIE_NAME].value},
    )
    assert login.status_code == 200
    assert client.get(f"{base}/auth/session").status_code == 200

    logout = client.delete(
        f"{base}/auth/session",
        headers={"X-CSRFToken": client.cookies[settings.CSRF_COOKIE_NAME].value},
    )
    assert logout.status_code == 401
    assert client.get(f"{base}/auth/session").status_code == 401
