# ST-017 Result — MCP Versioning and Deprecation Contract

**Status:** PARTIAL / DOCUMENTATION HARDENING  
**Area:** MCP compatibility

## Verified version surfaces

- hosted server metadata: `server.json` version **1.2.1**
- public MCP server card: **1.2.1**
- local `packages/civitae-mcp`: **0.4.0**
- public package pointer in `server.json`: **0.3.3**

The package mismatch is currently intentional because local 0.4.0 has not yet been published to PyPI. Advertising 0.4.0 publicly before publication would be false.

## Problem

There is no single written rule defining:

- which version represents the hosted MCP contract
- what constitutes a breaking tool/schema change
- how long deprecated tools/fields remain available
- when the package pointer may advance independently

## Decision

Treat `server.json` + the public server-card version as the authoritative **hosted contract version**, and require them to match in CI.

Package versions remain independent release artifacts and must only be advanced in public metadata after the package is actually published.

Do not add decorative `X-MCP-Version` headers unless a real client consumes them.

## Deprecation policy

For a public hosted tool/schema:

- additive optional fields/tools: minor contract increment
- incompatible rename/removal/required-field change: major contract increment
- breaking removal requires a documented migration/deprecation period
- documentation-only corrections: patch increment when they change the published contract description materially
