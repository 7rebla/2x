"""The two roles of the application: "Manage" and "Read" (E-40).

A role is membership in one of two Django groups, named like the role. The
data migration ``0002_role_groups`` creates both groups. A superuser always
counts as ``manage``; a user in both groups also counts as ``manage``.
"""

from typing import Final, Literal

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from twox.accounts.models import User

type Role = Literal["manage", "read"]

MANAGE: Final[Literal["manage"]] = "manage"
READ: Final[Literal["read"]] = "read"

# Ordered from most to least rights.
ROLES: Final[tuple[Role, ...]] = (MANAGE, READ)

# Display names; the group names above stay the same in every language.
ROLE_LABELS: Final[dict[Role, Promise]] = {
    MANAGE: _("Manage"),
    READ: _("Read"),
}


def user_role(user: AbstractBaseUser | AnonymousUser) -> Role | None:
    """Return the role of ``user``, or ``None`` for anonymous, inactive or role-less users."""
    if not isinstance(user, User) or not user.is_active:
        return None
    if user.is_superuser:
        return MANAGE
    names = set(user.groups.filter(name__in=ROLES).values_list("name", flat=True))
    for role in ROLES:
        if role in names:
            return role
    return None
