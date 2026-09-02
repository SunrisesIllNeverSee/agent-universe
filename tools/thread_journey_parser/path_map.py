from __future__ import annotations

import csv
import html
from pathlib import Path


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _safe_id(value: str) -> str:
    return "N_" + "".join(ch if ch.isalnum() else "_" for ch in value)


def render_mermaid(run_dir: str | Path) -> str:
    """Render preserved parent/child topology with active-path flow annotations."""
    run = Path(run_dir)
    canonical = run / "canonical"
    turns = _rows(canonical / "turns.csv")
    edges = _rows(canonical / "edges.csv")
    by_id = {row.get("turn_id", ""): row for row in turns}

    lines = ["flowchart TD"]
    for turn in turns:
        turn_id = turn.get("turn_id", "")
        if not turn_id:
            continue
        speaker = turn.get("speaker", "")
        summary = (turn.get("summary") or turn.get("raw_text") or "").replace("\n", " ")[:70]
        summary = summary.replace('"', "'")
        active = str(turn.get("is_active_path", "")).lower() in {"true", "1", "yes"}
        scope = "active" if active else "branch"
        label = f"{turn_id} · {speaker} · {scope}<br/>{summary}"
        lines.append(f'    {_safe_id(turn_id)}["{label}"]')

    seen: set[tuple[str, str, str]] = set()
    for edge in edges:
        source = edge.get("from_turn_id", "")
        target = edge.get("to_turn_id", "")
        if not source or not target or source not in by_id or target not in by_id:
            continue
        relation = edge.get("relation") or edge.get("edge_type") or "parent"
        signature = (source, target, relation)
        if signature in seen:
            continue
        seen.add(signature)
        lines.append(f"    {_safe_id(source)} -->|{relation}| {_safe_id(target)}")

    return "\n".join(lines) + "\n"


def render_dot(run_dir: str | Path) -> str:
    run = Path(run_dir)
    canonical = run / "canonical"
    turns = _rows(canonical / "turns.csv")
    edges = _rows(canonical / "edges.csv")
    by_id = {row.get("turn_id", ""): row for row in turns}
    lines = ["digraph thread {", "  rankdir=TB;", "  node [shape=box];"]
    for turn in turns:
        tid = turn.get("turn_id", "")
        if not tid:
            continue
        label = f"{tid} {turn.get('speaker','')}\\n{(turn.get('summary') or '')[:80]}"
        label = label.replace('"', "\\\"")
        lines.append(f'  "{tid}" [label="{label}"];')
    for edge in edges:
        source, target = edge.get("from_turn_id", ""), edge.get("to_turn_id", "")
        if source in by_id and target in by_id:
            relation = (edge.get("relation") or edge.get("edge_type") or "parent").replace('"', "'")
            lines.append(f'  "{source}" -> "{target}" [label="{relation}"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_path_report(run_dir: str | Path) -> str:
    run = Path(run_dir)
    canonical = run / "canonical"
    turns = _rows(canonical / "turns.csv")
    edges = _rows(canonical / "edges.csv")
    active = [r for r in turns if str(r.get("is_active_path", "")).lower() in {"true", "1", "yes"}]
    branches = [r for r in turns if r not in active]
    flow_edges = [e for e in edges if e.get("relation") and e.get("relation") != "PARENT_CHILD"]
    lines = [
        "# Thread Path Map",
        "",
        f"- Archived turns: **{len(turns)}**",
        f"- Active-path turns: **{len(active)}**",
        f"- Preserved off-path turns: **{len(branches)}**",
        f"- Interpreted flow edges: **{len(flow_edges)}**",
        "",
        "## Active path",
        "",
    ]
    for turn in active:
        lines.append(
            f"- **{turn.get('turn_id')} · {turn.get('speaker')}** — {(turn.get('summary') or '')[:200]}"
        )
    if branches:
        lines.extend(["", "## Preserved branches", ""])
        for turn in branches:
            lines.append(
                f"- **{turn.get('turn_id')}** ← parent `{turn.get('parent_turn_id') or 'root'}` — {(turn.get('summary') or '')[:160]}"
            )
    if flow_edges:
        lines.extend(["", "## Flow transitions", ""])
        for edge in flow_edges:
            lines.append(
                f"- `{edge.get('from_turn_id')}` → `{edge.get('to_turn_id')}`: **{edge.get('relation')}** "
                f"(confidence {edge.get('confidence') or '?'})"
            )
    return "\n".join(lines) + "\n"


def write_path_maps(run_dir: str | Path, out_dir: str | Path | None = None) -> dict[str, Path]:
    run = Path(run_dir)
    target = Path(out_dir) if out_dir is not None else run / "maps"
    target.mkdir(parents=True, exist_ok=True)
    outputs = {
        "mermaid": target / "thread-tree.mmd",
        "dot": target / "thread-tree.dot",
        "report": target / "path-map.md",
    }
    outputs["mermaid"].write_text(render_mermaid(run), encoding="utf-8")
    outputs["dot"].write_text(render_dot(run), encoding="utf-8")
    outputs["report"].write_text(render_path_report(run), encoding="utf-8")
    return outputs
