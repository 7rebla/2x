"""API basics: health endpoint, default permission and OpenAPI schema."""

from io import StringIO
from typing import Any

import pytest
import yaml
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.urls import URLPattern, path
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from tests.config.expected_paths import ALL_EXPECTED_PATHS
from twox.accounts.models import User
from twox.config.health import HealthView
from twox.config.webui import web_index


class ProbeView(APIView):
    """A view that states no permission of its own; it exists only in this test."""

    def get(self, request: Request) -> Response:
        return Response({"probe": "reached"})

    def post(self, request: Request) -> Response:
        return Response({"probe": "written"})


urlpatterns: list[URLPattern] = [
    path("api/v1/health/", HealthView.as_view()),
    path("api/v1/probe/", ProbeView.as_view()),
    # Sets the CSRF cookie, as the web UI does in the browser.
    path("", web_index),
]


def generate_schema() -> tuple[dict[str, Any], str]:
    """Run ``manage.py spectacular`` and return the parsed schema and stderr."""
    stdout = StringIO()
    stderr = StringIO()
    call_command("spectacular", "--validate", stdout=stdout, stderr=stderr)
    schema: dict[str, Any] = yaml.safe_load(stdout.getvalue())
    return schema, stderr.getvalue()


def test_health_answers_ok_without_credentials() -> None:
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert response.json() == {"status": "ok"}


def test_health_rejects_writes() -> None:
    response = APIClient().post("/api/v1/health/", {}, format="json")

    assert response.status_code == 405


def test_default_authentication_is_the_django_session() -> None:
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == [
        "rest_framework.authentication.SessionAuthentication"
    ]


def test_default_permission_is_is_authenticated() -> None:
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]


@pytest.mark.urls(__name__)
def test_view_without_own_permission_refuses_anonymous_requests() -> None:
    response = APIClient().get("/api/v1/probe/")

    assert response.status_code == 403
    assert "probe" not in response.json()


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_signed_in_session_reaches_view_without_own_permission() -> None:
    client = APIClient()
    client.force_login(User.objects.create_user(username="probe"))

    response = client.get("/api/v1/probe/")

    assert response.status_code == 200
    assert response.json() == {"probe": "reached"}


def signed_in_client_with_csrf_cookie() -> tuple[APIClient, str]:
    """Return a signed-in client that checks CSRF, and its CSRF cookie value."""
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(User.objects.create_user(username="probe"))
    client.get("/")
    return client, client.cookies[settings.CSRF_COOKIE_NAME].value


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_session_write_without_csrf_token_is_refused() -> None:
    client, _ = signed_in_client_with_csrf_cookie()

    response = client.post("/api/v1/probe/", {}, format="json")

    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_session_write_with_csrf_token_is_accepted() -> None:
    client, token = signed_in_client_with_csrf_cookie()

    response = client.post("/api/v1/probe/", {}, format="json", headers={"X-CSRFToken": token})

    assert response.status_code == 200
    assert response.json() == {"probe": "written"}


def test_view_without_own_permission_serves_authenticated_user() -> None:
    request = APIRequestFactory().get("/api/v1/probe/")
    force_authenticate(request, user=User(username="probe"))

    response = ProbeView.as_view()(request)

    assert response.status_code == 200
    assert response.data == {"probe": "reached"}


def test_view_without_own_permission_refuses_anonymous_user_object() -> None:
    request = APIRequestFactory().get("/api/v1/probe/")
    force_authenticate(request, user=AnonymousUser())

    response = ProbeView.as_view()(request)

    assert response.status_code == 403


def test_schema_contains_health_path() -> None:
    schema, stderr = generate_schema()

    assert stderr == ""
    operation = schema["paths"]["/api/v1/health/"]["get"]
    assert operation["operationId"] == "health_retrieve"
    # Public endpoint: besides "no credentials" no security scheme is listed.
    assert operation.get("security", [{}]) == [{}]
    assert schema["components"]["schemas"]["Health"]["required"] == ["status"]


def test_schema_lists_exactly_the_known_paths() -> None:
    schema, _ = generate_schema()

    assert sorted(schema["paths"]) == ALL_EXPECTED_PATHS
