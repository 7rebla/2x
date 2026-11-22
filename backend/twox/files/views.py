"""API views of the files app: list, upload, versions and download.

Reading needs the role ``read`` or ``manage`` (``CanRead``), uploading the
role ``manage`` (``CanManageOrReadOnly``, E-40). Uploads are
``multipart/form-data`` and limited by ``TWOX_UPLOAD_MAX_BYTES`` before and
while the body is read (``twox.files.uploads``). Downloads are always
attachments with a safe content type (``twox.files.downloads``).
"""

from collections.abc import Iterable

from django.db.models import Prefetch, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import BaseParser
from rest_framework.renderers import BaseRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from twox.accounts.models import User
from twox.accounts.permissions import CanManageOrReadOnly, CanRead
from twox.assets.models import Device
from twox.files.downloads import BlobDownloadResponse
from twox.files.models import Document, DocumentVersion
from twox.files.serializers import (
    DocumentDetailSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
    DuplicateVersionErrorSerializer,
    ErrorDetailSerializer,
    UploadResultSerializer,
    VersionUploadSerializer,
    prefetch_latest_ingest_job,
)
from twox.files.services import (
    ConfigurationNotAcceptedError,
    DuplicateVersionError,
    UploadResult,
    UploadTooLargeError,
    add_version,
    create_document,
)
from twox.files.storage import get_blob_storage
from twox.files.uploads import LimitedUploadView, UploadTooLarge

_ERROR_403 = OpenApiResponse(ErrorDetailSerializer, description="No role, or not allowed.")
_ERROR_404 = OpenApiResponse(ErrorDetailSerializer, description="Not found.")
_ERROR_413 = OpenApiResponse(
    ErrorDetailSerializer, description="Larger than TWOX_UPLOAD_MAX_BYTES."
)


def documents_with_versions() -> QuerySet[Document]:
    """Documents with uploader names and all versions, oldest version first.

    The newest ingest job of every version comes with one more query, however
    many documents and versions there are (work order 051).
    """
    versions = (
        DocumentVersion.objects.select_related("uploaded_by")
        .order_by("number")
        .prefetch_related(prefetch_latest_ingest_job())
    )
    return Document.objects.select_related("created_by").prefetch_related(
        Prefetch("versions", queryset=versions)
    )


def acting_user(request: Request) -> User | None:
    user = request.user
    return user if isinstance(user, User) else None


def upload_result_response(result: UploadResult) -> Response:
    data = {
        "document": documents_with_versions().get(pk=result.document.pk),
        "version": result.version,
        "duplicates": result.duplicates,
    }
    return Response(UploadResultSerializer(data).data, status=status.HTTP_201_CREATED)


class DeviceDocumentsView(LimitedUploadView):
    """The files of a device: list them, or upload a new one."""

    permission_classes = (CanManageOrReadOnly,)

    @extend_schema(
        operation_id="device_documents_list",
        responses={200: DocumentSerializer(many=True), 403: _ERROR_403, 404: _ERROR_404},
    )
    def get(self, request: Request, device_id: int) -> Response:
        """The files of the device, each with its newest version, ordered by title."""
        device = get_object_or_404(Device, pk=device_id)
        documents = documents_with_versions().filter(device=device)
        return Response(DocumentSerializer(documents, many=True).data)

    @extend_schema(
        operation_id="device_documents_create",
        request={"multipart/form-data": DocumentUploadSerializer},
        responses={
            201: UploadResultSerializer,
            400: OpenApiResponse(description="Invalid form, or a configuration file."),
            403: _ERROR_403,
            404: _ERROR_404,
            413: _ERROR_413,
        },
    )
    def post(self, request: Request, device_id: int) -> Response:
        """Upload a new file of the device as version 1.

        ``duplicates`` lists other places with the same content; the upload is
        accepted all the same.
        """
        device = get_object_or_404(Device, pk=device_id)
        form = DocumentUploadSerializer(data=self.upload_data(request))
        form.is_valid(raise_exception=True)
        try:
            result = create_document(
                device,
                form.validated_data["file"],
                form.validated_data.get("title"),
                form.validated_data["kind"],
                acting_user(request),
            )
        except ConfigurationNotAcceptedError as error:
            raise ValidationError({"kind": [str(error)]}) from error
        except UploadTooLargeError as error:
            raise UploadTooLarge from error
        return upload_result_response(result)


class DocumentDetailView(APIView):
    """One file with all its versions."""

    permission_classes = (CanRead,)

    @extend_schema(
        operation_id="document_retrieve",
        responses={200: DocumentDetailSerializer, 403: _ERROR_403, 404: _ERROR_404},
    )
    def get(self, request: Request, document_id: int) -> Response:
        """The file with all versions, oldest first."""
        document = get_object_or_404(documents_with_versions(), pk=document_id)
        return Response(DocumentDetailSerializer(document).data)


class DocumentVersionsView(LimitedUploadView):
    """New versions of a file."""

    permission_classes = (CanManageOrReadOnly,)

    @extend_schema(
        operation_id="document_version_create",
        request={"multipart/form-data": VersionUploadSerializer},
        responses={
            201: UploadResultSerializer,
            400: OpenApiResponse(description="Invalid form, or a configuration file."),
            403: _ERROR_403,
            404: _ERROR_404,
            409: DuplicateVersionErrorSerializer,
            413: _ERROR_413,
        },
    )
    def post(self, request: Request, document_id: int) -> Response:
        """Upload a new version of the file.

        409 if the content equals the newest version; the answer names that
        version. The same content as an older version or another file is
        accepted and listed in ``duplicates``.
        """
        document = get_object_or_404(Document, pk=document_id)
        form = VersionUploadSerializer(data=self.upload_data(request))
        form.is_valid(raise_exception=True)
        try:
            result = add_version(document, form.validated_data["file"], acting_user(request))
        except DuplicateVersionError as error:
            body = {
                "detail": str(error),
                "code": "duplicate_version",
                "existing_version": error.version,
            }
            return Response(
                DuplicateVersionErrorSerializer(body).data, status=status.HTTP_409_CONFLICT
            )
        except ConfigurationNotAcceptedError as error:
            raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: [str(error)]}) from error
        except UploadTooLargeError as error:
            raise UploadTooLarge from error
        return upload_result_response(result)


class FirstRendererNegotiation(BaseContentNegotiation):
    """Ignore ``Accept``: a download is never refused with 406.

    Errors are rendered by the first renderer (JSON); the file itself is no
    DRF response and needs no renderer.
    """

    def select_parser(self, request: Request, parsers: Iterable[BaseParser]) -> BaseParser | None:
        return next(iter(parsers), None)

    def select_renderer(
        self, request: Request, renderers: Iterable[BaseRenderer], format_suffix: str | None = None
    ) -> tuple[BaseRenderer, str]:
        renderer = next(iter(renderers))
        return renderer, renderer.media_type


class DocumentVersionDownloadView(APIView):
    """The bytes of one version, as an attachment."""

    permission_classes = (CanRead,)
    content_negotiation_class = FirstRendererNegotiation

    @extend_schema(
        operation_id="document_version_download",
        responses={
            (200, "*/*"): OpenApiResponse(
                OpenApiTypes.BINARY,
                description=(
                    "The file as an attachment. Content-Type is the stored type if it is "
                    "a known document or image type, otherwise application/octet-stream."
                ),
            ),
            (403, "application/json"): _ERROR_403,
            (404, "application/json"): _ERROR_404,
        },
    )
    def get(self, request: Request, version_id: int) -> BlobDownloadResponse:
        """Download the version: streamed from the storage, always as an attachment."""
        version = get_object_or_404(DocumentVersion, pk=version_id)
        blob = get_blob_storage().open_blob(version.blob_key)
        return BlobDownloadResponse(
            blob, filename=version.original_filename, content_type=version.content_type
        )
