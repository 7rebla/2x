"""API of the ingestion: list the ingest jobs, start ingesting a version again (work order 051).

- ``GET /api/v1/ingest-jobs/`` lists every ingest job, newest first, 50 per
  page, with document, version and device. Both roles read it (``CanRead``).
- ``POST /api/v1/document-versions/{version_id}/ingest/`` starts a new job for
  one version through :func:`twox.ingest.services.request_ingest`; only the
  role ``manage`` may (``CanManage``, E-40). 409 while the version has a
  queued or running job, 400 for a configuration.

The state of the newest job of each version also comes with the files API
(field ``ingest`` of a version, :mod:`twox.files.serializers`).

Who started a job (``requested_by``) is shown to the role ``manage`` only,
like the change log (E-43); the role ``read`` always gets ``null``. The
cleaned technical text ``error_detail`` is shown to both roles (E-57).

The API works the same with the AI features switched off (E-59): no field
here depends on embeddings, and nothing here calls the model service.
"""

from typing import Any, Final

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from twox.accounts.models import User
from twox.accounts.permissions import CanManage, CanRead
from twox.accounts.roles import MANAGE, user_role
from twox.assets.models import Device
from twox.assets.views import id_parameter, query_id
from twox.files.models import Document, DocumentVersion
from twox.files.serializers import ErrorDetailSerializer, IngestJobSummarySerializer
from twox.ingest.models import IngestJob, IngestStatus
from twox.ingest.services import IngestAlreadyActiveError, IngestNotAllowedError, request_ingest

#: Context key of :class:`IngestJobSerializer`: show the user name in ``requested_by``.
SHOW_REQUESTED_BY: Final = "show_requested_by"

#: ``code`` of the answers 409 and 400 of the ingest endpoint.
CODE_INGEST_ACTIVE: Final = "ingest_active"
CODE_CONFIGURATION: Final = "configuration_not_ingested"

_ERROR_403 = OpenApiResponse(ErrorDetailSerializer, description="No role, or not allowed.")
_ERROR_404 = OpenApiResponse(ErrorDetailSerializer, description="Not found.")


class IngestJobDocumentSerializer(serializers.ModelSerializer[Document]):
    """The document of an ingest job."""

    class Meta:
        model = Document
        fields: tuple[str, ...] = ("id", "title")
        read_only_fields = fields


class IngestJobVersionSerializer(serializers.ModelSerializer[DocumentVersion]):
    """The document version of an ingest job."""

    class Meta:
        model = DocumentVersion
        fields: tuple[str, ...] = ("id", "number", "original_filename")
        read_only_fields = fields


class IngestJobDeviceSerializer(serializers.ModelSerializer[Device]):
    """The device the document of an ingest job belongs to."""

    class Meta:
        model = Device
        fields: tuple[str, ...] = ("id", "key", "name")
        read_only_fields = fields


class IngestJobSerializer(IngestJobSummarySerializer):
    """An ingest job with its document, version and device.

    ``requested_by`` is the user name only when the context says so
    (:data:`SHOW_REQUESTED_BY`, the role ``manage``); otherwise ``null``.
    """

    document = IngestJobDocumentSerializer(source="document_version.document", read_only=True)
    version = IngestJobVersionSerializer(source="document_version", read_only=True)
    device = IngestJobDeviceSerializer(source="document_version.document.device", read_only=True)
    requested_by = serializers.SerializerMethodField(
        help_text=(
            "User name of the user who started the job; null for the system, "
            "and always null for the role read."
        )
    )

    class Meta(IngestJobSummarySerializer.Meta):
        fields = (
            *IngestJobSummarySerializer.Meta.fields,
            "document",
            "version",
            "device",
            "requested_by",
        )
        read_only_fields = fields

    def get_requested_by(self, job: IngestJob) -> str | None:
        if not self.context.get(SHOW_REQUESTED_BY, False) or job.requested_by is None:
            return None
        return job.requested_by.get_username()


class IngestRequestErrorSerializer(serializers.Serializer[Any]):
    """400: the version cannot be ingested (a configuration)."""

    detail = serializers.CharField()
    code = serializers.CharField()


class IngestConflictSerializer(serializers.Serializer[Any]):
    """409: the version has a queued or running ingest job already."""

    detail = serializers.CharField()
    code = serializers.CharField()
    job = IngestJobSummarySerializer(help_text="The queued or running job.")


class IngestJobPagination(PageNumberPagination):
    """Fixed pages of 50 jobs; the client cannot choose another size."""

    page_size = 50


def ingest_jobs() -> QuerySet[IngestJob]:
    """All ingest jobs, newest first, with document, device and requester in the same query."""
    return IngestJob.objects.select_related(
        "document_version__document__device", "requested_by"
    ).order_by("-created_at", "-pk")


def shows_requested_by(request: Request) -> bool:
    """Whether the user may see who started a job: the role ``manage`` only (E-43, E-57)."""
    return user_role(request.user) == MANAGE


def query_statuses(request: Request) -> list[str]:
    """The values of the repeatable query parameter ``status``; 400 for an unknown one."""
    field = serializers.ChoiceField(choices=IngestStatus.choices)
    values = []
    for raw in request.query_params.getlist("status"):
        try:
            values.append(field.run_validation(raw))
        except serializers.ValidationError as error:
            raise serializers.ValidationError({"status": error.detail}) from error
    return values


@extend_schema_view(
    get=extend_schema(
        operation_id="ingest_jobs_list",
        parameters=[
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                many=True,
                explode=True,
                enum=IngestStatus.values,
                description="Only jobs in one of these states; repeat the parameter for more.",
            ),
            id_parameter("device", "Only jobs of documents of the device with this id."),
            id_parameter("document", "Only jobs of the document with this id."),
            id_parameter("version", "Only jobs of the document version with this id."),
        ],
        responses={
            200: IngestJobSerializer(many=True),
            400: OpenApiResponse(description="Invalid filter value."),
            403: _ERROR_403,
        },
    ),
)
class IngestJobListView(generics.ListAPIView[IngestJob]):
    """Every ingest job, newest first, 50 per page.

    For both roles. ``requested_by`` names the user for the role ``manage``
    only and is ``null`` for the role ``read``.
    """

    permission_classes = (CanRead,)
    serializer_class = IngestJobSerializer
    pagination_class = IngestJobPagination

    def get_queryset(self) -> QuerySet[IngestJob]:
        queryset = ingest_jobs()
        statuses = query_statuses(self.request)
        if statuses:
            queryset = queryset.filter(status__in=statuses)
        device = query_id(self.request, "device")
        if device is not None:
            queryset = queryset.filter(document_version__document__device_id=device)
        document = query_id(self.request, "document")
        if document is not None:
            queryset = queryset.filter(document_version__document_id=document)
        version = query_id(self.request, "version")
        if version is not None:
            queryset = queryset.filter(document_version_id=version)
        return queryset

    def get_serializer_context(self) -> dict[str, Any]:
        return {
            **super().get_serializer_context(),
            SHOW_REQUESTED_BY: shows_requested_by(self.request),
        }


class VersionIngestView(APIView):
    """Start ingesting one document version again."""

    permission_classes = (CanManage,)

    @extend_schema(
        operation_id="document_version_ingest",
        request=None,
        responses={
            202: IngestJobSerializer,
            400: OpenApiResponse(
                IngestRequestErrorSerializer,
                description="The version belongs to a configuration, which is not ingested.",
            ),
            403: _ERROR_403,
            404: _ERROR_404,
            409: OpenApiResponse(
                IngestConflictSerializer,
                description="The version has a queued or running ingest job already.",
            ),
        },
    )
    def post(self, request: Request, version_id: int) -> Response:
        """Create a new ingest job for the version; the requester is the signed-in user.

        A file outside the ingested formats gets a job that is ``skipped`` at
        once, missing content a ``failed`` one (``content_missing``); both
        answer 202 as well. A queued job is sent to the worker after the commit.
        """
        user = request.user
        if not isinstance(user, User):  # CanManage lets only accounts through
            raise PermissionDenied
        version = get_object_or_404(
            DocumentVersion.objects.select_related("document"), pk=version_id
        )
        try:
            job = request_ingest(version, user)
        except IngestNotAllowedError:
            body = {
                "detail": gettext("Configuration files are not ingested."),
                "code": CODE_CONFIGURATION,
            }
            return Response(
                IngestRequestErrorSerializer(body).data, status=status.HTTP_400_BAD_REQUEST
            )
        except IngestAlreadyActiveError as error:
            conflict = {
                "detail": gettext("This document version is already being ingested."),
                "code": CODE_INGEST_ACTIVE,
                "job": error.job,
            }
            return Response(
                IngestConflictSerializer(conflict).data, status=status.HTTP_409_CONFLICT
            )
        answer = IngestJobSerializer(
            ingest_jobs().get(pk=job.pk), context={SHOW_REQUESTED_BY: True}
        )
        return Response(answer.data, status=status.HTTP_202_ACCEPTED)
