"""The project's Django admin: a tool for superusers only.

The admin manages users and helps in emergencies (E-39). Being ``is_staff``
is not enough; only active superusers get in. The app config below replaces
``django.contrib.admin`` in INSTALLED_APPS and makes this site the default
one, so every ``admin.site.register(...)`` ends up here.
"""

from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig
from django.http import HttpRequest


class TwoxAdminSite(AdminSite):
    """Admin site that admits active superusers only."""

    site_header = "2x administration"
    site_title = "2x administration"
    index_title = "Administration"

    def has_permission(self, request: HttpRequest) -> bool:
        """Return True for an active superuser, never for staff alone."""
        user = request.user
        return bool(user.is_active and user.is_superuser)


class TwoxAdminConfig(AdminConfig):
    """``django.contrib.admin`` with :class:`TwoxAdminSite` as the default site."""

    default_site = "twox.config.admin_site.TwoxAdminSite"
