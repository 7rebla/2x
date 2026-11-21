"""The command create_account: accounts with a role, without the admin."""

from io import StringIO

import pytest
from django.contrib.auth.models import Group
from django.core.management import CommandError, call_command

from twox.accounts.management.commands import create_account
from twox.accounts.models import User

pytestmark = pytest.mark.django_db

# Recognisable test values, long enough for the validators (12 characters).
FIRST_PASSWORD = "account-test-only-first"
SECOND_PASSWORD = "account-test-only-second"


class FakeTerminal(StringIO):
    """Stands in for standard input; tells the command whether it is a terminal."""

    def __init__(self, is_terminal: bool) -> None:
        super().__init__()
        self.is_terminal = is_terminal

    def isatty(self) -> bool:
        return self.is_terminal


@pytest.fixture
def no_password_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(create_account.PASSWORD_VARIABLE, raising=False)


def run(*args: str, password: str | None, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    """Run the command with ``password`` in the environment; return stdout and stderr."""
    if password is None:
        monkeypatch.delenv(create_account.PASSWORD_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(create_account.PASSWORD_VARIABLE, password)
    stdout = StringIO()
    stderr = StringIO()
    call_command("create_account", *args, stdout=stdout, stderr=stderr, stdin=FakeTerminal(False))
    return stdout.getvalue(), stderr.getvalue()


def role_names(user: User) -> set[str]:
    return set(user.groups.values_list("name", flat=True))


@pytest.mark.parametrize("role", ["read", "manage"])
def test_creates_account_with_role(monkeypatch: pytest.MonkeyPatch, role: str) -> None:
    stdout, stderr = run(
        "reader1", "--role", role, password=FIRST_PASSWORD, monkeypatch=monkeypatch
    )

    user = User.objects.get(username="reader1")
    assert user.check_password(FIRST_PASSWORD)
    assert role_names(user) == {role}
    assert user.is_active
    assert not user.is_staff
    assert not user.is_superuser
    assert "Created account 'reader1'" in stdout
    assert FIRST_PASSWORD not in stdout + stderr


def test_second_call_without_update_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    run("reader1", "--role", "read", password=FIRST_PASSWORD, monkeypatch=monkeypatch)

    with pytest.raises(CommandError, match="exists already") as error:
        run("reader1", "--role", "read", password=SECOND_PASSWORD, monkeypatch=monkeypatch)

    assert SECOND_PASSWORD not in str(error.value)
    assert User.objects.get(username="reader1").check_password(FIRST_PASSWORD)


def test_second_call_with_update_sets_password_and_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run("reader1", "--role", "read", password=FIRST_PASSWORD, monkeypatch=monkeypatch)

    stdout, stderr = run(
        "reader1", "--role", "manage", "--update", password=SECOND_PASSWORD, monkeypatch=monkeypatch
    )

    user = User.objects.get(username="reader1")
    assert user.check_password(SECOND_PASSWORD)
    assert not user.check_password(FIRST_PASSWORD)
    assert role_names(user) == {"manage"}
    assert not user.is_staff
    assert not user.is_superuser
    assert "Updated account 'reader1'" in stdout
    assert SECOND_PASSWORD not in stdout + stderr
    assert User.objects.filter(username="reader1").count() == 1


def test_update_is_repeatable(monkeypatch: pytest.MonkeyPatch) -> None:
    for _ in range(2):
        run(
            "reader1",
            "--role",
            "read",
            "--update",
            password=FIRST_PASSWORD,
            monkeypatch=monkeypatch,
        )

    user = User.objects.get(username="reader1")
    assert user.check_password(FIRST_PASSWORD)
    assert role_names(user) == {"read"}


def test_update_keeps_groups_other_than_roles(monkeypatch: pytest.MonkeyPatch) -> None:
    run("reader1", "--role", "read", password=FIRST_PASSWORD, monkeypatch=monkeypatch)
    user = User.objects.get(username="reader1")
    user.groups.add(Group.objects.create(name="something-else"))

    run("reader1", "--role", "manage", "--update", password=FIRST_PASSWORD, monkeypatch=monkeypatch)

    assert role_names(user) == {"manage", "something-else"}


def test_update_never_grants_staff_or_superuser(monkeypatch: pytest.MonkeyPatch) -> None:
    User.objects.create_user(username="plain", password=FIRST_PASSWORD)

    run("plain", "--role", "manage", "--update", password=SECOND_PASSWORD, monkeypatch=monkeypatch)

    user = User.objects.get(username="plain")
    assert not user.is_staff
    assert not user.is_superuser


@pytest.mark.parametrize(
    "weak",
    [
        "short-pw",  # shorter than 12 characters
        "123456789012345",  # only digits
        "password12345",  # a common password
        "reader1-4711",  # too similar to the user name
    ],
)
def test_weak_password_is_rejected(monkeypatch: pytest.MonkeyPatch, weak: str) -> None:
    with pytest.raises(CommandError, match="Password rejected") as error:
        run("reader1", "--role", "read", password=weak, monkeypatch=monkeypatch)

    assert weak not in str(error.value)
    assert not User.objects.filter(username="reader1").exists()


def test_weak_password_does_not_change_existing_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run("reader1", "--role", "read", password=FIRST_PASSWORD, monkeypatch=monkeypatch)

    with pytest.raises(CommandError, match="Password rejected"):
        run("reader1", "--role", "manage", "--update", password="short-pw", monkeypatch=monkeypatch)

    user = User.objects.get(username="reader1")
    assert user.check_password(FIRST_PASSWORD)
    assert role_names(user) == {"read"}


def test_empty_password_variable_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(CommandError, match="empty"):
        run("reader1", "--role", "read", password="", monkeypatch=monkeypatch)

    assert not User.objects.filter(username="reader1").exists()


@pytest.mark.usefixtures("no_password_variable")
def test_without_variable_and_terminal_the_command_fails() -> None:
    with pytest.raises(CommandError, match="No password"):
        call_command(
            "create_account",
            "reader1",
            "--role",
            "read",
            stdout=StringIO(),
            stdin=FakeTerminal(False),
        )

    assert not User.objects.filter(username="reader1").exists()


@pytest.mark.usefixtures("no_password_variable")
def test_password_is_asked_for_in_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter([FIRST_PASSWORD, FIRST_PASSWORD])
    monkeypatch.setattr("getpass.getpass", lambda prompt: next(answers))
    stdout = StringIO()

    call_command(
        "create_account", "reader1", "--role", "read", stdout=stdout, stdin=FakeTerminal(True)
    )

    assert User.objects.get(username="reader1").check_password(FIRST_PASSWORD)
    assert FIRST_PASSWORD not in stdout.getvalue()


@pytest.mark.usefixtures("no_password_variable")
def test_differing_passwords_in_a_terminal_are_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter([FIRST_PASSWORD, SECOND_PASSWORD])
    monkeypatch.setattr("getpass.getpass", lambda prompt: next(answers))

    with pytest.raises(CommandError, match="differ"):
        call_command(
            "create_account",
            "reader1",
            "--role",
            "read",
            stdout=StringIO(),
            stdin=FakeTerminal(True),
        )

    assert not User.objects.filter(username="reader1").exists()


def test_password_is_no_command_line_option() -> None:
    with pytest.raises(CommandError):
        call_command("create_account", "reader1", "--role", "read", "--password", FIRST_PASSWORD)


@pytest.mark.parametrize("role", ["admin", "superuser", ""])
def test_unknown_role_is_an_error(monkeypatch: pytest.MonkeyPatch, role: str) -> None:
    with pytest.raises(CommandError):
        run("reader1", "--role", role, password=FIRST_PASSWORD, monkeypatch=monkeypatch)

    assert not User.objects.filter(username="reader1").exists()


def test_role_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(CommandError):
        run("reader1", password=FIRST_PASSWORD, monkeypatch=monkeypatch)


def test_invalid_user_name_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(CommandError, match="Invalid account"):
        run("no spaces allowed", "--role", "read", password=FIRST_PASSWORD, monkeypatch=monkeypatch)

    assert not User.objects.exists()
