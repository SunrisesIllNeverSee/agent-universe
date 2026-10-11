#!/usr/bin/env python3
"""Stdlib check: manifest cited headings exist in frozen contracts, hashes match, pages are offline/complete."""
import hashlib, json, re, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
M = json.loads((OUT / "manifest.json").read_text())
CW = Path(M["control_workspace_root"])
fails, checks = [], 0

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(s): return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())

heads = {}
for k, v in M["frozen_contracts"].items():
    p = CW / v["file"]; checks += 1
    if sha(p) != v["sha256"]: fails.append(f"frozen contract hash mismatch {k}")
    heads[k] = [l for l in p.read_text().splitlines() if l.startswith("#")]

def heading_ok(contract, section):
    m = re.match(r"§([\w.]+)\s*(.*)", section)
    if not m: return False
    num, title = m[1], re.sub(r"\(.*?\)", "", m[2]).strip()
    for h in heads[contract]:
        hm = re.match(r"#+\s*(?:§)?\s*([\w.]+?)\.?\s+(.*)", h)
        if hm and hm[1] == num and norm(title)[:25] in norm(hm[2]):
            return True
    return False

def check_cites(label, cites):
    global checks
    for c in cites:
        checks += 1
        if not heading_ok(c["contract"], c["section"]): fails.append(f"{label}: heading not found {c['contract']} {c['section']}")

for p in M["pages"] + [M["decision_board"]]:
    label = p.get("id", "board")
    check_cites(label, p["cited_contract_headings"])
    f = OUT / p["file"]; checks += 1
    if not f.exists(): fails.append(f"missing page {f}"); continue
    h = f.read_text()
    for need in ("PROPOSAL", "P2_FINAL", "PENDING"):
        checks += 1
        if need not in h: fails.append(f"{label}: page lacks '{need}'")
    for a in p["acceptance_criteria"]:
        checks += 1
        if a not in h: fails.append(f"{label}: AC {a} not on page")
    checks += 1
    if re.search(r'(src|href)="https?://', h) or "url(http" in h: fails.append(f"{label}: external reference found")
    for m in p.get("masters", []) + p.get("supplementary_display_files", []):
        checks += 1
        mp = CW / m["path"]
        if not mp.exists(): fails.append(f"{label}: master missing {m['path']}")
        elif sha(mp) != m["sha256"]: fails.append(f"{label}: master hash mismatch {m['path']}")
        elif m["sha256"] not in h: fails.append(f"{label}: page does not display master sha {m['path']}")

ex = (OUT / "Q8-Q9-exhibit.html").read_text(); checks += 1
for need in ("PROPOSAL", "P2_FINAL", "PENDING", "Town Hall != formal Governance", "ORIENT", "WORLD", "no tenth primary mode"):
    if need not in ex.replace("&gt;", ">"): fails.append(f"exhibit lacks '{need}'")
if re.search(r'(src|href)="https?://', ex) or "/Users/" in ex: fails.append("exhibit: external ref or local path")
if 'Q8-Q9-exhibit.html' not in (OUT / "index.html").read_text(): fails.append("index lacks exhibit link")

for s in ("Rank/Refinery", "Switchboard", "Enterprise Entity Node"):
    checks += 1
    if s not in M["no_original_master"]: fails.append(f"no-master list missing {s}")
checks += 1
if "NO ORIGINAL MASTER" not in (OUT / "DG6.html").read_text(): fails.append("DG6 lacks NO ORIGINAL MASTER label")

print(f"pages: {len(M['pages'])} + decision board; checks run: {checks}")
for f in fails: print("FAIL:", f)
print("RESULT:", "FAIL" if fails else "PASS")
sys.exit(1 if fails else 0)
