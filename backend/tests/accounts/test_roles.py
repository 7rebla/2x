"""The roles "manage" and "read" are two groups made by a data migration (E-40)."""

import pytest
from django.contrib.auth.models import AnonymousUser, Group
from django.utils import translation

from tests.accounts.users import TEST_PASSWORD, UserFactory
from twox.accounts.models import User
from twox.accounts.roles import MANAGE, READ, ROLE_LABELS, ROLES, user_role


@pytest.mark.django_db
def test_role_groups_exist_after_migration() -> None:
    names = set(Group.objects.values_list("name", flat=True))

    assert {"manage", "read"} <= names


def test_role_constants() -> None:
    assert MANAGE == "manage"
    assert READ == "read"
    assert ROLES == ("manage", "read")


def test_role_labels_are_lazy_english_texts() -> None:
    with translation.override("en"):
        assert {role: str(label) for role, label in ROLE_LABELS.items()} == {
            "manage": "Manage",
            "read": "Read",
        }


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("anonymous", None),
        ("no_role", None),
        ("read", "read"),
        ("manage", "manage"),
        ("superuser", "manage"),
    ],
)
def test_user_role(user_factory: UserFactory, kind: str, expected: str | None) -> None:
    user = user_factory(kind)

    assert user_role(user if user is not None else AnonymousUser()) == expected


@pytest.mark.django_db
def test_user_in_both_groups_counts_as_manage() -> None:
    user = User.objects.create_user(username="both", password=TEST_PASSWORD)
    user.groups.add(*Group.objects.filter(name__in=["read", "manage"]))

    assert user_role(user) == "manage"


@pytest.mark.django_db
def test_other_groups_give_no_role() -> None:
    user = User.objects.create_user(username="other", password=TEST_PASSWORD)
    user.groups.add(Group.objects.create(name="something-else"))

    assert user_role(user) is None


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["read", "manage", "superuser"])
def test_inactive_user_has_no_role(user_factory: UserFactory, kind: str) -> None:
    user = user_factory(kind)
    assert user is not None
    user.is_active = False
    user.save()

    assert user_role(user) is None
