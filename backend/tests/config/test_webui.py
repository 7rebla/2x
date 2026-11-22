"""Delivery of the built web UI: index.html for its pages, the build below /static/.

Every test works on a prepared folder, never on a real build.
"""

import json
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client
from pytest_django.fixtures import Settings

from tests.config.test_settings import run_python
from twox.config.staticfinders import ADMIN_APP_NAME, AdminAppDirectoriesFinder

INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>2x</title>
    <script type="module" crossorigin src="/static/assets/index-abc123.js"></script>
    <link rel="stylesheet" crossorigin href="/static/assets/index-def456.css">
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
"""
SCRIPT = "console.log('prepared build');\n"
STYLE = "body { margin: 0; }\n"


def write_build(root: Path) -> Path:
    """Write a small stand-in for the Vite build output to ``root``."""
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (root / "assets" / "index-abc123.js").write_text(SCRIPT, encoding="utf-8")
    (root / "assets" / "index-def456.css").write_text(STYLE, encoding="utf-8")
    return root


# Stand-ins for the icons Vite copies from web/public/ (not real image data).
ICONS = {
    "favicon.ico": b"\x00\x00\x01\x00prepared icon",
    "favicon.svg": b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"></svg>\n',
    "apple-touch-icon.png": b"\x89PNG\r\n\x1a\nprepared icon",
}


def write_icons(root: Path) -> None:
    """Write the icons next to index.html, where the Vite build puts them."""
    for name, content in ICONS.items():
        (root / name).write_bytes(content)


@pytest.fixture
def built_ui(tmp_path: Path, settings: Settings) -> Path:
    """Point STATIC_ROOT at a prepared build, as collectstatic leaves it in the image."""
    static_root = write_build(tmp_path / "staticfiles")
    write_icons(static_root)
    settings.STATIC_ROOT = static_root
    return static_root


@pytest.fixture
def missing_ui(tmp_path: Path, settings: Settings) -> None:
    """Point STATIC_ROOT at a folder that does not exist (no built UI)."""
    settings.STATIC_ROOT = tmp_path / "staticfiles"


@pytest.mark.usefixtures("built_ui")
def test_root_serves_index_html_with_root_element() -> None:
    response = Client().get("/")

    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"
    assert '<div id="root"></div>' in response.content.decode()
    # A new build must reach the browser at once: no stale asset names.
    assert response["Cache-Control"] == "no-cache"


@pytest.mark.usefixtures("built_ui")
def test_root_answers_head_but_rejects_writes() -> None:
    assert Client().head("/").status_code == 200
    assert Client().post("/").status_code == 405


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize(
    ("path", "content_type", "body"),
    [
        ("/static/assets/index-abc123.js", "text/javascript", SCRIPT),
        ("/static/assets/index-def456.css", "text/css", STYLE),
    ],
)
def test_built_assets_are_served_below_static(path: str, content_type: str, body: str) -> None:
    response = Client().get(path)

    assert response.status_code == 200
    # WhiteNoise writes the parameter quoted: charset="utf-8".
    media_type, _, parameters = response["Content-Type"].partition(";")
    assert media_type == content_type
    assert parameters.strip().replace('"', "") == "charset=utf-8"
    assert response.getvalue().decode() == body
    # Vite puts a content hash into every name below assets/.
    assert "immutable" in response["Cache-Control"]


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize(
    "path",
    [
        "/static/assets/index-missing.js",
        "/static/unknown.css",
        "/static/",
        "/static/assets/",
    ],
)
def test_unknown_static_path_is_404(path: str) -> None:
    response = Client().get(path)

    assert response.status_code == 404
    assert '<div id="root">' not in response.content.decode()


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize(
    ("name", "content_type"),
    [
        ("favicon.ico", "image/x-icon"),
        ("favicon.svg", "image/svg+xml"),
        ("apple-touch-icon.png", "image/png"),
    ],
)
def test_icons_are_served_at_the_root(name: str, content_type: str) -> None:
    response = Client().get(f"/{name}")

    assert response.status_code == 200
    assert response["Content-Type"] == content_type
    assert response.getvalue() == ICONS[name]
    assert response["Cache-Control"] == "public, max-age=86400"
    assert "csrftoken" not in response.cookies


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize(
    ("name", "content_type"),
    [
        ("favicon.ico", "image/x-icon"),
        ("favicon.svg", "image/svg+xml"),
        ("apple-touch-icon.png", "image/png"),
    ],
)
def test_icons_are_served_below_static_too(name: str, content_type: str) -> None:
    # The built index.html links them with the base /static/ in front.
    response = Client().get(f"/static/{name}")

    assert response.status_code == 200
    assert response["Content-Type"].partition(";")[0] == content_type
    assert response.getvalue() == ICONS[name]


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize("name", ["favicon.ico", "favicon.svg", "apple-touch-icon.png"])
def test_icons_answer_head_but_reject_writes(name: str) -> None:
    assert Client().head(f"/{name}").status_code == 200
    assert Client().post(f"/{name}").status_code == 405


@pytest.mark.usefixtures("missing_ui")
@pytest.mark.parametrize("path", ["/favicon.ico", "/favicon.svg", "/apple-touch-icon.png"])
def test_missing_icon_is_404_not_the_ui(path: str) -> None:
    response = Client().get(path)

    assert response.status_code == 404
    assert '<div id="root">' not in response.content.decode()


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize("path", ["/favicon.ico/", "/favicon.png", "/x/favicon.ico", "/index.html"])
def test_other_root_names_stay_page_paths(path: str) -> None:
    # Only the three icon names are files; everything else is a page path of the UI.
    response = Client().get(path)

    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"


@pytest.mark.usefixtures("built_ui")
def test_api_is_not_caught_by_the_ui() -> None:
    response = Client().get("/api/v1/health/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert response.json() == {"status": "ok"}


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize(
    "path", ["/devices/1", "/selftest", "/apix/", "/unknown/", "/static-files", "/administration"]
)
def test_page_paths_of_the_ui_serve_index_html(path: str) -> None:
    response = Client().get(path)

    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"
    assert '<div id="root"></div>' in response.content.decode()
    assert response["Cache-Control"] == "no-cache"


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize(
    "path",
    [
        "/api",
        "/api/",
        "/api/v1/",
        "/api/v1/unknown",
        "/api/v1/unknown/",
        "/static",
        "/static/missing.js",
        "/_allauth/x",
        "/accounts/x",
    ],
)
def test_reserved_paths_never_serve_the_ui(path: str) -> None:
    response = Client().get(path)

    assert response.status_code == 404
    assert '<div id="root">' not in response.content.decode()


@pytest.mark.usefixtures("built_ui")
def test_admin_without_slash_redirects_instead_of_serving_the_ui() -> None:
    response = Client().get("/admin")

    assert response.status_code == 301
    assert response["Location"] == "/admin/"


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize("path", ["/", "/devices/1"])
def test_ui_sets_the_csrf_cookie(path: str) -> None:
    response = Client().get(path)

    cookie = response.cookies[settings.CSRF_COOKIE_NAME]
    assert cookie.value
    assert cookie["samesite"] == "Lax"


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize("path", ["/", "/devices/1"])
def test_ui_paths_reject_writes(path: str) -> None:
    assert Client().head(path).status_code == 200
    assert Client().post(path).status_code == 405
    assert Client(enforce_csrf_checks=True).post(path).status_code == 403


@pytest.mark.usefixtures("missing_ui")
def test_root_without_built_ui_is_404() -> None:
    response = Client().get("/")

    assert response.status_code == 404
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert "not part of this build" in response.content.decode()


@pytest.mark.usefixtures("missing_ui")
def test_api_works_without_built_ui() -> None:
    response = Client().get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


COLLECT_STATIC = """
import json, sys
import django
from django.conf import settings
from django.core.management import call_command
from django.test.utils import override_settings

django.setup()
with override_settings(STATIC_ROOT=sys.argv[1]):
    call_command("collectstatic", "--noinput", verbosity=0)
print(json.dumps({"dirs": [str(d) for d in settings.STATICFILES_DIRS],
                  "url": settings.STATIC_URL}))
"""


def test_collectstatic_copies_the_build_without_database(tmp_path: Path) -> None:
    dist = write_build(tmp_path / "dist")
    static_root = tmp_path / "collected"

    # The database host cannot resolve (see run_python): no connection needed.
    result = run_python(COLLECT_STATIC, {"TWOX_WEB_DIST_DIR": str(dist)}, args=[str(static_root)])

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"dirs": [str(dist)], "url": "/static/"}
    assert (static_root / "index.html").read_text(encoding="utf-8") == INDEX_HTML
    collected = sorted(
        path.relative_to(static_root).as_posix()
        for path in static_root.rglob("*")
        if path.is_file()
    )
    # The build plus the admin's files; nothing from other app folders (for
    # example DRF's own assets below rest_framework/).
    outside_admin = [name for name in collected if not name.startswith("admin/")]
    assert outside_admin == ["assets/index-abc123.js", "assets/index-def456.css", "index.html"]
    assert "admin/css/base.css" in collected
    assert not (static_root / "rest_framework").exists()
    # The licence files of the libraries the admin ships are served too.
    for library in ("jquery", "select2", "xregexp"):
        licences = list((static_root / "admin" / "js" / "vendor" / library).glob("LICENSE*"))
        assert len(licences) == 1, library


def test_admin_finder_searches_the_admin_app_only() -> None:
    finder = AdminAppDirectoriesFinder()

    found = sorted(path for path, _ in finder.list([]))

    assert finder.apps == [ADMIN_APP_NAME]
    assert "admin/css/base.css" in found
    assert all(path.startswith("admin/") for path in found)


def test_missing_build_adds_no_static_folder(tmp_path: Path) -> None:
    result = run_python(
        "import django, json\n"
        "from django.conf import settings\n"
        "django.setup()\n"
        "print(json.dumps([str(d) for d in settings.STATICFILES_DIRS]))\n",
        {"TWOX_WEB_DIST_DIR": str(tmp_path / "no-build")},
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == []
