"""API views of the accounts app."""

from typing import Any

from auditlog.models import LogEntry
from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, serializers
from rest_framework.exceptions import NotAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from twox.accounts.models import User
from twox.accounts.permissions import CanManage
from twox.accounts.roles import user_role
from twox.accounts.serializers import (
    AUDIT_ACTIONS,
    AuditLogEntrySerializer,
    Me,
    MeSerializer,
)

# Largest value of a bigint column; larger object ids cannot exist.
MAX_ID = 2**63 - 1


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


class AuditLogPagination(PageNumberPagination):
    """Fixed pages of 50 entries; the client cannot choose another size."""

    page_size = 50


def query_value[T](
    request: Request, name: str, field: serializers.Field[T, Any, Any, Any]
) -> T | None:
    """Return the query parameter ``name`` checked by ``field``, or ``None`` if not given.

    A value that ``field`` rejects gives 400 with an error at ``name``.
    """
    raw = request.query_params.get(name)
    if raw is None:
        return None
    try:
        value: T = field.run_validation(raw)
    except serializers.ValidationError as error:
        raise serializers.ValidationError({name: error.detail}) from error
    return value


@extend_schema_view(
    get=extend_schema(
        operation_id="audit_log_list",
        parameters=[
            OpenApiParameter(
                "object_type",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Only entries of this kind of object, for example assets.device.",
            ),
            OpenApiParameter(
                "object_id",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Only entries of the object with this id (use with object_type).",
            ),
            OpenApiParameter(
                "actor",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Only entries of the user with this user name.",
            ),
        ],
    ),
)
class AuditLogView(generics.ListAPIView[LogEntry]):
    """The change log: who changed what and when, newest first (E-43).

    For the role "Manage" only. Read-only: there is no way to change or
    delete entries through the API.
    """

    permission_classes = (CanManage,)
    serializer_class = AuditLogEntrySerializer
    pagination_class = AuditLogPagination

    def get_queryset(self) -> QuerySet[LogEntry]:
        queryset = (
            LogEntry.objects.filter(action__in=list(AUDIT_ACTIONS))
            .select_related("actor", "content_type")
            .order_by("-timestamp", "-pk")
        )
        object_type = query_value(
            self.request,
            "object_type",
            serializers.RegexField(r"^[a-z0-9_]+\.[a-z0-9_]+$", max_length=201),
        )
        if object_type is not None:
            app_label, model = object_type.split(".")
            queryset = queryset.filter(content_type__app_label=app_label, content_type__model=model)
        object_id = query_value(
            self.request, "object_id", serializers.IntegerField(min_value=1, max_value=MAX_ID)
        )
        if object_id is not None:
            queryset = queryset.filter(object_id=object_id)
        actor = query_value(self.request, "actor", serializers.CharField(max_length=150))
        if actor is not None:
            queryset = queryset.filter(actor__username=actor)
        return queryset
