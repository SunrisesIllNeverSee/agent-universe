"""P3 shell exit, in a real browser: signed in through the entry door, every
rail mode renders its first surface inside the canvas without bouncing to the
cockpit login, the principal survives each move, and cold-load deep links are
checked against the registry before the first navigation.

Skipped when Playwright (python) or its Chromium is not installed.
"""
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest

sync_api = pytest.importorskip("playwright.sync_api")

MODES = [
    ("orient", "/portal"), ("find", "/kassa"), ("mc", "/agentdash"),
    ("deploy", "/deploy"), ("command", "/command"), ("campaign", "/campaign"),
    ("govern", "/governance"), ("econ", "/economics"), ("ref", "/vault"),
]


REPO = Path(__file__).resolve().parents[1]
SERVE = """
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from app.server import create_app
import uvicorn
uvicorn.run(create_app(Path(sys.argv[2])), host="127.0.0.1", port=int(sys.argv[3]), log_level="warning")
"""


@pytest.fixture(scope="module")
def live_url(tmp_path_factory):
    """Real frontend + page registry in an isolated root, own process, DEV_MODE off."""
    root = tmp_path_factory.mktemp("p3_browser_root")
    for d in ("config", "frontend"):
        shutil.copytree(REPO / d, root / d)
    for d in ("data", "vault"):
        (root / d).mkdir(exist_ok=True)
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    env = dict(os.environ, CIVITAE_ADMIN_KEY="p3-browser-" + uuid.uuid4().hex,
               KASSA_JWT_SECRET="p3-browser-jwt-" + uuid.uuid4().hex)
    env.pop("CIVITAE_DEV_MODE", None)
    env.pop("RAILWAY_ENVIRONMENT", None)
    proc = subprocess.Popen([sys.executable, "-c", SERVE, str(REPO), str(root), str(port)],
                            env=env, cwd=str(root))
    url = f"http://127.0.0.1:{port}"
    for _ in range(200):
        try:
            if httpx.get(url + "/shell", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail("shell server did not start")
    yield url
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # browser binary missing
            pytest.skip(f"chromium unavailable: {e}")
        yield b
        b.close()


def _frame_path(page):
    return page.evaluate("new URL(document.getElementById('frame').contentWindow.location.href).pathname")


def _wait_frame(page, path):
    page.wait_for_function(
        "p => { try { const w = document.getElementById('frame').contentWindow;"
        " return w.location.pathname === p && w.document.readyState === 'complete'; }"
        " catch (e) { return false; } }", arg=path, timeout=15000)


def test_shell_walks_nine_modes_signed_in(live_url, browser):
    resp = httpx.post(live_url + "/api/provision/signup",
                      json={"name": "P3Walk-" + uuid.uuid4().hex[:6], "system": "claude"},
                      headers={"x-forwarded-for": "10.9.9.9"}, timeout=10)
    assert resp.status_code == 200, resp.text
    agent = resp.json()
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(live_url + "/portal")
    # Exactly what /entry stores after signup (entry.html storeAndShow).
    page.evaluate("""a => {
        localStorage.setItem('au_agent_id', a.agent_id);
        localStorage.setItem('au_api_key', a.api_key);
        localStorage.setItem('kassa_jwt', a.token);
    }""", agent)
    page.goto(live_url + "/shell")
    page.wait_for_function(
        "id => document.getElementById('who-sub').textContent.includes(id)",
        arg=agent["agent_id"], timeout=15000)
    assert "cockpit pages" not in page.inner_text("#who-sub")

    for mode_id, first in MODES:
        page.click(f"#mode-{mode_id}")
        _wait_frame(page, first)
        assert _frame_path(page) == first, f"{mode_id} landed on {_frame_path(page)}"
        assert "on" in page.get_attribute(f"#mode-{mode_id}", "class")
        assert agent["agent_id"] in page.inner_text("#who-sub")
    ctx.close()


@pytest.mark.parametrize("hostile", [
    "/nonexistent-page", "/../etc/passwd", "/x/../api/operator/stats",
    "//evil.example/x", "/api/operator/stats", "/shell",
])
def test_cold_load_rejects_unregistered_routes(live_url, browser, hostile):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(live_url + "/shell?route=" + hostile)
    _wait_frame(page, "/portal")
    assert _frame_path(page) == "/portal"
    ctx.close()


def test_cold_load_keeps_registered_deep_link(live_url, browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(live_url + "/shell?route=/kassa")
    _wait_frame(page, "/kassa")
    assert page.inner_text("#mode-name") == "FIND WORK"
    ctx.close()
