"""Canary leak sweep (2026-10-16, owner-approved).

Root-cause class behind the /api/state PII hotfix (a12d5d4): public endpoints returned raw
internal records, so private fields added later leaked automatically. This test plants
unmistakable fake secrets in every store that holds private data, then calls EVERY GET route
the app exposes (enumerated from ``app.routes``, never hand-listed) anonymously and as an
unrelated authenticated agent, captures the public live feeds (/ws, /ws/public initial frame
and every broadcast while planting) and the read-only MCP tools, and asserts that no canary
value appears in any response body.

Owners: a secret owned by agent B may be shown to B (own data, principal-bound); nothing
else may appear to B, and nothing at all may appear to an anonymous caller.

New routes and new MCP read tools are covered automatically. Routes that cannot be called
generically are listed in ``SKIP_ROUTES`` with the reason.

Product decisions recorded here:
- ``{handle}@signomy.xyz`` agent mailboxes are public identity labels (not secrets).
- Linked wallet addresses are PRIVATE: the product only shows them to the owning agent
  (GET /api/economy/wallets, JWT-bound) and the operator (payout approvals, admin key).
- Stripe account / checkout-session ids are PRIVATE (owner/operator only).
- Per-agent money is PRIVATE (ledger privacy, 2026-10-16): balances, ledger rows, fee-credit
  balances, trial liability, commission buyer ids and amounts, recruitment rewards. Only the
  agent itself and the operator may read them; aggregate treasury totals stay public.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from starlette.testclient import TestClient

TAG = "7f3a"
REPO = Path(__file__).resolve().parents[1]


def S(field: str) -> str:
    return f"CANARY-SECRET-{field}-{TAG}"


def E(field: str) -> str:
    return f"canary-{field}-{TAG}@example.invalid"


IP_A, IP_B = "203.0.113.77", "203.0.113.78"
EVM_A = "0x" + "7f3acafe" * 5          # valid 0x + 40 hex: linked-wallet address of agent A
ACCT_A = f"acct_CANARY{TAG}stripeacctA"
SESSION_A = f"cs_CANARY{TAG}checkoutsessionA"

# Routes intentionally not called generically (path -> reason). Keep this short.
SKIP_ROUTES = {
    # FastAPI's /api/* JSON 404 fallback; it never reads stores.
    "/api/{unmatched_path:path}": "catch-all 404 handler, no data access",
}

# Canary labels a route may still show while an owner decision is pending (route -> labels).
# Each entry is a STOP recorded in the ledger-privacy report; remove it when the owner rules.
OWNER_STOP_ALLOW = {
    # tests/test_routes_economy.py::test_balance_zero_for_new_agent asserts an anonymous 200.
    "/api/economy/balance/{agent_id}": {"treasury.balance"},
}

# Path-parameter names whose values we cannot derive get this probe value.
FALLBACK_PARAM = "canary-probe"


class _RecordingHub:
    """Stands in for a ConnectionHub: records every broadcast (the public live feed) and still
    fans out to real sockets so the initial-frame websocket checks work."""

    def __init__(self, inner):
        self.inner = inner
        self.frames: list[str] = []

    @property
    def connections(self):
        return self.inner.connections

    async def connect(self, websocket):
        await self.inner.connect(websocket)

    def disconnect(self, websocket):
        self.inner.disconnect(websocket)

    async def broadcast(self, event: dict) -> None:
        self.frames.append(json.dumps(event, default=str))
        await self.inner.broadcast(event)


def _ip() -> str:
    return f"198.51.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"


@pytest.fixture(scope="module")
def canary(app, tmp_root, tmp_path_factory):
    """Isolated app + data dir with canary secrets planted through the app's own APIs/stores.
    The shared session state is restored afterwards so no other test sees the canaries."""
    import os

    from app import seeds as seeds_mod
    from app import seeds_otel as seeds_otel_mod
    from app.deps import state
    from app.routes import economy as economy_routes
    from app.server import create_app

    saved_state = dict(state.__dict__)
    saved_seeds_file = seeds_mod.SEEDS_FILE
    saved_otel_root = seeds_otel_mod._PROJECT_ROOT
    saved_chain_router = getattr(economy_routes._get_chain_router, "_instance", None)
    saved_admin_env = os.environ.get("CIVITAE_ADMIN_KEY")

    root = tmp_path_factory.mktemp("canary_root")
    shutil.copytree(tmp_root / "config", root / "config")
    (root / "frontend").symlink_to(REPO / "frontend", target_is_directory=True)
    (root / "vault").mkdir()
    (root / "data").mkdir()
    seeds_mod.SEEDS_FILE = str(root / "data" / "seeds.jsonl")
    seeds_otel_mod._PROJECT_ROOT = root   # /api/traces/dataset writes its export under <root>/data
    admin_key = S("admin_key")
    os.environ["CIVITAE_ADMIN_KEY"] = admin_key
    try:
        capp = create_app(root)
    finally:
        if saved_admin_env is None:
            os.environ.pop("CIVITAE_ADMIN_KEY", None)
        else:
            os.environ["CIVITAE_ADMIN_KEY"] = saved_admin_env
    economy_routes._get_chain_router._instance = None
    state.hub = _RecordingHub(state.hub)
    state.public_hub = _RecordingHub(state.public_hub)

    try:
        yield _plant(capp, state, admin_key)
    finally:
        state.__dict__.clear()
        state.__dict__.update(saved_state)
        seeds_mod.SEEDS_FILE = saved_seeds_file
        seeds_otel_mod._PROJECT_ROOT = saved_otel_root
        economy_routes._get_chain_router._instance = saved_chain_router


def _plant(capp, state, admin_key: str) -> dict:
    anon = TestClient(capp, raise_server_exceptions=False)
    admin = TestClient(capp, raise_server_exceptions=False, headers={"X-Admin-Key": admin_key})
    secrets: dict[str, tuple[str, str]] = {}   # value -> (owner, label)

    def secret(owner: str, label: str, value: str) -> str:
        secrets[value] = (owner, label)
        return value

    # ── agents A (victim) and B (unrelated caller) via the real signup + login ──
    def signup(name: str, ip: str, contact: str) -> dict:
        r = anon.post("/api/provision/signup",
                      json={"name": name, "handle": name, "system": "claude", "operator_contact": contact},
                      headers={"x-forwarded-for": ip})
        assert r.status_code == 200, r.text
        d = r.json()
        r = anon.post("/api/provision/login", json={"agent_id": d["agent_id"], "api_key": d["api_key"]},
                      headers={"x-forwarded-for": _ip()})
        assert r.status_code == 200, r.text
        d["token"] = r.json()["token"]
        return d

    a = signup(f"canary-a-{TAG}", IP_A, E("operator_contact_a"))
    b = signup(f"canary-b-{TAG}", IP_B, E("operator_contact_b"))
    for owner, d, ip in (("A", a, IP_A), ("B", b, IP_B)):
        secret(owner, "api_key", d["api_key"])
        secret(owner, "jwt", d["token"])
        secret(owner, "key_prefix", d["api_key"][:12])
        secret(owner, "key_hash", hashlib.sha256(d["api_key"].encode()).hexdigest())
        secret(owner, "signup_ip", ip)
        secret(owner, "operator_contact", E(f"operator_contact_{owner.lower()}"))
    # Private registry fields the signup does not set: simulate "a private field added later"
    # (rate_limit/last_login values are made unmistakable; the allowlist must drop them all).
    for owner, d in (("A", a), ("B", b)):
        entry = next(r for r in state.runtime.registry if r.get("agent_id") == d["agent_id"])
        entry["last_login"] = secret(owner, "last_login", S(f"last_login_{owner}"))
        entry["rate_limit"] = {"requests_per_minute": 10, "burst": 20,
                               "note": secret(owner, "rate_limit", S(f"rate_limit_{owner}"))}
        for f in ("password", "phone", "webhook_secret", "stripe_account_id", "private_notes"):
            entry[f] = secret(owner, f, S(f"{f}_{owner}"))
    # A legacy-shaped registry record whose `email` holds a real external address (the public
    # mailbox label must be the only email any public surface shows).
    state.runtime.registry.append({
        "agent_id": f"agent-legacy{TAG}", "name": f"canary-legacy-{TAG}", "handle": f"canary-legacy-{TAG}",
        "type": "agent", "status": "active", "provisioned": "2026-01-01T00:00:00+00:00",
        "email": secret("legacy", "registry.email(external)", E("legacy_email")),
        "key_hash": secret("legacy", "key_hash", hashlib.sha256(S("legacy_key").encode()).hexdigest()),
        "signup_ip": "203.0.113.79", "operator_contact": secret("legacy", "operator_contact", E("legacy_contact"))})
    secret("legacy", "signup_ip", "203.0.113.79")
    state.runtime.persist_registry()
    ha = {"Authorization": f"Bearer {a['api_key']}"}
    ja = {"Authorization": f"Bearer {a['token']}"}

    # ── KA§§A: operator-published post with poster PII, an agent post in review, contact form ──
    r = admin.post("/api/kassa/posts", json={
        "tab": "bounties", "title": "Canary bounty", "body": "canary body", "from_name": "Canary Poster",
        "from_email": secret("poster", "post.from_email", E("poster"))})
    assert r.status_code == 200, r.text
    live_post = r.json()["id"]
    r = anon.post("/api/kassa/posts", headers={**ha, "x-forwarded-for": _ip()}, json={
        "tab": "services", "title": "Canary review post", "body": "canary body two", "from_name": "Canary A",
        "from_email": secret("A", "post.from_email(review)", E("review_poster"))})
    assert r.status_code == 200, r.text
    review_post = r.json()["id"]
    r = anon.post("/api/kassa/contact", json={
        "post_id": live_post, "tab": "bounties", "from_name": secret("contact", "kassa_contact.name", S("kassa_contact_name")),
        "from_email": secret("contact", "kassa_contact.email", E("kassa_contact")),
        "message": secret("contact", "kassa_contact.message", S("kassa_contact_message"))})
    assert r.status_code == 200, r.text
    # Thread on the live post: A stakes (A sees its own thread). B never staked.
    r = anon.post(f"/api/kassa/posts/{live_post}/stake", headers=ja)
    assert r.status_code == 200, r.text
    thread = next(t for t in state.kassa.load_threads(agent_id=a["agent_id"]))
    secret("poster", "thread.magic_token(hash)", thread["magic_token"])

    # ── operator contact form, Open Roles applications, advisory seat applications ──
    r = anon.post("/api/contact", headers={"x-forwarded-for": _ip()}, json={
        "name": secret("contact", "contact.name", S("contact_name")),
        "email": secret("contact", "contact.email", E("contact")),
        "subject": "canary", "message": secret("contact", "contact.message", S("contact_message"))})
    assert r.status_code == 200, r.text
    r = anon.post("/api/inbox/apply", headers={"x-forwarded-for": _ip()}, json={
        "name": secret("applicant", "inbox.name", S("applicant_name")), "role": "builder",
        "handle": secret("applicant", "inbox.handle", S("applicant_handle")),
        "message": secret("applicant", "inbox.message", S("applicant_message"))})
    assert r.status_code == 200, r.text
    inbox_app = r.json()["application_id"]
    r = anon.post("/api/advisory/apply", json={
        "seat_id": "seat-07", "name": secret("advisory", "advisory.name", S("advisory_name")),
        "email": secret("advisory", "advisory.email", E("advisory")), "type": "BI",
        "message": secret("advisory", "advisory.message", S("advisory_message"))})
    assert r.status_code == 200, r.text
    advisory_app = r.json()["app_id"]
    r = anon.post("/api/advisory/apply", json={   # an AAI-typed application (sigrank lists AAI creators)
        "seat_id": "seat-08", "name": secret("advisory", "advisory.name(aai)", S("advisory_name_aai")),
        "email": secret("advisory", "advisory.email(aai)", E("advisory_aai")), "type": "AAI",
        "message": secret("advisory", "advisory.message(aai)", S("advisory_message_aai"))})
    assert r.status_code == 200, r.text

    # ── money: linked wallet (via API), Stripe binding, payout approval, escrow with session id ──
    secret("A", "wallet.address", EVM_A)
    r = anon.post("/api/economy/wallets", headers=ja, json={"chain": "base", "address": EVM_A, "label": "canary"})
    assert r.status_code == 201, r.text
    link = r.json()["wallet"]
    # A withdraws to the linked wallet twice: through a stubbed adapter (pending path) and a
    # "signed" adapter (completed path). Both are audited and broadcast; nothing is sent anywhere.
    from app.routes import economy as economy_routes

    class _Adapter:
        def __init__(self, note):
            self.note = note

        def transfer(self, chain, to, amount, agent_id="", confirm=False):
            return {"status": "SIGNED", "chain": chain, "note": self.note}

    state.economy.treasury.credit(a["agent_id"], 20.0, reason="test_seed_balance")
    for note in ("governed transaction stub", "canary adapter"):
        economy_routes._get_chain_router._instance = _Adapter(note)
        r = anon.post("/api/economy/withdraw", headers=ja,
                      json={"amount": 5, "chain": "base", "confirm": True, "wallet_id": link["wallet_id"]})
        assert r.status_code == 200 and r.json().get("chain_transfer"), r.text
    economy_routes._get_chain_router._instance = None
    state.wallets.note_stripe_binding(a["agent_id"], secret("A", "stripe.account_id", ACCT_A))
    state.wallets.create_approval(a["agent_id"], link, 1.0)
    esc = state.escrow.fund(poster_id=a["agent_id"], amount=5.0, source="stripe_checkout",
                            stripe_session_id=secret("A", "escrow.stripe_session_id", SESSION_A))

    # ── per-agent money (ledger privacy 2026-10-16): unmistakable amounts and ledger text ──
    aid = a["agent_id"]
    state.economy.treasury.credit(aid, 73113.37, reason=secret("A", "ledger.reason", S("ledger_reason")),
                                  mission_id=secret("A", "ledger.mission_id", S("ledger_mission")))
    secret("A", "ledger.credit_amount", "73113.37")
    state.economy.fee_credits.credit(aid, 6464.6464, pack_name=secret("A", "fee_credit.pack", S("fee_pack")))
    secret("A", "fee_credit.balance", "6464.6464")
    state.economy.trials.init_trial(aid)
    state.economy.trials.record_trial_mission(aid, 5151.5151)
    secret("A", "trial.liability", "5151.5151")
    r = admin.post("/api/kassa/commissions", json={
        "referrer_id": aid, "buyer_id": secret("A", "commission.buyer_id", S("commission_buyer")),
        "product_post_id": live_post, "purchase_amount": 8282.82, "commission_rate": 0.1})
    assert r.status_code == 200, r.text
    secret("A", "commission.purchase_amount", "8282.82")
    secret("A", "commission.amount", "828.282")
    r = admin.post("/api/kassa/recruitments", json={
        "recruiter_id": aid, "recruited_id": b["agent_id"], "base_economic": 3737.37})
    assert r.status_code == 200, r.text
    secret("A", "recruitment.reward_economic", "3737.37")
    balance = json.dumps(state.economy.treasury.balance(aid))
    assert len(balance) >= 8, balance          # unmistakable, never a small common number
    secret("A", "treasury.balance", balance)

    # ── platform secrets ──
    secret("platform", "admin_key", admin_key)
    if state.jwt_secret:
        secret("platform", "jwt_secret", state.jwt_secret)
    from app import kassa_payments
    if kassa_payments.STRIPE_WEBHOOK_SECRET:
        secret("platform", "stripe_webhook_secret", kassa_payments.STRIPE_WEBHOOK_SECRET)

    from app.seeds import _read_seeds
    seed_dois = [s["doi"] for s in _read_seeds()]
    params = {
        "agent_id": [a["agent_id"]], "recruiter_id": [a["agent_id"]],
        "handle": [a["name"], a["agent_id"], f"canary-legacy-{TAG}"],
        "post_id": [live_post, review_post], "thread_id": [thread["thread_id"]],
        "app_id": [inbox_app, advisory_app], "escrow_id": [esc["escrow_id"]],
        "doi": seed_dois, "session_id": [SESSION_A], "account_id": [ACCT_A], "seat_id": ["seat-07"],
        "ref": [f"kassa:{live_post}", live_post], "page": ["index"],
    }
    return {"app": capp, "state": state, "secrets": secrets, "a": a, "b": b, "params": params,
            "admin_key": admin_key}


def _hits(text: str, secrets: dict, allowed_owner: str | None, allowed_labels: frozenset = frozenset()) -> list[str]:
    return sorted({f"{label} ({owner})" for value, (owner, label) in secrets.items()
                   if owner != allowed_owner and label not in allowed_labels and value in text})


def _get_routes(capp):
    for r in capp.routes:
        if isinstance(r, APIRoute) and "GET" in r.methods:
            yield r


# Query parameters filled with agent A's identity / large limits on the second variant.
_QUERY_FILL = {
    "agent_id": "a", "poster_id": "a", "owner": "a", "entrant": "a", "handle": "a",
    "recruiter_id": "a", "referrer_id": "a", "recruited_id": "a", "reviewer_id": "a", "creator_id": "a",
    "limit": 200, "status": "all", "trust": "all",
    "anonymize": "false",   # a caller-controlled privacy toggle must not unlock private data
}


def _urls(route: APIRoute, params: dict, a: dict) -> list[str]:
    names = [p.name for p in route.dependant.path_params]
    combos = [route.path_format]
    for name in names:
        values = params.get(name) or [FALLBACK_PARAM]
        combos = [c.replace("{" + name + "}", str(v)) for c in combos for v in values]
    urls = list(combos)
    required = [qp for qp in route.dependant.query_params if qp.field_info.is_required()]
    if required:   # a required query param: every variant must carry it, or the route only 422s
        base = "&".join(f"{qp.name}={(params.get(qp.name) or [FALLBACK_PARAM])[0]}" for qp in required)
        urls = [f"{u}?{base}" for u in combos]
    q = []
    for qp in route.dependant.query_params:
        if qp.name in _QUERY_FILL and not qp.field_info.is_required():
            v = _QUERY_FILL[qp.name]
            q.append(f"{qp.name}={a['agent_id'] if v == 'a' else v}")
    if q:
        urls += [f"{u}{'&' if required else '?'}{'&'.join(q)}" for u in urls[:len(combos)]]
    return urls


def test_get_route_enumeration_is_automatic(canary):
    routes = [r.path for r in _get_routes(canary["app"])]
    # sanity: the sweep really sees the API surface (fails loudly if enumeration breaks)
    assert len(routes) > 150
    for must in ("/api/state", "/api/audit", "/api/seeds", "/api/agents", "/api/kassa/posts"):
        assert must in routes
    unknown_skips = set(SKIP_ROUTES) - set(routes)
    assert not unknown_skips, f"SKIP_ROUTES lists routes that no longer exist: {unknown_skips}"
    unknown_stops = set(OWNER_STOP_ALLOW) - set(routes)
    assert not unknown_stops, f"OWNER_STOP_ALLOW lists routes that no longer exist: {unknown_stops}"


def test_money_canaries_are_live_for_their_owner(canary):
    """The money canaries are not vacuous: the owner and the operator really read them."""
    capp, a = canary["app"], canary["a"]
    client = TestClient(capp, raise_server_exceptions=False)
    own = {"Authorization": f"Bearer {a['token']}"}
    admin = {"X-Admin-Key": canary["admin_key"]}
    aid = a["agent_id"]
    checks = {f"/api/economy/history/{aid}?limit=200": S("ledger_reason"),
              f"/api/fee-credits/balance/{aid}": "6464.6464",
              f"/api/economy/trial/{aid}": "5151.5151",
              f"/api/kassa/commissions?referrer_id={aid}": S("commission_buyer"),
              f"/api/kassa/recruitments/{aid}/stats": "3737.37"}
    for url, value in checks.items():
        for headers in (own, admin):
            r = client.get(url, headers={**headers, "x-forwarded-for": _ip()})
            assert r.status_code == 200 and value in r.text, (url, r.status_code, r.text[:200])
        assert client.get(url, headers={"x-forwarded-for": _ip()}).status_code == 401, url


def test_no_canary_in_any_get_route(canary):
    capp, secrets, a, b = canary["app"], canary["secrets"], canary["a"], canary["b"]
    callers = {
        "anonymous": ({}, None),
        "agent-B api_key": ({"Authorization": f"Bearer {b['api_key']}"}, "B"),
        "agent-B jwt": ({"Authorization": f"Bearer {b['token']}"}, "B"),
        # A staked on the poster's post: A may see its own data, never the poster's or contacts'.
        "agent-A jwt": ({"Authorization": f"Bearer {a['token']}"}, "A"),
        "agent-A api_key": ({"Authorization": f"Bearer {a['api_key']}"}, "A"),
    }
    client = TestClient(capp, raise_server_exceptions=False)
    findings, called = [], 0
    for route in _get_routes(capp):
        if route.path in SKIP_ROUTES:
            continue
        for url in _urls(route, canary["params"], a):
            for who, (headers, owner) in callers.items():
                r = client.get(url, headers={**headers, "x-forwarded-for": _ip()})
                called += 1
                hits = _hits(r.text, secrets, owner, frozenset(OWNER_STOP_ALLOW.get(route.path, ())))
                if hits:
                    findings.append(f"GET {url} [{who}] -> {r.status_code}: {', '.join(hits)}")
    assert called > 400
    assert not findings, "canary secrets leaked:\n" + "\n".join(findings)


def test_no_canary_in_public_live_feed(canary, monkeypatch):
    from app.routes import core
    monkeypatch.setattr(core, "_ws_connect_times", {})   # per-IP WS budget is shared across tests
    capp, secrets, state = canary["app"], canary["secrets"], canary["state"]
    frames = list(state.public_hub.frames) + list(state.hub.frames)
    client = TestClient(capp, raise_server_exceptions=False)
    for path in ("/ws/public", "/ws"):
        with client.websocket_connect(path) as ws:
            frames.append(json.dumps(ws.receive_json()))
    findings = [f"frame {f[:120]}...: {', '.join(_hits(f, secrets, None))}"
                for f in frames if _hits(f, secrets, None)]
    assert len(frames) >= 3
    assert not findings, "canary secrets on the unauthenticated live feed:\n" + "\n".join(findings)


def test_no_canary_in_readonly_mcp_tools(canary):
    secrets, state, a, b = canary["secrets"], canary["state"], canary["a"], canary["b"]
    mcp = state.mcp_bridge.build_fastmcp()
    tools = asyncio.run(mcp.list_tools())
    findings, called = [], 0
    for tool, handle in [(t, h) for t in tools for h in (a["name"], f"canary-legacy-{TAG}")]:
        fill = {"handle": handle, "agent_id": a["agent_id"], "name": f"canary-reader-{TAG}",
                "mission_id": FALLBACK_PARAM, "limit": 200}
        ann = tool.annotations
        if not (getattr(ann, "readOnly", None) or getattr(ann, "readOnlyHint", None)):
            continue   # never call mutating tools from a leak sweep
        props = (tool.inputSchema or {}).get("properties", {})
        for who, key, owner in (("anonymous", None, None), ("agent-B", b["api_key"], "B")):
            args = {k: v for k, v in fill.items() if k in props}
            if "api_key" in props:
                if key is None and "api_key" in (tool.inputSchema or {}).get("required", []):
                    continue
                if key is not None:
                    args["api_key"] = key
            try:
                res = asyncio.run(mcp.call_tool(tool.name, args))
                text = json.dumps(res, default=lambda o: getattr(o, "__dict__", str(o)))
            except Exception as exc:  # noqa: BLE001 - an error text is scanned too
                text = str(exc)
            called += 1
            hits = _hits(text, secrets, owner)
            if hits:
                findings.append(f"MCP {tool.name} [{who}]: {', '.join(hits)}")
    assert called >= 10
    assert not findings, "canary secrets leaked via MCP:\n" + "\n".join(findings)
