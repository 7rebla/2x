"""System check of the answers: is a usable chat model configured?

With the AI features on (E-59), answers need ``TWOX_CHAT_MODEL``. An empty
value is only a warning: the test environment and the CI start with the
template (AI on, no chat model, work order 128 chooses one), and everything
except answers works without it. A name that looks like an Ollama cloud model
is an error - texts would leave the house (Leitplanke 6).

With the AI features off nothing is reported. The check opens no connection;
whether the model is loaded is checked by the client before its first request.

Registered in :meth:`twox.answers.apps.AnswersConfig.ready`.
"""

from collections.abc import Sequence

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import CheckMessage, Error
from django.core.checks import Warning as CheckWarning

from twox.answers.llm_guard import is_cloud_model_name

#: ID of the warning "no chat model configured".
NO_CHAT_MODEL_WARNING_ID = "twox.answers.W001"
#: ID of the error "the chat model is a cloud model".
CLOUD_CHAT_MODEL_ERROR_ID = "twox.answers.E001"


def check_chat_model(
    app_configs: Sequence[AppConfig] | None = None, **kwargs: object
) -> list[CheckMessage]:
    """Report a missing or a cloud chat model while the AI features are on."""
    if not settings.TWOX_AI_ENABLED:
        return []
    model: str = settings.TWOX_CHAT_MODEL
    if not model:
        return [
            CheckWarning(
                "No chat model configured (TWOX_CHAT_MODEL is empty)",
                hint=(
                    "Set TWOX_CHAT_MODEL to a local chat model loaded in Ollama;"
                    " answers stay unavailable until then."
                ),
                id=NO_CHAT_MODEL_WARNING_ID,
            )
        ]
    if is_cloud_model_name(model):
        return [
            Error(
                f"TWOX_CHAT_MODEL {model!r} is an Ollama cloud model; texts would leave the house",
                hint="Set TWOX_CHAT_MODEL to a local chat model loaded in Ollama.",
                id=CLOUD_CHAT_MODEL_ERROR_ID,
            )
        ]
    return []
