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
    # 11 modes (original 9; GOVERN split into Civitas + Comms; World split
    # out of ORIENT) in 4 groups + utility
    assert html.count('label:"') == 11


def test_shell_separation_semantics():
    """Mission Control != COMMAND != DEPLOY != CAMPAIGN stay distinct modes."""
    html = Path("frontend/shell.html").read_text()
    for mode in ('label:"MISSION CONTROL"', 'label:"DEPLOY"',
                 'label:"COMMAND"', 'label:"CAMPAIGN"'):
        assert mode in html
    # each maps to its own routes — no cross-contamination
    assert 'id:"deploy",  group:"work", label:"DEPLOY",    routes:["/deploy"]' in html
    assert 'id:"command", group:"work", label:"COMMAND",   routes:["/command"]' in html


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


# ── Object-context derivation (Task A, RESUME item 1) ────────────────────────
def _derive_src():
    html = Path("frontend/shell.html").read_text()
    start = html.index("function deriveContext()")
    end = html.index('frame.addEventListener("load", deriveContext)')
    return html[start:end]


def test_hosted_deploy_slots_pages_expose_no_url_params():
    """Evidence for why deriveContext adds no new keys for /deploy and /slots:
    neither hosted page reads location.search/hash/URLSearchParams (their slot,
    formation and deployment state is in-memory only). If this fails, a hosted
    page gained a real URL param and deriveContext/Inspector should be extended."""
    for page in ("frontend/deploy.html", "frontend/slots.html"):
        src = Path(page).read_text()
        for needle in ("URLSearchParams", "location.search", "location.hash",
                       "searchParams"):
            assert needle not in src, f"{page} now reads {needle}"


def test_derive_context_clears_all_keys_on_navigation_and_catch():
    src = _derive_src()
    keys = '["post_id","thread_id","mission_id","slot_id"]'
    # cleared at the top of every derivation AND in the catch path
    assert src.count(keys + ".forEach(k=>setCtx(k,null))") == 2
    # every key that deriveContext sets is in the cleared list
    import re
    for k in set(re.findall(r'setCtx\("(\w+)"\s*,\s*(?!null)', src)):
        assert f'"{k}"' in keys, f"{k} is set but never cleared"


def test_inspector_phase4_rows_are_placeholders_never_values():
    html = Path("frontend/shell.html").read_text()
    assert '["agreement_id", "PHASE-4 — not implemented"]' in html
    assert '["workentry", "PHASE-4 — not implemented"]' in html
    # deriveContext must never populate Phase-4 objects
    src = _derive_src()
    for forbidden in ("agreement", "workentry", "work_entry"):
        assert forbidden not in src.lower()


def test_inspector_values_use_textcontent_only():
    html = Path("frontend/shell.html").read_text()
    start = html.index("function renderInspector()")
    end = html.index("// ── Principal")
    body = html[start:end]
    assert "sp.textContent = v" in body
    assert "innerHTML" not in body.replace('host.innerHTML = ""', "")
    assert "insertAdjacentHTML" not in body


def test_derive_context_known_param_shapes_pinned():
    """Pin the shapes that ARE real (kassa path ids, /mission?id= and
    /mission/<id>) and that deploy/slots only use the legacy optional
    ?slot=/?id= read (no hosted page emits it today; see EVIDENCE.md)."""
    src = _derive_src()
    assert '"/kassa/post/"' in src and '"/kassa/thread/"' in src
    assert 'path === "/mission"' in src and 'path.startsWith("/mission/")' in src
    assert 'searchParams.get("slot")' in src


# ── P4 slice 0: rail regroup (navigation only) ───────────────────────────────
import json
import re

GROUP_HEADINGS = ["USER", "WORK", "CIVIC", "LEDGER & WORLD"]


def _modes():
    html = Path("frontend/shell.html").read_text()
    out = {}
    for m in re.finditer(r'\{id:"(\w+)",\s*group:"(\w+)",\s*label:"([^"]+)",\s*routes:\[([^\]]*)\]', html):
        out[m.group(1)] = (m.group(2), m.group(3), re.findall(r'"([^"]+)"', m.group(4)))
    return html, out


def test_rail_has_four_owner_groups_in_order():
    html, _ = _modes()
    m = re.search(r"const GROUPS = \[(.*?)\];", html, re.S)
    assert m, "GROUPS table missing"
    assert re.findall(r'title:"([^"]+)"', m.group(1)) == GROUP_HEADINGS


def test_rail_group_membership():
    _, modes = _modes()
    by_group = {}
    for mid, (g, label, _r) in modes.items():
        by_group.setdefault(g, []).append(mid)
    assert by_group["user"] == ["orient"]
    assert by_group["work"] == ["find", "mc", "deploy", "command", "campaign"]
    assert by_group["civic"] == ["civitas", "comms"]
    assert by_group["ledger"] == ["econ", "world", "ref"]


def test_town_hall_not_formal_governance():
    _, modes = _modes()
    assert "/forums" in modes["comms"][2]
    assert "/forums" not in modes["civitas"][2]
    assert "/governance" in modes["civitas"][2]


def test_world_moved_out_of_orient():
    _, modes = _modes()
    assert "/world" not in modes["orient"][2]
    assert modes["world"][2] == ["/world"]


def test_review_gap_pages_have_a_sidebar_home():
    _, modes = _modes()
    homes = {r: m for m, (_g, _l, rs) in modes.items() for r in rs}
    for route in ("/seeds", "/advisory", "/earnings-journey"):
        assert route in homes, f"{route} has no mode"
    # and each is a registered page, so the shell will host it
    pages = json.loads(Path("config/pages.json").read_text())
    text = json.dumps(pages)
    for route in ("/seeds", "/advisory", "/earnings-journey"):
        assert f'"route": "{route}"' in text


def test_gated_tiles_not_rail_modes():
    _, modes = _modes()
    for bad in ("rank", "refinery", "switchboard"):
        assert bad not in modes


def test_utility_slot_is_gear_with_console_and_out():
    html = Path("frontend/shell.html").read_text()
    assert "⚙" in html
    assert 'id="util-console"' in html and 'id="util-outside"' in html
    assert 'aria-label="Console"' in html
