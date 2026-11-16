import asyncio
import hashlib
import json
import stat

import pytest
from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from app.auth import active_agent_from_bearer, admin_key_matches
from app.forensic_logging import (
    Call, CallSink, ForensicMiddleware, audited_fastmcp, current_call, note_audit, note_auth,
)


def test_rest_records_verified_identity_and_resource_without_secrets(tmp_path):
    app = FastAPI()
    key = "SENTINEL-BEARER-NEVER-LOG"
    record = {"agent_id": "agent-1234abcd", "status": "active", "key_hash": hashlib.sha256(key.encode()).hexdigest()}

    @app.post("/api/probe/{resource}")
    async def probe(resource: str, request: Request, payload: dict):
        assert active_agent_from_bearer(request, [record])["agent_id"] == record["agent_id"]
        # Optional, failed admin check must not erase an accepted agent principal.
        assert not admin_key_matches(request, "different")
        note_audit({"id": 40, "detail": {"agent_id": record["agent_id"], "key_hash": record["key_hash"], "text": payload}})
        return {"api_key": key}

    app.add_middleware(ForensicMiddleware, router=app.router, sink=CallSink(tmp_path))
    response = TestClient(app).post("/api/probe/PRIVATE-PATH?token=PRIVATE-QUERY", json={"text": "PRIVATE-BODY"},
        headers={"Authorization": "Bearer " + key, "X-Admin-Key": "PRIVATE-ADMIN"})
    assert response.status_code == 200
    text = (tmp_path / "security_calls.jsonl").read_text()
    event = json.loads(text)
    assert event["route"] == "/api/probe/{resource}"
    assert event["principal_id"] == record["agent_id"]
    assert event["auth_result"] == "accepted"
    assert event["audit_event_ids"] == [41]
    assert event["resource_ids"] == [{"kind": "agent", "id": record["agent_id"]}]
    assert event["request_id"] == response.headers["x-signomy-request-id"]
    for forbidden in [key, record["key_hash"], "PRIVATE-PATH", "PRIVATE-QUERY", "PRIVATE-BODY", "PRIVATE-ADMIN"]:
        assert forbidden not in text
    assert stat.S_IMODE((tmp_path / "security_calls.jsonl").stat().st_mode) == 0o600
    assert current_call.get() is None


def test_rpc_metadata_never_requires_body_or_argument_logging(tmp_path):
    app = FastAPI()

    @app.post("/mcp")
    async def rpc(request: Request):
        return await request.json()

    app.add_middleware(ForensicMiddleware, router=app.router, sink=CallSink(tmp_path))
    client = TestClient(app)
    for method, expected in [("tools/call", "tools/call"), ({"secret": "SENSITIVE"}, "<unavailable>")]:
        assert client.post("/mcp", json={"method": method, "params": {"api_key": "SENSITIVE"}}).status_code == 200
        event = json.loads((tmp_path / "security_calls.jsonl").read_text().splitlines()[-1])
        assert event["rpc_method"] == expected
    assert "SENSITIVE" not in (tmp_path / "security_calls.jsonl").read_text()


def test_large_rpc_body_passes_through_without_capture(tmp_path):
    app = FastAPI()

    @app.post("/mcp")
    async def rpc(request: Request):
        return {"length": len((await request.json())["params"]["text"])}

    app.add_middleware(ForensicMiddleware, router=app.router, sink=CallSink(tmp_path))
    response = TestClient(app).post("/mcp", json={"method": "tools/call", "params": {"text": "X" * 100000}})
    assert response.json() == {"length": 100000}
    assert json.loads((tmp_path / "security_calls.jsonl").read_text())["rpc_method"] == "<unavailable>"


def test_railway_ids_and_real_ip_use_existing_trust_boundary(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    app = FastAPI()

    @app.get("/api/probe")
    def probe():
        return {"ok": True}

    app.add_middleware(ForensicMiddleware, router=app.router, sink=CallSink(tmp_path))
    TestClient(app).get("/api/probe", headers={"X-Real-IP": "192.0.2.8", "X-Forwarded-For": "198.51.100.9", "X-Railway-Request-Id": "edge-123"})
    event = json.loads((tmp_path / "security_calls.jsonl").read_text())
    assert event["source_ip"] == "192.0.2.8"
    assert event["edge_request_id"] == "edge-123"


def test_mcp_call_error_and_claimed_name_are_not_authentication():
    from mcp.server.fastmcp import FastMCP
    events = []
    mcp = audited_fastmcp(FastMCP)("test")

    @mcp.tool()
    def read(name: str, message: str) -> dict:
        return {"error": "PRIVATE-ERROR", "echo": message}

    token = current_call.set(Call(events.append, "request-1", "192.0.2.1"))
    try:
        result = asyncio.run(mcp.call_tool("read", {"name": "audit-fixture", "message": "PRIVATE-MESSAGE"}))
        assert result is not None
        assert events[-1]["tool"] == "read"
        assert events[-1]["principal_id"] is None
        assert events[-1]["auth_result"] == "not_present"
        assert events[-1]["outcome"] == "tool_error"
        assert "PRIVATE" not in json.dumps(events)
        assert "audit-fixture" not in json.dumps(events)
        with pytest.raises(Exception):
            asyncio.run(mcp.call_tool("UNKNOWN-SECRET", {}))
        assert events[-1]["tool"] == "<unknown>"
        assert events[-1]["outcome"] == "exception"
    finally:
        current_call.reset(token)


def test_concurrent_mcp_principals_cannot_bleed_between_requests():
    from mcp.server.fastmcp import FastMCP
    events = []
    mcp = audited_fastmcp(FastMCP)("test")

    @mcp.tool()
    async def probe(index: int) -> dict:
        note_auth("agent_key", "accepted", f"agent-{index:08x}")
        await asyncio.sleep(0)
        note_audit({"id": index, "detail": {"agent_id": f"agent-{index:08x}"}})
        return {"ok": True}

    async def run(index):
        token = current_call.set(Call(events.append, f"request-{index}", "192.0.2.1"))
        try:
            await mcp.call_tool("probe", {"index": index})
        finally:
            current_call.reset(token)

    async def main():
        await asyncio.gather(*(run(i) for i in range(6)))

    asyncio.run(main())
    assert len(events) == 6
    for event in events:
        index = int(event["request_id"].split("-")[1])
        assert event["principal_id"] == f"agent-{index:08x}"
        assert event["audit_event_ids"] == [index + 1]


def test_failed_logging_does_not_change_response():
    app = FastAPI()

    @app.get("/api/probe")
    def probe():
        return {"ok": True}

    def broken_sink(_):
        raise OSError("unavailable")

    app.add_middleware(ForensicMiddleware, router=app.router, sink=broken_sink)
    assert TestClient(app).get("/api/probe").json() == {"ok": True}


def test_jwt_signature_is_not_confused_with_revocation_liveness():
    from app.auth import agent_token_alive
    from app.jwt_config import issue_agent_jwt, verify_jwt
    events = []
    call = Call(events.append, "jwt-test", "192.0.2.1")
    token = current_call.set(call)
    try:
        encoded = issue_agent_jwt("agent-1234abcd", "PRIVATE-NAME", epoch=2)
        claims = verify_jwt(encoded)
        assert call.auth_result == "signature_valid"
        assert not agent_token_alive({"agent_id": "agent-1234abcd", "status": "active", "token_epoch": 3}, claims)
        assert call.auth_result == "rejected"
        assert call.principal_id is None
        assert encoded not in json.dumps(call.auth_checks)
        assert "PRIVATE-NAME" not in json.dumps(call.auth_checks)
    finally:
        current_call.reset(token)


def test_real_http_mcp_registration_correlates_resource_and_transport(app, tmp_root, tmp_path, monkeypatch):
    import shutil
    from app.deps import state
    from app.server import create_app
    previous = dict(vars(state))
    root = tmp_path / "isolated-root"
    shutil.copytree(tmp_root, root)
    from app import seeds
    monkeypatch.setattr(seeds, "_PROJECT_ROOT", root)
    monkeypatch.setattr(seeds, "SEEDS_FILE", str(root / "data" / "seeds.jsonl"))
    monkeypatch.setenv("CIVITAE_FORENSIC_LOGGING", "1")
    try:
        logged_app = create_app(root)
        with TestClient(logged_app) as client:
            response = client.post("/mcp", headers={"Accept": "application/json, text/event-stream"}, json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
                    "name": "agent.register", "arguments": {"name": "PRIVATE-CLAIM", "handle": "private-claim"}}})
        assert response.status_code == 200
        text = (root / "data" / "security_calls.jsonl").read_text()
        events = [json.loads(line) for line in text.splitlines()]
        tool = next(e for e in events if e["transport"] == "mcp")
        http = next(e for e in events if e["transport"] == "http")
        assert tool["request_id"] == http["request_id"] == response.headers["x-signomy-request-id"]
        assert tool["tool"] == "agent.register"
        assert http["rpc_method"] == "tools/call"
        assert tool["outcome"] == "completed"
        assert tool["audit_event_ids"]
        assert any(r["kind"] == "agent" for r in tool["resource_ids"])
        assert "PRIVATE-CLAIM" not in text
        assert "cmd_ak_" not in text
    finally:
        vars(state).clear()
        vars(state).update(previous)


def test_real_server_records_guard_rejections(app, tmp_root, monkeypatch):
    from app.deps import state
    from app.server import create_app
    previous = dict(vars(state))
    monkeypatch.setenv("CIVITAE_FORENSIC_LOGGING", "1")
    try:
        logged_app = create_app(tmp_root)
        response = TestClient(logged_app).get("/api/provision/registry?secret=PRIVATE-QUERY",
            headers={"X-Admin-Key": "PRIVATE-KEY"})
        assert response.status_code == 403
        text = (tmp_root / "data" / "security_calls.jsonl").read_text()
        event = json.loads(text.splitlines()[-1])
        assert event["status"] == 403
        assert event["auth_result"] == "rejected"
        assert "PRIVATE" not in text
    finally:
        vars(state).clear()
        vars(state).update(previous)


def test_voluntary_run_marker_and_ua_hash_are_metadata_only(tmp_path):
    import hashlib
    app = FastAPI()
    @app.get("/api/health-probe")
    def probe():
        return {"ok": True}
    app.add_middleware(ForensicMiddleware, router=app.router, sink=CallSink(tmp_path))
    secret_ua = "PRIVATE-SENTINEL-UNTRUSTED-UA"
    response = TestClient(app).get("/api/health-probe",
        headers={"X-Signomy-Test-Run": "test-20261116-abcdef",
                 "X-Signomy-Test-Suite": "civitae-stress-v1", "User-Agent": secret_ua})
    assert response.status_code == 200
    content = (tmp_path / "security_calls.jsonl").read_text()
    event = json.loads(content)
    assert event["client_test_run_id"] == "test-20261116-abcdef"
    assert event["client_test_suite"] == "civitae-stress-v1"
    assert event["user_agent_fingerprint"] == hashlib.sha256(secret_ua.encode()).hexdigest()[:16]
    assert secret_ua not in content


def test_malicious_run_marker_is_not_recorded(tmp_path):
    app = FastAPI()
    @app.get("/api/probe")
    def probe(): return {"ok": True}
    app.add_middleware(ForensicMiddleware, router=app.router, sink=CallSink(tmp_path))
    TestClient(app).get("/api/probe",
        headers={"X-Signomy-Test-Run": "SECRET/with-private-content"})
    text = (tmp_path / "security_calls.jsonl").read_text()
    assert "SECRET" not in text
    assert json.loads(text)["client_test_run_id"] is None
