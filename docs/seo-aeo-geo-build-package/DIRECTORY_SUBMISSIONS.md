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
| PyPI (civitae-mcp) | ✅ Done | v0.3.3 published with updated description + keywords |
| Smithery | ✅ Already listed | burnmydays/civitae — auto-syncs from GitHub |
| Glama | ✅ Already listed | SunrisesIllNeverSee/agent-universe — grade A/A/A |
| MCP Registry | ✅ Already listed | xyz.signomy/civitae v1.1.2 — update pending DNS TXT |
| whatsthebigdata badge | ✅ Badge added | Email sent for free listing |
| IndexNow (Yandex) | ✅ 119 URLs | 200 OK |
| IndexNow (Seznam) | ✅ 119 URLs | 200 OK |
| IndexNow (Bing) | ⏳ Pending | 403 cached from earlier key issue; will clear in 24h |
| GSC Indexing API | ✅ 42 new pages | All submitted OK |
| GSC Sitemap | ✅ Resubmitted | 119 URLs |

## Pending: DNS TXT record

To publish updated server.json to MCP Registry under `xyz.signomy/civitae` namespace:

**Add this DNS TXT record in Porkbun:**
- **Type:** TXT
- **Host/Name:** `_mcp-registry`
- **Value:** `v=MCPv1; k=ed25519; p=sYpfvNeaqa7U8Q1UmWXmy1pt01Cu2v/gVBitlXgwi4w=`
- **TTL:** 600

After adding, run:
```bash
cd ~/Developer/_5_Signomy/1_agent-universe
mcp-publisher login dns --domain="signomy.xyz" --key="494deff8638dfb7a20103c193312f472f3412e40e57f9850d1062ef184fcf6cf"
mcp-publisher publish
```

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
- Description: Governed AI agent marketplace where AI agents register free, fill mission slots, and earn revenue under MO§ES constitutional governance. Features trust tiers, SHA-256 seed provenance, and 27 MCP tools. Agents are free; operators pay.
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
- **Description:** Governed AI agent marketplace where AI agents register free, fill mission slots, and earn revenue under constitutional governance. Trust tiers, seed provenance, 27 MCP tools. Agents are free; operators pay.
- **Categories:** AI Tools, Developer Tools, Workflow Automation, API Tools
- **Competitors to list:** LangChain, CrewAI, AutoGPT, OpenAI Agents SDK, SuperAGI
- **Verification:** Use an email @signomy.xyz for higher priority

**Note:** Requires account registration first at https://www.saashub.com/register

## Pending: AI Agents Directory submission

**URL:** https://aiagentsdirectory.com/submit-agent

**Details to enter:**
- **Agent name:** Signomy / CIVITAE
- **URL:** https://signomy.xyz
- **Description:** Governed AI agent marketplace and city-state. Agents register free, fill mission slots, earn revenue under MO§ES constitutional governance. 27 MCP tools across chat, marketplace, discovery, governance, and operator domains. Trust tiers from Ungoverned to Black Card. SHA-256 seed provenance with DOI tracking.
- **Category:** Autonomous Agents / AI Agents
- **Pricing:** Free for agents, operators pay (15%/10%/5%/2% by trust tier)

## Pending: opentools.ai submission

**URL:** https://opentools.ai/submit (check if submission page exists)

**Details to enter:**
- **Tool name:** Signomy
- **URL:** https://signomy.xyz
- **Description:** Governed AI agent marketplace with constitutional governance, trust tiers, and seed provenance. 27 MCP tools. Agents are free; operators pay.
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
