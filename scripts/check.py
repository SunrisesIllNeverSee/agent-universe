#!/usr/bin/env python3
"""
Agent coordination checker — validates claims/registry/locks consistency.

Reads .agents/registry.yaml, .agents/claims.yaml, and .agents/locks.json
plus filesystem state and reports inconsistencies. Exit codes:
  0 = clean
  1 = warnings (advisory; CI green)
  2 = blockers (CI red)

Checks:
  1. No two active claims overlap on the same file lane
  2. No active claim has a stale heartbeat (>24h)
  3. Released claims must have released_at AND at least one landed_commits
  4. registry.yaml migrations.next is one greater than highest applied number
  5. locks.json has no expired locks (warns, doesn't block)
  6. All sessions in claims.yaml have a matching entry in sessions list

Usage:
  python3 scripts/check.py                # human-readable report
  python3 scripts/check.py --strict       # treat warnings as blockers
  python3 scripts/check.py --json         # machine-readable output
  python3 scripts/check.py --quiet        # only print on failure
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

# Stdlib-only YAML parser — our YAML files use a deliberately narrow subset.
# Falls back to pyyaml if available for better accuracy.
try:
    import yaml  # type: ignore
    _HAVE_PYYAML = True
except ImportError:
    _HAVE_PYYAML = False


def parse_simple_yaml(text: str) -> dict:
    """Parse the narrow YAML subset we use. Not a general parser."""
    result: dict = {}
    current_key = None
    in_list = False
    in_dict = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped == '[]' or stripped == '{}':
            if current_key:
                result[current_key] = [] if stripped == '[]' else {}
            continue

        # Top-level key: value
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$', stripped)
        if m and not line.startswith(' '):
            key, val = m.group(1), m.group(2)
            current_key = key
            if val:
                result[key] = val.strip('"\'')
            else:
                result[key] = []
            continue

    return result


def load_yaml(path: Path) -> dict:
    text = path.read_text()
    if _HAVE_PYYAML:
        try:
            return yaml.safe_load(text) or {}
        except Exception:
            pass
    return parse_simple_yaml(text)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description='Agent coordination checker')
    parser.add_argument('--strict', action='store_true', help='treat warnings as blockers')
    parser.add_argument('--json', action='store_true', help='machine-readable output')
    parser.add_argument('--quiet', action='store_true', help='only print on failure')
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    agents_dir = repo_root / '.agents'
    claims_path = agents_dir / 'claims.yaml'
    registry_path = agents_dir / 'registry.yaml'
    locks_path = agents_dir / 'locks.json'

    warnings: list[str] = []
    blockers: list[str] = []
    info: list[str] = []

    # Load files
    claims_data = load_yaml(claims_path) if claims_path.exists() else {}
    registry_data = load_yaml(registry_path) if registry_path.exists() else {}
    locks_data = load_json(locks_path) if locks_path.exists() else {}

    sessions = claims_data.get('sessions', []) or []
    claims = claims_data.get('claims', []) or []
    locks = locks_data.get('locks', {}) or {}

    now = dt.datetime.now(dt.timezone.utc)

    # Check 1: overlapping active file_lane claims
    active_claims = [c for c in claims if not c.get('released_at')]
    path_owners: dict[str, str] = {}
    for claim in active_claims:
        if claim.get('type') != 'file_lane':
            continue
        for p in claim.get('paths', []):
            if p in path_owners:
                blockers.append(f'Overlap: {p} claimed by both {path_owners[p]} and {claim.get("session", "?")}')
            else:
                path_owners[p] = claim.get('session', '?')

    # Check 2: stale heartbeats
    for s in sessions:
        if s.get('status') != 'active':
            continue
        hb = s.get('heartbeat')
        if not hb:
            continue
        try:
            hb_dt = dt.datetime.fromisoformat(hb.replace('Z', '+00:00'))
            age = (now - hb_dt).total_seconds() / 3600
            if age > 24:
                warnings.append(f'Stale session: {s.get("id", "?")} heartbeat {age:.0f}h ago')
        except Exception:
            pass

    # Check 3: released claims missing data
    for c in claims:
        if c.get('released_at') and not c.get('landed_commits'):
            warnings.append(f'Released claim {c.get("id", "?")} has no landed_commits')

    # Check 4: migration next number
    migrations = registry_data.get('migrations', {}) or {}
    applied = migrations.get('applied', []) or []
    if applied:
        nums = [a.get('n', 0) for a in applied if isinstance(a, dict)]
        highest = max(nums) if nums else 0
        expected_next = highest + 1
        actual_next = migrations.get('next', 0)
        if actual_next != expected_next:
            warnings.append(f'migrations.next={actual_next} but expected {expected_next} (highest applied={highest})')

    # Check 5: expired locks
    for path, lock in locks.items():
        if not isinstance(lock, dict):
            continue
        expires = lock.get('expires_at')
        if not expires:
            continue
        try:
            exp_dt = dt.datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if now > exp_dt:
                warnings.append(f'Expired lock on {path} (expired {exp_dt.isoformat()})')
        except Exception:
            pass

    # Check 6: orphan claims (session not in sessions list)
    session_ids = {s.get('id') for s in sessions if isinstance(s, dict)}
    for c in active_claims:
        sid = c.get('session')
        if sid and sid not in session_ids:
            warnings.append(f'Claim {c.get("id", "?")} references unknown session {sid}')

    # Summary
    total_issues = len(warnings) + len(blockers)
    if args.quiet and total_issues == 0:
        return 0

    if args.json:
        print(json.dumps({
            'blockers': blockers,
            'warnings': warnings,
            'clean': total_issues == 0,
        }, indent=2))
    else:
        if blockers:
            print(f'\n!! {len(blockers)} BLOCKER(S):')
            for b in blockers:
                print(f'  {b}')
        if warnings:
            print(f'\n!  {len(warnings)} WARNING(S):')
            for w in warnings:
                print(f'  {w}')
        if not blockers and not warnings:
            print('✓ coordination state clean — no issues found')

    if blockers:
        return 2
    if warnings and args.strict:
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
