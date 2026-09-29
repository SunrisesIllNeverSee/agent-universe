---
type: Design
title: LOBBY-RETHINK — structural brainstorm pad
description: Working pad for the deeper site-structure session — layout working backwards from endpoints (governance → committee → KA§§A → products). Captures evidence, what's already resolved, and the open questions.
tags: [architecture, lobby, auth, ia, brainstorm]
timestamp: 2026-09-27T00:00:00Z
last_touched: 2026-09-27 11:00 UTC
---

# LOBBY-RETHINK — structural brainstorm pad

## What this session is for

Origin question (owner, 2026-09-26): the lobby needs "a deeper audit and understanding or
brainstorming... including the layout structural function of the site — easiest working
backwards with the endpoints, i.e. products and locations like governance, committee,
kassa. The front end is a little messy."

Goal of the session when we run it: **produce a canonical surface map** — which pages
exist, who they're for (public / agent / operator / admin), what backend cluster they
talk to, and which ones should be merged, gated, or killed. Not a redesign — a structure
decision record.

## Evidence base

Regeneratable artifacts (were in `_workspace/audit/`, recreate on demand):

- Route crawler → ~133 routes inventoried, status + link graph incl. JS-injected links
- Visual sweep → 71 rendered routes in headless Chromium (nav/footer/CTA/console errors)
- Endpoint map → **282 routes across 102 groups** extracted from `app/routes/*.py`
- Surface↔backend coupling matrix → which frontend pages call which endpoint groups
- PostHog (project 491591) → 30-day traffic: ~46 users, 99 pageviews, 91% direct,
  45/70 sessions enter at `/`, `/lobby` had **zero** pageviews, zero custom events

Backend cluster shape (from the endpoint map):

| Cluster | ~Endpoints | Role |
|---|---|---|
| Money spine — kassa + economy + connect | ~63 | Product core |
| Work spine — missions/slots/tasks/campaigns/deploy | ~30 | Operations |
| Trust layer — governance/advisory/seeds/audit/chains | ~30 | MO§ES proof |
| Identity — provision/agents/operator/availability | ~25 | Agent registry |
| Lobby | 9 | Dead appendage (see below) |

## Already resolved (don't re-litigate)

Since the audit ran, these landed:

1. **Velvet Rope page gate: DELETED.** `64613c0`. It was FastAPI middleware gating HTML
   pages Vercel never routed through it; `lobby_session` cookies were never issued by
   any flow; `/api/*` was exempt anyway. Backend lobby store + `/api/lobby/*` endpoints
   remain **dormant** (lead-list only — join form still fire-and-forgets `/api/lobby/join`).
2. **Operator auth wall: BUILT.** `28424d0`. `_auth.js` + `admin_key_guard` accepts
   registered-agent `Bearer <api_key>` on cockpit write paths
   (`_OPERATOR_WRITE_PREFIXES` in `app/server.py`). Console/deploy/campaign/agentdash
   gate to `/dashboard?next=<origin>`. Kassa writes were already JWT-gated at route level.
3. **Join surfaces consolidated.** `8331f0a`. Agents → `/entry` (terminal/API key),
   humans → `/#collaborate`, roles → `/helpwanted`. `/lobby` + `/join` redirect.
   `/profile` → `/dashboard` (`0e49ddb`-era vercel.json).
4. **Admin-endpoint leaks on public pages: fixed.** Public pages read `/api/agents`
   (`9cf9936`, `1aa2927`). `dashboard`'s `/api/provision/status/{id}` Bearer check is
   intentionally retained — that IS the login.
5. **Deploy pipeline: fixed.** `0e49ddb`. ci.yml had `persist-credentials` as a
   sibling of `uses:` → workflow-file invalid → every CI run 0s-failed for ~3 weeks →
   Railway wait-for-CI skipped all deploys. Pushes now auto-deploy again.

## Site map (2026-09-29 — firecrawl map + code, both verified)

The site models itself as a **city** (`config/pages.json`: Tile Zero → Active → Context → Building). ~120 live URLs total.

```
DISCOVERY (~69 pages — programmatic SEO, pulls strangers in)
├── /vs/* ×20            comparison pages (autogpt, crew-ai, langchain…)
├── /alternatives/* ×9   "best X alternatives"
├── /concepts/* ×10      glossary/definition pages
├── /guides/* ×4         how-to (register, join, post, mcp-bridge)
├── /metrics/* ×4        trust-tier, flame-score, seed-provenance, treasury-split
├── /tools/* ×3          earnings-calc, governance-checker, trust-tier-calc
└── /blog/* ×13          posts
   → FINDING: CTAs mostly link to other content pages, not the doors.
     Strangers orbit the content layer; last mile to /entry is self-navigated.

ENTRY — Tile Zero (~9)
├── /                    kingdoms hex map + two-door tabs (AAI/BI)
├── /civitas             about/vision        ├── /portal      full directory
├── /moses               MO§ES framework     ├── /contact     governed intake
├── /grand-opening       genesis week        ├── /black-card  2% fee tier
├── /early-believers     first-50 agents     └── /fee-credits prepaid packs
   DOORS: /entry (agent → api_key)  |  /#collaborate (human → contact lead)

ACTIVE (~15 — the working surface, all public-read)
├── /world               3D hub             ├── /kassa       marketplace board
├── /missions            26 listed          ├── /slots       EMPTY feed
├── /forums              threads            ├── /seeds       provenance feed
├── /advisory            14-seat council    ├── /openroles   roles (→helpwanted)
├── /earnings-matrix     projected earnings ├── /earnings-journey
├── /mission             detail             └── /connect     Stripe onboarding
   ⚠ marketplace split across SIX surfaces:
     /kassa /bountyboard /products /services /hiring /iso-collaborators

CONTEXT (~17 — the protocol layer)
├── /senate /governance /economics /treasury /academia
└── /vault + /vault/gov-001…006    constitutional docs
   ⚠ 11 pages of law for a platform with 0 executed missions — governance
     IS the product thesis, but it makes the empty working surface louder.

OPERATOR (auth wall — _auth.js → /dashboard?next)
├── /dashboard  login (agent_id + api_key → civitas_auth)
├── /agentdash  cockpit             ├── /console    operator console
├── /deploy     mission create      ├── /campaign   campaigns
└── /connect    payouts

BUILDING (advertised unfinished — status badges live on them)
├── /sig-arena [wip]  /leaderboard [wip]  /wave-registry [live]
├── /refinery [EMPTY] /switchboard [EMPTY]

ADMIN: /admin (admin-key ops)

AGENT-FACING FILES (the real agent door — not HTML):
/skill.md /agent.json /llms.txt /.well-known/{agent,mcp-server-card,
governance,exchange}.json /mcp — this surface is already well-built.
```

## The flow map — where motion dies

```
STRANGER  discovery page → content maze → maybe / → doors
AGENT     /entry → signup → api_key → heartbeat → /slots ∅ → DEAD
          → /missions: 26 active, agents:{}, results:[] → DEAD
          → /kassa: requires SECOND identity (kassa JWT) → DEAD
HUMAN     /#collaborate → /api/contact → becomes a lead. Nowhere to go.
OPERATOR  /dashboard login → verified → cockpit surfaces WORK
```

**The lobby parallel (this is why the lobby question kept recurring):** the lobby
put a gate on the front door of a building with empty rooms. The actual problem it
gestured at — "how does an actor get from door to work" — was never a gating
problem. It's the flow problem: `register → find work → do work → get paid →
visible receipt`. Today the chain breaks at "find work" — empty slots feed, no
exposed fill path on missions, a second identity wall at kassa, and marketplace
demand fragmented across six surfaces instead of one busy room.

## Deep dive 2026-09-29 — MCP review + registry audit

### MCP bridge (signomy.xyz/mcp) — HEALTHY, with 4 real issues

Verified live: streamable-HTTP MCP at `/mcp`, protocol `2024-11-05`, 27 tools
registered, `tools/call` works against prod data, `agent.register` minted a real
key (`agent-13c7a5b6`), valid-vs-invalid key auth verified clean. Content
fencing on `market.browse`/`forum.thread` already guards prompt injection.

Issues:
1. ~~`platform.health` returns `version: "unknown"`, `uptime_s: -0.0`~~
   **FIXED `e39d73e`** — `state.version`/`start_time` wired at startup; prod
   verified `0.9.0` / real uptime.
2. ~~**No heartbeat tool in MCP.**~~ **FIXED `e39d73e`** — `agent.heartbeat`
   (api_key-scoped, mirrors REST last_seen + metrics bootstrap + 1-in-10 seed
   sampling). Verified live with a real key. Prod seed log prior: heartbeat
   count = **1**.
3. **Three surfaces drifted**: bridge 27→28 tools (dot names) / PyPI `civitae-mcp`
   15 tools (underscore names) / stale `civitae_mcp_server.py` copy with wrong
   env vars. Homepage recommends the 15-tool package. `skill.md` count fixed
   (`e39d73e`) but package↔bridge naming drift is still open — keep both naming
   conventions documented or converge. `docs/plans/MCP-UPGRADE-PLAN.md`.
4. Bridge test coverage = 2 tests (registration + tool inventory).

### Registry audit — 62 agents (61 + devin probe `agent-13c7a5b6`, flagged for removal)

| Cohort | Count | Verdict |
|---|---|---|
| `STRESS-*` / `stress-*` (Apr 10 + Sep 8) | 19 | junk — purge |
| `hange-monitor-*` ×3, Codex Smoke, `test-bot-check`, `check2`, `sample-value`, `devin-mcp-probe` | 7 | junk — purge |
| `my-agent-42` (the docs example handle) | 1 | likely test — confirm w/ owner |
| **May-21 cohort** — one-day mass reg, all `system: gpt`, date-stamped handles (`*-20260521`), several `signomy-*` named | 30 | owner-created (confirmed) — single operator; purge or keep as demo fleet |
| `leosniu`, `geoffrey-labs`, `haldrin-envoy`, `orchardsguide` | 4 | plausibly real — spaced single registrations Jun–Sep |

`orchardsguide` verified real-looking: GPT, governed tier, capabilities
"public product documentation / community onboarding", registered Sep 23,
0 missions. A live lead sitting idle.

### The seed log is the real motion record (204 seeds)

`kassa_post:57  registration:46  document:22  message:12  forum_thread:9
stake:8  thread:8  contact:7  payment_initiated:3  council_seated:2
heartbeat:1`

**Kassa WAS exercised** (57 posts, 8 stakes, 12 messages). Missions/tasks/slots
never were (`agents:{}`, `results:[]`, treasury all zeros, 0 open slots).
The work spine exists end-to-end (`/api/tasks assign→start→deliver→close`,
`/api/slots create→fill`, `/api/mission-dash` milestones) — never executed.

### Structural blocker for "connect everyone": no reach channel

Registration captures name/handle/capabilities + `signup_ip` — and a
**fake `@signomy.xyz` email nobody can receive**. No operator contact, no
webhook. Agents are write-only records: the platform cannot reach them
out-of-band; connection requires them to poll back in.

→ Add an `operator_contact` (email or webhook URL) field to signup. Optional,
but without it every registration is a dead letter.

### Contribution Exchange — what it is, where it fits

SignalAF-hosted protocol (`/.well-known/exchange.json` v0.2, private_alpha):
signomy delegates to the hosted steward at `signalaf.com/api/exchange/steward/
signomy.xyz` — verified LIVE, `auto_engage.enabled: true, max_cash: $250`.
Accepts guest + registered agents, unsolicited contributions AND contribution
requests; settles cash/royalty/reciprocal/attribution; 500bps platform fee.

**It is the generalized form of what missions/bounties do** — and it answers
the exact break in the flow map: an agent can propose a contribution TODAY
without waiting for a posted mission, without even registering (guest_agents).
Owner question for the session: separate surface vs. fold into
missions/bountyboard. Recommendation: don't redesign it apart — surface
exchange signals as a third post type on the marketplace (mission / bounty /
open-contribution). One busy room beats seven empty ones.

**Ping check 2026-09-29:** `signals?domain=signomy.xyz` → `[]`. Proposals and
requests are POST-only endpoints. **First real artifact landed 2026-09-29:**
proposal `CX-2026-1A3AEA8D` ("End-to-end work-spine dry run") accepted by the
steward, disposition `escalate` → human_required (unclassified category falls
outside the auto-engage allowlist — policy working as designed). Signals feed
still 0: signals are a separate emitted record type, not inbound proposals.
Proposer key for `CX-2026-1A3AEA8D` held by Devin session — needed to act on
the proposal thread again.

**KASSA "Open Contributions" tab — shipped 2026-09-29.** Sixth tab added to
`frontend/kassa.html` (button + panel + modal option); `tab` is free-form
TEXT so stakes/threads/seed-provenance inherit for free, no migration. Seeded
4 platform request posts (K-00071..K-00074): MCP test coverage, API reference
coverage, agent-side notification design, first mission dry-run — all real
gaps from this audit, all negotiable within Exchange policy.

**Email reality check:** `RESEND_API_KEY` + SMTP vars ARE configured on
Railway — outbound mail works. Wired and firing: `send_magic_link` to the
poster when a stake opens a thread, `send_message_notification` to the poster
on each reply (`app/routes/kassa.py`). The gap is asymmetric — poster-side
email exists, agent-side does NOT: `{handle}@signomy.xyz` is an identity
label with no mailbox behind it; agents get no notification and must poll
kassa threads. Seeded as contribution request K-00073.

**Activity correction (owner was right — it's been used):** seed log shows
real motion on the *working* surfaces, not the empty ones. `agent-f0b899e1`
(= `geoffrey-labs`) ran 8 kassa stakes + an 11-message negotiation thread on
2026-08-22; `agent-5dfe456b` posted 6 forum threads; a real human
(`lennythelobster77066@gmail.com`) posted to kassa + 2 contacts; persona
agents (`@persona.mimiqai.com`) reached out; 3 payment initiations.
Missions/slots/exchange idle because the motion went to kassa + forums.

## Open questions for the session

1. **Site structure / IA.** ~60 HTML pages, several overlapping: `missions` vs
   `mission`, `agents` vs `agent` vs `agent-profile` vs `agentdash` vs `dashboard`,
   `console` vs `command` (marketing page *about* the console) vs `agentdash`,
   `kassa` vs `kassa-post` vs `kassa-thread`, `slots` vs `deploy`, plus orphan-ish
   surfaces (`kingdoms`, `sig-arena`, `vault`, `wave-registry`, `bountyboard`,
   `switchboard`, `refinery`, `black-card`, `grand-opening`, `early-believers`…).
   Working backwards from endpoint clusters: which surfaces are *products*
   (public-read), which are *cockpits* (gated), which are *docs*?
2. **Governance/committee/KA§§A as locations.** User's framing — treat these as the
   site's "places" the frontend routes to: what is the canonical page for each, and
   does every place have a real endpoint cluster behind it?
3. ~~**Dormant lobby backend.**~~ **RESOLVED 2026-09-27 — archived, not deleted.**
   `app/lobby.py`, `app/routes/lobby.py`, `frontend/lobby.html`, `frontend/join.html`,
   `data/lobby.db`, `tests/test_routes_lobby.py` → `Developer/_5_Signomy/_archive/lobby-velvet-rope/`.
   Wiring stripped: server.py store/router/prefixes, deps state field, pages.py
   whitelist, index.html lobby link + `/api/lobby/join` fire-and-forget, admin.html
   lobby-requests section, `_nav.js` comment, `config/pages.json` join+lobby entries,
   vercel.json `/lobby` rewrite (the `/lobby` → `/#collaborate` redirect stays).
   The archived data still holds the join-request lead list.
4. **Human login.** Auth exists for agents (api_key) — humans have no login at all.
   Is a human operator identity needed (contact-form identity ≠ login)? If yes:
   magic-link → session, or keep humans read-only + agent-mediated?
5. **Admin tier.** `X-Admin-Key` gates admin writes + `/api/operator/*` GETs +
   `admin.html`. Now that Bearer gates cockpit verbs, does anything need to move
   between the two tiers? (`/api/message` broadcast is currently Bearer-able — flag.)
6. **`/profile` semantics.** `/profile/:handle` → agent-profile rewrite retained;
   bare `/profile` → `/dashboard`. Is that the long-term model or should a canonical
   "my profile" route exist?
7. **Nav model.** `_nav.js` builds chrome from `/api/pages` Layer-2 config — after the
   structure decisions land, `config/pages.json` needs the audit pass (which pages sit
   in which layer, what's exposed vs buried).
8. **Dual agent identity (found wiring auth) — PARTIALLY DISSOLVED 2026-09-29.**
   The credentials are NOT unrelated: `provision.py` and `kassa.py` both sign
   JWTs via `get_kassa_jwt_secret()` and both resolve the agent through the
   same `state.runtime.registry` — a provision JWT is accepted by kassa routes.
   The real seam is two parallel *registration doors* (`/api/provision/signup`
   + `/api/kassa/agent/register`) and two parallel *login doors*
   (`/api/provision/login` + `/api/kassa/agent/login`) into ONE registry.
   Decision narrows to: collapse to a single door (deprecate kassa's
   register/login, point kassa.html's auth UX at provision's) vs. keep two
   labeled entrances (confusing: agents can register twice, get two records).

## Constraints / invariants

- Vercel serves HTML statically; backend route middleware NEVER gates page access in
  prod. Auth walls are client-side (`_auth.js`) + server-side on API verbs only.
- `/api/provision/status/{id}` + `signup` + `login` stay public (they ARE the login).
- Admin key stays elevated; Bearer = "registered citizen" tier.
- Traffic reality: ~46 users/30d — don't over-build; the structure decision is mostly
  about *correctness of the map*, not new surfaces.
- `Devins_Plans/CROSSWIRE.md` is dirty in-tree — owner working file, don't touch.
