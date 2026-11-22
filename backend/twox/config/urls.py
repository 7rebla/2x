"""Root URL configuration."""

from typing import NoReturn

from django.contrib import admin
from django.http import Http404, HttpRequest
from django.urls import URLPattern, URLResolver, include, path, re_path

from twox.config.health import HealthView
from twox.config.selftest import SelftestView
from twox.config.webui import ROOT_FILES, web_index, web_root_file

# First path segments that never belong to the web UI. A request below one of
# them that matches no pattern stays a 404 (or gets its slash appended).
RESERVED_PREFIXES = ("api", "static", "admin", "_allauth", "accounts")

# Every path whose first segment is not one of RESERVED_PREFIXES: the segment
# has to be followed by "/" or the end of the path to count, so /apix/ is a UI
# path while /api and /api/... are not.
_RESERVED_ALTERNATIVES = "|".join(RESERVED_PREFIXES)
WEB_UI_PATH = rf"^(?!(?:{_RESERVED_ALTERNATIVES})(?:/|$)).+$"

# Endpoints of the allauth headless API (65.22.1) that milestone M1 does not
# offer (E-38): changing one's own password, resetting it by email and
# managing email addresses. They are matched before allauth and answer 404,
# for both headless clients.
CLOSED_ALLAUTH_PATH = (
    r"^_allauth/(?:browser|app)/v1/"
    r"(?:account/password/change|account/email|auth/password/request|auth/password/reset)$"
)


def closed_allauth_endpoint(request: HttpRequest) -> NoReturn:
    """Answer 404 for an allauth endpoint that this installation does not offer."""
    raise Http404


urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    re_path(CLOSED_ALLAUTH_PATH, closed_allauth_endpoint),
    # django-allauth: the headless API for the web UI (sign-in, sign-out,
    # session). accounts/ is where allauth expects its own URLs; with
    # HEADLESS_ONLY and without OpenID Connect it registers none yet.
    path("_allauth/", include("allauth.headless.urls")),
    path("accounts/", include("allauth.urls")),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/selftest/", SelftestView.as_view(), name="selftest"),
    # One urls.py per app; each app adds its endpoints there.
    path("api/v1/", include("twox.accounts.urls")),
    path("api/v1/", include("twox.assets.urls")),
    path("api/v1/", include("twox.files.urls")),
    path("api/v1/", include("twox.ingest.urls")),
    path("api/v1/", include("twox.search.urls")),
    path("api/v1/", include("twox.answers.urls")),
    # The web UI routes in the browser: / and all its page paths return the
    # same index.html. The files below /static/ come from WhiteNoise.
    path("", web_index, name="web-index"),
    # Icons at the root of the site (/favicon.ico ...); never the index.html.
    *(path(name, web_root_file, {"name": name}) for name in ROOT_FILES),
    re_path(WEB_UI_PATH, web_index, name="web-ui"),
]
