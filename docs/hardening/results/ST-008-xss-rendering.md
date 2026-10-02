# ST-008 Result — Stored/Rendered HTML and XSS

**Status:** PARTIAL / NO FIRST-PARTY XSS REPRODUCED  
**Area:** user-generated content / frontend rendering

## Review claim

The external review claimed forum/KA§§A content was not HTML-escaped and that a payload such as `<img src=x onerror=...>` could render as executable markup.

## Verified current behavior

### REST storage paths

REST KA§§A and forum writes already use `app.sanitize.sanitize_text()` / `sanitize_name()`, which call `html.escape(..., quote=True)` and strip null bytes before persistence.

### MCP storage paths

MCP writes use a separate local `_sanitize()` helper. It performs prompt-keyword filtering and truncation but does not HTML-escape before storage. This is an invariant mismatch.

### First-party render paths

The mismatch does **not** currently become an executable first-party XSS on the reviewed surfaces:

- `frontend/kassa.html` applies `esc()` to user-controlled post fields before `innerHTML`
- `frontend/kassa-post.html` escapes dynamic header fields and renders the body with `textContent`
- `frontend/kassa-thread.html` renders message bodies with `textContent`
- `frontend/forums.html` renders thread titles, bodies, and replies with `textContent`

Thus raw HTML stored through MCP is rendered as text on the primary first-party surfaces reviewed.

## Remaining risk

- The repository's stated "escape at storage boundary" invariant is not universally true because MCP writes bypass it.
- A future consumer that assumes all stored content is pre-escaped could introduce XSS.
- Blindly adding storage escaping to MCP now would alter visible stored semantics and can double-escape content because current frontends already escape at render.

## Decision

**PARTIAL.** No current first-party XSS exploit was reproduced, so do not add a dependency such as `bleach` or mutate stored-content semantics solely from the review claim.

Hardening action:

1. Preserve render-boundary escaping/textContent as the primary safety invariant.
2. Add regression/static tests for the critical first-party render paths.
3. Clarify sanitizer documentation so future code does not assume every storage ingress is escaped.
4. Revisit storage canonicalization only as a migration with data-compatibility tests.
