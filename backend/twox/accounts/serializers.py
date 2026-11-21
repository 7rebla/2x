"""Serializers of the accounts API."""

from typing import TypedDict

from rest_framework import serializers

from twox.accounts.roles import ROLES, Role


class Me(TypedDict):
    username: str
    role: Role | None
    is_superuser: bool


class MeSerializer(serializers.Serializer[Me]):
    """The signed-in user as the web UI needs it."""

    username = serializers.CharField()
    role = serializers.ChoiceField(choices=list(ROLES), allow_null=True)
    is_superuser = serializers.BooleanField()
