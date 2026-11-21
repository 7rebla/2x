"""Sign-in with local accounts through the headless browser API of django-allauth."""

import json
import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import Client
from django.urls import URLPattern, URLResolver, include, path
from pytest_django.fixtures import Settings
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from twox.accounts.models import User
from twox.config.webui import web_index

if TYPE_CHECKING:
    # The response type of the test client; it exists in django-stubs only.
    from django.test.client import _MonkeyPatchedWSGIResponse as TestResponse

BASE = "/_allauth/browser/v1"
LOGIN_URL = f"{BASE}/auth/login"
SESSION_URL = f"{BASE}/auth/session"
SIGNUP_URL = f"{BASE}/auth/signup"
PASSWORD_RESET_URL = f"{BASE}/auth/password/request"
PROBE_URL = "/api/v1/probe/"

USERNAME = "test-operator"
# Test values only; never a real password.
PASSWORD = "test-only-correct-pw-1"
WRONG_PASSWORD = "test-only-wrong-pw-2"

# E-38: the defaults of allauth, set explicitly.
FAILED_PER_ACCOUNT = 5
LOGINS_PER_IP = 30


class ProbeView(APIView):
    """A view that states no permission of its own; it exists only in this test."""

    def get(self, request: Request) -> Response:
        return Response({"probe": "reached", "user": request.user.get_username()})


urlpatterns: list[URLPattern | URLResolver] = [
    path("_allauth/", include("allauth.headless.urls")),
    path("accounts/", include("allauth.urls")),
    path("api/v1/probe/", ProbeView.as_view()),
    # Sets the CSRF cookie, as the web UI does in the browser.
    path("", web_index),
]

pytestmark = [pytest.mark.django_db, pytest.mark.urls(__name__)]


@pytest.fixture(autouse=True)
def fast_password_hasher(settings: Settings) -> Iterator[None]:
    """Hash with MD5 in these tests only: the rate limit tests sign in often."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    yield


@pytest.fixture
def account() -> User:
    return User.objects.create_user(
        username=USERNAME, password=PASSWORD, email="operator@example.test"
    )


def browser() -> Client:
    """Return a client that checks CSRF like a browser and holds the CSRF cookie."""
    client = Client(enforce_csrf_checks=True)
    client.get("/")
    return client


def csrf_token(client: Client) -> str:
    """Return the current CSRF cookie; Django rotates it at every sign-in."""
    return client.cookies[settings.CSRF_COOKIE_NAME].value


def post_json(client: Client, url: str, data: dict[str, str], *, csrf: bool = True) -> TestResponse:
    headers = {"X-CSRFToken": csrf_token(client)} if csrf else {}
    return client.post(url, data=json.dumps(data), content_type="application/json", headers=headers)


def log_in(client: Client, password: str = PASSWORD, username: str = USERNAME) -> TestResponse:
    return post_json(client, LOGIN_URL, {"username": username, "password": password})


def error_codes(response: TestResponse) -> list[str]:
    return [error["code"] for error in response.json().get("errors", [])]


def is_signed_in(client: Client) -> bool:
    return "_auth_user_id" in client.session


def test_login_with_valid_account_opens_a_session(account: User) -> None:
    client = browser()
    assert client.get(PROBE_URL).status_code == 403

    response = log_in(client)

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["is_authenticated"] is True
    assert body["data"]["user"]["username"] == USERNAME
    assert settings.SESSION_COOKIE_NAME in client.cookies
    probe = client.get(PROBE_URL)
    assert probe.status_code == 200
    assert probe.json() == {"probe": "reached", "user": USERNAME}


def test_wrong_password_is_refused_and_logged_without_password(
    account: User, caplog: pytest.LogCaptureFixture
) -> None:
    client = browser()
    caplog.set_level(logging.INFO)

    response = log_in(client, password=WRONG_PASSWORD)

    assert response.status_code == 400
    assert "username_password_mismatch" in error_codes(response)
    assert not is_signed_in(client)
    assert client.get(PROBE_URL).status_code == 403
    failed = [
        record
        for record in caplog.records
        if record.name == "twox.accounts.adapter" and "Failed sign-in" in record.getMessage()
    ]
    assert len(failed) == 1
    assert failed[0].levelno == logging.WARNING
    assert repr(USERNAME) in failed[0].getMessage()
    assert WRONG_PASSWORD not in caplog.text
    assert PASSWORD not in caplog.text


def test_unknown_username_is_logged_like_a_wrong_password(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = browser()
    caplog.set_level(logging.INFO)

    response = log_in(client, username="test-nobody", password=WRONG_PASSWORD)

    assert response.status_code == 400
    assert "username_password_mismatch" in error_codes(response)
    assert "Failed sign-in for username 'test-nobody'." in caplog.messages
    assert WRONG_PASSWORD not in caplog.text


def test_login_without_csrf_token_is_refused(account: User) -> None:
    client = browser()

    response = post_json(
        client, LOGIN_URL, {"username": USERNAME, "password": PASSWORD}, csrf=False
    )

    assert response.status_code == 403
    assert not is_signed_in(client)


def test_too_many_wrong_passwords_block_even_the_right_one(
    account: User, caplog: pytest.LogCaptureFixture
) -> None:
    client = browser()
    for _ in range(FAILED_PER_ACCOUNT):
        assert log_in(client, password=WRONG_PASSWORD).status_code == 400
    caplog.set_level(logging.INFO)

    response = log_in(client)

    # allauth answers a blocked sign-in with 400 and the code
    # too_many_login_attempts, not with 429.
    assert response.status_code == 400
    assert error_codes(response) == ["too_many_login_attempts"]
    assert not is_signed_in(client)
    assert f"Sign-in blocked by the rate limit for username {USERNAME!r}." in caplog.messages
    assert PASSWORD not in caplog.text


def test_failed_sign_ins_count_per_account_across_clients(account: User) -> None:
    # A new client (new session, same address) does not reset the count.
    for _ in range(FAILED_PER_ACCOUNT):
        assert log_in(browser(), password=WRONG_PASSWORD).status_code == 400

    response = log_in(browser())

    assert error_codes(response) == ["too_many_login_attempts"]


def test_one_failure_less_than_the_limit_still_signs_in(account: User) -> None:
    client = browser()
    for _ in range(FAILED_PER_ACCOUNT - 1):
        assert log_in(client, password=WRONG_PASSWORD).status_code == 400

    assert log_in(client).status_code == 200


def test_rate_limit_lives_in_the_django_cache(account: User) -> None:
    client = browser()
    for _ in range(FAILED_PER_ACCOUNT):
        log_in(client, password=WRONG_PASSWORD)
    assert error_codes(log_in(client)) == ["too_many_login_attempts"]

    # The counters are in the default cache (Valkey in operation, shared by
    # all API processes); without them the account is free again.
    cache.clear()

    assert log_in(client).status_code == 200


def test_too_many_sign_in_attempts_from_one_address_get_429() -> None:
    client = browser()
    for _ in range(LOGINS_PER_IP):
        assert log_in(client, username="test-nobody").status_code == 400

    response = log_in(client, username="test-nobody")

    assert response.status_code == 429


def test_session_reports_signed_in_and_signed_out(account: User) -> None:
    client = browser()

    anonymous = client.get(SESSION_URL)
    assert anonymous.status_code == 401
    assert anonymous.json()["meta"]["is_authenticated"] is False

    assert log_in(client).status_code == 200
    signed_in = client.get(SESSION_URL)
    assert signed_in.status_code == 200
    assert signed_in.json()["meta"]["is_authenticated"] is True
    assert signed_in.json()["data"]["user"]["username"] == USERNAME


def test_delete_session_signs_out(account: User) -> None:
    client = browser()
    assert log_in(client).status_code == 200

    response = client.delete(SESSION_URL, headers={"X-CSRFToken": csrf_token(client)})

    assert response.status_code == 401
    assert response.json()["meta"]["is_authenticated"] is False
    assert not is_signed_in(client)
    assert client.get(SESSION_URL).status_code == 401
    assert client.get(PROBE_URL).status_code == 403


def test_delete_session_without_csrf_token_keeps_the_session(account: User) -> None:
    client = browser()
    assert log_in(client).status_code == 200

    response = client.delete(SESSION_URL)

    assert response.status_code == 403
    assert client.get(SESSION_URL).status_code == 200


def test_signup_is_closed() -> None:
    client = browser()

    response = post_json(
        client,
        SIGNUP_URL,
        {"username": "test-newcomer", "password": "test-only-new-pw-3"},
    )

    assert response.status_code == 403
    assert not User.objects.filter(username="test-newcomer").exists()
    config = client.get(f"{BASE}/config").json()
    assert config["data"]["account"]["is_open_for_signup"] is False


@pytest.mark.parametrize("email", ["operator@example.test", "nobody@example.test"])
def test_password_reset_request_sends_no_email(
    account: User, email: str, caplog: pytest.LogCaptureFixture
) -> None:
    client = browser()
    caplog.set_level(logging.INFO)

    response = post_json(client, PASSWORD_RESET_URL, {"email": email})

    # Known and unknown addresses get the same answer; nothing is sent.
    assert response.status_code == 200
    assert mail.outbox == []
    assert "password_reset_url" not in caplog.text


def test_adding_an_email_address_sends_no_email(account: User) -> None:
    client = browser()
    assert log_in(client).status_code == 200

    response = post_json(client, f"{BASE}/account/email", {"email": "second@example.test"})

    assert response.status_code == 200
    assert mail.outbox == []


def test_config_endpoint_answers() -> None:
    response = Client().get(f"{BASE}/config")

    assert response.status_code == 200
    assert response.json()["data"]["account"]["login_methods"] == ["username"]


def test_only_the_browser_client_is_offered() -> None:
    assert Client().get("/_allauth/app/v1/config").status_code == 404


def test_allauth_renders_no_pages_of_its_own() -> None:
    assert Client().get("/accounts/login/").status_code == 404
    assert Client().get("/accounts/signup/").status_code == 404


def test_rate_limits_are_set_explicitly() -> None:
    assert settings.ACCOUNT_RATE_LIMITS == {
        "login_failed": "10/m/ip,5/300s/key",
        "login": "30/m/ip",
    }


def test_authentication_backends() -> None:
    assert settings.AUTHENTICATION_BACKENDS == [
        "django.contrib.auth.backends.ModelBackend",
        "allauth.account.auth_backends.AuthenticationBackend",
    ]


def test_headless_settings() -> None:
    assert settings.HEADLESS_ONLY is True
    assert settings.HEADLESS_CLIENTS == ("browser",)
    assert set(settings.ACCOUNT_LOGIN_METHODS) == {"username"}
    assert settings.ACCOUNT_EMAIL_VERIFICATION == "none"
    assert settings.ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS is False
    assert settings.ACCOUNT_ADAPTER == "twox.accounts.adapter.AccountAdapter"
