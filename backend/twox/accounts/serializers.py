"""Serializers of the accounts API."""

from typing import Any, Literal, TypedDict

from auditlog.models import LogEntry
from drf_spectacular.utils import extend_schema_field
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


type AuditAction = Literal["create", "update", "delete"]

#: The actions of the change log by their number in auditlog. auditlog also
#: knows "access"; nothing in the project logs it, the API leaves it out.
AUDIT_ACTIONS: dict[int, AuditAction] = {
    LogEntry.Action.CREATE: "create",
    LogEntry.Action.UPDATE: "update",
    LogEntry.Action.DELETE: "delete",
}

#: The actions as choices; named AuditActionEnum in the schema (see
#: SPECTACULAR_SETTINGS), so that it never clashes with another "action".
AUDIT_ACTION_CHOICES: list[tuple[AuditAction, AuditAction]] = [
    (action, action) for action in AUDIT_ACTIONS.values()
]

#: Schema of ``changes``: per field either ``[old, new]`` or, for the groups
#: of a user (a role change), the added or removed groups.
CHANGES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Changed fields by name. A plain field has [old, new]; on create old is null,"
        " on delete new is null. Times are UTC, written without a zone"
        ' ("2026-01-31 12:00:00.000000"); a reference to another object is its id.'
        " The groups of a user (the role) have"
        ' {"type": "m2m", "operation": "add" or "delete", "objects": [group names]}.'
    ),
    "additionalProperties": {
        "oneOf": [
            {"type": "array", "items": {}, "minItems": 2, "maxItems": 2},
            {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["m2m"]},
                    "operation": {"type": "string", "enum": ["add", "delete"]},
                    "objects": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["type", "operation", "objects"],
            },
        ]
    },
}


class AuditLogEntrySerializer(serializers.ModelSerializer[LogEntry]):
    """One entry of the change log: who changed which object when, and how."""

    actor = serializers.CharField(
        source="actor.username",
        allow_null=True,
        read_only=True,
        help_text="User name of the actor; null for changes without a signed-in user.",
    )
    action = serializers.SerializerMethodField()
    object_type = serializers.SerializerMethodField()
    changes = serializers.SerializerMethodField()

    class Meta:
        model = LogEntry
        fields = (
            "id",
            "timestamp",
            "actor",
            "action",
            "object_type",
            "object_id",
            "object_repr",
            "changes",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.ChoiceField(choices=AUDIT_ACTION_CHOICES))
    def get_action(self, entry: LogEntry) -> AuditAction:
        return AUDIT_ACTIONS[entry.action]

    @extend_schema_field(
        serializers.CharField(help_text="App label and model, for example assets.device.")
    )
    def get_object_type(self, entry: LogEntry) -> str:
        return f"{entry.content_type.app_label}.{entry.content_type.model}"

    @extend_schema_field(CHANGES_SCHEMA)
    def get_changes(self, entry: LogEntry) -> dict[str, Any]:
        changes: dict[str, Any] | None = entry.changes
        return changes or {}
