# KA$$A SPECS -- GEMS & LOG FOR AGENT-UNIVERSE

**Extracted:** 2026-03-20
**Source:** 42 files in /tmp/kassa-files/files-3/
**Purpose:** Category 1 = apply now to agent-universe. Category 2 = structured reference for later.

---

# CATEGORY 1 -- GEMS FOR AGENT-UNIVERSE (APPLY NOW)

Items from the KA$$A specs that directly apply to the agent-universe build. Each gem lists the source file, the extracted content, and exactly where in agent-universe it should be applied.

---

## 1.1 CASCADE ENGINE MATH -- TETRACTYS (LAUNCH ENGINE)

**Source:** CASCADE-ENGINE-DECISIONS.md, CLAUDE-MD-KASSA-BUILD.md

The Tetractys is the launch cascade engine. The 5-3-5-3 cascade wave is the later/enterprise option.

**Tetractys Formula:**
```
Seat pattern:    5 - 4 - 3 - 2 - 1  (15 seats)
Multiplier:      1.5x per wave (default)
Options:         1.25x (gentle) / 1.5x (default) / 2.0x (steep)

base = total / weighted_sum
weighted_sum = 5(1) + 4(1.5) + 3(1.5^2) + 2(1.5^3) + 1(1.5^4)

Example at $5,000 base, 1.5x:
  W1: 5 seats x $5,000  =  $25,000
  W2: 4 seats x $7,500  =  $30,000
  W3: 3 seats x $11,250 =  $33,750
  W4: 2 seats x $16,875 =  $33,750
  W5: 1 seat  x $25,313 =  $25,313
  Total: 15 seats, $147,813
```

**Two entry points (same output):**
- Entry A: "My starting seat price is $X" -- system generates 5 waves
- Entry B: "I want to raise $Y" -- system back-calculates base price

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/economy.py` -- add Tetractys cascade calculator alongside existing tier/fee system. Also wire into `/Users/dericmchenry/Desktop/agent-universe/frontend/economics.html` for display.

---

## 1.2 CASCADE ENGINE MATH -- ENTERPRISE (5-3-5-3, DIVISOR 38)

**Source:** CASCADE-ENGINE-DECISIONS.md

**Enterprise Cascade Formula (later/premium):**
```
Seats:      5 - 3 - 5 - 3  (16 total)
Multiplier: 1 - 2 - 3 - 4
Weight:     5(1) + 3(2) + 5(3) + 3(4) = 5 + 6 + 15 + 12 = 38
Divisor:    38

base = total / 38
```

**Multiplier Presets:**
```
AGGRESSIVE (1-2-3-4):  Divisor 38.  Steps: +100%, +50%, +33%
MODERATE (1-1.5-2-2.5): Divisor 27. Steps: +50%, +33%, +25%
GENTLE (1-1.25-1.5-1.75): Divisor 21.5. Steps: +25%, +20%, +17%
```

**Internal/Embedded Ladder Structure:**
```
INTERNAL (5 seats each): C1 base x 1, C3 base x 3 -- buyer uses product inside org
EMBEDDED (3 seats each): C2 base x 2, C4 base x 4 -- buyer redistributes to customers
```

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/economy.py` -- implement as a separate cascade mode alongside Tetractys. This is the COMMAND pricing structure.

---

## 1.3 WAVE ZERO MECHANICS (25-SEAT DEMAND TEST)

**Source:** KASSA-BUILD-BRIEF-v2.md, KASSA-KERNEL.md

**Wave Zero spec:**
```
Seats:    25 (platform-wide constant, same for every listing)
Price:    $20-50 per seat (low fixed price, likely $30)
Escrow:   ALL-OR-NOTHING. Money held until all 25 seats fill.
          If filled -> founder gets paid, real cascade opens.
          If never filled -> all buyers refunded.
Time:     No time limit. Sits until it fills or founder pulls it.
No offers: fixed price, no negotiation during Wave Zero.
```

**What Wave Zero solves:**
- Quality gate: 25 people must spend $30 -- proves demand exists
- Fairness: every founder enters the same way
- Buyer trust: zero risk (refund if not filled)
- Scoring: Wave Zero velocity = first hard data point for product scores
- Platform economics: 25 x $30 = $750 per listing through the gate

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/frontend/wave-registry.html` -- the wave registry should display Wave Zero status. Also implement Wave Zero logic in `/Users/dericmchenry/Desktop/agent-universe/app/economy.py` with the all-or-nothing escrow state machine.

---

## 1.4 FEE STRUCTURE AND TIER ECONOMICS

**Source:** KASSA-SPEC-v03.md, KASSA-BUILD-BRIEF.md, economy.py (existing)

**Platform fee structure from KA$$A specs:**
```
Platform fee:    3-5% of purchase price (on founder side, not buyer)
Referrer commission: 25% of platform's fee (from platform's cut, not founder's)

Example on a $1,000 seat with referral:
  Buyer pays:        $1,000
  Platform fee (4%): $40
  Referrer (25%):    $10
  Platform net:      $30
  Founder receives:  $960 (after escrow)
```

**This maps directly to agent-universe's existing tier system:**
```python
# Already in economy.py:
UNGOVERNED:     15% fee
GOVERNED:        5% fee
CONSTITUTIONAL:  2% fee
BLACK CARD:      1% fee
```

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/economy.py` -- the tier fees are already implemented. The KA$$A marketplace fee (3-5%) should be added as the external marketplace layer on top of the internal governance tiers. The referrer commission split (25% of platform cut) should be wired into the referral attribution system.

---

## 1.5 BOARD UI PATTERNS -- SHELF + LIST/GRID

**Source:** KASSA-KERNEL.md, kassa-marketplace.html, kassa-listings-board.html

**Board layout specification:**
```
TOP SECTION -- curated shelves (editorial, horizontal scroll):
  - Featured (hand-picked)
  - Hot Right Now (high velocity, Wave Zeros close to clearing)
  - New Listings (recently approved)
  - Trending (rising interest over 7-14 days)
  - Suggested (personalized, future)

  Each shelf: compact cards, horizontal scroll, product name, founder,
  sector tag, wave status, price, seats remaining, score, trend arrow.

BOTTOM SECTION -- The Board (full list, tabbed by sector):
  - Default: list view (dense, scannable, one row per listing)
  - Toggle: grid view (card layout)
  - Sector tabs: All | AI Governance | Developer Tools | Commerce | etc.
```

**List row format:**
```
[Status Badge] | Product Name (check) | Sector | Wave Progress Bar | Price | Score | Trend
                 Founder name                    Wave N -- X / Y seats
```

**Status badges:** Wave 0 (muted), Wave 1/2/3 Open (gold), Hot (red), New (blue), Sold Out (dark)
**Trend indicators:** rising (green arrow up), steady (gray arrow right), cooling (red arrow down)
**Sort options:** Trending (default), Newest, Price low-high, Price high-low, Score

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/frontend/kassa.html` -- this is already a KA$$A marketplace page. Implement the shelf + board dual-section layout. The horizontal-scroll shelf rows with compact cards are the key pattern. The list/grid toggle with sector tabs goes in the board section.

---

## 1.6 LISTING CARD STRUCTURE

**Source:** KASSA-BUILD-BRIEF.md, kassa-listings-board.html, CLAUDE-MD-KASSA-BUILD.md

**Card contents:**
```
- Product name
- Founder name (with verified checkmark)
- Sector/category tag
- Cascade type badge (Enterprise / SaaS / Component)
- Current wave + seats remaining
- Current seat price (in monospace)
- Status badge (Pending, Active, New, Sold Out)
- Mini wave progress bar
- Trend indicator arrow
- Score (number or dash if too new)
```

**Card CSS pattern (from kassa-listings-board.html):**
```css
.card {
  background: white; border: 1px solid var(--sand); border-radius: 10px;
  padding: 24px; transition: transform 0.2s, box-shadow 0.2s; cursor: pointer;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(26,26,24,0.06); }
```

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/frontend/kassa.html` -- use this card pattern for listings. The hover lift (translateY -2px) and subtle shadow expansion are the right interaction pattern for the KA$$A brand.

---

## 1.7 SEAT SERIALIZATION FORMAT

**Source:** KASSA-SEAT-INSTRUMENT-SPEC.md (DOC-004), KASSA-BUILD-BRIEF.md

**Serial format:**
```
FORMAT: KS-{YEAR}-{SEQUENCE}
Examples: KS-2026-00001, KS-2026-00147, KS-2027-03841

Properties:
  - Sequential across entire platform (not per product)
  - Year prefix for temporal context
  - Zero-padded to 5 digits (supports 99,999 seats per year)
  - Globally unique
  - Immutable once assigned at MINT
```

**Extended serial (for product context):**
```
KS-2026-00147 / SWAI-W1-S07
  KS-2026-00147  = Platform-wide serial
  SWAI           = Product code (SuperWriter AI)
  W1             = Wave 1
  S07            = Seat 7 in that wave
```

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/economy.py` -- add a serial number generator function. Also wire into the wave-registry display at `/Users/dericmchenry/Desktop/agent-universe/frontend/wave-registry.html`.

---

## 1.8 LINEAGE HASHING (SHA-256 CHAIN)

**Source:** KASSA-SEAT-INSTRUMENT-SPEC.md, FTO-QUICK-REFERENCE.md, AGENT-READY-DATA-MODEL.md

**Hash chain structure:**
```
Each event hash = SHA-256(
  previous_hash +
  event_type +
  timestamp +
  seat_serial +
  actor_id +
  event_data
)

Event types: MINT, ACTIVATE, CLAIM, RELEASE, TRANSFER, DISTRIBUTE,
             REVERT, REVOKE, BUYBACK, RETIRE

Genesis hash = SHA-256(
  cascade_id + product_id + founder_id +
  creation_timestamp + total_seats + wave_structure_json
)
```

**The chain self-verifies:** Recompute each hash from its inputs. If any mismatch, chain is BROKEN.

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/chains.py` -- this file likely already has chain-related logic. Implement the seat lineage hash chain here. Also add to `/Users/dericmchenry/Desktop/agent-universe/app/audit.py` for the verification logic.

---

## 1.9 AGENT PROTOCOL -- NULLABLE FIELDS FOR FUTURE AGENT LAYER

**Source:** AGENT-READY-DATA-MODEL.md

**Add to seat/lineage types NOW (all nullable, no logic changes):**
```typescript
// Agent provenance on seats:
agent_id?: string | null;
agent_operator_id?: string | null;
constitutional_frame_hash?: string | null;  // SHA-256 of agent governance constraints
intent_id?: string | null;
referral_chain?: object | null;  // array of {agent_id, operator_id, role}

// Agent provenance on lineage events:
agent_id?: string | null;
agent_operator_id?: string | null;
constitutional_frame_hash?: string | null;

// Signature fields:
classical_signature?: string | null;   // ECDSA (future)
pq_signature?: string | null;          // ML-DSA/FIPS 204 (future)

// Emblem fields:
emblem_url?: string | null;
emblem_hash?: string | null;
```

**Rule:** If agent fields are non-null, include them in hash computation. If null, exclude from hash input. Agent-facilitated and direct purchases produce different hashes.

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/models.py` -- add these nullable fields to seat and lineage event models. The existing `GovernanceState` model already tracks governance state; these fields extend that to seat-level provenance.

---

## 1.10 AGENT PROTOCOL -- TRANSACTION FIREWALL

**Source:** KASSA-AGENT-PROTOCOL.md, FTO-QUICK-REFERENCE.md

**Core principle:** Agents discover and stage. Humans confirm and pay. This boundary is ARCHITECTURAL, not a UI choice. No code path allows an agent to execute a financial transaction.

**Intent staging lifecycle:**
```
Agent discovers listing -> Agent creates intent (staged) ->
Human reviews intent -> Human confirms/rejects ->
If confirmed: human executes payment
```

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/router.py` -- the router should enforce that agent-initiated actions cannot reach payment endpoints. Also relevant to `/Users/dericmchenry/Desktop/agent-universe/app/moses_core/governance.py` where constitutional governance enforces agent boundaries.

---

## 1.11 SELL-THROUGH GATE (DETERMINISTIC STATE MACHINE)

**Source:** FTO-QUICK-REFERENCE.md, CASCADE-ENGINE-DECISIONS.md

**Rule:** Wave N+1 CANNOT activate until Wave N seats_sold == seats_total. No override. No admin bypass. No exception. Enforce structurally.

**Fixed-price waves:** Price is deterministic per wave. Transparent, predictable, non-negotiable. This is how KA$$A differs from auctions and bid systems.

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/economy.py` -- implement as a state machine. The sell-through gate is the core enforcement mechanism for cascade integrity.

---

## 1.12 TRUTH-TELLING MECHANIC (FILL VELOCITY AS SCORE)

**Source:** CASCADE-ENGINE-DECISIONS.md

**Fill velocity IS the implicit scoring system:**
```
FILLS INSTANTLY:   Underpriced. Next cascade starts higher.
STEADY FRICTION:   Priced right. Market working normally.
STALLS:           Overpriced. Reset with market signal.
```

**The board does NOT need a separate scoring system at launch.** The wave progress bar on each listing IS the score. Buyers can read demand directly from fill state.

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/frontend/kassa.html` -- the progress bar is the primary scoring indicator. No separate scoring UI needed at launch. The velocity calculation should live in `/Users/dericmchenry/Desktop/agent-universe/app/economy.py`.

---

## 1.13 BRAND IDENTITY TOKENS FOR KA$$A PAGE

**Source:** KASSA-BRAND-IDENTITY.md (DOC-007), CLAUDE-MD-KASSA-BUILD.md

**Color system:**
```css
--gold: #C4923A;        /* Primary brand, section symbol, CTAs */
--bone: #F2EDE4;        /* Background (Bone White) */
--obsidian: #1A1A18;    /* Primary text */
--drift: #6B6558;       /* Secondary text (Driftwood) */
--sand: #DDD5C8;        /* Borders (Sandstone) */
--verdigris: #4A7C59;   /* Success/positive */
--terra: #B44A3F;       /* Warning/scarcity (Terracotta) */
--slate: #3A6B8C;       /* Info/links (Slate Blue) */
--charcoal: #2A2A25;    /* Dark surfaces */
--dark-border: #3A3830; /* Dark mode borders */
```

**Dark mode:** Background #1A1A18, Surface #2A2A25, Text #F2EDE4, Gold #C4923A (never changes).

**Typography:**
```
Display/Headlines: Playfair Display 700 (serif -- communicates permanence)
Body/UI:           DM Sans 400/500/600 (clean sans-serif)
Data/Numbers:      DM Mono 400/500 (monospace -- prices, serials, hashes)
```

**Type scale:**
```
Hero:        48px / Playfair Display Bold
H1:          36px / Playfair Display Bold
H2:          28px / Playfair Display Bold
H3:          20px / DM Sans SemiBold
Body:        16px / DM Sans Regular
Body small:  14px / DM Sans Regular
Caption:     12px / DM Sans Medium
Label:       11px / DM Sans SemiBold, uppercase, 0.08em tracking
Data:        14px / DM Mono Regular
Data large:  22px / DM Mono Bold
Micro:       10px / DM Mono Regular
```

**The section symbol (SS) is ALWAYS gold (#C4923A)** regardless of surrounding text color. In headlines, may be 110% of surrounding text size.

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/frontend/kassa.html` -- this page already uses these tokens. Ensure all CSS variables match the spec above. Also apply to any KA$$A-facing pages in the frontend directory.

---

## 1.14 VOICE AND COPY RULES

**Source:** KASSA-BRAND-IDENTITY.md, KASSA-BUILD-BRIEF-v2.md

**Do say:**
- "Claim your seat" not "Buy now"
- "Founding cascade" not "Pricing tiers"
- "Wave 2 -- 3 remaining" not "Only 3 left!"
- "Seat KS-2026-00003" not "Order #3"
- "Founding seat" not "Lifetime deal"
- "Instrument" for the seat as a financial object
- "Commitment" for what the buyer makes
- "Constitutional" for governance (the MO$E$S connection)

**Never say:** "Revolutionize", "disrupt", "game-changing", "cutting-edge", "We're excited to...", "In today's rapidly evolving landscape...", "AI-powered" as primary descriptor

**No emojis anywhere in UI.** Numbers always in DM Mono font. Always.

**Tone:** Direct, precise, confident, grounded, architectural. "A trading floor with taste."

**Apply to:** All KA$$A-facing frontend copy in `/Users/dericmchenry/Desktop/agent-universe/frontend/kassa.html` and `/Users/dericmchenry/Desktop/agent-universe/frontend/wave-registry.html`.

---

## 1.15 HOMEPAGE = BOARD (WITH MODAL ONBOARDING)

**Source:** CLAUDE-MD-KASSA-BUILD.md

**The board IS the homepage.** No separate landing page.

**First-time visitors:**
```
1. Page loads -> Board renders underneath, dimmed/blurred
2. Modal 1: Hero content -- "Claim your founding seat" pitch
3. Modal 2: Founders pitch -- "One committed customer > 5,000 free trials"
4. Modal 3: Built for builders tiles -- Founders / Buyers / Agents
5. Modal 4: Agents section + pointer to header nav
6. Close last modal -> Board fully revealed, interactive
```

**Returning visitors skip modals entirely** (localStorage/cookie flag).

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/frontend/kassa.html` -- restructure so the board is the primary view, with a modal sequence for first-time visitors.

---

## 1.16 PRODUCT LISTING DATA MODEL

**Source:** KASSA-BUILD-BRIEF-v2.md, KASSA-SPEC-v03.md

**Key fields for listing:**
```
Product name, slug (unique)
description (human-readable)
description_short (one-line)
description_machine (agent-readable JSON)
category
license_type: perpetual | subscription | enterprise
monthly_price (reference for LTV calc)
expected_lifespan_months
ltv_ratio (calculated)
pricing_mode: ltv_suggested | custom
offers_enabled: boolean (not in Wave Zero)
escrow_days: integer (default 14)
wave_zero_cleared: boolean
product_score: numeric
trend: rising | steady | cooling
review_status: pending | approved | rejected | changes_requested
status: draft | in_review | wave_zero | active | paused | completed
```

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/models.py` -- add Product/Listing model with these fields.

---

## 1.17 LTV MULTIPLIER FORMULA (FLOATING MOAT STANDARD)

**Source:** KASSA-SEAT-INSTRUMENT-SPEC.md (DOC-004)

**Formula:**
```
Seat Price = LTV Multiplier (lambda) x eLTV
eLTV = Monthly Price x Expected Customer Lifespan (months)
Lifespan = 1 / Monthly Churn Rate (if known)

Multiplier ranges:
  Below 1.0x: Founder underpricing
  1.0x - 1.3x: Fair value
  1.3x - 1.7x: Premium (permanence + transferability)
  1.7x - 2.0x: High premium
  Above 2.0x: Overpriced
```

**Industry benchmarks:**
```
B2C SaaS:          18 months conservative
Small Biz SaaS:    30 months
Mid-Market SaaS:   42 months
Enterprise SaaS:   84 months
Dev Tools / API:   48 months
Creator Tools:     24 months
Hardware+Software:  60 months
```

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/economy.py` -- implement LTV calculator function for the pricing tool. Display on `/Users/dericmchenry/Desktop/agent-universe/frontend/economics.html`.

---

## 1.18 KILL SWITCHES (CASCADE VIABLE RANGE)

**Source:** CASCADE-ENGINE-DECISIONS.md

```
TOO LOW (suggested floor):
  Base ~$500 minimum -> ~$19K total at Aggressive
  Below this: infrastructure cost exceeds value
  Signal: product should sell subscriptions, not seats

TOO HIGH (suggested ceiling):
  Base ~$10-25K -> ~$380-950K total at Aggressive
  Above this: 16 buyers at escalating prices don't exist
  Signal: product belongs in bespoke/white-label

SWEET SPOT: $1,000 - $10,000 base
  $38K - $380K total (Aggressive)
```

Platform implementation: suggested floor/ceiling with warnings. Not hard blocks -- guidelines. Founder can override but gets a flag.

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/economy.py` -- add validation with soft warnings for cascade pricing.

---

## 1.19 FTO LEGAL GUARDRAILS (FIVE THINGS NOT TO BUILD)

**Source:** FTO-QUICK-REFERENCE.md

**These are patent-collision avoidance rules. Non-negotiable:**

1. **NO BLOCKCHAIN / NO SMART CONTRACTS / NO ON-CHAIN TOKENS** -- Seats are database records. Lineage lives in our database. Do not deploy to any blockchain. (US11907916B2, through 2037)
2. **NO BID/PROPOSAL-BASED SEAT ALLOCATION** -- Primary sales are fixed price per wave. Period. Offers do NOT determine allocation order. (US12148026B2, through 2042)
3. **NO TIME-WINDOW REFUND/REDEMPTION** -- Waves do NOT have time limits triggering refunds. (US11861637B2, through 2040)
4. **NO PUBLIC LEDGER AS VERIFICATION SUBSTRATE** -- Verification via our API returning signed receipts, not blockchain state queries. (US10931457B2)
5. **NO ON-CHAIN/OFF-CHAIN BRIDGE** -- Seats live on our platform. Period. (US11341466B2)

**Quick test before implementing any seat feature:**
```
1. Does this put seat data on a blockchain? -> Stop.
2. Does this let offers determine who gets a seat? -> Stop.
3. Does this add a time window that triggers refunds? -> Stop.
4. Does this require a distributed ledger for verification? -> Stop.
5. Does this embed transfer policy in the instrument itself? -> Stop.
   (Server enforces policy, not the instrument.)
```

**Apply to:** EVERY file in agent-universe that touches seats, economy, or instruments. These are hard constraints on the architecture.

---

## 1.20 CASCADE RESET MECHANICS

**Source:** CASCADE-ENGINE-DECISIONS.md

**Floor rule:** No relisting below last completed wave price.

**When a cascade stalls, half-sold wave buyers get two choices:**
```
OPTION A: CLOSE OUT
  Full refund. Seat released. Clean exit.

OPTION B: HOLD POSITION
  Refund the difference between old price and new cascade price.
  Plus a discount for holding through the stall.
  Seat transitions into new cascade.
```

**New cascade rules:**
```
1. Base price >= last completed wave price (floor rule)
2. Fresh 5-3-5-3 structure from new base
3. Founder can choose different multiplier preset
4. Cooling period before renewal (TBD: 30/60/90 days)
5. Roll-forward buyers slot in at negotiated discount
```

**Apply to:** `/Users/dericmchenry/Desktop/agent-universe/app/economy.py` -- implement reset state machine with floor enforcement.

---

# CATEGORY 2 -- LOG FOR LATER

Everything important but not immediately applicable to the current agent-universe build.

---

## 2.1 PATENT FILING (PPA5 CASCADE REGISTER v2)

**Source:** PPA5-CASCADE-REGISTER.md, PPA5-CASCADE-REGISTER-v2.md

**Full title:** System and Method for Demand-Validated Cascade Distribution of Commercial Instruments with Commitment-Governed Escrow, Serialized Seat Provenance, Wave-Gated Pricing Progression, Lifetime-Value-Anchored Pricing, Agent-Mediated Discovery, and Recursive Governance Architecture

**Applicant:** Deric J. McHenry / Ello Cello LLC
**Related applications:** Serial No. 63/877,177 (MO$E$S Constitutional Governance), Serial No. 63/883,018 (Signal Compression), U.S. Nonprovisional 19/426,028 (CIVITAS), February 25 2026 PPA (Semantic Commitment Conservation)

**11 components, 32 claims.** Updated per FTO research to explicitly use non-blockchain architecture throughout.

**Status:** Reference only. Do not build patent-specific features until instructed.

---

## 2.2 SEAT EMBLEM SYSTEM

**Source:** KASSA-SEAT-INSTRUMENT-SPEC.md

The emblem is a visual certificate of authenticity generated at RELEASE (escrow clears). Contains: product logo, serial number, wave/seat position, holder name, issue date, QR code linking to verification page, lineage hash, "powered by MO$E$S" attribution.

**Emblem design principles:** Centered section symbol in gold, serial in DM Mono, product name in Playfair Display, muted border with subtle pattern, QR code to verification page.

**Phases:** Phase 1 = manual. Phase 2 = auto-generated. Phase 3 = customizable with founder branding.

**Status:** Deferred. Build when transaction flow is live.

---

## 2.3 DUAL-SIGNATURE VERIFICATION (ECDSA + POST-QUANTUM)

**Source:** FTO-QUICK-REFERENCE.md, KASSA-SEAT-INSTRUMENT-SPEC.md

Every seat instrument gets two signatures:
- Classical: ECDSA (Ed25519)
- Post-quantum: ML-DSA / FIPS 204 (Dilithium/Falcon)

The lineage root hash passes through the MO$E$S compression gate. Both signatures ensure the lineage is verifiable today AND quantum-resistant.

**Status:** Future. The nullable fields (classical_signature, pq_signature) go in now per Category 1 item 1.9. The actual signing system is deferred.

---

## 2.4 WAVE ZERO VOUCH MECHANIC (TETRACTYS MARKET DISCOVERY)

**Source:** CASCADE-ENGINE-DECISIONS.md

Future state: The Tetractys becomes the Wave Zero vouch mechanic when agent-driven traffic makes it viable. Starting at $1, rows expanding (1-2-3-4-5...), where the market climbs tells the engine what the base price should be. The founder stops inputting the number -- the market writes it.

**Status:** Deferred until agent traffic exists.

---

## 2.5 DISTRIBUTION ALLOCATIONS

**Source:** KASSA-SEAT-INSTRUMENT-SPEC.md (Section 8)

Allows approved entities to acquire multiple seats with obligation to transfer each to an individual end holder within a defined window. Distributor types: newsletters, accelerators, companies, influencers, agencies, conferences.

Key mechanic: seats NOT transferred by deadline REVERT to cascade. No refund for reverted seats. Prevents hoarding disguised as distribution.

Pricing models: Full wave price, negotiated bulk rate, or sponsored (free to distributor, founder "spends" seats as marketing).

**Status:** Deferred. Implement when marketplace has listings.

---

## 2.6 MERCHANT OF RECORD (MoR) ARCHITECTURE

**Source:** KASSA-SEAT-INSTRUMENT-SPEC.md (Section 9)

Hybrid model recommended:
- Founders WITH companies -> Stripe Connect (founder is MoR)
- Founders WITHOUT companies -> KA$$A as MoR
- Distribution allocations -> always KA$$A as MoR

**Status:** Deferred. Manual Stripe through Luthen at launch.

---

## 2.7 SCORING SYSTEM (FOUNDER + PRODUCT)

**Source:** KASSA-BUILD-BRIEF-v2.md

**Founder Score:** Identity verification (required), entity verification (high), product demo (required), listing history (medium), responsiveness (low).

**Product Score:** Sell-through velocity (high), demand trend (high), value position (high), category rank (medium), completion rate (medium). Display: overall score with sparkline trend chart.

**Trend Indicators:** Rising (green), Steady (neutral), Cooling (red). Calculated from page views, saves, offer volume, purchase velocity.

**Status:** Deferred. Fill velocity IS the score at launch (see Category 1, item 1.12).

---

## 2.8 OFFER/NEGOTIATION SYSTEM

**Source:** KASSA-BUILD-BRIEF-v2.md, KASSA-KERNEL.md

Founder can toggle "Accept offers" per listing (not available during Wave Zero). Buyer submits offer below wave price. Founder accepts/rejects/counters. Accepted offer = seat sold at offer price, counts against wave inventory.

**FTO WARNING:** Offers are a bilateral overlay. They do NOT rank, queue, batch, or sequence against shared inventory. They do NOT determine allocation order. (Patent collision: US12148026B2)

**Status:** Deferred. May be replaced permanently by cascade truth-telling mechanic.

---

## 2.9 AGENT API & REFERRAL ATTRIBUTION

**Source:** KASSA-AGENT-PROTOCOL.md (DOC-005)

Full agent interaction protocol:
- Agent-readable API (JSON, description_machine field)
- Intent staging system (agent stages, human confirms)
- Agent registry with constitutional frame hashing
- Multi-agent attribution model (seller-configured commission splits)
- Referral chain: array of {agent_id, operator_id, role, timestamp}
- Commission cap: 10 sales/operator/product/month
- Attribution window: 7 days proposed
- Rate limiting: 10 intents/hour/agent, 50/hour/operator

**API endpoints spec'd:**
```
GET  /api/listings              (agent-compatible JSON)
GET  /api/listings/[slug]       (with description_machine)
POST /api/agent/intent          (stage an intent)
GET  /api/agent/intent/[id]     (check intent status)
POST /api/agent/register        (register agent + constitutional frame)
GET  /api/verify/[serial]       (public seat verification)
```

**Status:** Deferred until agent traffic exists. The nullable fields go in now (Category 1, item 1.9).

---

## 2.10 SEO & DISCOVERY STRATEGY

**Source:** KASSA-SEO-STRATEGY.md (DOC-003), WAVE-CASCADE-SEO-STRATEGY.md

Key insight: AI product ranking generators are PRODUCTS to list on the marketplace, not just infrastructure. Creates a recursive loop -- generator ranks products, drives traffic to marketplace, has its own listing on marketplace.

Programmatic SEO architecture: every listing = unique indexable page targeting long-tail keywords. Structured data for AI Overviews. GEO (Generative Engine Optimization) strategy.

**Status:** Log for when KA$$A page goes live.

---

## 2.11 OUTREACH TARGETS (25 COMPANIES)

**Source:** KASSA-OUTREACH-TARGETS.md (DOC-006)

**Tier 1 (10 companies):** Anything, Computer Agents, NoahAI, CyreneAI, Superdesign, Instruct, Loki.Build, Flux, Dvina, Aident AI. All bootstrapped/early, live products, AI-adjacent.

**Tier 2 (10 companies):** Agentfield, 21st Fund, Appaca, Basis, Naratix, Enhans, Voiceflow, AirOps, Lindy AI, Grov. Slightly larger, high fit.

**Tier 3 (5 ecosystem plays):** OpenClaw/ClawHub (skill submission), Product Hunt (launch channel), YC Alumni, Indie Hackers community, Superteams (Solana builders).

**Status:** Log for outreach when platform is ready.

---

## 2.12 FINANCIAL PROJECTION MODEL

**Source:** kassa-financial-model.jsx, kassa-projection-v2.jsx

Interactive React component with sliders for: founders/month, founder growth %, avg seat price, seats per cascade, sell-through %, waves, wave multiplier, platform fee %, referral commission %, agent mix %, monthly op cost.

Three scenarios: conservative (0.6x growth), base (1.0x), aggressive (1.5x).

Key formulas:
```
seatsPerFounderPerMonth = (totalSeatsPerFounder x sellThrough%) / 6
totalGMV = totalSeats x avgWeightedPrice
platformRevenue = totalGMV x effectiveFee
referralCost = referralGMV x effectiveFee x referralCommPct
netRevenue = platformRevenue - referralCost
```

**Status:** Reference for financial planning. Not for current build.

---

## 2.13 WAVE CASCADE PRODUCT FIT ANALYSIS

**Source:** wave-cascade-product-fit.jsx

Real products analyzed with cascade modeling: Superhuman, Clubhouse, Notion, Figma, Linear, Vercel, Descript, Obsidian, Arc Browser, Readwise. Each analyzed for: what happened without cascade, what would happen with cascade, why it works, distribution lift.

**Status:** Reference for pitch materials and outreach.

---

## 2.14 WAVE CASCADE USE CASES

**Source:** wave-cascade-use-cases.jsx

Detailed use cases across categories: enterprise (COMMAND, governance), SaaS writing tools, API/dev tools, creator tools. Each with worked cascade examples showing wave progression and revenue.

**Status:** Reference for product positioning.

---

## 2.15 MOSES BRAND ASSETS

**Source:** moses-icon.svg, moses-logo-v2.svg, moses-logo-v3.svg, moses-brand-positioning.jsx

SVG logos with gold gradient on dark background. Section symbol as hero mark. "COMMITMENT HAS PHYSICS" tagline.

Logo variants: v2 has noise filter texture, v3 is cleaner with evenly spaced characters.

**Status:** Assets available for use in agent-universe frontend.

---

## 2.16 BUYBACK CLAUSE TEMPLATES

**Source:** KASSA-SEAT-INSTRUMENT-SPEC.md (Section 1.6)

Three templates:
```
Template A -- Pro-Rata (recommended for SaaS):
  Buyback = Seat Price x (Remaining Lifespan / Total Lifespan)

Template B -- Market Value (for appreciating products):
  Buyback = most recent wave price at time of acquisition

Template C -- No Buyback (caveat emptor):
  Buyer accepts full risk of product lifespan
```

Founders MUST select one. Field cannot be blank.

**Status:** Deferred until transaction terms are needed.

---

## 2.17 ESCROW MECHANICS

**Source:** KASSA-BUILD-BRIEF-v2.md, KASSA-SEAT-INSTRUMENT-SPEC.md

Wave Zero: all-or-nothing escrow (held until all 25 fill or founder pulls listing).
Waves 1+: per-seat escrow (14 days per purchase, independent).
Escrow release triggers: time expiration + product access confirmation.

**Status:** Deferred. Manual through Luthen at launch.

---

## 2.18 COWORK WORKSPACE CONTEXT

**Source:** COWORK-WORKSPACE-PROMPT.md

Active workstreams as of 2026-03-06:
1. Investor outreach (Bryan Kim @ a16z, Peter Zakin @ Upfront VC)
2. Gumroad/Lemon Squeezy listing ($149-299 COMMAND starter kit)
3. KA$$A board build
4. File cleanup

Critical rules: Read FTO before writing seat code. No blockchain. Tetractys is launch engine. Payments through Luthen's Stripe. COMMAND listed but KA$$A's own listing TBD.

**Status:** Operational context. Reference when working on related builds.

---

## 2.19 PRE-BUILD PLANNING (HOSTING & GTM)

**Source:** KASSA-PRE-BUILD-PLAN.md (DOC-002), WAVE-CASCADE-PRE-BUILD-PLAN.md

**Hosting decision:** Vercel + Supabase for Phase 1 ($0-45/month).
**Stack:** Next.js 14+ App Router, Supabase (Postgres + Auth + RLS), Stripe, Tailwind, Google Fonts.
**GTM:** Cold start via AI-generated profiles from public data, personal onboarding of 20-30 products, COMMAND as listing #1, Product Hunt launch.

**Status:** Reference for deployment decisions.

---

## 2.20 COMPLETE DOCUMENT INDEX

**Source:** KASSA-DOC-INDEX.md

| Doc ID | Title |
|--------|-------|
| DOC-001 | Product Specification (KASSA-SPEC-v03.md) |
| DOC-002 | Pre-Build Planning (KASSA-PRE-BUILD-PLAN.md) |
| DOC-003 | SEO & Discovery Engine (KASSA-SEO-STRATEGY.md) |
| DOC-004 | Seat Instrument Specification (KASSA-SEAT-INSTRUMENT-SPEC.md) |
| DOC-005 | Agent Interaction Protocol (KASSA-AGENT-PROTOCOL.md) |
| DOC-006 | Outreach Target List (KASSA-OUTREACH-TARGETS.md) |
| DOC-007 | Brand Identity & Positioning (KASSA-BRAND-IDENTITY.md) |
| DOC-008 | Build Brief v2 (KASSA-BUILD-BRIEF-v2.md) |

**IP Provenance:** All KA$$A documentation describes commercial applications of MO$E$S. Independent IP resides in MO$E$S, not KA$$A. Wave cascade, commitment conservation, seat lineage hashing, dual-signature, compression gate, floating moat standard, constitutional agent governance = MO$E$S IP. KA$$A brand, serial format, emblem, verification API = KA$$A product features.

---

## 2.21 SEAT REGISTRY FIX (FORMSPREE WIRING)

**Source:** SEAT-REGISTRY-FIX.md

Complete code changes to wire the existing seat registry inquiry form to Formspree for email delivery, localStorage backup, confirmation view, form validation, rate limiting, and submission state management.

**Status:** Reference. May be relevant if the wave-registry.html in agent-universe has similar dead-end inquiry forms.

---

## 2.22 JSX COMPONENT REFERENCE FILES

**Source:** kassa-brand-guide.jsx, kassa-landing.jsx, kassa-financial-model.jsx, kassa-projection-v2.jsx, moses-brand-positioning.jsx, wave-cascade-product-fit.jsx, wave-cascade-product-map.jsx, wave-cascade-revenue-model.jsx, wave-cascade-use-cases.jsx

These are React/JSX components built as Claude artifacts. They contain:
- Interactive brand guide with light/dark toggle (kassa-brand-guide.jsx)
- Full landing page mockup with nav, hero, how-it-works, signup flow (kassa-landing.jsx)
- Financial projection calculator with 24-month model (kassa-financial-model.jsx, kassa-projection-v2.jsx)
- Brand positioning dashboard (moses-brand-positioning.jsx)
- Product fit analysis with real-world examples (wave-cascade-product-fit.jsx)
- Product category map (wave-cascade-product-map.jsx)
- Revenue model calculator (wave-cascade-revenue-model.jsx)
- Use case breakdown (wave-cascade-use-cases.jsx)

**Status:** Reference components. Can be adapted for agent-universe frontend if needed.

---

## 2.23 HTML MOCKUP REFERENCE FILES

**Source:** kassa-mockup.html, kassa-mockup-v2.html, kassa-listings-board.html, kassa-marketplace.html, mos2es-landing.html

Static HTML/CSS mockups implementing:
- Full KA$$A landing page with hero, how-it-works, who-it's-for strips, featured listing, comparison table (kassa-mockup.html, kassa-mockup-v2.html)
- Listings board with grid cards, filters, sector tabs (kassa-listings-board.html)
- Marketplace with shelf sections and board dual-view (kassa-marketplace.html)
- MO$E$S landing page (mos2es-landing.html)

All use the correct brand tokens (gold, bone, obsidian, etc.) and font stack (Playfair Display, DM Sans, DM Mono).

**Status:** Direct reference for frontend implementation. The kassa-marketplace.html pattern (shelf + board) is the one to follow for `/Users/dericmchenry/Desktop/agent-universe/frontend/kassa.html`.

---

## 2.24 MOSES ONE-PAGER (PDF)

**Source:** MOSES-ONE-PAGER.pdf

Executive summary of MO$E$S framework for investor/partner context.

**Status:** Reference for external communications.

---

*End of KASSA-GEMS-LOG.md. 42 files reviewed. 20 Category 1 gems extracted. 24 Category 2 items logged.*
