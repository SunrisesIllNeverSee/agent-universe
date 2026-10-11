"""Frontend route coverage: repaired pages serve 200; no hard-coded localhost URLs."""
from __future__ import annotations

import re
from pathlib import Path

import shutil

import pytest

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@pytest.fixture(autouse=True)
def _stage_pages(tmp_root):
    """The shared test app serves a temp frontend dir; stage the pages under test."""
    dest = tmp_root / "frontend"
    staged = [dest / "helpwanted.html", dest / "campaign.html", dest / "guides"]
    shutil.copy2(FRONTEND / "helpwanted.html", dest / "helpwanted.html")
    shutil.copy2(FRONTEND / "campaign.html", dest / "campaign.html")
    shutil.copytree(FRONTEND / "guides", dest / "guides", dirs_exist_ok=True)
    yield
    for p in staged:
        shutil.rmtree(p) if p.is_dir() else p.unlink(missing_ok=True)


@pytest.mark.parametrize("path", [
    "/guides",
    "/guides/how-to-register-an-agent",
    "/guides/how-to-post-a-mission",
    "/guides/how-to-join-a-mission",
    "/guides/how-to-use-the-mcp-bridge",
    "/helpwanted",
    "/campaign",
])
def test_repaired_pages_serve(client, path):
    assert client.get(path).status_code == 200


def test_webmcp_js_served_as_javascript(client, tmp_root):
    shutil.copy2(FRONTEND / "webmcp.js", tmp_root / "frontend" / "webmcp.js")
    r = client.get("/webmcp.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]


@pytest.mark.parametrize("path", ["/guides/nope", "/guides/..%2Fapp", "/guides/index"])
def test_unknown_guide_404(client, path):
    assert client.get(path).status_code == 404


def test_guides_index_links_every_guide():
    html = (FRONTEND / "guides" / "index.html").read_text()
    for f in (FRONTEND / "guides").glob("how-to-*.html"):
        assert f"/guides/{f.stem}" in html


def test_frontend_has_no_localhost_api_urls():
    pat = re.compile(r"https?://(localhost|127\.0\.0\.1)")
    offenders = [
        str(p.relative_to(FRONTEND))
        for p in FRONTEND.rglob("*")
        if p.suffix in {".html", ".js"} and pat.search(p.read_text(errors="ignore"))
    ]
    assert not offenders, offenders


def test_nav_js_guards_null_body():
    src = (FRONTEND / "_nav.js").read_text()
    assert "document.body.appendChild(wmcp)" not in src
    assert "if (document.body) document.body.appendChild(footer)" in src
