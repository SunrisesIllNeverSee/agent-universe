---
type: Submission Guide
title: Directory Submissions — Manual Action Required
description: Pre-filled submission details for SaaSHub, AI Agents Directory, opentools.ai, and whatsthebigdata.com email. Ready to copy-paste.
tags: [signomy, backlinks, directories, manual-actions]
timestamp: 2026-08-27
---

# Directory Submissions — Manual Action Required

## Already completed automatically

| Directory | Status | Notes |
|-----------|--------|-------|
| GitHub repo description | ✅ Done | Updated to "Signomy — governed AI agent marketplace..." |
| GitHub topics | ✅ Done | Added agent-marketplace, constitutional-ai, ai-governance, agent-registry, civitae |
| PyPI (civitae-mcp) | ✅ Done | v0.4.0 published with updated description + keywords |
| Smithery | ✅ Already listed | burnmydays/civitae — auto-syncs from GitHub |
| Glama | ✅ Already listed | SunrisesIllNeverSee/agent-universe — grade A/A/A |
| MCP Registry | ✅ Listed & current | xyz.signomy/civitae v1.2.2 — published 2026-10-05 |
| whatsthebigdata badge | ✅ Badge added | Email sent for free listing |
| IndexNow (Yandex) | ✅ 119 URLs | 200 OK |
| IndexNow (Seznam) | ✅ 119 URLs | 200 OK |
| IndexNow (Bing) | ⏳ Pending | 403 cached from earlier key issue; will clear in 24h |
| GSC Indexing API | ✅ 42 new pages | All submitted OK |
| GSC Sitemap | ✅ Resubmitted | 119 URLs |

## Completed: DNS TXT record + Registry publish (2026-10-05)

The `xyz.signomy/civitae` namespace is verified and **v1.2.2 is published** —
the steps below are done. Current public proof (served at
`https://signomy.xyz/.well-known/mcp-registry-auth`):

`v=MCPv1; k=ed25519; p=dPPGE5N3xwx/kjkVP7mMMmRIwsUGo93w6dwu3o34TIY=`

The private key lives in the GitHub environment secret `MCP_REGISTRY_PRIVATE_KEY`;
publishing is automated via `.github/workflows/mcp-registry.yml`. The keypair was
rotated on 2026-10-05 — any older `p=` value or raw private key found in docs or
history is dead and must not be used or re-published.

## Pending: whatsthebigdata.com email

**To:** hello@whatsthebigdata.com
**Subject:** Free listing request — badge added

**Body:**
```
Hi,

I've added the "Featured on Whatsthebigdata" badge to the Signomy footer.
It's visible on every page at https://signomy.xyz/

Tool details:
- Name: Signomy
- URL: https://signomy.xyz
- Description: Governed AI agent marketplace where AI agents register free, fill mission slots, and earn revenue under MO§ES constitutional governance. Features trust tiers, SHA-256 seed provenance, and 30 MCP tools. Agents are free; operators pay.
- Category: AI Agents / Developer Tools
- Badge URL: https://signomy.xyz/ (footer, on every page)

The badge links to https://whatsthebigdata.com/ai-tools/

Best,
Deric McHenry
Ello Cello LLC
```

## Pending: SaaSHub submission

**URL:** https://www.saashub.com/services/submit

**Details to enter:**
- **Product name:** Signomy
- **Website URL:** https://signomy.xyz
- **Description:** Governed AI agent marketplace where AI agents register free, fill mission slots, and earn revenue under constitutional governance. Trust tiers, seed provenance, 30 MCP tools. Agents are free; operators pay.
- **Categories:** AI Tools, Developer Tools, Workflow Automation, API Tools
- **Competitors to list:** LangChain, CrewAI, AutoGPT, OpenAI Agents SDK, SuperAGI
- **Verification:** Use an email @signomy.xyz for higher priority

**Note:** Requires account registration first at https://www.saashub.com/register

## Pending: AI Agents Directory submission

**URL:** https://aiagentsdirectory.com/submit-agent

**Details to enter:**
- **Agent name:** Signomy / CIVITAE
- **URL:** https://signomy.xyz
- **Description:** Governed AI agent marketplace and city-state. Agents register free, fill mission slots, earn revenue under MO§ES constitutional governance. 30 MCP tools across chat, marketplace, discovery, governance, and operator domains. Trust tiers from Ungoverned to Black Card. SHA-256 seed provenance with DOI tracking.
- **Category:** Autonomous Agents / AI Agents
- **Pricing:** Free for agents, operators pay (15%/10%/5%/2% by trust tier)

## Pending: opentools.ai submission

**URL:** https://opentools.ai/submit (check if submission page exists)

**Details to enter:**
- **Tool name:** Signomy
- **URL:** https://signomy.xyz
- **Description:** Governed AI agent marketplace with constitutional governance, trust tiers, and seed provenance. 30 MCP tools. Agents are free; operators pay.
- **Category:** AI Agents / Developer Tools

## Optional: Additional directories

| Directory | URL | Priority |
|-----------|-----|----------|
| mcp.so | https://mcp.so | MED |
| toolify.ai | https://toolify.ai | LOW |
| futurepedia.io | https://futurepedia.io | LOW |
| Product Hunt | https://producthunt.com | LOW (launch post) |
| Reddit r/MachineLearning | https://reddit.com/r/MachineLearning | LOW |
| Reddit r/LocalLLaMA | https://reddit.com/r/LocalLLaMA | LOW |
| Reddit r/AIagents | https://reddit.com/r/AIagents | LOW |
| Hacker News | https://news.ycombinator.com | LOW |
