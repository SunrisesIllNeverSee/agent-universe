# Migration Map — agent-universe

**Installed:** 2026-08-19
**Mode:** migrate
**Profile:** platform

## Existing structure preserved

All existing root directories declared in `allowed_root_dirs_extra`:
- `.agents/`, `.circleci/`, `.playwright-mcp/` — tooling/config
- `adapters/`, `agents/`, `app/`, `config/`, `data/`, `frontend/`, `packages/`, `scripts/`, `tests/` — application code
- `Devins_Plans/` — legacy coordination (preserved as historical record)
- `docs/` — documentation (added to document_roots)

All existing root files declared in `allowed_root_files_extra`:
- `.env.example`, `.vercelignore`, `CLAUDE.md`, `Dockerfile.glama`, `ONTOLOGY.md`,
  `Procfile`, `glama.json`, `LICENSE-MCP`, `railway.json`, `run.py`, `run_prod.py`, `server.json`

## Pre-existing coordination (preserved, NOT active bus)

Extensive legacy coordination infrastructure in `Devins_Plans/`:
- `SCRATCHPAD.md`, `STATE.md`, `handoffs/`, `DECISIONS.md`, `CROSSWIRE.md`, `state/ROSTER.md`
- `.agents/claims.yaml` — legacy lane claims
- `scripts/set-role.sh`, `scripts/check.py`, `scripts/status.sh` — legacy coordination scripts

All preserved as historical record. Canonical bus: `.coord/micro/SCRATCHPAD.md`.

## Canon context

- Authority role: `implementation`
- Canon contexts: `signomy`, `civitae`
- Authority owner: `search_authority`

## Migration steps (before enforce)

1. [ ] Assess whether legacy `Devins_Plans/` coordination should be archived or kept as reference
2. [ ] Verify the 1 remaining warning (docs/DOC-001-CIVITAE-SUBMISSION-COPY.md — legitimate document name, false positive from suffix checker)
3. [ ] Verify GitHub ruleset application (solo-fast)
4. [ ] Switch REPO.yaml mode from `migrate` → `enforce`

## Enforce readiness

Nearly ready — 0 errors, 1 warning (legitimate document name false positive).
Requires legacy coordination assessment and ruleset verification before enforce.
