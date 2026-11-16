"""Bounded, metadata-only call records. Never serialize requests or tool arguments."""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import hashlib
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import sys
import time
import uuid

from starlette.requests import Request
from starlette.routing import Match

from .rate_limit import client_ip


@dataclass
class Call:
    sink: object
    request_id: str
    source_ip: str
    edge_request_id: str | None = None
    auth_kind: str = "anonymous"
    auth_result: str = "not_present"
    principal_id: str | None = None
    audit_event_ids: list[int] = field(default_factory=list)
    resource_ids: list[dict] = field(default_factory=list)
    auth_checks: list[dict] = field(default_factory=list)
    client_test_run_id: str | None = None
    client_test_suite: str | None = None
    ua_fingerprint: str | None = None


current_call: ContextVar[Call | None] = ContextVar("forensic_call", default=None)


def note_auth(kind: str, result: str, principal_id: str | None = None) -> None:
    call = current_call.get()
    if call is not None:
        if len(call.auth_checks) < 16:
            call.auth_checks.append({"kind": kind, "result": result, "principal_id": principal_id})
        if result == "accepted" or call.auth_result != "accepted":
            call.auth_kind, call.auth_result = kind, result
            call.principal_id = principal_id


def note_audit(entry: dict) -> None:
    call = current_call.get()
    if call is None:
        return
    if len(call.audit_event_ids) < 16:
        # AuditSpine exposes the ledger's zero-based IDs as one-based IDs.
        call.audit_event_ids.append(int(entry["id"]) + 1)
    detail = entry.get("detail", {})
    for key in ("agent_id", "mission_id", "post_id", "thread_id", "message_id", "slot_id", "meeting_id"):
        value = detail.get(key)
        if value is None or len(call.resource_ids) >= 16:
            continue
        text = str(value)
        # Only machine-shaped identifiers, never free-text names, tokens or hashes.
        if not (isinstance(value, int) or re.fullmatch(r"(?:agent|mission|post|thread|slot|meeting)-[0-9a-f]{8,32}", text)
                or re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", text)):
            continue
        item = {"kind": key.removesuffix("_id"), "id": value}
        if item not in call.resource_ids:
            call.resource_ids.append(item)


class _PrivateRotatingFile(RotatingFileHandler):
    def _open(self):
        fd = os.open(self.baseFilename, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        return os.fdopen(fd, "a", encoding="utf-8")


class CallSink:
    def __init__(self, data_dir: Path):
        self.logger = logging.Logger("civitae.forensics", logging.INFO)
        formatter = logging.Formatter("%(message)s")
        for handler in (logging.StreamHandler(sys.stdout), _PrivateRotatingFile(
                data_dir / "security_calls.jsonl", maxBytes=5 * 1024 * 1024, backupCount=4,
                encoding="utf-8", delay=True)):
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def __call__(self, event: dict) -> None:
        self.logger.info(json.dumps(event, separators=(",", ":"), sort_keys=True))


def emit(call: Call, *, transport: str, outcome: str, started: float, **fields) -> None:
    event = {
        "event": "security_call", "version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transport": transport, "request_id": call.request_id,
        "edge_request_id": call.edge_request_id, "source_ip": call.source_ip,
        "auth_kind": call.auth_kind, "auth_result": call.auth_result,
        "principal_id": call.principal_id, "outcome": outcome,
        "client_test_run_id": call.client_test_run_id,
        "client_test_suite": call.client_test_suite,
        "user_agent_fingerprint": call.ua_fingerprint,
        "auth_checks": list(call.auth_checks),
        "duration_ms": round((time.monotonic() - started) * 1000, 2),
        "audit_event_ids": list(call.audit_event_ids), "resource_ids": list(call.resource_ids),
        **fields,
    }
    try:
        call.sink(event)
    except Exception:
        # Telemetry failures must not alter authorization or application results.
        logging.getLogger("civitae.forensics.failure").error("security_call_write_failed")


class ForensicMiddleware:
    def __init__(self, app, *, router, sink):
        self.app, self.router, self.sink = app, router, sink

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] != "http" or not (path.startswith("/api/") or path == "/mcp" or path.startswith("/mcp/")):
            return await self.app(scope, receive, send)
        request = Request(scope)
        edge_id = request.headers.get("x-railway-request-id", "") if os.environ.get("RAILWAY_ENVIRONMENT") else ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", edge_id):
            edge_id = None
        run_id = request.headers.get("x-signomy-test-run", "")
        suite = request.headers.get("x-signomy-test-suite", "")
        # These labels are untrusted hints, never proof of the originating process.
        run_id = run_id if re.fullmatch(r"[A-Za-z0-9_-]{8,64}", run_id) else None
        suite = suite if re.fullmatch(r"[A-Za-z0-9_-]{4,64}", suite) else None
        ua = request.headers.get("user-agent", "")
        ua_fp = hashlib.sha256(ua.encode("utf-8")).hexdigest()[:16] if ua else None
        call = Call(self.sink, uuid.uuid4().hex, client_ip(request), edge_id,
                    client_test_run_id=run_id, client_test_suite=suite,
                    ua_fingerprint=ua_fp)
        if any(request.headers.get(h) for h in ("authorization", "x-admin-key", "x-api-key", "x-magic-token")):
            call.auth_kind, call.auth_result = "supplied", "not_evaluated"
        token = current_call.set(call)
        started, status = time.monotonic(), 500
        body, body_size = bytearray(), 0

        async def observe_receive():
            nonlocal body_size
            message = await receive()
            if path == "/mcp" and message["type"] == "http.request":
                chunk = message.get("body", b"")
                body_size += len(chunk)
                if body_size <= 65536:
                    body.extend(chunk)
                else:
                    body.clear()
            return message

        async def capture(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message = dict(message)
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-signomy-request-id", call.request_id.encode())]
            await send(message)

        try:
            await self.app(scope, observe_receive, capture)
        finally:
            route = "<unmatched>"
            for candidate in self.router.routes:
                if candidate.matches(scope)[0] == Match.FULL:
                    route = getattr(candidate, "path", "<mounted>") or "<mounted>"
                    break
            rpc_method = None
            if path == "/mcp" and scope["method"] == "POST":
                rpc_method = "<unavailable>"
                if body_size <= 65536:
                    try:
                        rpc = json.loads(body)
                        method = rpc.get("method") if isinstance(rpc, dict) else None
                        if isinstance(method, str) and method in {"initialize", "notifications/initialized", "ping", "tools/list", "tools/call",
                                      "resources/list", "resources/read", "resources/templates/list", "prompts/list", "prompts/get"}:
                            rpc_method = method
                    except (ValueError, UnicodeDecodeError, RecursionError):
                        pass
                body.clear()
            try:
                emit(call, transport="http", outcome="http_success" if status < 400 else "http_error",
                     started=started, method=scope["method"], route=route, status=status, rpc_method=rpc_method)
            finally:
                current_call.reset(token)


def audited_fastmcp(base):
    class AuditedFastMCP(base):
        async def call_tool(self, name, arguments):
            parent = current_call.get()
            if parent is None:
                return await super().call_tool(name, arguments)
            call = Call(parent.sink, parent.request_id, parent.source_ip, parent.edge_request_id,
                        parent.auth_kind, parent.auth_result, parent.principal_id,
                        client_test_run_id=parent.client_test_run_id,
                        client_test_suite=parent.client_test_suite,
                        ua_fingerprint=parent.ua_fingerprint)
            token = current_call.set(call)
            started, outcome = time.monotonic(), "exception"
            known = False
            try:
                known = self._tool_manager.get_tool(name) is not None
                result = await super().call_tool(name, arguments)
                # Typed FastMCP results carry structured output beside text content.
                structured = result[1] if isinstance(result, tuple) and len(result) == 2 else result
                # Generic dict-returning tools may instead carry JSON in a text block.
                # Inspect only in memory; no output text or arguments enter the record.
                if isinstance(structured, list) and len(structured) == 1:
                    text = getattr(structured[0], "text", None)
                    if isinstance(text, str) and len(text) <= 65536:
                        try:
                            structured = json.loads(text)
                        except (ValueError, UnicodeDecodeError, RecursionError):
                            pass
                outcome = "tool_error" if isinstance(structured, dict) and (
                    structured.get("error") or structured.get("isError") is True) else "completed"
                return result
            finally:
                emit(call, transport="mcp", outcome=outcome, started=started,
                     rpc_method="tools/call", tool=name if known else "<unknown>")
                current_call.reset(token)
    return AuditedFastMCP
