"""P4 slice 7 -- the screens, driven in a real browser against a real server.

Find Work Enter flow (INTENT/TERMS before CONFIRM), poster accept/reject/retire (signed-in and
magic link), Mission Control Agreement node + Acceptance record + PROGRESS, ARM DEPLOY preflight
(deploy page) + second confirmation (COMMAND), and the shell Inspector's real agreement_id /
workentry values. Every assertion compares the screen with the server's own record.

Skipped when Playwright (python) or its Chromium is not installed.
"""
import hashlib
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

sync_api = pytest.importorskip("playwright.sync_api")

REPO = Path(__file__).resolve().parents[1]
MAGIC_POST = "K-MAGIC7"
MAGIC_THREAD = "thr-magic7"
MAGIC_TOKEN = "magic-token-p4-slice7-" + "x" * 24

SERVE = """
import hashlib, os, sys
from datetime import UTC, datetime
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from app.server import create_app
import uvicorn
app = create_app(Path(sys.argv[2]))
from app.deps import state
now = datetime.now(UTC).isoformat()
state.kassa.insert_post({"id": sys.argv[4], "tab": "bounties", "title": "Magic poster post", "tag": "t",
    "body": "email-only poster", "from_name": "Poster", "from_email": "poster@example.com",
    "created_at": now, "updated_at": now, "status": "open", "poster_agent_id": None})
state.kassa.insert_thread({"thread_id": sys.argv[5], "post_id": sys.argv[4], "post_tab": "bounties",
    "post_title": "Magic poster post", "agent_id": "x", "agent_name": "x", "poster_name": "Poster",
    "poster_email": "poster@example.com", "magic_token": hashlib.sha256(sys.argv[6].encode()).hexdigest(),
    "status": "open", "message_count": 0, "created_at": now, "updated_at": now})
uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[3]), log_level="warning")
"""


class Live:
    def __init__(self, url, admin):
        self.url, self.admin = url, admin


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    root = tmp_path_factory.mktemp("p4_screens_root")
    for d in ("config", "frontend"):
        shutil.copytree(REPO / d, root / d)
    for d in ("data", "vault"):
        (root / d).mkdir(exist_ok=True)
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    admin = "p4-screens-" + uuid.uuid4().hex
    env = dict(os.environ, CIVITAE_ADMIN_KEY=admin, KASSA_JWT_SECRET="p4-screens-jwt-" + uuid.uuid4().hex)
    env.pop("CIVITAE_DEV_MODE", None)
    env.pop("RAILWAY_ENVIRONMENT", None)
    proc = subprocess.Popen([sys.executable, "-c", SERVE, str(REPO), str(root), str(port),
                             MAGIC_POST, MAGIC_THREAD, MAGIC_TOKEN], env=env, cwd=str(root))
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
    yield Live(url, admin)
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


# ── world helpers (API only) ─────────────────────────────────────────────

def _ip():
    return f"10.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


def agent(live):
    r = httpx.post(live.url + "/api/provision/signup",
                   json={"name": "S7-" + uuid.uuid4().hex[:6], "system": "claude"},
                   headers={"x-forwarded-for": _ip()}, timeout=10)
    assert r.status_code == 200, r.text
    a = r.json()
    return {"id": a["agent_id"], "key": a["api_key"], "jwt": a["token"],
            "h": {"Authorization": "Bearer " + a["api_key"]}}


def make_post(live, owner):
    r = httpx.post(live.url + "/api/kassa/posts", headers={**owner["h"], "x-forwarded-for": _ip()},
                   json={"tab": "bounties", "title": "Slice7 " + uuid.uuid4().hex[:5], "body": "Build the thing",
                         "from_name": "Owner", "from_email": "owner@example.com", "tag": "t"}, timeout=10)
    assert r.status_code == 200, r.text
    kid = r.json()["id"]
    ap = httpx.patch(live.url + f"/api/operator/reviews/rev-{kid}", params={"action": "approve"},
                     headers={"X-Admin-Key": live.admin}, timeout=10)
    assert ap.status_code == 200, ap.text
    return kid


def api(live, who, method, path, **kw):
    hd = who["h"] if isinstance(who, dict) else who
    return httpx.request(method, live.url + path, headers=hd, timeout=15, **kw)


def file_entry(live, ent, ref, **kw):
    r = api(live, ent, "POST", "/api/work-entry", json={"opportunity_ref": ref, "pitch": "I can do it", **kw})
    assert r.status_code == 201, r.text
    return r.json()["agreement"]["agreement_id"]


def active_world(live):
    """owner posts, entrant files, owner accepts (mints mission+slot), entrant activates."""
    owner, ent = agent(live), agent(live)
    pid = make_post(live, owner)
    aid = file_entry(live, ent, f"post:{pid}", delivery_evidence_class=2)
    assert api(live, owner, "POST", f"/api/work-entry/{aid}/accept").status_code == 200
    act = api(live, ent, "POST", f"/api/work-entry/{aid}/activate")
    assert act.status_code == 200, act.text
    mid = act.json()["mission_id"]
    assert mid
    return {"owner": owner, "ent": ent, "pid": pid, "aid": aid, "mid": mid}


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


# ═══ Find Work: Enter flow ═══════════════════════════════════════════════

def test_enter_flow_steps_before_commit_then_receipt(live, browser):
    owner, ent = agent(live), agent(live)
    pid = make_post(live, owner)
    ctx = signed_in(browser, ent)
    page = ctx.new_page()
    page.goto(live.url + f"/kassa/post/{pid}")
    page.click("#enter-btn")
    page.wait_for_selector("#enter-modal")
    # step 1 INTENT: nothing is written yet (wait out the async terms load: it was a timing race)
    page.wait_for_function("document.querySelector('#enter-modal').innerText.includes('How do you want in?')")
    assert "How do you want in?" in page.inner_text("#enter-modal")
    assert page.locator('[data-step="1"].cur').count() == 1
    assert "Stake" in page.inner_text("#enter-modal")      # stake stays separate, never converts
    page.fill("#cve-note", "I shipped this before")
    page.click("#cve-continue")
    # step 2 TERMS: values are the server's
    assert page.locator('[data-step="2"].cur').count() == 1
    pv = httpx.get(live.url + f"/api/work-entry/opportunity/post:{pid}").json()
    assert tid(page, "opp-ref").count() == 0 and page.locator('[data-k="opp-ref"]').inner_text() == f"post:{pid}"
    assert page.locator('[data-k="mode"]').inner_text() == "Standard" and pv["entry_mode"] == "standard"
    assert page.locator('[data-k="acceptance"]').inner_text() == pv["acceptance"]["text"]
    page.select_option("#cve-ev", "solution_proof")
    assert api(live, ent, "GET", "/api/work-entry", params={"entrant": ent["id"]}).json()["count"] == 0
    page.click("#cve-continue")
    # step 3 PREFLIGHT: seven ordered steps, steps 4-7 waiting
    assert page.locator('[data-testid="preflight-list"] li').count() == 7
    assert ent["id"] in page.inner_text('[data-testid="preflight-list"]')
    page.click("#cve-continue")
    # step 4 CONFIRM: still nothing written
    assert page.locator('[data-k="principal"]').inner_text() == ent["id"]
    assert "Force assign" in page.inner_text('[data-testid="force-assign"]') and "ADMIN ONLY" in page.inner_text('[data-testid="force-assign"]')
    assert api(live, ent, "GET", "/api/work-entry", params={"entrant": ent["id"]}).json()["count"] == 0
    page.click("#cve-confirm")
    page.wait_for_selector('[data-testid="enter-receipt"]')
    aid = page.locator('[data-k="agreement-id"]').inner_text()
    assert page.locator('[data-k="agreement-state"]').inner_text() == "pending"
    rec = api(live, ent, "GET", f"/api/work-entry/{aid}").json()
    # G2: the entrant is told who it waits on, and the poster's typical response time (from the API)
    assert rec["waiting_on"] == "poster"
    assert page.locator('[data-testid="waiting-on-poster"]').text_content() == \
        "Waiting on the poster · " + rec["poster_response"]["label"] + " · " + rec["pending_windows"]["label"]
    assert rec["agreement"]["state"] == "pending" and rec["agreement"]["terms"]["pitch"] == "I shipped this before"
    assert rec["agreement"]["terms"]["delivery_evidence_class"] == "solution_proof"
    assert page.locator('[data-k="receipt-id"]').inner_text() == rec["receipts"][-1]["receipt_id"]
    assert page.locator('[data-k="seed-doi"]').inner_text() == rec["receipts"][-1]["seed_doi"]
    ctx.close()


def test_enter_flow_on_the_board_and_duplicate_is_loud(live, browser):
    owner, ent = agent(live), agent(live)
    pid = make_post(live, owner)
    aid = file_entry(live, ent, f"post:{pid}")
    ctx = signed_in(browser, ent)
    page = ctx.new_page()
    page.goto(live.url + "/kassa")
    page.click('[data-tab="bounties"]')
    card = page.locator(f'.card[data-id="{pid}"]')
    card.wait_for()
    # original labels stay: the Respond (contact) button is still there beside Enter
    assert "Respond" in card.inner_text()
    card.locator(".btn-enter").click()
    page.wait_for_selector("#enter-modal")
    page.wait_for_selector('[data-testid="enter-blocked"]')
    assert aid in tid(page, "enter-blocked").inner_text()          # existing live entry, named
    assert page.locator("#cve-continue").is_disabled()
    ctx.close()


def test_enter_flow_open_mode_two_clicks_and_signed_out(live, browser):
    owner, ent = agent(live), agent(live)
    s = api(live, owner, "POST", "/api/slots/create",
            json={"label": "S7", "positions": [{"row": 0, "col": 0}], "roles": ["primary"]}).json()["slots"][0]
    ctx = signed_in(browser, ent)
    page = ctx.new_page()
    page.goto(live.url + "/kassa")
    page.evaluate("ref => window.CIVITAE_ENTRY.openEnter({ref, title: 'slot'})", f"slot:{s['id']}")
    page.wait_for_selector("#enter-modal")
    page.click("#cve-continue")
    assert page.locator('[data-k="mode"]').inner_text() == "Open"
    page.click("#cve-continue"); page.click("#cve-continue")
    page.click("#cve-confirm")
    page.wait_for_selector('[data-testid="enter-receipt"]')
    assert page.locator('[data-k="agreement-state"]').inner_text() == "accepted"      # click 1
    page.click("#cve-click2")
    page.wait_for_function("() => document.querySelector('[data-k=agreement-state]').textContent === 'active'")
    aid = page.locator('[data-k="agreement-id"]').inner_text()
    got = api(live, ent, "GET", f"/api/work-entry/{aid}").json()["agreement"]
    assert got["state"] == "active" and got["objects"]["slot_id"] == s["id"]
    assert tid(page, "mc-link").get_attribute("href") == f"/missions?mission={s['mission_id']}"
    ctx.close()
    # signed out: no credential, no entry; the one door is /entry
    s2 = api(live, owner, "POST", "/api/slots/create",
             json={"label": "S7b", "positions": [{"row": 0, "col": 0}], "roles": ["primary"]}).json()["slots"][0]
    anon = browser.new_context().new_page()
    anon.goto(live.url + "/kassa")
    anon.evaluate("ref => window.CIVITAE_ENTRY.openEnter({ref, title: 'slot'})", f"slot:{s2['id']}")
    anon.wait_for_selector('[data-testid="enter-blocked"]')
    assert anon.locator("#cve-continue").is_disabled()
    assert anon.locator('[data-testid="enter-blocked"] a').get_attribute("href") == "/entry"


# ═══ Poster side ═════════════════════════════════════════════════════════

def test_poster_signed_in_reject_needs_reason_accept_activate(live, browser):
    owner, ent = agent(live), agent(live)
    pid = make_post(live, owner)
    aid = file_entry(live, ent, f"post:{pid}")
    ctx = signed_in(browser, owner)
    page = ctx.new_page()
    page.goto(live.url + f"/kassa/post/{pid}")
    row = page.locator(f'[data-testid="entry-row"][data-agreement-id="{aid}"]')
    row.wait_for()
    assert row.get_attribute("data-state") == "pending"
    row.locator('[data-act="reject"]').click()
    assert "named reason" in tid(page, "entry-msg").inner_text()
    assert api(live, owner, "GET", f"/api/work-entry/{aid}").json()["agreement"]["state"] == "pending"
    row.locator('[data-act="accept"]').click()
    page.wait_for_selector(f'[data-agreement-id="{aid}"][data-state="accepted"]')
    got = api(live, owner, "GET", f"/api/work-entry/{aid}").json()
    assert got["agreement"]["state"] == "accepted" and got["agreement"]["objects"]["mission_id"]
    assert got["receipts"][-1]["credential_ref"] == f"{owner['id']}#api_key"
    page.locator(f'[data-agreement-id="{aid}"] [data-act="activate"]').click()
    page.wait_for_selector(f'[data-agreement-id="{aid}"][data-state="active"]')
    ctx.close()
    # the entrant sees only its own entry, with withdraw (not accept)
    ent_ctx = signed_in(browser, ent)
    ep = ent_ctx.new_page()
    other = file_entry(live, agent(live), f"post:{pid}")
    ep.goto(live.url + f"/kassa/post/{pid}")
    ep.wait_for_selector(f'[data-agreement-id="{aid}"]')
    assert ep.locator(f'[data-agreement-id="{other}"]').count() == 0
    assert ep.locator('[data-act="accept"]').count() == 0
    ent_ctx.close()


def test_poster_reject_and_retire_with_reasons(live, browser):
    owner = agent(live)
    pid = make_post(live, owner)
    e1, e2 = file_entry(live, agent(live), f"post:{pid}"), file_entry(live, agent(live), f"post:{pid}")
    ctx = signed_in(browser, owner)
    page = ctx.new_page()
    page.goto(live.url + f"/kassa/post/{pid}")
    r1 = page.locator(f'[data-agreement-id="{e1}"]')
    r1.wait_for()
    r1.locator('[data-testid="reason"]').fill("scope mismatch")
    r1.locator('[data-act="reject"]').click()
    page.wait_for_selector(f'[data-agreement-id="{e1}"][data-state="rejected"]')
    assert api(live, owner, "GET", f"/api/work-entry/{e1}").json()["agreement"]["outcome_reason"] == "scope mismatch"
    r2 = page.locator(f'[data-agreement-id="{e2}"]')
    r2.locator('[data-testid="reason"]').fill("no longer needed")
    r2.locator('[data-act="retire"]').click()
    page.wait_for_selector(f'[data-agreement-id="{e2}"][data-state="retired"]')
    assert api(live, owner, "GET", f"/api/work-entry/{e2}").json()["agreement"]["state"] == "retired"
    ctx.close()


def test_poster_magic_link_accepts_and_retires_from_the_thread(live, browser):
    ent1, ent2 = agent(live), agent(live)
    a1 = file_entry(live, ent1, f"post:{MAGIC_POST}")
    a2 = file_entry(live, ent2, f"post:{MAGIC_POST}")
    page = browser.new_context().new_page()          # no agent credential at all
    page.goto(live.url + f"/kassa/thread/{MAGIC_THREAD}?magic={MAGIC_TOKEN}")
    page.wait_for_selector('[data-testid="entry-panel"]')
    r1 = page.locator(f'[data-agreement-id="{a1}"]')
    r1.wait_for()
    r1.locator('[data-act="accept"]').click()
    page.wait_for_selector(f'[data-agreement-id="{a1}"][data-state="accepted"]')
    rc = httpx.get(live.url + f"/api/work-entry/{a1}",
                   headers={"X-Magic-Token": MAGIC_TOKEN, "X-Thread-Id": MAGIC_THREAD}).json()["receipts"][-1]
    assert rc["credential_ref"] == f"poster-link:{MAGIC_THREAD}#magic_link" and rc["transition"] == "accept"
    page.locator(f'[data-agreement-id="{a2}"] [data-testid="reason"]').fill("filled elsewhere")
    page.locator(f'[data-agreement-id="{a2}"] [data-act="retire"]').click()
    page.wait_for_selector(f'[data-agreement-id="{a2}"][data-state="retired"]')


def test_poster_panel_hidden_when_signed_out(live, browser):
    owner = agent(live)
    pid = make_post(live, owner)
    page = browser.new_context().new_page()
    page.goto(live.url + f"/kassa/post/{pid}")
    page.wait_for_selector("#enter-btn")
    page.wait_for_timeout(800)
    assert page.locator('[data-testid="entry-row"]').count() == 0


# ═══ Mission Control ═════════════════════════════════════════════════════

def test_mission_control_node_acceptance_record_and_progress(live, browser):
    w = active_world(live)
    ctx = signed_in(browser, w["ent"])
    page = ctx.new_page()
    page.goto(live.url + f"/missions?mission={w['mid']}")
    node = page.locator('[data-testid="agreement-node"]')
    node.wait_for()
    assert node.count() == 1
    assert node.get_attribute("data-agreement-id") == w["aid"] and node.get_attribute("data-state") == "active"
    assert tid(page, "node-label").inner_text() == "terms_accepted → active"
    assert page.locator('[data-testid="node-chain"] span.lit').count() == 2
    got = api(live, w["ent"], "GET", f"/api/work-entry/mission/{w['mid']}").json()
    ac = got["agreements"][0]["acceptance"]
    # Inspector tab: the Acceptance record, every value the server's
    assert page.locator('[data-k="agreement-id"]').first.inner_text() == w["aid"]
    assert page.locator('[data-k="accepted-by"]').inner_text() == w["owner"]["id"] == ac["accepted_by"]
    assert page.locator('[data-k="evidence-class"]').inner_text() == "solution_proof"
    import re
    want = re.sub(r"\.\d+", "", ac["terms_accepted_at"].replace("T", " ")).replace("+00:00", "Z")
    assert page.locator('[data-k="terms-accepted-at"]').inner_text() == want
    assert page.locator('[data-k="acceptance-receipt"]').inner_text() == ac["acceptance_receipt_id"]
    assert page.locator('[data-k="acceptance-seed"]').inner_text() == ac["acceptance_seed_doi"]
    # PROGRESS tab: the receipts, in order
    page.click('[data-tab="PROGRESS"]')
    steps = page.eval_on_selector_all('[data-testid="progress-list"] li', "els => els.map(e => e.dataset.transition)")
    assert steps == [r["transition"] for r in got["agreements"][0]["receipts"]] and steps[-1] == "activate"
    assert w["aid"] and "accept" in steps
    # a stranger sees no Agreement, with the reason
    stranger = signed_in(browser, agent(live)).new_page()
    stranger.goto(live.url + f"/missions?mission={w['mid']}")
    stranger.wait_for_selector('[data-testid="mc-agreement-note"]')
    assert "party to an Agreement" in tid(stranger, "mc-agreement-note").inner_text()
    ctx.close()


def test_mission_control_mission_page_and_agentdash_nodes(live, browser):
    w = active_world(live)
    ctx = signed_in(browser, w["owner"])
    page = ctx.new_page()
    page.goto(live.url + f"/mission?mission={w['mid']}")
    page.wait_for_selector('[data-testid="agreement-node"]')
    assert tid(page, "agreement-node").get_attribute("data-agreement-id") == w["aid"]
    dash = ctx.new_page()
    dash.goto(live.url + "/agentdash")
    dash.click('[data-tab="missions"]')
    dash.wait_for_selector(f'#mc-mine [data-agreement-id="{w["aid"]}"]')
    dash.locator(f'#mc-mine [data-agreement-id="{w["aid"]}"]').click()
    dash.wait_for_selector('#mc-agreement [data-testid="acceptance-record"]')
    assert dash.locator('#mc-agreement [data-testid="acceptance-record"]').count() == 1
    ctx.close()


# ═══ COMMAND / DEPLOY: ARM DEPLOY ════════════════════════════════════════

def test_arm_deploy_preflight_on_deploy_then_confirm_in_command(live, browser):
    w = active_world(live)
    ctx = signed_in(browser, w["owner"])
    page = ctx.new_page()
    page.goto(live.url + "/deploy")
    page.click("#cve-arm-open")
    page.wait_for_function("m => document.querySelector('#cve-mission').value === m", arg=w["mid"])
    page.click("#cve-arm")
    page.wait_for_selector('[data-testid="arm-available"]')
    pre = api(live, w["owner"], "GET", f"/api/work-entry/mission/{w['mid']}/deploy/preflight").json()
    assert pre["can_deploy"] is True
    assert page.locator('[data-testid="preflight"] li').count() == 5
    assert page.locator("#cve-deploy").count() == 0               # the deploy page only arms; no commit here
    href = page.locator("#cve-to-command").get_attribute("href")
    assert href == f"/command?mission={w['mid']}"
    cmd = ctx.new_page()
    cmd.goto(live.url + href)
    cmd.click("#cve-arm")
    cmd.wait_for_selector("#cve-deploy")
    assert api(live, w["owner"], "GET", f"/api/work-entry/mission/{w['mid']}").json()["deployments"] == []
    cmd.click("#cve-deploy")
    cmd.wait_for_selector('[data-testid="deploy-receipt"]')
    dep = api(live, w["owner"], "GET", f"/api/work-entry/mission/{w['mid']}").json()["deployments"]
    assert len(dep) == 1 and dep[0]["receipt_id"] == cmd.locator('[data-k="deploy-receipt-id"]').inner_text()
    ctx.close()


def test_arm_deploy_blocked_without_authority_or_agreement(live, browser):
    w = active_world(live)
    # the entrant holds an active Agreement but not the owner's deploy authority
    ctx = signed_in(browser, w["ent"])
    page = ctx.new_page()
    page.goto(live.url + f"/command?mission={w['mid']}")
    page.click("#cve-arm")
    page.wait_for_selector('[data-testid="arm-blocked"]')
    assert tid(page, "arm-blocked").get_attribute("data-blocking") == "no_deploy_authority"
    assert page.locator("#cve-deploy").count() == 0
    # a mission with no Agreement at all
    owner2 = agent(live)
    s = api(live, owner2, "POST", "/api/slots/create",
            json={"positions": [{"row": 0, "col": 0}], "roles": ["primary"]}).json()["slots"][0]
    ctx2 = signed_in(browser, owner2)
    p2 = ctx2.new_page()
    p2.goto(live.url + f"/command?mission={s['mission_id']}")
    p2.click("#cve-arm")
    p2.wait_for_selector('[data-testid="arm-blocked"]')
    assert tid(p2, "arm-blocked").get_attribute("data-blocking") == "no_active_agreement"
    # signed out: the preflight is refused, not drawn
    anon = browser.new_context().new_page()
    anon.goto(live.url + f"/command?mission={w['mid']}")
    anon.click("#cve-arm")
    anon.wait_for_selector('[data-testid="arm-error"]')
    ctx.close(); ctx2.close()


# ═══ Shell Inspector ═════════════════════════════════════════════════════

def _insp(page):
    return page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#insp-fields .kv')]
        .map(r => [r.querySelector('b').textContent, r.querySelector('span').textContent]))""")


def _wait_insp(page, key, want):
    page.wait_for_function(
        "([k, v]) => [...document.querySelectorAll('#insp-fields .kv')].some(r => "
        "r.querySelector('b').textContent === k && r.querySelector('span').textContent === v)",
        arg=[key, want], timeout=15000)


def test_shell_inspector_shows_real_agreement_values(live, browser):
    w = active_world(live)
    ctx = signed_in(browser, w["ent"])
    rec = api(live, w["ent"], "GET", f"/api/work-entry/{w['aid']}").json()
    last_seed = rec["receipts"][-1]["seed_doi"]
    # mission page -> server lookup by mission_id
    page = ctx.new_page()
    page.goto(live.url + f"/shell?route=/missions?mission={w['mid']}")
    _wait_insp(page, "agreement_id", w["aid"])
    _wait_insp(page, "seed evidence", last_seed)
    ins = _insp(page)
    assert ins["workentry"] == "WorkEntryAgreement \u00b7 standard \u00b7 active"
    assert ins["mission_id"] == w["mid"]
    assert "PHASE-4" not in page.inner_text("#inspector")
    # explicit ?agreement= object id on a hosted page (no mission, no post)
    page = ctx.new_page()
    page.goto(live.url + f"/shell?route=/missions?agreement={w['aid']}")
    _wait_insp(page, "agreement_id", w["aid"])
    _wait_insp(page, "workentry", "WorkEntryAgreement \u00b7 standard \u00b7 active")
    assert _insp(page)["mission_id"] == "\u2014"
    # post page -> lookup by post_id (party-filtered by the caller's credential)
    page = ctx.new_page()
    page.goto(live.url + f"/shell?route=/kassa/post/{w['pid']}")
    _wait_insp(page, "opportunity/post", w["pid"])
    _wait_insp(page, "agreement_id", w["aid"])
    # nothing on record: honest, not a placeholder
    page = ctx.new_page()
    page.goto(live.url + "/shell?route=/portal")
    _wait_insp(page, "agreement_id", "none on record")
    assert _insp(page)["workentry"] == "none on record"
    ctx.close()


def test_shell_inspector_does_not_leak_a_foreign_agreement(live, browser):
    w = active_world(live)
    stranger = signed_in(browser, agent(live))
    page = stranger.new_page()
    page.goto(live.url + f"/shell?route=/missions?mission={w['mid']}")
    _wait_insp(page, "mission_id", w["mid"])
    page.wait_for_timeout(800)
    assert _insp(page)["agreement_id"] == "none on record"
    stranger.close()
