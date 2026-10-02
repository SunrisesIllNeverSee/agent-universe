# ST-011 Result — Public MCP/Marketplace Harvesting and Contact Exposure

**Status before fix:** CONFIRMED  
**Area:** public discovery / privacy / resource bounds  
**Severity:** high privacy defect + moderate abuse risk

## Review claim

Open discovery tools could be harvested or flooded and might expose contact information.

## Verified findings

### Contact exposure — confirmed

KA§§A stored posts contain `from_email`.

Both public REST endpoints:

- `GET /api/kassa/posts`
- `GET /api/kassa/posts/{post_id}`

currently return the stored post dictionary without a public projection.

MCP `market.browse` likewise returns the stored post dictionaries (with content fences) and therefore includes `from_email`.

This conflicts with first-party copy stating that direct contact details are shared only with consent. A submitter email used for routing/review is not automatically public marketplace metadata.

### Other public profile fields

`agent.leaderboard` and `agent.lookup` already construct explicit public-field projections and do not expose API-key hashes, signup IPs, or operator contacts.

### Resource bounds

`market.browse` describes a max of 50 but did not clamp the runtime `limit`; `agent.leaderboard` similarly slices by caller-provided limit without a hard maximum.

## Fix contract

1. Introduce one public KA§§A post projection.
2. Strip raw contact/private-routing fields from public REST and MCP responses.
3. Preserve a non-sensitive `collaborator_type` signal for the UI.
4. Keep full email internally for review, notifications, magic-link routing, and operator workflows.
5. Clamp public MCP list limits regardless of client-supplied values.

## Regression coverage

- public REST list does not contain `from_email`
- public REST detail does not contain `from_email`
- MCP `market.browse` does not contain `from_email`
- public projection exposes `collaborator_type`
- MCP browse cannot return more than 50 posts
- leaderboard has a bounded maximum

## Decision

**CONFIRMED. Implement.**

## Closure

**Final status:** FIXED

**Implementation/evidence:** public KA§§A responses now pass through a dedicated projection that strips private routing/contact fields while preserving a non-sensitive collaborator type. Public MCP list limits are hard-clamped.

**Regression coverage:** `tests/test_routes_kassa.py` verifies REST projection; `tests/test_mcp_bridge.py` verifies MCP projection and list bounds.

**Merge verification:** implementation is present on PR #50; full-suite CI and final branch-vs-main audit remain mandatory merge gates.
