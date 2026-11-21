"""Management command import_devices."""

from io import StringIO
from pathlib import Path

import pytest
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError

from tests.accounts.users import make_user
from tests.assets.csv_files import TESTFACTORY_DEVICES_CSV, csv_text, row
from twox.accounts.models import User
from twox.assets.models import Device, Site

pytestmark = pytest.mark.django_db

SUMMARY_CREATED = [
    "rows: 14",
    "sites: 1 created, 0 updated, 0 unchanged",
    "areas: 3 created, 0 updated, 0 unchanged",
    "plants: 10 created, 0 updated, 0 unchanged",
    "devices: 13 created, 0 updated, 0 unchanged",
]


@pytest.fixture
def importer() -> User:
    user = make_user("manage")
    assert user is not None
    return user


def run(*args: str) -> tuple[list[str], list[str]]:
    stdout = StringIO()
    stderr = StringIO()
    call_command("import_devices", *args, stdout=stdout, stderr=stderr)
    return stdout.getvalue().splitlines(), stderr.getvalue().splitlines()


def test_without_commit_it_is_a_dry_run(importer: User) -> None:
    out, err = run(str(TESTFACTORY_DEVICES_CSV), "--user", importer.username)

    assert out == [*SUMMARY_CREATED, "Dry run: nothing was saved. Add --commit to save."]
    assert err == []
    assert Site.objects.count() == 0


def test_commit_saves_and_a_second_run_changes_nothing(importer: User) -> None:
    first, _ = run(str(TESTFACTORY_DEVICES_CSV), "--user", importer.username, "--commit")
    second, _ = run(str(TESTFACTORY_DEVICES_CSV), "--user", importer.username, "--commit")

    assert first == [*SUMMARY_CREATED, "Saved."]
    assert second == [
        "rows: 14",
        "sites: 0 created, 0 updated, 1 unchanged",
        "areas: 0 created, 0 updated, 3 unchanged",
        "plants: 0 created, 0 updated, 10 unchanged",
        "devices: 0 created, 0 updated, 13 unchanged",
        "Saved.",
    ]
    assert Device.objects.count() == 13


def test_change_log_names_the_user_of_the_command(importer: User) -> None:
    run(str(TESTFACTORY_DEVICES_CSV), "--user", importer.username, "--commit")

    entries = LogEntry.objects.filter(content_type=ContentType.objects.get_for_model(Device))
    assert entries.count() == 13
    assert {entry.actor for entry in entries} == {importer}


def test_errors_are_printed_and_nothing_is_saved(importer: User, tmp_path: Path) -> None:
    path = tmp_path / "devices.csv"
    rows = [row(), row(device_id="second", ip_address="bad"), row(device_name="Again")]
    path.write_text(csv_text(rows), encoding="utf-8")
    stderr = StringIO()

    with pytest.raises(CommandError, match=r"2 error\(s\) in .*; nothing was saved\."):
        call_command(
            "import_devices", str(path), "--user", importer.username, "--commit", stderr=stderr
        )

    assert stderr.getvalue().splitlines() == [
        "line 3, ip_address: Enter a valid IPv4 or IPv6 address.",
        "line 4, device_id: The device press-plc appears in line 2 already.",
    ]
    assert Site.objects.count() == 0


def test_file_error_is_printed_without_column(importer: User, tmp_path: Path) -> None:
    path = tmp_path / "devices.csv"
    path.write_bytes(b"\xff\xfe")
    stderr = StringIO()

    with pytest.raises(CommandError):
        call_command("import_devices", str(path), "--user", importer.username, stderr=stderr)

    assert stderr.getvalue().startswith("line 1: The file is not UTF-8")


def test_missing_file_is_an_error(importer: User, tmp_path: Path) -> None:
    with pytest.raises(CommandError, match="Cannot read"):
        run(str(tmp_path / "missing.csv"), "--user", importer.username)


def test_directory_is_an_error(importer: User, tmp_path: Path) -> None:
    with pytest.raises(CommandError, match="Cannot read"):
        run(str(tmp_path), "--user", importer.username)


def test_unknown_user_is_an_error() -> None:
    with pytest.raises(CommandError, match="no active account 'nobody'"):
        run(str(TESTFACTORY_DEVICES_CSV), "--user", "nobody", "--commit")

    assert Site.objects.count() == 0


def test_inactive_user_is_an_error(importer: User) -> None:
    importer.is_active = False
    importer.save()

    with pytest.raises(CommandError, match="no active account"):
        run(str(TESTFACTORY_DEVICES_CSV), "--user", importer.username, "--commit")


@pytest.mark.parametrize("kind", ["no_role", "read"])
def test_user_without_role_manage_is_an_error(kind: str) -> None:
    user = make_user(kind)
    assert user is not None

    with pytest.raises(CommandError, match="does not have the role 'manage'"):
        run(str(TESTFACTORY_DEVICES_CSV), "--user", user.username, "--commit")

    assert Site.objects.count() == 0


def test_user_is_required() -> None:
    with pytest.raises(CommandError, match="--user"):
        run(str(TESTFACTORY_DEVICES_CSV))
