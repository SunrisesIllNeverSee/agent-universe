#!/usr/bin/env python3
"""
audit_repo.py — Generate STATUS.md from git history + codebase scan.

No external dependencies. Run from repo root:
    python scripts/audit_repo.py

Produces STATUS.md at repo root.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "STATUS.md"


# ── Helpers ────────────────────────────────────────────────────────────────

def git(*args: str) -> str:
    r = subprocess.run(["git"] + list(args), capture_output=True, text=True, cwd=ROOT, timeout=30)
    return r.stdout.strip()


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Part A: Daily Operations ──────────────────────────────────────────────

def section_today() -> str:
    lines = git("log", "--since=midnight", "--format=%h %s", "--no-merges")
    if not lines:
        return f"## Today ({today_str()})\n\nNo commits today.\n"
    commits = lines.splitlines()
    out = f"## Today ({today_str()}) — {len(commits)} commits\n\n"
    for c in commits:
        out += f"- {c}\n"
    return out + "\n"


def section_week() -> str:
    lines = git("log", "--since=7 days ago", "--format=%h %s ||| %ai", "--no-merges")
    if not lines:
        return "## This Week (7 days)\n\nNo commits this week.\n"
    by_day: dict[str, list[str]] = defaultdict(list)
    for line in lines.splitlines():
        if "|||" not in line:
            continue
        msg, date_str = line.rsplit("|||", 1)
        day = date_str.strip()[:10]
        by_day[day].append(msg.strip())
    out = f"## This Week (7 days) — {sum(len(v) for v in by_day.values())} commits\n\n"
    for day in sorted(by_day.keys(), reverse=True):
        commits = by_day[day]
        out += f"### {day} ({len(commits)} commits)\n"
        for c in commits:
            out += f"- {c}\n"
        out += "\n"
    return out


def section_recent_files() -> str:
    lines = git("diff", "--name-only", "HEAD~20")
    if not lines:
        return "## Recently Modified Files (last 20 commits)\n\nNone.\n"
    files = sorted(set(f for f in lines.splitlines() if f.strip()))
    by_dir: dict[str, list[str]] = defaultdict(list)
    for f in files:
        parts = f.split("/", 1)
        d = parts[0] + "/" if len(parts) > 1 else "./"
        by_dir[d].append(parts[1] if len(parts) > 1 else parts[0])
    out = "## Recently Modified Files (last 20 commits)\n\n"
    for d in sorted(by_dir.keys()):
        out += f"**{d}**\n"
        for f in sorted(by_dir[d]):
            out += f"  {f}\n"
        out += "\n"
    return out


def section_changelog_staleness() -> str:
    cl = ROOT / "CHANGELOG.md"
    if not cl.exists():
        return "## CHANGELOG\n\nNo CHANGELOG.md found.\n"
    text = cl.read_text(encoding="utf-8")
    dates = re.findall(r"^##\s+(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
    if not dates:
        return "## CHANGELOG\n\nNo dated entries found in CHANGELOG.md.\n"
    last = dates[0]
    try:
        days_ago = (datetime.now() - datetime.strptime(last, "%Y-%m-%d")).days
    except ValueError:
        days_ago = -1
    try:
        cs = git("log", "--oneline", f"--since={last}", "--no-merges", "-200")
        commits_since = len(cs.splitlines()) if cs else 0
    except Exception:
        commits_since = "?"
    out = f"## CHANGELOG\n\n"
    out += f"Last entry: {last} ({days_ago} days ago)\n"
    out += f"Recent commits not in changelog: {commits_since}\n"
    if days_ago > 7:
        out += f"CHANGELOG is stale.\n"
    return out + "\n"


# ── Part B: Codebase Audit ────────────────────────────────────────────────

def section_frontend_pages() -> str:
    pj = ROOT / "config" / "pages.json"
    if not pj.exists():
        pj = ROOT / "frontend" / "pages.json"
    if not pj.exists():
        return "## Frontend Pages\n\nNo pages.json found.\n"
    data = json.loads(pj.read_text(encoding="utf-8"))
    counts: dict[str, int] = defaultdict(int)
    missing: list[str] = []
    all_pages: list[dict] = []

    def extract(items: list) -> None:
        for item in items:
            if isinstance(item, dict) and "status" in item:
                counts[item["status"]] += 1
                all_pages.append(item)
                f = item.get("file", "")
                if f and not (ROOT / "frontend" / f"{f}.html").exists():
                    missing.append(f"{item.get('route', '?')} -> {f}.html")

    for section in data.get("tileZero", {}).get("pages", []):
        extract([section] if isinstance(section, dict) else [])
    for layer in data.get("layers", []):
        extract(layer.get("pages", []))

    out = "## Frontend Pages\n\n"
    out += " | ".join(f"{s}: {c}" for s, c in sorted(counts.items())) + "\n\n"
    if missing:
        out += "**Missing HTML files:**\n"
        for m in missing:
            out += f"- {m}\n"
        out += "\n"

    wip = [p for p in all_pages if p.get("status") == "wip"]
    empty = [p for p in all_pages if p.get("status") == "empty"]
    if wip:
        out += "**WIP pages:**\n"
        for p in wip:
            out += f"- {p.get('route', '?')} — {p.get('name', '?')}\n"
        out += "\n"
    if empty:
        out += "**Empty pages:**\n"
        for p in empty:
            out += f"- {p.get('route', '?')} — {p.get('name', '?')}\n"
        out += "\n"
    return out


def section_endpoints() -> str:
    routes_dir = ROOT / "app" / "routes"
    if not routes_dir.exists():
        return "## API Endpoints\n\nNo app/routes/ directory.\n"
    pat = re.compile(r'@router\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']')
    by_module: dict[str, dict[str, int]] = {}
    total = 0
    for f in sorted(routes_dir.glob("*.py")):
        text = f.read_text(encoding="utf-8")
        methods: dict[str, int] = defaultdict(int)
        for m in pat.finditer(text):
            methods[m.group(1).upper()] += 1
            total += 1
        if methods:
            by_module[f.stem] = dict(methods)

    # Also check seeds, seeds_otel
    for extra in ["seeds.py", "seeds_otel.py"]:
        ep = ROOT / "app" / extra
        if ep.exists():
            text = ep.read_text(encoding="utf-8")
            methods: dict[str, int] = defaultdict(int)
            for m in pat.finditer(text):
                methods[m.group(1).upper()] += 1
                total += 1
            if methods:
                by_module[ep.stem] = dict(methods)

    out = f"## API Endpoints — {total} total\n\n"
    out += "| Module | GET | POST | PUT | PATCH | DELETE | Total |\n"
    out += "|--------|-----|------|-----|-------|--------|-------|\n"
    for mod in sorted(by_module.keys()):
        ms = by_module[mod]
        row_total = sum(ms.values())
        out += f"| {mod} | {ms.get('GET',0)} | {ms.get('POST',0)} | {ms.get('PUT',0)} | {ms.get('PATCH',0)} | {ms.get('DELETE',0)} | {row_total} |\n"
    out += f"| **Total** | | | | | | **{total}** |\n\n"
    return out


def section_seed_coverage() -> str:
    routes_dir = ROOT / "app" / "routes"
    if not routes_dir.exists():
        return ""
    pat_endpoint = re.compile(r'@router\.(post|put|patch|delete)\(\s*["\']([^"\']+)["\']')
    seeded = 0
    unseeded_list: list[str] = []
    total_state = 0
    for f in sorted(routes_dir.glob("*.py")):
        text = f.read_text(encoding="utf-8")
        for m in pat_endpoint.finditer(text):
            total_state += 1
            # Find the function body after this decorator
            start = m.end()
            chunk = text[start:start + 2000]
            if "create_seed" in chunk:
                seeded += 1
            else:
                unseeded_list.append(f"{f.stem}: {m.group(1).upper()} {m.group(2)}")

    out = f"## Seed Coverage — {seeded}/{total_state} state-changing endpoints seeded\n\n"
    if unseeded_list and len(unseeded_list) <= 30:
        out += "**Unseeded:**\n"
        for u in unseeded_list[:20]:
            out += f"- {u}\n"
        if len(unseeded_list) > 20:
            out += f"- ...and {len(unseeded_list) - 20} more\n"
        out += "\n"
    return out


def section_tests() -> str:
    tests_dir = ROOT / "tests"
    if not tests_dir.exists():
        return "## Tests\n\nNo tests/ directory.\n"
    pat = re.compile(r"^def (test_\w+)", re.MULTILINE)
    total_funcs = 0
    by_file: dict[str, int] = {}
    for f in sorted(tests_dir.glob("test_*.py")):
        text = f.read_text(encoding="utf-8")
        funcs = pat.findall(text)
        by_file[f.name] = len(funcs)
        total_funcs += len(funcs)

    out = f"## Tests — {total_funcs} test functions across {len(by_file)} files\n\n"
    for name, count in sorted(by_file.items()):
        out += f"- {name}: {count} tests\n"
    out += "\n"
    return out


# ── Summary ───────────────────────────────────────────────────────────────

def build_status() -> str:
    parts_a = [
        section_today(),
        section_week(),
        section_recent_files(),
        section_changelog_staleness(),
    ]
    parts_b = [
        section_frontend_pages(),
        section_endpoints(),
        section_seed_coverage(),
        section_tests(),
    ]

    # Count commits from already-generated sections (avoid duplicate git calls)
    today_lines = git("log", "--since=midnight", "--format=%h", "--no-merges")
    today_count = len(today_lines.splitlines()) if today_lines else 0
    week_lines = git("log", "--since=7 days ago", "--format=%h", "--no-merges")
    week_count = len(week_lines.splitlines()) if week_lines else 0

    header = f"""# SIGNOMY — Status Report
Generated: {now_str()}

## Quick View
- Today: {today_count} commits
- This week: {week_count} commits
"""

    body = "\n---\n\n# Part A: Daily Operations\n\n"
    body += "\n".join(parts_a)
    body += "\n---\n\n# Part B: Codebase Audit\n\n"
    body += "\n".join(parts_b)

    return header + body


def main() -> None:
    status = build_status()
    OUT.write_text(status, encoding="utf-8")
    # Print summary to stdout
    for line in status.splitlines()[:12]:
        print(line)
    print(f"\nFull report: {OUT}")


if __name__ == "__main__":
    main()
