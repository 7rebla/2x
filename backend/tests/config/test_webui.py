"""Delivery of the built web UI: index.html at /, the build below /static/.

Every test works on a prepared folder, never on a real build.
"""

import json
from pathlib import Path

import pytest
from django.test import Client
from pytest_django.fixtures import Settings

from tests.config.test_settings import run_python

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


@pytest.fixture
def built_ui(tmp_path: Path, settings: Settings) -> Path:
    """Point STATIC_ROOT at a prepared build, as collectstatic leaves it in the image."""
    static_root = write_build(tmp_path / "staticfiles")
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
def test_api_is_not_caught_by_the_ui() -> None:
    response = Client().get("/api/v1/health/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert response.json() == {"status": "ok"}


@pytest.mark.usefixtures("built_ui")
@pytest.mark.parametrize("path", ["/api/", "/api/v1/", "/api/v1/unknown/", "/unknown/"])
def test_unknown_paths_are_404_not_the_ui(path: str) -> None:
    response = Client().get(path)

    assert response.status_code == 404
    assert '<div id="root">' not in response.content.decode()


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
    assert (static_root / "assets" / "index-abc123.js").is_file()
    assert (static_root / "assets" / "index-def456.css").is_file()


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
