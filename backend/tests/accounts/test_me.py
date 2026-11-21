"""GET /api/v1/me/ tells the web UI who is signed in and with which role."""

from io import StringIO
from typing import Any

import pytest
import yaml
from django.core.management import call_command
from rest_framework.test import APIClient

from tests.accounts.users import UserFactory

URL = "/api/v1/me/"


def client_for(user_factory: UserFactory, kind: str) -> APIClient:
    client = APIClient()
    user = user_factory(kind)
    if user is not None:
        client.force_login(user)
    return client


@pytest.mark.django_db
def test_anonymous_request_is_refused() -> None:
    response = APIClient().get(URL)

    assert response.status_code == 403
    assert "username" not in response.json()


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("no_role", {"username": "no_role", "role": None, "is_superuser": False}),
        ("read", {"username": "read", "role": "read", "is_superuser": False}),
        ("manage", {"username": "manage", "role": "manage", "is_superuser": False}),
        ("superuser", {"username": "root", "role": "manage", "is_superuser": True}),
    ],
)
def test_signed_in_user_gets_name_and_role(
    user_factory: UserFactory, kind: str, expected: dict[str, Any]
) -> None:
    response = client_for(user_factory, kind).get(URL)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert response.json() == expected


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_me_is_read_only(user_factory: UserFactory, method: str) -> None:
    response = getattr(client_for(user_factory, "manage"), method)(URL, {}, format="json")

    assert response.status_code == 405


def test_me_is_described_in_the_schema() -> None:
    stdout = StringIO()
    stderr = StringIO()
    call_command("spectacular", "--validate", stdout=stdout, stderr=stderr)
    schema: dict[str, Any] = yaml.safe_load(stdout.getvalue())

    assert stderr.getvalue() == ""
    operation = schema["paths"][URL]["get"]
    assert operation["operationId"] == "me_retrieve"
    assert set(operation["responses"]) == {"200"}
    me = schema["components"]["schemas"]["Me"]
    assert sorted(me["required"]) == ["is_superuser", "role", "username"]
    assert me["properties"]["role"]["nullable"] is True
