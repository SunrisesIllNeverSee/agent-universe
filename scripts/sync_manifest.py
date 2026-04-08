"""
sync_manifest.py — Sync governance logic + taxonomy into public agent.json and llms.txt

Run from repo root:
    python scripts/sync_manifest.py

Reads:
    config/taxonomy.json       — action taxonomy with min_tier + risk_weight
    app/moses_core/governance  — MODE_ALIASES, POSTURES

Writes:
    frontend/agent.json        — machine-readable platform manifest
    frontend/llms.txt          — plain-text LLM discovery file
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.moses_core.governance import MODE_ALIASES, POSTURES, MODES


def load_json(path: Path) -> dict:
    if not path.exists():
        print(f"WARNING: {path} not found, skipping.")
        return {}
    return json.loads(path.read_text())


def sync_manifests():
    taxonomy = load_json(ROOT / "config" / "taxonomy.json")
    existing_agent = load_json(ROOT / "frontend" / "agent.json")

    # Build governance section from live code
    governance_section = {
        "modes": list(MODE_ALIASES.keys()),
        "postures": {k: v["behavior"] for k, v in POSTURES.items()},
        "taxonomy": taxonomy.get("categories", {}),
        "taxonomy_version": taxonomy.get("version", "unknown"),
    }

    # Merge into existing agent.json — preserve all existing fields
    existing_agent["governance_protocol"] = governance_section
    existing_agent["taxonomy_version"] = taxonomy.get("version", "unknown")

    agent_path = ROOT / "frontend" / "agent.json"
    agent_path.write_text(json.dumps(existing_agent, indent=2, ensure_ascii=False))
    print(f"✓ {agent_path.relative_to(ROOT)} updated")

    # Update llms.txt — append taxonomy section
    llms_path = ROOT / "frontend" / "llms.txt"
    content = llms_path.read_text() if llms_path.exists() else ""

    # Strip old taxonomy block if present, then append fresh one
    marker = "\n## Action Taxonomy (MO§ES)\n"
    if marker in content:
        content = content[:content.index(marker)]

    taxonomy_block = marker
    taxonomy_block += "_Categories define minimum trust tier required per action type._\n\n"
    for cat, data in taxonomy.get("categories", {}).items():
        taxonomy_block += f"- **{cat}**: Requires `{data['min_tier']}` tier · Risk {data['risk_weight']}\n"
        taxonomy_block += f"  Keywords: {', '.join(data['keywords'][:6])}{'...' if len(data['keywords']) > 6 else ''}\n"

    governance_block = "\n## Governance Modes\n"
    governance_block += "_Ambiguous or unknown mode input defaults to High Security (fail-safe)._\n\n"
    for alias, canonical in MODE_ALIASES.items():
        governance_block += f"- `{alias}` → {canonical}\n"

    content = content.rstrip() + taxonomy_block + governance_block + "\n"
    llms_path.write_text(content)
    print(f"✓ {llms_path.relative_to(ROOT)} updated")

    print("\nSync complete.")
    print(f"  Taxonomy categories: {len(taxonomy.get('categories', {}))}")
    print(f"  Governance modes:    {len(MODE_ALIASES)}")


if __name__ == "__main__":
    sync_manifests()
