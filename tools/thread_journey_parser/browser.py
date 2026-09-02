from __future__ import annotations

import argparse
import json
import sqlite3
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

from .compare import compare_threads
from .search_index import ArchiveIndex


APP_HTML = r'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thread Parser Archive</title>
<style>
:root{--bg:#f5f4ef;--panel:#fff;--ink:#171717;--muted:#666;--line:#ddd;--accent:#222}
*{box-sizing:border-box}body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system;background:var(--bg);color:var(--ink)}
header{padding:18px 24px;border-bottom:1px solid var(--line);background:var(--panel);position:sticky;top:0;z-index:5}h1{font-size:20px;margin:0 0 4px}.sub{color:var(--muted);font-size:13px}
.layout{display:grid;grid-template-columns:280px 1fr;min-height:calc(100vh - 76px)}aside{border-right:1px solid var(--line);padding:16px;background:#faf9f5}.main{padding:20px;min-width:0}
input,select,button,textarea{font:inherit;border:1px solid #bbb;border-radius:6px;padding:8px;background:white}button{cursor:pointer}button.primary{background:#222;color:#fff;border-color:#222}
.stack>*{margin-bottom:8px}.thread{display:block;width:100%;text-align:left;padding:9px;border:0;background:transparent;border-radius:6px}.thread:hover,.thread.active{background:#e9e7df}.thread small{display:block;color:var(--muted)}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}.toolbar input{min-width:280px;flex:1}.grid{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:16px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.record{border-bottom:1px solid #eee;padding:12px 0}.record:last-child{border-bottom:0}.meta{font-size:12px;color:var(--muted);margin-bottom:6px}.content{white-space:pre-wrap;overflow-wrap:anywhere}.pill{display:inline-block;border:1px solid #ccc;border-radius:999px;padding:2px 7px;font-size:11px;margin:2px}.pill.user{font-weight:700}.tag{background:#efeee8}.hidden{display:none}.empty{color:var(--muted);padding:20px 0}
pre{white-space:pre-wrap;overflow:auto;background:#f6f6f6;padding:10px;border-radius:6px}.section-title{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:16px 0 8px}.compare-list label{display:block;margin:5px 0}@media(max-width:900px){.layout{grid-template-columns:1fr}aside{border-right:0;border-bottom:1px solid var(--line)}.grid{grid-template-columns:1fr}.toolbar input{min-width:0}}
</style></head>
<body><header><h1>Thread Parser Archive</h1><div class="sub">Local archive browser · search, filter, tag, collect, compare · parser state remains read-only</div></header>
<div class="layout"><aside><div class="section-title">Threads</div><div id="threads" class="stack"></div><div class="section-title">Collections</div><div id="collections" class="stack"></div></aside>
<main class="main"><div class="toolbar"><input id="q" placeholder="Search turns, items, documents"><select id="type"><option value="">all records</option><option>turn</option><option>item</option><option>document</option></select><input id="tagFilter" placeholder="tag filter"><button class="primary" id="searchBtn">Search</button></div>
<div class="grid"><section class="panel"><div id="context"></div><div id="results"></div></section><aside class="panel"><div id="detail"><div class="empty">Select a record.</div></div></aside></div></main></div>
<script>
let selectedThread='',selectedRecord='';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,opts){const r=await fetch(path,opts);if(!r.ok)throw new Error(await r.text());return r.json()}
function pill(text,cls=''){return text?`<span class="pill ${cls}">${esc(text)}</span>`:''}
async function loadThreads(){const data=await api('/api/threads');const el=document.getElementById('threads');el.innerHTML=data.map(t=>`<button class="thread ${t.thread_id===selectedThread?'active':''}" onclick="chooseThread('${esc(t.thread_id)}')"><b>${esc(t.thread_id)}</b><small>${t.records} records · ${t.turns} turns</small></button>`).join('')||'<div class="empty">No indexed threads.</div>';renderCompare(data)}
async function loadCollections(){const data=await api('/api/collections');document.getElementById('collections').innerHTML=data.map(c=>`<button class="thread" onclick="showCollection('${esc(c.name)}')"><b>${esc(c.name)}</b><small>${c.members} records</small></button>`).join('')||'<div class="empty">No collections.</div>'}
async function chooseThread(id){selectedThread=id;await loadThreads();document.getElementById('context').innerHTML=`<h2>${esc(id)}</h2><div class="toolbar"><button onclick="browseThread()">Browse thread</button><button onclick="showThreadProfile()">Profile</button></div>`;await browseThread()}
async function browseThread(){const q=new URLSearchParams({thread_id:selectedThread,limit:'500'});const rows=await api('/api/records?'+q);renderRows(rows)}
async function doSearch(){const q=new URLSearchParams({q:document.getElementById('q').value,type:document.getElementById('type').value,tag:document.getElementById('tagFilter').value,thread_id:selectedThread,limit:'200'});const rows=await api('/api/search?'+q);renderRows(rows)}
function renderRows(rows){const el=document.getElementById('results');el.innerHTML=rows.map(r=>`<article class="record" onclick="showRecord('${esc(r.record_key)}')"><div class="meta">${pill(r.record_type)} ${pill(r.target_id)} ${pill(r.speaker,r.speaker==='USER'?'user':'')} ${pill(r.category)} ${pill(r.authority)} ${pill(r.status)}</div><b>${esc(r.title||r.record_key)}</b><div class="content">${esc((r.content||'').slice(0,650))}</div></article>`).join('')||'<div class="empty">No matches.</div>'}
async function showRecord(key){selectedRecord=key;const r=await api('/api/record?key='+encodeURIComponent(key));const tags=(r.tags||[]).map(t=>pill(t,'tag')).join(' ');const cols=(r.collections||[]).map(c=>pill(c)).join(' ');document.getElementById('detail').innerHTML=`<div class="meta">${esc(r.record_key)}</div><h3>${esc(r.title)}</h3><div>${tags}</div><pre>${esc(r.content||'')}</pre><div class="section-title">Tags</div><div class="toolbar"><input id="newTag" placeholder="tag"><button onclick="addTag()">Add</button></div><div class="section-title">Collections</div><div>${cols||'none'}</div><div class="toolbar"><input id="newCollection" placeholder="collection"><button onclick="addCollection()">Add</button></div>`}
async function addTag(){const tag=document.getElementById('newTag').value.trim();if(!tag)return;await api('/api/tag',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({record_key:selectedRecord,tag})});await showRecord(selectedRecord);await loadCollections()}
async function addCollection(){const name=document.getElementById('newCollection').value.trim();if(!name)return;await api('/api/collection/add',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({record_key:selectedRecord,name})});await showRecord(selectedRecord);await loadCollections()}
async function showCollection(name){const rows=await api('/api/collection?name='+encodeURIComponent(name));selectedThread='';document.getElementById('context').innerHTML=`<h2>Collection: ${esc(name)}</h2>`;renderRows(rows);await loadThreads()}
async function showThreadProfile(){const data=await api('/api/compare?threads='+encodeURIComponent(selectedThread+','+selectedThread));document.getElementById('results').innerHTML=`<pre>${esc(JSON.stringify(data.profiles?.[0]||{},null,2))}</pre>`}
function renderCompare(threads){let box=document.getElementById('compareBox');if(!box){box=document.createElement('div');box.id='compareBox';document.querySelector('aside').appendChild(box)}box.innerHTML=`<div class="section-title">Compare threads</div><div class="compare-list">${threads.map(t=>`<label><input type="checkbox" value="${esc(t.thread_id)}"> ${esc(t.thread_id)}</label>`).join('')}</div><button onclick="compareSelected()">Compare</button>`}
async function compareSelected(){const ids=[...document.querySelectorAll('#compareBox input:checked')].map(x=>x.value);if(ids.length<2){alert('Select at least two threads');return}const data=await api('/api/compare?threads='+encodeURIComponent(ids.join(',')));document.getElementById('context').innerHTML='<h2>Multi-thread comparison</h2>';document.getElementById('results').innerHTML=`<pre>${esc(JSON.stringify(data,null,2))}</pre>`}
document.getElementById('searchBtn').addEventListener('click',doSearch);document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')doSearch()});loadThreads();loadCollections();
</script></body></html>'''


class ArchiveBrowserHandler(BaseHTTPRequestHandler):
    server_version = "ThreadParserArchive/0.1"

    @property
    def index(self) -> ArchiveIndex:
        return self.server.archive_index  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: object) -> None:
        if getattr(self.server, "quiet", False):  # type: ignore[attr-defined]
            return
        super().log_message(format, *args)

    def _json(self, payload: Any, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self, text: str) -> None:
        data = text.encode()
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        if parsed.path == "/":
            self._html(APP_HTML)
            return
        try:
            if parsed.path == "/api/threads":
                rows = self.index.conn.execute(
                    """SELECT thread_id,COUNT(*) records,
                              SUM(CASE WHEN record_type='turn' THEN 1 ELSE 0 END) turns,
                              SUM(CASE WHEN record_type='item' THEN 1 ELSE 0 END) items,
                              SUM(CASE WHEN record_type='document' THEN 1 ELSE 0 END) documents
                       FROM records GROUP BY thread_id ORDER BY thread_id"""
                ).fetchall()
                self._json([dict(row) for row in rows]); return
            if parsed.path == "/api/records":
                thread_id = q.get("thread_id", [""])[0]
                limit = min(int(q.get("limit", ["200"])[0]), 2000)
                rows = self.index.conn.execute(
                    "SELECT * FROM records WHERE (?='' OR thread_id=?) ORDER BY timestamp,record_key LIMIT ?",
                    (thread_id, thread_id, limit),
                ).fetchall()
                self._json([dict(row) for row in rows]); return
            if parsed.path == "/api/search":
                self._json(self.index.search(
                    q.get("q", [""])[0],
                    thread_id=q.get("thread_id", [""])[0] or None,
                    record_type=q.get("type", [""])[0] or None,
                    tag=q.get("tag", [""])[0] or None,
                    limit=min(int(q.get("limit", ["100"])[0]), 1000),
                )); return
            if parsed.path == "/api/record":
                key = q.get("key", [""])[0]
                row = self.index.conn.execute("SELECT * FROM records WHERE record_key=?", (key,)).fetchone()
                if not row:
                    self._json({"error": "not found"}, 404); return
                payload = dict(row)
                payload["tags"] = [r[0] for r in self.index.conn.execute("SELECT tag FROM tags WHERE record_key=? ORDER BY tag", (key,)).fetchall()]
                payload["collections"] = [r[0] for r in self.index.conn.execute("SELECT collection_name FROM collection_members WHERE record_key=? ORDER BY collection_name", (key,)).fetchall()]
                self._json(payload); return
            if parsed.path == "/api/collections":
                rows = self.index.conn.execute(
                    """SELECT c.name,c.description,COUNT(m.record_key) members FROM collections c
                       LEFT JOIN collection_members m ON m.collection_name=c.name GROUP BY c.name ORDER BY c.name"""
                ).fetchall()
                self._json([dict(row) for row in rows]); return
            if parsed.path == "/api/collection":
                self._json(self.index.collection(q.get("name", [""])[0])); return
            if parsed.path == "/api/compare":
                ids = [x for x in q.get("threads", [""])[0].split(",") if x]
                if len(ids) == 1:
                    ids = ids + ids
                self._json(compare_threads(self.index.conn, ids)); return
            self._json({"error": "not found"}, 404)
        except (ValueError, KeyError, sqlite3.Error) as exc:
            self._json({"error": str(exc)}, 400)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            body = self._body()
            if parsed.path == "/api/tag":
                self.index.add_tag(str(body["record_key"]), str(body["tag"]))
                self._json({"ok": True}); return
            if parsed.path == "/api/collection/add":
                self.index.add_to_collection(str(body["name"]), str(body["record_key"]))
                self._json({"ok": True}); return
            if parsed.path == "/api/collection/create":
                self.index.create_collection(str(body["name"]), str(body.get("description", "")))
                self._json({"ok": True}); return
            self._json({"error": "not found"}, 404)
        except (ValueError, KeyError, sqlite3.Error, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, 400)


def serve_archive(
    db_path: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
    quiet: bool = False,
) -> None:
    index = ArchiveIndex(db_path)
    server = ThreadingHTTPServer((host, port), ArchiveBrowserHandler)
    server.archive_index = index  # type: ignore[attr-defined]
    server.quiet = quiet  # type: ignore[attr-defined]
    url = f"http://{host}:{port}/"
    print(f"Thread Parser archive browser: {url}")
    print("Local-only by default. Ctrl-C to stop.")
    if open_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()
        index.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local Thread Parser archive browser.")
    parser.add_argument("db", help="Archive SQLite database")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", dest="open_browser")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    serve_archive(args.db, host=args.host, port=args.port, open_browser=args.open_browser, quiet=args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
