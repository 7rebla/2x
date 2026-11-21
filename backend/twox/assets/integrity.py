"""Unique constraints of the structure, as field errors.

The serializers check uniqueness before saving, but two requests can pass
that check at the same time; then the database constraint stops the second
one with an ``IntegrityError``. :func:`unique_violation` turns such an error
into the field and the message the serializer would have given, so the API
answers 400 instead of 500. The CSV import uses the same mapping.

Messages are marked for translation (work order 034).
"""

from dataclasses import dataclass

from django.db import IntegrityError
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

SITE_NAME_TAKEN = _("A site with this name exists already.")
AREA_NAME_TAKEN = _("This site has an area with this name already.")
PLANT_KEY_TAKEN = _("A plant with this key exists already.")
DEVICE_KEY_TAKEN = _("A device with this key exists already.")


@dataclass(frozen=True)
class UniqueViolation:
    """A unique constraint of the structure: the field it guards and its message."""

    constraint: str
    field: str
    message: str | Promise


#: Every unique constraint of the models in ``twox.assets.models``.
UNIQUE_CONSTRAINTS: dict[str, UniqueViolation] = {
    violation.constraint: violation
    for violation in (
        UniqueViolation("assets_site_name_unique", "name", SITE_NAME_TAKEN),
        UniqueViolation("assets_area_site_name_unique", "name", AREA_NAME_TAKEN),
        UniqueViolation("assets_plant_key_unique", "key", PLANT_KEY_TAKEN),
        UniqueViolation("assets_device_key_unique", "key", DEVICE_KEY_TAKEN),
    )
}


def constraint_name(error: IntegrityError) -> str | None:
    """The name of the constraint behind ``error``, as PostgreSQL reports it.

    psycopg puts the diagnostics of the server on the original exception,
    which Django keeps as ``__cause__``.
    """
    diagnostics = getattr(error.__cause__, "diag", None)
    name = getattr(diagnostics, "constraint_name", None)
    return name if isinstance(name, str) else None


def unique_violation(error: IntegrityError) -> UniqueViolation | None:
    """The unique constraint of the structure that ``error`` reports, if it is one."""
    name = constraint_name(error)
    return None if name is None else UNIQUE_CONSTRAINTS.get(name)
