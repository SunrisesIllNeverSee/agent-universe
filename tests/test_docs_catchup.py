"""Docs catch-up (p5c): skill.md, OpenAPI and the field guide must match the code.

Tool names/params, REST paths and every fee number are checked against what the
app registers and what config/economic_rates.json says, so the docs cannot drift
silently again.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = (ROOT / "frontend" / "skill.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "docs" / "agent-onboarding" / "AGENT-FIELD-GUIDE.md").read_text(encoding="utf-8")
RATES = json.loads((ROOT / "config" / "economic_rates.json").read_text(encoding="utf-8"))

TOOL_RE = re.compile(r"^(chat|agent|market|govern|mission|forum|economy|platform|admin|entry)\.[a-z_]+(\.[a-z_]+)?$")
PENDING_MARKER = "<!-- p5c: escrow rules / force-assign pending -->"


def _registered_tools(app) -> dict:
    from app.deps import state
    mcp = state.mcp_bridge.build_fastmcp()
    return {t.name: t for t in asyncio.run(mcp.list_tools())}


def _doc_tool_tokens(text: str) -> set[str]:
    toks = set(re.findall(r"`([^`\s]+)`", text))
    return {t for t in toks if TOOL_RE.match(t) and not t.endswith((".json", ".md", ".txt"))}


def _pct(x: float) -> str:
    return f"{x * 100:g}%"


def _config_percents() -> set[str]:
    out = {_pct(v["fee_rate"]) for v in RATES["tiers"].values()}
    out |= {_pct(v) for k, v in RATES["target_tier_rates"].items() if not k.startswith("_")}
    out |= {_pct(v) for v in RATES["credits"].values() if isinstance(v, float) and v < 1}
    out |= {_pct(v) for k, v in RATES["fee_split"].items() if isinstance(v, float)}
    out.add(_pct(RATES["trial"]["fee_rate"]))
    return out


def test_every_registered_mcp_tool_is_in_skill_md_and_vice_versa(app):
    registered = set(_registered_tools(app))
    documented = _doc_tool_tokens(SKILL)
    assert registered - documented == set(), f"tools missing from skill.md: {sorted(registered - documented)}"
    assert documented - registered == set(), f"skill.md names tools that are not registered: {sorted(documented - registered)}"


def test_skill_md_documents_each_tool_params_and_auth(app):
    tools = _registered_tools(app)
    rows = {}
    for line in SKILL.splitlines():
        m = re.match(r"\|\s*`([a-z_.]+)`\s*\|", line)
        if m and m.group(1) in tools:
            rows[m.group(1)] = line
    assert set(rows) == set(tools), f"tools without a table row: {sorted(set(tools) - set(rows))}"
    for name, tool in tools.items():
        schema = tool.inputSchema
        props = set(schema.get("properties", {}))
        required = set(schema.get("required", []))
        for p in props - {"api_key", "admin_key"}:
            assert f"`{p}`" in rows[name], f"{name}: param {p} not documented"
        auth = ("admin_key" if "admin_key" in props else "api_key" if "api_key" in required
                else "api_key?" if "api_key" in props else "none")
        assert f"| {auth} |" in rows[name], f"{name}: auth column should be {auth}"


def test_skill_md_tool_count_matches_registered(app):
    n = len(_registered_tools(app))
    counts = {int(c) for c in re.findall(r"(\d+) (?:MCP )?tools", SKILL)}
    assert counts == {n}, f"skill.md tool counts {counts} != registered {n}"


def test_every_percentage_in_skill_md_comes_from_config():
    allowed = _config_percents()
    stated = set(re.findall(r"(?<![\d.])(\d+(?:\.\d+)?%)", SKILL))
    assert stated, "skill.md states no fee numbers"
    assert stated <= allowed, f"percentages not in config/economic_rates.json: {sorted(stated - allowed)}"


def test_skill_md_flat_rate_and_trial_match_config():
    flat = {v["fee_rate"] for v in RATES["tiers"].values()}
    assert len(flat) == 1, "config is no longer flat; reword the soft-launch paragraph"
    assert f"Flat {_pct(flat.pop())}" in SKILL
    t = RATES["trial"]
    assert f"first {t['mission_limit']} missions or {t['day_limit']} days" in SKILL
    for tier, v in RATES["target_tier_rates"].items():
        if not tier.startswith("_"):
            assert f"{RATES['tiers'][tier]['label'].title()} {_pct(v)}" in SKILL


def test_field_guide_flat_rate_matches_config():
    flat = _pct(next(iter(RATES["tiers"].values()))["fee_rate"])
    assert f"flat {flat}" in GUIDE.lower() or f"Flat {flat}" in GUIDE


def test_skill_md_rest_endpoints_are_live_routes(app):
    live = set()
    for route in app.routes:
        for method in getattr(route, "methods", None) or ():
            live.add((method.upper(), re.sub(r"\{[^}]+\}", "{}", route.path)))
    ghosts = []
    for m in re.finditer(r"^\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`([^`]+)`", SKILL, re.M):
        path = re.sub(r"\{[^}]+\}", "{}", m.group(2).split("?")[0])
        if (m.group(1), path) not in live:
            ghosts.append(f"{m.group(1)} {m.group(2)}")
    assert ghosts == [], f"skill.md lists non-live endpoints: {ghosts}"


def test_skill_md_covers_p5_surfaces():
    for needle in ("/api/escrow/checkout", "/api/escrow/{escrow_id}/dispute", "/meetings", "/api/connect/products",
                   "/api/connect/checkout", "/api/economy/trial/{agent_id}", "provenance_error", "provenance_errors",
                   "govern.point_of_order", "govern.rule", "govern.appeal", "govern.second", "govern.appeal_vote"):
        assert needle in SKILL, f"skill.md missing {needle}"
    assert PENDING_MARKER in SKILL


def test_skill_md_money_rules_stated():
    low = SKILL.lower()
    assert "bound" in low and "stripe account" in low
    assert "price" in low and "product record" in low


def test_openapi_cashout_does_not_require_body_account():
    spec = json.loads((ROOT / "frontend" / "openapi.json").read_text(encoding="utf-8"))
    schema = spec["paths"]["/api/connect/cashout"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert schema["required"] == ["amount"]
    assert "bound" in spec["paths"]["/api/connect/cashout"]["post"]["description"].lower()


def test_openapi_documents_escrow_and_checkout_paths():
    spec = json.loads((ROOT / "frontend" / "openapi.json").read_text(encoding="utf-8"))
    for p in ("/api/escrow/checkout", "/api/escrow", "/api/escrow/{escrow_id}", "/api/escrow/{escrow_id}/refund",
              "/api/escrow/{escrow_id}/dispute", "/api/connect/products", "/api/connect/checkout",
              "/api/economy/trial/{agent_id}"):
        assert p in spec["paths"], f"openapi.json missing {p}"
    checkout = spec["paths"]["/api/connect/checkout"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert checkout["required"] == ["product_id"]
    assert "price_cents" not in checkout["properties"]


def test_trial_init_note_uses_config_numbers(admin_client):
    from app.economy import TRIAL_DAY_LIMIT, TRIAL_MISSION_LIMIT
    r = admin_client.post("/api/economy/trial/init", json={"agent_id": "p5c-trial-note"})
    assert r.status_code == 200
    note = r.json()["note"]
    assert f"{TRIAL_MISSION_LIMIT} missions" in note and f"{TRIAL_DAY_LIMIT} days" in note


def test_field_guide_covers_p5_money_and_procedure():
    for needle in ("/api/escrow/checkout", "bound to your agent", "provenance_error", "govern.appeal_vote", "/meetings"):
        assert needle in GUIDE, f"field guide missing {needle}"
    assert PENDING_MARKER in GUIDE
