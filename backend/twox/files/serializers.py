"""Serializers of the files API: documents, versions, uploads and their answers."""

from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from twox.files.models import Document, DocumentKind, DocumentVersion
from twox.files.services import DuplicateLocation


def username_field(source: str, help_text: str) -> serializers.CharField:
    """The user name behind a user foreign key; ``null`` for system operations."""
    return serializers.CharField(
        source=f"{source}.username", read_only=True, allow_null=True, help_text=help_text
    )


@extend_schema_field(OpenApiTypes.BINARY)
class UploadFileField(serializers.FileField):
    """A file part of a ``multipart/form-data`` form (binary in the schema)."""


class DocumentVersionSerializer(serializers.ModelSerializer[DocumentVersion]):
    """One immutable version of a document; its bytes come from the download endpoint."""

    uploaded_by = username_field("uploaded_by", "User name of the uploader; null for the system.")

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
        )
        read_only_fields = fields


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
