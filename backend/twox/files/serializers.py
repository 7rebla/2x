"""Serializers of the files API: documents, versions, uploads and their answers."""

from typing import Any, Final

from django.db.models import Prefetch, QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from twox.files.models import Document, DocumentKind, DocumentVersion
from twox.files.services import DuplicateLocation
from twox.ingest.models import IngestErrorCode, IngestJob, IngestStatus, IngestStep

#: Attribute that :func:`prefetch_latest_ingest_job` fills on each version:
#: a list with the newest ingest job, or an empty list.
LATEST_INGEST_JOB_ATTR: Final = "latest_ingest_jobs"

#: Start of ``error_detail`` of a job that Docling converted only in part
#: (``partial_success``, work order 046); such a job ends ``done``.
PARTIAL_DETAIL_PREFIX: Final = "converted with "


def username_field(source: str, help_text: str) -> serializers.CharField:
    """The user name behind a user foreign key; ``null`` for system operations."""
    return serializers.CharField(
        source=f"{source}.username", read_only=True, allow_null=True, help_text=help_text
    )


def newest_ingest_jobs() -> QuerySet[IngestJob]:
    """The newest ingest job of each version, in one query (``DISTINCT ON``)."""
    return IngestJob.objects.order_by("document_version_id", "-created_at", "-pk").distinct(
        "document_version_id"
    )


def prefetch_latest_ingest_job() -> Prefetch[str, QuerySet[IngestJob], str]:
    """For a queryset of versions: load the newest ingest job of each with one extra query."""
    return Prefetch("ingest_jobs", queryset=newest_ingest_jobs(), to_attr=LATEST_INGEST_JOB_ATTR)


def latest_ingest_job(version: DocumentVersion) -> IngestJob | None:
    """The newest ingest job of ``version``; prefetched if possible, else one query."""
    prefetched: list[IngestJob] | None = getattr(version, LATEST_INGEST_JOB_ATTR, None)
    if prefetched is not None:
        return prefetched[0] if prefetched else None
    return version.ingest_jobs.order_by("-created_at", "-pk").first()


@extend_schema_field(OpenApiTypes.BINARY)
class UploadFileField(serializers.FileField):
    """A file part of a ``multipart/form-data`` form (binary in the schema)."""


class IngestJobSummarySerializer(serializers.ModelSerializer[IngestJob]):
    """State of one ingest job of a version (work order 051).

    ``error_code`` is a fixed key that the web UI translates; ``error_detail``
    is a short English technical text, cleaned of paths, addresses and file
    names (046). Every role sees both (E-57).
    """

    # Declared here so that the schema lists the empty value as well.
    step = serializers.ChoiceField(
        choices=IngestStep.choices,
        allow_blank=True,
        read_only=True,
        help_text="Step the job is in or failed in; empty before the first step.",
    )
    error_code = serializers.ChoiceField(
        choices=IngestErrorCode.choices,
        allow_blank=True,
        read_only=True,
        help_text="Kind of error of a failed or skipped job; empty otherwise.",
    )
    error_detail = serializers.CharField(
        read_only=True,
        help_text=(
            "Technical detail in English. Set for failed and skipped jobs, and for a done "
            "job that was converted only in part (then it starts with 'converted with ')."
        ),
    )
    # Not "partial": serializers use that name for partial updates.
    partly_converted = serializers.SerializerMethodField(
        help_text="True for a done job that was converted only in part; see error_detail."
    )

    class Meta:
        model = IngestJob
        fields: tuple[str, ...] = (
            "id",
            "status",
            "step",
            "error_code",
            "error_detail",
            "partly_converted",
            "section_count",
            "page_count",
            "created_at",
            "finished_at",
        )
        read_only_fields: tuple[str, ...] = fields

    def get_partly_converted(self, job: IngestJob) -> bool:
        return job.status == IngestStatus.DONE and job.error_detail.startswith(
            PARTIAL_DETAIL_PREFIX
        )


class DocumentVersionSerializer(serializers.ModelSerializer[DocumentVersion]):
    """One immutable version of a document; its bytes come from the download endpoint."""

    uploaded_by = username_field("uploaded_by", "User name of the uploader; null for the system.")
    ingest = serializers.SerializerMethodField(
        help_text="The newest ingest job of the version; null if it was never ingested."
    )

    class Meta:
        model = DocumentVersion
        fields: tuple[str, ...] = (
            "id",
            "number",
            "sha256",
            "size",
            "content_type",
            "original_filename",
            "uploaded_by",
            "created_at",
            "ingest",
        )
        read_only_fields = fields

    @extend_schema_field(IngestJobSummarySerializer(allow_null=True))
    def get_ingest(self, version: DocumentVersion) -> dict[str, Any] | None:
        """The newest ingest job; the views prefetch it (:func:`prefetch_latest_ingest_job`)."""
        job = latest_ingest_job(version)
        return None if job is None else dict(IngestJobSummarySerializer(job).data)


class DocumentSerializer(serializers.ModelSerializer[Document]):
    """A file of a device with its newest version."""

    created_by = username_field("created_by", "User name of the creator; null for the system.")
    latest_version = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields: tuple[str, ...] = (
            "id",
            "device",
            "title",
            "kind",
            "created_at",
            "created_by",
            "latest_version",
        )
        read_only_fields: tuple[str, ...] = fields

    @extend_schema_field(DocumentVersionSerializer(allow_null=True))
    def get_latest_version(self, document: Document) -> dict[str, Any] | None:
        """The version with the highest number; ``None`` only for a document without any.

        The views prefetch the versions, so this reads no further rows.
        """
        newest = max(document.versions.all(), key=lambda version: version.number, default=None)
        return None if newest is None else dict(DocumentVersionSerializer(newest).data)


class DocumentDetailSerializer(DocumentSerializer):
    """A file of a device with all its versions, oldest first."""

    versions = DocumentVersionSerializer(many=True, read_only=True)

    class Meta(DocumentSerializer.Meta):
        fields = (*DocumentSerializer.Meta.fields, "versions")
        read_only_fields = fields


class DuplicateSerializer(serializers.Serializer[DuplicateLocation]):
    """Another place where the same content is already stored."""

    device = serializers.IntegerField(source="device.pk")
    device_key = serializers.CharField(source="device.key")
    device_name = serializers.CharField(source="device.name")
    document = serializers.IntegerField(source="document.pk")
    document_title = serializers.CharField(source="document.title")
    version = serializers.IntegerField(source="version.pk")
    version_number = serializers.IntegerField(source="version.number")


class UploadResultSerializer(serializers.Serializer[Any]):
    """Answer to an upload: the document, the new version and other places of its content."""

    document = DocumentSerializer()
    version = DocumentVersionSerializer()
    duplicates = DuplicateSerializer(many=True)


class DocumentUploadSerializer(serializers.Serializer[Any]):
    """Form of a new file (``multipart/form-data``)."""

    file = UploadFileField(help_text="The file; at most TWOX_UPLOAD_MAX_BYTES bytes.")
    title = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Title of the document; the file name if empty or missing.",
    )
    kind = serializers.ChoiceField(
        choices=DocumentKind.choices,
        default=DocumentKind.DOCUMENT,
        help_text="Only 'document' is accepted for now; configurations follow with redaction.",
    )


class VersionUploadSerializer(serializers.Serializer[Any]):
    """Form of a new version of an existing file (``multipart/form-data``)."""

    file = UploadFileField(help_text="The file; at most TWOX_UPLOAD_MAX_BYTES bytes.")


class DuplicateVersionErrorSerializer(serializers.Serializer[Any]):
    """409: the upload equals the newest version of the document."""

    detail = serializers.CharField()
    code = serializers.CharField()
    existing_version = DocumentVersionSerializer()


class ErrorDetailSerializer(serializers.Serializer[Any]):
    """An error with a message, for example 404 or 413."""

    detail = serializers.CharField()
