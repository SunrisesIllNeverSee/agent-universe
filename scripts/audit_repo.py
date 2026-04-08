#!/usr/bin/env python3
"""
audit_repo.py — CIVITAE daily repo audit
Generates STATUS.md at the repo root using stdlib only.
Usage: python3 scripts/audit_repo.py
"""

import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATUS_FILE = REPO_ROOT / "STATUS.md"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git(*args, check=False):
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT)] + list(args),
        capture_output=True, text=True, check=check
    )
    return result.stdout.strip()


def section(title, char="="):
    bar = char * len(title)
    return f"\n{bar}\n{title}\n{bar}\n"


# ---------------------------------------------------------------------------
# A1 — Today's commits
# ---------------------------------------------------------------------------

def a1_today_commits():
    out = git("log", "--since=midnight", "--format=%h %s", "--no-merges")
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return "A1: Today's Commits", "(none yet today)"
    body = "\n".join(f"  {l}" for l in lines)
    return "A1: Today's Commits", body


# ---------------------------------------------------------------------------
# A2 — This week's commits grouped by date
# ---------------------------------------------------------------------------

def a2_week_commits():
    since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    out = git("log", f"--since={since}", "--format=%ad %h %s", "--date=short", "--no-merges")
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return "A2: This Week's Commits", "(none)"
    by_date = {}
    for line in lines:
        parts = line.split(" ", 2)
        if len(parts) < 3:
            continue
        date, sha, msg = parts
        by_date.setdefault(date, []).append(f"  {sha} {msg}")
    rows = []
    for date in sorted(by_date.keys(), reverse=True):
        rows.append(f"\n  {date}")
        rows.extend(by_date[date])
    return "A2: This Week's Commits", "\n".join(rows)


# ---------------------------------------------------------------------------
# A3 — Recently modified files (last 3 days), grouped by directory
# ---------------------------------------------------------------------------

def a3_recent_files():
    out = git("log", "--since=3.days", "--name-only", "--format=", "--no-merges")
    files = sorted(set(l for l in out.splitlines() if l.strip()))
    if not files:
        return "A3: Recently Modified Files (3 days)", "(none)"
    by_dir = {}
    for f in files:
        p = Path(f)
        d = str(p.parent) if str(p.parent) != "." else "(root)"
        by_dir.setdefault(d, []).append(p.name)
    rows = []
    for d in sorted(by_dir.keys()):
        rows.append(f"\n  {d}/")
        for name in sorted(by_dir[d]):
            rows.append(f"    {name}")
    return "A3: Recently Modified Files (3 days)", "\n".join(rows)


# ---------------------------------------------------------------------------
# A4 — TODO tracker: check "not built yet" items for code evidence
# ---------------------------------------------------------------------------

NOT_BUILT = [
    ("Fee Credit Pack backend",  ["fee_credit", "fee-credit", "credit_pack", "credit_balance"]),
    ("Seed Card",                ["seed_card", "SeedCard", "streak", "badge_assign"]),
    ("Sliding Scale Reward",     ["sliding_scale", "SlidingScale", "reward_engine"]),
    ("Phase transition logic",   ["phase_transition", "day_1", "day_8", "day_31"]),
    ("Founder badge auto-assign",["founding_contributor", "FoundingContributor"]),
    ("Cascade Matcher",          ["cascade_match", "CascadeMatcher"]),
    ("Operator auth flow",       ["operator_login", "operator_auth", "operator_jwt"]),
    ("Refinery/SIGRANK",         ["sigrank", "Refinery", "SIGRANK"]),
    ("Switchboard",              ["Switchboard", "switchboard"]),
    ("GPT/Gemini/DeepSeek/Grok", ["gpt_agent", "gemini_agent", "deepseek", "grok_agent"]),
    ("Chain adapter execution",  ["chain_execute", "ChainAdapter", "execute_chain"]),
]

def a4_todo_tracker():
    app_dir = REPO_ROOT / "app"
    rows = []
    for label, keywords in NOT_BUILT:
        found = []
        for py_file in app_dir.rglob("*.py"):
            try:
                content = py_file.read_text(errors="ignore")
            except Exception:
                continue
            for kw in keywords:
                if kw.lower() in content.lower():
                    found.append(py_file.relative_to(REPO_ROOT))
                    break
        if found:
            hits = ", ".join(str(f) for f in found[:3])
            rows.append(f"  [PARTIAL] {label} — found in: {hits}")
        else:
            rows.append(f"  [MISSING] {label}")
    return "A4: TODO Tracker (Not Built Yet)", "\n".join(rows)


# ---------------------------------------------------------------------------
# A5 — Test count
# ---------------------------------------------------------------------------

def a5_test_count():
    tests_dir = REPO_ROOT / "tests"
    if not tests_dir.exists():
        return "A5: Test Count", "(no tests/ directory)"
    test_files = list(tests_dir.glob("test_*.py"))
    total_funcs = 0
    rows = []
    for tf in sorted(test_files):
        content = tf.read_text(errors="ignore")
        n = len(re.findall(r"^\s+def test_", content, re.MULTILINE))
        total_funcs += n
        rows.append(f"  {tf.name}: {n} tests")
    rows.append(f"\n  Total test functions: {total_funcs}")
    rows.append(f"  Total test files: {len(test_files)}")
    return "A5: Test Count", "\n".join(rows)


# ---------------------------------------------------------------------------
# B1 — Frontend pages from pages.json
# ---------------------------------------------------------------------------

def b1_frontend_pages():
    pages_json = REPO_ROOT / "config" / "pages.json"
    if not pages_json.exists():
        return "B1: Frontend Pages", "(config/pages.json not found)"
    try:
        data = json.loads(pages_json.read_text())
    except Exception as e:
        return "B1: Frontend Pages", f"(parse error: {e})"

    status_counts = {}
    all_pages = []

    def collect(layer):
        for item in layer:
            if isinstance(item, dict):
                status = item.get("status", "unknown")
                name = item.get("name", item.get("label", "?"))
                route = item.get("route", item.get("path", ""))
                status_counts[status] = status_counts.get(status, 0) + 1
                all_pages.append((status, name, route))
                for sub in item.get("subLinks", []):
                    if isinstance(sub, dict):
                        s = sub.get("status", "unknown")
                        n = sub.get("name", sub.get("label", "?"))
                        r = sub.get("route", sub.get("path", ""))
                        status_counts[s] = status_counts.get(s, 0) + 1
                        all_pages.append((s, n, r))

    # tileZero
    tile = data.get("tileZero")
    if tile and isinstance(tile, dict):
        status = tile.get("status", "unknown")
        name = tile.get("name", "?")
        route = tile.get("route", "")
        status_counts[status] = status_counts.get(status, 0) + 1
        all_pages.append((status, name, route))

    for layer in data.get("layers", []):
        pages = layer.get("pages", layer.get("navLinks", []))
        collect(pages)

    total = len(all_pages)
    rows = [f"  Total pages tracked: {total}"]
    for status in ["live", "wip", "empty", "planned", "admin", "unknown"]:
        count = status_counts.get(status, 0)
        if count:
            rows.append(f"  {status}: {count}")
    return "B1: Frontend Pages (from pages.json)", "\n".join(rows)


# ---------------------------------------------------------------------------
# B2 — API endpoint count from app/routes/*.py
# ---------------------------------------------------------------------------

def b2_endpoint_count():
    routes_dir = REPO_ROOT / "app" / "routes"
    if not routes_dir.exists():
        return "B2: API Endpoints", "(app/routes/ not found)"

    decorator_pattern = re.compile(
        r'@\w+\.(get|post|put|patch|delete|head|options|websocket)\s*\(', re.IGNORECASE
    )
    rows = []
    grand_total = 0
    for py_file in sorted(routes_dir.glob("*.py")):
        content = py_file.read_text(errors="ignore")
        matches = decorator_pattern.findall(content)
        count = len(matches)
        grand_total += count
        if count:
            rows.append(f"  {py_file.name}: {count} endpoints")
    rows.append(f"\n  Grand total: {grand_total} endpoints")
    return "B2: API Endpoints (by route module)", "\n".join(rows)


# ---------------------------------------------------------------------------
# B3 — Test file and function summary
# ---------------------------------------------------------------------------

def b3_test_summary():
    tests_dir = REPO_ROOT / "tests"
    if not tests_dir.exists():
        return "B3: Test Summary", "(no tests/ directory)"
    test_files = list(tests_dir.glob("test_*.py"))
    total_funcs = sum(
        len(re.findall(r"^\s+def test_", f.read_text(errors="ignore"), re.MULTILINE))
        for f in test_files
    )
    body = f"  Test files: {len(test_files)}\n  Test functions: {total_funcs}"
    return "B3: Test Summary", body


# ---------------------------------------------------------------------------
# Summary block
# ---------------------------------------------------------------------------

def build_summary(today_count, week_count, endpoint_count, page_count, test_count):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"Generated: {now}",
        f"",
        f"  Commits today:      {today_count}",
        f"  Commits this week:  {week_count}",
        f"  API endpoints:      {endpoint_count}",
        f"  Frontend pages:     {page_count}",
        f"  Test functions:     {test_count}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Collect all sections
    a1_title, a1_body = a1_today_commits()
    a2_title, a2_body = a2_week_commits()
    a3_title, a3_body = a3_recent_files()
    a4_title, a4_body = a4_todo_tracker()
    a5_title, a5_body = a5_test_count()

    b1_title, b1_body = b1_frontend_pages()
    b2_title, b2_body = b2_endpoint_count()
    b3_title, b3_body = b3_test_summary()

    # Quick counts for summary block
    today_count = len([l for l in a1_body.splitlines() if l.strip() and not l.startswith("(")])
    week_lines = [l for l in a2_body.splitlines() if l.strip().startswith("  ") and len(l.strip()) > 8 and not l.strip().startswith("2026")]
    week_count = len(week_lines)

    endpoint_match = re.search(r"Grand total:\s*(\d+)", b2_body)
    endpoint_count = endpoint_match.group(1) if endpoint_match else "?"

    page_match = re.search(r"Total pages tracked:\s*(\d+)", b1_body)
    page_count = page_match.group(1) if page_match else "?"

    test_match = re.search(r"Total test functions:\s*(\d+)", a5_body)
    test_count = test_match.group(1) if test_match else "?"

    # Build STATUS.md
    out = []
    out.append("# CIVITAE — STATUS.md")
    out.append(f"> Auto-generated by scripts/audit_repo.py")
    out.append("")
    out.append("```")
    out.append(build_summary(today_count, week_count, endpoint_count, page_count, test_count))
    out.append("```")

    out.append(section("PART A — Daily Operations", "-"))

    out.append(f"\n### {a1_title}\n")
    out.append(a1_body)

    out.append(f"\n### {a2_title}\n")
    out.append(a2_body)

    out.append(f"\n### {a3_title}\n")
    out.append(a3_body)

    out.append(f"\n### {a4_title}\n")
    out.append(a4_body)

    out.append(f"\n### {a5_title}\n")
    out.append(a5_body)

    out.append(section("PART B — Codebase Audit", "-"))

    out.append(f"\n### {b1_title}\n")
    out.append(b1_body)

    out.append(f"\n### {b2_title}\n")
    out.append(b2_body)

    out.append(f"\n### {b3_title}\n")
    out.append(b3_body)

    STATUS_FILE.write_text("\n".join(out) + "\n")
    print(f"STATUS.md written to {STATUS_FILE}")

    # Print summary to stdout
    print("")
    print("=== SUMMARY ===")
    print(build_summary(today_count, week_count, endpoint_count, page_count, test_count))
    print("")
    print("=== A4: TODO TRACKER ===")
    print(a4_body)


if __name__ == "__main__":
    main()
