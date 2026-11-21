"""Import a device list from a CSV file (E-44); a dry run unless ``--commit`` is given.

Usage::

    python manage.py import_devices <path> --user <name> [--commit]

The file has the format of ``testfactory/layout/devices.csv`` (see
``twox.assets.csv_import``). ``--user`` names the account that the change log
records as the actor; it must be active and have the role ``manage``. Without
``--commit`` the command checks the file and prints what an import would do,
and saves nothing. With errors it prints them, saves nothing and exits with
code 1.
"""

from django.core.management.base import BaseCommand, CommandError, CommandParser

from twox.accounts.models import User
from twox.accounts.roles import MANAGE, user_role
from twox.assets.csv_import import ImportReport, RowError, apply, parse


def format_error(error: RowError) -> str:
    """One error as a line of output: ``line 3, ip_address: message``."""
    place = [f"line {error.line}"] if error.line is not None else ["file"]
    if error.column is not None:
        place.append(error.column)
    return f"{', '.join(place)}: {error.message}"


def format_counts(report: ImportReport) -> list[str]:
    """The counts of each level as lines of output."""
    return [
        f"{name}: {counts.created} created, {counts.updated} updated, {counts.unchanged} unchanged"
        for name, counts in (
            ("sites", report.sites),
            ("areas", report.areas),
            ("plants", report.plants),
            ("devices", report.devices),
        )
    ]


class Command(BaseCommand):
    help = (
        "Import a device list (CSV in the format of testfactory/layout/devices.csv)."
        " Without --commit it is a dry run that saves nothing."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("path", help="Path of the CSV file.")
        parser.add_argument(
            "--user",
            required=True,
            help="User name of the account named as the actor in the change log (role manage).",
        )
        parser.add_argument(
            "--commit", action="store_true", help="Save the changes (default: dry run)."
        )

    def handle(self, *args: object, **options: object) -> None:
        path = options["path"]
        username = options["user"]
        commit = options["commit"] is True
        if not isinstance(path, str) or not isinstance(username, str):
            raise CommandError("Path and user name must be text.")

        user = User.objects.filter(username=username, is_active=True).first()
        if user is None:
            raise CommandError(f"There is no active account {username!r}.")
        if user_role(user) != MANAGE:
            raise CommandError(f"The account {username!r} does not have the role {MANAGE!r}.")

        try:
            with open(path, "rb") as stream:
                parsed = parse(stream)
        except OSError as error:
            raise CommandError(f"Cannot read {path}: {error.strerror or error}") from None

        report = apply(parsed, user, dry_run=not commit)
        if report.errors:
            for problem in report.errors:
                self.stderr.write(format_error(problem))
            raise CommandError(f"{len(report.errors)} error(s) in {path}; nothing was saved.")

        self.stdout.write(f"rows: {report.rows}")
        for line in format_counts(report):
            self.stdout.write(line)
        if report.saved:
            self.stdout.write("Saved.")
        else:
            self.stdout.write("Dry run: nothing was saved. Add --commit to save.")
