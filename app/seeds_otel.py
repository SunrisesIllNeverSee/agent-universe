"""
seeds_otel.py — OpenTelemetry Trace Export Adapter for CIVITAE Seeds

Converts seeds.jsonl into OTel-compatible trace spans. Every seed becomes
a span. Lineage chains (parent_doi → child) become parent-child span
relationships. Governance metadata rides as span attributes.

Export targets:
  - OTel JSON (compatible with Langfuse, LangSmith, Phoenix, Jaeger)
  - Hugging Face dataset (JSON lines, for open agent trace research)
  - SIGRANK metrics (behavioral composites computed from trace data)

Plug into FastAPI app:
    from app.seeds_otel import otel_router
    app.include_router(otel_router, prefix="/api/traces", tags=["traces"])
"""

import json
import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Optional
from collections import defaultdict
from fastapi import APIRouter, Query

from app.data_paths import project_root, resolve_data_dir
from app.seeds import _read_seeds

_PROJECT_ROOT = project_root()


# ── OTel Span Model ──────────────────────────────────────────────────────────

def seed_to_span(seed: dict, trace_id: str = None) -> dict:
    """
    Convert a single seed record into an OpenTelemetry-compatible span.

    Maps:
      seed.doi          → span.span_id (hashed to 16-char hex)
      seed.parent_doi   → span.parent_span_id
      seed.source_type  → span.name
      seed.created_at   → span.start_time
      seed.*            → span.attributes
    """
    span_id = hashlib.sha256(seed["doi"].encode()).hexdigest()[:16]

    parent_span_id = None
    if seed.get("parent_doi"):
        parent_span_id = hashlib.sha256(seed["parent_doi"].encode()).hexdigest()[:16]

    if trace_id is None:
        trace_id = hashlib.sha256(
            (seed.get("parent_doi") or seed["doi"]).encode()
        ).hexdigest()[:32]

    created_at = seed.get("created_at", "")
    try:
        ts = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        start_time_unix_nano = int(ts.timestamp() * 1e9)
    except (ValueError, AttributeError):
        start_time_unix_nano = int(time.time() * 1e9)

    span = {
        "traceId": trace_id,
        "spanId": span_id,
        "parentSpanId": parent_span_id,
        "name": f"civitae.{seed.get('source_type', 'unknown')}",
        "kind": "SPAN_KIND_INTERNAL",
        "startTimeUnixNano": start_time_unix_nano,
        "endTimeUnixNano": start_time_unix_nano,
        "status": {"code": "STATUS_CODE_OK"},
        "attributes": [
            {"key": "civitae.doi", "value": {"stringValue": seed.get("doi", "")}},
            {"key": "civitae.seed_type", "value": {"stringValue": seed.get("seed_type", "")}},
            {"key": "civitae.source_type", "value": {"stringValue": seed.get("source_type", "")}},
            {"key": "civitae.source_id", "value": {"stringValue": seed.get("source_id", "")}},
            {"key": "civitae.creator_id", "value": {"stringValue": seed.get("creator_id", "")}},
            {"key": "civitae.creator_type", "value": {"stringValue": seed.get("creator_type", "")}},
            {"key": "civitae.content_hash", "value": {"stringValue": seed.get("content_hash", "")}},
            {"key": "civitae.governance", "value": {"stringValue": "constitutional"}},
            # Constitutional state at time of action — mode, posture, tier
            {"key": "civitae.governance.mode", "value": {"stringValue": metadata.get("governance_mode", "")}},
            {"key": "civitae.governance.posture", "value": {"stringValue": metadata.get("governance_posture", "")}},
            {"key": "civitae.governance.tier", "value": {"stringValue": metadata.get("agent_tier", "")}},
            {"key": "civitae.governance.mode_raw_input", "value": {"stringValue": metadata.get("governance_mode_raw", "")}},
        ],
    }

    metadata = seed.get("metadata", {})
    for k, v in metadata.items():
        span["attributes"].append({
            "key": f"civitae.metadata.{k}",
            "value": {"stringValue": str(v)}
        })

    return span


# ── Trace Assembly ────────────────────────────────────────────────────────────

def build_trace_groups(seeds: list[dict]) -> dict[str, list[dict]]:
    """
    Group seeds into traces by lineage chain.
    Each root seed (no parent_doi) starts a new trace.
    Children are grouped under their root's trace ID.
    """
    doi_map = {s["doi"]: s for s in seeds}

    def find_root(seed):
        visited = set()
        current = seed
        while current.get("parent_doi") and current["parent_doi"] not in visited:
            visited.add(current["doi"])
            parent = doi_map.get(current["parent_doi"])
            if not parent:
                break
            current = parent
        return current["doi"]

    traces = defaultdict(list)
    for seed in seeds:
        root_doi = find_root(seed)
        trace_id = hashlib.sha256(root_doi.encode()).hexdigest()[:32]
        traces[trace_id].append(seed)

    return dict(traces)


def export_otel_traces(
    since: str = None,
    creator_type: str = None,
    anonymize: bool = False,
) -> dict:
    """
    Export all seeds as OTel-compatible trace data (OTLP JSON format).
    """
    seeds = _read_seeds()

    if since:
        seeds = [s for s in seeds if s.get("created_at", "") >= since]
    if creator_type:
        seeds = [s for s in seeds if s.get("creator_type") == creator_type]

    if anonymize:
        for seed in seeds:
            cid = seed.get("creator_id", "")
            seed["creator_id"] = hashlib.sha256(cid.encode()).hexdigest()[:12]
            meta = seed.get("metadata", {})
            for key in ["contact", "contact_email", "email"]:
                meta.pop(key, None)

    trace_groups = build_trace_groups(seeds)

    resource_spans = []
    for trace_id, trace_seeds in trace_groups.items():
        spans = [seed_to_span(s, trace_id) for s in trace_seeds]
        resource_spans.append({
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "civitae"}},
                    {"key": "service.version", "value": {"stringValue": "0.1.0"}},
                    {"key": "civitae.governance", "value": {"stringValue": "six_fold_flame"}},
                ]
            },
            "scopeSpans": [{
                "scope": {"name": "civitae.seeds", "version": "1"},
                "spans": spans
            }]
        })

    return {
        "resourceSpans": resource_spans,
        "metadata": {
            "total_traces": len(trace_groups),
            "total_spans": sum(len(g) for g in trace_groups.values()),
            "export_time": datetime.now(timezone.utc).isoformat(),
            "format": "OTLP_JSON",
            "governance": "Six Fold Flame constitutional governance",
            "source": "CIVITAE governed agent city-state",
        }
    }


# ── Hugging Face Dataset Export ───────────────────────────────────────────────

def export_hf_dataset(
    output_path: str = None,
    anonymize: bool = True,
    since: str = None,
) -> dict:
    """
    Export seeds as a Hugging Face-ready JSONL dataset.
    Always anonymizes creator_ids for public release.
    """
    if output_path is None:
        output_path = str(resolve_data_dir(_PROJECT_ROOT) / "civitae-agent-traces.jsonl")

    seeds = _read_seeds()

    if since:
        seeds = [s for s in seeds if s.get("created_at", "") >= since]

    if anonymize:
        for seed in seeds:
            cid = seed.get("creator_id", "")
            seed["creator_id"] = hashlib.sha256(cid.encode()).hexdigest()[:12]
            meta = seed.get("metadata", {})
            for key in ["contact", "contact_email", "email"]:
                meta.pop(key, None)

    trace_groups = build_trace_groups(seeds)

    records = []
    for trace_id, trace_seeds in trace_groups.items():
        trace_seeds.sort(key=lambda s: s.get("created_at", ""))

        action_types = [s.get("source_type") for s in trace_seeds]
        creator_types = set(s.get("creator_type") for s in trace_seeds)
        seed_types = [s.get("seed_type") for s in trace_seeds]

        record = {
            "trace_id": trace_id,
            "root_doi": trace_seeds[0].get("doi"),
            "span_count": len(trace_seeds),
            "action_sequence": action_types,
            "unique_actions": list(set(action_types)),
            "creator_types": list(creator_types),
            "seed_type_distribution": {
                "planted": seed_types.count("planted"),
                "touched": seed_types.count("touched"),
                "grown": seed_types.count("grown"),
            },
            "start_time": trace_seeds[0].get("created_at"),
            "end_time": trace_seeds[-1].get("created_at"),
            "governance": {
                "framework": "Six Fold Flame",
                "protocol": "MO§E§™",
                "enforcement": "constitutional_blocking",
            },
            "spans": [{
                "doi": s.get("doi"),
                "parent_doi": s.get("parent_doi"),
                "source_type": s.get("source_type"),
                "seed_type": s.get("seed_type"),
                "creator_type": s.get("creator_type"),
                "creator_id": s.get("creator_id"),
                "content_hash": s.get("content_hash"),
                "created_at": s.get("created_at"),
                "metadata": s.get("metadata", {}),
            } for s in trace_seeds]
        }
        records.append(record)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        for record in records:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

    return {
        "exported": len(records),
        "total_spans": sum(r["span_count"] for r in records),
        "output": output_path,
        "format": "jsonl",
        "anonymized": anonymize,
    }


# ── SIGRANK Metrics from Traces ───────────────────────────────────────────────

def compute_sigrank(agent_id: str) -> dict:
    """
    Compute SIGRANK behavioral composite for an agent from their seed traces.

    Five metrics compose the Transmitter Composite:
    1. Compression — metadata richness per planted seed
    2. Prompt Complexity — diversity of action types
    3. Cross-Thread Referencing — ratio of grown seeds
    4. Session Depth — avg seeds per trace
    5. Token Throughput — total planted seeds
    """
    seeds = _read_seeds()
    agent_seeds = [s for s in seeds if s.get("creator_id") == agent_id]

    if not agent_seeds:
        return {
            "agent_id": agent_id,
            "total_seeds": 0,
            "composite": None,
            "metrics": {},
            "tier_recommendation": "UNGOVERNED",
            "note": "No trace data. Agent has not performed any actions."
        }

    total = len(agent_seeds)
    planted = [s for s in agent_seeds if s.get("seed_type") == "planted"]
    touched = [s for s in agent_seeds if s.get("seed_type") == "touched"]
    grown = [s for s in agent_seeds if s.get("seed_type") == "grown"]

    # 1. Compression
    if planted:
        meta_sizes = [len(json.dumps(s.get("metadata", {}))) for s in planted]
        compression = min(1.0, sum(meta_sizes) / (len(meta_sizes) * 200))
    else:
        compression = 0.0

    # 2. Prompt Complexity
    source_types = set(s.get("source_type") for s in agent_seeds)
    prompt_complexity = min(1.0, len(source_types) / 10)

    # 3. Cross-Thread Referencing
    cross_thread = len(grown) / total if total > 0 else 0.0

    # 4. Session Depth
    trace_groups = build_trace_groups(agent_seeds)
    if trace_groups:
        avg_depth = sum(len(v) for v in trace_groups.values()) / len(trace_groups)
        session_depth = min(1.0, avg_depth / 10)
    else:
        session_depth = 0.0

    # 5. Token Throughput
    throughput = min(1.0, len(planted) / 50)

    # Composite
    weights = {
        "compression": 0.20,
        "prompt_complexity": 0.20,
        "cross_thread": 0.25,
        "session_depth": 0.15,
        "throughput": 0.20,
    }

    composite = (
        compression * weights["compression"] +
        prompt_complexity * weights["prompt_complexity"] +
        cross_thread * weights["cross_thread"] +
        session_depth * weights["session_depth"] +
        throughput * weights["throughput"]
    )

    if composite >= 0.85:
        tier = "BLACK_CARD"
    elif composite >= 0.65:
        tier = "CONSTITUTIONAL"
    elif composite >= 0.40:
        tier = "GOVERNED"
    else:
        tier = "UNGOVERNED"

    return {
        "agent_id": agent_id,
        "total_seeds": total,
        "composite": round(composite, 4),
        "metrics": {
            "compression": round(compression, 4),
            "prompt_complexity": round(prompt_complexity, 4),
            "cross_thread_referencing": round(cross_thread, 4),
            "session_depth": round(session_depth, 4),
            "token_throughput": round(throughput, 4),
        },
        "weights": weights,
        "tier_recommendation": tier,
        "breakdown": {
            "planted": len(planted),
            "touched": len(touched),
            "grown": len(grown),
            "unique_source_types": list(source_types),
            "trace_count": len(trace_groups),
        }
    }


# ── API Router ────────────────────────────────────────────────────────────────

otel_router = APIRouter()


@otel_router.get("/otel")
async def get_otel_traces(
    since: Optional[str] = Query(None),
    creator_type: Optional[str] = Query(None),
    anonymize: bool = Query(False),
):
    """Export seeds as OTel-compatible traces."""
    return export_otel_traces(since=since, creator_type=creator_type, anonymize=anonymize)


@otel_router.get("/dataset")
async def get_hf_dataset(
    since: Optional[str] = Query(None),
    anonymize: bool = Query(True),
):
    """Export seeds as Hugging Face-ready JSONL dataset."""
    result = export_hf_dataset(anonymize=anonymize, since=since)
    return result


@otel_router.get("/sigrank/{agent_id}")
async def get_sigrank(agent_id: str):
    """Compute SIGRANK behavioral composite for an agent."""
    return compute_sigrank(agent_id)


@otel_router.get("/sigrank")
async def get_all_sigrank():
    """Compute SIGRANK for all agents with trace data."""
    seeds = _read_seeds()
    agent_ids = set(
        s.get("creator_id") for s in seeds
        if s.get("creator_type") == "AAI" and s.get("creator_id")
    )
    results = {}
    for aid in agent_ids:
        results[aid] = compute_sigrank(aid)
    ranked = sorted(
        results.values(),
        key=lambda r: r.get("composite") or 0,
        reverse=True
    )
    return {
        "total_agents": len(ranked),
        "leaderboard": ranked
    }
