"""The system check of the chat model; it never opens a connection."""

import socket
from io import StringIO

import pytest
from django.core.checks import Error
from django.core.checks import Warning as CheckWarning
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from pytest_django import Settings

from twox.answers.checks import check_chat_model


@pytest.fixture(autouse=True)
def no_connections(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every outgoing connection fails the test: the check must not open one."""
    attempts: list[str] = []

    def refuse(*args: object, **kwargs: object) -> object:
        attempts.append(repr(args))
        raise AssertionError("the system check must not open a connection")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    return attempts


def test_ai_on_without_chat_model_warns_once(settings: Settings, no_connections: list[str]) -> None:
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_CHAT_MODEL = ""

    [message] = check_chat_model()

    assert isinstance(message, CheckWarning)
    assert not isinstance(message, Error)
    assert message.id == "twox.answers.W001"
    assert message.hint is not None
    assert "TWOX_CHAT_MODEL" in message.hint
    output = StringIO()
    call_command("check", stdout=output, stderr=output)
    assert output.getvalue().count("twox.answers.W001") == 1
    assert no_connections == []


@pytest.mark.parametrize("model", ["", "local-chat", "big:cloud"])
def test_ai_off_reports_nothing(settings: Settings, no_connections: list[str], model: str) -> None:
    settings.TWOX_AI_ENABLED = False
    settings.TWOX_CHAT_MODEL = model

    assert check_chat_model() == []
    assert no_connections == []


@pytest.mark.parametrize("model", ["gpt-oss:120b-cloud", "minimax-m2:cloud"])
def test_ai_on_with_cloud_model_is_an_error(
    settings: Settings, no_connections: list[str], model: str
) -> None:
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_CHAT_MODEL = model

    [message] = check_chat_model()

    assert isinstance(message, Error)
    assert message.id == "twox.answers.E001"
    with pytest.raises(SystemCheckError, match=r"twox\.answers\.E001"):
        call_command("check")
    assert no_connections == []


def test_ai_on_with_local_model_is_fine(settings: Settings, no_connections: list[str]) -> None:
    settings.TWOX_AI_ENABLED = True
    settings.TWOX_CHAT_MODEL = "local-chat:8b"

    assert check_chat_model() == []
    assert no_connections == []
