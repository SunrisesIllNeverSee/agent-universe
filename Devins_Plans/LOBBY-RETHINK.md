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
8. **Dual agent identity (new seam, found wiring auth).** Agents hold TWO unrelated
   credentials: provision `api_key` (`cmd_ak_…`, what `_auth.js`/dashboard verify)
   vs kassa's own `/api/kassa/agent/register|login` JWT. An agent logged into the
   console is still anonymous to kassa posting. Decision: unify (kassa accepts
   provision JWT/api_key) or keep kassa self-contained with its own identity UX.

## Constraints / invariants

- Vercel serves HTML statically; backend route middleware NEVER gates page access in
  prod. Auth walls are client-side (`_auth.js`) + server-side on API verbs only.
- `/api/provision/status/{id}` + `signup` + `login` stay public (they ARE the login).
- Admin key stays elevated; Bearer = "registered citizen" tier.
- Traffic reality: ~46 users/30d — don't over-build; the structure decision is mostly
  about *correctness of the map*, not new surfaces.
- `Devins_Plans/CROSSWIRE.md` is dirty in-tree — owner working file, don't touch.
