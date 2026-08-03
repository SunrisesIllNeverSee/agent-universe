"""
pages.py — HTML page-serving endpoints and page-related API routes.

Extracted from server.py create_app() monolith.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response

from app.deps import state

router = APIRouter(tags=["pages"])

# ── Static assets ────────────────────────────────────────────────────────────

@router.get("/favicon.ico")
async def favicon() -> FileResponse:
    return FileResponse(state.frontend_dir / "favicon.ico")


@router.get("/apple-touch-icon.png")
async def apple_touch_icon() -> FileResponse:
    return FileResponse(state.frontend_dir / "apple-touch-icon.png")


# ── Page serves ──────────────────────────────────────────────────────────────

@router.get("/")
async def index() -> FileResponse:
    return FileResponse(state.frontend_dir / "index.html")


@router.get("/3d")
async def world_3d_redirect():
    return RedirectResponse("/world", status_code=301)


@router.get("/missions")
async def missions_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "missions.html")


@router.get("/deploy")
async def deploy_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "deploy.html")


@router.get("/campaign")
async def campaign_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "campaign.html")


@router.get("/kassa")
async def kassa_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "kassa.html")


@router.get("/kassa/post/{post_id}")
async def kassa_post_detail_page(post_id: str) -> FileResponse:
    return FileResponse(state.frontend_dir / "kassa-post.html")


@router.get("/world")
async def world_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "world.html")


@router.get("/slots")
async def slots_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "slots.html")


@router.get("/wave-registry")
async def wave_registry_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "wave-registry.html")


@router.get("/economics")
async def economics_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "economics.html")


@router.get("/command")
async def command_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "command.html")


@router.get("/mission")
async def mission_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "mission.html")


@router.get("/civitas")
async def civitas_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "civitas.html")


@router.get("/senate")
async def senate_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "senate.html")


@router.get("/academia")
async def academia_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "academia.html")


@router.get("/kingdoms")
async def kingdoms_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "kingdoms.html")


@router.get("/welcome")
async def welcome_page():
    return RedirectResponse("/academia")


@router.get("/sir-hawk.png")
async def sir_hawk_img() -> FileResponse:
    return FileResponse(state.frontend_dir / "sir-hawk.png")


@router.get("/forums")
async def forums_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "forums.html")


@router.get("/join")
async def join_redirect():
    return RedirectResponse("/#collaborate", status_code=301)


# STASHED — restore post-launch
@router.get("/agents")
async def agents_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "agents.html")

# @router.get("/agent/{slug}")
# async def agent_detail(slug: str) -> FileResponse:
#     return FileResponse(state.frontend_dir / "agent.html")


@router.get("/dashboard")
async def dashboard_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "dashboard.html")


# STASHED — restore post-launch
# @router.get("/admin")
# async def admin_page() -> FileResponse:
#     return FileResponse(state.frontend_dir / "admin.html")

@router.get("/mapsite")
async def mapsite_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "sitemap.html")


@router.get("/sitemap")
async def sitemap_redirect():
    return RedirectResponse("/mapsite", status_code=301)


# ── Page-related API endpoints ───────────────────────────────────────────────

@router.get("/api/pages")
async def get_pages() -> JSONResponse:
    pages_file = Path(__file__).parent.parent.parent / "config" / "pages.json"
    data = json.loads(pages_file.read_text())
    return JSONResponse(data)


@router.get("/flowchart")
async def flowchart_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "flowchart.html")


@router.get("/api/admin/page-html")
async def get_page_html(page: str) -> JSONResponse:
    """Return raw HTML source of a frontend page for the sitemap editor."""
    _ALLOWED_PAGES = {
        "about", "admin", "agent", "agent-profile", "agents", "bountyboard", "campaign",
        "civitae-map", "civitae-roadmap", "civitas", "command", "console", "contact",
        "dashboard", "deploy", "economics", "entry", "flowchart",
        "governance", "helpwanted", "hiring", "index", "iso-collaborators",
        "kassa", "kassa-post", "kassa-thread", "kingdoms", "leaderboard", "mission", "missions",
        "products", "refinery", "services", "sig-arena", "sitemap",
        "join", "lobby",
        "slots", "switchboard", "treasury", "vault", "wave-registry", "welcome", "world",
    }
    # Reject path traversal characters before any filesystem operation
    if ".." in page or "/" in page or "\\" in page:
        return JSONResponse({"error": "invalid page"}, status_code=400)
    safe = page.strip().lower()
    if safe not in _ALLOWED_PAGES:
        return JSONResponse({"error": "invalid page"}, status_code=400)
    frontend_dir = state.frontend_dir
    target = (frontend_dir / f"{safe}.html").resolve()
    # Defense-in-depth: ensure resolved path is within frontend_dir
    if not str(target).startswith(str(frontend_dir.resolve())):
        return JSONResponse({"error": "invalid page"}, status_code=400)
    if target.exists():
        return JSONResponse({"page": safe, "html": target.read_text()})
    return JSONResponse({"error": f"page '{safe}' not found"}, status_code=404)


# ── More page serves ─────────────────────────────────────────────────────────

@router.get("/entry")
async def entry_page():
    return RedirectResponse("/academia#register")


@router.get("/governance")
async def governance_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "governance.html")


@router.get("/advisory")
async def advisory_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "advisory.html")


@router.get("/portal")
async def portal_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "portal.html")


@router.get("/moses")
async def moses_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "moses.html")


@router.get("/grand-opening")
async def grand_opening_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "grand-opening.html")


@router.get("/black-card")
async def black_card_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "black-card.html")


@router.get("/early-believers")
async def early_believers_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "early-believers.html")



@router.get("/earnings-matrix")
async def earnings_matrix_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "agent-earnings-matrix.html")


@router.get("/agent-earnings-matrix")
async def agent_earnings_matrix_redirect():
    return RedirectResponse("/earnings-matrix", status_code=301)


@router.get("/earnings-journey")
async def earnings_journey_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "agent-earnings-journey.html")


@router.get("/agent-earnings-journey")
async def agent_earnings_journey_redirect():
    return RedirectResponse("/earnings-journey", status_code=301)


@router.get("/fee-credits")
async def fee_credits_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "fee-credit-packs.html")


@router.get("/fee-credit-packs")
async def fee_credit_packs_redirect():
    return RedirectResponse("/fee-credits", status_code=301)


@router.get("/agentdash")
async def agentdash_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "agentdash.html")


@router.get("/refinery")
async def refinery_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "refinery.html")


@router.get("/openroles")
async def openroles_redirect():
    return RedirectResponse("/helpwanted", status_code=301)


@router.get("/helpwanted")
async def helpwanted_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "helpwanted.html")


@router.get("/iso-collaborators")
async def iso_collaborators_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "iso-collaborators.html")


@router.get("/hiring")
async def hiring_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "hiring.html")


@router.get("/sig-arena")
async def sig_arena_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "sig-arena.html")


@router.get("/products")
async def products_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "products.html")


@router.get("/marketplace")
async def marketplace_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "products.html")


@router.get("/about")
async def about_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "about.html")


@router.get("/skill.md")
async def skill_md() -> FileResponse:
    return FileResponse(state.frontend_dir / "skill.md", media_type="text/markdown")


# ── Agent discovery files ───────────────────────────────────────────────────

@router.get("/llms.txt")
async def llms_txt() -> FileResponse:
    return FileResponse(state.frontend_dir / "llms.txt", media_type="text/plain")


@router.get("/agent.json")
async def agent_json() -> FileResponse:
    return FileResponse(state.frontend_dir / "agent.json", media_type="application/json")


@router.get("/robots.txt")
async def robots_txt() -> FileResponse:
    return FileResponse(state.frontend_dir / "robots.txt", media_type="text/plain")


@router.get("/indexnow-key.txt")
async def indexnow_key():
    """IndexNow verification key — 32-char hex, must match key in IndexNow pings."""
    return PlainTextResponse("51976fa8a5d2128a98a52af6b05d2141")


@router.get("/BingSiteAuth.xml")
async def bing_site_auth() -> Response:
    """Bing Webmaster Tools site verification."""
    return Response(
        '<?xml version="1.0"?>\n<users>\n\t<user>PLACEHOLDER_GET_FROM_BING_WEBMASTER_TOOLS</user>\n</users>',
        media_type="application/xml",
    )


@router.get("/.well-known/agent.json")
async def well_known_agent_json() -> FileResponse:
    return FileResponse(state.frontend_dir / "agent.json", media_type="application/json")


@router.get("/.well-known/mcp-server-card.json")
async def well_known_mcp_server_card() -> FileResponse:
    return FileResponse(
        state.frontend_dir / ".well-known" / "mcp-server-card.json",
        media_type="application/json",
    )


@router.get("/.well-known/governance.json")
async def well_known_governance_json() -> FileResponse:
    return FileResponse(
        state.frontend_dir / ".well-known" / "governance.json",
        media_type="application/json",
    )


@router.get("/seeds")
async def seeds_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "seeds.html")


@router.get("/services")
async def services_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "services.html")


@router.get("/console")
async def console_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "console.html")


@router.get("/admin")
async def admin_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "admin.html")


@router.get("/leaderboard")
async def leaderboard_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "leaderboard.html")


@router.get("/switchboard")
async def switchboard_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "switchboard.html")


@router.get("/mission-console")
async def mission_console_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "index.html")


@router.get("/civitae-map")
async def civitae_map_page():
    return RedirectResponse("/")


# STASHED — restore post-launch
# @router.get("/civitae-roadmap")
# async def civitae_roadmap_page():
#     return RedirectResponse("/sitemap")


@router.get("/treasury")
async def treasury_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "treasury.html")


@router.get("/vault")
async def vault_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "vault.html")


@router.get("/vault/{doc_id}")
async def vault_doc_page(doc_id: str) -> Response:
    """Serve vault-doc.html with document metadata and content server-side rendered.

    The JS renderer remains as progressive enhancement, but the raw HTML now
    includes the document title, H1, meta description, canonical, and a
    plain-text content block so search engines and crawlers see real content
    instead of a 'Loading document…' stub.
    """
    # Read the document data using the same logic as the API endpoint
    gov_dir = state.root / "docs" / "governance"
    prefix = doc_id.upper()
    matched = None
    if gov_dir.is_dir():
        for f in gov_dir.iterdir():
            if f.name.startswith(prefix) and f.suffix == ".md":
                matched = f
                break
    if not matched or not matched.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    text = matched.read_text(encoding="utf-8")
    meta: dict = {
        "doc_id": doc_id.upper(),
        "status": "DRAFT",
        "version": "1.0",
        "date": "",
        "title": "",
        "author": "",
        "flame": "6/6",
    }
    lines = text.split("\n")
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            meta["title"] = line[2:].strip()
        elif line.startswith("**Document ID:**"):
            meta["doc_id"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Version:**"):
            meta["version"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Status:**"):
            meta["status"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Date:**"):
            meta["date"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Author:**"):
            meta["author"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Six Fold Flame"):
            raw = line.split(":**", 1)[1].strip()
            meta["flame"] = "6/6" if "six" in raw.lower() or "all" in raw.lower() else raw
        elif line.startswith("## ") and body_start == 0:
            body_start = i
            break
    body_md = "\n".join(lines[body_start:]) if body_start else text

    # Build SEO-friendly title and meta description
    full_title = meta["title"] or meta["doc_id"]
    # Strip "GOV-00X: " prefix for cleaner display
    colon_idx = full_title.find(":")
    short_title = full_title[colon_idx + 1:].strip() if 0 < colon_idx < 10 else full_title
    seo_title = f"{short_title} — The Vault | SIGNOMY"
    meta_desc = f"{meta['doc_id']}: {short_title}. {meta['status'].lower()} document v{meta['version']} ({meta['date']}). Part of the six-document constitutional archive governing AI agent operations under MO§ES."
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152] + "..."

    # Convert markdown body to plain text for noscript/crawler content
    import re as _re
    plain_lines = []
    for ln in body_md.split("\n"):
        stripped = ln.strip()
        if not stripped or stripped == "---":
            continue
        # Remove markdown formatting
        clean = _re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
        clean = _re.sub(r"^\|.*\|$", "", clean)  # skip table rows
        clean = _re.sub(r"^#+\s*", "", clean)  # remove heading markers
        clean = _re.sub(r"^-\s+", "", clean)  # remove list markers
        if clean.strip():
            plain_lines.append(clean)
    plain_text = "\n".join(plain_lines[:200])  # cap at 200 lines

    # Read the template and inject SSR content
    template = (state.frontend_dir / "vault-doc.html").read_text(encoding="utf-8")

    # Replace the static canonical with a self-referencing one
    canonical_url = f"https://signomy.xyz/vault/{doc_id}"
    template = template.replace(
        '<link rel="canonical" href="https://signomy.xyz/vault" />',
        f'<link rel="canonical" href="{canonical_url}" />',
    )

    # Replace the static title
    template = template.replace(
        "<title>Document — The Vault</title>",
        f"<title>{seo_title}</title>",
    )

    # Add meta description after the canonical
    template = template.replace(
        f'<link rel="canonical" href="{canonical_url}" />',
        f'<link rel="canonical" href="{canonical_url}" />\n<meta name="description" content="{meta_desc}" />',
    )

    # Replace the loading state with SSR content (JS will enhance it if it runs)
    ssr_html = f"""<div class="doc-header">
  <div class="doc-meta-row">
    <span class="doc-id-badge">{meta['doc_id']}</span>
    <span class="status-badge status-{meta['status'].lower()}">{meta['status']}</span>
    <span class="flame-badge"><span class="dot"></span> {meta['flame']} Flame</span>
    <span class="version-badge">v{meta['version']} · {meta['date']}</span>
  </div>
  <h1 class="doc-title">{short_title}</h1>
  <div class="doc-author">{meta['author']}</div>
</div>
<div class="doc-body">
  <div class="doc-section"><div class="doc-para" style="white-space: pre-wrap;">{plain_text}</div></div>
</div>"""

    template = template.replace(
        '<div class="loading-state" id="doc-loading">Loading document&hellip;</div>',
        ssr_html,
    )

    return Response(content=template, media_type="text/html; charset=utf-8")


@router.get("/api/vault/documents/{doc_id}")
async def vault_get_document(doc_id: str) -> dict:
    """Return a GOV document's metadata and body from docs/governance/."""
    gov_dir = state.root / "docs" / "governance"
    # Map doc_id (e.g. "gov-001") to filename prefix (e.g. "GOV-001")
    prefix = doc_id.upper()
    matched = None
    if gov_dir.is_dir():
        for f in gov_dir.iterdir():
            if f.name.startswith(prefix) and f.suffix == ".md":
                matched = f
                break
    if not matched or not matched.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    text = matched.read_text(encoding="utf-8")
    # Parse metadata from header lines
    meta: dict = {"doc_id": doc_id.upper(), "status": "DRAFT", "version": "1.0", "date": "", "title": "", "author": "", "flame": "6/6"}
    lines = text.split("\n")
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            meta["title"] = line[2:].strip()
        elif line.startswith("**Document ID:**"):
            meta["doc_id"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Version:**"):
            meta["version"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Status:**"):
            meta["status"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Date:**"):
            meta["date"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Author:**"):
            meta["author"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Six Fold Flame"):
            raw = line.split(":**", 1)[1].strip()
            meta["flame"] = "6/6" if "six" in raw.lower() or "all" in raw.lower() else raw
        elif line.startswith("## ") and body_start == 0:
            body_start = i
            break
    body = "\n".join(lines[body_start:]) if body_start else text
    return {"meta": meta, "body": body}


@router.get("/bountyboard")
async def bountyboard_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "bountyboard.html")


# ── Contact page serve ───────────────────────────────────────────────────────

@router.get("/contact")
async def contact_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "contact.html")


# ── Sitemap ───────────────────────────────────────────────────────────────────

@router.get("/sitemap.xml")
async def sitemap_xml():
    """Redirect to sitemap-v2.xml — the focused sitemap we actually want crawled."""
    return RedirectResponse("/sitemap-v2.xml", status_code=301)
