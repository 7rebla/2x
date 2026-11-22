"""Start the ingestion of existing versions; a dry run unless ``--commit`` is given.

Usage::

    python manage.py ingest_versions --user <name> [--commit]
        [--missing] [--failed] [--stuck MINUTES] [--all] [--version ID ...]

At least one selection is needed; several are combined:

``--missing``
    versions without any ingest job (for example uploaded before M2);
``--failed``
    versions whose newest job is ``failed``;
``--stuck MINUTES``
    jobs that are ``queued`` or ``running`` and were not updated for at least
    MINUTES minutes become ``failed`` (``timeout``) and their version is
    started again. Every status query at Docling updates a running job (at
    least once per ``TWOX_INGEST_POLL_MAX_SECONDS``, work order 048), so this
    takes jobs that are no longer queried at all, for example after a hard
    stop of the worker. A job that is still queried ends on its own: after
    ``TWOX_INGEST_TIMEOUT_SECONDS`` from the start at Docling, or from the
    start of the job if Docling never starts the task (work order 065).
    For running jobs more than that deadline remains the safe choice;
    ``--stuck 0`` takes every active job;
``--all``
    a new job for every version (builds the sections again with the current
    ``TWOX_SECTION_MAX_CHARS``; the stored Docling answer is reused);
``--version ID``
    the version with this ID; may be given several times.

Only versions of documents of the kind ``document`` are taken; configurations
are never ingested before M5. A version with an active job that is not stuck
is left alone and counted as running.

``--user`` names the account stored as ``requested_by``; it must be active
and have the role ``manage``. Without ``--commit`` the command prints what it
would do and changes nothing (it reads the stored files for the format
check).
"""

from argparse import ArgumentTypeError
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.db.models import OuterRef, QuerySet, Subquery
from django.utils import timezone

from twox.accounts.models import User
from twox.accounts.roles import MANAGE, user_role
from twox.files.models import DocumentKind, DocumentVersion
from twox.files.storage import BlobNotFoundError
from twox.ingest.models import ACTIVE_STATUSES, IngestErrorCode, IngestJob, IngestStatus
from twox.ingest.services import (
    IngestAlreadyActiveError,
    active_job,
    check_version_format,
    request_ingest,
)

#: Detail of a job that ``--stuck`` ended.
STUCK_DETAIL = "no progress for at least {minutes} minutes; started again by ingest_versions"


def non_negative_int(value: str) -> int:
    """An argument of ``--stuck``: a whole number of minutes, 0 or more."""
    try:
        number = int(value)
    except ValueError:
        raise ArgumentTypeError(f"not a whole number: {value!r}") from None
    if number < 0:
        raise ArgumentTypeError(f"must be 0 or more: {number}")
    return number


def positive_int(value: str) -> int:
    """An argument of ``--version``: an ID, 1 or more."""
    number = non_negative_int(value)
    if number < 1:
        raise ArgumentTypeError(f"must be 1 or more: {number}")
    return number


@dataclass(frozen=True, slots=True)
class Selection:
    """Which versions the options choose."""

    missing: bool = False
    failed: bool = False
    all_versions: bool = False
    stuck_minutes: int | None = None
    version_ids: tuple[int, ...] = ()

    @classmethod
    def from_options(cls, options: Mapping[str, object]) -> Selection:
        stuck = options.get("stuck")
        ids = options.get("version_ids")
        return cls(
            missing=options.get("missing") is True,
            failed=options.get("failed") is True,
            all_versions=options.get("all_versions") is True,
            stuck_minutes=stuck if isinstance(stuck, int) else None,
            version_ids=tuple(i for i in ids if isinstance(i, int))
            if isinstance(ids, list)
            else (),
        )

    @property
    def empty(self) -> bool:
        return not (
            self.missing
            or self.failed
            or self.all_versions
            or self.stuck_minutes is not None
            or self.version_ids
        )


@dataclass
class Counts:
    """What the command did, or would do in a dry run."""

    versions: int = 0
    created: int = 0
    skipped: int = 0
    content_missing: int = 0
    running: int = 0
    stuck: int = 0

    def lines(self) -> list[str]:
        return [
            f"versions: {self.versions}",
            f"created: {self.created}",
            f"skipped (unsupported format): {self.skipped}",
            f"failed (content missing): {self.content_missing}",
            f"running (left alone): {self.running}",
            f"stuck (set to failed and started again): {self.stuck}",
        ]

    def count_job(self, job: IngestJob) -> None:
        if job.status == IngestStatus.QUEUED:
            self.created += 1
        elif job.status == IngestStatus.SKIPPED:
            self.skipped += 1
        else:
            self.content_missing += 1


def document_versions() -> QuerySet[DocumentVersion]:
    """All versions of documents of the kind ``document``."""
    return DocumentVersion.objects.filter(document__kind=DocumentKind.DOCUMENT)


def newest_status() -> Subquery:
    """The status of the newest job of a version."""
    jobs = IngestJob.objects.filter(document_version=OuterRef("pk")).order_by("-created_at", "-pk")
    return Subquery(jobs.values("status")[:1])


def stuck_jobs(cutoff: datetime) -> QuerySet[IngestJob]:
    """Active jobs of documents that were not updated since ``cutoff``."""
    return IngestJob.objects.filter(
        status__in=ACTIVE_STATUSES,
        updated_at__lte=cutoff,
        document_version__document__kind=DocumentKind.DOCUMENT,
    )


class Command(BaseCommand):
    help = (
        "Start the ingestion of existing document versions: --missing, --failed,"
        " --stuck MINUTES, --all or --version ID. Without --commit it is a dry run"
        " that changes nothing."
    )

    def create_parser(self, prog_name: str, subcommand: str, **kwargs: object) -> CommandParser:
        # --version selects versions here; it replaces Django's option that
        # prints the Django version.
        return super().create_parser(prog_name, subcommand, conflict_handler="resolve", **kwargs)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--user",
            required=True,
            help="User name of the account stored as requested_by (role manage).",
        )
        parser.add_argument(
            "--commit", action="store_true", help="Create the jobs (default: dry run)."
        )
        parser.add_argument("--missing", action="store_true", help="Versions without any job.")
        parser.add_argument(
            "--failed", action="store_true", help="Versions whose newest job failed."
        )
        parser.add_argument(
            "--stuck",
            type=non_negative_int,
            metavar="MINUTES",
            help=(
                "Jobs queued or running without an update for at least MINUTES minutes:"
                " set them to failed (timeout) and start their versions again. Every status"
                " query at Docling updates a running job, so this takes jobs that are no"
                " longer queried (for example after a hard stop of the worker); for running"
                " jobs more than TWOX_INGEST_TIMEOUT_SECONDS is the safe choice."
            ),
        )
        parser.add_argument(
            "--all", action="store_true", dest="all_versions", help="A new job for every version."
        )
        parser.add_argument(
            "--version",
            type=positive_int,
            action="append",
            dest="version_ids",
            metavar="ID",
            help="The version with this ID; may be given several times.",
        )

    def handle(self, *args: object, **options: object) -> None:
        username = options["user"]
        if not isinstance(username, str):
            raise CommandError("The user name must be text.")
        commit = options["commit"] is True
        selection = Selection.from_options(options)
        if selection.empty:
            raise CommandError(
                "Choose at least one of --missing, --failed, --stuck, --all, --version."
            )

        user = User.objects.filter(username=username, is_active=True).first()
        if user is None:
            raise CommandError(f"There is no active account {username!r}.")
        if user_role(user) != MANAGE:
            raise CommandError(f"The account {username!r} does not have the role {MANAGE!r}.")

        self._check_version_ids(selection.version_ids)
        stuck_minutes = selection.stuck_minutes
        cutoff = (
            None if stuck_minutes is None else timezone.now() - timedelta(minutes=stuck_minutes)
        )
        stuck_job_ids = (
            set() if cutoff is None else set(stuck_jobs(cutoff).values_list("pk", flat=True))
        )

        selected = self._select(selection, cutoff)
        counts = Counts(versions=len(selected))
        for version in selected:
            if commit:
                self._start(version, user, counts, stuck_job_ids, cutoff, stuck_minutes)
            else:
                self._plan(version, counts, stuck_job_ids)

        for line in counts.lines():
            self.stdout.write(line)
        if commit:
            self.stdout.write("Saved.")
        else:
            self.stdout.write("Dry run: nothing was changed. Add --commit to start the jobs.")

    def _check_version_ids(self, version_ids: Iterable[int]) -> None:
        wanted = set(version_ids)
        if not wanted:
            return
        found = dict(
            DocumentVersion.objects.filter(pk__in=wanted).values_list("pk", "document__kind")
        )
        unknown = sorted(wanted - found.keys())
        if unknown:
            raise CommandError(f"There is no document version {', '.join(map(str, unknown))}.")
        configurations = sorted(pk for pk, kind in found.items() if kind != DocumentKind.DOCUMENT)
        if configurations:
            raise CommandError(
                f"Configurations are not ingested: version {', '.join(map(str, configurations))}."
            )

    def _select(self, selection: Selection, cutoff: datetime | None) -> list[DocumentVersion]:
        versions = document_versions()
        ids: set[int] = set(selection.version_ids)
        if selection.all_versions:
            ids.update(versions.values_list("pk", flat=True))
        if selection.missing:
            ids.update(versions.filter(ingest_jobs__isnull=True).values_list("pk", flat=True))
        if selection.failed:
            failed = versions.annotate(newest_status=newest_status()).filter(
                newest_status=IngestStatus.FAILED
            )
            ids.update(failed.values_list("pk", flat=True))
        if cutoff is not None:
            ids.update(stuck_jobs(cutoff).values_list("document_version_id", flat=True))
        return list(versions.filter(pk__in=ids).select_related("document").order_by("pk"))

    def _plan(self, version: DocumentVersion, counts: Counts, stuck_job_ids: set[int]) -> None:
        """Count what ``--commit`` would do with the version; change nothing."""
        active = active_job(version)
        if active is not None:
            if active.pk not in stuck_job_ids:
                counts.running += 1
                return
            counts.stuck += 1
        try:
            check = check_version_format(version)
        except BlobNotFoundError:
            counts.content_missing += 1
            return
        if check.supported:
            counts.created += 1
        else:
            counts.skipped += 1

    def _start(
        self,
        version: DocumentVersion,
        user: User,
        counts: Counts,
        stuck_job_ids: set[int],
        cutoff: datetime | None,
        stuck_minutes: int | None,
    ) -> None:
        """End a stuck job of the version, if any, and request a new one in one transaction."""
        with transaction.atomic():
            active = active_job(version)
            if active is not None and active.pk in stuck_job_ids and cutoff is not None:
                now = timezone.now()
                # Only if it is still stuck: a job that moved on meanwhile stays.
                ended = IngestJob.objects.filter(
                    pk=active.pk, status__in=ACTIVE_STATUSES, updated_at__lte=cutoff
                ).update(
                    status=IngestStatus.FAILED,
                    error_code=IngestErrorCode.TIMEOUT,
                    error_detail=STUCK_DETAIL.format(minutes=stuck_minutes),
                    finished_at=now,
                    updated_at=now,
                )
                if ended:
                    counts.stuck += 1
            try:
                job = request_ingest(version, user)
            except IngestAlreadyActiveError:
                counts.running += 1
                return
        counts.count_job(job)
