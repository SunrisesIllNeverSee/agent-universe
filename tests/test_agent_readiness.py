"""Contract tests for public agent-readiness and discovery surfaces."""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def _vercel() -> dict:
    return json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))


def test_markdown_content_negotiation_is_cache_safe() -> None:
    config = _vercel()
    markdown_rewrites = [
        rule for rule in config["rewrites"]
        if rule.get("source") == "/"
        and any(
            cond.get("type") == "header"
            and cond.get("key", "").lower() == "accept"
            and "text/markdown" in str(cond.get("value", ""))
            for cond in rule.get("has", [])
        )
    ]
    assert markdown_rewrites
    assert markdown_rewrites[0]["destination"] == "/index.md"

    root_headers = [rule for rule in config["headers"] if rule.get("source") == "/"]
    vary_values = [
        h["value"]
        for rule in root_headers
        for h in rule.get("headers", [])
        if h.get("key", "").lower() == "vary"
    ]
    assert any("Accept" in value and "Accept-Encoding" in value for value in vary_values)
    assert (FRONTEND / "index.md").read_text(encoding="utf-8").startswith("# Signomy")


def test_agent_friendly_404_recovery_files_exist() -> None:
    markdown = (FRONTEND / "404.md").read_text(encoding="utf-8")
    html = (FRONTEND / "404.html").read_text(encoding="utf-8")
    for target in ("/sitemap.xml", "/llms.txt", "/developers", "/openapi.json"):
        assert target in markdown
        assert target in html
    assert "noindex" in html


def test_openapi_json_is_function_calling_ready() -> None:
    spec = json.loads((FRONTEND / "openapi.json").read_text(encoding="utf-8"))
    assert spec["openapi"].startswith("3.1")
    assert spec["servers"][0]["url"] == "https://signomy.xyz"

    operation_ids: list[str] = []
    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            operation_id = operation.get("operationId")
            assert operation_id, f"missing operationId: {method.upper()} {path}"
            operation_ids.append(operation_id)
            assert operation.get("description"), f"missing description: {operation_id}"
            assert operation.get("responses"), f"missing responses: {operation_id}"
            for parameter in operation.get("parameters", []):
                assert parameter.get("schema"), f"untyped parameter in {operation_id}"
                assert parameter.get("description"), f"undocumented parameter in {operation_id}"
            request_body = operation.get("requestBody")
            if request_body:
                schema = request_body["content"]["application/json"]["schema"]
                assert schema, f"untyped request body in {operation_id}"

    assert len(operation_ids) == len(set(operation_ids))
    error = spec["components"]["schemas"]["ErrorResponse"]["properties"]["error"]
    assert set(error["required"]) == {"code", "message", "hint"}


def test_openapi_json_and_yaml_are_both_published() -> None:
    assert (FRONTEND / "openapi.json").is_file()
    yaml_text = (FRONTEND / "openapi.yaml").read_text(encoding="utf-8")
    assert yaml_text.startswith("openapi: 3.1.0")


def test_mcp_well_known_discovery_points_to_server_card() -> None:
    rewrites = _vercel()["rewrites"]
    rule = next(rule for rule in rewrites if rule.get("source") == "/.well-known/mcp")
    assert rule["destination"] == "/.well-known/mcp-server-card.json"
    card = json.loads((FRONTEND / ".well-known" / "mcp-server-card.json").read_text(encoding="utf-8"))
    assert card["url"] == "https://signomy.xyz/mcp"
    assert card["transport"] == "streamable-http"


def test_llms_has_when_to_use_and_developer_discovery() -> None:
    text = (FRONTEND / "llms.txt").read_text(encoding="utf-8")
    assert "## When to use Signomy / CIVITAE" in text
    for url in (
        "https://signomy.xyz/developers",
        "https://signomy.xyz/openapi.json",
        "https://signomy.xyz/.well-known/mcp",
        "https://signomy.xyz/mcp",
    ):
        assert url in text


def test_developer_and_privacy_trust_pages_are_substantive() -> None:
    developers = (FRONTEND / "developers.html").read_text(encoding="utf-8")
    privacy = (FRONTEND / "privacy.html").read_text(encoding="utf-8")
    assert "<h1>SIGNOMY developer resources</h1>" in developers
    assert "/openapi.json" in developers and "/mcp" in developers
    assert len(re.sub(r"<[^>]+>", " ", privacy)) > 500
    assert "<h1>Privacy notice</h1>" in privacy


def test_complete_organization_schema_is_discoverable() -> None:
    html = (FRONTEND / "developers.html").read_text(encoding="utf-8")
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
        html,
        flags=re.DOTALL,
    )
    schemas = [json.loads(block) for block in blocks]
    org = next(schema for schema in schemas if schema.get("@type") == "Organization")
    assert org["name"] == "SIGNOMY"
    assert org["contactPoint"]["contactType"]
    assert org["contactPoint"]["email"]
    assert org["address"]["@type"] == "PostalAddress"
    assert org["address"]["addressCountry"] == "US"


def test_signomy_cli_alias_is_packaged() -> None:
    with (ROOT / "packages" / "civitae-mcp" / "pyproject.toml").open("rb") as fh:
        project = tomllib.load(fh)["project"]
    assert project["scripts"]["civitae-mcp"] == "civitae_mcp:main"
    assert project["scripts"]["signomy"] == "civitae_mcp:main"
    assert "signomy" in project["keywords"]


def test_sitemap_lists_new_human_facing_trust_surfaces() -> None:
    sitemap = (FRONTEND / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://signomy.xyz/developers" in sitemap
    assert "https://signomy.xyz/privacy" in sitemap


def test_api_404_is_structured_json(client) -> None:
    response = client.get("/api/agent-readiness-probe-does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["message"]
    assert "openapi.json" in error["hint"]


def test_api_validation_error_is_structured_json(client) -> None:
    response = client.post("/api/provision/login", json={})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["message"]
    assert error["hint"]
    assert error["details"]


def test_admin_guard_error_is_structured_json(client) -> None:
    response = client.post("/api/message", json={"message": "probe"})
    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "admin_key_required"
    assert error["message"]
    assert error["hint"]
