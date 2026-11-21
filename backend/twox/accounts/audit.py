"""Change log: who changed what and when (E-43), with django-auditlog.

Every model whose changes are logged is registered here and nowhere else;
``AccountsConfig.ready()`` calls :func:`register_models`. During a request,
:class:`AuditMiddleware` (see the settings) names the signed-in user as the
actor. Outside a request (management commands, imports) wrap the work in
:func:`acting_as`.

Only ``save()`` and ``delete()`` are logged: ``bulk_create`` and
``QuerySet.update`` write no entries.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from auditlog.context import auditlog_value, set_actor
from auditlog.middleware import AuditlogMiddleware
from auditlog.registry import auditlog
from django.db.models import Model
from django.http import HttpRequest

from twox.accounts.models import User
from twox.assets.models import Area, Device, Plant, Site
from twox.files.models import Document, DocumentVersion

#: Structure and files: every field is logged.
STRUCTURE_AND_FILE_MODELS: tuple[type[Model], ...] = (
    Site,
    Area,
    Plant,
    Device,
    Document,
    DocumentVersion,
)

#: Never in the log: the password hash, and the time of the last sign-in
#: (it changes at every sign-in and is no change by anyone).
USER_EXCLUDED_FIELDS = ("password", "last_login")

#: Role changes are changes of the group membership.
USER_M2M_FIELDS = frozenset({"groups"})

#: All logged models.
AUDITED_MODELS: tuple[type[Model], ...] = (*STRUCTURE_AND_FILE_MODELS, User)


def tracked_fields(model: type[Model]) -> list[str]:
    """The fields of ``model`` that the log compares: its own columns.

    Without this list auditlog would also put reverse relations (for example
    the devices of a plant) into the entry of a new or deleted object, as the
    text of their related manager.
    """
    return [field.name for field in model._meta.concrete_fields]


def register_models() -> None:
    """Register every model of :data:`AUDITED_MODELS` with auditlog."""
    for model in STRUCTURE_AND_FILE_MODELS:
        auditlog.register(model, include_fields=tracked_fields(model))
    auditlog.register(
        User,
        include_fields=tracked_fields(User),
        exclude_fields=list(USER_EXCLUDED_FIELDS),
        m2m_fields=set(USER_M2M_FIELDS),
    )


class AuditMiddleware(AuditlogMiddleware):
    """auditlog's middleware without any value from request headers.

    In auditlog 3.4.2 the middleware takes ``remote_port`` from the header
    ``X-Forwarded-Port`` (also with ``AUDITLOG_DISABLE_REMOTE_ADDR``) and the
    address from ``X-Forwarded-For``. A port that does not fit the column
    makes writing the entry fail after the change itself is saved: the change
    would stay without an entry. So neither is ever taken from the request;
    only the signed-in user is. The correlation id is switched off in the
    settings (``AUDITLOG_CID_HEADER = None``).
    """

    @staticmethod
    def _get_remote_addr(request: HttpRequest) -> None:
        return None

    @staticmethod
    def _get_remote_port(request: HttpRequest) -> None:
        return None


@contextmanager
def acting_as(user: User | None) -> Iterator[None]:
    """Name ``user`` as the actor of every change logged inside the block.

    For work outside a request, for example a management command or an
    import. ``None`` logs the changes without an actor. No IP address and no
    port are recorded. After the block, an actor set around it (for example
    by the middleware) applies again.
    """
    # set_actor() of auditlog leaves its own context in place after the block;
    # restore the one from before, or later changes would lose their actor.
    previous = auditlog_value.get(None)
    try:
        with set_actor(user):
            yield
    finally:
        if previous is not None:
            auditlog_value.set(previous)
