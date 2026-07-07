#!/usr/bin/env python3
"""
MO§ES™ Three-Researcher Crew Test

Three governed agents collaborate on a research topic under SCOUT posture:

  Turn 1 — LUTHEN (Primary)   frames the landscape, initial research
  Turn 2 — K-2SO  (Secondary) digs deep, evidence, counterarguments
  Turn 3 — HANGE  (Observer)  synthesizes everything into the final report

Each agent registers with Agent Universe, fills a governed slot, and runs
their LLM call with MO§ES™ governance injected into the system prompt.
The full run is captured in the audit trail at /api/audit.

Usage:
  export ANTHROPIC_API_KEY="sk-ant-..."
  cd /path/to/agent-universe
  python3 tests/crew_research.py
  python3 tests/crew_research.py "What is decentralized AI governance?"
  python3 tests/crew_research.py --host http://localhost:8300 --topic "AI sovereignty"
  python3 tests/crew_research.py --dry-run   # skips LLM calls, tests backend only

© 2026 Ello Cello LLC · Patent Pending: Serial No. 63/877,177
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

# ── Config ─────────────────────────────────────────────────────────────────────
BASE_URL = os.environ.get("COMMAND_URL", "http://localhost:8300")
API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL    = os.environ.get("CLAUDE_MODEL", "claude-opus-4-5")

DEFAULT_TOPIC = (
    "What is MO§ES™ sovereign AI governance, how does the Conservation Law "
    "C(T(S)) = C(S) work, and what problems does this solve for autonomous "
    "AI agent systems operating at scale?"
)

# ── Three Researcher Personas ───────────────────────────────────────────────────
CREW = [
    {
        "name":        "zeke-strategist",
        "role":        "primary",
        "persona":     "Zeke Yeager",
        "seq":         1,
        "posture":     "SCOUT",
        "description": (
            "Campaign Strategist. Frames the research question from a high-altitude view. "
            "Sees the whole board — alliances, leverage points, long-game implications. "
            "Calm, calculating, always three moves ahead."
        ),
        "task": (
            "You are the LEAD researcher (Campaign Strategist role).\n\n"
            "Your job:\n"
            "1. Frame the research question from a strategic standpoint\n"
            "2. Map the key forces, stakeholders, and leverage points\n"
            "3. Provide your initial strategic assessment (~350 words)\n"
            "4. List exactly 3 specific intelligence gaps for the Analyst to fill\n\n"
            "Think in systems. Identify what controls the outcome."
        ),
    },
    {
        "name":        "micro-analyst",
        "role":        "secondary",
        "persona":     "Micro",
        "seq":         2,
        "posture":     "SCOUT",
        "description": (
            "Intelligence Analyst and technical deep-diver. Finds the evidence others miss. "
            "Digs into data, patterns, and technical details. Connects the dots that look "
            "unrelated. Precise, methodical, leaves no thread unpulled."
        ),
        "task": (
            "You are the ANALYST (Intelligence role).\n\n"
            "The Strategist has mapped the landscape above. Your job:\n"
            "1. Fill the 3 intelligence gaps with specific evidence and data\n"
            "2. Identify what the Strategist missed or didn't have intel on\n"
            "3. Find the technical or operational details that change the picture (~350 words)\n"
            "4. Hand the Writer exactly 3 verified findings to anchor the report\n\n"
            "Evidence over assertion. Technical precision matters."
        ),
    },
    {
        "name":        "nebula-validator",
        "role":        "observer",
        "persona":     "Nebula",
        "seq":         3,
        "posture":     "SCOUT",
        "description": (
            "Pattern Validator and final synthesizer. Identifies signal from noise across "
            "all the material. Relentless about accuracy — will not let bad data or "
            "unverified claims pass into the final output. Produces the definitive report."
        ),
        "task": (
            "You are the VALIDATOR. The Strategist and Analyst have done their work above.\n\n"
            "Write the FINAL RESEARCH REPORT. Structure it for operational use:\n\n"
            "# [Precise Title — no fluff]\n\n"
            "## Situation Report\n"
            "(3-4 sentences — verified facts only, what they mean)\n\n"
            "## Validated Findings\n"
            "(4-5 bullet points — cross-referenced from both prior researchers)\n\n"
            "## Pattern Analysis\n"
            "(2-3 paragraphs — what the data actually shows, where patterns hold, "
            "where they break)\n\n"
            "## Operational Implications\n"
            "(What this demands in practice. Where the gaps remain.)\n\n"
            "## Verdict\n"
            "(1 sentence. No hedging. No qualifications.)\n\n"
            "~500 words. Validate everything. Pass nothing you can't confirm."
        ),
    },
]


# ── HTTP helpers ─────────────────────────────────────────────────────────────────
def api(method: str, path: str, **kwargs) -> dict:
    """Call the Agent Universe backend."""
    url = f"{BASE_URL}{path}"
    try:
        r = httpx.request(method, url, timeout=15, **kwargs)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        print(f"  ⚠  HTTP {e.response.status_code} on {path}: {e.response.text[:200]}")
        return {}
    except httpx.ConnectError:
        print(f"  ✗  Cannot connect to {BASE_URL}")
        print(f"     Is the backend running? → python3 run.py")
        return {}
    except Exception as e:
        print(f"  ⚠  {path}: {e}")
        return {}


def check_backend() -> bool:
    """Quick health check before starting."""
    resp = api("GET", "/api/state")
    return bool(resp)


def register_agent(agent: dict) -> str:
    """Register agent with AU backend. Returns agent_id (or a fallback)."""
    resp = api("POST", "/api/provision/signup", json={
        "name": agent["name"],
        "type": "agent",
        "system": "claude",
        "role": agent["role"],
    })
    agent_id = resp.get("agent_id")
    status = resp.get("status", "?")

    # If already exists, try to get their ID
    if not agent_id and "already registered" in str(resp.get("error", "")):
        existing_id = resp.get("agent_id", f"anon-{agent['name']}")
        print(f"    ↩  {agent['name']} already registered → {existing_id}")
        return existing_id

    if agent_id:
        print(f"    ✓  {agent['name']} ({agent['persona']}) → {agent_id} [{status}]")
    else:
        fallback = f"anon-{agent['name']}"
        print(f"    ~  {agent['name']} registration unclear → using {fallback}")
        return fallback

    return agent_id


def create_research_slots(mission_id: str, label: str) -> list[dict]:
    """Create 3 governed SCOUT slots for this research mission."""
    resp = api("POST", "/api/slots/create", json={
        "mission_id":    mission_id,
        "formation_id":  "three-researcher",
        "label":         label,
        "posture":       "SCOUT",
        "governance_mode": "STANDARD",
        "positions": [
            {"row": 0, "col": 0},
            {"row": 0, "col": 1},
            {"row": 0, "col": 2},
        ],
        "roles":           ["primary", "secondary", "observer"],
        "revenue_splits":  [40, 35, 25],
    })
    return resp.get("slots", [])


def fill_slot(slot_id: str, agent_id: str, agent_name: str) -> dict:
    return api("POST", "/api/slots/fill", json={
        "slot_id":    slot_id,
        "agent_id":   agent_id,
        "agent_name": agent_name,
    })


# ── Governed LLM call ────────────────────────────────────────────────────────────
def call_claude_governed(
    agent:   dict,
    slot:    dict,
    topic:   str,
    history: list[str],
) -> str:
    """
    Make a governed Claude call for this researcher's turn.
    Governance context from the slot is injected into the system prompt.
    Previous researchers' outputs are threaded as message history.
    """
    gov      = slot.get("governance", {})
    gov_mode = gov.get("mode", "STANDARD")
    posture  = gov.get("posture", "SCOUT")

    system = "\n".join([
        "You are operating under MO§ES™ constitutional governance.",
        f"Mode: {gov_mode} | Posture: {posture}",
        f"Role: {agent['role'].upper()} (researcher {agent['seq']} of 3)",
        f"Persona: {agent['persona']}",
        f"Identity: {agent['description']}",
        "",
        "SCOUT posture: gather and analyze information only.",
        "No state changes. No transactions. Every response is audited.",
        "",
        "─── YOUR TASK ───",
        agent["task"],
    ])

    # Build message history — previous researchers' outputs feed forward
    messages: list[dict] = []

    if not history:
        # LEAD: just the raw topic
        messages.append({"role": "user", "content": f"Research topic: {topic}"})
    else:
        # Thread prior outputs as context, then ask this agent to perform their role
        prior_context_parts = [f"Research topic: {topic}", ""]
        for i, prev_output in enumerate(history):
            prior_context_parts.append(f"=== {CREW[i]['persona']} ({CREW[i]['role']}) ===")
            prior_context_parts.append(prev_output.strip())
            prior_context_parts.append("")
        prior_context_parts.append(
            f"=== Now it is your turn, {agent['persona']}. Perform your role. ==="
        )
        messages.append({"role": "user", "content": "\n".join(prior_context_parts)})

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":          API_KEY,
                "anthropic-version":  "2023-06-01",
                "content-type":       "application/json",
            },
            json={
                "model":      MODEL,
                "max_tokens": 1500,
                "system":     system,
                "messages":   messages,
            },
            timeout=90,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    except httpx.HTTPStatusError as e:
        return f"[{agent['persona']} LLM ERROR] HTTP {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"[{agent['persona']} LLM ERROR] {e}"


# ── Main crew run ─────────────────────────────────────────────────────────────────
def run_crew(topic: str, dry_run: bool = False, output_file: Path | None = None) -> None:
    width = 62
    print(f"\n{'═' * width}")
    print(f"  MO§ES™  THREE-RESEARCHER CREW")
    print(f"  {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    if dry_run:
        print(f"  DRY RUN — LLM calls skipped")
    print(f"{'═' * width}")
    print(f"\n  Topic: {topic[:80]}\n")

    # ── 0. Backend health check ───────────────────────────────────────────────
    print("Checking backend...")
    if not check_backend():
        print(f"\n  ✗ Backend not reachable at {BASE_URL}")
        print(f"    Start it:  python3 run.py")
        sys.exit(1)
    print(f"  ✓ Backend live at {BASE_URL}\n")

    # ── 1. Register agents ────────────────────────────────────────────────────
    print("Step 1 — Registering agents...")
    agent_ids: dict[str, str] = {}
    for agent in CREW:
        aid = register_agent(agent)
        agent_ids[agent["name"]] = aid
    print()

    # ── 2. Create mission + slots ─────────────────────────────────────────────
    mission_id = f"research-{int(time.time())}"
    label = f"RESEARCH: {topic[:52]}"
    print(f"Step 2 — Creating mission: {mission_id}")
    slots = create_research_slots(mission_id, label)
    if not slots:
        print("  ✗ Slot creation failed — check backend logs")
        sys.exit(1)
    print(f"  ✓ {len(slots)} SCOUT slots created")
    print()

    # ── 3. Fill slots ─────────────────────────────────────────────────────────
    print("Step 3 — Filling slots...")
    filled_slots: dict[str, dict] = {}
    for i, agent in enumerate(CREW):
        slot = slots[i] if i < len(slots) else {}
        aid  = agent_ids[agent["name"]]
        result = fill_slot(slot.get("id", ""), aid, agent["name"])
        filled_slots[agent["name"]] = slot

        if result.get("filled"):
            gov_mode    = result.get("governance_applied", {}).get("mode", "?")
            gov_posture = result.get("governance_applied", {}).get("posture", "?")
            print(f"  ✓ {agent['persona']:<14} [{agent['role']:<10}] [{gov_mode}/{gov_posture}]")
        else:
            print(f"  ~ {agent['persona']:<14} [{agent['role']:<10}] (slot pre-assigned)")
    print()

    # ── 4. Run research turns ──────────────────────────────────────────────────
    print(f"Step 4 — Running governed research ({MODEL})...\n")
    outputs  = []
    history  = []
    turn_labels = ["LEAD RESEARCH", "DEEP ANALYSIS", "FINAL REPORT"]

    for i, agent in enumerate(CREW):
        slot = filled_slots.get(agent["name"], {})
        print(f"{'─' * width}")
        print(f"  Turn {i+1}/3 — {agent['persona']}  ·  {turn_labels[i]}")
        print(f"{'─' * width}")

        if dry_run or not API_KEY:
            output = (
                f"[DRY RUN — {agent['persona']}]\n"
                f"Role: {agent['role']} | Slot: {slot.get('id','N/A')}\n"
                f"Governance: {slot.get('governance', {})}\n"
                f"Task would be: {agent['task'][:120]}..."
            )
        else:
            print(f"  Calling {MODEL}...")
            output = call_claude_governed(agent, slot, topic, history)

        history.append(output)
        outputs.append({
            "turn":     i + 1,
            "agent":    agent["name"],
            "persona":  agent["persona"],
            "role":     agent["role"],
            "slot_id":  slot.get("id", ""),
            "gov":      slot.get("governance", {}),
            "output":   output,
        })

        # Print preview (first 10 lines)
        lines   = output.strip().split("\n")
        preview = "\n".join(f"  {line}" for line in lines[:10])
        print(preview)
        if len(lines) > 10:
            print(f"  ... [{len(lines) - 10} more lines]")
        print()

    # ── 5. Save report ────────────────────────────────────────────────────────
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    if output_file is None:
        data_dir = Path(__file__).resolve().parents[1] / "data"
        data_dir.mkdir(exist_ok=True)
        output_file = data_dir / f"crew_{timestamp}.md"

    # Markdown report
    def section(turn_idx: int) -> str:
        if turn_idx >= len(outputs):
            return "_No output_"
        return outputs[turn_idx]["output"]

    report_md = f"""# MO§ES™ Research Report

**Topic:** {topic}
**Date:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}
**Mission:** `{mission_id}`
**Model:** `{MODEL}`
**Governance:** STANDARD / SCOUT posture

---

## Turn 1 — {CREW[0]['persona']} (Lead Research)

{section(0)}

---

## Turn 2 — {CREW[1]['persona']} (Deep Analysis)

{section(1)}

---

## Final Report — {CREW[2]['persona']} (Synthesis)

{section(2)}

---

*Generated by MO§ES™ Agent Universe · Three-Researcher formation*
*© 2026 Ello Cello LLC · Patent Pending: Serial No. 63/877,177*
"""

    output_file.write_text(report_md)

    # Raw JSON for analysis / replay
    json_file = output_file.with_suffix(".json")
    json_file.write_text(json.dumps({
        "topic":      topic,
        "mission_id": mission_id,
        "timestamp":  timestamp,
        "model":      MODEL,
        "dry_run":    dry_run,
        "crew":       [{"name": a["name"], "persona": a["persona"], "role": a["role"]} for a in CREW],
        "turns":      outputs,
    }, indent=2))

    print(f"{'═' * width}")
    print(f"  ✓ Report:       {output_file}")
    print(f"  ✓ Raw JSON:     {json_file}")
    print(f"  ✓ Mission:      {mission_id}")
    print(f"  ✓ Audit trail:  {BASE_URL}/api/audit")
    print(f"{'═' * width}\n")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MO§ES™ Three-Researcher Crew Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default=DEFAULT_TOPIC,
        help="Research topic (default: MO§ES™ governance overview)",
    )
    parser.add_argument("--host",    default=BASE_URL,   help="COMMAND URL (default: http://localhost:8300)")
    parser.add_argument("--model",   default=MODEL,      help="Claude model")
    parser.add_argument("--output",  type=Path,          help="Output .md file path")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM calls — test backend only")
    args = parser.parse_args()

    BASE_URL = args.host
    MODEL    = args.model

    run_crew(
        topic       = args.topic,
        dry_run     = args.dry_run,
        output_file = args.output,
    )
