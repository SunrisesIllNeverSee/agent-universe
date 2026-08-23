from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyze import analyze_thread
from .normalize import load_thread
from .report import render_report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Parse one conversation into a cited turn-by-turn journey ledger.")
    p.add_argument("input", help="Thread JSON/ChatGPT export JSON/markdown transcript")
    p.add_argument("--out", default="thread-parser-output", help="Output directory")
    p.add_argument("--thread-id", default=None, help="Optional stable thread identifier")
    p.add_argument("--title", default=None, help="Override parsed thread title")
    return p


def main() -> int:
    args = build_parser().parse_args()
    title, turns = load_thread(args.input)
    if args.title:
        title = args.title
    ledger = analyze_thread(title, turns, thread_id=args.thread_id)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "thread-ledger.json").write_text(json.dumps(ledger.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "thread-report.md").write_text(render_report(ledger), encoding="utf-8")
    print(f"Parsed {len(turns)} turns")
    print(out / "thread-ledger.json")
    print(out / "thread-report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
