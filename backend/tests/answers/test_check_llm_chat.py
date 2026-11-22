"""`check_llm --chat` (work order 129): one line, timing only, never the answer.

The model service is the stand-in of Ollama from :mod:`tests.answers.fake_ollama`
or :class:`twox.answers.chat.FakeChatModel`; no test talks to a real model.
"""

import logging
import re
from collections.abc import Sequence

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from pytest_django import Settings

from tests.answers.fake_ollama import (
    CHAT_MODEL,
    EMBEDDING_ONLY_MODEL,
    LOCAL_MODEL,
    FakeOllama,
    fake_ollama,
)
from tests.answers.test_check_llm import forbid_network, run_check, single_line
from twox.answers import chat
from twox.answers.management.commands import check_llm
from twox.answers.management.commands.check_llm import DISABLED_LINE

# A striking text in the answer of the model: it must never be printed or logged.
ANSWER_MARKER = "ANSWER-MARKER-5c1e"
OK_LINE = re.compile(
    r"^OK: chat with local-chat: first token after \d+\.\d\ds,"
    r" (?P<chunks>\d+) chunks in \d+\.\d\ds \(\d+\.\d chunks/s\)$"
)


@pytest.fixture(autouse=True)
def chat_settings(settings: Settings) -> Settings:
    """AI on with a local chat model; the stand-in decides what the service says."""
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_CHAT_MODEL = "local-chat"
    settings.TWOX_CHAT_TIMEOUT_SECONDS = 5
    settings.TWOX_CHAT_MAX_TOKENS = 1024
    settings.TWOX_CHAT_TEMPERATURE = 0.0
    settings.TWOX_CHAT_REASONING_EFFORT = "none"
    return settings


def chat_fake(**changes: object) -> FakeOllama:
    fake = FakeOllama(
        models=[dict(LOCAL_MODEL), dict(CHAT_MODEL)],
        chat_pieces=["The sky ", ANSWER_MARKER, " is blue."],
    )
    for name, value in changes.items():
        setattr(fake, name, value)
    return fake


def test_disabled_prints_the_neutral_line_and_contacts_nothing(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.TWOX_AI_ENABLED = False
    with fake_ollama(chat_fake()) as (base_url, fake):
        settings.TWOX_LLM_BASE_URL = base_url
        attempts = forbid_network(monkeypatch)
        code, output = run_check("--chat")

    assert code == 0
    assert single_line(output) == DISABLED_LINE
    assert fake.requests == []
    assert attempts == []


def test_ok_reports_first_token_and_rate_but_not_the_answer(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    with fake_ollama(chat_fake()) as (base_url, fake):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--chat")

    line = single_line(output)
    assert code == 0
    match = OK_LINE.match(line)
    assert match is not None, line
    assert match["chunks"] == "3"
    # Neither the answer nor the prompt reaches the output or the log.
    for text in (output, caplog.text):
        assert ANSWER_MARKER not in text
        assert "sky" not in text
        assert check_llm.CHAT_TEST_PROMPT not in text
    # The model list, then one chat request with the small fixed limits.
    assert [request.path for request in fake.requests] == ["/api/tags", "/v1/chat/completions"]
    (request,) = fake.chat_requests
    assert request.body["model"] == "local-chat"
    assert request.body["messages"] == [{"role": "user", "content": check_llm.CHAT_TEST_PROMPT}]
    assert request.body["max_tokens"] == check_llm.CHAT_TEST_MAX_TOKENS == 32
    assert request.body["temperature"] == 0
    assert request.body["seed"] == check_llm.CHAT_TEST_SEED
    assert request.body["stream"] is True


def test_empty_chat_model_is_an_invalid_configuration(settings: Settings) -> None:
    settings.TWOX_CHAT_MODEL = ""
    with fake_ollama(chat_fake()) as (base_url, fake):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--chat")

    assert code == 1
    assert single_line(output) == "FAILED: invalid configuration: TWOX_CHAT_MODEL is empty"
    assert fake.requests == []


def test_invalid_address_is_an_invalid_configuration(settings: Settings) -> None:
    settings.TWOX_LLM_BASE_URL = "host.docker.internal:11434"
    code, output = run_check("--chat")

    assert code == 1
    assert single_line(output).startswith("FAILED: invalid configuration: ")


def test_missing_model_names_ollama_pull(settings: Settings) -> None:
    with fake_ollama(chat_fake(models=[dict(LOCAL_MODEL)])) as (base_url, fake):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--chat")

    assert code == 1
    assert single_line(output) == (
        "FAILED: ChatRejectedError: model 'local-chat' is not loaded in Ollama;"
        " load it with: ollama pull local-chat"
    )
    assert fake.chat_requests == []


def test_model_without_completion_is_refused(settings: Settings) -> None:
    settings.TWOX_CHAT_MODEL = "bge-m3"
    with fake_ollama(chat_fake(models=[dict(EMBEDDING_ONLY_MODEL)])) as (base_url, fake):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--chat")

    assert code == 1
    assert single_line(output).startswith(
        "FAILED: ChatRejectedError: model 'bge-m3' cannot generate"
    )
    assert fake.chat_requests == []


@pytest.mark.parametrize("name", ["gpt-oss:120b-cloud", "minimax-m2:cloud"])
def test_cloud_model_by_name_is_never_asked(settings: Settings, name: str) -> None:
    settings.TWOX_CHAT_MODEL = name
    with fake_ollama(chat_fake()) as (base_url, fake):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--chat")

    assert code == 1
    assert single_line(output).startswith("FAILED: ChatRemoteModelError: ")
    assert fake.requests == []


def test_cloud_model_by_remote_entry_is_never_asked(settings: Settings) -> None:
    remote = dict(CHAT_MODEL, remote_host="https://ollama.com:443")
    with fake_ollama(chat_fake(models=[remote])) as (base_url, fake):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--chat")

    assert code == 1
    assert single_line(output).startswith("FAILED: ChatRemoteModelError: ")
    assert fake.chat_requests == []


def test_timeout_uses_the_chat_time_limit(settings: Settings) -> None:
    settings.TWOX_CHAT_TIMEOUT_SECONDS = 1
    fake = chat_fake(chat_pause_before=0, chat_pause_seconds=5.0)
    with fake_ollama(fake) as (base_url, _fake):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--chat", "--timeout", "30")
        # The connection is given up, not left to the model.
        assert fake.client_closed.wait(timeout=5)

    line = single_line(output)
    assert code == 1
    assert line.startswith("FAILED: ChatUnavailableError: ")
    assert "within 1s" in line


def test_empty_answer_is_a_failure(settings: Settings) -> None:
    with fake_ollama(chat_fake(chat_pieces=[])) as (base_url, _fake):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--chat")

    assert code == 1
    assert single_line(output) == (
        "FAILED: empty answer: model 'local-chat' returned no text within 32 tokens"
    )


def test_chat_and_embed_exclude_each_other() -> None:
    with pytest.raises(CommandError, match="not allowed with argument"):
        call_command("check_llm", "--chat", "--embed")


def test_warning_comes_first_for_a_model_service_elsewhere(settings: Settings) -> None:
    with fake_ollama(chat_fake(), host="127.0.0.2") as (base_url, _fake):
        settings.TWOX_LLM_BASE_URL = base_url
        code, output = run_check("--chat")

    warning, result, *rest = output.splitlines()
    assert code == 0
    assert warning.startswith("WARNING: TWOX_LLM_BASE_URL points to '127.0.0.2'")
    assert result.startswith("OK: chat with local-chat: ")
    assert rest == []


class RecordingFakeChat(chat.FakeChatModel):
    """Keeps every stream it hands out, so a test can see that it was closed."""

    def __init__(
        self,
        pieces: Sequence[str] = ("one", "two"),
        *,
        error: chat.ChatError | None = None,
        error_after: int = 0,
        fail_on_call: chat.ChatError | None = None,
    ) -> None:
        super().__init__(
            pieces,
            model_name="local-chat",
            error=error,
            error_after=error_after,
            fail_on_call=fail_on_call,
        )
        self.streams: list[chat.ChatStream] = []

    def stream(
        self,
        messages: Sequence[chat.ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> chat.ChatStream:
        handed_out = super().stream(
            messages, max_tokens=max_tokens, temperature=temperature, seed=seed
        )
        self.streams.append(handed_out)
        return handed_out


@pytest.mark.parametrize("error_after", [0, 1])
def test_stream_and_model_are_closed_after_an_error(
    monkeypatch: pytest.MonkeyPatch, error_after: int
) -> None:
    model = RecordingFakeChat(
        error=chat.ChatUnavailableError("the answer broke off before its end"),
        error_after=error_after,
    )
    monkeypatch.setattr(chat, "get_chat_model", lambda: model)

    code, output = run_check("--chat")

    assert code == 1
    assert single_line(output) == (
        "FAILED: ChatUnavailableError: the answer broke off before its end"
    )
    (stream,) = model.streams
    assert stream.closed
    assert model.close_count == 1


def test_model_is_closed_when_the_request_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    model = RecordingFakeChat(fail_on_call=chat.ChatRejectedError("refused (HTTP 400)"))
    monkeypatch.setattr(chat, "get_chat_model", lambda: model)

    code, output = run_check("--chat")

    assert code == 1
    assert single_line(output) == "FAILED: ChatRejectedError: refused (HTTP 400)"
    assert model.close_count == 1


def test_stream_and_model_are_closed_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    model = RecordingFakeChat()
    monkeypatch.setattr(chat, "get_chat_model", lambda: model)

    code, output = run_check("--chat")

    assert code == 0
    assert OK_LINE.match(single_line(output))
    (stream,) = model.streams
    assert stream.closed
    assert model.close_count == 1
    (call,) = model.calls
    assert (call.max_tokens, call.temperature, call.seed) == (
        check_llm.CHAT_TEST_MAX_TOKENS,
        check_llm.CHAT_TEST_TEMPERATURE,
        check_llm.CHAT_TEST_SEED,
    )
