"""Root URL configuration."""

from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path, re_path

from twox.config.health import HealthView
from twox.config.selftest import SelftestView
from twox.config.webui import web_index

# First path segments that never belong to the web UI. A request below one of
# them that matches no pattern stays a 404 (or gets its slash appended).
RESERVED_PREFIXES = ("api", "static", "admin", "_allauth", "accounts")

# Every path whose first segment is not one of RESERVED_PREFIXES: the segment
# has to be followed by "/" or the end of the path to count, so /apix/ is a UI
# path while /api and /api/... are not.
_RESERVED_ALTERNATIVES = "|".join(RESERVED_PREFIXES)
WEB_UI_PATH = rf"^(?!(?:{_RESERVED_ALTERNATIVES})(?:/|$)).+$"

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/selftest/", SelftestView.as_view(), name="selftest"),
    # One urls.py per app; each app adds its endpoints there.
    path("api/v1/", include("twox.accounts.urls")),
    path("api/v1/", include("twox.assets.urls")),
    path("api/v1/", include("twox.files.urls")),
    # The web UI routes in the browser: / and all its page paths return the
    # same index.html. The files below /static/ come from WhiteNoise.
    path("", web_index, name="web-index"),
    re_path(WEB_UI_PATH, web_index, name="web-ui"),
]
