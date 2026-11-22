"""Ingest jobs and sections in the admin: read only, like the files (E-39).

The admin admits active superusers only (``twox.config.admin_site``). Jobs
and sections are written by the ingest flow; nobody adds, changes or deletes
them here. Sections without an embedding are normal while the AI features are
switched off (E-59); the list shows and filters them without marking an error.
"""

from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.db.models import ExpressionWrapper, Q, QuerySet
from django.db.models import fields as model_fields
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from twox.ingest.models import IngestJob, Section

# Django's admin classes are generic for the type checker only; they cannot be
# subscripted at runtime.
if TYPE_CHECKING:
    IngestJobAdminBase = admin.ModelAdmin[IngestJob]
    SectionAdminBase = admin.ModelAdmin[Section]
else:
    IngestJobAdminBase = SectionAdminBase = admin.ModelAdmin

JOB_FIELDS = (
    "document_version",
    "status",
    "step",
    "error_code",
    "error_detail",
    "attempts",
    "requested_by",
    "docling_task_id",
    "docling_started_at",
    "result_blob_key",
    "reused_from",
    "page_count",
    "section_count",
    "created_at",
    "started_at",
    "finished_at",
    "updated_at",
)

SECTION_FIELDS = (
    "document_version",
    "ingest_job",
    "ordinal",
    "page_start",
    "page_end",
    "heading_text",
    "text",
    "has_embedding",
    "embedding_model",
    "created_at",
)


@admin.register(IngestJob)
class IngestJobAdmin(IngestJobAdminBase):
    """Ingest jobs, read only."""

    list_display = (
        "document_version",
        "status",
        "step",
        "error_code",
        "attempts",
        "section_count",
        "requested_by",
        "created_at",
    )
    list_filter = ("status", "step", "error_code")
    search_fields = ("document_version__document__title", "docling_task_id")
    list_select_related = ("document_version__document", "requested_by")
    fields = JOB_FIELDS
    readonly_fields = JOB_FIELDS

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: IngestJob | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: IngestJob | None = None) -> bool:
        return False


class EmbeddingFilter(admin.SimpleListFilter):
    """Sections with or without an embedding."""

    title = _("embedding")
    parameter_name = "embedding"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Any]
    ) -> list[tuple[str, str]]:
        return [("yes", str(_("with embedding"))), ("no", str(_("without embedding")))]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Section]) -> QuerySet[Section]:
        if self.value() == "yes":
            return queryset.filter(embedding__isnull=False)
        if self.value() == "no":
            return queryset.filter(embedding__isnull=True)
        return queryset


@admin.register(Section)
class SectionAdmin(SectionAdminBase):
    """Sections, read only; the vector columns are not loaded."""

    list_display = (
        "document_version",
        "ordinal",
        "page_start",
        "page_end",
        "heading_text",
        "has_embedding",
        "embedding_model",
    )
    list_filter = (EmbeddingFilter, "embedding_model")
    search_fields = ("heading_text", "document_version__document__title")
    list_select_related = ("document_version__document",)
    fields = SECTION_FIELDS
    readonly_fields = SECTION_FIELDS

    def get_queryset(self, request: HttpRequest) -> QuerySet[Section]:
        return (
            super()
            .get_queryset(request)
            .defer("embedding", "search_vector")
            .annotate(
                embedding_present=ExpressionWrapper(
                    Q(embedding__isnull=False), output_field=model_fields.BooleanField()
                )
            )
        )

    @admin.display(boolean=True, description=_("has embedding"))
    def has_embedding(self, obj: Section) -> bool:
        present: bool = getattr(obj, "embedding_present", False)
        return present

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Section | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Section | None = None) -> bool:
        return False
