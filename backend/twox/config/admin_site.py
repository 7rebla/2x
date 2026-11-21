"""The project's Django admin: a tool for superusers only.

The admin manages users and helps in emergencies (E-39). Being ``is_staff``
is not enough; only active superusers get in. The app config below replaces
``django.contrib.admin`` in INSTALLED_APPS and makes this site the default
one, so every ``admin.site.register(...)`` ends up here.

The admin has no sign-in form of its own (E-39, work order 030): its login
page sends the browser to the sign-in page of the web UI, which signs in
through django-allauth with its rate limits. That way there is exactly one
way to get a session.
"""

from typing import Any
from urllib.parse import unquote, urlencode, urlsplit

from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache

# Address of the sign-in page of the web UI (web/src/routes.tsx).
WEB_UI_LOGIN_PATH = "/login"


class TwoxAdminSite(AdminSite):
    """Admin site that admits active superusers only."""

    site_header = "2x administration"
    site_title = "2x administration"
    index_title = "Administration"

    def has_permission(self, request: HttpRequest) -> bool:
        """Return True for an active superuser, never for staff alone."""
        user = request.user
        return bool(user.is_active and user.is_superuser)

    @method_decorator(never_cache)
    @login_not_required
    def login(
        self, request: HttpRequest, extra_context: dict[str, Any] | None = None
    ) -> HttpResponse:
        """Replace Django's admin sign-in form; it never signs anyone in.

        - Not signed in (any method, also a POST to the old form): redirect to
          ``/login?next=<admin path>`` of the web UI.
        - Signed in as an active superuser: go on to the admin path.
        - Signed in without access: 403. A redirect to the sign-in page would
          only send the user straight back here (a sign-in loop).
        """
        next_path = self.next_admin_path(request)
        if request.user.is_authenticated:
            if self.has_permission(request):
                return HttpResponseRedirect(next_path)
            raise PermissionDenied
        query = urlencode({REDIRECT_FIELD_NAME: next_path})
        return HttpResponseRedirect(f"{WEB_UI_LOGIN_PATH}?{query}")

    def next_admin_path(self, request: HttpRequest) -> str:
        """Return the admin path from ``?next=``, or the admin index.

        Only a path of this host below the admin is accepted, so the sign-in
        page never sends anyone to a foreign address.
        """
        index = reverse("admin:index", current_app=self.name)
        candidate = request.GET.get(REDIRECT_FIELD_NAME, "")
        safe = url_has_allowed_host_and_scheme(
            candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        )
        if safe and candidate.startswith(index) and is_plain_path(candidate):
            return candidate
        return index


def is_plain_path(url: str) -> bool:
    """Return True if the path of ``url`` stays as written when a browser resolves it.

    Dot segments ("..", "%2e%2e"), backslashes and empty segments ("//") are
    refused: "/admin/..//host/" starts with "/admin/" but resolves to "//host/".
    """
    path = unquote(urlsplit(url).path)
    if "\\" in path or "//" in path:
        return False
    return all(segment not in {".", ".."} for segment in path.split("/"))


class TwoxAdminConfig(AdminConfig):
    """``django.contrib.admin`` with :class:`TwoxAdminSite` as the default site."""

    default_site = "twox.config.admin_site.TwoxAdminSite"
