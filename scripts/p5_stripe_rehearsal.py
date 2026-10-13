#!/usr/bin/env python3
"""
P5 Stripe TEST-MODE rehearsal: post -> fund -> enter -> deliver -> accept -> release -> cashout.

Safety (this is a rehearsal, never a live run):
  * STRIPE_SECRET_KEY must start with sk_test_ or the script refuses before any call.
  * The target server must be local (localhost / 127.0.0.1 / ::1), started with the SAME
    sk_test_ key and STRIPE_WEBHOOK_SECRET, plus CIVITAE_ADMIN_KEY (sent as X-Admin-Key).

Funding is real Stripe test mode: a PaymentIntent is confirmed with pm_card_visa, then a
checkout.session.completed event for that amount is signed with STRIPE_WEBHOOK_SECRET and
delivered to /api/kassa/webhooks/stripe, so the server's signature path is what funds the
escrow. Cashout needs the entrant's connected account to have charges enabled; in test
mode that means completing the onboarding link once (the script prints it and stops).

    STRIPE_SECRET_KEY=sk_test_... STRIPE_WEBHOOK_SECRET=whsec_... CIVITAE_ADMIN_KEY=... \
        python scripts/p5_stripe_rehearsal.py [--base http://127.0.0.1:8300] [--amount 25]
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlparse

LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "[::1]")


def require_test_key(key: str | None) -> str:
    """Refuse anything that is not a Stripe test secret key."""
    if not key or not key.startswith("sk_test_"):
        raise SystemExit("refusing: STRIPE_SECRET_KEY must be set and start with sk_test_ (test mode only)")
    return key


def require_local(base: str) -> str:
    host = urlparse(base).hostname or ""
    if host not in LOCAL_HOSTS:
        raise SystemExit(f"refusing: {base} is not a local server (rehearsal never targets live)")
    return base.rstrip("/")


def sign_webhook(payload: bytes, secret: str, ts: int | None = None) -> str:
    ts = ts or int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


class Api:
    def __init__(self, base: str, admin: str):
        self.base, self.admin = base, admin

    def call(self, method: str, path: str, body: dict | None = None, *, bearer: str | None = None,
             admin: bool = False, raw: bytes | None = None, headers: dict | None = None) -> tuple[int, dict]:
        h = {"content-type": "application/json", **(headers or {})}
        if admin:
            h["X-Admin-Key"] = self.admin
        if bearer:
            h["Authorization"] = f"Bearer {bearer}"
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")


def step(n: str, ok: bool, detail: str = "") -> None:
    print(f"[{'ok' if ok else 'FAIL'}] {n} {detail}")
    if not ok:
        raise SystemExit(f"rehearsal stopped at: {n}")


def signup(api: Api, name: str) -> dict:
    s, d = api.call("POST", "/api/provision/signup", {"name": name, "system": "claude"})
    step(f"signup {name}", s == 200, str(s))
    s2, lg = api.call("POST", "/api/provision/login", {"agent_id": d["agent_id"], "api_key": d["api_key"]})
    step(f"login {name}", s2 == 200, str(s2))
    return {"id": d["agent_id"], "key": d["api_key"], "jwt": lg["token"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get("CIVITAE_URL", "http://127.0.0.1:8300"))
    ap.add_argument("--amount", type=float, default=25.0, help="escrow amount in USD")
    args = ap.parse_args()

    key = require_test_key(os.environ.get("STRIPE_SECRET_KEY"))
    base = require_local(args.base)
    admin = os.environ.get("CIVITAE_ADMIN_KEY", "")
    whsec = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not admin or not whsec:
        raise SystemExit("set CIVITAE_ADMIN_KEY and STRIPE_WEBHOOK_SECRET (the server's values)")
    import stripe
    stripe.api_key = key
    api = Api(base, admin)
    tag = uuid.uuid4().hex[:6]

    poster, entrant = signup(api, f"rehearsal-poster-{tag}"), signup(api, f"rehearsal-entrant-{tag}")

    # post
    s, d = api.call("POST", "/api/slots/create", {"label": f"rehearsal-{tag}", "positions": [{"row": 0, "col": 0}],
                                                   "roles": ["primary"]}, bearer=poster["key"])
    step("post work (mission + slot)", s == 200, str(s))
    slot = d["slots"][0]

    # fund: real test-mode PaymentIntent, then the signed webhook the server verifies
    cents = int(round(args.amount * 100))
    pi = stripe.PaymentIntent.create(amount=cents, currency="usd", payment_method="pm_card_visa", confirm=True,
                                     automatic_payment_methods={"enabled": True, "allow_redirects": "never"})
    step("stripe test PaymentIntent confirmed", pi.status == "succeeded", pi.status)
    event = {"id": f"evt_rehearsal_{tag}", "object": "event", "type": "checkout.session.completed",
             "data": {"object": {"id": f"cs_rehearsal_{pi.id}", "object": "checkout.session", "amount_total": cents,
                                 "payment_status": "paid", "payment_intent": pi.id,
                                 "metadata": {"type": "escrow_funding", "mission_id": slot["mission_id"],
                                              "poster_id": poster["id"]}}}}
    raw = json.dumps(event).encode()
    s, d = api.call("POST", "/api/kassa/webhooks/stripe", raw=raw, headers={"stripe-signature": sign_webhook(raw, whsec)})
    step("signed webhook funds escrow", s == 200 and d.get("escrow_id"), json.dumps(d)[:120])
    eid = d["escrow_id"]

    # enter
    s, d = api.call("POST", "/api/slots/fill", {"slot_id": slot["id"], "agent_id": entrant["id"]}, bearer=entrant["key"])
    step("entrant enters (Agreement active)", s == 200, str(s))
    aid = d["agreement_id"]
    s, esc = api.call("GET", f"/api/escrow/{eid}", admin=True)
    step("escrow held and linked", esc["state"] == "held", esc["state"])
    s, ag = api.call("GET", f"/api/work-entry/{aid}", admin=True)
    step("escrow_id on the Agreement", (ag.get("objects") or {}).get("escrow_id") == eid)

    # deliver (activity on the entry), accept (poster ends the mission -> release from escrow)
    s, _ = api.call("POST", f"/api/work-entry/{aid}/activity", {}, bearer=entrant["jwt"])
    step("entrant delivers (activity recorded)", s == 200, str(s))
    s, out = api.call("POST", f"/api/missions/{slot['mission_id']}/end", {}, bearer=poster["key"])
    step("poster accepts: mission end releases escrow", s == 200 and len(out["payouts"]) == 1
         and not out["payout_errors"] and not out["provenance_errors"], json.dumps(out.get("escrow")))
    net = out["payouts"][0]["fee_breakdown"]["net_to_agent"]
    print(f"      net to entrant after configured fee: {net}")

    # cashout (entrant's own connected account only)
    s, acct = api.call("POST", "/api/connect/accounts", {"display_name": "Rehearsal Entrant", "email": f"{tag}@example.test"},
                       bearer=entrant["jwt"])
    step("entrant links Stripe test account", s == 200, str(s))
    s, d = api.call("POST", "/api/connect/cashout", {"amount": net}, bearer=entrant["jwt"])
    if s == 400 and "onboarding" in json.dumps(d).lower():
        s2, link = api.call("POST", f"/api/connect/accounts/{acct['account_id']}/onboard", {}, admin=True)
        print("      cashout blocked: finish test-mode onboarding, then re-run the cashout:")
        print("      ", link.get("url") or link)
        return
    step("cashout to bound test account", s == 200, json.dumps(d)[:140])
    print("rehearsal complete")


if __name__ == "__main__":
    main()
