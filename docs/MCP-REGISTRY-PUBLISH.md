---
type: Reference
title: MCP Registry — CIVITAE Publish Runbook
description: MCP Registry — CIVITAE Publish Runbook — documentation in docs/.
tags: [documentation, docs]
timestamp: 2026-08-19
---

# MCP Registry — CIVITAE Publish Runbook

This is the **correct** submission flow for the official MCP registry. There is no GitHub PR — the registry uses a CLI tool (`mcp-publisher`) plus domain-based authentication.

The namespace `xyz.signomy/civitae` is gated by a DNS or HTTP challenge against `signomy.xyz`. We use the HTTP challenge because we already serve `/.well-known/` from Vercel.

---

## Files in this repo

- **`server.json`** (repo root) — what `mcp-publisher` reads. Conforms to the official `server.schema.json`. Edit this when tools, version, or transport change.
- **`frontend/.well-known/mcp-server-card.json`** — discovery card (already live).
- **`frontend/.well-known/mcp-registry-auth`** — committed **public proof only**. It contains the public Ed25519 key material served at `/.well-known/mcp-registry-auth`; the matching private key must never touch git.

---

## One-time setup (per machine that will publish)

### 1. Install mcp-publisher

```bash
brew install mcp-publisher
```

### 2. Generate Ed25519 keypair (locally — never commit)

```bash
openssl genpkey -algorithm Ed25519 -out key.pem
PUBLIC_KEY="$(openssl pkey -in key.pem -pubout -outform DER | tail -c 32 | base64)"
echo "v=MCPv1; k=ed25519; p=${PUBLIC_KEY}" > mcp-registry-auth
```

`*.pem`, `key.pem`, and `mcp-registry-auth` are all gitignored. Keep `key.pem` somewhere safe (password manager, 1Password vault, etc.) — losing it means re-doing the auth file and waiting for cache invalidation.

### 3. Deploy the auth file to the domain

The file must be served at `https://signomy.xyz/.well-known/mcp-registry-auth`.

The public proof is now intentionally committed at `frontend/.well-known/mcp-registry-auth` so deployments reproduce the same domain challenge. Verify:

```bash
curl https://signomy.xyz/.well-known/mcp-registry-auth
# Expected: v=MCPv1; k=ed25519; p=<base64-public-key>
```

> **Alternative (cleaner):** add the file directly to the Vercel project as a static asset via their CLI/dashboard so it never enters git history at all.

---

## Publish (every time you cut a release)

### 4. Authenticate

```bash
PRIVATE_KEY="$(openssl pkey -in key.pem -noout -text | grep -A3 "priv:" | tail -n +2 | tr -d ' :\n')"
mcp-publisher login http --domain signomy.xyz --private-key "${PRIVATE_KEY}"
```

### 5. Publish

```bash
mcp-publisher publish
```

The CLI reads `server.json` from the current directory and submits it to the registry.

---

## Updating the listing

1. Bump `version` in `server.json` (semver).
2. Update `description` / `remotes` / capabilities as needed.
3. Re-run step 5. Auth from step 4 is cached for the session.

---

## Troubleshooting

- **`domain verification failed`** — check `https://signomy.xyz/.well-known/mcp-registry-auth` returns 200 with the exact line `v=MCPv1; k=ed25519; p=<key>`. Watch for trailing newlines or BOM.
- **`schema validation failed`** — validate `server.json` against the schema URL in its `$schema` field.
- **`namespace already claimed`** — `xyz.signomy/civitae` should be available; if not, the auth file may be pointing at a different keypair than the one you're authenticating with.


---

## GitHub Actions publish path

The repository includes `.github/workflows/mcp-registry.yml`.

- Pull requests changing `server.json` or the workflow run the official `mcp-publisher validate` command.
- The workflow pins `mcp-publisher v1.8.1` and verifies the upstream SHA-256 digest before execution.
- Publishing is manual only: run **MCP Registry** with `publish=true`.
- The publish job uses the protected `mcp-registry` environment and expects one secret:
  `MCP_REGISTRY_PRIVATE_KEY`.
- That secret must contain the same private-key hex accepted by:
  `mcp-publisher login http --domain signomy.xyz --private-key ...`.
- The private key must never be committed, echoed, attached to artifacts, or placed in repository files.

This workflow preserves the existing `xyz.signomy/civitae` domain namespace. GitHub/OIDC authentication is intentionally not substituted because GitHub-authenticated Registry namespaces use the `io.github.*` naming scheme.
