"""Create an account with a role, or update it with ``--update``.

Usage::

    python manage.py create_account <username> --role manage|read [--update]

The password comes from the environment variable ``TWOX_ACCOUNT_PASSWORD`` or,
without it, is asked for twice in a terminal. It is never a command-line
argument (those show up in process lists and shell histories) and it never
appears in the output. Without the variable and without a terminal the command
fails. The password must pass the project's password validators.

An existing account is an error unless ``--update`` is given. With
``--update`` the command sets the role and the password of the account (and
creates it if it is missing), so it can run again and again, for example in
CI. The command never sets ``is_staff`` or ``is_superuser``.
"""

import getpass
import os
import sys

from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import IntegrityError, transaction

from twox.accounts.models import User
from twox.accounts.roles import ROLES, Role

PASSWORD_VARIABLE = "TWOX_ACCOUNT_PASSWORD"


def _messages(error: ValidationError) -> str:
    return " ".join(error.messages)


def _role(value: object) -> Role:
    for role in ROLES:
        if value == role:
            return role
    raise CommandError(f"--role must be one of: {', '.join(ROLES)}.")


def _is_terminal(stream: object) -> bool:
    isatty = getattr(stream, "isatty", None)
    return callable(isatty) and isatty() is True


def _read_password(is_terminal: bool) -> str:
    """Return the password from the environment or, in a terminal, from the user."""
    password = os.environ.get(PASSWORD_VARIABLE)
    if password is not None:
        if not password:
            raise CommandError(f"{PASSWORD_VARIABLE} is set but empty.")
        return password
    if not is_terminal:
        raise CommandError(
            f"No password: set {PASSWORD_VARIABLE} or run the command in a terminal."
        )
    first = getpass.getpass("Password: ")
    second = getpass.getpass("Password (again): ")
    if first != second:
        raise CommandError("The two passwords differ.")
    if not first:
        raise CommandError("The password is empty.")
    return first


class Command(BaseCommand):
    help = (
        "Create an account with the role manage or read; with --update, set the role and"
        f" password of an existing account. The password comes from {PASSWORD_VARIABLE}"
        " or is asked for in a terminal."
    )
    # Lets tests pass a stand-in for the terminal.
    stealth_options = ("stdin",)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("username", help="User name of the account.")
        parser.add_argument("--role", required=True, choices=ROLES, help="Role of the account.")
        parser.add_argument(
            "--update",
            action="store_true",
            help="Set role and password if the account exists already (else create it).",
        )

    def handle(self, *args: object, **options: object) -> None:
        username = options["username"]
        role = _role(options["role"])
        update = options["update"] is True
        if not isinstance(username, str):
            raise CommandError("The user name must be text.")
        is_terminal = _is_terminal(options.get("stdin") or sys.stdin)

        user = User.objects.filter(username=username).first()
        created = user is None
        if user is None:
            user = User(username=username)
        elif not update:
            raise CommandError(
                f"The account {username!r} exists already. Use --update to set its"
                " role and password."
            )

        try:
            user.full_clean(exclude=["password"])
        except ValidationError as error:
            raise CommandError(f"Invalid account: {_messages(error)}") from None

        password = _read_password(is_terminal)
        try:
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError(f"Password rejected: {_messages(error)}") from None

        try:
            with transaction.atomic():
                user.set_password(password)
                user.save()
                role_groups = [Group.objects.get_or_create(name=name)[0] for name in ROLES]
                target = next(group for group in role_groups if group.name == role)
                # Remove only role groups the account really has: the change
                # log records every group passed to remove() (E-43).
                user.groups.remove(*user.groups.filter(name__in=ROLES).exclude(pk=target.pk))
                user.groups.add(target)
        except IntegrityError:
            raise CommandError(
                f"The account {username!r} could not be saved; it may have been created"
                " at the same time. Run the command again."
            ) from None

        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} account {username!r} with role {role!r}.")
