#!/usr/bin/env python3
"""Read-only reconstruction of Signomy stress-like API activity.

Accepts Railway --http --json, structured security_call logs, JSON arrays or
JSONL. No network, account changes, credentials or raw request bodies.
Buckets are *suite-equivalent patterns*, not identified operators/machines.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

SIGNATURE = {
    "signup": 12, "mission": 6, "kassa": 3,
    "forum": 2, "credit": 1, "challenge": 1, "slot": 1,
}


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return t.astimezone(timezone.utc) if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _documents(path: Path):
    raw = path.read_text(encoding="utf-8")
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            yield from value
        elif isinstance(value, dict):
            if isinstance(value.get("selected"), list):
                yield from value["selected"]
            else:
                yield value
        return
    except json.JSONDecodeError:
        pass
    for line in raw.splitlines():
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _phase(method: str, path: str) -> str | None:
    if method != "POST":
        return None
    if path == "/api/provision/signup":
        return "signup"
    if path == "/api/missions":
        return "mission"
    if path == "/api/kassa/posts":
        return "kassa"
    if path == "/api/forums/threads":
        return "forum"
    if path == "/api/mpp/credit":
        return "credit"
    if path == "/api/mpp/challenge":
        return "challenge"
    if path.startswith("/api/slots/"):
        return "slot"
    return None


def normalize(d: dict) -> dict | None:
    # Provider HTTP logs and new metadata-only app records are different grains.
    is_app = d.get("event") == "security_call"
    if is_app and d.get("transport") != "http":
        return None
    method = d.get("method")
    path = d.get("route") if is_app else d.get("path")
    if not isinstance(method, str) or not isinstance(path, str):
        return None
    time = _time(d.get("timestamp"))
    if time is None:
        return None
    phase = _phase(method, path)
    return {
        "timestamp": time.isoformat(),
        "time": time,
        "phase": phase,
        "method": method,
        "path": path,
        "status": int(d.get("status") or d.get("httpStatus") or 0),
        "source_ip": d.get("source_ip") if is_app else d.get("srcIp"),
        "ua_fp": d.get("user_agent_fingerprint") if is_app else d.get("clientUa"),
        "request_id": d.get("request_id") if is_app else d.get("requestId"),
        "edge_id": d.get("edge_request_id") if is_app else d.get("requestId"),
        "principal_id": d.get("principal_id") if is_app else None,
        "test_run_id": d.get("client_test_run_id") if is_app else None,
        "source": "app" if is_app else "railway",
    }


def analyze(paths: list[Path], gap_seconds: int = 600) -> dict:
    rows = []
    seen = set()
    for path in paths:
        for d in _documents(path):
            if not isinstance(d, dict):
                continue
            r = normalize(d)
            if not r:
                continue
            # Two exports of the same observation are not two requests.
            dedup = (r["source"], r["request_id"], r["timestamp"], r["method"], r["path"])
            if dedup in seen:
                continue
            seen.add(dedup)
            rows.append(r)
    rows.sort(key=lambda r: r["time"])
    runs = []
    active = []
    for r in rows:
        if not r["phase"]:
            continue
        if active and (r["time"] - active[-1]["time"]).total_seconds() > gap_seconds:
            runs.append(active)
            active = []
        active.append(r)
    if active:
        runs.append(active)
    findings = []
    for group in runs:
        counts = Counter(r["phase"] for r in group)
        successes = Counter(r["phase"] for r in group if 200 <= r["status"] < 300)
        blocked = Counter(r["phase"] for r in group if r["status"] >= 400)
        phases = [p for p in SIGNATURE if counts[p]]
        # Multiple matching phases matter much more than name or user-agent alone.
        consistent = [p for p in ("mission", "kassa", "forum", "credit", "challenge", "slot") if
                      counts[p] >= SIGNATURE[p] and counts[p] % SIGNATURE[p] == 0]
        hint_runs = sorted({r["test_run_id"] for r in group if r["test_run_id"]})
        findings.append({
            "start_utc": group[0]["timestamp"],
            "end_utc": group[-1]["timestamp"],
            "assessment": ("multi_phase_stress_like" if len(consistent) >= 3 and counts["signup"]
                           else "signup_burst" if counts["signup"] >= 5 else "partial_pattern"),
            "confidence_note": "Pattern grouping does not establish runner, operator or shared intent.",
            "phase_counts": dict(counts),
            "phase_successes": dict(successes),
            "phase_rejections": dict(blocked),
            "suite_equivalent_ratios": {p: round(counts[p] / n, 2) for p, n in SIGNATURE.items() if counts[p]},
            "phases_observed": phases,
            "distinct_source_ips": len({r["source_ip"] for r in group if r["source_ip"]}),
            "distinct_user_agent_fingerprints": len({r["ua_fp"] for r in group if r["ua_fp"]}),
            "claimed_run_ids": hint_runs,
            "authenticated_principals": sorted({r["principal_id"] for r in group if r["principal_id"]}),
            "request_ids": sorted({r["request_id"] for r in group if r["request_id"]}),
            "edge_request_ids": sorted({r["edge_id"] for r in group if r["edge_id"]}),
        })
    return {"schema_version": 1, "source_files": [str(p) for p in paths], "normalized_requests": len(rows),
            "pattern_groups": findings,
            "limitations": [
                "External source IP and user-agent are not operator identities.",
                "A matching test-run header is caller supplied and not authenticated.",
                "HTTP 2xx does not establish success of an inner MCP tool call.",
                "Across-source duplicates without matching request IDs may remain.",
                "No request bodies, tokens or private contents are ingested.",
            ]}


def markdown(result: dict) -> str:
    lines = ["# Signomy read-only stress-run fingerprint analysis", "",
             f"Normalized requests: {result['normalized_requests']}",
             f"Pattern groups: {len(result['pattern_groups'])}", ""]
    for i, g in enumerate(result["pattern_groups"], 1):
        lines += [f"## Group {i}: {g['assessment']}", "",
                  f"Window: {g['start_utc']} to {g['end_utc']}",
                  f"Sources: {g['distinct_source_ips']} distinct observed IPs; "
                  f"UA fingerprints: {g['distinct_user_agent_fingerprints']}",
                  f"Phase counts: `{json.dumps(g['phase_counts'], sort_keys=True)}`",
                  f"Successful phase requests: `{json.dumps(g['phase_successes'], sort_keys=True)}`",
                  f"Rejected phase requests: `{json.dumps(g['phase_rejections'], sort_keys=True)}`",
                  f"Declared test runs (unverified): {', '.join(g['claimed_run_ids']) or 'none'}",
                  f"Authenticated principals: {', '.join(g['authenticated_principals']) or 'none established'}",
                  f"**Assessment limit:** {g['confidence_note']}", ""]
    lines += ["## Limitations", ""]
    lines += [f"- {x}" for x in result["limitations"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="+", type=Path, help="Railway HTTP or structured security_call JSON/JSONL")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    args = parser.parse_args()
    result = analyze(args.input)
    if args.json_out:
        args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.md_out:
        args.md_out.write_text(markdown(result))
    print(json.dumps({"normalized_requests": result["normalized_requests"],
                      "pattern_groups": [{k: g[k] for k in ("start_utc", "end_utc", "assessment", "phase_counts", "phase_successes", "phase_rejections", "distinct_source_ips")} for g in result["pattern_groups"]]}, indent=2))


if __name__ == "__main__":
    main()
