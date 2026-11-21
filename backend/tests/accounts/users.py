"""Users with each role, for the tests of roles, permissions and the me endpoint."""

from collections.abc import Callable

from django.contrib.auth.models import Group

from twox.accounts.models import User

# Every test user is signed in with ``force_login`` or ``force_authenticate``;
# the password only satisfies the model and is a recognisable test value.
TEST_PASSWORD = "roles-test-only-password"

KINDS = ["anonymous", "no_role", "read", "manage", "superuser"]

type UserFactory = Callable[[str], User | None]


def make_user(kind: str) -> User | None:
    """Return a saved user of ``kind``, or ``None`` for ``anonymous``.

    Kinds: see ``KINDS``. Each kind can be made once per test.
    """
    if kind == "anonymous":
        return None
    if kind == "superuser":
        return User.objects.create_superuser(username="root", password=TEST_PASSWORD)
    if kind not in {"no_role", "read", "manage"}:
        raise ValueError(f"unknown kind of user: {kind}")
    user = User.objects.create_user(username=kind, password=TEST_PASSWORD)
    if kind != "no_role":
        user.groups.add(Group.objects.get(name=kind))
    return user
