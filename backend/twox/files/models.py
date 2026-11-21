"""Files of a device and their immutable versions.

A :class:`Document` belongs to exactly one device and has one or more
:class:`DocumentVersion` rows, numbered 1, 2, ... per document. A version
points to its bytes in the blob storage (``twox.files.storage``) by key and
keeps checksum, size, content type, the original file name, who uploaded it
and when. Versions are never changed after they are created.

Rows are created through ``twox.files.services`` only; it checks size,
kind and duplicates and numbers the versions without a race.
"""

from collections.abc import Iterable

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.base import ModelBase
from django.utils.translation import gettext_lazy as _

from twox.assets.models import Device

TITLE_MAX_LENGTH = 200
FILENAME_MAX_LENGTH = 255
CONTENT_TYPE_MAX_LENGTH = 100
SHA256_LENGTH = 64
# "sha256/ab/cd/" plus 64 hexadecimal characters is 77; room for other schemes.
BLOB_KEY_MAX_LENGTH = 100

#: ``type/subtype`` with the token characters of RFC 6838, no parameters.
CONTENT_TYPE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$"

validate_content_type = RegexValidator(
    regex=CONTENT_TYPE_PATTERN,
    message=_("Enter a media type of the form type/subtype."),
    code="invalid_content_type",
)

validate_sha256 = RegexValidator(
    regex=r"^[0-9a-f]{64}$",
    message=_("Enter a SHA-256 checksum as 64 lowercase hexadecimal characters."),
    code="invalid_sha256",
)


class DocumentKind(models.TextChoices):
    """What a file is; the ingestion in M2 and M5 chooses its way by it."""

    DOCUMENT = "document", _("document")
    CONFIGURATION = "configuration", _("configuration")


class VersionImmutableError(Exception):
    """An existing document version was about to be changed."""


class Document(models.Model):
    """A file of a device, for example a manual; its content lives in versions."""

    device = models.ForeignKey(
        Device,
        on_delete=models.PROTECT,
        related_name="documents",
        verbose_name=_("device"),
    )
    title = models.CharField(_("title"), max_length=TITLE_MAX_LENGTH)
    kind = models.CharField(
        _("kind"),
        max_length=32,
        choices=DocumentKind.choices,
        default=DocumentKind.DOCUMENT,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    # Empty for system operations (for example a later import job).
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_documents",
        verbose_name=_("created by"),
    )

    class Meta:
        ordering = ("title", "pk")
        verbose_name = _("document")
        verbose_name_plural = _("documents")
        constraints = (
            models.CheckConstraint(
                condition=Q(kind__in=DocumentKind.values),
                name="files_document_kind_valid",
            ),
        )

    def __str__(self) -> str:
        return self.title


class DocumentVersion(models.Model):
    """One immutable state of a document: its bytes in the blob storage."""

    document = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        related_name="versions",
        verbose_name=_("document"),
    )
    number = models.PositiveIntegerField(_("number"), validators=[MinValueValidator(1)])
    blob_key = models.CharField(_("blob key"), max_length=BLOB_KEY_MAX_LENGTH)
    sha256 = models.CharField(
        _("SHA-256"),
        max_length=SHA256_LENGTH,
        db_index=True,
        validators=[validate_sha256],
    )
    size = models.PositiveBigIntegerField(_("size in bytes"))
    content_type = models.CharField(
        _("content type"),
        max_length=CONTENT_TYPE_MAX_LENGTH,
        validators=[validate_content_type],
    )
    original_filename = models.CharField(_("original file name"), max_length=FILENAME_MAX_LENGTH)
    # Empty for system operations (for example a later import job).
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="uploaded_versions",
        verbose_name=_("uploaded by"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ("document", "number")
        verbose_name = _("document version")
        verbose_name_plural = _("document versions")
        constraints = (
            models.UniqueConstraint(
                fields=["document", "number"],
                name="files_version_document_number_unique",
            ),
            models.CheckConstraint(condition=Q(number__gte=1), name="files_version_number_min"),
        )

    def __str__(self) -> str:
        return f"{self.document} v{self.number}"

    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        """Insert a new version; an existing version is never changed.

        ``QuerySet.update()`` bypasses this method; nothing in the code uses it
        on versions.
        """
        if not self._state.adding or force_update or update_fields is not None:
            raise VersionImmutableError(f"document version {self.pk} is immutable")
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
