"""API basics: health endpoint, default permission and OpenAPI schema."""

import re
from collections.abc import Callable, Iterable, Iterator
from io import StringIO
from typing import Any

import pytest
import yaml
from django.conf import settings
from django.core.management import call_command
from django.http import HttpRequest, HttpResponse
from django.urls import (
    Resolver404,
    URLPattern,
    URLResolver,
    get_resolver,
    path,
    re_path,
    resolve,
)
from django.urls.resolvers import RegexPattern, RoutePattern
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from tests.accounts.users import make_user
from tests.config.expected_paths import ALL_EXPECTED_PATHS
from twox.config.health import HealthView
from twox.config.webui import web_index

API_PREFIX = "/api/v1/"

# The only exceptions to "every endpoint needs a role" (E-40). A new entry
# needs a reason in the short report of its work order; the Leitstelle decides.
#
# Open to anonymous requests:
# - health: container health checks carry no credentials.
# - selftest: data source of the test page; restricted by work order 027.
OPEN_PATHS = frozenset({"/api/v1/health/", "/api/v1/selftest/"})
# Open to signed-in users without a role:
# - me: the web UI tells such a user why nothing else is available.
ROLELESS_PATHS = frozenset({"/api/v1/me/"})

# Values that fill the placeholders of a URL pattern; the first one that
# matches the placeholder's regular expression is used.
PLACEHOLDER_VALUES = ("1", "00000000-0000-4000-8000-000000000001", "x")
# DRF format suffixes (format_suffix_patterns, routers): a known format, so
# that content negotiation does not answer 404 before the permission check.
FORMAT_VALUES = ("json", ".json")

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_ROUTE_PLACEHOLDER = re.compile(r"<(?:[^>:]+:)?(?P<name>[^>]+)>")
_REGEX_GROUP = re.compile(r"\(\?P<(?P<name>\w+)>(?P<regex>[^()]*)\)")
_REGEX_SPECIAL = re.compile(r"[\\.^$*+?()\[\]{}|]")


class ProbeView(APIView):
    """A view that states no permission of its own; it exists only in this test."""

    def get(self, request: Request) -> Response:
        return Response({"probe": "reached"})

    def post(self, request: Request) -> Response:
        return Response({"probe": "written"})


class LeakyView(APIView):
    """A view open to every signed-in user; the path check must report it."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, **kwargs: str) -> Response:
        return Response({"leaky": "reached"})


def plain_django_view(request: HttpRequest) -> HttpResponse:
    """Not a DRF view: DRF permissions never run, the path check must report it."""
    return HttpResponse("plain")


urlpatterns: list[URLPattern] = [
    path("api/v1/health/", HealthView.as_view()),
    path("api/v1/probe/", ProbeView.as_view()),
    path("api/v1/leaky/<int:pk>/", LeakyView.as_view()),
    re_path(r"^api/v1/leaky-regex/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$", LeakyView.as_view()),
    path("api/v1/plain/", plain_django_view),
    # Sets the CSRF cookie, as the web UI does in the browser.
    path("", web_index),
]


def placeholder_value(name: str, regex: str) -> str:
    """Return a value for the placeholder ``name`` that matches ``regex``."""
    candidates = FORMAT_VALUES if name == "format" else PLACEHOLDER_VALUES
    for candidate in candidates:
        if re.fullmatch(regex, candidate):
            return candidate
    raise ValueError(f"no value for placeholder {name!r} ({regex}); extend PLACEHOLDER_VALUES")


def literal_start(pattern: RoutePattern | RegexPattern) -> str:
    """Return the fixed text at the start of ``pattern``, before any placeholder."""
    if isinstance(pattern, RoutePattern):
        return str(pattern).split("<", 1)[0]
    text = str(pattern).removeprefix("^")
    return _REGEX_SPECIAL.split(text, maxsplit=1)[0]


def fill_pattern(pattern: RoutePattern | RegexPattern) -> str:
    """Return ``pattern`` as a concrete path segment, placeholders filled."""
    if isinstance(pattern, RoutePattern):
        return _ROUTE_PLACEHOLDER.sub(
            lambda match: placeholder_value(match["name"], pattern.converters[match["name"]].regex),
            str(pattern),
        )
    text = str(pattern).removeprefix("^").removesuffix("$").removesuffix(r"\Z")
    text = _REGEX_GROUP.sub(lambda match: placeholder_value(match["name"], match["regex"]), text)
    return text.replace("/?", "/").replace(r"\.", ".")


def could_lead_to_api(path_so_far: str) -> bool:
    return path_so_far.startswith(API_PREFIX) or API_PREFIX.startswith(path_so_far)


def walk_api_patterns(
    entries: Iterable[URLPattern | URLResolver], prefix: str
) -> Iterator[tuple[str, URLPattern]]:
    """Yield ``(path, pattern)`` for every URL pattern below ``API_PREFIX``."""
    for entry in entries:
        pattern = entry.pattern
        if not isinstance(pattern, RoutePattern | RegexPattern):
            raise TypeError(f"unknown kind of URL pattern below {prefix}: {pattern!r}")
        if not could_lead_to_api(prefix + literal_start(pattern)):
            continue
        full = prefix + fill_pattern(pattern)
        if isinstance(entry, URLResolver):
            yield from walk_api_patterns(entry.url_patterns, full)
        elif full.startswith(API_PREFIX):
            yield full, entry


def api_endpoints() -> list[tuple[str, Callable[..., Any]]]:
    """Every path below ``/api/v1/`` in the active URL configuration, with its view.

    The paths come from the URL resolver, not from the OpenAPI schema, so that
    views missing from the schema are found as well.
    """
    endpoints = []
    for full, pattern in walk_api_patterns(get_resolver().url_patterns, "/"):
        try:
            match = resolve(full)
        except Resolver404:
            match = None
        if match is None or match.func is not pattern.callback:
            raise AssertionError(
                f"{full} does not resolve to the view of {pattern!r}; extend fill_pattern"
            )
        endpoints.append((full, pattern.callback))
    return endpoints


def allowed_methods(view: Callable[..., Any]) -> list[str]:
    """The HTTP methods a DRF view function answers, HEAD and OPTIONS included."""
    view_class: type[APIView] = getattr(view, "cls")  # noqa: B009
    actions: dict[str, str] | None = getattr(view, "actions", None)
    if actions is not None:
        methods = {method.upper() for method in actions} | {"OPTIONS"}
    else:
        methods = {
            method.upper() for method in view_class.http_method_names if hasattr(view_class, method)
        }
    if "GET" in methods:
        methods.add("HEAD")
    return sorted(methods)


def is_drf_view(view: Callable[..., Any]) -> bool:
    view_class = getattr(view, "cls", None)
    return isinstance(view_class, type) and issubclass(view_class, APIView)


def paths_open_to(client: APIClient, exempt: frozenset[str]) -> list[str]:
    """Call every API path with every method; list each answer that is not 403.

    Paths in ``exempt`` are not called. A view that is not a DRF view is listed
    as well: DRF permissions would never run for it.
    """
    findings = []
    for full, view in api_endpoints():
        if full in exempt:
            continue
        if not is_drf_view(view):
            findings.append(f"{full}: not a DRF view")
            continue
        for method in allowed_methods(view):
            data = "{}" if method in WRITE_METHODS else ""
            response = client.generic(method, full, data, content_type="application/json")
            if response.status_code != 403:
                findings.append(f"{method} {full}: {response.status_code}")
    return findings


def client_for(kind: str) -> APIClient:
    """An API client signed in as a user of ``kind`` (see tests.accounts.users)."""
    client = APIClient()
    user = make_user(kind)
    if user is not None:
        client.force_login(user)
    return client


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


@pytest.mark.urls(__name__)
def test_view_without_own_permission_refuses_anonymous_requests() -> None:
    response = APIClient().get("/api/v1/probe/")

    assert response.status_code == 403
    assert "probe" not in response.json()


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_view_without_own_permission_refuses_signed_in_user_without_role() -> None:
    response = client_for("no_role").get("/api/v1/probe/")

    assert response.status_code == 403
    assert "probe" not in response.json()


@pytest.mark.django_db
@pytest.mark.urls(__name__)
@pytest.mark.parametrize("kind", ["read", "manage", "superuser"])
def test_signed_in_session_with_role_reaches_view_without_own_permission(kind: str) -> None:
    response = client_for(kind).get("/api/v1/probe/")

    assert response.status_code == 200
    assert response.json() == {"probe": "reached"}


def signed_in_client_with_csrf_cookie() -> tuple[APIClient, str]:
    """Return a client signed in with the role read that checks CSRF, and its CSRF cookie."""
    client = APIClient(enforce_csrf_checks=True)
    reader = make_user("read")
    assert reader is not None
    client.force_login(reader)
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


@pytest.mark.django_db
@pytest.mark.parametrize(("kind", "status"), [("anonymous", 403), ("no_role", 403), ("read", 200)])
def test_view_without_own_permission_needs_a_role(kind: str, status: int) -> None:
    request = APIRequestFactory().get("/api/v1/probe/")
    force_authenticate(request, user=make_user(kind))

    response = ProbeView.as_view()(request)

    assert response.status_code == status


@pytest.mark.django_db
def test_no_api_path_is_open_to_anonymous_requests() -> None:
    assert paths_open_to(client_for("anonymous"), exempt=OPEN_PATHS) == []


@pytest.mark.django_db
def test_no_api_path_is_open_to_signed_in_users_without_role() -> None:
    assert paths_open_to(client_for("no_role"), exempt=OPEN_PATHS | ROLELESS_PATHS) == []


def test_every_exception_names_an_existing_api_path() -> None:
    found = {full for full, _ in api_endpoints()}

    assert found >= OPEN_PATHS | ROLELESS_PATHS
    assert not OPEN_PATHS & ROLELESS_PATHS


def test_path_check_finds_every_path_without_placeholder_in_the_schema() -> None:
    found = {full for full, _ in api_endpoints()}

    assert {schema_path for schema_path in ALL_EXPECTED_PATHS if "{" not in schema_path} <= found


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_path_check_reports_views_open_without_role() -> None:
    # The probe without own permission is closed by the default class; the
    # leaky views and the plain Django view are reported.
    assert paths_open_to(client_for("no_role"), exempt=OPEN_PATHS) == [
        "GET /api/v1/leaky/1/: 200",
        "HEAD /api/v1/leaky/1/: 200",
        "OPTIONS /api/v1/leaky/1/: 200",
        "GET /api/v1/leaky-regex/1.json/: 200",
        "HEAD /api/v1/leaky-regex/1.json/: 200",
        "OPTIONS /api/v1/leaky-regex/1.json/: 200",
        "/api/v1/plain/: not a DRF view",
    ]


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_path_check_reports_views_open_to_anonymous_requests() -> None:
    assert paths_open_to(client_for("anonymous"), exempt=frozenset()) == [
        "GET /api/v1/health/: 200",
        "HEAD /api/v1/health/: 200",
        "OPTIONS /api/v1/health/: 200",
        "/api/v1/plain/: not a DRF view",
    ]


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
