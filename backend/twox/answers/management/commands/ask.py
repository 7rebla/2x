"""Ask a question through the answer service (work order 126); for the test setup.

``manage.py ask "<question>" [--device ID ...] [--plant ID ...] [--seed N] [--json]``

Without ``--json`` the text pieces appear on standard output as they come.
After them follow the sources (``[n] title, version, pages`` or the heading
path), a line ``final:`` with the checked text when it differs from the
streamed one, and a last line ``status: <status>`` with the number of valid
citations and of removed sentences.

With ``--json`` every event is one line of JSON (JSON Lines), as
:func:`twox.answers.types.to_json` writes it; standard output then holds
nothing else.

An ``error`` event prints ``FAILED: <code>`` on standard error (exit code 1).
With the AI features off (E-59) the command contacts nothing and prints one
neutral line ``DISABLED:`` (exit code 0); with ``--json`` that line goes to
standard error, after the JSON line of the event. An empty question is an
error of the command (exit code 1).

The command shows answer and sources on the terminal - that is its purpose -
but never writes them to a log or a file.
"""

import json
import sys
from collections.abc import Iterator

from django.core.management.base import BaseCommand, CommandError, CommandParser

from twox.answers import service, types
from twox.answers.types import (
    AnswerEvent,
    DeltaEvent,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    SourceRef,
    SourcesEvent,
)

DISABLED_LINE = (
    "DISABLED: AI features are not enabled (TWOX_AI_ENABLED is false);"
    " nothing was searched and the model service was not contacted"
)


def describe_source(source: SourceRef) -> str:
    """One line for a source: ``[n] title, version, pages`` or the heading path."""
    location = source.locations[0]
    parts = [f"[{source.n}] {location.document_title}", f"version {location.version_number}"]
    if source.page_start is not None:
        end = source.page_end if source.page_end is not None else source.page_start
        parts.append(
            f"p. {source.page_start}"
            if end == source.page_start
            else f"pp. {source.page_start}-{end}"
        )
    elif source.heading_path:
        parts.append(" / ".join(source.heading_path))
    return ", ".join(parts)


def status_line(done: DoneEvent) -> str:
    """The last line of the text output."""
    numbers = ", ".join(str(n) for n in done.cited) or "none"
    return (
        f"status: {done.status.value} ({len(done.cited)} valid citation(s): {numbers};"
        f" {done.removed_sentences} removed sentence(s))"
    )


class Command(BaseCommand):
    help = (
        "Answer a question from the ingested documents through the answer service."
        " Streams the answer, then lists the sources and the status; --json prints"
        " every event as one line of JSON. FAILED: <code> on standard error and exit"
        " code 1 if the answer fails; DISABLED: (exit code 0) if TWOX_AI_ENABLED is off."
    )
    # The system checks would warn about an empty TWOX_CHAT_MODEL before every answer.
    requires_system_checks = []  # noqa: RUF012

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("question", help="The question, in quotes.")
        parser.add_argument(
            "--device",
            dest="device_ids",
            action="append",
            type=int,
            default=None,
            metavar="ID",
            help="Only sources of this device (id); may be given more than once.",
        )
        parser.add_argument(
            "--plant",
            dest="plant_ids",
            action="append",
            type=int,
            default=None,
            metavar="ID",
            help="Only sources of this plant (id); may be given more than once.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            metavar="N",
            help="Seed for the chat model (for repeatable runs); none by default.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print every event as one line of JSON (JSON Lines).",
        )

    def handle(self, *args: object, **options: object) -> None:
        question = options["question"]
        if not isinstance(question, str) or not question.strip():
            raise CommandError("The question must not be empty.")
        device_ids = _ids(options["device_ids"])
        plant_ids = _ids(options["plant_ids"])
        seed = options["seed"]
        if seed is not None and not isinstance(seed, int):
            raise CommandError("--seed must be a whole number.")

        events = service.answer(question, device_ids=device_ids, plant_ids=plant_ids, seed=seed)
        printer = self._print_json if options["json"] else self._print_text
        try:
            error = printer(events)
        finally:
            close = getattr(events, "close", None)
            if callable(close):
                close()
        if error is None:
            return
        if error.code is ErrorCode.AI_DISABLED:
            # E-59: a neutral state, not an error; nothing was contacted.
            (self.stderr if options["json"] else self.stdout).write(DISABLED_LINE)
            return
        self.stderr.write(f"FAILED: {error.code.value}")
        sys.exit(1)

    def _print_json(self, events: Iterator[AnswerEvent]) -> ErrorEvent | None:
        error: ErrorEvent | None = None
        for event in events:
            self.stdout.write(json.dumps(types.to_json(event), ensure_ascii=False))
            self.stdout.flush()
            if isinstance(event, ErrorEvent):
                error = event
        return error

    def _print_text(self, events: Iterator[AnswerEvent]) -> ErrorEvent | None:
        sources: list[SourceRef] = []
        streamed: list[str] = []
        for event in events:
            match event:
                case SourcesEvent():
                    sources = list(event.sources)
                case DeltaEvent():
                    streamed.append(event.text)
                    self.stdout.write(event.text, ending="")
                    self.stdout.flush()
                case DoneEvent():
                    self._print_end(event, sources, "".join(streamed))
                case ErrorEvent():
                    if streamed:
                        self.stdout.write("")
                    return event
        return None

    def _print_end(self, done: DoneEvent, sources: list[SourceRef], streamed: str) -> None:
        if streamed:
            self.stdout.write("")
        self.stdout.write("")
        self.stdout.write("sources:" if sources else "sources: none")
        for source in sources:
            self.stdout.write("  " + describe_source(source))
        if done.final_text != streamed:
            self.stdout.write("final:")
            self.stdout.write(done.final_text)
        self.stdout.write(status_line(done))


def _ids(value: object) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
        raise CommandError("--device and --plant take whole numbers.")
    return list(value)
