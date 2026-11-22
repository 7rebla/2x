"""Ask the test questions through the answer service and judge the answers (M3, 127).

Reads the test questions (``--questions PATH``, by default
``/testfactory/questions.yaml``, as mounted in ``backend-dev``; ``-`` reads
them from standard input) and the expected places of a probe list
(``--probes NAME|PATH``, by default ``m3``, i.e. ``twox/search/probes/m3.json``).
Every question is asked ``--runs N`` times (default 3, D5) through the answer
service, without restriction to devices or plants, and judged automatically
(definition of "right": :mod:`twox.answers.evaluation`). The report prints per
question the final verdict, the right runs of N, the rank of the evidence and
the times, per run the details, then "x/10 right" per run and over the
questions under both acceptance rules. ``--json`` prints the same as JSON.

Options: ``--mode majority|strict`` (a question is right in more than half or
in all of its runs), ``--control-mode strict|majority`` (the control question;
strict unless asked), ``--rule per-question|per-run`` (which rule gives
``passed``), ``--wording yaml|probe`` (ask the question of ``questions.yaml``
without its notes, or the query of its first probe), ``--literal`` (ignore
``key_fact_alternatives``), ``--only ID[,ID...]`` (a part of the questions).

Examples::

    docker compose run --rm backend-dev python manage.py evaluate_answers --runs 3 --json
    docker compose exec -T api python manage.py evaluate_answers --questions - \
        < testfactory/questions.yaml

The output holds identifiers, pages, heading paths of the probes, numbers,
statuses and codes; never a question, an answer or a section text. With the
AI features off (E-59) nothing is asked and the report says "not measured".
Invalid input ends with a message and exit code 1; a finished measurement
ends with exit code 0 even when M3 is not passed (see ``passed``).
"""

import io
import re
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError, CommandParser

from twox.answers.evaluation import (
    DEFAULT_RUNS,
    Mode,
    QuestionFormatError,
    Rule,
    Wording,
    evaluate,
    format_json,
    format_table,
    load_questions,
    question_places,
)
from twox.search.evaluation import ProbeFormatError, probe_list_text

DEFAULT_QUESTIONS = "/testfactory/questions.yaml"
DEFAULT_PROBES = "m3"
BYTE_ORDER_MARK = "\N{ZERO WIDTH NO-BREAK SPACE}"
_PROBE_LIST_NAME = re.compile(r"[a-z0-9-]+")


def read_stdin(stream: object) -> str:
    """The text of ``stream``: UTF-8, an optional byte order mark is dropped."""
    if isinstance(stream, io.TextIOWrapper):
        if stream.isatty():
            raise CommandError(
                "Expected test questions in JSON on standard input with --questions -."
            )
        data: bytes = stream.buffer.read()
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise CommandError("Invalid test questions: standard input is not UTF-8.") from None
    if isinstance(stream, io.TextIOBase):
        return stream.read().removeprefix(BYTE_ORDER_MARK)
    raise CommandError("Standard input cannot be read.")


def read_file(path: str, what: str) -> str:
    """The UTF-8 text of the file ``path``; :class:`CommandError` if it cannot be read."""
    try:
        return Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise CommandError(
            f"Invalid {what}: cannot read {path!r} ({type(error).__name__})."
        ) from None


def parse_only(text: str) -> set[int]:
    """The question ids of ``--only`` ("1,2,6"); :class:`CommandError` if invalid."""
    ids: set[int] = set()
    for part in text.split(","):
        value = part.strip()
        if not value.isdigit() or int(value) < 1:
            raise CommandError(f"Invalid --only: {value!r} is not a question id.")
        ids.add(int(value))
    return ids


class Command(BaseCommand):
    help = (
        "Ask the test questions through the answer service and judge the answers: verdict,"
        " right runs, evidence rank and times per question, x/10 per run and overall."
        " Prints no question, answer or section text."
    )
    # Like ask and check_llm: the warning about a missing chat model would
    # otherwise precede every report.
    requires_system_checks = []  # noqa: RUF012
    # Lets tests pass the questions without a real standard input.
    stealth_options = ("stdin",)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--questions",
            default=DEFAULT_QUESTIONS,
            metavar="PATH",
            help=f"Test questions in JSON (default {DEFAULT_QUESTIONS}); '-' reads standard input.",
        )
        parser.add_argument(
            "--probes",
            default=DEFAULT_PROBES,
            metavar="NAME|PATH",
            help="Probe list with the expected places: a name of twox/search/probes/"
            f" (default {DEFAULT_PROBES}) or the path of a JSON file.",
        )
        parser.add_argument(
            "--runs",
            type=int,
            default=DEFAULT_RUNS,
            help=f"Runs per question (default {DEFAULT_RUNS}).",
        )
        parser.add_argument(
            "--mode",
            choices=[mode.value for mode in Mode],
            default=Mode.MAJORITY.value,
            help="A question is right in more than half (majority) or in all (strict) of its runs.",
        )
        parser.add_argument(
            "--control-mode",
            choices=[mode.value for mode in Mode],
            default=Mode.STRICT.value,
            help="The same for the control question (default strict).",
        )
        parser.add_argument(
            "--rule",
            choices=[rule.value for rule in Rule],
            default=Rule.PER_QUESTION.value,
            help="Acceptance rule that decides 'passed' (default per-question).",
        )
        parser.add_argument(
            "--wording",
            choices=[wording.value for wording in Wording],
            default=Wording.YAML.value,
            help="Ask the question without its notes (yaml) or the query of its first probe.",
        )
        parser.add_argument(
            "--literal",
            action="store_true",
            help="Ignore key_fact_alternatives; key facts count as written only.",
        )
        parser.add_argument(
            "--only", metavar="ID[,ID...]", help="Ask only these questions (ids, comma-separated)."
        )
        parser.add_argument(
            "--json", action="store_true", help="Print the result as JSON instead of tables."
        )

    def _probes_text(self, value: str) -> str:
        if _PROBE_LIST_NAME.fullmatch(value) is not None:
            try:
                return probe_list_text(value)
            except ValueError as error:
                raise CommandError(f"Invalid --probes: {error}") from None
        return read_file(value, "probe list")

    def handle(self, *args: object, **options: object) -> None:
        runs = options["runs"]
        if not isinstance(runs, int) or runs < 1:
            raise CommandError("Invalid --runs: expected a whole number from 1.")
        path = str(options["questions"])
        if path == "-":
            text = read_stdin(options.get("stdin") or sys.stdin)
        else:
            text = read_file(path, "test questions")
        try:
            questions = load_questions(text)
        except QuestionFormatError as error:
            raise CommandError(f"Invalid test questions: {error}") from None
        try:
            places = question_places(self._probes_text(str(options["probes"])))
        except ProbeFormatError as error:
            raise CommandError(f"Invalid probe list: {error}") from None
        only = options.get("only")
        if isinstance(only, str):
            wanted = parse_only(only)
            unknown = sorted(wanted - {question.id for question in questions})
            if unknown:
                raise CommandError(
                    f"Invalid --only: no test question {', '.join(map(str, unknown))}."
                )
            questions = [question for question in questions if question.id in wanted]
        report = evaluate(
            questions,
            places,
            runs=runs,
            mode=Mode(str(options["mode"])),
            control_mode=Mode(str(options["control_mode"])),
            rule=Rule(str(options["rule"])),
            wording=Wording(str(options["wording"])),
            literal=bool(options["literal"]),
        )
        output = format_json(report) if options["json"] else format_table(report)
        self.stdout.write(output, ending="")
