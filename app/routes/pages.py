"""
pages.py — HTML page-serving endpoints and page-related API routes.

Extracted from server.py create_app() monolith.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

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
    return FileResponse(state.frontend_dir / "kingdoms.html")


@router.get("/3d")
async def world_3d_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "world.html")


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


# STASHED — restore post-launch
# @router.get("/agents")
# async def agents_page() -> FileResponse:
#     return FileResponse(state.frontend_dir / "agents.html")

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

# @router.get("/sitemap")
# async def sitemap_page() -> FileResponse:
#     return FileResponse(state.frontend_dir / "sitemap.html")


# ── Page-related API endpoints ───────────────────────────────────────────────

@router.get("/api/pages")
async def get_pages() -> JSONResponse:
    pages_file = Path(__file__).parent.parent / "config" / "pages.json"
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


@router.get("/refinery")
async def refinery_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "refinery.html")


@router.get("/openroles")
async def openroles_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "helpwanted.html")


@router.get("/helpwanted")
async def helpwanted_redirect():
    from starlette.responses import RedirectResponse
    return RedirectResponse("/openroles", status_code=301)


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


@router.get("/seeds")
async def seeds_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "seeds.html")


@router.get("/services")
async def services_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "services.html")


@router.get("/console")
async def console_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "console.html")


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
async def vault_doc_page(doc_id: str) -> FileResponse:
    return FileResponse(state.frontend_dir / "vault-doc.html")


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
