"""Ingest jobs and the sections they produce.

An :class:`IngestJob` is one attempt to ingest one document version: convert
it with Docling, build the sections and, when the AI features are switched on
(E-59), embed them. Every attempt is a row of its own, so the history stays
visible without deleting anything (E-55). The job carries a fixed error code
that the web UI translates, plus a short English technical detail.

A :class:`Section` is a piece of text of a document version with its heading
path and pages. Sections are derived machine data: the ingest flow replaces
all sections of a version in one transaction and writes them with
``bulk_create`` through :func:`section_rows`. Neither model is registered in
the audit log (E-55); who started a job is in ``requested_by``.

The search vector is a generated column, so PostgreSQL keeps it in step with
heading and text on every write, ``QuerySet.update()`` included. The
embedding is optional: without AI features (E-59) every section stays without
one, and the keyword search works on the search vector alone.
"""

from collections.abc import Iterable, Sequence
from typing import Final, Protocol

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex, OpClass
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, ProhibitNullCharactersValidator
from django.db import models
from django.db.models import Expression, F, Q
from django.db.models.base import ModelBase
from django.utils.translation import gettext_lazy as _
from pgvector.django import HnswIndex, VectorField

from twox.files.models import BLOB_KEY_MAX_LENGTH, DocumentVersion
from twox.files.storage import InvalidBlobKeyError, validate_key

#: Length of every embedding (bge-m3, E-56). The embedding settings of 044 and
#: 048 must match it; a vector of another length is rejected by the database.
EMBEDDING_DIMENSIONS = 1024

#: Text search configurations of the search vector (E-55): ``simple`` keeps
#: identifiers such as ``S7-1200`` word for word, ``german`` and ``english``
#: find word forms in the mixed-language manuals.
SEARCH_CONFIGS = ("simple", "german", "english")

#: Separator of the headings in :attr:`Section.heading_text`.
HEADING_SEPARATOR = " > "

ERROR_DETAIL_MAX_LENGTH = 2000
#: Start of ``error_detail`` of a job that Docling converted only in part
#: (``partial_success``, work order 046); such a job ends ``done``. Defined
#: here, not in the ingest flow, so that the files API can use it without
#: importing the flow and its clients (work order 061).
PARTIAL_DETAIL_PREFIX: Final = "converted with "
EMBEDDING_MODEL_MAX_LENGTH = 200
DOCLING_TASK_ID_MAX_LENGTH = 200

prohibit_null_characters = ProhibitNullCharactersValidator()


class IngestStatus(models.TextChoices):
    """State of an ingest job."""

    QUEUED = "queued", _("queued")
    RUNNING = "running", _("running")
    DONE = "done", _("done")
    FAILED = "failed", _("failed")
    SKIPPED = "skipped", _("skipped")


#: States of a job that is not finished yet; at most one per version.
ACTIVE_STATUSES = (IngestStatus.QUEUED, IngestStatus.RUNNING)


class IngestStep(models.TextChoices):
    """Step an ingest job is in or failed in; empty before the first step."""

    CONVERT = "convert", _("convert")
    SECTIONS = "sections", _("sections")
    EMBED = "embed", _("embed")


class IngestErrorCode(models.TextChoices):
    """Kind of error of a failed or skipped job; the web UI translates it."""

    DOCLING_UNAVAILABLE = "docling_unavailable", _("converter unavailable")
    DOCLING_REJECTED = "docling_rejected", _("converter rejected the file")
    CONVERSION_FAILED = "conversion_failed", _("conversion failed")
    CONTENT_MISSING = "content_missing", _("stored content missing")
    UNSUPPORTED_FORMAT = "unsupported_format", _("unsupported format")
    EMBEDDING_UNAVAILABLE = "embedding_unavailable", _("embedding service unavailable")
    EMBEDDING_REJECTED = "embedding_rejected", _("embedding service rejected the request")
    EMBEDDING_DIMENSION_MISMATCH = (
        "embedding_dimension_mismatch",
        _("embedding has the wrong number of dimensions"),
    )
    TIMEOUT = "timeout", _("time limit exceeded")
    INTERNAL = "internal", _("internal error")


def validate_blob_key(value: str) -> None:
    """Accept a key of the blob storage (``sha256/ab/cd/<sha256>``) only."""
    try:
        validate_key(value)
    except InvalidBlobKeyError as error:
        raise ValidationError(
            _("Enter a key of the blob storage."), code="invalid_blob_key"
        ) from error


def validate_embedding_dimensions(value: Sequence[float]) -> None:
    """Accept a vector of exactly :data:`EMBEDDING_DIMENSIONS` numbers only.

    The database rejects other lengths as well; this gives ``full_clean`` a
    clear message before anything is written.
    """
    if len(value) != EMBEDDING_DIMENSIONS:
        raise ValidationError(
            _("An embedding must have %(expected)d dimensions, not %(actual)d."),
            code="invalid_embedding_dimensions",
            params={"expected": EMBEDDING_DIMENSIONS, "actual": len(value)},
        )


class IngestJob(models.Model):
    """One attempt to ingest one document version."""

    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.PROTECT,
        related_name="ingest_jobs",
        verbose_name=_("document version"),
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=IngestStatus.choices,
        default=IngestStatus.QUEUED,
    )
    step = models.CharField(_("step"), max_length=16, choices=IngestStep.choices, blank=True)
    error_code = models.CharField(
        _("error code"), max_length=40, choices=IngestErrorCode.choices, blank=True
    )
    # Short English technical text, cleaned by the ingest flow (046).
    error_detail = models.CharField(
        _("error detail"),
        max_length=ERROR_DETAIL_MAX_LENGTH,
        blank=True,
        validators=[prohibit_null_characters],
    )
    attempts = models.PositiveSmallIntegerField(_("attempts"), default=0)
    # Empty for system operations. Who may see it is decided in the API (E-57).
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ingest_jobs",
        verbose_name=_("requested by"),
    )
    docling_task_id = models.CharField(
        _("converter task ID"), max_length=DOCLING_TASK_ID_MAX_LENGTH, blank=True
    )
    # First "started" state reported by Docling; the time limit counts from here.
    docling_started_at = models.DateTimeField(_("converter started at"), null=True, blank=True)
    # The stored Docling answer, content-addressed in twox.files.storage (E-55).
    result_blob_key = models.CharField(
        _("result blob key"),
        max_length=BLOB_KEY_MAX_LENGTH,
        blank=True,
        validators=[validate_blob_key],
    )
    # Set when the Docling answer of a job with the same content was reused.
    reused_from = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reused_by",
        verbose_name=_("reused from"),
    )
    page_count = models.PositiveIntegerField(_("page count"), null=True, blank=True)
    section_count = models.PositiveIntegerField(_("section count"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    started_at = models.DateTimeField(_("started at"), null=True, blank=True)
    finished_at = models.DateTimeField(_("finished at"), null=True, blank=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = _("ingest job")
        verbose_name_plural = _("ingest jobs")
        constraints = (
            models.UniqueConstraint(
                fields=["document_version"],
                condition=Q(status__in=ACTIVE_STATUSES),
                name="ingest_job_one_active_per_version",
                violation_error_message=_(
                    "This document version already has a queued or running ingest job."
                ),
            ),
            models.CheckConstraint(
                condition=Q(status__in=IngestStatus.values),
                name="ingest_job_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(step="") | Q(step__in=IngestStep.values),
                name="ingest_job_step_valid",
            ),
            models.CheckConstraint(
                condition=Q(error_code="") | Q(error_code__in=IngestErrorCode.values),
                name="ingest_job_error_code_valid",
            ),
        )

    def __str__(self) -> str:
        return f"{self.document_version}: {self.status}"


def search_vector_expression() -> Expression:
    """The expression of :attr:`Section.search_vector`.

    ``setweight(to_tsvector(config, column), weight)`` for every config in
    :data:`SEARCH_CONFIGS`, joined with ``||``: weight A from the headings,
    B from the text. Both functions are immutable with a fixed configuration,
    so PostgreSQL accepts them in a generated column.
    """
    vectors = [
        SearchVector(column, config=config, weight=weight)
        for column, weight in (("heading_text", "A"), ("text", "B"))
        for config in SEARCH_CONFIGS
    ]
    combined: Expression = vectors[0]
    for vector in vectors[1:]:
        combined = combined + vector
    return combined


def join_headings(heading_path: Iterable[str]) -> str:
    """The headings of a path as one text, for example ``Chapter 1 > Safety``."""
    return HEADING_SEPARATOR.join(heading_path)


class Section(models.Model):
    """A piece of text of a document version, with headings and pages."""

    # The unique constraint on (document_version, ordinal) serves as its index.
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.PROTECT,
        related_name="sections",
        verbose_name=_("document version"),
        db_index=False,
    )
    ingest_job = models.ForeignKey(
        IngestJob,
        on_delete=models.PROTECT,
        related_name="sections",
        verbose_name=_("ingest job"),
    )
    ordinal = models.PositiveIntegerField(_("ordinal"))
    # Empty for formats without pages (for example Markdown).
    page_start = models.PositiveIntegerField(
        _("first page"), null=True, blank=True, validators=[MinValueValidator(1)]
    )
    page_end = models.PositiveIntegerField(
        _("last page"), null=True, blank=True, validators=[MinValueValidator(1)]
    )
    heading_path = ArrayField(
        models.TextField(validators=[prohibit_null_characters]),
        verbose_name=_("heading path"),
        default=list,
        blank=True,
    )
    # The same headings joined with " > "; filled by save() and section_rows().
    heading_text = models.TextField(
        _("heading text"), blank=True, validators=[prohibit_null_characters]
    )
    text = models.TextField(_("text"), validators=[prohibit_null_characters])
    search_vector = models.GeneratedField(
        expression=search_vector_expression(),
        output_field=SearchVectorField(),
        db_persist=True,
        verbose_name=_("search vector"),
    )
    # Empty without AI features (E-59) and until the embed step has run.
    embedding = VectorField(
        _("embedding"),
        dimensions=EMBEDDING_DIMENSIONS,
        null=True,
        blank=True,
        validators=[validate_embedding_dimensions],
    )
    embedding_model = models.CharField(
        _("embedding model"), max_length=EMBEDDING_MODEL_MAX_LENGTH, blank=True
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        # By the column, not the related model: no join for the default order.
        ordering = ("document_version_id", "ordinal")
        verbose_name = _("section")
        verbose_name_plural = _("sections")
        constraints = (
            models.UniqueConstraint(
                fields=["document_version", "ordinal"],
                name="ingest_section_version_ordinal_unique",
            ),
            models.CheckConstraint(
                # Explicit IS NOT NULL: a CHECK passes when it yields NULL.
                condition=Q(page_start__isnull=True, page_end__isnull=True)
                | Q(
                    page_start__isnull=False,
                    page_end__isnull=False,
                    page_start__gte=1,
                    page_end__gte=F("page_start"),
                ),
                name="ingest_section_pages_valid",
            ),
            models.CheckConstraint(
                condition=Q(embedding__isnull=True, embedding_model="")
                | (Q(embedding__isnull=False) & ~Q(embedding_model="")),
                name="ingest_section_embedding_has_model",
            ),
        )
        indexes = (
            GinIndex(fields=["search_vector"], name="ingest_section_search_gin"),
            GinIndex(OpClass(F("text"), name="gin_trgm_ops"), name="ingest_section_text_trgm"),
            HnswIndex(
                fields=["embedding"],
                opclasses=["vector_cosine_ops"],
                name="ingest_section_embedding_hnsw",
            ),
        )

    def __str__(self) -> str:
        return f"{self.document_version} #{self.ordinal}"

    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        """Keep :attr:`heading_text` in step with :attr:`heading_path`."""
        self.heading_text = join_headings(self.heading_path)
        if update_fields is not None and "heading_path" in update_fields:
            update_fields = {*update_fields, "heading_text"}
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class SectionDraftLike(Protocol):
    """What :func:`section_rows` reads from a section draft (043)."""

    @property
    def ordinal(self) -> int: ...

    @property
    def heading_path(self) -> Sequence[str]: ...

    @property
    def text(self) -> str: ...

    @property
    def page_start(self) -> int | None: ...

    @property
    def page_end(self) -> int | None: ...


#: Fields that section_rows() leaves to the database or to the caller.
_UNCHECKED_ROW_FIELDS = ("document_version", "ingest_job", "embedding", "embedding_model")


def section_rows(
    drafts: Iterable[SectionDraftLike], version: DocumentVersion, job: IngestJob
) -> list[Section]:
    """Unsaved sections of ``version`` from section drafts, for ``bulk_create``.

    ``bulk_create`` does not call :meth:`Section.save`, so this function fills
    :attr:`Section.heading_text`. Each row is checked with ``clean_fields``
    (no database queries), so a NUL character or an invalid page raises
    :class:`~django.core.exceptions.ValidationError` before anything is
    written. The search vector is computed by the database.
    """
    rows = []
    for draft in drafts:
        heading_path = list(draft.heading_path)
        row = Section(
            document_version=version,
            ingest_job=job,
            ordinal=draft.ordinal,
            page_start=draft.page_start,
            page_end=draft.page_end,
            heading_path=heading_path,
            heading_text=join_headings(heading_path),
            text=draft.text,
        )
        row.clean_fields(exclude=_UNCHECKED_ROW_FIELDS)
        rows.append(row)
    return rows
