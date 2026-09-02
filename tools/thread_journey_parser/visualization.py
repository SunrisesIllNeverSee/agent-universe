from __future__ import annotations

import csv
import html
import json
from pathlib import Path


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
        lines.append(f'    n_{turn_id}["{label}"]')
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
    lines.extend(["    classDef active stroke-width:3px;", "    classDef inactive stroke-dasharray: 5 5;"])
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
    """Render an interactive, dependency-free SVG conversation tree.

    Parent/child topology is visually primary. Active-path nodes/edges are emphasized;
    inactive branches remain visible and inspectable. Clicking a node exposes the raw
    turn and parser metadata without changing any stored state.
    """
    run = Path(run_dir)
    turns = _read_csv(run / "canonical" / "turns.csv")
    edges = _read_csv(run / "canonical" / "edges.csv")
    turn_json = json.dumps(turns, ensure_ascii=False).replace("</", "<\\/")
    edge_json = json.dumps(edges, ensure_ascii=False).replace("</", "<\\/")
    title = "Thread Path Map"
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>
:root{{--bg:#f5f4ef;--panel:#fff;--ink:#171717;--muted:#666;--line:#d8d6cf;--active:#111;--inactive:#9b9b95}}
*{{box-sizing:border-box}}body{{margin:0;font-family:ui-sans-serif,system-ui;background:var(--bg);color:var(--ink)}}header{{padding:16px 20px;background:var(--panel);border-bottom:1px solid var(--line)}}h1{{margin:0;font-size:20px}}.sub{{font-size:12px;color:var(--muted)}}main{{display:grid;grid-template-columns:minmax(0,1fr) 360px;height:calc(100vh - 70px)}}#viewport{{overflow:auto;position:relative}}#detail{{border-left:1px solid var(--line);padding:16px;background:var(--panel);overflow:auto}}svg{{min-width:100%;min-height:100%}}.edge{{fill:none;stroke:#aaa;stroke-width:1.5}}.edge.active{{stroke:#222;stroke-width:3}}.edge.inactive{{stroke-dasharray:5 5}}.node rect{{fill:white;stroke:#aaa;stroke-width:1.5;rx:8}}.node.active rect{{stroke:#111;stroke-width:3}}.node.inactive{{opacity:.68}}.node text{{font-size:11px;pointer-events:none}}.node{{cursor:pointer}}.label{{font-size:9px;fill:#666}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f4f2;padding:10px;border-radius:6px}}.toolbar{{display:flex;gap:8px;padding:10px 12px;background:#faf9f5;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:3}}input,select{{font:inherit;padding:7px;border:1px solid #bbb;border-radius:6px;background:white}}input{{min-width:240px;flex:1}}@media(max-width:900px){{main{{grid-template-columns:1fr}}#detail{{border-left:0;border-top:1px solid var(--line);max-height:45vh}}}}
</style></head><body><header><h1>{title}</h1><div class="sub">Topology + chronology · active path emphasized · abandoned branches preserved</div></header>
<div class="toolbar"><input id="filter" placeholder="Filter visible nodes"><select id="scope"><option value="all">all paths</option><option value="active">active path</option><option value="inactive">inactive branches</option></select></div>
<main><section id="viewport"><svg id="graph"></svg></section><aside id="detail"><p>Select a turn.</p></aside></main>
<script>
const turns={turn_json}; const edges={edge_json};
const byId=Object.fromEntries(turns.map(t=>[t.turn_id,t]));
const parentEdges=edges.filter(e=>(e.edge_type||'').toUpperCase()==='PARENT_CHILD');
const children={{}}; const parents={{}};
for(const e of parentEdges){{(children[e.from_turn_id]??=[]).push(e.to_turn_id);parents[e.to_turn_id]=e.from_turn_id}}
const roots=turns.map(t=>t.turn_id).filter(id=>!parents[id]);
const pos={{}}; let leaf=0;
function place(id,depth){{const kids=(children[id]||[]).filter(k=>byId[k]); if(!kids.length){{pos[id]={{x:40+depth*280,y:40+leaf++*120}};return pos[id].y}} const ys=kids.map(k=>place(k,depth+1)); const y=ys.reduce((a,b)=>a+b,0)/ys.length; pos[id]={{x:40+depth*280,y}}; return y}}
for(const r of roots)place(r,0);
const maxX=Math.max(900,...Object.values(pos).map(p=>p.x+250)); const maxY=Math.max(600,...Object.values(pos).map(p=>p.y+100));
const svg=document.getElementById('graph'); svg.setAttribute('viewBox',`0 0 ${{maxX}} ${{maxY}}`); svg.setAttribute('width',maxX); svg.setAttribute('height',maxY);
const NS='http://www.w3.org/2000/svg';
function el(name,attrs={{}}){{const n=document.createElementNS(NS,name);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n}}
for(const e of parentEdges){{if(!pos[e.from_turn_id]||!pos[e.to_turn_id])continue;const a=pos[e.from_turn_id],b=pos[e.to_turn_id];const active=String(e.is_active_path).toLowerCase()==='true'||String(e.is_active_path)==='1';const p=el('path',{{d:`M ${{a.x+210}} ${{a.y+32}} C ${{a.x+245}} ${{a.y+32}}, ${{b.x-35}} ${{b.y+32}}, ${{b.x}} ${{b.y+32}}`,class:`edge ${{active?'active':'inactive'}}`}});svg.appendChild(p)}}
for(const t of turns){{if(!pos[t.turn_id])continue;const p=pos[t.turn_id];const active=String(t.is_active_path).toLowerCase()==='true'||String(t.is_active_path)==='1';const g=el('g',{{class:`node ${{active?'active':'inactive'}}`,'data-id':t.turn_id}});g.appendChild(el('rect',{{x:p.x,y:p.y,width:210,height:66}}));const tx=el('text',{{x:p.x+10,y:p.y+18}});const line1=el('tspan',{{x:p.x+10,dy:0}});line1.textContent=`${{t.turn_id}} · ${{t.speaker||''}} · ${{t.primary_category||''}}`;tx.appendChild(line1);const line2=el('tspan',{{x:p.x+10,dy:17}});line2.textContent=(t.summary||'').slice(0,32);tx.appendChild(line2);const line3=el('tspan',{{x:p.x+10,dy:15}});line3.textContent=(t.summary||'').slice(32,64);tx.appendChild(line3);g.appendChild(tx);g.addEventListener('click',()=>show(t));svg.appendChild(g)}}
function esc(s){{return String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function show(t){{document.getElementById('detail').innerHTML=`<h3>${{esc(t.turn_id)}} · ${{esc(t.speaker)}}</h3><p><b>Category:</b> ${{esc(t.primary_category)}}<br><b>Authority:</b> ${{esc(t.authority_type)}}<br><b>Branch:</b> ${{esc(t.branch_id)}}<br><b>Parent:</b> ${{esc(t.parent_turn_id||'root')}}</p><pre>${{esc(t.raw_text||'')}}</pre>`}}
function applyFilter(){{const q=document.getElementById('filter').value.toLowerCase();const scope=document.getElementById('scope').value;document.querySelectorAll('.node').forEach(n=>{{const t=byId[n.dataset.id];const text=(t.turn_id+' '+t.speaker+' '+t.primary_category+' '+t.raw_text).toLowerCase();const scopeOK=scope==='all'||n.classList.contains(scope);n.style.display=(scopeOK&&(!q||text.includes(q)))?'':'none'}})}}
document.getElementById('filter').addEventListener('input',applyFilter);document.getElementById('scope').addEventListener('change',applyFilter);
</script></body></html>'''


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
