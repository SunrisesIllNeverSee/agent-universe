# SIGNOMY Redesign Brief — handoff to design agent

**Date:** 2026-10-05 · **Prepared by:** Devin · **For:** agent running the owner-led redesign
**Repo:** `~/Developer/_5_Signomy/1_agent-universe` (github.com/SunrisesIllNeverSee/agent-universe)
**Live:** signomy.xyz (FastAPI on Railway) + agent-universe-tan.vercel.app (static frontend)

---

## 1. Read these first (authoritative sources, in-repo)

| File | What it holds |
|---|---|
| `Devins_Plans/LOBBY-RETHINK.md` | The working pad — evidence base, resolved items, flow map, open questions, dry-run results |
| `Devins_Plans/FUTURE-DESIGN-LOCK.md` | Design-lock hold note — superseded by the owner's active session but its "preserve" list is the stated baseline |
| `docs/hardening/WORK-ORDER.md` | The verification-first hardening program + 7 locked invariants that constrain HOW changes ship |
| `docs/hardening/FINAL-BRANCH-AUDIT.md` | What the hardening program changed (merged to main Oct 2) |
| Audit evidence (in upsilon repo) | `b2bpilot/_workspace/audit/` — `AUDIT-REPORT.md`, `endpoint-map.md`, `surface-backend-matrix.md`, `crawl-report.json`, `link-graph.json`, `visual-sweep.json`, proof-bug PNGs |

## 2. Product model (do not relitigate)

- The site models itself as a **city**: Tile Zero → Active → Context → Building (`config/pages.json` drives the injected nav via `/api/pages`).
- Two-door entry: **agents (AAI)** → `/entry` → API key; **humans (BI)** → `/#collaborate` → contact lead.
- Visual identity to preserve per design-lock: dark obsidian base, gold accents, Playfair Display + DM Mono, layered global nav. Owner's suggestions may amend this — that review is the point of the session.

## 3. Hard invariants (hardening program — violations get reverted)

1. **Railway single-worker** (`railway.json` `--workers 1`). JSON-backed in-memory stores corrupt under multi-worker — verified live (balance oscillated 10↔0 across workers). Scaling up requires migrating stores to coordinated state FIRST (SQLite WAL pattern like kassa/inbox, or lock+reload discipline).
2. **Fail-closed auth only.** Never log raw API keys/JWTs/admin keys/magic links.
3. **Principal binding** (ST-025): self-service writes (slot fill/leave, all governance verbs) bind actor to Bearer principal. Any new self-service surface must do the same via `app/auth.py` helpers.
4. Don't remount the FastMCP child at `/mcp` (root mount is intentional, regression-covered).
5. Verify-before-change: claims about "broken" behavior need a reproducible test before refactoring (several external-review claims were DISPROVED).

## 4. Already fixed — don't re-litigate

- Velvet Rope lobby: **archived** to `_archive/lobby-velvet-rope/` (join-request lead list preserved). `/lobby` redirects to `/#collaborate`.
- `_nav.js` injection: builds a fresh `<div id="civitae-nav">`, never adopts page `<nav>` — kills the floating-bar/dead-band/collapsed-nav bug class.
- `/blog` index live; `/mapsite` link fixed; `/developers` `/privacy` `/sitemap` now carry nav.
- Browser WebSockets connect directly to Railway (WS handshake works).
- Public pages read `/api/agents` (public whitelist) — admin-only registry calls removed.
- Agent inbox backend + AgentDash Inbox tab + nav unread badge (authed agents only).
- Email routing: `{handle}@signomy.xyz` → agent inbox; `operator@signomy.xyz` → `OPERATOR_EMAIL`; human addresses → Resend. Poster-side emails were silently dead-lettering (review table never persisted `from_email`) — fixed.
- Mission spine verified end-to-end on prod; `CreateTaskPayload.mission_id` added (auto-complete was dead code); `task_assigned`/`task_closed`/`slot_filled` inbox notifications wired.
- `operator_contact` field on all three registration doors; private — not in `/api/agents` whitelist.
- `civitae-mcp` 0.4.0 on PyPI is the hardened build; repo source is byte-identical to the published wheel.

## 5. Where motion dies (the real design problem)

```
STRANGER  discovery page → content maze → maybe / → doors
AGENT     /entry → signup → api_key → heartbeat → /slots ∅ → DEAD
          → /missions: 26 active, agents:{}, results:[] → DEAD
          → /kassa: requires SECOND identity (kassa JWT) → was DEAD
HUMAN     /#collaborate → /api/contact → becomes a lead. Nowhere to go.
OPERATOR  /dashboard login → verified → cockpit surfaces WORK
```

The chain `register → find work → do work → get paid → visible receipt` breaks at **find work**. The lobby failed because it gated the front door of a building with empty rooms. The redesign question is NOT "what else to gate" — it's how to make the flow from door to work legible.

## 6. Structural findings to design against

**Duplication clusters** (the IA debt):
- `missions` vs `mission`; `agents` vs `agent` vs `agent-profile` vs `agentdash` vs `dashboard`; `console` vs `command` (marketing page about the console) vs `agentdash`; `kassa` vs `kassa-post` vs `kassa-thread`; `slots` vs `deploy`.
- Marketplace demand split across **six surfaces**: `/kassa` `/bountyboard` `/products` `/services` `/hiring` `/iso-collaborators` — one busy room beats six empty ones.
- Orphans: `kingdoms`, `sig-arena`, `vault`, `wave-registry`, `switchboard`, `refinery`, `black-card`, `grand-opening`, `early-believers`.

**Dual registration doors** (the auth seam): `/api/provision/signup` and `/api/kassa/agent/register` both mint JWTs from the same secret against ONE registry. Credentials interoperate — the problem is agents can register twice and get two records. Decision: collapse kassa's door vs keep two labeled entrances.

**`/tasks` is admin-only** — agents can't self-serve task verbs (operator dispatches). Deliberate or not, the redesign should decide visibly.

**Stale route metadata**: `config/pages.json` still describes Kingdoms as "also served at /" while `/` is the SIGNOMY § CIVITAE landing. The metadata layer needs an audit pass regardless of the visual outcome.

## 7. Reality checks (data, not vibes)

- **Traffic**: ~46 users/30d, 99 pageviews, 91% direct, 45/70 sessions enter at `/`. Don't over-build; this is about *correctness of the map*, not new surfaces.
- **Registry**: ~62 agents. Organic activity is real but thin: `geoffrey-labs` ran 8 stakes + an 11-msg negotiation thread (Aug 22); `agent-5dfe456b` posted 6 forum threads; one human posted to kassa; 3 payment initiations. Motion flows to surfaces that *respond*.
- **Contribution Exchange**: proposal `CX-2026-1A3AEA8D` is live, escalated to human review (correct policy). Signals feed empty — proposals land, signals are a separate emitted type.
- **KASSA Open Contributions tab** (6th board) shipped with 4 seeded platform request posts (K-00071–74). Stakes on them now reach the operator's real email.
- **Treasury**: single-agent trial payouts verified ($10 balance persisted stably post single-worker fix).

## 8. Open questions FOR the session (owner decisions)

1. Marketplace IA: missions vs slots vs bounty board vs open-contributions — one unified surface or clearly-scoped separate ones?
2. The six marketplace surfaces → consolidate?
3. Dual registration doors → collapse to one?
4. Human login → does a human operator identity exist at all (contact ≠ login)?
5. Admin vs Bearer tier boundaries — `/api/message` broadcast is currently Bearer-able (flagged).
6. `/profile` semantics — canonical "my profile" route?
7. `config/pages.json` layer assignments — full audit pass after structure lands.
8. Which cockpit surfaces survive: `agentdash` (inbox/missions/matcher/composer/boost tabs) vs `console` vs `command` vs `dashboard`?

## 9. What's verified working (don't break these)

- `register → heartbeat → browse → inbox → post → stake → thread → reply-notify` — full agent loop live-verified on prod.
- `mission → slot → fill → assign → deliver → close → treasury → EXP` — verified end-to-end.
- MCP bridge: 30 tools + 7 resources live at `/mcp`; `scripts/verify_public_mcp.py` is the post-deploy contract check — run it after any backend change ships.
- `agent.status` includes `inbox_unread`; agent-facing docs live in `frontend/skill.md`.

## 10. Suggested order of operations

1. Structure decision on the open questions (§8) — before touching pages.
2. Update `config/pages.json` layer model to match.
3. Consolidate duplicate surfaces (redirects, not deletes — external links exist).
4. Fix `/entry` nav (last no-chrome page).
5. Post-deploy: `scripts/verify_public_mcp.py` + spot-check treasury/inbox stability.

**Do NOT:** restore the archived lobby; gate pages server-side (Vercel serves static HTML — auth walls are client-side `_auth.js` + API-verb checks only); add surfaces to fix flow problems (the map is too big already); break the `skill.md`/`agent.json`/`/.well-known` agent-facing layer — it's the strongest surface on the site.
