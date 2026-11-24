"""Embed the sections again, for example after a change of the embedding model.

Usage::

    python manage.py embed_sections --user <name> [--missing | --all] [--commit]

``--missing`` (the default) takes every document version with sections that
have no embedding or one of another model than ``TWOX_EMBED_MODEL``, or no
pieces of that model (work order 150). After the migration of 150 that is
every version; its sections keep their embeddings, and only the pieces of
sections longer than ``TWOX_PIECE_MAX_CHARS`` ask the model (a section of one
piece gives it its own vector). ``--all`` takes every version with sections;
their embeddings and pieces are cleared first, so that all of them are
computed again (also after a change of ``TWOX_PIECE_MAX_CHARS``). ``--user``
names the account recorded as
``requested_by`` of the new jobs; it must be active and have the role
``manage``.

Without ``--commit`` the command only counts and saves nothing. With it, it
creates one ingest job per version (step ``embed``) in one transaction and
sends the task ``twox.ingest.embed`` after its commit (``ignore_result``; a
message that cannot be sent leaves its job queued, with a warning). A
version that already has a queued or running job is skipped and counted.

The newest job of a version is its ingest state in the files API (051). So
that an embedding job does not hide the result of the conversion, each new
job takes over ``page_count`` and ``conversion_error_count`` from the newest
finished conversion of the version, also one whose embedding failed (work
orders 061 and 068), together with a note on a partial conversion in
``error_detail`` for people.

The AI features are optional (E-59): with them off, the command says so
(``DISABLED:``, exit code 0) and creates nothing.
"""

import logging
from dataclasses import dataclass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q, QuerySet

from twox.accounts.models import User
from twox.accounts.roles import MANAGE, user_role
from twox.files.models import DocumentVersion
from twox.ingest import tasks
from twox.ingest.models import (
    ACTIVE_STATUSES,
    IngestJob,
    IngestStatus,
    IngestStep,
    Section,
    SectionPiece,
)
from twox.ingest.pipeline import needs_embedding, partial_detail
from twox.ingest.services import SEND_RETRY_POLICY

logger = logging.getLogger(__name__)

DISABLED_MESSAGE = (
    "DISABLED: AI features are not enabled (TWOX_AI_ENABLED is false); nothing was embedded"
)


@dataclass
class Counts:
    """Versions and sections, each created or skipped."""

    versions_created: int = 0
    sections_created: int = 0
    versions_skipped: int = 0
    sections_skipped: int = 0


def selected_sections(*, everything: bool, model: str) -> QuerySet[Section]:
    """The sections to embed: all, or those without an embedding of ``model``."""
    if everything:
        return Section.objects.all()
    return Section.objects.filter(needs_embedding(model))


def selected_versions(sections: QuerySet[Section]) -> QuerySet[DocumentVersion]:
    """The versions with at least one of ``sections``, in the order of their IDs."""
    return DocumentVersion.objects.filter(
        Exists(sections.filter(document_version=OuterRef("pk")))
    ).order_by("pk")


def is_busy(version: DocumentVersion) -> bool:
    """Whether ``version`` has a queued or running ingest job."""
    return IngestJob.objects.filter(document_version=version, status__in=ACTIVE_STATUSES).exists()


@dataclass(frozen=True)
class ConversionState:
    """What an embedding job takes over from the conversion of its version."""

    page_count: int | None = None
    conversion_error_count: int = 0
    error_detail: str = ""


def conversion_state(version: DocumentVersion) -> ConversionState:
    """Page count and conversion errors of the newest finished conversion of ``version``.

    A finished conversion has a stored Docling answer (its own or one it
    reused; an embedding job has none) and is ``done``, or ``failed`` in the
    step ``embed``: its sections were written, only the embedding failed, and
    ``_fail`` of the pipeline leaves page count, ``conversion_error_count``
    and answer in place. Without such a job the state is empty.

    ``error_detail`` is the note for people on a partial conversion only: of
    a ``done`` conversion its own note; of a failed one, whose detail is the
    embedding error, a note built from the count. Of a complete conversion
    nothing is taken over.
    """
    conversion = (
        IngestJob.objects.filter(document_version=version)
        .filter(Q(status=IngestStatus.DONE) | Q(status=IngestStatus.FAILED, step=IngestStep.EMBED))
        .exclude(result_blob_key="")
        .order_by("-created_at", "-pk")
        .only("status", "page_count", "conversion_error_count", "error_detail")
        .first()
    )
    if conversion is None:
        return ConversionState()
    count = conversion.conversion_error_count
    if count == 0:
        detail = ""
    elif conversion.status == IngestStatus.DONE:
        detail = conversion.error_detail
    else:
        detail = partial_detail(count)
    return ConversionState(
        page_count=conversion.page_count, conversion_error_count=count, error_detail=detail
    )


class Command(BaseCommand):
    help = (
        "Embed the sections of document versions again (after a change of the embedding model)."
        " Without --commit it is a dry run that saves nothing."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--user",
            required=True,
            help="User name of the account recorded as requester of the jobs (role manage).",
        )
        which = parser.add_mutually_exclusive_group()
        which.add_argument(
            "--missing",
            action="store_true",
            help=(
                "Versions with sections without an embedding or without pieces of"
                " TWOX_EMBED_MODEL (default)."
            ),
        )
        which.add_argument(
            "--all",
            action="store_true",
            help="All versions with sections; their embeddings are computed again.",
        )
        parser.add_argument(
            "--commit", action="store_true", help="Create the jobs (default: dry run)."
        )

    def handle(self, *args: object, **options: object) -> None:
        username = options["user"]
        if not isinstance(username, str):
            raise CommandError("The user name must be text.")
        everything = options["all"] is True
        commit = options["commit"] is True

        user = User.objects.filter(username=username, is_active=True).first()
        if user is None:
            raise CommandError(f"There is no active account {username!r}.")
        if user_role(user) != MANAGE:
            raise CommandError(f"The account {username!r} does not have the role {MANAGE!r}.")
        if not settings.TWOX_AI_ENABLED:
            self.stdout.write(DISABLED_MESSAGE)
            return

        model: str = settings.TWOX_EMBED_MODEL
        sections = selected_sections(everything=everything, model=model)
        counts = Counts()
        planned: list[tuple[DocumentVersion, int]] = []
        for version in selected_versions(sections):
            total = sections.filter(document_version=version).count()
            if is_busy(version):
                counts.versions_skipped += 1
                counts.sections_skipped += total
            else:
                planned.append((version, total))

        unsent: list[int] = []
        if commit:
            created = self._create_jobs(planned, user, everything, unsent)
        else:
            created = {version.pk for version, _total in planned}
        for version, total in planned:
            if version.pk in created:
                counts.versions_created += 1
                counts.sections_created += total
            else:
                counts.versions_skipped += 1
                counts.sections_skipped += total

        mode = (
            "all sections"
            if everything
            else f"sections without an embedding or without pieces of {model!r}"
        )
        self.stdout.write(f"selection: {mode}")
        verb = "created" if commit else "to create"
        self.stdout.write(
            f"versions: {counts.versions_created} jobs {verb},"
            f" {counts.versions_skipped} skipped (queued or running job)"
        )
        self.stdout.write(
            f"sections: {counts.sections_created} to embed, {counts.sections_skipped} skipped"
        )
        if unsent:
            self.stdout.write(
                f"WARNING: {len(unsent)} job(s) could not be sent to the task queue and stay"
                " queued; start them again with: manage.py ingest_versions --stuck <minutes>"
                " --user <name> --commit"
            )
        if commit:
            self.stdout.write("Saved; the worker embeds the sections.")
        else:
            self.stdout.write("Dry run: nothing was saved. Add --commit to create the jobs.")

    def _create_jobs(
        self,
        planned: list[tuple[DocumentVersion, int]],
        user: User,
        everything: bool,
        unsent: list[int],
    ) -> set[int]:
        """Create the jobs in one transaction and send embed after its commit.

        With ``--all`` the embeddings and pieces of every version that gets a
        job are cleared in the same transaction, before any message is sent. Otherwise
        the first job could take over the old vectors of a version with the
        same content that is not cleared yet (see ``_copy_embeddings`` in the
        pipeline), and nothing would be computed again. Returns the IDs of the
        versions that got a job; ``unsent`` collects the jobs whose message
        could not be sent (after the commit).
        """
        job_ids: list[int] = []
        created: set[int] = set()
        with transaction.atomic():
            for version, _total in planned:
                state = conversion_state(version)
                try:
                    with transaction.atomic():
                        job = IngestJob.objects.create(
                            document_version=version,
                            status=IngestStatus.QUEUED,
                            step=IngestStep.EMBED,
                            requested_by=user,
                            section_count=Section.objects.filter(document_version=version).count(),
                            page_count=state.page_count,
                            conversion_error_count=state.conversion_error_count,
                            error_detail=state.error_detail,
                        )
                except IntegrityError:
                    # Another job became active since the selection (one per version).
                    continue
                job_ids.append(job.pk)
                created.add(version.pk)
            if everything and created:
                Section.objects.filter(document_version_id__in=created).update(
                    embedding=None, embedding_model=""
                )
                SectionPiece.objects.filter(section__document_version_id__in=created).delete()
            transaction.on_commit(lambda: unsent.extend(send_all(job_ids)))
        return created


def send_embed(job_id: int) -> bool:
    """Send ``twox.ingest.embed`` for the job; ``False`` (and a warning) if that fails.

    As ``send_convert`` of work order 049: the job row holds the outcome, so
    no task result is kept (``ignore_result``).
    """
    try:
        tasks.embed.apply_async(
            (job_id,), ignore_result=True, retry=True, retry_policy=SEND_RETRY_POLICY
        )
    except Exception:
        logger.warning(
            "ingest: job %s could not be sent to the task queue and stays queued; start it"
            " again with: manage.py ingest_versions --stuck <minutes> --user <name> --commit",
            job_id,
            exc_info=True,
        )
        return False
    return True


def send_all(job_ids: list[int]) -> list[int]:
    """Send embed for every job; return the IDs whose message could not be sent."""
    return [job_id for job_id in job_ids if not send_embed(job_id)]
