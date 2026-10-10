# Roadmap Engine v0.3

Portable, evidence-gated roadmap controller. Stdlib only; no external services.
`python3 -m roadmap_engine --project <dir> <command>`

## What it does

The `roadmap.json` is the authoritative *desired* plan. The engine runs
tasks whose dependencies are satisfied, executes their commands, runs their
independent checks, hashes their output artifacts, and writes durable
receipts. Nothing counts as done without a receipt; nothing attests an
owner gate but a real evidence file supplied by the operator.

## Commands

| Command | Purpose |
|---|---|
| `init <dir>` | Scaffold a runnable example workflow |
| `validate` | Schema + DAG check |
| `status` / `next` / `blockers` | Task state, eligible work, held tasks |
| `run [--max-tasks N] [--parallel N]` | Execute eligible tasks; `--parallel` runs disjoint `files` lanes concurrently |
| `resume` | Same as run — safe after interruption (running tasks are recovered as `interrupted`, not silently re-run) |
| `retry <task> --acknowledge-side-effects` | Explicitly re-admit a failed/interrupted task |
| `verify` | Re-validate every accepted receipt (contract hash + artifact hashes + checks) |
| `drift` | Report passed tasks whose contract or artifacts changed since PASS |
| `refresh` | Run the configured observer (read-only source projection; never changes task state) |
| `migrate [--rollback]` | Upgrade roadmap schema v1 → v2 preserving receipts; backup at `.roadmap/roadmap.v1.bak` |
| `attest <task> --evidence <file>` | Operator attestation for `manual`/`approval` gates |
| `render` | Regenerate ROADMAP_STATUS.md |

## Task schema (v2, backward-compatible with v1)

Required (unchanged): `id`, `phase`, `goal`, `needs[]`, `scope`
(`local`|`approval`), `executor`, `checks[]`, `outputs[]`.

New optional fields (metadata — do **not** invalidate receipts):

- `acceptance` — human-readable acceptance criteria.
- `files[]` — permitted write scope. Every declared output must live
  inside a listed path (a trailing `/` marks a directory prefix).
  Declaring `files` also makes the task eligible for parallel lanes:
  two tasks with overlapping `files` never run in the same wave.
- `lane` — concurrency grouping label.
- `risk` — `low` | `medium` | `high`.
- `authority` — `technical` (auto-verified) | `owner` (requires
  `scope=approval`, attestation-only) | `implementation` (a separately
  authorized scope — kept honest by the same approval gate).
- `retry` — `{max_attempts, backoff_seconds}` for bounded automatic retry.
- `executor.type: "adapter"` — resolved at run time from
  `adapters/<name>.json` (`{"argv": [...]}` with `{param}` substitution
  from `executor.params`). Missing adapter blocks the task instead of
  failing it — this is the documented boundary for future orchestrator
  integration (e.g. Devin agent launch), not a claim that it exists.

## Receipt model

Each PASS writes `.roadmap/receipts/<task>.json` binding: task id,
contract hash, executor exit, every check exit code, output artifact
hashes, start/end git SHAs. `verify` and `drift` re-check these.

v2 receipts hash the *execution contract* (id, goal, needs, scope,
executor, checks, outputs). Metadata edits (acceptance/risk/lane) do not
drift receipts; contract edits do. Receipts from v1 (whole-task hash)
remain accepted — `verify`/`drift` honor legacy digests and optional
`prior_contract_sha256` aliases recorded by migrations.

## Honesty contract

- Source observation (`refresh`) is read-only; it never graduates a task.
- `manual` executors can never auto-run.
- An approval-scope task cannot have an automatic executor (validate rejects).
- Interrupted tasks are never silently re-run; explicit retry is required.
- There is no git-event sync, background watcher, or agent orchestrator
  claim — `refresh` and `run` are explicit invocations. Adapters are the
  documented extension seam.
