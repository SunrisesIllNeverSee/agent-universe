"""P5k -- operator payout-approvals screen (/admin/payouts).

Route-exists + static checks (key never in a URL, no key persistence) and a browser test.
The browser test drives the real page against a real server: the admin gate and wallet-flags
call are real; the approvals list and the approve POST are stubbed at the network layer so no
money path runs. Browser part is skipped when Playwright/Chromium is missing.
"""
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "frontend" / "admin-payouts.html"


def test_route_exists(client):
    import shutil

    from app.deps import state
    shutil.copy2(PAGE, state.frontend_dir / PAGE.name)  # conftest's temp root only carries shell.html
    r = client.get("/admin/payouts")
    assert r.status_code == 200
    assert "Payout Approvals" in r.text
    assert "/api/operator/payout-approvals" in r.text and "/api/operator/wallet-flags" in r.text


def test_page_key_handling_matches_admin_page():
    src = PAGE.read_text()
    assert "X-Admin-Key" in src
    assert "localStorage" not in src and "sessionStorage" not in src
    assert not re.search(r"[?&](admin_?key|key)=", src)
    assert "type=\"password\"" in src
    assert "confirm-bar" in src  # approve/reject go through a confirm step


def test_api_still_admin_gated(client):
    assert client.get("/api/operator/payout-approvals").status_code == 403
    assert client.get("/api/operator/wallet-flags").status_code == 403


# ── browser ──────────────────────────────────────────────────────────────

try:
    import playwright.sync_api  # noqa: F401
    from tests.test_p4_screens_browser import browser, live  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False

APPROVAL = {"approval_id": "apr-ui-1", "agent_id": "agent-ui", "wallet_id": "w1", "chain": "base",
            "address": "0xabc0000000000000000000000000000000000001", "amount": 12.5, "status": "pending",
            "reserve_txn": "t1", "created_at": "2026-10-14T00:00:00+00:00", "decided_at": None,
            "decided_by": "", "transfer": "", "shared_address_agents": []}


@pytest.mark.skipif(not HAVE_PW, reason="playwright (python) not installed")
def test_screen_lists_and_confirms_before_approve(live, browser):
    page = browser.new_page()
    calls = []

    def approvals(route):
        req = route.request
        if req.method == "POST":
            calls.append((req.url, req.headers.get("x-admin-key")))
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"approval": {**APPROVAL, "status": "approved"}}))
        else:
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"approvals": [APPROVAL], "wallet_flags": []}))

    page.route("**/api/operator/payout-approvals**", approvals)
    page.goto(live.url + "/admin/payouts")
    page.fill('[data-testid="admin-key"]', live.admin)
    page.click('[data-testid="admin-enter"]')
    card = page.locator('[data-testid="approval"][data-id="apr-ui-1"]')
    card.wait_for()
    assert card.locator('[data-testid="approval-amount"]').inner_text() == "12.5"
    assert card.locator('[data-testid="approval-agent"]').inner_text() == "agent-ui"
    assert APPROVAL["address"] in card.locator('[data-testid="approval-destination"]').inner_text()
    assert card.locator('[data-testid="approval-state"]').inner_text().lower() == "pending"
    page.locator('[data-testid="flags-empty"]').wait_for()
    assert live.admin not in page.url
    # confirm step: first click sends nothing; cancel sends nothing
    card.locator('[data-testid="approve"]').click()
    card.locator('[data-testid="confirm-bar"]').wait_for()
    assert calls == []
    card.locator('[data-testid="confirm-cancel"]').click()
    assert calls == []
    card.locator('[data-testid="approve"]').click()
    card.locator('[data-testid="confirm-approve"]').click()
    card.locator('[data-testid="result-note"]').wait_for()
    assert len(calls) == 1
    assert calls[0][0].endswith("/api/operator/payout-approvals/apr-ui-1/approve")
    assert calls[0][1] == live.admin
    assert "Approved" in card.locator('[data-testid="result-note"]').inner_text()
    page.close()
