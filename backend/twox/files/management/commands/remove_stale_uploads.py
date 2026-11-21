"""Remove temporary upload files that a killed process left behind.

The file system storage writes every upload to
``<TWOX_MEDIA_ROOT>/tmp/upload-*.part`` first and removes that file itself in
every normal case. Only a hard stop of the process (SIGKILL, out of memory)
leaves one behind. This command deletes such files once they are older than
a period (24 hours by default), so that no upload still being written is
touched. Run it in the ``api`` or ``worker`` container, for example:

    python manage.py remove_stale_uploads --older-than-hours 24
"""

import math
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from twox.files.storage import TMP_DIR_NAME

#: Name pattern of the temporary files of ``FileSystemBlobStorage.store_blob``.
TEMP_FILE_PATTERN = "upload-*.part"

DEFAULT_MIN_AGE_HOURS = 24.0


def remove_stale_uploads(root: Path, min_age_seconds: float) -> list[Path]:
    """Delete temporary upload files below ``root`` older than ``min_age_seconds``.

    Returns the deleted paths. Only regular files matching
    :data:`TEMP_FILE_PATTERN` directly in the temporary folder are touched.
    """
    tmp_dir = root / TMP_DIR_NAME
    if not tmp_dir.is_dir():
        return []
    cutoff = time.time() - min_age_seconds
    removed = []
    for path in sorted(tmp_dir.glob(TEMP_FILE_PATTERN)):
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_mtime >= cutoff:
                continue
            path.unlink()
        except FileNotFoundError:
            # Finished or removed by its own process in the meantime.
            continue
        removed.append(path)
    return removed


class Command(BaseCommand):
    help = "Delete temporary upload files (tmp/upload-*.part) older than a period."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--older-than-hours",
            type=float,
            default=DEFAULT_MIN_AGE_HOURS,
            help=f"Minimum age in hours, at least 1 (default {DEFAULT_MIN_AGE_HOURS:g}).",
        )

    def handle(self, *args: object, **options: object) -> None:
        hours = options["older_than_hours"]
        # int from code (call_command), float from the command line; bool is
        # an int but no period. nan and inf would pass a plain "< 1" check.
        if (
            isinstance(hours, bool)
            or not isinstance(hours, int | float)
            or not math.isfinite(hours)
            or hours < 1
        ):
            raise CommandError("--older-than-hours must be a finite number of at least 1.")
        removed = remove_stale_uploads(Path(settings.TWOX_MEDIA_ROOT), hours * 3600)
        for path in removed:
            self.stdout.write(f"Removed {path.name}")
        self.stdout.write(f"Removed {len(removed)} stale temporary upload file(s).")
