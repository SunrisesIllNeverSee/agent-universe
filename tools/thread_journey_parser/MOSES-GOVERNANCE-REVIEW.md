# MO§ES™ Governance Review — Thread Journey Parser

This review checks the parser against three governance surfaces:

1. the public MO§ES™ constitution and Six Fold Flame at `https://signomy.xyz/moses`,
2. the runtime governance implementation in `app/moses_core/governance.py`, and
3. the CIVITAE MCP bridge in `app/mcp_bridge.py`.

The parser is a read/analyze/report tool. It must not manufacture authority, silently rewrite canon, or convert assistant inference into owner-approved truth.

## Six Fold Flame

### I. Sovereignty — PASS

- Every normalized turn retains speaker identity.
- Every extracted item retains its introducing turn, source turns, and authority class.
- User statements/corrections/decisions outrank assistant proposals.
- Behavioral continuation can lift a specific assistant-originated item, but only as `IMPLICITLY_ACCEPTED` thread-local evidence.

Boundary: the parser does not authenticate real-world identity; it preserves the identity supplied by the source transcript.

### II. Compression — PASS WITH CONSTRAINT

- The parser compresses turns into summaries and structured records.
- Raw turn text remains in `thread-ledger.json` so compression is reversible/auditable.
- Reports cite the exact normalized turns behind compressed claims.

Constraint: downstream tools must not discard the raw ledger and retain only the report if evidentiary fidelity matters.

### III. Purpose — PASS

The tool has a narrow constitutional purpose: reconstruct one thread's journey, including decisions, ideas, actions, errors, pivots, documents, authority changes, and unresolved work.

It intentionally excludes global memory and automatic cross-thread canon promotion.

### IV. Modularity — PASS

- The parser is isolated under `tools/thread_journey_parser/`.
- It does not modify Signomy/CIVITAE production runtime.
- It now carries its own `pyproject.toml`, so the directory can be copied or extracted and installed independently.

### V. Verifiability — PASS

- Every substantive report claim uses `[T###]` turn citations.
- Raw turn text is retained.
- Documents retain introduction/reference turns and optional content hashes.
- Authority transitions are stored as explicit evolution events rather than inferred only at report time.
- Parser commentary remains labeled inference, not canon.

### VI. Reciprocal Resonance — CONDITIONAL PASS

The same ledger/report is designed to be useful to both human operators and agents: humans can audit how a thread evolved; agents can consume the structured JSON state.

This remains conditional because usefulness should be validated against real long threads rather than assumed from schema design.

## Runtime governance alignment

The runtime's High Integrity mode requires accuracy, source citation, explicit uncertainty, and separation of fact/inference/speculation. The parser implements the same separation through authority classes, turn provenance, confidence values, and explicit `Parser inference — not canon` labeling.

The runtime also preserves original intent alongside canonical translation (`mode_raw_input`) so translation distortion is auditable. The parser mirrors this principle by freezing the thread foundation from the opening exchange and retaining raw turns even after summarization.

## MCP alignment

The CIVITAE MCP bridge exposes governance state, uses registered agent identities, and records actions with audit/provenance metadata. The parser does not need to execute through MCP because parsing itself is read-only, but any future write-back operation (for example, publishing a canon update) MUST become a governed action rather than a local parser side effect.

## Non-negotiable enforcement rules

1. **No automatic canon promotion.** The parser may produce canon candidates and supersession candidates; a separate authorized process must approve any global canon write.
2. **Assistant suggestions remain low-authority by default.** They can gain scoped weight only through later user behavior or explicit confirmation.
3. **Continuation is evidence, not proof.** `IMPLICITLY_ACCEPTED` must remain distinct from `USER_EXPLICIT`.
4. **Deferred objections survive continuation.** A later turn cannot erase an explicitly deferred error merely because the conversation kept moving.
5. **Supersession stays auditable.** Older records are retained and linked; they are not deleted or rewritten.
6. **Documents remain source objects.** Their role and turn provenance must survive summary generation.
7. **Future write actions require governance.** If the parser is later allowed to alter Signomy canon, tasks, or operator state, that write path must pass MO§ES™ GovernanceState and emit provenance.

## Result

**Current parser design: governance-compatible for read-only thread reconstruction.**

The strongest alignment is with lineage and verifiability. The principal risk is authority inflation: treating inferred continuation or semantic supersession as equivalent to an explicit owner decision. V0.2 therefore keeps those distinctions visible and disables automatic canon promotion.
