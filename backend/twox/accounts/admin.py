"""Accounts and the change log in the admin, which admits superusers only (E-39)."""

from typing import TYPE_CHECKING

from auditlog.models import LogEntry
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest

from twox.accounts.models import User

# ModelAdmin is generic for the type checker only; at runtime it cannot be
# subscripted (that would need django-stubs-ext in the runtime image).
if TYPE_CHECKING:
    LogEntryAdminBase = admin.ModelAdmin[LogEntry]
else:
    LogEntryAdminBase = admin.ModelAdmin

admin.site.register(User, UserAdmin)

# auditlog brings its own admin view; it allows deleting entries in some
# cases. It is replaced by the read-only view below (E-43).
if admin.site.is_registered(LogEntry):
    admin.site.unregister(LogEntry)


@admin.register(LogEntry)
class AuditLogEntryAdmin(LogEntryAdminBase):
    """The change log, read-only for everybody, superusers included."""

    list_display = ("timestamp", "action", "content_type", "object_repr", "actor")
    list_filter = ("action", "content_type")
    list_select_related = ("content_type", "actor")
    search_fields = ("object_repr", "actor__username")
    date_hierarchy = "timestamp"
    fields = (
        "timestamp",
        "actor",
        "action",
        "content_type",
        "object_id",
        "object_repr",
        "changes",
    )
    readonly_fields = fields

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: LogEntry | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: LogEntry | None = None) -> bool:
        return False
