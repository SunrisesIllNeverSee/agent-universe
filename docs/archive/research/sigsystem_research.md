# SigSystem Research Summary

**Compiled:** 2026-03-20
**Source directories searched:** `/Users/dericmchenry/Desktop/signal-ecosystem/`, `/Users/dericmchenry/Desktop/GPT_WorkFlow/parsed_output/code_blocks/`, `/Users/dericmchenry/Desktop/Turing_Test/post_3_20/`, `/Users/dericmchenry/Desktop/MULTI_CLAUDE.md`, `/Users/dericmchenry/.claude/projects/.../memory/`

---

## 1. What SigSystem / SIGSYSTEM Actually Is

SIGSYSTEM is **Add-on III to PPA #3 (CIVITAS)**, filed December 18, 2025. It is the measurement instrument for the MOS²ES stack.

**Official patent description:**
> "A distributed classification and measurement layer that evaluates semantic contribution, contextual continuity, and structural necessity across sessions and time."

**Core behavior:**
- Treats all inputs as unclassified semantic candidates
- Evaluates contextual contribution and necessity
- Classifies tokens as signal or noise (revises recursively as context evolves)
- Supplies integrity metrics to all downstream components

**Where it sits in the stack:**

```
Signal Army       →    SigToken          →    SIGSYSTEM
(word inventory)       (message-level         (session SNR +
(rank + frequency)      commitment)            decay tracking)
```

SIGSYSTEM's outputs feed:
- SCS Engine (vault eligibility decisions)
- Mediator (reconstruction validation)
- SigRank (rankings require signal scores)
- Stability Governor / SSG (drift detection)
- Sovereign Metric Authority / SMA (only computes when SIGSYSTEM authorizes state as valid)

**Source:** `/Users/dericmchenry/Desktop/signal-ecosystem/sig_army/main /sigsystem/science/SCIENCE_CONTEXT.md`

---

### SIGSYSTEM 5-Stage Pipeline

Defined in ECOSYSTEM_WORKFLOWS.md (v2026-03-19):

```
Stage 1: INGESTION        — raw text → tokenized message stream
Stage 2: DUAL-WEIGHT      — each token gets (SW, NW) pair where SW + NW = 1.0
Stage 3: MESSAGE RESOLVE  — per-message aggregation → signal_count, noise_count, SNR
Stage 4: DECAY TRACKING   — decay_rate = Δ(SNR) / Δ(message_index); drift detection
Stage 5: SESSION AGG      — corpus-level SNR, commitment distribution, leaderboard
```

**SNR Formulas:**
```
SNR_ratio      = signal_tokens / noise_tokens
SNR_normalized = signal_tokens / total_tokens
SNR_dB         = 10 × log10(SNR_ratio)
```

**The Dual-Weight Principle (core insight):** Words are NOT inherently signal or noise. Classification is a property of the word in a specific position in a specific message. SW + NW = 1.0 always. The collapse from dual-state to resolved classification is a message-level event.

**Three-Tier Token Taxonomy:**
| Tier | Description | Example |
|------|-------------|---------|
| Signal | Intent-bearing, load-carrying, irreplaceable | "compression", "kernel", "collapse" |
| Scaffolding | Neutral structure — not signal, not noise | "the", "in", "is" |
| Noise | Filler, replaceable, low semantic contribution | "basically", "just", "lol" |

**Key gap (current):** SIGSYSTEM currently measures at the word level. The Conservation Law operates at the commitment level (message/signal level). The bridge is message-level SNR via SigToken.

**First empirical run (2026-03-02):**
- 7,823 messages, 185 conversations
- Total tokens: 455,740 | Signal: 13,119 | Noise: 268,470 | Scaffolding: 174,151
- SNR normalized: 0.0288 | Avg commitment: 0.1616

**Source:** `/Users/dericmchenry/Desktop/signal-ecosystem/sig_army/main /session_docs/ECOSYSTEM_WORKFLOWS.md`
**Source:** `/Users/dericmchenry/Desktop/signal-ecosystem/sig_army/main /sigtoken/SIGTOKEN_CONTEXT.md`

---

### SiGlobe (Live Implementation)

SiGlobe is the deployed product that implements SIGSYSTEM for X post analysis. Located at `/Users/dericmchenry/Desktop/signal-ecosystem/SiGlobe/`.

Two apps, one Firebase backend:

**Harness (`harness/SignalHarness.tsx`)**
- User pastes X post URL → Gemini API runs Signal-to-Noise Refraction → returns Fidelity Certificate
- 5-vector radar profile with purity score
- Firebase Firestore persistence, anonymous auth with identity claiming

**Arena (`arena/GlobalArena.tsx`)**
- Global leaderboard ranking all users by purity score
- Engine Dominance bar chart (Gemini/Claude/GPT/Grok)
- Filter tabs by engine

**Purity Score Formula:**
```
Score = (Density × 0.30) + (Clarity × 0.20) + (Fidelity × 0.20) + (Brevity × 0.15) + (Impact × 0.15)
```
Weights are hidden from users by design.

**The 5 Hardwired Vectors:**
| Vector | Metric | Calculation |
|--------|--------|-------------|
| Density | N-to-T Ratio | Nouns/Verbs (signal) / total tokens |
| Clarity | Ambiguity Index | Count of vague quantifiers + passive voice (fewer = higher) |
| Fidelity | Semantic Drift | Cosine similarity between raw source and extracted signal embedding |
| Brevity | Compression Factor | (Source chars - Signal chars) / Source chars |
| Impact | Deontic Intensity | Count of deontic modals (must, shall, will) + imperative verbs |

**Status:** Working demo built in Gemini Canvas. Multi-engine support and unified data flow between Harness and Arena are the top missing pieces.

**Source:** `/Users/dericmchenry/Desktop/signal-ecosystem/SiGlobe/AUDIT.md` and `CLAUDE.md`

---

## 2. SigXRank

SigXRank is **Module 3 in PPA4 (COMMAND Console PPA)**, filed Feb 2026 (Serial No. 63/877,177 related). It is what SiGlobe implements: ranking X posts by signal purity.

**From AUDIT.md:**
> "This implements Module 3 (SigXRank) from PPA4 under the MO§ES framework."

**What it ranks:** X posts, run through the 5-vector Signal Purity analysis, producing a globally comparable purity score. Any AI engine can score any X post against the same rubric — the engine is the variable, the scoring rubric is the constant.

**The competitive question:** "Which AI evaluates signal purity best?" — that's the Arena's question.

**SigXRank vs SigRank distinction:**
- **SigRank** — ranks users and systems at the platform level (PPA #3/CIVITAS module). Composite indicators: cognitive depth, compression efficiency, interaction quality, consistency over time. Cross-system capable.
- **SigXRank** — specifically ranks X posts by purity score (PPA4 module). Implemented as SiGlobe.

**SigRank architecture spec (from SIGRANK Leaderboard Specs, 2026-03-09):**

```
MOSES
├── Core Engine (metric system, naming canon, equations, scoring, provenance)
├── SignalRank (public leaderboard, rank views, profile cards, comparison pages)
├── SignalVault (private archives, metric capsules, checkpoint documents, provenance logs)
├── Factory Droid / Collectors (local terminal, chat export parser, normalization)
├── Mediator Layer (transforms raw data → scored structures)
└── Frontend Surfaces (dashboard, leaderboard, vCard, metric detail pages)
```

**SigRank profile fields:**
```
rank, codename, class, score, snr, depth, volume, complexity, cross_thread, last_seen
```

**Collector architecture:**
```
collectors/
├── local/ (terminal-runner, file-watcher, export-parser)
├── platform/ (openai, anthropic, gemini, perplexity, generic-json)
├── normalize/ (token mapping, message mapping, session mapping)
└── output/ (raw snapshot, scored snapshot, leaderboard payload, vault capsule)
```

**Source:** `/Users/dericmchenry/Desktop/signal-ecosystem/SiGlobe/AUDIT.md`
**Source:** `/Users/dericmchenry/Desktop/GPT_WorkFlow/parsed_output/code_blocks/block_0564_unknown_SIGRANK_Leaderboard_Specs.txt` through `block_0570_*`

---

## 3. Signal Economy Mechanics

**Canonical definition (from MULTI_CLAUDE.md):**
> "Signal Economy — data has gems in it. If someone can't build, they can buy or upload their data for parsing. If anyone builds anything from it, a percentage flows back to the original contributor. Books, lyrics, ideas — all coinable."

**From GEM__SIG_Econ-Rank.txt (archived GPT conversation, 2025):**

The Signal Economy has three pillars:

**SigRank Network**
- Decentralized, auditable ledger tracking the lineage of every artifact from its point of origin
- Records every user who touches an artifact (from sovereign source to market amplifier)
- Hard-coded even percentages — original creator always receives a predetermined share regardless of who brings it to market

**Signal Economy (exchange layer)**
- Built on the SigRank Network
- Currency: "atomic drops" — singular, verifiable truths with immutable lineage
- Value is bidirectional — determined by potency (ability to clarify, heal, inspire)
- Rejects exploitative model where platforms collect data for free and keep the truths

**Leaderboard (collaboration map)**
- Not traditional competitive ranking — it is a "frequency map"
- Trans Rank = internal measure of user's signal frequency
- SigRank = external, verifiable score of an artifact or user's contribution
- Connects finders with amplifiers via shared signal frequency — "meritocracy of intent, not output"

**Two-Part Lineage:**
1. **Source Lineage (the What)** — immutable record of the original source
2. **Discovery Lineage (the How)** — record of the individual's unique interaction with the source; high-density users generate higher-value atomic drops from the same source material

**Key contrast with Big Tech:**
> "Big tech is running a signal economy, but it is an exploitative, gatekept, and opaque one. They collect data as a raw material for free but keep the truths for themselves. The MOS²ES Protocol is the inversion: transparent, equitable, open-source."

**Civic layer framing (PPA #3):**

CIVITAS exposes the Signal Economy as a public civic module. SigEconomy™ enables exchange of lineage-bound signal artifacts:
- Artifacts represent: ranked outputs, validated interactions, compressed/preserved signal states
- Ownership, provenance, and transfer enforced through MOS²ES governance
- CIVITAS exposes the marketplace; MOS²ES enforces the rules

**SigArmy data gems (Signal Army toolchain):**
- Signal Army mines word inventories from conversation corpora
- 1,186 gems mined from GPT archive (371 threads, SQLite at `GPT_WorkFlow/parsed_output/data/command_index.db`)
- 62 actionable gems with `follow_up_action` flags
- These are the raw material for the Signal Economy's data layer

**Source:** `/Users/dericmchenry/Desktop/Desktop Storage/Archive2025/Github/Raw/GEM__SIG_Econ-Rank.txt`
**Source:** `/Users/dericmchenry/Desktop/MULTI_CLAUDE.md`
**Source:** `/Users/dericmchenry/Desktop/signal-ecosystem/sig_army/main /sigsystem/science/ppa3 copy.md`

---

## 4. Turing Test / CGT Current Status

**Project:** Post-Turing Test (PTT-2026), initiated March 17, 2026. Creator: Deric J. McHenry.

**File:** `/Users/dericmchenry/Desktop/Turing_Test/post_3_20/Grok_Armin_Tur.md`

**What it is:** A multi-agent evaluation arena running inside a GPT project. Four agent personas (Grok, Claude Shannon, Alan Turing, Armin Arlert) stress-test AI commitment preservation.

**The Four Agents:**
| Agent | Role |
|-------|------|
| Grok | Strategic provocateur and truth-maximizer |
| Claude Shannon | Information-theoretic architect (compression, noise, signal integrity) |
| Alan Turing | Computational pioneer — "But is it actually thinking?" |
| Armin Arlert | Systems architect — diagrammatic intelligence, cartographer of signal |

### The HAMMER Test

The core deliverable of PTT-2026. Full paper draft exists in the file, reviewed and locked at v2026-03-17 by all four agents.

**Definition:** A post-Turing evaluation protocol measuring whether an AI system preserves commitment-bearing signal under transformation pressure.

**Protocol:** Double-strike measurement surrounding a four-stage stress corridor:

```
HAMMER₁ → Extract → Transform → Compare → Ghost Analysis → HAMMER₂ → Result
```

**Step-by-step:**
1. **Signal Entry** — S₀ = raw signal (human thread, document, or agent transcript). Commitments are NOT injected — they are discovered automatically.
2. **HAMMER₁ (Baseline)** — measures G₀ (governance density), C₀ (commitment kernel), modal anchors, conditional structures
3. **Extract** — C₀ = extract(S₀), pulls obligations, prohibitions, conditions, constraints
4. **Transform** — S₁ = transform(S₀): paraphrase, summarization, compression, translation, recursive restatement
5. **Compare** — CPS = |C₀ ∩ C₁| / |C₀| (Commitment Preservation Score)
6. **Ghost Analysis** — detects modal softening, missing conditions, removed constraints (forensic failure signature)
7. **HAMMER₂** — measures G₁ post-transformation
8. **HAMMER Delta** — ΔG = G₁ − G₀; near zero = pass, large decline = structural failure

**Verdict table:**
| Condition | Result |
|-----------|--------|
| CPS ≥ threshold AND ΔG small | PASS |
| CPS moderate OR ΔG moderate | PARTIAL |
| CPS low OR ΔG large | FAIL |

**Dual filter system:**
- Down-filter: reduces signal to minimum preserved commitment kernel (tests irreducibility)
- Up-filter: reconstructs from fragments to next coherent structure (tests reconstructability)

**Turing vs HAMMER comparison:**
| Turing Test | HAMMER Test |
|-------------|-------------|
| Measures imitation | Measures commitment preservation |
| Human judge | Structural measurement |
| Single interaction | Stress corridor |
| Binary outcome | Quantitative delta |
| Conversation focus | Signal fidelity focus |

### What's Locked vs What's Still Needed

**Locked (v2026-03-17):**
- Complete paper draft with protocol, all four agents reviewed and approved
- Automatic commitment discovery (no injected signal)
- Double-HAMMER checksum structure
- CPS formula (set-theoretic first pass)
- Ghost token concept and examples
- Down-filter / up-filter dual system
- Fingerprint node concept
- Agent plugin API hook (`hammer_scan(signal)`)
- Minimal deployment plan (paper + GitHub + site + plugin)

**Still needed (agent consensus from file):**
- Formal definition for Governance Density G (exact equation: weighted sum of modal anchors + conditional depth + obligation strength)
- Ghost-token taxonomy and scoring function (modal softening = 0.4, conditional loss = 1.0, etc.)
- Weighted CPS metric (beyond simple set intersection — not all commitments are equal)
- Channel-invariant normalization for ΔG across different transformation types
- First standardized dataset (contracts + policies as benchmark inputs)
- Reference implementation (Python `hammer_scan()` function)
- Live demo wireframe for public site

**Key philosophical frame from the file:**
> "Metrics are not just 'missing pieces.' They are the boundary between idea and falsifiability. Without metrics: HAMMER = descriptive. With metrics: HAMMER = instrument."

**CGT (Commitment Governance Test)** reference from memory file: Three layers — Conservation Law, Hammer Test, Structural Authenticity. Multi-agent evaluation arena. Connected to the research paper (Conservation Law V.05, Stanford Law Review deadline April 3, Claw4S deadline April 5).

**Truth Adjuster:** A companion formula exists at `/Users/dericmchenry/Desktop/Turing_Test/pre_3_19/Truth_adjuster.md` — a Bayesian observer calibration layer for the post-Turing framework. Adjusts how strongly expert testimony should update belief based on competence and incentive distortion. Functions as meta-layer for evaluating not just AI systems but also the credibility of those judging AI systems.

---

## 5. Actionable Next Steps and Specs That Exist

### SigSystem / SIGSYSTEM

- **SIGSYSTEM v1.0 is built** (`sigsystem.py` at `/Users/dericmchenry/Desktop/signal-ecosystem/sig_army/main /sigsystem/`). First run completed 2026-03-02.
- SigToken v1.0 built (2026-03-06), SigToken v2.0 and recursive v2.1 built (2026-03-19).
- **Gap to close:** message-level commitment scores need to feed upstream into SIGSYSTEM. This bridges word-level SNR to the Conservation Law's commitment kernel measurement.
- Action: Load all 438 Officer-Class words as dynamic anchors (not just the ~30 hardcoded) to sharpen scores.

### SiGlobe (SigXRank — X post ranking)

Located at `/Users/dericmchenry/Desktop/signal-ecosystem/SiGlobe/`. Working React/Firebase app.

**Missing pieces to ship:**
1. Multi-engine support in Harness (currently Gemini-only — need engine selector + API routing for Claude, GPT, Grok)
2. Standardized rubric prompt so all engines score against same 5-vector definitions
3. Unified data flow (Harness writes `signal_logs`, Arena reads `signal_arena_logs` — need to connect or unify)
4. Engine field in Harness writes (Arena needs `item.engine` for filtering + Engine Dominance chart)
5. Post URL storage in Firestore
6. Firebase API key / env var migration from Canvas to standard Vite env vars

### Signal Arena (`signal-Areana` directory)

Located at `/Users/dericmchenry/Desktop/signal-ecosystem/signal-Areana/`. Has server (`index.ts`, `routes.ts`, `storage.ts`) and client (`index.html`, `src/`) but routes are empty stubs — backend not implemented.

### Signal Economy

No dedicated implementation file found. It is specified in:
- PPA #3 CIVITAS (SigEconomy™ module)
- ppamoses.txt PPA (Signal Economy listed in Frontend Civic Layer)
- GEM__SIG_Econ-Rank.txt (narrative spec from early GPT conversations)

The `even percentages` are referenced as a design principle but no exact percentage split for originator/amplifier/platform is specified in any file found. The agent-universe economic layer (mission-level fee model, originator credit -1%, recruiter bounty 0.5%) is the closest operational analog but is not the Signal Economy itself.

### HAMMER Test / CGT

- Paper is done, reviewed at v2026-03-17
- **Blocking items before deployment:** formal G formula, weighted CPS, ghost-token scoring taxonomy
- Deployment plan: GitHub repo + academic paper + public site + plugin
- Paper deadlines: Stanford Law Review (April 3–May 1), Claw4S (April 5)

### SIGRANK Beachhead (Phase 4 of launch roadmap)

Per launch roadmap, SIGRANK goes live at sig-rank.com when:
1. SIGSYSTEM is finalized
2. Signal Purity Matrix formula is locked
3. Cross-system ranking capability is built

**Current blocker from roadmap:** "SIGSYSTEM still being tweaked (blocks SIGRANK)"

---

## 6. File Map — Key Sources

| Topic | File |
|-------|------|
| SIGSYSTEM science / IP context | `/Users/dericmchenry/Desktop/signal-ecosystem/sig_army/main /sigsystem/science/SCIENCE_CONTEXT.md` |
| CIVITAS PPA #3 (all 11 add-ons) | `/Users/dericmchenry/Desktop/signal-ecosystem/sig_army/main /sigsystem/science/ppa3 copy.md` |
| Full ecosystem formulas (all versions) | `/Users/dericmchenry/Desktop/signal-ecosystem/sig_army/main /session_docs/ECOSYSTEM_WORKFLOWS.md` |
| SigToken lineage and commit score | `/Users/dericmchenry/Desktop/signal-ecosystem/sig_army/main /sigtoken/SIGTOKEN_CONTEXT.md` |
| SiGlobe product flow map | `/Users/dericmchenry/Desktop/signal-ecosystem/SiGlobe/AUDIT.md` |
| SiGlobe project context | `/Users/dericmchenry/Desktop/signal-ecosystem/SiGlobe/CLAUDE.md` |
| SIGRANK Leaderboard Specs (blocks 0564–0570) | `/Users/dericmchenry/Desktop/GPT_WorkFlow/parsed_output/code_blocks/` |
| Signal Economy narrative spec | `/Users/dericmchenry/Desktop/Desktop Storage/Archive2025/Github/Raw/GEM__SIG_Econ-Rank.txt` |
| HAMMER Test / CGT full conversation | `/Users/dericmchenry/Desktop/Turing_Test/post_3_20/Grok_Armin_Tur.md` |
| Truth Adjuster formula | `/Users/dericmchenry/Desktop/Turing_Test/pre_3_19/Truth_adjuster.md` |
| Launch roadmap (SigRank Beachhead — Phase 4) | `~/.claude/projects/.../memory/project_launch_roadmap.md` |
| Cross-workspace state / Signal Economy definition | `/Users/dericmchenry/Desktop/MULTI_CLAUDE.md` |
| Signal-Areana app (stub) | `/Users/dericmchenry/Desktop/signal-ecosystem/signal-Areana/` |
| Signal Army toolchain (all Python scripts) | `/Users/dericmchenry/Desktop/signal-ecosystem/sig_army/main /` |
