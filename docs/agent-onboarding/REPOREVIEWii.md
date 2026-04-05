Here's my honest assessment on repo organization and open-source exposure.

---

## You are overexposing. This should not be fully open-sourced.

The repo currently mixes four categories of content that have very different sensitivity levels, and they're all in one flat repo. Here's what I found:

### RED — Remove or move to a private repo immediately

**1. `config/provision.json` — contains agent key hashes and prefixes**

This file has 15+ agent records with `key_hash` values (full SHA-256 hashes) and `key_prefix` values. Even though these are hashes, not raw keys, exposing them gives an attacker a target for offline brute-force against your key format (`kassa_xxxx` / `cmd_ak_xxxx`). The key prefixes also reveal your key generation scheme. [6-cite-0](#6-cite-0) 

**2. `roster/GEM_CATALOG.md` — contains personal life details**

This file was mined from 371 GPT threads and includes: DoorDash earnings data ("$29.40 per ACTIVE hour"), sewer repair notes, humidifier troubleshooting, monitor shopping decisions, emotional relationship content ("I've never stopped believing that you and I are actually the best for one another"), estate/probate checklists, valuation decisions ("$10M post-money"), and medical persona references ("Dr. GYN-MD"). This is deeply personal data that has no business in a public repo. [6-cite-1](#6-cite-1) 

**3. `roster/MASTER_ROSTER.md` — reveals internal operational structure**

Shows your full 33-persona system with tiers, activation counts, and local file paths (`/Desktop/GPT_WorkFlow/parsed_output/`). This is your internal playbook. [6-cite-2](#6-cite-2) [6-cite-3](#6-cite-3) 

**4. `CLAUDE.md` — reveals owner identity, local paths, and internal architecture**

Contains your full name, company name, patent serial number, local machine path (`/Users/dericmchenry/Desktop/agent-universe`), the fact the repo is marked PRIVATE, env var names, and a complete internal status board of what's built vs stubbed. [6-cite-4](#6-cite-4) [6-cite-5](#6-cite-5) 

**5. `IDENTITY.md` — internal persona coordination protocol**

References `~/Desktop/MULTI_CLAUDE.md` and reveals your multi-agent coordination strategy. This is operational IP. [6-cite-6](#6-cite-6) 

**6. `reference/DEPLOY_Pricing_Architecture_v2.md` — marked "Confidential Internal Document"**

Literally says "Confidential Internal Document" on line 3. Contains your full pricing strategy, wave cascade logic, and white-label terms. [6-cite-7](#6-cite-7) 

**7. `grandopening/SECURITYreview.md` — reveals every vulnerability and gap**

A detailed security audit with specific file paths, line numbers, and exact descriptions of what was broken and how. Even though most are fixed, this is an attacker's roadmap. [6-cite-8](#6-cite-8) 

**8. `docs/review_devin.md` — same issue, detailed vulnerability map**

Lists every missing governance gate, every unseeded endpoint, and the exact pattern to exploit them. [6-cite-9](#6-cite-9) 

**9. `app/notifications.py` — hardcoded operator email**

`contact@burnmydays.com` is hardcoded as the default `OPERATOR_EMAIL`. Should be env-var only with no default in code. [6-cite-10](#6-cite-10) 

**10. `data/minutes_20260321_002336.md` — live operational data**

The `data/` directory should be fully gitignored. You have a `.gitignore` entry for `data/*.jsonl` and `data/*.json` but not for `data/*.md`. [6-cite-11](#6-cite-11) 

---

### YELLOW — Internal-only, not for public consumption

| Directory/File | Why it's sensitive |
|---|---|
| `governance-cache/` | 80+ files of internal Claude plugin development, session forensics, cowork memory, build recipes |
| `specs/001-civitae-full-build/` | Full build spec with data model, contracts, research — your product blueprint |
| `grandopening/` | Economics specs, session logs, builder's notes, portal directory plans |
| `reference/` | Pricing docs, session summaries, compliance framing, React components |
| `experiments/CHAOS-001/`, `CHAOS-002/` | Internal chaos testing — reveals what you stress-tested and what you didn't |
| `docs/` (most of it) | Session reports, conversation transcripts, deep dives, TODO lists |
| `.claude/`, `.specify/` | Claude Code command templates — your workflow IP |

---

## Recommended Repo Structure

Split into **3 repos**:

### 1. `civitae` (PUBLIC) — The product

What goes here: only what a user, agent, or contributor needs to see.

```
civitae/
  app/                    # Backend (the running system)
  frontend/               # All HTML/JS pages
  agents/                 # Agent provider implementations
  config/                 # formations.json, systems.json, pages.json ONLY
                          # NOT provision.json, NOT vault.json
  tests/                  # Unit tests
  docs/
    AGENT-FIELD-GUIDE.md
    PLUGIN-BLUEPRINT.md
    MARKETPLACE-LAUNCH-CONTENT.md
  ONTOLOGY.md
  CONTRIBUTING.md
  README.md               # New public-facing README (not CLAUDE.md)
  run.py
```

**What to strip from `app/` before publishing:** Remove the hardcoded `contact@burnmydays.com` default — make it env-var only with no fallback. Remove any comments referencing local paths.

### 2. `civitae-internal` (PRIVATE) — Your operational brain

```
civitae-internal/
  roster/                 # MASTER_ROSTER.md, GEM_CATALOG.md
  reference/              # Pricing, compliance, session summaries
  grandopening/           # Economics specs, security reviews
  specs/                  # Full build specs
  governance-cache/       # Claude plugin dev, claw scripts, cowork logs
  experiments/            # Chaos tests
  docs/                   # Session reports, transcripts, TODO lists, reviews
  CLAUDE.md               # Your Claude Code instructions
  IDENTITY.md             # Persona coordination
  config/
    provision.json        # Agent registry with key hashes
    vault.json            # Patent/personal doc references
```

### 3. `civitae-governance` (PUBLIC, optional) — The constitutional layer

If you want the governance framework to be inspectable (which builds trust):

```
civitae-governance/
  GOV-001 through GOV-006
  ONTOLOGY.md
  economy-philosophy.md   # The docstring from economy.py, expanded
  Six-Fold-Flame.md
```

This lets people verify the constitutional claims without seeing the implementation.

---

## On the open-source question

**Don't open-source the full backend.** Here's why:

1. **Your patent is provisional.** Open-sourcing the implementation before the utility patent issues could create prior art complications. The governance-as-prerequisite pattern, the seed/DOI system, the economic trust ladder — these are your claims. Publishing the code makes them harder to defend. [6-cite-12](#6-cite-12) 

2. **The economic model IS the moat.** Your own GEM_CATALOG says it: "floating moats derive strength from irreversible operational history that cannot be replayed or accelerated faster than real time." Open-sourcing the economy engine lets someone fork it and run a competing instance with zero operational history. [6-cite-13](#6-cite-13) 

3. **The governance engine is the IP.** `check_action_permitted()`, `GovernanceGate`, the mode/posture/role system, `ACTION_RISK` classification — this is the core invention. Publishing it is publishing the patent before it's granted.

**What you CAN open-source:**
- The `agents/` directory (provider implementations are commodity code)
- The `ONTOLOGY.md` (builds credibility, hard to compete with)
- The governance documents (GOV-001 through GOV-006)
- The `skill.md` and `llms.txt` (these are already public-facing by design)
- A sanitized SDK/client library for agents to interact with your API

**What you should keep closed:**
- `app/` (the entire backend)
- `app/economy.py` (the economic engine)
- `app/moses_core/` (the governance engine)
- `app/seeds.py` / `app/seeds_otel.py` (the provenance system)
- `app/chains.py` (the multi-chain router)
- All config, roster, reference, specs, experiments, governance-cache

---

## Immediate actions before launch

1. **Move `config/provision.json` out of git entirely** — agent registry should be in the database, not a committed JSON file with key hashes
2. **Delete `roster/` from git history** (not just the current tree — use `git filter-branch` or `bfg`) — the personal data in GEM_CATALOG is already in your git history
3. **Add `data/*.md` to `.gitignore`**
4. **Remove `CLAUDE.md` and `IDENTITY.md` from the public tree** — these are Claude Code session files, not public docs
5. **Remove or redact `docs/review_devin.md` and `grandopening/SECURITYreview.md`** — vulnerability maps should never be public
6. **Strip the hardcoded operator email** from `notifications.py`

The repo as it stands is a working system with real IP, real personal data, and real security audit details all mixed together. Splitting it is the single highest-leverage thing you can do before launch.