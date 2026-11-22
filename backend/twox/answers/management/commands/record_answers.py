"""Record the model answers of the CI questions again (work order 135).

Runs ``tests/answers/test_ci_questions.py`` through ``pytest.main`` with
``TWOX_RECORD_ANSWERS=1``. The test then builds the same set-up as in the CI
(Docling fixtures, stand-in vectors, the same context selection) and only the
chat model is real (``TWOX_CHAT_MODEL``, temperature 0, a fixed seed). Every
check runs as well; the recording ``tests/answers/recorded/ci_questions.json``
is written only when every question that asked the model passed.

Only for a local run in ``backend-dev``, with the chat model on the host::

    docker compose run --rm -e TWOX_CHAT_MODEL=<model> backend-dev \
        python manage.py record_answers

The runtime image has no ``pytest``; there the command ends with a short
message and exit code 1. With the AI features off (E-59) or without a chat
model the command ends with exit code 1 before anything is contacted. The
cloud check of :mod:`twox.answers.llm_guard` applies unchanged.
"""

import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from twox.answers.replay import RECORD_ENV

#: The test module that records (``backend/tests/answers/test_ci_questions.py``).
TEST_MODULE = Path(__file__).resolve().parents[4] / "tests" / "answers" / "test_ci_questions.py"


class Command(BaseCommand):
    help = (
        "Record the answers of the chat model to the CI questions again"
        " (tests/answers/recorded/ci_questions.json). Only in backend-dev."
    )

    def handle(self, *args: object, **options: object) -> None:
        try:
            import pytest  # not in the runtime image
        except ImportError:
            raise CommandError("record_answers runs only in backend-dev") from None
        if not settings.TWOX_AI_ENABLED:
            raise CommandError(
                "AI features are not enabled (TWOX_AI_ENABLED is false); nothing was recorded"
            )
        if not settings.TWOX_CHAT_MODEL:
            raise CommandError("TWOX_CHAT_MODEL is empty; set the chat model to record with")
        previous = os.environ.get(RECORD_ENV)
        os.environ[RECORD_ENV] = "1"
        try:
            code = pytest.main([str(TEST_MODULE)])
        finally:
            if previous is None:
                os.environ.pop(RECORD_ENV, None)
            else:
                os.environ[RECORD_ENV] = previous
        if code != 0:
            raise CommandError(
                f"recording failed (pytest exit code {int(code)}); see the test output above"
            )
        self.stdout.write("OK: recorded tests/answers/recorded/ci_questions.json")
