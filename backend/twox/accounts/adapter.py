"""Account adapter for django-allauth.

Accounts are local and created by an administrator (work order 021); nobody
signs up on their own. The application runs without internet, so allauth never
sends an email. Failed sign-ins are written to the server log with the
username, never with the password.
"""

import logging
from typing import TYPE_CHECKING, Any

from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError
from django.http import HttpRequest

if TYPE_CHECKING:
    from allauth.account.models import EmailConfirmation

logger = logging.getLogger(__name__)


def _username(credentials: dict[str, object]) -> str:
    """Return the username of a sign-in attempt; the password is never read."""
    return str(credentials.get("username", ""))


class AccountAdapter(DefaultAccountAdapter):
    """No self-registration, no email, and a log line for every failed sign-in."""

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        """Accounts are created by an administrator only."""
        return False

    def send_mail(self, template_prefix: str, email: str, context: dict[str, Any]) -> None:
        """Send nothing: there is no mail server and no internet (guardrail 6)."""
        logger.info("No email sent (%s): this installation does not send email.", template_prefix)

    def send_confirmation_mail(
        self, request: HttpRequest, emailconfirmation: EmailConfirmation, signup: bool
    ) -> None:
        """Send nothing and build no confirmation link.

        allauth builds the link before it sends the email; with HEADLESS_ONLY
        that link would need a page of the web UI, and without one adding an
        email address through the API ended in an error 500.
        """
        logger.info("No email sent (email confirmation): this installation does not send email.")

    def get_reset_password_from_key_url(self, key: str) -> str:
        """Return no link: a password reset email is never sent (E-38).

        allauth builds the link before it sends the email, and with
        HEADLESS_ONLY it would need a page of the web UI for it: without this,
        a reset request for a known address ends in an error 500. Unknown
        addresses get no email at all (ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS), so
        both get the same answer and nothing leaves the server.
        """
        return ""

    def pre_authenticate(self, request: HttpRequest, **credentials: object) -> None:
        """Log an attempt that the rate limit for failed sign-ins turns away."""
        try:
            super().pre_authenticate(request, **credentials)
        except ValidationError:
            logger.warning(
                "Sign-in blocked by the rate limit for username %r.", _username(credentials)
            )
            raise

    def authentication_failed(self, request: HttpRequest, **credentials: object) -> None:
        """Log a failed sign-in with the username only."""
        super().authentication_failed(request, **credentials)
        logger.warning("Failed sign-in for username %r.", _username(credentials))
