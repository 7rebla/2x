"""App configuration for twox.accounts."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "twox.accounts"

    def ready(self) -> None:
        # Imported here: audit.py imports models of several apps.
        from twox.accounts.audit import register_models

        register_models()
