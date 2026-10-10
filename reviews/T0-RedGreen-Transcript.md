# T0 RED/GREEN Transcript — 2026-10-09 · HEAD f2c01a6

Invariant: unauthenticated/forged reads of /api/inbox and
/api/kassa/messages fail closed (4xx) and return no PII.

## GREEN — baseline (real tree)

```
$ .venv/bin/python reviews/t0_redgreen_probe.py .
GREEN — inbox/contact read guards fail closed (3/3 checks)
EXIT=0
```

## RED — deliberate guard-disable in disposable worktree

```
$ git worktree add /tmp/t0-wt HEAD          # f2c01a6
$ sed -i ... 'app/auth.py'   # admin_key_matches → return True
$ .venv/bin/python reviews/t0_redgreen_probe.py /tmp/t0-wt
RED — invariant violated:
  - anonymous GET /api/inbox -> 200 (expected 4xx fail-closed)
  - forged-admin GET /api/inbox -> 200 (expected 4xx fail-closed)
  - anonymous GET /api/kassa/messages -> 200 (expected 4xx fail-closed)
EXIT=1
```

## Restore + re-verify

```
$ git worktree remove --force /tmp/t0-wt
$ .venv/bin/python reviews/t0_redgreen_probe.py .
GREEN — inbox/contact read guards fail closed (3/3 checks)
EXIT=0
$ grep -n "DELIBERATE" app/auth.py   # (no output — main untouched)
$ git diff --stat app/               # empty
```

Runtime unchanged by the exercise; the mutation existed only inside
/tmp/t0-wt and was never committed.
