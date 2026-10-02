# ST-014 Result — Multi-Worker State Integrity

**Status:** INTENTIONAL / DO NOT IMPLEMENT REVIEW RECOMMENDATION  
**Area:** deployment concurrency

## Review claim

Increase Railway uvicorn workers to 2–4 for scalability.

## Repository evidence

A prior 4-worker production pass exposed authoritative-state corruption/staleness across JSON-backed and per-worker in-memory ledgers. The deployment was deliberately returned to:

```
--workers 1
```

Some registry operations now use file locks, but registry locking alone does not make all treasury, runtime, trial, mission, and other process-local state multi-worker safe.

## Decision

**Preserve one worker.**

Horizontal/multi-worker scaling is blocked on a storage/coordination redesign plus an explicit cross-worker integrity suite. Performance pressure does not override correctness.
