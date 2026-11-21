"""DRF permission classes for the roles "Manage" and "Read" (E-40).

Anonymous requests and signed-in users without a role get 403 from all three
classes. Later work orders use these names; do not rename them.
"""

from typing import TYPE_CHECKING

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from twox.accounts.roles import MANAGE, user_role

if TYPE_CHECKING:
    # Only for the annotations: CanRead is the default permission class in the
    # settings, and rest_framework.views reads that default while it is
    # imported. A runtime import here would be circular.
    from rest_framework.views import APIView


class CanRead(BasePermission):
    """Any method for users with the role ``read`` or ``manage``."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return user_role(request.user) is not None


class CanManageOrReadOnly(BasePermission):
    """Reading methods for ``read`` and ``manage``; writing methods for ``manage`` only."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        role = user_role(request.user)
        if request.method in SAFE_METHODS:
            return role is not None
        return role == MANAGE


class CanManage(BasePermission):
    """Any method, for users with the role ``manage`` only."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return user_role(request.user) == MANAGE
