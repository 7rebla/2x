"""Measure how well the search finds the places a probe list expects (056).

Reads a probe list in JSON from standard input (format and measures:
:mod:`twox.search.evaluation`) and prints per probe and kind (keyword, vector,
combined) the rank of the first correct entry, the correct entries among the
first 5 and 10, the reciprocal rank and the time; then Recall@5, Recall@10,
MRR and times per kind, with embedding model and ``TWOX_SECTION_MAX_CHARS``.
``--json`` prints the same as JSON.

Example (the probe list need not be in the image)::

    docker compose exec -T api python manage.py evaluate_search \
        < backend/twox/search/probes/m2.json

The output holds ranks, pages, checksums and identifiers only, never the
text of a section. A probe whose files are not ingested is reported as
"not ingested" and does not count against the search. With AI features off
(E-59) only the keyword search is measured and the model service is never
contacted. An invalid probe list ends with a message and exit code 1.
"""

import io
import sys

from django.core.management.base import BaseCommand, CommandError, CommandParser

from twox.search.evaluation import (
    ProbeFormatError,
    evaluate,
    format_json,
    format_table,
    load_probes,
)

BYTE_ORDER_MARK = "\N{ZERO WIDTH NO-BREAK SPACE}"


def read_input(stream: object) -> str:
    """The text of ``stream``: UTF-8, an optional byte order mark is dropped."""
    if isinstance(stream, io.TextIOWrapper):
        if stream.isatty():
            raise CommandError(
                "Expected a probe list in JSON on standard input, for example"
                " `python manage.py evaluate_search < probes.json`."
            )
        data: bytes = stream.buffer.read()
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise CommandError("Invalid probe list: standard input is not UTF-8.") from None
    if isinstance(stream, io.TextIOBase):
        return stream.read().removeprefix(BYTE_ORDER_MARK)
    raise CommandError("Standard input cannot be read.")


class Command(BaseCommand):
    help = (
        "Measure the search with a probe list in JSON read from standard input: rank,"
        " Recall@5, Recall@10, MRR and time per probe for keyword, vector and combined search."
        " Prints no section texts."
    )
    # Lets tests pass the probe list without a real standard input.
    stealth_options = ("stdin",)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--json", action="store_true", help="Print the result as JSON instead of tables."
        )

    def handle(self, *args: object, **options: object) -> None:
        text = read_input(options.get("stdin") or sys.stdin)
        try:
            probes = load_probes(text)
        except ProbeFormatError as error:
            raise CommandError(f"Invalid probe list: {error}") from None
        report = evaluate(probes)
        output = format_json(report) if options["json"] else format_table(report)
        self.stdout.write(output, ending="")
