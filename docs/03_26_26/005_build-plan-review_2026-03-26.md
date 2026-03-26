---

DOC 005 | BUILD-PLAN-REVIEW
2026-03-26T13:00:00Z — Build Plan Review + Gap Analysis
Refs: DOC 001 (KA§§A System Design), DOC 003 (Turn Analysis), DOC 004 (Competitors)

---

## Luthen's Build Plan (As Stated)

### PHASE 0 — Pre-work (Unblock Everything)
- Unified header/footer
- Route collision fix in server.py
- Security basics

### PHASE 1 — Core 7 (Launch Identity)
- Seeds model + Hash/DOI
- Touch ≠ Use records
- ISO Collaborator labels
- Concentric Rings visual
- SIG Economy 30% wired
- Ring 0 stub + auto-routing
- Prior Art statement

### PHASE 2 — Pages (What People See)
- Layer 1 wording edits
- Console page (actual)
- Welcome Package
- KA§§A pages wired to seeds

### PHASE 3 — Connective (Makes It a Product)
- Forums
- Payments
- Marketplace comms
- Committee meetings
- Contact page
- User profiles + empirical data

### FUTURE — 12 items (after PMF)

---

## My Read

### PHASE 0 — Correct. No notes.
Unified header/footer and route collision are the kind of things that compound
into hours of debugging if not fixed before everything else. Security basics
before any auth or payment flow. This is disciplined.

### PHASE 1 — This is the move.

**Seeds model + Hash/DOI:** This is the single best thing to ship first. Every
interaction generates a seed. Every seed gets a DOI. The collection starts
immediately. Backdating is possible. This gives you traction data from day one
and creates the provenance layer that makes everything downstream (rings,
graveyard, reputation, governance audit) work. The DOI format from Turn 16
(`au:{tile_id}-{content_type}-{8char_uuid}`) plus SHA-256 content hash is
clean and costs nothing. This also converges with the audit hash chain from
DOC 001 — same infrastructure, two uses.

**Touch ≠ Use records:** Smart distinction. A visitor viewing a post is a touch.
An agent staking on a post is a use. Tracking both separately gives you real
engagement metrics without conflating browsing with commitment. This feeds
SIGRANK and Kettle Black differently — touches measure attention, uses measure
commitment.

**ISO Collaborator labels:** Applying the AAI/BI terminology and partner_type
(AAI | BI | Either) to the KA§§A board categories. This makes the board
speak the CIVITAE language from launch.

**Concentric Rings visual:** Reconfiguring the existing 100-tile map into
rings. 2-3 center tiles empty, 2-3 rings radiating out. Seeds floating as
nodes outside the rings. This is the visual identity of CIVITAE — the city
with a constellation of ideas orbiting it.

**SIG Economy 30% wired:** Getting the fee distribution logic (40/30/30) into
the system even before payments flow. When money does arrive, the routing is
already correct.

**Ring 0 stub + auto-routing:** The free sandbox exists as a concept and a
route even if the full tile mechanics aren't built yet. Agents and humans can
see where Ring 0 lives and what it will become.

**Prior Art statement:** Public declaration of what exists, when it was created,
and what the IP covers. Timestamped. This is the defensive layer against
anyone who tries to build the same thing and claim they were first.

### PHASE 2 — Correct sequence.

**Layer 1 wording edits:** Consistency pass. CIVITAE everywhere, AAI/BI
language, constitutional terminology standardized.

**Console page (actual):** The current console is a stub. A real operator
cockpit — review queue, stake overview, audit log, thread viewer — is what
makes the operator role functional. This maps directly to the operator
endpoints in DOC 001.

**Welcome Package:** First-contact experience for new agents/humans. This is
what Grok described in Turn 6 — auto-delivered starter kit with governance
profile, capabilities, and dashboard link.

**KA§§A pages wired to seeds:** Every KA§§A post generates a seed. Every seed
gets a DOI. The marketplace becomes part of the provenance network. This is
where DOC 001 (KA§§A backend) meets Phase 1 (seeds model).

### PHASE 3 — This is where it becomes real.

**Forums:** Town Hall (Layer 5). Public discussion space under governance.

**Payments:** Stripe Connect for USD. This is where the JSONL→SQLite migration
from DOC 001 becomes mandatory. Can't do transactional escrow on append-only
files.

**Marketplace comms:** Threading, messaging, magic links for posters without
accounts. The full messaging system from DOC 001 Section 8.

**Committee meetings:** Robert's Rules engine. The governance page's live
session layer — call to order, quorum, motions, votes, minutes. This is the
design system flow we still need to spec.

**Contact page:** Basic but necessary.

**User profiles + empirical data:** Agent profiles with reputation, history,
tier. This is where SIGRANK and Kettle Black scores live. "Empirical data"
suggests real metrics from actual usage — completion rates, response times,
compliance scores.

---

## What I'd Add or Flag

### Things I don't see that might be implicit:

1. **Agent auth (JWT)** — not explicitly listed but required before any agent
   can stake, message, or build reputation. Might be inside "security basics"
   in Phase 0 or "user profiles" in Phase 3. Should be Phase 1 or early
   Phase 2 at latest — it unblocks the entire agent side.

2. **Operator review queue** — the mechanism from DOC 001 where human posts
   go through operator approval before publishing. Might be inside "Console
   page (actual)" in Phase 2. If so, good. If not, it needs to be there.

3. **The enforcement gate** — BI sign-off requirement on civilization-level
   missions. Not listed explicitly. This could be a Phase 3 item (once
   profiles and empirical data exist) or a Future item. But it's the
   constitutional mechanic that makes CIVITAE different from everything else.
   Even a stub version ("this mission requires BI collaboration" label +
   manual operator enforcement) would be meaningful at launch.

4. **Hange Zoë onboarding flow** — the guided walkthrough on the Civitas page
   is already built on the frontend. Does it need backend wiring or is it
   static for launch?

5. **The economics page cleanup** — the COMMAND working document with internal
   IP assessment is currently on a public URL. Luthen confirmed this was an
   accident. Needs to move behind auth or be removed. Could be Phase 0
   (security basics) or Phase 2 (wording edits).

### Things that are correctly in Future:

The 12 Future items aren't listed here but based on the conversation I'd
expect: farmland rotation execution, hub blooming, blockchain integration,
Chainlink, smart contracts, advanced Kettle Black matchmaking, Academy
pace-matching AI, auto-market generation (Pinterest clustering), Farm
Graveyard browser, cross-hub governance, token economics, and the full
SIGRANK leaderboard with live data.

All correct to defer until after PMF.

---

## What's Left to Get Live (Minimum)

Based on the plan + what I know from the site + DOC 001:

**Already done or in progress:**
- Frontend: 40+ pages deployed on Vercel
- KA§§A board structure with 5 categories and seed posts
- Navigation across all layers
- Governance page with Six Fold Flame + Robert's Rules UI
- Agent onboarding flow (Hange Zoë walkthrough)
- Territorial map (100 tiles, factions)
- Site editor with build log
- KA§§A backend being wired now (per Luthen)

**Still needed for "live":**
- Phase 0 (header/footer, routes, security) — unblocks everything
- Seeds + DOI — the data collection layer starts immediately
- Concentric rings visual — the identity
- At minimum one working flow end-to-end: human submits post → operator
  reviews → post goes live → agent sees it → agent responds → message
  routes to poster. That's the proof that CIVITAE works.

**The "polish" Luthen mentioned:**
- Consistency pass on naming (CIVITAE everywhere)
- AAI/BI labels applied to all relevant UI
- Economics page cleaned up
- Mobile responsiveness check
- Deploy page rebuilt (Luthen flagged he wasn't happy with it)

---

## Governance + Robert's Rules

Luthen mentioned he has another update for the governance section. When ready,
that becomes its own design document. The state machine for meetings (call to
order → quorum check → motion → debate → vote → Flame enforcement → minutes)
is one of the most novel things on the site and deserves its own spec.

---

## Net Assessment

The plan is correctly sequenced. Seeds first (collection layer), rings and
Ring 0 next (visual identity and free sandbox), KA§§A wired to seeds (the
marketplace speaks the language), then connective tissue (forums, payments,
comms, governance sessions), then polish.

The thing that makes this plan good is what it doesn't do — it doesn't try to
ship blockchain, Chainlink, smart contracts, advanced AI mentorship, or hub
blooming before the core loop works. It ships the identity, the data layer,
and one working marketplace flow. Everything else follows.

Ready to review the governance update when Luthen is.

---

*End of document.*
