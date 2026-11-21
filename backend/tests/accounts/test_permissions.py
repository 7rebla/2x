"""The permission classes CanRead, CanManageOrReadOnly and CanManage (E-40)."""

import pytest
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from tests.accounts.users import KINDS, UserFactory
from twox.accounts.permissions import CanManage, CanManageOrReadOnly, CanRead

READING = ["GET", "HEAD", "OPTIONS"]
WRITING = ["POST", "PUT", "PATCH", "DELETE"]

# Kinds of user that each class lets through, for reading and for writing.
ALLOWED: dict[type[BasePermission], dict[str, set[str]]] = {
    CanRead: {
        "read": {"read", "manage", "superuser"},
        "write": {"read", "manage", "superuser"},
    },
    CanManageOrReadOnly: {
        "read": {"read", "manage", "superuser"},
        "write": {"manage", "superuser"},
    },
    CanManage: {
        "read": {"manage", "superuser"},
        "write": {"manage", "superuser"},
    },
}


class ProbeView(APIView):
    """Answers every method with 200 once the permission check has passed."""

    def get(self, request: Request) -> Response:
        return Response({"probe": "reached"})

    def post(self, request: Request) -> Response:
        return Response({"probe": "reached"})

    def put(self, request: Request) -> Response:
        return Response({"probe": "reached"})

    def patch(self, request: Request) -> Response:
        return Response({"probe": "reached"})

    def delete(self, request: Request) -> Response:
        return Response({"probe": "reached"})


def call(
    permission: type[BasePermission], method: str, user_factory: UserFactory, kind: str
) -> int:
    """Send ``method`` as user ``kind`` to a probe view guarded by ``permission``."""
    request = APIRequestFactory().generic(method, "/api/v1/probe/")
    user = user_factory(kind)
    if user is not None:
        force_authenticate(request, user=user)
    view = ProbeView.as_view(permission_classes=(permission,))
    return view(request).status_code


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("method", READING + WRITING)
@pytest.mark.parametrize("permission", list(ALLOWED), ids=[cls.__name__ for cls in ALLOWED])
def test_permission_matrix(
    user_factory: UserFactory, permission: type[BasePermission], method: str, kind: str
) -> None:
    access = "read" if method in READING else "write"
    expected = 200 if kind in ALLOWED[permission][access] else 403

    assert call(permission, method, user_factory, kind) == expected


def test_signed_in_users_without_role_are_never_let_through() -> None:
    for allowed in ALLOWED.values():
        assert "anonymous" not in allowed["read"] | allowed["write"]
        assert "no_role" not in allowed["read"] | allowed["write"]
