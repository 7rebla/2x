"""Command remove_stale_uploads: leftovers of killed uploads go, everything else stays."""

import os
import time
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from twox.files.management.commands.remove_stale_uploads import remove_stale_uploads

HOUR = 3600


def make_file(path: Path, age_seconds: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"partial")
    stamp = time.time() - age_seconds
    os.utime(path, (stamp, stamp))
    return path


def test_only_old_temporary_upload_files_are_removed(media_root: Path) -> None:
    tmp = media_root / "tmp"
    old = make_file(tmp / "upload-old.part", 25 * HOUR)
    fresh = make_file(tmp / "upload-fresh.part", 1 * HOUR)
    other_name = make_file(tmp / "other-old.part", 25 * HOUR)
    blob = make_file(media_root / "sha256" / "ab" / "cd" / "upload-x.part", 25 * HOUR)

    removed = remove_stale_uploads(media_root, 24 * HOUR)

    assert removed == [old]
    assert not old.exists()
    assert fresh.exists()
    assert other_name.exists()
    assert blob.exists()


def test_symbolic_links_are_left_alone(media_root: Path, tmp_path: Path) -> None:
    target = make_file(tmp_path / "elsewhere.txt", 25 * HOUR)
    link = media_root / "tmp" / "upload-link.part"
    link.parent.mkdir()
    link.symlink_to(target)

    assert remove_stale_uploads(media_root, 24 * HOUR) == []
    assert link.is_symlink()
    assert target.exists()


def test_missing_tmp_folder_is_fine(media_root: Path) -> None:
    assert remove_stale_uploads(media_root, 24 * HOUR) == []


def test_command_reports_what_it_removed(media_root: Path) -> None:
    make_file(media_root / "tmp" / "upload-a.part", 3 * HOUR)
    make_file(media_root / "tmp" / "upload-b.part", 1 * HOUR)
    out = StringIO()

    call_command("remove_stale_uploads", "--older-than-hours", "2", stdout=out)

    assert out.getvalue().splitlines() == [
        "Removed upload-a.part",
        "Removed 1 stale temporary upload file(s).",
    ]


def test_command_default_is_24_hours(media_root: Path) -> None:
    kept = make_file(media_root / "tmp" / "upload-a.part", 23 * HOUR)
    out = StringIO()

    call_command("remove_stale_uploads", stdout=out)

    assert kept.exists()
    assert out.getvalue().strip() == "Removed 0 stale temporary upload file(s)."


def test_command_refuses_a_period_below_one_hour(media_root: Path) -> None:
    with pytest.raises(CommandError, match="at least 1"):
        call_command("remove_stale_uploads", "--older-than-hours", "0.5")
