"""App configuration for twox.answers."""

from django.apps import AppConfig
from django.core import checks


class AnswersConfig(AppConfig):
    name = "twox.answers"

    def ready(self) -> None:
        """Register the system check of the chat model (work order 121)."""
        from twox.answers.checks import check_chat_model

        checks.register(check_chat_model)
