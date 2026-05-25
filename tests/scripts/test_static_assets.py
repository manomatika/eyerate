"""
Regression test: eyerate static asset serving.

This test directly mounts the StaticFiles directory that EyeRatePlugin.on_load()
mounts at /eyerate/static, then verifies the compiled JS files are reachable.

BEFORE A1 reorganization: FAILS — src/eyerate/static/ did not exist, the mount
was silently skipped by the os.path.exists() guard, and both URLs returned 404.

AFTER A1 reorganization: PASSES — src/eyerate/static/js/{admin,dialogs}/ exist
and contain the compiled output.

Does NOT call on_load() directly (it requires a live SQLAlchemy Session).
Instead it replicates only the static-mount portion of on_load() — the logic
under test is trivially simple (one mount call) and this is sufficient.
"""
from pathlib import Path

import pytest

# fastapi and httpx are runtime deps of eyerate; if absent in the local
# Python env, skip gracefully rather than erroring.
fastapi = pytest.importorskip("fastapi", reason="fastapi not available in this environment")
pytest.importorskip("httpx", reason="httpx (TestClient dep) not available in this environment")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

# Resolve the static directory the same way plugin.py does:
#   os.path.join(os.path.dirname(__file__), "static")
# __file__ for plugin.py is src/eyerate/plugin.py → static is src/eyerate/static/
EYERATE_PKG = Path(__file__).parent.parent.parent / "src" / "eyerate"
STATIC_DIR = EYERATE_PKG / "static"


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.mount(
        "/eyerate/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="eyerate_static",
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_admin_securities_js_returns_200(client):
    r = client.get("/eyerate/static/js/admin/admin-securities.js")
    assert r.status_code == 200, (
        f"Expected 200, got {r.status_code}. "
        "Check that src/eyerate/static/js/admin/admin-securities.js exists."
    )


def test_admin_securities_js_content_type(client):
    r = client.get("/eyerate/static/js/admin/admin-securities.js")
    ct = r.headers.get("content-type", "")
    assert "javascript" in ct.lower(), f"Unexpected Content-Type: {ct!r}"


def test_admin_securities_js_body_non_empty(client):
    r = client.get("/eyerate/static/js/admin/admin-securities.js")
    assert len(r.content) > 0


def test_lookup_dialog_js_returns_200(client):
    r = client.get("/eyerate/static/js/dialogs/lookup-dialog.js")
    assert r.status_code == 200, (
        f"Expected 200, got {r.status_code}. "
        "Check that src/eyerate/static/js/dialogs/lookup-dialog.js exists."
    )


def test_lookup_dialog_js_content_type(client):
    r = client.get("/eyerate/static/js/dialogs/lookup-dialog.js")
    ct = r.headers.get("content-type", "")
    assert "javascript" in ct.lower(), f"Unexpected Content-Type: {ct!r}"


def test_lookup_dialog_js_body_non_empty(client):
    r = client.get("/eyerate/static/js/dialogs/lookup-dialog.js")
    assert len(r.content) > 0
