"""P3 shell: route, structure, separation semantics, context derivation."""
from pathlib import Path


def test_shell_route_serves(client):
    r = client.get("/shell")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_shell_route_deep_link(client):
    r = client.get("/shell?route=/kassa")
    assert r.status_code == 200


def test_shell_structure_landmarks():
    html = Path("frontend/shell.html").read_text()
    for landmark in ('id="rail"', 'id="sidebar"', 'id="canvas"',
                     'id="inspector"', 'id="hud"'):
        assert landmark in html, f"missing {landmark}"
    # 9 modes + utility
    assert html.count('label:"') == 9


def test_shell_separation_semantics():
    """Mission Control != COMMAND != DEPLOY != CAMPAIGN stay distinct modes."""
    html = Path("frontend/shell.html").read_text()
    for mode in ('label:"MISSION CONTROL"', 'label:"DEPLOY"',
                 'label:"COMMAND"', 'label:"CAMPAIGN"'):
        assert mode in html
    # each maps to its own routes — no cross-contamination
    assert 'id:"deploy",  label:"DEPLOY",    routes:["/deploy"]' in html
    assert 'id:"command", label:"COMMAND",   routes:["/command"]' in html


def test_shell_no_fake_authority():
    html = Path("frontend/shell.html").read_text()
    # Phase-4 objects must render as placeholders, never as records
    assert "PHASE-4" in html
    assert "not implemented" in html
    # no write endpoints called by the shell itself — read-only + hosted pages
    import re
    assert not re.search(r'fetch\([^)]*method\s*:\s*["\']POST', html), \
        "shell must not issue writes"


def test_shell_principal_readonly():
    html = Path("frontend/shell.html").read_text()
    # principal resolution uses existing credential surfaces only
    assert "/api/kassa/agent/me" in html
    assert "/api/provision/status/" in html
    # HUD reads the existing public state model, no new event subscription
    assert "/api/state" in html
