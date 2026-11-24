"""The command ``ask`` (work order 126).

The chat model is :class:`~twox.answers.chat.FakeChatModel`, put in place of
:func:`twox.answers.chat.get_chat_model`; the context selection is the real
one over the database with :class:`FakeEmbedder`. No test reaches a real
model service. All texts are written for these tests.
"""

import json
import socket
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pytest_django.fixtures import Settings

from tests.search.fake_embedder import FakeEmbedder, at_angle, embed
from tests.search.test_keyword_search import add_sections, make_device, make_document, make_plant
from twox.answers import chat as chat_module
from twox.answers.chat import ChatRejectedError, FakeChatModel
from twox.answers.management.commands.ask import DISABLED_LINE
from twox.answers.types import NO_EVIDENCE_TEXT, DoneEvent, SourcesEvent, from_json

# The sections of these tests are a few words long (work order 153).
pytestmark = pytest.mark.usefixtures("every_text_a_source")

QUESTION = "Wie viel hält der Greifer?"
TEXT_A = "Der Greifer G-12 hält höchstens 5 kg."
TEXT_B = "Der Greifer G-14 hält höchstens 8 kg."


def run_ask(*args: str) -> tuple[int, str, str]:
    """Run the command; return exit code, standard output and standard error."""
    stdout, stderr = StringIO(), StringIO()
    try:
        call_command("ask", *args, stdout=stdout, stderr=stderr)
    except SystemExit as exit_:
        assert isinstance(exit_.code, int)
        return exit_.code, stdout.getvalue(), stderr.getvalue()
    return 0, stdout.getvalue(), stderr.getvalue()


def use_chat(monkeypatch: pytest.MonkeyPatch, chat: FakeChatModel) -> FakeChatModel:
    monkeypatch.setattr(chat_module, "get_chat_model", lambda: chat)
    return chat


@pytest.fixture
def devices(fake_embedder: FakeEmbedder) -> tuple[int, int]:
    """Two devices, each with one section close to the question."""
    plant = make_plant()
    device_a = make_device(plant, "gripper-a")
    device_b = make_device(plant, "gripper-b")
    (section_a,) = add_sections(make_document(device_a, title="Handbuch A"), TEXT_A, page=4)
    (section_b,) = add_sections(
        make_document(device_b, title="Handbuch B"), TEXT_B, page=None, headings=("Daten", "Last")
    )
    embed(section_a, at_angle(10, axis=1))
    embed(section_b, at_angle(20, axis=2))
    return device_a.pk, device_b.pk


@pytest.mark.django_db
def test_json_prints_one_valid_line_per_event(
    devices: tuple[int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    chat = use_chat(monkeypatch, FakeChatModel(["Der Greifer G-12 ", "hält 5 kg [1]."]))

    code, output, errors = run_ask(QUESTION, "--json", "--seed", "11")

    assert code == 0
    assert errors == ""
    lines = output.splitlines()
    events = [from_json(json.loads(line)) for line in lines]
    assert [event.type for event in events] == ["sources", "delta", "delta", "done"]
    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert done.cited == [1]
    assert chat.calls[0].seed == 11
    assert chat.close_count == 1


@pytest.mark.django_db
def test_text_output_streams_and_ends_with_the_status(
    devices: tuple[int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    use_chat(monkeypatch, FakeChatModel(["Der Greifer G-12 ", "hält 5 kg [1]."]))

    code, output, errors = run_ask(QUESTION)

    assert code == 0
    assert errors == ""
    lines = output.splitlines()
    assert lines[0] == "Der Greifer G-12 hält 5 kg [1]."
    assert "  [1] Handbuch A, version 1, p. 4" in lines
    assert "  [2] Handbuch B, version 1, Daten / Last" in lines
    assert "final:" not in lines
    assert lines[-1].startswith("status: answered (1 valid citation(s): 1;")
    assert lines[-1].endswith("0 removed sentence(s))")


@pytest.mark.django_db
def test_text_output_shows_the_final_text_when_it_differs(
    devices: tuple[int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    use_chat(monkeypatch, FakeChatModel(["Er wiegt 9 kg [3]."]))

    code, output, _errors = run_ask(QUESTION)

    lines = output.splitlines()
    assert code == 0
    assert lines[lines.index("final:") + 1] == NO_EVIDENCE_TEXT
    assert lines[-1].startswith("status: no_evidence (0 valid citation(s): none;")
    assert lines[-1].endswith("1 removed sentence(s))")


@pytest.mark.django_db
def test_device_limits_the_sources(
    devices: tuple[int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    device_a, device_b = devices
    use_chat(monkeypatch, FakeChatModel(["Der Greifer G-14 hält 8 kg [1]."]))

    _code, both, _ = run_ask(QUESTION, "--json")
    _code, only_b, _ = run_ask(QUESTION, "--json", "--device", str(device_b))
    _code, a_and_b, _ = run_ask(
        QUESTION, "--json", "--device", str(device_a), "--device", str(device_b)
    )

    def devices_of(output: str) -> list[int]:
        event = from_json(json.loads(output.splitlines()[0]))
        assert isinstance(event, SourcesEvent)
        return [source.locations[0].device_id for source in event.sources]

    assert devices_of(both) == [device_a, device_b]
    assert devices_of(only_b) == [device_b]
    assert devices_of(a_and_b) == [device_a, device_b]


def test_ai_off_prints_disabled_and_contacts_nothing(
    settings: Settings, no_real_model_service: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.TWOX_AI_ENABLED = False
    attempts: list[str] = []

    def refuse(*args: object, **kwargs: object) -> object:
        attempts.append(repr(args))
        raise AssertionError("the network must not be used")

    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)

    code, output, errors = run_ask(QUESTION)
    json_code, json_output, json_errors = run_ask(QUESTION, "--json")

    assert (code, output, errors) == (0, DISABLED_LINE + "\n", "")
    assert DISABLED_LINE.startswith("DISABLED: ")
    assert json_code == 0
    assert json.loads(json_output) == {"type": "error", "code": "ai_disabled"}
    assert json_errors == DISABLED_LINE + "\n"
    assert attempts == []


@pytest.mark.django_db
def test_error_prints_failed_with_the_code(
    devices: tuple[int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    use_chat(
        monkeypatch,
        FakeChatModel(
            ["Der Greifer ", "hält"], error=ChatRejectedError("geheim 10.1.2.3"), error_after=1
        ),
    )

    code, output, errors = run_ask(QUESTION)

    assert code == 1
    assert errors == "FAILED: model_rejected\n"
    assert output == "Der Greifer \n"
    assert "geheim" not in output + errors
    assert "Traceback" not in output + errors


@pytest.mark.django_db
def test_empty_chat_model_fails_without_traceback(
    devices: tuple[int, int], settings: Settings
) -> None:
    settings.TWOX_CHAT_MODEL = ""

    code, output, errors = run_ask(QUESTION, "--json")

    assert code == 1
    assert errors == "FAILED: model_unavailable\n"
    assert [json.loads(line)["type"] for line in output.splitlines()] == ["sources", "error"]


@pytest.mark.parametrize("question", ["", "   "])
def test_empty_question_is_a_command_error(question: str) -> None:
    with pytest.raises(CommandError, match="empty"):
        call_command("ask", question, stdout=StringIO(), stderr=StringIO())
