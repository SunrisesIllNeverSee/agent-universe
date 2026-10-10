"""T0 RED/GREEN probe — invariant: unauthenticated GET /api/inbox fails closed.
Usage: PYTHONPATH=<repo> python3 t0_redgreen_probe.py <repo_root>
Exit 0 = guard holds; exit 1 = invariant violated (RED)."""
import json, os, sys, tempfile
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(repo))
os.environ.setdefault("CIVITAE_ADMIN_KEY", "probe-admin-key")
os.environ.setdefault("CIVITAE_DEV_MODE", "1")
sys.argv = [sys.argv[0]]

root = Path(tempfile.mkdtemp(prefix="t0probe-"))
for d in ("config", "frontend", "vault", "data"):
    (root / d).mkdir(parents=True, exist_ok=True)
(root / "config" / "systems.json").write_text(json.dumps({
    "systems": [
        {"id": "claude", "name": "Claude", "provider": "x", "codename": "c", "class": "z", "online": True},
        {"id": "gpt", "name": "GPT", "provider": "x", "codename": "g", "class": "z", "online": True},
    ]}))
for n, c in {"agents.json": '{"agents":[]}', "vault.json": '{"vault":{}}',
             "pages.json": '{"tileZero":{"slot":"0","name":"x","route":"/","status":"live"},"layers":[]}',
             "formations.json": '{"formations":[]}',
             "provision.json": '{"require_governance":false,"max_agents":100,"approval_mode":"auto","rate_limit":10}'}.items():
    (root / "config" / n).write_text(c)

from starlette.testclient import TestClient
import importlib
srv = importlib.import_module("app.server")
app = srv.create_app(root)
client = TestClient(app, raise_server_exceptions=False)
fails = []

def expect_closed(r, label):
    if r.status_code < 400:
        fails.append(f"{label} -> {r.status_code} (expected 4xx fail-closed)")
        body = r.text.lower()
        if any(k in body for k in ("email", "name", "applicant", "message")):
            fails.append(f"{label} leaked PII/contact content in 200 body")

expect_closed(client.get("/api/inbox"), "anonymous GET /api/inbox")
expect_closed(client.get("/api/inbox", headers={"X-Admin-Key": "wrong-key"}),
              "forged-admin GET /api/inbox")
expect_closed(client.get("/api/kassa/messages"), "anonymous GET /api/kassa/messages")

if fails:
    print("RED — invariant violated:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("GREEN — inbox/contact read guards fail closed (3/3 checks)")
sys.exit(0)
