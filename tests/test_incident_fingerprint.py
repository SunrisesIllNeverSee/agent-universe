import json
from pathlib import Path

from scripts.incident_fingerprint import analyze, markdown


def test_fingerprint_reconstructs_mixed_proxy_run_without_attributing_operator(tmp_path: Path):
    path = tmp_path / "http.jsonl"
    rows = []
    counts = {
        "/api/provision/signup": (12, 200), "/api/missions": (6, 403),
        "/api/kassa/posts": (3, 401), "/api/forums/threads": (2, 401),
        "/api/mpp/credit": (1, 403), "/api/mpp/challenge": (1, 403),
        "/api/slots/fill": (1, 403),
    }
    n = 0
    for route, (total, status) in counts.items():
        for _ in range(total):
            rows.append({"timestamp": f"2026-11-12T22:03:{n:02d}Z",
                         "method": "POST", "path": route, "httpStatus": status,
                         "srcIp": f"173.252.83.{n % 20 + 1}", "clientUa": "caller-claim",
                         "requestId": f"edge-{n}"})
            n += 1
    path.write_text("\n".join(json.dumps(r) for r in rows))
    result = analyze([path, path])
    assert result["normalized_requests"] == len(rows)
    group = result["pattern_groups"][0]
    assert group["assessment"] == "multi_phase_stress_like"
    assert group["phase_counts"]["signup"] == 12
    assert group["phase_successes"]["signup"] == 12
    assert group["phase_rejections"]["mission"] == 6
    assert group["distinct_source_ips"] == 20
    assert group["authenticated_principals"] == []
    assert "does not establish" in markdown(result)


def test_structured_mcp_tool_outcome_not_mistaken_for_http_success(tmp_path: Path):
    p = tmp_path / "app.json"
    p.write_text(json.dumps([
        {"timestamp": "2026-11-16T12:12:01Z", "event": "security_call",
         "transport": "mcp", "tool": "agent.register", "outcome": "tool_error",
         "request_id": "ab1", "status": 200},
        {"timestamp": "2026-11-16T12:12:01Z", "event": "security_call",
         "transport": "http", "method": "POST", "route": "/api/provision/signup",
         "status": 429, "client_test_run_id": "run-12345678",
         "source_ip": "203.0.113.2", "request_id": "ab2"},
    ]))
    result = analyze([p])
    assert result["normalized_requests"] == 1
    assert result["pattern_groups"][0]["phase_rejections"]["signup"] == 1
    assert result["pattern_groups"][0]["claimed_run_ids"] == ["run-12345678"]
