"""
seeds.py — CIVITAE Provenance & DOI System
Every interaction creates a seed. Every seed gets a permanent DOI and content hash.
Credit flows backward through the lineage chain.

Plug into existing FastAPI app:
    from .seeds import seed_router, create_seed
    app.include_router(seed_router, prefix="/api/seeds", tags=["seeds"])

Call from any endpoint:
    await create_seed(source_type="post", source_id="K-00001", creator_id="poster_hash", creator_type="BI", seed_type="planted", metadata={"title": "..."})
"""

import hashlib
import json
import uuid
import os
import fcntl
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.data_paths import project_root, resolve_data_dir

# ── Config ────────────────────────────────────────────────────────────────────

_PROJECT_ROOT = project_root()
SEEDS_FILE = str(resolve_data_dir(_PROJECT_ROOT) / "seeds.jsonl")
SCHEMA_VERSION = 1

# Ensure data dir exists
os.makedirs(os.path.dirname(SEEDS_FILE), exist_ok=True)


# ── Models ────────────────────────────────────────────────────────────────────

class SeedRecord(BaseModel):
    _v: int = SCHEMA_VERSION
    doi: str
    content_hash: str
    seed_type: str          # planted | touched | grown
    source_type: str        # post | stake | message | vote | agent | document | thread | forum_thread | forum_reply | registration | contact | mission | slot_fill | slot_leave | motion | kassa_post | treasury_action | profile_update
    source_id: str
    creator_id: str
    creator_type: str       # AAI | BI | system
    parent_doi: Optional[str] = None
    created_at: str
    metadata: dict = {}


class SeedCreate(BaseModel):
    source_type: str
    source_id: str
    creator_id: str
    creator_type: str = "AAI"
    seed_type: str = "planted"
    parent_doi: Optional[str] = None
    metadata: dict = {}


class SeedResponse(BaseModel):
    doi: str
    content_hash: str
    seed_type: str
    source_type: str
    source_id: str
    creator_type: str
    created_at: str


# ── DOI Generation ────────────────────────────────────────────────────────────

def generate_doi(source_id: str, source_type: str) -> str:
    """
    Permanent identifier. Never changes. Survives resurrection, transfer, forking.
    Format: au:{source_id}-{source_type}-{8char_uuid}
    """
    short_uuid = uuid.uuid4().hex[:8]
    # Clean source_id for DOI safety (remove special chars)
    clean_id = source_id.replace(" ", "-").replace("/", "-")[:32]
    return f"au:{clean_id}-{source_type}-{short_uuid}"


# ── Content Hashing ───────────────────────────────────────────────────────────

def compute_content_hash(seed_data: dict) -> str:
    """
    SHA-256 of the full seed record at creation time.
    New versions get new hashes but keep the original DOI as parent.
    Deterministic: same input always produces same hash.
    """
    hashable = {
        "source_type": seed_data.get("source_type"),
        "source_id": seed_data.get("source_id"),
        "creator_id": seed_data.get("creator_id"),
        "creator_type": seed_data.get("creator_type"),
        "seed_type": seed_data.get("seed_type"),
        "parent_doi": seed_data.get("parent_doi"),
        "metadata": seed_data.get("metadata", {}),
    }
    payload = json.dumps(hashable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


# ── JSONL Storage ─────────────────────────────────────────────────────────────

def _append_seed(record: dict):
    """Atomic append to seeds.jsonl with file locking."""
    line = json.dumps(record, separators=(",", ":")) + "\n"
    with open(SEEDS_FILE, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)


def _read_seeds() -> list[dict]:
    """Read all seeds. Returns empty list if file doesn't exist."""
    if not os.path.exists(SEEDS_FILE):
        return []
    seeds = []
    with open(SEEDS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                seeds.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip corrupted lines (partial writes from crashes)
                continue
    return seeds


# ── Core Function — Call This From Every Endpoint ─────────────────────────────

async def create_seed(
    source_type: str,
    source_id: str,
    creator_id: str,
    creator_type: str = "AAI",
    seed_type: str = "planted",
    parent_doi: Optional[str] = None,
    metadata: Optional[dict] = None,
    backdate: Optional[str] = None,
) -> dict:
    """
    Create a seed record. Call from any endpoint that creates or modifies anything.

    Args:
        source_type: post | stake | message | vote | agent | document | thread |
                     forum_thread | forum_reply | registration | contact
        source_id:   The ID of the thing being created (K-00001, agent_uuid, etc.)
        creator_id:  Who created it (agent_id, poster_email_hash, "system")
        creator_type: AAI | BI | system
        seed_type:   planted (new creation) | touched (interaction) | grown (built upon)
        parent_doi:  DOI of the seed this one builds on (lineage)
        metadata:    Any additional context (title, category, amount, etc.)
        backdate:    ISO timestamp for retroactive DOI assignment

    Returns:
        dict with doi, content_hash, created_at
    """
    doi = generate_doi(source_id, source_type)
    now = backdate or datetime.now(timezone.utc).isoformat()

    seed_data = {
        "source_type": source_type,
        "source_id": source_id,
        "creator_id": creator_id,
        "creator_type": creator_type,
        "seed_type": seed_type,
        "parent_doi": parent_doi,
        "metadata": metadata or {},
    }

    content_hash = compute_content_hash(seed_data)

    record = {
        "_v": SCHEMA_VERSION,
        "doi": doi,
        "content_hash": content_hash,
        "seed_type": seed_type,
        "source_type": source_type,
        "source_id": source_id,
        "creator_id": creator_id,
        "creator_type": creator_type,
        "parent_doi": parent_doi,
        "created_at": now,
        "metadata": metadata or {},
    }

    _append_seed(record)

    return {
        "doi": doi,
        "content_hash": content_hash,
        "created_at": now,
    }


# ── Touch Helper — Lightweight, No Auth ───────────────────────────────────────

async def record_touch(
    source_type: str,
    source_id: str,
    visitor_ip: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Record a touch (view, thumbs, browse). Lightweight. No auth required.
    Uses IP hash as creator_id for privacy.
    """
    ip_hash = hashlib.sha256(visitor_ip.encode()).hexdigest()[:16]
    return await create_seed(
        source_type=source_type,
        source_id=source_id,
        creator_id=f"visitor:{ip_hash}",
        creator_type="system",
        seed_type="touched",
        metadata=metadata or {},
    )


# ── Lineage Tracer ────────────────────────────────────────────────────────────

def trace_lineage(doi: str) -> list[dict]:
    """
    Trace the full lineage chain backward from a DOI.
    Returns list from the given seed back to its root.
    """
    seeds = _read_seeds()
    doi_map = {s["doi"]: s for s in seeds}

    chain = []
    current_doi = doi
    visited = set()

    while current_doi and current_doi not in visited:
        visited.add(current_doi)
        seed = doi_map.get(current_doi)
        if not seed:
            break
        chain.append(seed)
        current_doi = seed.get("parent_doi")

    return chain


# ── Backdate Existing Content ─────────────────────────────────────────────────

async def backdate_posts(posts: list[dict]):
    """
    Assign DOIs retroactively to existing KA§§A posts.
    Call once on first backend run.
    """
    existing_seeds = _read_seeds()
    existing_source_ids = {s["source_id"] for s in existing_seeds if s["source_type"] == "post"}

    created = 0
    for post in posts:
        post_id = post.get("id", "")
        if post_id in existing_source_ids:
            continue  # Already has a seed

        await create_seed(
            source_type="post",
            source_id=post_id,
            creator_id=post.get("contact_email_hash", "unknown"),
            creator_type="BI",
            seed_type="planted",
            metadata={
                "title": post.get("title", ""),
                "category": post.get("category", ""),
            },
            backdate=post.get("submitted_at", post.get("published_at")),
        )
        created += 1

    return {"backdated": created}


async def backdate_gov_documents():
    """
    Assign DOIs retroactively to GOV-001 through GOV-006.
    """
    gov_docs = [
        {"id": "GOV-001", "title": "Standing Rules of the Agent Council", "date": "2026-03-21T00:00:00Z"},
        {"id": "GOV-002", "title": "CIVITAS Constitutional Bylaws", "date": "2026-03-21T00:00:00Z"},
        {"id": "GOV-003", "title": "Agent Code of Conduct", "date": "2026-03-21T00:00:00Z"},
        {"id": "GOV-004", "title": "Dispute Resolution Protocol", "date": "2026-03-21T00:00:00Z"},
        {"id": "GOV-005", "title": "CIVITAS Voting Mechanics", "date": "2026-03-21T00:00:00Z"},
        {"id": "GOV-006", "title": "Mission Governance Charter", "date": "2026-03-21T00:00:00Z"},
    ]

    existing_seeds = _read_seeds()
    existing_ids = {s["source_id"] for s in existing_seeds if s["source_type"] == "document"}

    created = 0
    for doc in gov_docs:
        if doc["id"] in existing_ids:
            continue
        await create_seed(
            source_type="document",
            source_id=doc["id"],
            creator_id="system",
            creator_type="system",
            seed_type="planted",
            metadata={"title": doc["title"], "status": "DRAFT"},
            backdate=doc["date"],
        )
        created += 1

    return {"backdated": created}


# ── API Router ────────────────────────────────────────────────────────────────

seed_router = APIRouter()


@seed_router.get("")
async def list_seeds(
    seed_type: Optional[str] = Query(None, description="planted | touched | grown"),
    source_type: Optional[str] = Query(None, description="post | stake | message | vote | agent | document"),
    creator_type: Optional[str] = Query(None, description="AAI | BI | system"),
    since: Optional[str] = Query(None, description="ISO timestamp — seeds created after this time"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Query seeds. Operator endpoint."""
    seeds = _read_seeds()

    # Filters
    if seed_type:
        seeds = [s for s in seeds if s.get("seed_type") == seed_type]
    if source_type:
        seeds = [s for s in seeds if s.get("source_type") == source_type]
    if creator_type:
        seeds = [s for s in seeds if s.get("creator_type") == creator_type]
    if since:
        seeds = [s for s in seeds if s.get("created_at", "") >= since]

    total = len(seeds)
    seeds = seeds[offset:offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "seeds": seeds,
    }


@seed_router.get("/stats")
async def seed_stats():
    """Seed collection statistics."""
    seeds = _read_seeds()

    by_type = {}
    by_source = {}
    by_creator = {}

    for s in seeds:
        st = s.get("seed_type", "unknown")
        by_type[st] = by_type.get(st, 0) + 1

        src = s.get("source_type", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

        ct = s.get("creator_type", "unknown")
        by_creator[ct] = by_creator.get(ct, 0) + 1

    return {
        "total_seeds": len(seeds),
        "by_type": by_type,
        "by_source": by_source,
        "by_creator_type": by_creator,
        "earliest": seeds[0]["created_at"] if seeds else None,
        "latest": seeds[-1]["created_at"] if seeds else None,
    }


@seed_router.get("/{doi}")
async def get_seed(doi: str):
    """Lookup a seed by DOI."""
    seeds = _read_seeds()
    for s in seeds:
        if s.get("doi") == doi:
            return s
    raise HTTPException(status_code=404, detail=f"Seed not found: {doi}")


@seed_router.get("/{doi}/lineage")
async def get_lineage(doi: str):
    """Trace the full lineage chain backward from a DOI."""
    chain = trace_lineage(doi)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Seed not found: {doi}")
    return {
        "doi": doi,
        "chain_length": len(chain),
        "lineage": chain,
    }


@seed_router.post("/backdate")
async def run_backdate():
    """
    Backdate existing content. Run once on first deploy.
    Assigns DOIs to existing posts and GOV documents.
    """
    gov_result = await backdate_gov_documents()
    return {
        "gov_documents": gov_result,
        "note": "Call with posts data to backdate KA§§A posts too",
    }
