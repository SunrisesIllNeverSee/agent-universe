"""p5i: documented REST paths must exist as routes in the app, and the new contracts must be documented."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SPEC_JSON = json.loads((ROOT / "frontend" / "openapi.json").read_text(encoding="utf-8"))
SPEC_YAML = yaml.safe_load((ROOT / "frontend" / "openapi.yaml").read_text(encoding="utf-8"))
SKILL = (ROOT / "frontend" / "skill.md").read_text(encoding="utf-8")

NEW = [("/api/economy/wallets", "get"), ("/api/economy/wallets", "post"),
       ("/api/economy/wallets/{wallet_id}", "delete"), ("/api/economy/withdraw", "post"),
       ("/api/connect/accounts", "post"), ("/api/work-entry/force-assign", "post"),
       ("/api/kassa/posts", "post")]


def _routes(app) -> set[tuple[str, str]]:
    out = set()
    for r in app.routes:
        path = getattr(r, "path", None)
        for m in getattr(r, "methods", None) or ():
            out.add((path, m.lower()))
    return out


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def _check(spec, app):
    have = {(_norm(p), m) for p, m in _routes(app)}
    missing = []
    for path, item in spec["paths"].items():
        for method in item:
            if method.lower() in {"get", "post", "put", "patch", "delete"} and (_norm(path), method.lower()) not in have:
                missing.append(f"{method.upper()} {path}")
    assert not missing, f"documented but not routed: {missing}"


def test_openapi_json_paths_exist_as_routes(app):
    _check(SPEC_JSON, app)


def test_openapi_yaml_paths_exist_as_routes(app):
    _check(SPEC_YAML, app)


def test_new_contracts_in_both_specs():
    for spec in (SPEC_JSON, SPEC_YAML):
        for path, method in NEW:
            assert method in spec["paths"].get(path, {}), f"{method} {path} missing"


def test_kassa_post_answer_window_and_wallet_cap():
    props = SPEC_JSON["paths"]["/api/kassa/posts"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]
    assert (props["answer_window_hours"]["minimum"], props["answer_window_hours"]["maximum"]) == (12, 168)
    assert "409" in SPEC_JSON["paths"]["/api/connect/accounts"]["post"]["responses"]
    assert "409" in SPEC_JSON["paths"]["/api/economy/wallets"]["post"]["responses"]


def test_coming_wallet_limits_use_config_key_names_in_docs():
    for key in ("wallets.link_interval_hours", "wallets.new_wallet_window_hours", "wallets.new_wallet_cap_usd"):
        assert key in SKILL, key
        assert key in json.dumps(SPEC_JSON), key
    assert "admin.force_assign" in SKILL
