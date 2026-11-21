"""Fixtures of the accounts tests."""

import pytest

from tests.accounts.users import UserFactory, make_user


@pytest.fixture
def user_factory(db: None) -> UserFactory:
    """Make users of a given kind (see ``tests.accounts.users.KINDS``)."""
    return make_user
