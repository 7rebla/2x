"""Documents and versions in the admin: read only (E-39, E-42).

The admin admits active superusers only (``twox.config.admin_site``). Files
are created through the API and its services; nobody adds, changes or deletes
them here.
"""

from typing import TYPE_CHECKING

from django.contrib import admin
from django.http import HttpRequest

from twox.files.models import Document, DocumentVersion

# Django's admin classes are generic for the type checker only; they cannot be
# subscripted at runtime.
if TYPE_CHECKING:
    DocumentAdminBase = admin.ModelAdmin[Document]
    DocumentVersionAdminBase = admin.ModelAdmin[DocumentVersion]
    DocumentVersionInlineBase = admin.TabularInline[DocumentVersion, Document]
else:
    DocumentAdminBase = DocumentVersionAdminBase = admin.ModelAdmin
    DocumentVersionInlineBase = admin.TabularInline

VERSION_FIELDS = (
    "number",
    "original_filename",
    "content_type",
    "size",
    "sha256",
    "uploaded_by",
    "created_at",
)


class DocumentVersionInline(DocumentVersionInlineBase):
    """The versions of a document, read only."""

    model = DocumentVersion
    extra = 0
    fields = VERSION_FIELDS
    readonly_fields = VERSION_FIELDS
    show_change_link = True

    def has_add_permission(self, request: HttpRequest, obj: Document | None = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Document | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Document | None = None) -> bool:
        return False


@admin.register(Document)
class DocumentAdmin(DocumentAdminBase):
    """Documents, read only."""

    list_display = ("title", "device", "kind", "created_by", "created_at")
    list_filter = ("kind",)
    search_fields = ("title", "device__key", "device__name")
    list_select_related = ("device", "created_by")
    fields = ("title", "device", "kind", "created_by", "created_at")
    readonly_fields = fields
    inlines = (DocumentVersionInline,)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Document | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Document | None = None) -> bool:
        return False


@admin.register(DocumentVersion)
class DocumentVersionAdmin(DocumentVersionAdminBase):
    """Document versions, read only."""

    list_display = ("document", "number", "original_filename", "size", "uploaded_by", "created_at")
    search_fields = ("document__title", "original_filename", "sha256")
    list_select_related = ("document", "uploaded_by")
    fields = ("document", *VERSION_FIELDS, "blob_key")
    readonly_fields = fields

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: DocumentVersion | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: DocumentVersion | None = None
    ) -> bool:
        return False
