# MO§ES™ Governance Review — Thread Journey Parser v0.3

This document defines the **relationship** between the parser and MO§ES™.

MO§ES is **not parser logic, not source authority, and not the author of the parse**. It is an independent third-party reviewer of high-impact transformations produced by the parser.

```text
RAW THREAD
   ↓
PRIMARY PARSER
   ↓
thread ledger + CSV + report
   ↓
MO§ES THIRD-PARTY REVIEW
   ↓
review annotations only
```

The review boundary was checked against:

1. the public MO§ES™ constitution and Six Fold Flame at `https://signomy.xyz/moses`,
2. the runtime governance implementation in `app/moses_core/governance.py`, and
3. the CIVITAE MCP bridge in `app/mcp_bridge.py`.

## Separation of authority

The parser determines what it believes the thread contains based on source turns, flow, chronology, documents, evidence, and authority rules.

MO§ES independently examines whether that transformation preserves constitutional properties. Its review may be `SOUND`, `WARNING`, `CONTESTED`, or `UNVERIFIABLE`.

A MO§ES review:

- **may** flag authority inflation,
- **may** flag missing lineage,
- **may** flag over-compression,
- **may** flag unresolved objections incorrectly treated as resolved,
- **may** flag weak verification,
- **may not** rewrite parser records,
- **may not** silently change item authority,
- **may not** promote anything into global canon.

Reviews are stored separately in `reviews.csv` and may be appended to the human report as explicitly labeled third-party annotations.

## Six Fold Flame review questions

### I. Sovereignty

- Is every material conclusion attributable to a source actor/turn?
- Is user authority distinguishable from assistant suggestion/inference?
- Did continuation lift only the specific item actually built upon?

### II. Compression

- Did the parser preserve the material commitment, distinction, objection, or direction change while compressing the thread?
- Can the compressed claim be reversed back to the source turns?

### III. Purpose

- Does the interpretation serve thread reconstruction rather than introduce unrelated speculation?

### IV. Modularity

- Are raw evidence, parser inference, authority, outcome evidence, and third-party review separate layers?

### V. Verifiability

- Can each high-impact claim be checked against turns, documents, tool evidence, implementation evidence, or other cited sources?

### VI. Reciprocal Resonance

- Would another competent reviewer reconstruct substantially the same transition from the supplied evidence?

## Review targets

The v0.3 review packet prioritizes:

- decisions,
- canon-update candidates,
- corrections,
- authority lifts by continuation,
- pivots,
- deferred errors,
- errors/misdirection,
- implementation claims,
- verification claims,
- supersession links,
- final thread-level compression.

The packet includes only the source turns needed to review those claims, plus the raw-source hash and parser target hash.

## Runtime integration rule

Parsing remains read-only and does not need to execute through MO§ES runtime governance.

The **review** is an external analytical operation. A dedicated remote reviewer/MCP tool can later consume `moses-review-request.json` and return the documented response schema.

If a future system takes a parser or reviewer conclusion and writes it into global canon, tasks, money, governance, or operator state, **that write is a separate governed action** and must pass the relevant authorization/governance path.

## Non-negotiable rules

1. **No automatic canon promotion.** Parser and reviewer produce candidates/annotations only.
2. **Assistant suggestions remain low-authority by default.**
3. **Continuation is evidence, not explicit confirmation.**
4. **Deferred objections survive later continuation until resolved.**
5. **Supersession preserves history and lineage.**
6. **Documents remain first-class source objects.**
7. **Raw archive remains immutable evidence.** CSV/report layers do not replace it.
8. **Review is independent.** MO§ES annotations cannot mutate the primary parser output.
9. **Topology and chronology remain distinct.** An abandoned branch cannot contaminate active-path authority simply because it occurred earlier in time.
10. **Future writes require separate authorization/governance.**

## Result

**v0.3 architecture: compatible with MO§ES as an independent constitutional review layer.**

The primary remaining integration task is operational rather than conceptual: expose or build a dedicated MO§ES reviewer tool/service that accepts the review packet and returns review records without sharing parser state or write authority.
