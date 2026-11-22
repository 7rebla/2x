"""Embed the sections again, for example after a change of the embedding model.

Usage::

    python manage.py embed_sections --user <name> [--missing | --all] [--commit]

``--missing`` (the default) takes every document version with sections that
have no embedding or one of another model than ``TWOX_EMBED_MODEL``. ``--all``
takes every version with sections; their embeddings are cleared first, so
that all of them are computed again. ``--user`` names the account recorded as
``requested_by`` of the new jobs; it must be active and have the role
``manage``.

Without ``--commit`` the command only counts and saves nothing. With it, it
creates one ingest job per version (step ``embed``) and sends the task
``twox.ingest.embed`` after the commit. A version that already has a queued or
running job is skipped and counted.

The AI features are optional (E-59): with them off, the command says so
(``DISABLED:``, exit code 0) and creates nothing.
"""

from dataclasses import dataclass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, QuerySet

from twox.accounts.models import User
from twox.accounts.roles import MANAGE, user_role
from twox.files.models import DocumentVersion
from twox.ingest import tasks
from twox.ingest.models import ACTIVE_STATUSES, IngestJob, IngestStatus, IngestStep, Section
from twox.ingest.pipeline import needs_embedding

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
            help=("Versions with sections without an embedding of TWOX_EMBED_MODEL (default)."),
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
        for version in selected_versions(sections):
            total = sections.filter(document_version=version).count()
            if is_busy(version) or (commit and not self._create_job(version, user, everything)):
                counts.versions_skipped += 1
                counts.sections_skipped += total
            else:
                counts.versions_created += 1
                counts.sections_created += total

        mode = "all sections" if everything else f"sections without an embedding of {model!r}"
        self.stdout.write(f"selection: {mode}")
        verb = "created" if commit else "to create"
        self.stdout.write(
            f"versions: {counts.versions_created} {verb},"
            f" {counts.versions_skipped} skipped (queued or running job)"
        )
        self.stdout.write(
            f"sections: {counts.sections_created} {verb}, {counts.sections_skipped} skipped"
        )
        if commit:
            self.stdout.write("Saved; the worker embeds the sections.")
        else:
            self.stdout.write("Dry run: nothing was saved. Add --commit to create the jobs.")

    def _create_job(self, version: DocumentVersion, user: User, everything: bool) -> bool:
        """Create the job of ``version`` and send embed after the commit; ``False`` if busy."""
        try:
            with transaction.atomic():
                job = IngestJob.objects.create(
                    document_version=version,
                    status=IngestStatus.QUEUED,
                    step=IngestStep.EMBED,
                    requested_by=user,
                    section_count=Section.objects.filter(document_version=version).count(),
                )
                if everything:
                    Section.objects.filter(document_version=version).update(
                        embedding=None, embedding_model=""
                    )
                job_id = job.pk
                transaction.on_commit(lambda: tasks.embed.delay(job_id))
        except IntegrityError:
            # Another job became active since the selection (one per version).
            return False
        return True
