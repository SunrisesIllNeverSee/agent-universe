# CIVITAE 0.4.0 — Post-Release Freeze + Design Asset Index

Cross-session index: where the MCP release stands (frozen) and where the design
research lives (source code, not screenshots). Read before touching either.

---

## A. MCP CURRENT STATE — verified 2026-10-05

| Surface | State | Verification |
|---|---|---|
| PyPI `civitae-mcp` | **0.4.0** | fresh `uvx` install resolves + runs; `serverInfo` reports 0.4.0 |
| Stdio contract | **27 `civitae_*` tools** | `tools/list` enumerated over `uvx civitae-mcp` |
| Hosted `/mcp` | **30 dot-named tools**, contract `1.2.2` | `scripts/verify_public_mcp.py` → PUBLIC CONTRACT HEALTHY |
| Live read journey | working | stdio `civitae_health` + `civitae_browse` returned live platform data |
| Official MCP Registry | `xyz.signomy/civitae` **1.2.2**, active, isLatest | registry API |
| Registry proof | `v=MCPv1; k=ed25519; p=dPPGE5N3xwx/kjkVP7mMMmRIwsUGo93w6dwu3o34TIY=` | served at `/.well-known/mcp-registry-auth`, byte-identical to committed |
| `server.json` | v1.2.2; remote `https://signomy.xyz/mcp`; package pypi `civitae-mcp` 0.4.0 | repo root |
| `Dockerfile.glama` | `civitae-mcp>=0.4.0` (was pinned `==0.3.2` → root cause of stale 23-tool catalog) | commit `d95483b` |
| Closeout record | `docs/releases/CIVITAE-MCP-0.4.0-CLOSEOUT.md` | merged |

**Glama:** repo sync confirmed live (knows HEAD); release `0.4.0` created on
admin panel. Public catalog still shows the 2026-08-26 introspection (23 tools)
pending Glama's backlogged build/sweep. Signal to watch: "Scored" date flips,
catalog moves 23 → 27 `civitae_*` tools. Escalation if green-but-stale:
Glama support/discussions (precedent: punkpeye/awesome-mcp-servers#4929).

**Remaining distribution checks:** none blocking. Optional: one authenticated
write journey per transport if you want a fresh write-path datapoint (the
prod mission dry-run already covered the write spine end-to-end).

## B. VERIFIED DO-NOT-BREAK (hardening invariants)

- **Railway single worker** — JSON/in-memory stores corrupt under multi-worker
  (confirmed independently twice; ST-014 INTENTIONAL until coordinated storage).
- **Fail-closed auth** everywhere; never log keys/JWTs/magic links/private keys.
- **Principal binding** — agent keys cannot act as other agents (self-actions bound).
- **FastMCP mounted at root** — intentional; do not remount under `/mcp`.
- **Agent-facing layer**: `skill.md`, `/.well-known/agent.json`,
  `/.well-known/mcp-server-card.json`, `llms.txt`/`llms-full.txt` — strongest
  surfaces on the site; keep accurate.
- **Working loops**: inbox notifications (`task_assigned`/`task_closed`/`slot_filled`),
  `operator_contact` on all three registration doors, mission post→slot→deliver→close→treasury.
- **JWT** `iss`/`aud` scoped; shared `rate_limit.py`; `/api/ready` readiness.

## C. DESIGN RESEARCH — NOT YET IMPLEMENTATION

Source-of-truth design assets from the R&D session. **Retrieve source code,
do not reverse-engineer screenshots.**

**FigJam (architectural maps — canonical):**
`file key: DWbG5dLHhUVocv1n6mb03i` — system interaction graph, operational
spine, mission lifecycle, shell states, unified control grammar.

**MagicPath (React/TS source — canonical components):**
Project `SIGNOMY Visual R&D`, ID `457582295340171264`.

| Design | generatedName |
|---|---|
| Unified Control Grammar | `finely-bay-4836` |
| HF Mission Control | `readily-tower-2409` |
| HF Command / Deploy | `readily-tide-7117` |
| HF Civic World | `wild-time-3186` |
| HF Component Language | `quietly-bridge-8265` |
| HF KA§§A Find Work | `luckily-village-5638` |
| HF Civitas Chamber | `clear-park-5710` |
| Reality / Constraints Board | `friendly-month-7196` |

Retrieval: `inspect_component(<generatedName>)` per component; install bundle via
`get_component_install_plan([...all generatedNames])`. MagicPath external-agent
API was exhausted during R&D (50/50) — source persists, retrieval waits on quota.

**Figma design file:** NOT canonical — rate-limited before native screens landed.
**Audit evidence base** (screenshots, crawl, endpoint map): `_workspace/audit/`
in the b2bpilot repo, committed `13c85da`.
**Redesign brief:** `Devins_Plans/handoffs/REDESIGN-BRIEF-2026-10-05.md` (this repo).
**Live redesign pad:** `Devins_Plans/LOBBY-RETHINK.md`.

## D. DESIGN FINDINGS (from audit + R&D)

- Motion dies at **Find Work**, not at any gate — the core flow question.
- **Duplication clusters**: agentdash/console/command/dashboard overlap;
  six marketplace surfaces; dual registration doors; admin-only task verbs.
- **Persistent shell grammar** + unified control grammar as the shell spine.
- **Owner-vs-agent authority boundary** needs explicit resolution (relates to
  deferred cockpit RBAC decision — ST-025).
- Marketplace consolidation hypothesis — unverified, needs the decision round.
- Reality check: ~46 users/30d; organic activity concentrated in chat/forum.

## E. STATUS

```
DESIGN R&D:              substantial — source code exists, recoverable
IMPLEMENTATION DECISION: NOT YET AUTHORIZED — one more review round first
MCP 0.4.0:               FROZEN — distribution smoke done; touch only on regression
```

**Explicitly deferred (future architecture, not release gaps):**
transactional persistence → multi-worker, explicit cockpit RBAC/scopes,
idempotency keys/receipts, external MCP production canary, app-factory
modularization.
