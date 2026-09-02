from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.server import app


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def _client() -> TestClient:
    return TestClient(app)


def test_markdown_negotiation_and_vary_headers() -> None:
    client = _client()
    response = client.get("/", headers={"Accept": "text/markdown"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers.get("Vary") == "Accept, Accept-Encoding"
    assert "SIGNOMY" in response.text

    direct = client.get("/404.md")
    assert direct.status_code == 200
    assert direct.headers["content-type"].startswith("text/markdown")
    assert direct.headers.get("Vary") == "Accept, Accept-Encoding"


def test_real_agent_friendly_404() -> None:
    client = _client()
    response = client.get("/agent-readiness-probe-does-not-exist")
    assert response.status_code == 404
    assert "404" in response.text
    assert "sitemap" in response.text.lower() or "llms" in response.text.lower()


def test_openapi_surfaces_are_valid() -> None:
    client = _client()
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    document = response.json()
    assert document["openapi"].startswith("3.")
    operation_ids: list[str] = []
    for path_item in document["paths"].values():
        for method, operation in path_item.items():
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                operation_ids.append(operation["operationId"])
                assert operation.get("description") or operation.get("summary")
                assert "responses" in operation
    assert len(operation_ids) == len(set(operation_ids))

    yaml_response = client.get("/openapi.yaml")
    assert yaml_response.status_code == 200
    assert "openapi:" in yaml_response.text


def test_mcp_discovery_manifest_is_present() -> None:
    client = _client()
    response = client.get("/.well-known/mcp")
    assert response.status_code == 200
    data = response.json()
    assert data["transport"] == "streamable-http"
    assert data["url"].endswith("/mcp")


def test_developer_privacy_and_sitemap_resources_exist() -> None:
    client = _client()
    developers = client.get("/developers")
    privacy = client.get("/privacy")
    assert developers.status_code == 200
    assert privacy.status_code == 200
    assert "<h1>SIGNOMY developer resources</h1>" in developers.text
    assert "/openapi.json" in developers.text and "/mcp" in developers.text
    assert len(re.sub(r"<[^>]+>", " ", privacy.text)) > 500
    assert "<h1>Privacy notice</h1>" in privacy.text


def test_complete_organization_schema_is_discoverable() -> None:
    html = (FRONTEND / "developers.html").read_text(encoding="utf-8")
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
        html,
        flags=re.DOTALL,
    )
    schemas = [json.loads(block) for block in blocks]
    org = next(schema for schema in schemas if schema.get("@type") == "Organization")
    # Search Authority-backed organization entity. SIGNOMY is the platform, not the legal organization.
    assert org["name"] == "Ello Cello LLC"
    assert org["contactPoint"]["contactType"]
    assert org["contactPoint"]["email"]
    assert org["address"]["@type"] == "PostalAddress"
    assert org["address"]["addressCountry"] == "US"


def test_shared_footer_surfaces_developer_links_and_complete_org_graph() -> None:
    footer = (FRONTEND / "_footer.js").read_text(encoding="utf-8")
    for target in ("/developers", "/openapi.json", "/privacy"):
        assert target in footer
    assert "Organization" in footer
    assert "contactPoint" in footer


def test_cli_package_metadata_exposes_signomy_alias() -> None:
    pyproject = (ROOT / "packages" / "civitae-mcp" / "pyproject.toml").read_text(encoding="utf-8")
    assert 'signomy = "civitae_mcp.cli:main"' in pyproject
