"""API views of the accounts app."""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from twox.accounts.models import User
from twox.accounts.roles import user_role
from twox.accounts.serializers import Me, MeSerializer


class MeView(APIView):
    """The signed-in user and their role.

    Open to every signed-in user, also without a role, so that the web UI can
    tell such a user why nothing else is available.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(operation_id="me_retrieve", responses=MeSerializer)
    def get(self, request: Request) -> Response:
        user = request.user
        if not isinstance(user, User):
            raise NotAuthenticated
        data: Me = {
            "username": user.get_username(),
            "role": user_role(user),
            "is_superuser": user.is_superuser,
        }
        return Response(MeSerializer(data).data)
