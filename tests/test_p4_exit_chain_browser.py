"""P4 slice 9 -- exit run: the full chain, in a real browser, for each of the three modes.

Find Work -> Enter -> Agreement -> Mission (Mission Control with mission_id) -> Deploy (ARM preflight +
agreement-bound deploy) -> Governance (constitutional gate) -> receipts visible, with the shell
Inspector carrying the addresses/IDs (post_id / mission_id / agreement_id / workentry) along the way.

Screens are driven where Phase 4 draws one. Where no screen exists (the governance meeting/motion/vote
itself, the operator countersign, slot creation) the step is an API call and is marked as such: nothing
is invented client-side. Every browser assertion compares the screen with the server's own record.
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

REPO = Path(__file__).resolve().parents[1]
GATE_WINDOW_HOURS = 0.004   # 14.4 s

SERVE = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from app.server import create_app
import uvicorn
uvicorn.run(create_app(Path(sys.argv[2])), host="127.0.0.1", port=int(sys.argv[3]), log_level="warning")
"""


class Live:
    def __init__(self, url, admin):
        self.url, self.admin = url, admin


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    root = tmp_path_factory.mktemp("p4_exit_root")
    for d in ("config", "frontend"):
        shutil.copytree(REPO / d, root / d)
    for d in ("data", "vault"):
        (root / d).mkdir(exist_ok=True)
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    admin = "p4-exit-" + uuid.uuid4().hex
    env = dict(os.environ, CIVITAE_ADMIN_KEY=admin, KASSA_JWT_SECRET="p4-exit-jwt-" + uuid.uuid4().hex)
    env.pop("CIVITAE_DEV_MODE", None)
    env.pop("RAILWAY_ENVIRONMENT", None)
    proc = subprocess.Popen([sys.executable, "-c", SERVE, str(REPO), str(root), str(port)], env=env, cwd=str(root))
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
        pytest.fail("server did not start")
    lv = Live(url, admin)
    # the async window is owner-configurable; seconds let the real motion close without waiting a day
    # (slice 10: votes at/after closes_at are refused, so 0 admits no vote). Slice 11 (G2): the window starts
    # when the motion is created and every vote must land inside it, so it needs real headroom over the
    # meeting/join/vote HTTP round trips on a loaded machine (~14 s; was 5.4 s, which left under 5 s of slack).
    r = httpx.post(url + "/api/work-entry/gate/settings", headers={"X-Admin-Key": admin},
                   json={"gate_window_hours": GATE_WINDOW_HOURS}, timeout=10)
    assert r.status_code == 200, r.text
    yield lv
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            # Local server only: external fonts/analytics fail fast instead of
            # stalling the page 'load' event (the exit-chain flake, run 37).
            b = p.chromium.launch(args=["--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1"])
        except Exception as e:  # browser binary missing
            pytest.skip(f"chromium unavailable: {e}")
        yield b
        b.close()


# ── helpers ──────────────────────────────────────────────────────────────

def _ip():
    return f"10.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


def agent(live):
    r = httpx.post(live.url + "/api/provision/signup",
                   json={"name": "X9-" + uuid.uuid4().hex[:6], "system": "claude"},
                   headers={"x-forwarded-for": _ip()}, timeout=10)
    assert r.status_code == 200, r.text
    a = r.json()
    return {"id": a["agent_id"], "key": a["api_key"], "jwt": a["token"],
            "h": {"Authorization": "Bearer " + a["api_key"]}}


def api(live, who, method, path, **kw):
    hd = who["h"] if "h" in who else who
    return httpx.request(method, live.url + path, headers=hd, timeout=15, **kw)


def admin(live):
    return {"X-Admin-Key": live.admin}


def make_post(live, owner):
    r = httpx.post(live.url + "/api/kassa/posts", headers={**owner["h"], "x-forwarded-for": _ip()},
                   json={"tab": "bounties", "title": "Exit " + uuid.uuid4().hex[:5], "body": "Build the thing",
                         "from_name": "Owner", "from_email": "owner@example.com", "tag": "t"}, timeout=10)
    assert r.status_code == 200, r.text
    kid = r.json()["id"]
    ap = httpx.patch(live.url + f"/api/operator/reviews/rev-{kid}", params={"action": "approve"},
                     headers=admin(live), timeout=10)
    assert ap.status_code == 200, ap.text
    return kid


def make_slot(live, owner, **extra):
    r = api(live, owner, "POST", "/api/slots/create",
            json={"label": "X9", "positions": [{"row": 0, "col": 0}], "roles": ["primary"], **extra})
    assert r.status_code == 200, r.text
    return r.json()["slots"][0]


def signed_in(browser, who):
    ctx = browser.new_context()
    ctx.add_init_script(f"""try {{
        localStorage.setItem('au_agent_id', {who['id']!r});
        localStorage.setItem('au_api_key', {who['key']!r});
        localStorage.setItem('kassa_jwt', {who['jwt']!r});
    }} catch (e) {{}}""")
    return ctx


def tid(page, name):
    return page.locator(f'[data-testid="{name}"]')


def enter_through_modal(page, note="chain walk"):
    """INTENT -> TERMS -> PREFLIGHT -> CONFIRM, then return the receipt screen's agreement id + state."""
    page.wait_for_selector("#enter-modal")
    page.wait_for_function("() => document.querySelector('#enter-modal').innerText.includes('How do you want in?')")
    page.fill("#cve-note", note)
    page.click("#cve-continue")                       # INTENT -> TERMS
    page.click("#cve-continue")                       # TERMS -> PREFLIGHT
    page.click("#cve-continue")                       # PREFLIGHT -> CONFIRM
    page.click("#cve-confirm")
    page.wait_for_selector('[data-testid="enter-receipt"]')
    return page.locator('[data-k="agreement-id"]').inner_text(), page.locator('[data-k="agreement-state"]').inner_text()


def mission_of(live, who, aid):
    ag = api(live, who, "GET", f"/api/work-entry/{aid}").json()["agreement"]
    assert ag["objects"]["mission_id"], ag
    return ag["objects"]["mission_id"]


def mission_control_shows(browser, live, who, mid, aid, want_state, want_mode):
    ctx = signed_in(browser, who)
    page = ctx.new_page()
    page.goto(live.url + f"/missions?mission={mid}")
    node = tid(page, "agreement-node")
    node.wait_for()
    assert node.get_attribute("data-agreement-id") == aid and node.get_attribute("data-state") == want_state
    got = api(live, who, "GET", f"/api/work-entry/mission/{mid}").json()
    assert got["entry_mode"] == want_mode and got["agreements"][0]["agreement"]["agreement_id"] == aid
    ac = got["agreements"][0]["acceptance"]
    assert page.locator('[data-k="acceptance-receipt"]').inner_text() == ac["acceptance_receipt_id"]
    assert page.locator('[data-k="acceptance-seed"]').inner_text() == ac["acceptance_seed_doi"]
    ctx.close()


def arm_and_deploy(browser, live, owner, mid, gate_kind_text=None):
    """ARM DEPLOY on /deploy (preflight only), confirm on /command (the one commit)."""
    ctx = signed_in(browser, owner)
    page = ctx.new_page()
    page.goto(live.url + "/deploy")
    page.click("#cve-arm-open")
    page.wait_for_function("m => document.querySelector('#cve-mission').value === m", arg=mid)
    page.click("#cve-arm")
    page.wait_for_selector('[data-testid="arm-available"]')
    pre = api(live, owner, "GET", f"/api/work-entry/mission/{mid}/deploy/preflight").json()
    assert pre["can_deploy"] is True
    if gate_kind_text:
        assert gate_kind_text in tid(page, "preflight").inner_text()
    href = page.locator("#cve-to-command").get_attribute("href")
    assert href == f"/command?mission={mid}"
    assert page.locator("#cve-deploy").count() == 0
    cmd = ctx.new_page()
    cmd.goto(live.url + href)
    cmd.click("#cve-arm")
    cmd.wait_for_selector("#cve-deploy")
    assert api(live, owner, "GET", f"/api/work-entry/mission/{mid}").json()["deployments"] == []
    cmd.click("#cve-deploy")
    cmd.wait_for_selector('[data-testid="deploy-receipt"]')
    dep = api(live, owner, "GET", f"/api/work-entry/mission/{mid}").json()["deployments"]
    assert len(dep) == 1
    assert dep[0]["receipt_id"] == cmd.locator('[data-k="deploy-receipt-id"]').inner_text()
    assert dep[0]["seed_doi"] == cmd.locator('[data-k="deploy-seed"]').inner_text()
    ctx.close()
    return dep[0]


def progress_ends_with_deploy(browser, live, who, mid, dep):
    ctx = signed_in(browser, who)
    page = ctx.new_page()
    page.goto(live.url + f"/missions?mission={mid}")
    tid(page, "agreement-node").wait_for()
    page.click('[data-tab="PROGRESS"]')
    steps = page.eval_on_selector_all('[data-testid="progress-list"] li', "els => els.map(e => e.dataset.transition)")
    assert steps[-1] == "deploy" and "activate" in steps
    assert dep["receipt_id"] in page.inner_text('[data-testid="progress-list"]')
    ctx.close()


def _insp(page):
    return page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#insp-fields .kv')]
        .map(r => [r.querySelector('b').textContent, r.querySelector('span').textContent]))""")


def _wait_insp(page, key, want):
    page.wait_for_function(
        "([k, v]) => [...document.querySelectorAll('#insp-fields .kv')].some(r => "
        "r.querySelector('b').textContent === k && r.querySelector('span').textContent === v)",
        arg=[key, want], timeout=15000)


def shell_carries_context(browser, live, who, mid, aid, mode, pid=None):
    """The shell keeps addresses/IDs (not rail position) across Mission Control, DEPLOY and COMMAND."""
    ctx = signed_in(browser, who)
    want = f"WorkEntryAgreement · {mode} · active"
    for route in (f"/missions?mission={mid}", f"/deploy?mission={mid}", f"/command?mission={mid}"):
        page = ctx.new_page()
        page.goto(live.url + f"/shell?route={route}")
        _wait_insp(page, "mission_id", mid)
        _wait_insp(page, "agreement_id", aid)
        _wait_insp(page, "workentry", want)
        page.close()
    if pid:
        page = ctx.new_page()
        page.goto(live.url + f"/shell?route=/kassa/post/{pid}")
        _wait_insp(page, "opportunity/post", pid)
        _wait_insp(page, "agreement_id", aid)
        page.close()
    ctx.close()


def gate_through_governance(live, owner, ent, aid):
    """API-driven (no Phase 4 screen for meetings/motions): meeting + typed motion + votes + sync +
    the owner-held operator countersign. Accept before this is refused."""
    third = agent(live)
    r = api(live, owner, "POST", f"/api/work-entry/{aid}/accept")
    assert r.status_code == 409 and r.json()["code"] == "governance_gate_required"
    m = api(live, owner, "POST", "/api/governance/meeting", json={"caller": owner["id"], "subject": "gate", "quorum": 1})
    assert m.status_code == 200, m.text
    meet = m.json()["id"]
    for o in (ent, third):
        assert api(live, o, "POST", f"/api/governance/meeting/{meet}/join", json={"agent_id": o["id"]}).status_code == 200
    mo = api(live, owner, "POST", f"/api/governance/meeting/{meet}/motion",
             json={"proposer": owner["id"], "motion": "", "kind": "work_entry_gate", "agreement_id": aid})
    assert mo.status_code == 200, mo.text
    for who in (owner, ent, third):
        v = api(live, who, "POST", f"/api/governance/meeting/{meet}/vote",
                json={"voter": who["id"], "motion_id": mo.json()["id"], "vote": "yea"})
        assert v.status_code == 200, v.text
    from datetime import datetime, UTC
    wait = (datetime.fromisoformat(mo.json()["closes_at"]) - datetime.now(UTC)).total_seconds()
    time.sleep(max(0.0, wait) + 0.3)   # the window must elapse before the motion resolves
    # poll rather than trust one sync: a pending result right after the window is a clock edge, not a verdict
    deadline = time.time() + 15
    while True:
        g = api(live, owner, "POST", f"/api/work-entry/{aid}/gate/sync").json()
        if g["gates"] and g["gates"][0]["result"] != "pending" or time.time() > deadline:
            break
        time.sleep(0.5)
    assert g["gates"][0]["result"] == "passed", g
    # a passed motion alone does not bind while the body is advisory
    r = api(live, owner, "POST", f"/api/work-entry/{aid}/accept")
    assert r.status_code == 409 and r.json()["code"] == "owner_countersign_required"
    cs = api(live, admin(live), "POST", f"/api/work-entry/{aid}/gate/countersign")
    assert cs.status_code == 200, cs.text
    return cs.json()["gate"]


# ═══ the three modes ═════════════════════════════════════════════════════

def test_chain_standard_mode(live, browser):
    owner, ent = agent(live), agent(live)
    pid = make_post(live, owner)
    # Find Work -> Enter (the board card, then the real modal)
    ctx = signed_in(browser, ent)
    page = ctx.new_page()
    page.goto(live.url + "/kassa")
    page.click('[data-tab="bounties"]')
    card = page.locator(f'.card[data-id="{pid}"]')
    card.wait_for()
    card.locator(".btn-enter").click()
    aid, state = enter_through_modal(page)
    assert state == "pending"
    rec = api(live, ent, "GET", f"/api/work-entry/{aid}").json()
    assert rec["agreement"]["entry_mode"] == "standard" and rec["agreement"]["objects"]["post_id"] == pid
    assert page.locator('[data-k="receipt-id"]').inner_text() == rec["receipts"][-1]["receipt_id"]
    ctx.close()
    # Agreement: the poster accepts and the entrant activates, on the post page
    octx = signed_in(browser, owner)
    op = octx.new_page()
    op.goto(live.url + f"/kassa/post/{pid}")
    row = op.locator(f'[data-testid="entry-row"][data-agreement-id="{aid}"]')
    row.wait_for()
    row.locator('[data-act="accept"]').click()
    op.wait_for_selector(f'[data-agreement-id="{aid}"][data-state="accepted"]')
    op.locator(f'[data-agreement-id="{aid}"] [data-act="activate"]').click()
    op.wait_for_selector(f'[data-agreement-id="{aid}"][data-state="active"]')
    octx.close()
    mid = mission_of(live, owner, aid)
    # Mission -> Deploy -> receipts -> shell
    mission_control_shows(browser, live, ent, mid, aid, "active", "standard")
    dep = arm_and_deploy(browser, live, owner, mid)
    assert dep["agreement_id"] == aid and dep["entry_mode"] == "standard" and dep["gate_id"] is None
    progress_ends_with_deploy(browser, live, owner, mid, dep)
    shell_carries_context(browser, live, ent, mid, aid, "standard", pid=pid)
    hist = api(live, owner, "GET", f"/api/work-entry/{aid}").json()
    assert [h["transition"] for h in hist["agreement"]["state_history"]][-3:] == ["file", "accept", "activate"]
    assert all(rc["seed_doi"] for rc in hist["receipts"])


def test_chain_open_mode(live, browser):
    owner, ent = agent(live), agent(live)
    s = make_slot(live, owner)                       # slot creation: API (no Phase 4 screen)
    ctx = signed_in(browser, ent)
    page = ctx.new_page()
    page.goto(live.url + "/kassa")
    page.evaluate("ref => window.CIVITAE_ENTRY.openEnter({ref, title: 'slot'})", f"slot:{s['id']}")
    aid, state = enter_through_modal(page)
    assert state == "accepted"                       # click 1: the object exists, mission still PUBLISHED
    page.click("#cve-click2")
    page.wait_for_function("() => document.querySelector('[data-k=agreement-state]').textContent === 'active'")
    mid = s["mission_id"]
    assert tid(page, "mc-link").get_attribute("href") == f"/missions?mission={mid}"
    ag = api(live, ent, "GET", f"/api/work-entry/{aid}").json()
    assert ag["agreement"]["state"] == "active" and ag["agreement"]["entry_mode"] == "open"
    assert ag["agreement"]["objects"]["slot_id"] == s["id"] and ag["agreement"]["objects"]["mission_id"] == mid
    # Mission Control follows the link the receipt screen gave
    page.click('[data-testid="mc-link"]')
    page.wait_for_selector('[data-testid="agreement-node"]')
    assert tid(page, "agreement-node").get_attribute("data-agreement-id") == aid
    ctx.close()
    dep = arm_and_deploy(browser, live, owner, mid)
    assert dep["agreement_id"] == aid and dep["entry_mode"] == "open" and dep["gate_id"] is None
    progress_ends_with_deploy(browser, live, ent, mid, dep)
    shell_carries_context(browser, live, ent, mid, aid, "open")
    # the legacy loop still compresses steps, never the object: history has every transition
    hist = api(live, ent, "GET", f"/api/work-entry/{aid}").json()
    assert [h["transition"] for h in hist["agreement"]["state_history"]][-3:] == ["file", "resolve_open", "activate"]


def test_chain_constitutional_mode(live, browser):
    owner, ent = agent(live), agent(live)
    s = make_slot(live, owner, entry_mode="constitutional")
    ctx = signed_in(browser, ent)
    page = ctx.new_page()
    page.goto(live.url + "/kassa")
    page.evaluate("ref => window.CIVITAE_ENTRY.openEnter({ref, title: 'slot'})", f"slot:{s['id']}")
    page.wait_for_selector("#enter-modal")
    page.wait_for_function("() => document.querySelector('#enter-modal').innerText.includes('How do you want in?')")
    page.fill("#cve-note", "constitutional chain")
    page.click("#cve-continue")
    assert page.locator('[data-k="mode"]').inner_text() == "Constitutional"
    page.click("#cve-continue"); page.click("#cve-continue"); page.click("#cve-confirm")
    page.wait_for_selector('[data-testid="enter-receipt"]')
    aid = page.locator('[data-k="agreement-id"]').inner_text()
    assert page.locator('[data-k="agreement-state"]').inner_text() == "pending"
    ctx.close()
    # Governance: the gate stands between pending and accepted/active
    gate = gate_through_governance(live, owner, ent, aid)
    assert api(live, owner, "POST", f"/api/work-entry/{aid}/accept").status_code == 200
    assert api(live, ent, "POST", f"/api/work-entry/{aid}/activate").status_code == 200
    mid = mission_of(live, owner, aid)
    assert mid == s["mission_id"]
    mission_control_shows(browser, live, ent, mid, aid, "active", "constitutional")
    # Deploy: the preflight on the screen names the gate and says it is satisfied
    dep = arm_and_deploy(browser, live, owner, mid, gate_kind_text="satisfied")
    assert dep["entry_mode"] == "constitutional" and dep["gate_id"] == gate["gate_id"]
    progress_ends_with_deploy(browser, live, ent, mid, dep)
    shell_carries_context(browser, live, ent, mid, aid, "constitutional")
    hist = api(live, ent, "GET", f"/api/work-entry/{aid}").json()
    assert [h["transition"] for h in hist["agreement"]["state_history"]][-3:] == ["file", "accept", "activate"]
    assert all(rc["seed_doi"] for rc in hist["receipts"]) and hist["gates"][0]["gate_id"] == gate["gate_id"]


def test_chain_refuses_deploy_without_the_chain(live, browser):
    """Negative end: a mission whose entry never became an active Agreement cannot be armed."""
    owner = agent(live)
    s = make_slot(live, owner, entry_mode="standard")
    ctx = signed_in(browser, owner)
    page = ctx.new_page()
    page.goto(live.url + f"/command?mission={s['mission_id']}")
    page.click("#cve-arm")
    page.wait_for_selector('[data-testid="arm-blocked"]')
    assert tid(page, "arm-blocked").get_attribute("data-blocking") == "no_active_agreement"
    assert page.locator("#cve-deploy").count() == 0
    ctx.close()


def test_browser_is_sealed_from_external_hosts(browser):
    """Guard for the run-37 flake: external fonts/analytics must fail at once, never stall 'load'."""
    page = browser.new_page()
    t0 = time.time()
    with pytest.raises(sync_api.Error, match="ERR_NAME_NOT_RESOLVED"):
        page.goto("https://fonts.googleapis.com/", timeout=10000)
    assert time.time() - t0 < 5
    page.close()
