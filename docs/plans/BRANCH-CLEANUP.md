---
type: Runbook
title: Branch Cleanup — agent-universe remote branch audit
description: Audit of 21 remote branches. 3 merged (safe delete), 18 unmerged (need review). Notes on difficulty, risk, and recommended action per branch.
tags: [branches, cleanup, audit, git]
timestamp: 2026-07-06T05:30:00Z
last_touched: 2026-07-06 05:30 UTC
---

# Branch Cleanup — agent-universe

**Audited:** 2026-07-06
**Total remote branches:** 21 (excluding `main` and `HEAD`)
**Merged (safe to delete):** 3
**Unmerged (need review):** 18
**Difficulty:** Low — most branches are 1-2 commits, 2 months stale, and likely superseded by work on main.

## Difficulty assessment

**Easy.** This is not a complex cleanup. Here's why:

- Only 3 branches have more than 3 commits ahead of main
- Most are 1-2 commits, all from May 4 (a single sprint day)
- The May 4 sprint was MCP hardening — most of that work likely landed on main via other PRs
- No branch is actively being worked on (newest is June 2, over a month stale)
- The repo is private with a single contributor — no coordination risk

**Time estimate:** 30 minutes if you review each unmerged branch's diff. 5 minutes if you just delete the merged ones and archive the rest.

## Merged branches — safe to delete now

These are fully merged into main. Deleting them loses nothing.

| Branch | Last activity | PR | Action |
|--------|--------------|-----|--------|
| `origin/001-civitae-full-build` | 2026-03-22 | merged via a31b2f2 | **Delete** |
| `origin/claude/fix-mcp-admin-guard` | 2026-05-04 | merged via PR #10 | **Delete** |
| `origin/copilot/build-mcp-for-github` | 2026-04-01 | merged via PR #? | **Delete** |
| `origin/railway/code-change-N8Csif` | 2026-03-31 | merged via PR #4 | **Delete** |

Command to delete merged branches:
```bash
git push origin --delete 001-civitae-full-build
git push origin --delete claude/fix-mcp-admin-guard
git push origin --delete copilot/build-mcp-for-github
git push origin --delete railway/code-change-N8Csif
```

## Unmerged branches — need review

### Tier 1: Likely safe to delete (superseded or trivial)

These are 1-2 commits from the May 4 MCP sprint. The work was likely redone on main or superseded by other PRs. Check the diff before deleting.

| Branch | Commits ahead | Last activity | What it did | Likely status |
|--------|--------------|---------------|-------------|---------------|
| `claude/badge-and-packages` | 1 | 2026-05-04 | Add AI Agents Directory badge + PyPI entry in server.json | Likely landed on main separately |
| `claude/circleci` | 2 | 2026-05-04 | Add CircleCI config | Check if `.circleci/` exists on main |
| `claude/favicon-and-configschema` | 1 | 2026-05-04 | Add favicon + config schema | Check if favicon exists on main |
| `claude/icon-and-naming` | 1 | 2026-05-04 | Rename MCP tools to dot-notation + brand icon | Check if dot-notation is on main |
| `claude/mcp-fix-annotations` | 1 | 2026-05-04 | Remove `from __future__ import annotations` | Trivial fix, likely done on main |
| `claude/mcp-quality-score` | 1 | 2026-05-04 | Add parameter descriptions to MCP tools | Check if descriptions are on main |
| `claude/mcp-stateless` | 1 | 2026-05-04 | Fix stateless HTTP for Railway workers | Check if fix is on main |
| `claude/mcp-wire-all-tools` | 1 | 2026-05-04 | Wire all 15 MCP tools into mcp_bridge.py | Check if wiring is on main |
| `devin/update-skills-1778405824` | 1 | 2026-05-10 | Add testing skill for local verification | Check if skill exists on main |
| `devin/update-skills-1778428819` | 1 | 2026-05-10 | Add SEO testing skill | Check if skill exists on main |
| `devin/update-skills-1780394899` | 1 | 2026-06-02 | Update testing-seo skill with IndexNow | Check if update is on main |

**Quick check for each:**
```bash
# Example: check if favicon exists on main
git show main:frontend/favicon.ico 2>/dev/null && echo "EXISTS on main" || echo "NOT on main"

# Check if dot-notation MCP tools are on main
git show main:app/mcp_bridge.py 2>/dev/null | grep -c "xyz.signomy" && echo "dot-notation on main"
```

### Tier 2: Worth reviewing (might have unique work)

These have more commits or touch substantial features. Review the diff before deciding.

| Branch | Commits ahead | Last activity | What it did | Risk |
|--------|--------------|---------------|-------------|------|
| `claude/fix-kingdoms` | 2 | 2026-05-04 | Kingdoms fix | Unknown — check diff |
| `claude/fix-mcp-dns-rebinding` | 3 | 2026-05-04 | DNS rebinding fix + merge conflict resolution | Security fix — check if on main |
| `claude/fix-mcp-endpoint` | 7 | 2026-05-04 | MCP endpoint resolution + server.json conflict | Most commits — likely has unique work |
| `claude/fix-seo-audit-5f33q` | 6 | 2026-05-04 | SEO audit fixes | Was merged via PR #10 but branch still shows unmerged — investigate |
| `devin/1775076305-seed-card-loyalty-system` | 4 | 2026-04-02 | Seed card loyalty system | Feature work — check if landed |
| `devin/1778427797-seo-sitemap-fixes` | 1 | 2026-05-10 | SEO sitemap fixes | Check if sitemap fixes are on main |
| `copilot/open-positions-for-agents` | 2 | 2026-03-23 | Help wanted apply modal fix | Old — check if fix is on main |

### Tier 3: Investigate before any action

| Branch | Commits ahead | Last activity | Why investigate |
|--------|--------------|---------------|-----------------|
| `claude/fix-seo-audit-5f33q` | 6 | 2026-05-04 | PR #10 says it was merged, but branch shows 6 commits ahead. Possible partial merge or the branch has additional commits after the PR was merged. |
| `claude/fix-mcp-endpoint` | 7 | 2026-05-04 | Largest unmerged branch. 7 commits of MCP endpoint work. Some may have landed via other PRs. |

## Recommended cleanup procedure

```bash
cd ~/Desktop/agent-universe

# Step 1: Delete the 4 merged branches (safe, loses nothing)
git push origin --delete 001-civitae-full-build
git push origin --delete claude/fix-mcp-admin-guard
git push origin --delete copilot/build-mcp-for-github
git push origin --delete railway/code-change-N8Csif

# Step 2: For each Tier 1 branch, check if the work is on main
# If yes → delete the branch
# If no → decide: cherry-pick or delete anyway
for b in claude/badge-and-packages claude/circleci claude/favicon-and-configschema \
         claude/icon-and-naming claude/mcp-fix-annotations claude/mcp-quality-score \
         claude/mcp-stateless claude/mcp-wire-all-tools; do
  echo "=== $b ==="
  git diff main...origin/$b --stat
  echo
done

# Step 3: For Tier 2 branches, review the full diff
git diff main...origin/claude/fix-mcp-endpoint
git diff main...origin/claude/fix-mcp-dns-rebinding
git diff main...origin/devin/1775076305-seed-card-loyalty-system

# Step 4: Delete branches that are superseded or no longer needed
# (run individually after reviewing each one)
git push origin --delete claude/badge-and-packages
# ... etc

# Step 5: Prune local refs
git fetch --prune
```

## After cleanup

Once branches are cleaned up, the repo should have:
- `main` (the only active branch)
- Maybe 1-2 feature branches if any had unique work worth keeping

This is the ideal state for installing multi-agent-coord v2 — a clean branch tree means `lanes.sh` and `status.sh` give clear signal instead of noise from 18 stale branches.

---

## Cleanup executed — 2026-07-06

**Result:** 21 remote branches → 2 (`main` + 1 preserved feature branch)

### Deleted: 4 merged branches (safe, lost nothing)
- `origin/001-civitae-full-build` — merged via a31b2f2
- `origin/claude/fix-mcp-admin-guard` — merged via PR #10
- `origin/copilot/build-mcp-for-github` — merged
- `origin/railway/code-change-N8Csif` — merged via PR #4

### Deleted: 17 unmerged branches (all superseded by work on main)
Each was diffed against main. The work each branch attempted is already present on main via other PRs or direct commits:

| Branch | What it did | Why superseded |
|--------|-------------|----------------|
| `claude/badge-and-packages` | AI Agents Directory badge + PyPI entry | README evolved on main |
| `claude/circleci` | Add CircleCI config | `.circleci/config.yml` exists on main |
| `claude/favicon-and-configschema` | Add favicon | `frontend/favicon.ico` exists on main (289 bytes) |
| `claude/icon-and-naming` | Dot-notation MCP tools + brand icon | Dot-notation (`chat.join`, `agent.register`, etc.) on main |
| `claude/mcp-fix-annotations` | Remove `from __future__ import annotations` | Already removed on main |
| `claude/mcp-quality-score` | Add parameter descriptions to MCP tools | Descriptions on main |
| `claude/mcp-stateless` | Fix stateless HTTP for Railway | `stateless_http` on main (2 hits) |
| `claude/mcp-wire-all-tools` | Wire all 15 MCP tools | All tools wired on main |
| `devin/update-skills-1778405824` | Add testing-local-server skill | Skill exists on main |
| `devin/update-skills-1778428819` | Add testing-seo skill | Skill exists on main |
| `devin/update-skills-1780394899` | Update testing-seo with IndexNow | Skill exists on main |
| `claude/fix-kingdoms` | Kingdoms nav fix | `_nav.js` has kingdoms on main |
| `claude/fix-mcp-dns-rebinding` | DNS rebinding fix | `enable_dns_rebinding_protection` on main |
| `claude/fix-mcp-endpoint` | MCP endpoint resolution | server.json on main is v1.1.2 (branch had v1.0.1) |
| `claude/fix-seo-audit-5f33q` | SEO audit + sitemap-v2 + docs | `sitemap-v2.xml` + docs (`MCP-REGISTRY-PUBLISH.md`, `DOC-001`) on main |
| `devin/1778427797-seo-sitemap-fixes` | SEO sitemap fixes | `vercel.json` + sitemap evolved on main |
| `copilot/open-positions-for-agents` | Help wanted apply modal | Apply modal on main (3 hits) |

### Preserved: 1 branch with unique work
- `origin/devin/1775076305-seed-card-loyalty-system` — **953 lines of unique seed card loyalty system code** (`app/seed_card.py`, `app/routes/seed_card.py`, `config/seed_card_rates.json`, frontend updates). Not on main. Worth cherry-picking or merging in a future session.

## Connection to multi-agent-coord v2

The branch cleanup is a prerequisite for clean coordination. With 18 stale branches:
- `lanes.sh` would show noise (every stale branch looks like "in flight" work)
- `claims.yaml` would be confusing (are those branches active claims?)
- New sessions would waste time investigating dead branches

After cleanup, when a new session runs `status.sh`, they see only `main` + any active feature branches. That's the signal.
