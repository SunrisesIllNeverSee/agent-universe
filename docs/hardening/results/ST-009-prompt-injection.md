# ST-009 Result — Prompt-Injection Detection and Fencing

**Status:** PARTIAL / DEFENSE-IN-DEPTH  
**Area:** agent-facing untrusted content

## Review claim

The external review characterized prompt filtering as a naive substring list and implied content fencing was a complete safety boundary.

## Verified current behavior

There are two different implementations:

### REST

`app/sanitize.py` has a compiled regex detector covering multiple instruction-override forms and a separate `sanitize_for_agent()` fence helper.

### MCP

`app/mcp_bridge.py` has a smaller local substring-based `_sanitize()` filter:
- `ignore previous`
- `disregard`
- `system:`
- `assistant:`
- `<|im_`

MCP read tools fence selected user-content fields before returning them to agents.

## Security interpretation

Neither pattern matching nor fencing can make arbitrary untrusted text "safe instructions." They are defense-in-depth signals and context separation.

The meaningful invariant is:

> user-controlled marketplace/forum/thread content remains data, never trusted system/developer instruction authority.

## Stress corpus

The detector must be tested against:

- casing and flexible whitespace
- zero-width characters / soft hyphens
- Unicode normalization variants
- role markers
- common override phrases
- benign phrases that should not false-positive
- nested user-content fences

Encoded/obfuscated arbitrary payloads (base64/ROT13/etc.) cannot be reliably classified by string filtering and must not be represented as solved.

## Decision

**PARTIAL.** Consolidate MCP detection onto the shared detector rather than maintaining two divergent rule sets. Add Unicode/zero-width normalization before detection, but keep fencing as a separate delivery mechanism and explicitly document that it is not an instruction-security guarantee.
