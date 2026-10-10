"""Independent T0 falsifier probe — extends coverage beyond reviews/t0_redgreen_probe.py.
Usage: .venv/bin/python reviews/t0_independent_rerun.py <repo_root>
Exit 0 = all fail-closed; exit 1 = at least one leak."""
import json, os, sys, tempfile
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(repo))
os.environ.setdefault("CIVITAE_ADMIN_KEY", "probe-admin-key")
os.environ.setdefault("CIVITAE_DEV_MODE", "1")
sys.argv = [sys.argv[0]]

root = Path(tempfile.mkdtemp(prefix="t0ind-"))
for d in ("config", "frontend", "vault", "data"):
    (root / d).mkdir(parents=True, exist_ok=True)
(root / "config" / "systems.json").write_text(json.dumps({"systems": [
    {"id": "claude", "name": "Claude", "provider": "x", "codename": "c", "class": "z", "online": True},
    {"id": "gpt", "name": "GPT", "provider": "x", "codename": "g", "class": "z", "online": True}]}))
for n, c in {"agents.json": '{"agents":[]}', "vault.json": '{"vault":{}}',
             "pages.json": '{"tileZero":{"slot":"0","name":"x","route":"/","status":"live"},"layers":[]}',
             "formations.json": '{"formations":[]}',
             "provision.json": '{"require_governance":false,"max_agents":100,"approval_mode":"auto","rate_limit":10}'}.items():
    (root / "config" / n).write_text(c)

from starlette.testclient import TestClient
import importlib
app = importlib.import_module("app.server").create_app(root)
c = TestClient(app, raise_server_exceptions=False)
fails, notes = [], []

def closed(r, label):
    if r.status_code < 400:
        fails.append(f"{label} -> {r.status_code} (expected 4xx)")

# --- Coverage extension: every guarded read the original probe missed ---
for p in ("/api/agent/inbox", "/api/inbox/app-deadbeef", "/api/operator/threads",
          "/api/operator/stats", "/api/operator/audit", "/api/operator/contacts",
          "/api/operator/reviews", "/api/provision/registry", "/api/kassa/messages?tab=iso"):
    closed(c.get(p), f"anon GET {p}")
    closed(c.get(p, headers={"X-Admin-Key": "wrong"}), f"forged-admin GET {p}")
closed(c.get("/api/agent/inbox", headers={"Authorization": "Bearer cmd_ak_forged"}),
       "forged-bearer GET /api/agent/inbox")

# --- NEW PROBE 1: advisory seat applicant PII via public GET /api/advisory/seats ---
r = c.post("/api/advisory/apply", json={
    "seat_id": "seat-01", "name": "Falsifier Human",
    "email": "pii-canary@falsifier.example", "type": "BI",
    "message": "secret applicant msg canary"})
print("advisory apply ->", r.status_code)
r = c.get("/api/advisory/seats")
body = r.text
if "pii-canary@falsifier.example" in body or "Falsifier Human" in body or "secret applicant msg canary" in body:
    fails.append(f"LEAK: anon GET /api/advisory/seats returns applicant PII -> {r.status_code} body[:400]={body[:400]!r}")
else:
    print("advisory seats clean")

# --- NEW PROBE 2: inbox apply -> anon reads + error-body PII check ---
r = c.post("/api/inbox/apply", json={"name": "Inbox Canary", "role": "x",
           "message": "inbox-pii-canary", "email": "inbox-canary@x.example"})
app_id = (r.json() or {}).get("application_id", "app-none")
for p in ("/api/inbox", f"/api/inbox/{app_id}"):
    rr = c.get(p)
    closed(rr, f"anon GET {p} after apply")
    if "inbox-pii-canary" in rr.text or "Inbox Canary" in rr.text:
        fails.append(f"LEAK: {p} returns applicant PII")

# --- NEW PROBE 3: public surfaces must not carry operator_contact/user PII ---
r = c.post("/api/provision/signup", json={"name": "CanaryAgent",
           "operator_contact": "op-canary@private.example"})
aid = (r.json() or {}).get("agent_id", "agent-none")
for p in ("/api/agents", f"/api/agents/CanaryAgent", f"/api/provision/status/{aid}"):
    rr = c.get(p)
    if rr.status_code == 200:
        if "op-canary@private.example" in rr.text:
            fails.append(f"LEAK: {p} exposes operator_contact")
        if p.startswith("/api/provision/status") and "email" in rr.text.lower():
            notes.append(f"INFO: {p} mentions 'email' key — inspect")
    else:
        notes.append(f"{p} -> {rr.status_code}")

# --- NEW PROBE 4: magic-link endpoint, wrong token, check reflection/no PII ---
rr = c.get("/api/kassa/threads/thr-nonexistent?magic=WRONGTOKEN123")
if rr.status_code < 400 or "WRONGTOKEN123" in rr.text:
    fails.append(f"magic-link probe -> {rr.status_code} reflects token or leaks: {rr.text[:200]!r}")

# --- NEW PROBE 5: unauthenticated write that has no route-level guard ---
rr = c.post("/api/provision/key", json={"agent_id": aid})
closed(rr, "anon POST /api/provision/key (middleware-only guard)")
rr = c.post(f"/api/inbox/{app_id}/review", json={"status": "approved"})
closed(rr, "anon POST /api/inbox/{id}/review (middleware-only guard)")

# --- NEW PROBE 6: public /api/audit must not carry applicant email ---
rr = c.get("/api/audit")
if "pii-canary@falsifier.example" in rr.text:
    fails.append("LEAK: /api/audit carries applicant email")
elif "Falsifier Human" in rr.text:
    notes.append("INFO: /api/audit carries advisory applicant NAME (advisory.py)")

for n in notes: print(" ", n)
if fails:
    print("RED — invariant violated:")
    for f in fails: print("  -", f)
    sys.exit(1)
print("GREEN — all probed reads fail closed")
