"""test_p5m_admin_no_analytics.py -- owner decision: no third-party scripts on any admin/operator page.

Pages that handle the admin key (X-Admin-Key) must load only first-party scripts and carry no
analytics (gtag / GTM / PostHog / beacon) init, and must not preconnect to third-party hosts.
"""
import re
from pathlib import Path

from starlette.routing import Route

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
FIRST_PARTY = re.compile(r"^(/(?!/)|https://(www\.)?signomy\.xyz(/|$))")
BANNED = ("googletagmanager", "google-analytics", "gtag(", "dataLayer", "posthog", "ai-beacon", "fonts.googleapis", "fonts.gstatic")


def _admin_pages(app):
    """Every frontend HTML page served on an /admin or /operator route, plus any page that uses the admin key."""
    pages = set()
    for r in app.routes:
        if isinstance(r, Route) and re.match(r"^/(admin|operator)(/|$)", r.path) and "{" not in r.path:
            resp = None
            from starlette.testclient import TestClient
            resp = TestClient(app, raise_server_exceptions=False).get(r.path)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                for f in FRONTEND.glob("*.html"):
                    if f.read_bytes() == resp.content:
                        pages.add(f)
    for f in FRONTEND.glob("*.html"):
        t = f.read_text()
        if f.name.startswith("admin") or re.search(r"""headers\s*:\s*\{[^}]*['"]X-Admin-Key['"]\s*:\s*adminKey""", t) or "var adminKey" in t:
            pages.add(f)
    return sorted(pages)


def test_admin_pages_enumerated(app):
    names = {p.name for p in _admin_pages(app)}
    assert {"admin.html", "admin-payouts.html"} <= names, names


def test_admin_pages_have_only_first_party_scripts_and_links(app):
    pages = _admin_pages(app)
    assert pages
    for page in pages:
        src = page.read_text()
        for m in re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", src):
            assert FIRST_PARTY.match(m), (page.name, m)
        for tag in re.findall(r"<link\b[^>]*>", src):
            href = re.search(r"href=[\"']([^\"']+)[\"']", tag)
            if href and re.match(r"(https?:)?//", href.group(1)):
                assert FIRST_PARTY.match(href.group(1)), (page.name, tag)
            if "preconnect" in tag or "dns-prefetch" in tag:
                assert href and FIRST_PARTY.match(href.group(1)), (page.name, tag)
        low = src.lower()
        for bad in BANNED:
            assert bad.lower() not in low, (page.name, bad)
