from __future__ import annotations

import csv
import html
from pathlib import Path
from typing import Any


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _node_label(turn: dict[str, str]) -> str:
    summary = (turn.get("summary") or turn.get("raw_text") or "").replace("\n", " ").strip()
    if len(summary) > 90:
        summary = summary[:87] + "..."
    speaker = turn.get("speaker", "")
    category = turn.get("primary_category", "")
    return f"{turn.get('turn_id','')} {speaker} [{category}]\\n{summary}".strip()


def render_mermaid(run_dir: str | Path, *, include_inactive: bool = True) -> str:
    run = Path(run_dir)
    turns = _read_csv(run / "canonical" / "turns.csv")
    edges = _read_csv(run / "canonical" / "edges.csv")
    visible = {
        turn["turn_id"]
        for turn in turns
        if include_inactive or turn.get("is_active_path", "").lower() in {"true", "1"}
    }
    lines = ["flowchart TD"]
    for turn in turns:
        turn_id = turn.get("turn_id", "")
        if turn_id not in visible:
            continue
        label = _node_label(turn).replace('"', "'")
        node = f'n_{turn_id}["{label}"]'
        lines.append("    " + node)
        if turn.get("is_active_path", "").lower() in {"true", "1"}:
            lines.append(f"    class n_{turn_id} active")
        else:
            lines.append(f"    class n_{turn_id} inactive")
    for edge in edges:
        source, target = edge.get("from_turn_id", ""), edge.get("to_turn_id", "")
        if not source or not target or source not in visible or target not in visible:
            continue
        relation = edge.get("relation") or edge.get("edge_type") or "NEXT"
        if edge.get("is_active_path", "").lower() in {"true", "1"}:
            lines.append(f"    n_{source} -->|{relation}| n_{target}")
        else:
            lines.append(f"    n_{source} -.->|{relation}| n_{target}")
    lines.extend([
        "    classDef active stroke-width:3px;",
        "    classDef inactive stroke-dasharray: 5 5;",
    ])
    return "\n".join(lines) + "\n"


def render_dot(run_dir: str | Path, *, include_inactive: bool = True) -> str:
    run = Path(run_dir)
    turns = _read_csv(run / "canonical" / "turns.csv")
    edges = _read_csv(run / "canonical" / "edges.csv")
    visible = {
        turn["turn_id"]
        for turn in turns
        if include_inactive or turn.get("is_active_path", "").lower() in {"true", "1"}
    }
    lines = ["digraph Thread {", '  rankdir="TB";', '  node [shape="box"];']
    for turn in turns:
        turn_id = turn.get("turn_id", "")
        if turn_id not in visible:
            continue
        label = _node_label(turn).replace("\\", "\\\\").replace('"', '\\"')
        style = "bold" if turn.get("is_active_path", "").lower() in {"true", "1"} else "dashed"
        lines.append(f'  "{turn_id}" [label="{label}", style="{style}"];')
    for edge in edges:
        source, target = edge.get("from_turn_id", ""), edge.get("to_turn_id", "")
        if not source or not target or source not in visible or target not in visible:
            continue
        relation = (edge.get("relation") or edge.get("edge_type") or "NEXT").replace('"', "'")
        style = "solid" if edge.get("is_active_path", "").lower() in {"true", "1"} else "dashed"
        lines.append(f'  "{source}" -> "{target}" [label="{relation}", style="{style}"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_standalone_html(run_dir: str | Path) -> str:
    """Render a dependency-free branch/path viewer for one parser run."""
    run = Path(run_dir)
    turns = _read_csv(run / "canonical" / "turns.csv")
    edges = _read_csv(run / "canonical" / "edges.csv")
    children: dict[str, list[dict[str, str]]] = {}
    for edge in edges:
        children.setdefault(edge.get("from_turn_id", ""), []).append(edge)
    incoming = {edge.get("to_turn_id", "") for edge in edges}
    roots = [turn for turn in turns if turn.get("turn_id", "") not in incoming]
    by_id = {turn.get("turn_id", ""): turn for turn in turns}

    cards = []
    for turn in turns:
        tid = turn.get("turn_id", "")
        active = turn.get("is_active_path", "").lower() in {"true", "1"}
        classes = "turn active" if active else "turn inactive"
        summary = html.escape(turn.get("summary") or "")
        raw = html.escape(turn.get("raw_text") or "")
        parent = html.escape(turn.get("parent_turn_id") or "root")
        cards.append(
            f'<article class="{classes}" data-id="{html.escape(tid)}" data-parent="{parent}" '
            f'data-speaker="{html.escape(turn.get("speaker", ""))}" data-category="{html.escape(turn.get("primary_category", ""))}">'
            f'<header><strong>{html.escape(tid)}</strong> · {html.escape(turn.get("speaker", ""))} · '
            f'{html.escape(turn.get("primary_category", ""))}</header>'
            f'<p>{summary}</p><details><summary>Raw turn</summary><pre>{raw}</pre></details>'
            f'<footer>parent: {parent} · branch: {html.escape(turn.get("branch_id", ""))}</footer></article>'
        )
    root_ids = ", ".join(root.get("turn_id", "") for root in roots)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Thread Path Map</title>
<style>
body{{font-family:ui-sans-serif,system-ui;margin:0;background:#f6f6f4;color:#171717}}
main{{max-width:1100px;margin:auto;padding:24px}} .controls{{position:sticky;top:0;background:#f6f6f4;padding:12px 0;z-index:2}}
input,select{{padding:8px;margin-right:8px}} .turn{{background:white;border:1px solid #ddd;border-left:5px solid #999;border-radius:8px;padding:14px;margin:10px 0}}
.turn.active{{border-left-width:8px}} .turn.inactive{{opacity:.66}} pre{{white-space:pre-wrap}} header,footer{{font-size:.85rem;color:#555}}
.hidden{{display:none}} code{{background:#eee;padding:2px 5px}}
</style></head><body><main>
<h1>Thread Path Map</h1><p>Root(s): <code>{html.escape(root_ids)}</code>. Bold-left cards are the active path; faded cards preserve inactive branches.</p>
<div class="controls"><input id="q" placeholder="filter text"><select id="path"><option value="all">all paths</option><option value="active">active path</option><option value="inactive">inactive branches</option></select></div>
<section id="turns">{''.join(cards)}</section>
<script>
const q=document.getElementById('q'), path=document.getElementById('path');
function filter(){{const term=q.value.toLowerCase();document.querySelectorAll('.turn').forEach(el=>{{const pathOK=path.value==='all'||el.classList.contains(path.value);const textOK=!term||el.textContent.toLowerCase().includes(term);el.classList.toggle('hidden',!(pathOK&&textOK));}})}}
q.addEventListener('input',filter);path.addEventListener('change',filter);
</script></main></body></html>"""


def write_visualizations(run_dir: str | Path, output_dir: str | Path | None = None) -> dict[str, Path]:
    run = Path(run_dir)
    out = Path(output_dir) if output_dir else run / "visualizations"
    out.mkdir(parents=True, exist_ok=True)
    outputs = {
        "mermaid": out / "thread-map.mmd",
        "dot": out / "thread-map.dot",
        "html": out / "thread-map.html",
    }
    outputs["mermaid"].write_text(render_mermaid(run), encoding="utf-8")
    outputs["dot"].write_text(render_dot(run), encoding="utf-8")
    outputs["html"].write_text(render_standalone_html(run), encoding="utf-8")
    return outputs
