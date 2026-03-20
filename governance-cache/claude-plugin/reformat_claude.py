#!/usr/bin/env python3
"""
reformat_claude.py — Clean up Claude.ai exported conversation markdown.

Removes duplicate thinking-title lines, preserves artifact references
(formatted as callout blocks), and converts date separators to headers.

Usage:
    python3 reformat_claude.py <file.md>
    python3 reformat_claude.py *.md          # multiple files

Output: <input_stem>_clean.md written next to the original (never overwrites).
"""

import re
import sys
from pathlib import Path

DATE_RE = re.compile(r"^\s*Mar\s+\d+\s*$")
ARTIFACT_TYPE_RE = re.compile(r"^(Document|Code|Image)\s+[·•]\s+\w+\s*$")


def clean_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Convert date lines to markdown section headers
        if DATE_RE.match(line):
            # Avoid double blank lines before header
            if out and out[-1].strip():
                out.append("")
            out.append(f"## {line.strip()}")
            out.append("")
            i += 1
            continue

        # Format artifact reference pairs as callout blocks and keep them
        # Pattern: artifact title line followed by "Document · MD" / "Code · JSX" etc.
        if i + 1 < len(lines) and ARTIFACT_TYPE_RE.match(lines[i + 1].strip()):
            title = line.strip()
            artifact_type = lines[i + 1].strip()
            if out and out[-1].strip():
                out.append("")
            out.append(f"> 📎 **{title}** *({artifact_type})*")
            out.append("")
            i += 2
            continue

        # Remove duplicate thinking-title pairs (same non-empty line repeated back-to-back)
        if (
            line.strip()
            and i + 1 < len(lines)
            and line == lines[i + 1]
        ):
            i += 2  # skip both occurrences of the thinking title
            continue

        out.append(line)
        i += 1

    # Collapse runs of 3+ blank lines into 2
    result: list[str] = []
    blank_run = 0
    for line in out:
        if not line.strip():
            blank_run += 1
            if blank_run <= 2:
                result.append(line)
        else:
            blank_run = 0
            result.append(line)

    return result


def process_file(filepath: str) -> None:
    path = Path(filepath)
    if not path.exists():
        print(f"  ✗ Not found: {path}")
        return

    lines = path.read_text(encoding="utf-8").splitlines()
    cleaned = clean_lines(lines)

    # Build output path: same dir, stem + _clean, same extension
    out_path = path.parent / (path.stem + "_clean" + path.suffix)
    out_path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")

    orig = len(lines)
    new = len(cleaned)
    pct = (1 - new / orig) * 100 if orig else 0
    print(f"  ✓ {out_path.name}  ({orig} → {new} lines, {pct:.0f}% reduction)")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 reformat_claude.py <file.md> [file2.md ...]")
        sys.exit(1)

    for arg in args:
        process_file(arg)


if __name__ == "__main__":
    main()
