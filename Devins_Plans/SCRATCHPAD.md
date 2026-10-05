---
type: Coordination
title: SCRATCHPAD — the canonical multi-session coordination bus
description: THE one shared message bus + decision log for all sessions. Read the tail before doing anything; append your status/decisions/questions. OKF frontmatter convention applies to every doc in this directory.
tags: [coordination, scratchpad, protocol]
timestamp: 2026-01-01T00:00:00Z
last_touched: 2026-07-06 05:14 UTC
---

# SCRATCHPAD (canonical coordination bus)
**THE shared message bus + decision log for every session.**

> ## COORDINATION PROTOCOL (read before acting)
> 1. **This file is the one bus.** Before starting work, read the tail. Append your status/decisions/
>    questions here. Don't start a parallel log.
> 2. **Message format:** `### ⤷ <FROM> → <TO>: <subject>`
> 3. **OWNER mediates** decisions code/canon can't answer.
> 4. **OKF convention:** every doc in this directory carries YAML frontmatter
>    (`type/title/description/tags/timestamp`). New docs MUST include it.
> 5. **Lane discipline:** shared files = announce here before editing.
> 6. **Install hooks once per clone:** `bash scripts/install-hooks.sh`

---

### ⤷ PREVIOUS SESSION → NEXT SESSION: carry-forward items from SESSION_RESUME.md

> Extracted 2026-07-06 from `docs/archive/SESSION_RESUME.md` (last checkpoint 2026-05-05).
> These are the live actionable items that need to stay warm.

#### MCP Distribution — status

| Platform | Status |
|----------|--------|
| Official MCP Registry | ✅ `xyz.signomy/civitae` v1.1.2 active |
| Smithery | ✅ `burnmydays/civitae`, 100% quality, 19 tools, TS SDK published |
| Glama | ⏳ paused mid-Docker-config (see below) |
| PulseMCP | ✅ live |
| AI Agents Directory | ✅ listed (badge in README) |
| PyPI `civitae-mcp` | ✅ v0.2.0 live |
| Agentic.ai | ⏳ blocked on business email |

#### Immediate: finish Glama Docker build

Glama wants a Dockerfile config to host the server. Values to paste into the Glama form:

**Build steps:**
```json
["pip install --no-cache-dir -r requirements.txt"]
```

**CMD:**
```json
["sh", "-c", "python -m uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8300}"]
```

**Placeholder parameters:**
```json
{
  "CIVITAE_ADMIN_KEY": "dummy-admin-key-not-for-real-use",
  "KASSA_JWT_SECRET": "dummy-jwt-secret-replace-in-prod",
  "RESEND_API_KEY": "re_dummy_for_glama_build_check",
  "OPERATOR_EMAIL": "noreply@signomy.xyz",
  "STRIPE_SECRET_KEY": "sk_test_dummy_for_glama_build_check"
}
```

> Note: Glama auto-detected base image (debian:trixie-slim), Python 3.14, Node 25, and pulled the env var schema from the repo. The three fields above are what's missing.

#### After Glama: wait on Agentic.ai (blocked on business email)

#### Credentials reminders

- **MCP registry private key:** stored in password manager. The auth file at `signomy.xyz/.well-known/mcp-registry-auth` references the matching public key. To republish: `mcp-publisher login http --domain signomy.xyz --private-key <key>`, then `mcp-publisher publish`.
- **PyPI token:** used once and deleted from `.pypirc`. Create a new project-scoped token at pypi.org if you need to push another version.
- **CircleCI:** config at `.circleci/config.yml` — connect via dashboard if not already done.

#### Open backend backlog (not blocking)

- Fee Credit Pack purchase/balance/apply endpoints
- Seed Card (points, streaks, badges, 48h banking) — 953 lines on `devin/1775076305-seed-card-loyalty-system` branch, ready to merge
- Sliding Scale Reward Engine
- Phase transition logic (Day 1/8/31)
- Operator auth flow (login → JWT → console)
- Cascade Matcher (AGENTDASH Layer 1)
- Refinery (SIGRANK) — placeholder
- Switchboard (signal routing) — depends on Refinery

---

<!-- POST-COMMIT HOOK APPENDS BELOW THIS LINE -->
[HOOK] 2026-10-05 11:35 UTC · 5e6d4f2 · Deric · chore(scratchpad): hook log lines
[HOOK] 2026-10-05 10:09 UTC · 68496a1 · Deric · docs(release): closeout sweep 3 — llms-full.txt + REPO.yaml hosted count
[HOOK] 2026-10-05 09:54 UTC · f138752 · Deric · docs(release): closeout sweep 2 — fix missed stale metadata + scrub dead keypair
[HOOK] 2026-10-05 09:39 UTC · 7057caa · Deric · docs(release): MCP 0.4.0 closeout — fix stale tool counts, record release state
[HOOK] 2026-10-05 09:24 UTC · 7392d8a · Deric · docs(handoff): consolidated redesign brief for design session
[HOOK] 2026-10-05 08:40 UTC · f9bd439 · Deric · docs(coord): sync CROSSWIRE handoff notes + hook-appended scratchpad log
[HOOK] 2026-10-05 08:28 UTC · 2b28531 · Deric · docs(pad): fold hardening-program arc + redesign-session status into LOBBY-RETHINK
[HOOK] 2026-10-05 08:09 UTC · f976d1c · Deric · fix(mcp): restore hardened 0.4.0 source from published PyPI artifact
[HOOK] 2026-09-29 10:32 UTC · d6558ee · Deric · docs(pad): dry-run results — workers-4 corruption fix, mission_id gap, follow-on ships
[HOOK] 2026-09-29 10:29 UTC · a884352 · Deric · feat(agents): inbox UI, operator_contact capture, civitae-mcp v0.4.0 sync
[HOOK] 2026-09-29 10:17 UTC · 277c945 · Deric · fix(deploy): drop to 1 uvicorn worker — multi-worker corrupts JSON stores
[HOOK] 2026-09-29 09:28 UTC · b7104b8 · Deric · fix(kassa): route poster mail by address role — operator posts reach the operator
[HOOK] 2026-09-29 09:08 UTC · 86e1feb · Deric · feat(inbox): agent-side mailbox — wire the missing notification half
[HOOK] 2026-09-29 08:51 UTC · 6978c89 · Deric · feat(kassa): open contributions tab — sixth board for exchange-shaped work
[HOOK] 2026-09-29 08:34 UTC · 97dda00 · Deric · docs(lobby-rethink): mark MCP fixes resolved, exchange ping check, email reality
[HOOK] 2026-09-29 08:27 UTC · e39d73e · Deric · fix(mcp): add agent.heartbeat tool + real health fields
[HOOK] 2026-09-29 07:57 UTC · 1254185 · Deric · docs(lobby-rethink): MCP review + registry audit + connection plan
[HOOK] 2026-09-29 06:42 UTC · d74c1f6 · Deric · docs(lobby-rethink): full site map + flow map — where motion dies
[HOOK] 2026-09-29 02:15 UTC · 4ee60fc · Deric · fix(tests): drop lobby-seat test — subsystem archived
[HOOK] 2026-09-29 02:14 UTC · f19759a · Deric · chore(lobby): finish extraction — runbook to archive, agent.json join→/entry
[HOOK] 2026-09-29 02:13 UTC · 36bfe61 · Deric · build(railway): scope deploys to backend paths via watchPatterns
[HOOK] 2026-09-29 02:13 UTC · f89d378 · Deric · chore(lobby): archive velvet-rope subsystem outside the product
[HOOK] 2026-09-29 02:00 UTC · 43133ea · Deric · docs(coord): hook verification + sweep note (DERIC-DEVIN-CLI)
[HOOK] 2026-09-29 01:56 UTC · 0442003 · Deric · test: verify post-commit hook
[HOOK] 2026-09-28 09:13 UTC · 2b26664 · Deric · fix(console): heartbeat hits real route + actually checks the response
[HOOK] 2026-09-28 08:41 UTC · ed69db8 · Deric · feat(docs+ux): lobby-rethink pad, /profile→/dashboard, hook repair
[HOOK] 2026-08-25 11:07 UTC · 962ffc2 · Deric · docs(seo): Phase 4 + Phase 8 fixes — GitHub edits, AEO panel docs
[HOOK] 2026-08-25 10:40 UTC · 3968e0f · Deric · feat(seo): Phase 5-10 — content layer, crawl fixes, AEO panels, runbooks
[HOOK] 2026-08-25 10:26 UTC · fecc1f0 · Deric · feat(seo): Phase 1-3 — OG meta, JSON-LD, sitemap, robots.txt for signomy.xyz
[HOOK] 2026-08-25 10:08 UTC · 9744acf · Deric · docs(seo): add signomy.xyz phased SEO/GEO/AEO implementation plan and execution prompt
[HOOK] 2026-08-25 09:26 UTC · d9ebdcd · Deric · docs: update SCRATCHPAD
[HOOK] 2026-08-25 08:24 UTC · dcde2ce · Deric · docs: add consolidated SEO/AEO/GEO build package v2.0
[HOOK] 2026-08-24 21:22 UTC · df7eaab · Deric · docs: update SCRATCHPAD
[HOOK] 2026-08-24 21:21 UTC · 773adfb · Deric · docs: update SCRATCHPAD with session notes
[HOOK] 2026-08-24 19:53 UTC · 4166b13 · Deric · feat(exchange): add /.well-known/exchange.json pointing at signalaf.com Steward
[HOOK] 2026-08-24 16:57 UTC · a1e0584 · Deric · fix(vercel): only deploy main branch — stop preview auth email flood
[HOOK] 2026-08-24 16:57 UTC · a1e0584 · Deric · fix(vercel): only deploy main branch — stop preview auth email flood
[HOOK] 2026-08-17 22:51 UTC · 15174a1 · Deric · Add Master Canon Context section to AGENTS.md
[HOOK] 2026-08-17 17:07 UTC · 319a7d1 · Deric · authority-remediation-v1: MO§ES™ naming fix, governance predicates, mos2es.com cross-link
[HOOK] 2026-07-13 10:26 UTC · 2c0c0a1 · Deric · SEO: crawl 3 verification — all major issues resolved, trim remaining titles+meta
[HOOK] 2026-07-13 10:08 UTC · e7c7a44 · Deric · docs: add SF CLI crawl script + update playbook with headless mode
[HOOK] 2026-07-13 09:40 UTC · 195eca4 · Deric · docs: save Screaming Frog crawl 2 data (2026-07-13 04:57 UTC)
[HOOK] 2026-07-13 09:36 UTC · 03695ac · Deric · SEO: generate static vault pages with real SSR content, unique titles, H1s, canonicals, JSON-LD
[HOOK] 2026-07-13 09:27 UTC · 5e5eb99 · Deric · SEO: fix crawl-2 issues — H1s on 5 static pages, title trims+expansions, meta pixel trims, seeds H1→H2
[HOOK] 2026-07-13 08:20 UTC · 4a1fe77 · Deric · SEO: fix remaining audit items — unsafe links, meta trims, title expansion, hidden H1s
[HOOK] 2026-07-13 04:39 UTC · 06a7363 · Deric · GEO/AEO: DefinedTerm schema, HowTo for missions+kassa, Article freshness, llms-full stats+citation
[HOOK] 2026-07-13 04:27 UTC · 4874a5f · Deric · SEO audit fixes: vault SSR, link sweep, JSON-LD, sitemap, headers
[HOOK] 2026-07-11 12:48 UTC · 40c0476 · Deric · fix: civitae-mcp glama score improvements
[HOOK] 2026-07-07 16:58 UTC · 288573e · Deric · Add mobile UI viewing to handoff TODO list
[HOOK] 2026-07-07 16:56 UTC · d096c13 · Deric · Document MCP upgrade + repo cleanup for next session
[HOOK] 2026-07-07 16:37 UTC · 22c1d28 · Deric · MCP upgrade: 27 tools, 7 resources, package v0.3.0
[HOOK] 2026-07-07 15:35 UTC · 6d79fe4 · Deric · Repo structure cleanup: dedupe configs, move MCP + sim scripts
[HOOK] 2026-07-07 15:20 UTC · c1c723b · Deric · Repo cleanup: untrack runtime files, archive stale docs
[HOOK] 2026-07-07 14:29 UTC · 9f04880 · Deric · Replace hardcoded fictional agents with real API data
[HOOK] 2026-07-07 11:21 UTC · e2fcffa · Deric · fix: complete GEO/SEO gaps on 4 missed pages
[HOOK] 2026-07-07 10:59 UTC · 276b7e4 · Deric · geo: optimize content for AI citation on 20 priority pages (Step 8)
[HOOK] 2026-07-07 10:31 UTC · 2076de9 · Deric · fix: exempt /api/indexnow from admin key guard
[HOOK] 2026-07-07 10:28 UTC · ac57a93 · Deric · seo: add JSON-LD, llms-full.txt, IndexNow, internal links, UTM, sameAs
[HOOK] 2026-07-07 10:15 UTC · b2b9057 · Deric · seo: trim sitemap from 51 to 20 priority URLs
[HOOK] 2026-07-07 10:14 UTC · a0ddc74 · Deric · seo: optimize meta tags for 20 priority pages (fix 0-click problem)
[HOOK] 2026-07-07 10:11 UTC · cc513c9 · Deric · docs: update GEO/SEO/AEO plan — focus on 20 pages, add meta tag + GEO content steps
[HOOK] 2026-07-07 09:36 UTC · 70979d8 · Deric · docs: document admin review queue in OPERATOR-GUIDE.md
[HOOK] 2026-07-07 09:27 UTC · 927f35d · Deric · feat: split operator review queue to /admin, clean up user console
[HOOK] 2026-07-07 09:10 UTC · fe8cc76 · Deric · feat: unified review queue — lobby joins + agent signups in console
[HOOK] 2026-07-07 08:00 UTC · 8f76298 · Deric · feat: notify operator on agent signup + lobby join request
[HOOK] 2026-07-06 23:12 UTC · b2a7cbe · Deric · fix: delete .dockerignore that was blocking NIXPACKS build context
[HOOK] 2026-07-06 23:08 UTC · 89c64aa · Deric · fix: rename Dockerfile → Dockerfile.glama so Railway uses NIXPACKS
[HOOK] 2026-07-06 19:56 UTC · 8ee2eb7 · Deric · fix: restore requirements.txt for Railway/NIXPACKS + CI
[HOOK] 2026-07-06 19:39 UTC · 8dc381a · Deric · fix(ci): install deps from pyproject.toml instead of deleted requirements.txt
[HOOK] 2026-07-06 13:45 UTC · dbe6018 · Deric · chore: archive SESSION_RESUME.md — extract live items to SCRATCHPAD
[HOOK] 2026-07-06 13:43 UTC · 942c4bc · Deric · fix: replace dead COWORK_CLAUDE.md ref with v2 coordination protocol
[HOOK] 2026-07-06 13:41 UTC · ab5ab6b · Deric · feat: install multi-agent-coord v2 — 6-layer coordination system

### ⤷ DEVIN → ALL: SEO audit complete — 3 crawls, all issues fixed

**Session:** 2026-07-13 (continuation from previous thread)
**Work:** Screaming Frog SEO audit of signomy.xyz — 3 crawls, all issues resolved

**Crawl history:**
- Crawl 1 (07-12 23:17): 12 issues found
- Crawl 2 (07-13 04:57): issues verified, vault root cause identified
- Crawl 3 (07-13 06:21): all major issues at zero — Grade A-

**Commits (6 total):**
- 4874a5f: vault SSR, link sweep, JSON-LD, sitemap, security headers
- 06a7363: GEO/AEO — DefinedTerm, HowTo, Article freshness, llms-full
- 4a1fe77: unsafe links, meta trims, title expansion, hidden H1s
- 5e5eb99: H1s on 5 static pages, title trims, meta pixel trims, seeds H1→H2
- 03695ac: vault pages generated with real SSR content (root cause fix)
- 2c0c0a1: crawl 3 verification, trim last 5 title/meta items

**Key discovery:** Vercel serves frontend/vault/gov-*.html as static files, bypassing
Railway backend SSR. Fixed by generating static pages with baked-in content via
scripts/generate_vault_pages.py.

**Remaining (low priority):**
- CSP header (security, needs policy design)
- H2 cosmetics on UI pages (not applicable to most)
- Low word count on interactive UI pages (expected)

**Artifacts saved:**
- 3 crawls of raw SF data (150+ CSVs, 4 SVG diagrams)
- 4 analysis docs with YAML frontmatter
- scripts/sf-crawl.sh (reusable CLI crawl script)
- scripts/generate_vault_pages.py (vault page generator)
- Updated SCREAMING-FROG-AUDIT-PLAYBOOK.md with CLI instructions

**ORCID profile:** Fully updated (biography, keywords, websites, employment, education)
**Zenodo backlinks:** Saved for another day (manual on Zenodo UI)

Status: DONE. No further action needed unless adding new pages.

### ⤷ DEVIN → ALL: Seed activity audit — real vs test signups

**Date:** 2026-07-13
**Source:** Live Railway API (`/api/seeds`) + local `data/seeds.jsonl`

**Live seed totals (Railway):** 161 seeds
- BI (human): 91 seeds from 10 unique identities
- AAI (AI agents): 48 seeds
- system: 22 seeds

**Local seed file:** 705 seeds (stale snapshot from 07-06 test runs — not live data)

**Real external human signups: 1**
- **leosniu** (leosniu@signomy.xyz) — posted a marketplace listing on 2026-06-22:
  "AI Agent for Hire — Copy, Research, SEO, Analysis" (services tab)

**Fake/test signups (MimiqAI personas):**
- anna.brewer.953a@persona.mimiqai.com — contacted a hiring post on 2026-05-21
- matt.frederick.7742@persona.mimiqai.com — contact form "Join" on 2026-05-21
- These are LLM-powered simulated users from gojiplus/mimiq (bot testing tool)
- Someone pointed MimiqAI at signomy.xyz to test the site

**Operator/owner activity (you):**
- contact@burnmydays.com: 52 seeds (kassa posts across all tabs)
- operator: 28 seeds (missions created, payments initiated)
- deric.mchenry@gmail.com: 2 seeds (contact form)
- Deric McHenry / burnmydays (Temporary Chair): 2 council_seated seeds

**Test/monitoring bots:**
- hange-monitor-*@signomy.xyz: 3 seeds (monitoring posts)
- test@test.com: 1 seed (test contact)

**51 agents in /api/agents:** All test/stress/monitoring bots — 14 STRESS-*, 3 hange-monitor-*, 1 Codex Smoke Agent, 35 GPT auto-registered agents. Zero real external agents.

**Lobby join requests:** 0 (local lobby.db empty, live endpoint requires admin key)

**Bottom line:** 1 real external user (leosniu). Everything else is you, test bots, or MimiqAI personas. The site has not attracted organic human signups yet.

**Next steps (deferred to user):**
- Investigate where MimiqAI test came from (who ran it?)
- Reach out to leosniu (the one real user)
- Consider why signups aren't happening (funnel analysis, UX friction)
- Check lobby requests with admin key for any pending applications

---

### ⤷ DEVIN → ALL: MatrAIx Phase 0 inventory complete — SIGNOMY_BASELINE.md written

**Date:** 2026-08-10 15:04 UTC
**Session:** devin-2026-08-10 (MatrAIx research workspace)
**Repo:** matraix (external research workspace at ~/Developer/active/matraix)

**What I did (read-only, no platform changes):**
1. Read coordination state (SCRATCHPAD, DECISIONS, claims, ROSTER, CROSSWIRE)
2. Installed commit-log hook, set role to DEVIN, claimed lane
3. Produced full runtime inventory → written to `_03signomy/manifests/SIGNOMY_BASELINE.md` in the matraix repo

**Key findings:**

**MCP discrepancy RECONCILED:**
| Source | Claims | Actual |
|--------|--------|--------|
| README.md | "19 governed tools" | **STALE** — actual is 27 |
| AGENTS.md | "27 tools, 7 resources" | CORRECT |
| MCP server card | "27 tools" v1.2.0 | CORRECT |
| Smithery | "19 tools" | **STALE** — needs update |
| PyPI | v0.2.0 published | **STALE** — local is v0.3.0 |
| Runtime (app/mcp_bridge.py) | 27 tools + 7 resources | **SOURCE OF TRUTH** |
| Package (civitae-mcp) | 23 tools | Correct for package subset |

**Runtime inventory:**
- Commit: b95f090 (main, 4 dirty files)
- HTTP routes: 295 total (~185 API + ~80 pages + 5 WS + well-known)
- MCP tools: 27 (chat 4, marketplace 4, discovery 8, governance 4, operator 4, economy 2)
- MCP resources: 7 (6 governance docs + 1 manifest)
- Storage: 3 SQLite DBs (forums, kassa, lobby) + 1 JSONL (seeds)
- Tests: 315 passed
- Python: 3.14.6 local, 3.13 CI
- Deployment: Railway (backend) + Vercel (frontend signomy.xyz)

**Gate P0:** ✓ baseline frozen, ✓ HTTP inventory, ✓ MCP counted, ✓ tests recorded, ✓ discrepancies documented. ⚠ No staging environment exists yet (Phase 1 task).

**No platform changes were made.** This was read-only inspection.

**Next (per signomyplans.md §27):** Task 3 — classify every external action (safety matrix). Then Task 4 — design staging isolation. Then Task 5 — STOP and report.

— DEVIN (MatrAIx research workspace)

---

### ⤷ DEVIN → ALL: Phase 0 Tasks 1-5 COMPLETE — STOP, awaiting owner review

**Date:** 2026-08-10 15:30 UTC
**Session:** devin-2026-08-10 (MatrAIx research workspace)

**All 5 Devin Tasks complete.** Artifacts written to matraix repo (`~/Developer/active/matraix/_03signomy/manifests/`):

| Artifact | Purpose |
|----------|---------|
| SIGNOMY_BASELINE.md | Full runtime inventory (commit, routes, MCP, storage, tests, CI) |
| ACTION_SAFETY_MATRIX.md | ~120 actions classified by surface/auth/side-effects/safety |
| STAGING_ISOLATION_DESIGN.md | Proposed staging architecture (3-line code change) |
| PHASE0_REPORT.md | Final report with discrepancy reconciliation + recommendation |

**Key findings:**
- MCP discrepancy reconciled: runtime has 27 tools + 7 resources. README says 19 (stale), Smithery says 19 (stale), PyPI has v0.2.0 (local v0.3.0). AGENTS.md and MCP server card are correct.
- 295 HTTP routes (113 write, 175 read, 7 WS)
- 315 tests pass
- Storage: 3 SQLite + JSONL, all file-based (isolation = separate data dir)
- Staging needs 3-line additive change to `app/data_paths.py` (CIVITAE_DATA_DIR env var)
- Recommended first interaction: **MCP** (agent-native, 27 tools, blind-boundary compatible)

**STOP.** Do not implement population simulation, modify economic logic, alter MO§ES rules, or add SigRank. Next phase begins only after owner reviews this inventory.

**No platform changes were made.** Only SCRATCHPAD appended (per coordination protocol).

— DEVIN (MatrAIx research workspace)

---

### ⤷ GTM2 → Next: Signoff — Glama/SEO/repo maintenance complete

**Session:** GTM2 (Devin)
**Date:** 2026-08-26
**Status:** Signing off. Handoff ready.

**Completed this session:**

1. **Glama MCP scoring (repo-side done):**
   - LICENSE swapped to MIT (GitHub detects MIT)
   - glama.json: description + license added
   - All 23 PyPI tools: rich docstrings + MCP annotations (v0.3.2)
   - Dockerfile.glama fixed for uv sync
   - License badge simplified to MIT only (removed "Proprietary" that may confuse scanners)
   - Tool count corrected (27→23 in glama.json description)

2. **README rewrite (SigRank-style):**
   - Table of contents, ecosystem table, stack section, related links
   - All 14 badge URLs verified 200
   - All ecosystem repo links verified 200
   - All live surface routes verified 200
   - Smithery badge fixed (their endpoint was 500)

3. **Repo security audit:**
   - Personal email removed from ai-plugin.json, openapi.json, 6 docs
   - Personal name removed from AGENTS.md, system-devin, test-reports, 4 docs
   - Local machine paths removed from 8 docs
   - Patent serial numbers removed
   - REPOREVIEW docs sanitized
   - Academic attribution (ORCID/Zenodo/JSON-LD) retained as legitimate

4. **Folder maintenance:**
   - `nuild_outs/` → `build_outs/` (typo fix)
   - 145 SF crawl CSV/SVG files removed from git
   - Old 0.2.0 dist wheels removed from git
   - .gitignore hardened (dist/, node_modules/, caches, SF crawl patterns)
   - Stray hash file removed from frontend

5. **Future ideas documented:**
   - `docs/plans/IDEAS.md` — civitae-cli TUI concept

**Pending (not repo-side):**
- Glama re-sync (Glama backend backlog — license still null, tools still empty)
- `hello@signomy.xyz` email setup (owner action in Porkbun)
- Glama tool quality score re-evaluation (will improve after re-sync)

**Handoff file:** `Devins_Plans/handoffs/2026-08-26-gtm2-to-next-glama-seo-maintenance.md`

— GTM2 (Devin)

### ⤷ DEVIN → NEXT: 500-keyword map logged in SEO/AEO/GEO package

**What:** Created the full 500-keyword map across 11 rings in the SEO/AEO/GEO build package:
- `docs/seo-aeo-geo-build-package/keywords/KEYWORD_MAP_500.md` — full annotated registry
- `docs/seo-aeo-geo-build-package/keywords/KEYWORD_MAP_500.csv` — machine-readable CSV (500 rows)
- Updated `docs/seo-aeo-geo-build-package/README.md` to reference the new directory

**Rings:**
1. SigRank direct vocabulary (20) — token telemetry, yield cascade, sigrank, etc.
2. Competitor alternatives (40) — ccusage/tokscale/viberank/tokenmaxxer alternatives
3. Tool-specific token tracking (50) — claude code/codex/cursor/gemini token usage
4. Leaderboard/gamification (50) — tokenmaxxing, vibe coding leaderboard, etc.
5. Efficiency/metrics/optimization (60) — cache hit rate, token efficiency, AI coding metrics
6. Enterprise cost/spend (60) — AI spend dashboard, cost per developer, team tracking
7. Tool comparisons (50) — claude code vs codex/cursor/gemini, best AI coding tool
8. Skill assessment/evaluation (50) — workera/worklytics alternatives (mos2es.org)
9. Agent observability/monitoring (40) — LLM monitoring, agent tracing
10. Broad AI coding/vibe coding (40) — vibe coding, MCP tools, AI coding guides
11. Prompt/context engineering (40) — prompt evaluation, context engineering

**GSC evidence embedded:** signalaf.com last 28 days — 63 queries, 407 impressions, 11 clicks.
Top terms: token telemetry (72i, #9.2), ccusage alternatives (6i, #7.0), cache hit rate (10i).

**Next:** Build missing /vs/ pages on signalaf.com for Ring 2 competitors (viberank, tokenmaxxer,
whoburnedmore, etc.) and optimize existing pages for Rings 3-5 keywords.

— DEVIN

### ⤷ de-seo → bus: orphan fix deployed — 70/C → 85/B (commits 3f4ca38, 1f0e41e)

- Root cause: _nav.js/_footer.js render all nav/footer links client-side;
  HTML-only crawlers saw zero nav links → 56 sitemap orphans. Plus internal
  hrefs used /x.html (308 → /x under cleanUrls).
- Fixes: stripped .html from 242 internal hrefs (59 files); added static
  <noscript> sitemap nav (nav+footer+orphan union, 82 targets) to 123 pages.
- Re-crawl: orphans 56→0, score 70/C → 85/B. Only flag: /mcp → 406 — that is
  CORRECT MCP-spec behavior (JSON-RPC needs Accept: text/event-stream); not a bug.

### ⤷ de-seo → bus: schema fix deployed — INVALID → 100/100 VALID (commit e594bf7)

- All 126 HTML files had object-form @context (`{@vocab, moses:*}`) — valid
  JSON-LD but fails validators/Google (expect literal "https://schema.org").
- Fix: string @context; canon/custom predicates now `moses:`-prefixed keys
  (sourceSystem, canonBacked, authorityApprovalRef, associatedWith, governs,
  operationalizes, enforcementArchitectureFor — IRI-scheme namespacing).
  16 array `@type` blocks → SoftwareApplication + additionalType DefinedTerm.
  119 BreadcrumbList +name; 33 app blocks +Offer (→/join, MO§ES→mos2es.com/contact).
- Verified: jev-seo schema on index/moses/about/vs pages → 100/100 VALID each.

— DEVIN

### ⤷ de-seo → bus: /mcp 406 resolved via Vercel `missing` rewrite (commit 409fef0)

- /mcp was never in sitemap — crawler scraped the URL from developers.html
  <code> text. 406 was spec-correct but also bad UX (browser hits got a
  JSON-RPC error).
- Fix: vercel.json rewrites — /mcp requests without
  `Accept: text/event-stream` → /guides/how-to-use-the-mcp-bridge.
- Verified live: SSE accept → 200 text/event-stream (protocol intact);
  text/html + */* → 200 docs page.

— DEVIN

### ⤷ de-infra → bus: operator auth wall shipped + 22-day deploy gap root-caused (commits 28424d0, 0e49ddb)

- **Auth model live**: `frontend/_auth.js` gates console/deploy/campaign/agentdash —
  verifies `civitas_auth` via `/api/provision/status`, redirects to `/dashboard?next=<origin>`.
  Cockpit POSTs now send `Authorization: Bearer <api_key>`; `admin_key_guard` accepts
  registered-agent Bearer on `_OPERATOR_WRITE_PREFIXES` (admin key unchanged).
- **dashboard.html was secretly dead on prod**: main `<script>` never closed →
  `</body></html>` swallowed as JS → SyntaxError → `doLogin` never defined.
  Login button has never worked until now. Fixed + `?next=` redirect-back added.
- **Deploys were dead since Sept 5**: ci.yml had `persist-credentials` sibling-of-`uses`
  → workflow-file invalid → CI 0s-failed → Railway wait-for-CI skipped ALL deploys
  (~22 days). One indent fix → CI green → Railway auto-deploys restored.
- **Lobby gate removal now actually live**: Railway rebuild carried `64613c0`;
  all previously-gated routes serve 200 directly (was 307→/lobby).
- **Brainstorm pad staged**: `Devins_Plans/LOBBY-RETHINK.md` — the structural session
  prep (evidence, resolved items, 7 open questions, invariants) for the
  backwards-from-endpoints site-map rethink.
- `/profile` → `/dashboard` 302 in vercel.json (`/profile/:handle` → agent-profile kept).

— DEVIN

## DERIC-DEVIN-CLI — hook + sweep note (2026-09-27)
- post-commit hook: VERIFIED working — execs scripts/hooks/post-commit.sh
  at correct path; empty test commit clean. Earlier `built/agent-universe`
  error resolved upstream (install-hooks.sh rerun).
- Fresh sweep: signomy.xyz now **100/A** crawl, 0 orphans, schema 100/100,
  llms 100/100.

### ⤷ de-infra → bus: velvet-rope lobby ARCHIVED + Railway watchPatterns scoped (2026-09-29)

- **Lobby subsystem removed from product, archived outside repo** at
  `Developer/_5_Signomy/_archive/lobby-velvet-rope/` (backend routes+store,
  lobby.html, join.html, lobby.db lead list, test_routes_lobby.py).
  Stripped: server.py store+router+prefixes, deps field, pages whitelist,
  index.html link+join fire-and-forget, admin.html requests section,
  _nav.js comment, pages.json entries, vercel.json dead rewrite.
  /lobby + /join redirects to /#collaborate remain live.
- **Test debris archived** to `_archive/test-debris/local-test-entries.json`
  (auth-test-agent + auth-test mission); local data/ clean.
- **railway.json build.watchPatterns** → backend redeploys only on
  app/config/deps changes; frontend-only pushes stop burning Railway builds.
- **LOBBY-RETHINK.md**: lobby question marked RESOLVED; new Q8 — dual agent
  identity (provision api_key vs kassa JWT) needs a unify-or-separate call.

— DEVIN
