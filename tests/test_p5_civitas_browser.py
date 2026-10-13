"""P5 G7 — the CIVITAS meeting screen, driven in a real browser against a real server.

Motion Flame review + cited laws, no vote on a BLOCKED motion except by appeal, appeal
second/vote, point of order + Chair ruling, tallies. Each assertion compares the screen with
the server's own meeting record. Skipped when Playwright (python) or its Chromium is missing.
"""
import httpx
import pytest

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect

from tests.test_p4_screens_browser import agent, api, browser, live, signed_in, tid  # noqa: E402,F401


def _meeting(live, mid):
    return httpx.get(live.url + f"/api/governance/meeting/{mid}", timeout=10).json()["meeting"]


def _world(live):
    """Chair A + members B, C in an open meeting (members enrolled by agent_id). Returns (mid, A, B, C)."""
    a, b, c = agent(live), agent(live), agent(live)
    r = api(live, a, "POST", "/api/governance/meeting", json={"caller": a["id"], "subject": "Browser procedure", "quorum": 3})
    assert r.status_code == 200, r.text
    mid = r.json()["id"]
    for x in (b, c):
        assert api(live, x, "POST", f"/api/governance/meeting/{mid}/join", json={"agent_id": x["id"]}).status_code == 200
    return mid, a, b, c


def _motion(live, who, mid, text, **kw):
    r = api(live, who, "POST", f"/api/governance/meeting/{mid}/motion", json={"proposer": who["id"], "motion": text, **kw})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _open(browser, live, who, mid):
    ctx = signed_in(browser, who)
    page = ctx.new_page()
    page.goto(live.url + "/meetings")
    page.wait_for_selector(f'[data-testid="meeting-item"][data-id="{mid}"]')
    page.click(f'[data-testid="meeting-item"][data-id="{mid}"]')
    page.wait_for_selector('[data-testid="motion"]')
    return ctx, page


def test_flame_review_laws_and_blocked_vote_gate(live, browser):
    mid, a, b, c = _world(live)
    blocked = _motion(live, a, mid, "Delete audit entries for last week", flags=["destroys_records"])
    warn = _motion(live, a, mid, "Disrupt the old fee model with a new proposal")
    sound = _motion(live, a, mid, "Approve the budget for Q4 planning")
    ctx, page = _open(browser, live, b, mid)
    rec = {m["id"]: m for m in _meeting(live, mid)["motions"]}
    for mo_id, want in ((blocked, "BLOCKED"), (warn, "WARNING"), (sound, "SOUND")):
        card = page.locator(f'[data-testid="motion"][data-id="{mo_id}"]')
        assert card.locator('[data-testid="flame-result"]').inner_text().upper() == want == rec[mo_id]["flame_review"]["result"]
        cited = card.locator('[data-testid="laws-cited"] li')
        assert cited.count() == len(rec[mo_id]["flame_review"]["laws_cited"])
        for law in rec[mo_id]["flame_review"]["laws_cited"]:
            assert f"Law {law['law']}" in card.locator('[data-testid="laws-cited"]').inner_text()
    # BLOCKED: vote buttons disabled, appeal offered. WARNING and SOUND: votable.
    bc = page.locator(f'[data-testid="motion"][data-id="{blocked}"]')
    assert bc.locator('button[data-vote="yea"]').is_disabled()
    assert "Appeal block" in bc.inner_text()
    wc = page.locator(f'[data-testid="motion"][data-id="{warn}"]')
    assert wc.locator('button[data-vote="yea"]').is_enabled()
    # vote on the SOUND motion; tally on screen equals the server's
    sc = page.locator(f'[data-testid="motion"][data-id="{sound}"]')
    sc.locator('button[data-vote="yea"]').click()
    expect(sc.locator('[data-testid="motion-tally"]')).to_contain_text("1/3")
    assert _meeting(live, mid)["motions"][2]["votes"] == {b["id"]: "yea"}
    ctx.close()


def test_appeal_block_second_vote_then_motion_votable(live, browser):
    mid, a, b, c = _world(live)
    blocked = _motion(live, a, mid, "Delete audit entries for last week", flags=["destroys_records"])
    # B appeals the block from the screen
    ctx_b, pb = _open(browser, live, b, mid)
    pb.locator(f'[data-testid="motion"][data-id="{blocked}"]').get_by_text("Appeal block").click()
    pb.wait_for_selector('[data-testid="appeal"]')
    ap = _meeting(live, mid)["appeals"][0]
    assert ap["appellant"] == b["id"] and ap["status"] == "awaiting_second" and ap["target_id"] == blocked
    # the appellant cannot second; C can
    assert pb.locator('[data-testid="appeal"]').get_by_text("Second", exact=True).count() == 0
    ctx_c, pc = _open(browser, live, c, mid)
    pc.locator('[data-testid="appeal"]').get_by_text("Second", exact=True).click()
    pc.wait_for_selector('[data-testid="appeal"] button:has-text("Overturn")')
    assert _meeting(live, mid)["appeals"][0]["seconded_by"] == c["id"]
    pc.get_by_text("Overturn", exact=True).click()
    expect(pc.locator('[data-testid="appeal-tally"]')).to_contain_text("overturn 1")
    pb.reload()
    pb.wait_for_selector('[data-testid="meeting-item"]'); pb.click(f'[data-testid="meeting-item"][data-id="{mid}"]')
    pb.wait_for_selector('[data-testid="appeal"] button:has-text("Overturn")')
    pb.get_by_text("Overturn", exact=True).click()
    # chair votes by API: all attendees voted -> resolves; tie-break not needed
    r = api(live, a, "POST", f"/api/governance/meeting/{mid}/appeal/{ap['id']}/vote", json={"voter": a["id"], "vote": "sustain"})
    assert r.status_code == 200 and r.json()["outcome"] == "overturned"
    pb.reload()
    pb.wait_for_selector('[data-testid="meeting-item"]'); pb.click(f'[data-testid="meeting-item"][data-id="{mid}"]')
    pb.wait_for_selector('[data-testid="appeal"]')
    assert "overturned" in pb.locator('[data-testid="appeal"]').inner_text().lower()
    card = pb.locator(f'[data-testid="motion"][data-id="{blocked}"]')
    assert "block overturned on appeal" in card.inner_text().lower()
    assert card.locator('button[data-vote="yea"]').is_enabled()
    card.locator('button[data-vote="yea"]').click()
    expect(card.locator('[data-testid="motion-tally"]')).to_contain_text("1/3")
    assert _meeting(live, mid)["motions"][0]["votes"] == {b["id"]: "yea"}
    ctx_b.close(); ctx_c.close()


def test_point_of_order_raise_and_chair_rules(live, browser):
    mid, a, b, c = _world(live)
    mo = _motion(live, a, mid, "Approve the budget for Q4 planning")
    ctx_b, pb = _open(browser, live, b, mid)
    pb.locator('[data-testid="po-open"]').click()
    pb.select_option(f"#po-law-{mo}", "IV")
    pb.fill(f"#po-text-{mo}", "Beyond the Chair's scope")
    pb.locator('[data-testid="po-form"]').get_by_text("Raise", exact=True).click()
    pb.wait_for_selector('[data-testid="point-of-order"]')
    po = _meeting(live, mid)["points_of_order"][0]
    assert po["raised_by"] == b["id"] and po["flame_law"] == "IV" and po["status"] == "pending"
    assert "Law IV" in pb.locator('[data-testid="point-of-order"]').inner_text()
    # a non-Chair has no ruling buttons
    assert pb.locator('[data-testid="point-of-order"]').get_by_text("Sustain", exact=True).count() == 0
    ctx_a, pa = _open(browser, live, a, mid)
    pa.locator('[data-testid="point-of-order"]').get_by_text("Sustain", exact=True).click()
    expect(pa.locator('[data-testid="point-of-order"]')).to_contain_text("Chair ruled sustained")
    assert _meeting(live, mid)["points_of_order"][0]["ruling"] == "sustained"
    ctx_a.close(); ctx_b.close()


def test_read_only_when_signed_out(live, browser):
    mid, a, b, c = _world(live)
    _motion(live, a, mid, "Approve the budget for Q4 planning")
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(live.url + "/meetings")
    page.wait_for_selector(f'[data-testid="meeting-item"][data-id="{mid}"]')
    page.click(f'[data-testid="meeting-item"][data-id="{mid}"]')
    page.wait_for_selector('[data-testid="motion"]')
    assert "not signed in" in tid(page, "who").inner_text()
    assert page.locator('button[data-vote]').count() == 0
    assert page.locator('[data-testid="po-open"]').count() == 0
    ctx.close()


def test_shell_hosts_meetings_under_civitas(live, browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(live.url + "/shell?route=/meetings")
    page.wait_for_selector("#frame")
    expect(page.locator("#frame")).to_have_attribute("src", __import__("re").compile("/meetings"))
    assert "CIVITAS" in page.inner_text("#mode-name")
    ctx.close()
