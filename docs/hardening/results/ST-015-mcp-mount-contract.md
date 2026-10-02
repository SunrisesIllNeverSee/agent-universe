# ST-015 Result — MCP Mount and Public Path Contract

**Status:** INTENTIONAL / REGRESSION-PROTECTED  
**Area:** MCP transport routing

## Review claim

Change `app.mount("", _mcp_app)` to `app.mount("/mcp", _mcp_app)`.

## Verified architecture

The FastMCP Starlette sub-app already owns its internal `/mcp` route. Parent root mounting maps that route 1:1 to the external path.

This repository previously fixed redirect/path nesting failures caused by mounting the sub-app itself at `/mcp`.

On 2026-10-01 the Vercel proxy was separately repaired so every external `/mcp` request proxies to Railway rather than being diverted to human documentation based on `Accept`.

Regression coverage now requires the public Vercel `/mcp` rule to point directly to Railway.

## Decision

**Do not apply the review recommendation.** Preserve:

```python
app.mount("", _mcp_app)
```
