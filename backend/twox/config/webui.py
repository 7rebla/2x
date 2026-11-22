"""Entry page of the web UI.

The built UI lives in STATIC_ROOT (collected at image build time). WhiteNoise
serves its files below STATIC_URL; this view returns its index.html at ``/``
and at every page path of the UI (the UI routes in the browser, see
twox/config/urls.py for the paths that stay out).
"""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_safe

INDEX_FILE_NAME = "index.html"
NOT_BUILT_MESSAGE = "The web interface is not part of this build.\n"

# Icons that browsers ask for at the root of the site, whatever the page says
# (work order 072). Vite copies them from web/public/ to the top of the build,
# so they lie in STATIC_ROOT next to index.html and WhiteNoise serves them
# below /static/ as well. Name → media type.
ROOT_FILES: dict[str, str] = {
    "favicon.ico": "image/x-icon",
    "favicon.svg": "image/svg+xml",
    "apple-touch-icon.png": "image/png",
}
# The icons keep their names from build to build: cache for a day, not forever.
ROOT_FILE_CACHE_CONTROL = "public, max-age=86400"


def index_file() -> Path:
    """Return the path of the collected index.html."""
    return Path(settings.STATIC_ROOT) / INDEX_FILE_NAME


@require_safe
def web_root_file(request: HttpRequest, name: str) -> FileResponse:
    """Return one of ROOT_FILES from the collected build, or 404 if it is missing."""
    content_type = ROOT_FILES.get(name)
    if content_type is None:
        raise Http404
    try:
        handle = (Path(settings.STATIC_ROOT) / name).open("rb")
    except FileNotFoundError:
        raise Http404 from None
    response = FileResponse(handle, content_type=content_type)
    response["Cache-Control"] = ROOT_FILE_CACHE_CONTROL
    return response


@require_safe
@ensure_csrf_cookie
def web_index(request: HttpRequest) -> HttpResponse:
    """Return the index.html of the built web UI, or 404 if there is none.

    The response sets the CSRF cookie: the UI sends its value back in the
    ``X-CSRFToken`` header with every write to the API.
    """
    try:
        content = index_file().read_bytes()
    except FileNotFoundError:
        # backend-dev and the tests run without a built UI.
        return HttpResponse(NOT_BUILT_MESSAGE, status=404, content_type="text/plain; charset=utf-8")
    response = HttpResponse(content, content_type="text/html; charset=utf-8")
    # The page names the hashed asset files of the current build: always ask
    # the server again, so that a new image never leaves stale names behind.
    response["Cache-Control"] = "no-cache"
    return response
