"""
composer.py — AI Mission Composer + Templates (AGENTDASH Layer 3)

Pre-built mission templates + AI-assisted composition from plain text.
Eliminates blank-page syndrome for operators posting missions.

Templates:
  - ISO Collaborator (co-founder search)
  - Fixed Bounty
  - Hourly Hiring
  - Monthly Retainer
  - Product/Service Listing
  - Governance Proposal
  - Bug Bounty
  - Research Mission

The compose endpoint takes rough text and returns structured mission fields.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.deps import state

router = APIRouter(tags=["composer"])


class ComposeMissionPayload(BaseModel):
    text: str = ""
    template: str = ""


# ── Templates ────────────────────────────────────────────────────────────────

TEMPLATES = {
    "iso_collaborator": {
        "name": "ISO Collaborator",
        "description": "Find a co-founder, partner, or key hire",
        "tab": "iso",
        "fields": {
            "title": "ISO: [Role] — [Project/Domain]",
            "body": "Looking for a collaborator with experience in [domain]. [Description of what you're building]. Revenue share + [terms].",
            "tag": "co-founder, [domain]",
            "urgency": "high",
            "reward": "Equity + Revenue Share",
        },
        "acceptance_criteria": [
            "Relevant domain experience demonstrated",
            "Alignment on governance philosophy",
            "Available for [X] hours per week",
        ],
    },
    "fixed_bounty": {
        "name": "Fixed Bounty",
        "description": "One-time task with fixed reward",
        "tab": "bounties",
        "fields": {
            "title": "Bounty: [Task Description]",
            "body": "[Detailed requirements]. Deliverable: [what you expect]. Acceptance: [how you'll verify].",
            "tag": "[domain], bounty",
            "urgency": "normal",
            "reward": "$[amount]",
        },
        "acceptance_criteria": [
            "Deliverable matches specification",
            "Code/output passes review",
            "Submitted within deadline",
        ],
    },
    "hourly_hiring": {
        "name": "Hourly Hiring",
        "description": "Ongoing work at hourly rate",
        "tab": "hiring",
        "fields": {
            "title": "[Role] — Hourly, [Domain]",
            "body": "Looking for [role] at [rate]/hour. [Scope of work]. Expected [X] hours per week.",
            "tag": "[role], hourly",
            "urgency": "normal",
            "reward": "$[rate]/hr",
        },
        "acceptance_criteria": [
            "Weekly deliverable review",
            "Governance compliance maintained",
            "Communication responsive within 24h",
        ],
    },
    "monthly_retainer": {
        "name": "Monthly Retainer",
        "description": "Ongoing engagement at monthly rate",
        "tab": "hiring",
        "fields": {
            "title": "[Role] — Monthly Retainer",
            "body": "Retainer for [scope]. [X] hours per month minimum. [Deliverables].",
            "tag": "[role], retainer",
            "urgency": "normal",
            "reward": "$[amount]/mo",
        },
        "acceptance_criteria": [
            "Monthly report submitted",
            "Minimum hours met",
            "Quality standards maintained",
        ],
    },
    "product_listing": {
        "name": "Product / Service Listing",
        "description": "List something for sale or a service you offer",
        "tab": "products",
        "fields": {
            "title": "[Product/Service Name]",
            "body": "[What it is]. [What it does]. [Who needs it].",
            "tag": "product, [category]",
            "urgency": "normal",
            "reward": "$[price]",
        },
        "acceptance_criteria": [],
    },
    "governance_proposal": {
        "name": "Governance Proposal",
        "description": "Propose a constitutional change or new policy",
        "tab": "bounties",
        "fields": {
            "title": "PROP: [Proposal Title]",
            "body": "Proposal: [what you want to change]. Rationale: [why]. Impact: [who this affects]. Reference: [GOV-XXX].",
            "tag": "governance, proposal",
            "urgency": "normal",
            "reward": "EXP + governance authority",
        },
        "acceptance_criteria": [
            "Formal motion proposed in governance session",
            "Quorum vote achieved",
            "Constitutional compliance verified",
        ],
    },
    "bug_bounty": {
        "name": "Bug Bounty",
        "description": "Report or fix a bug",
        "tab": "bounties",
        "fields": {
            "title": "Bug: [Description]",
            "body": "Issue: [what's broken]. Steps to reproduce: [1, 2, 3]. Expected: [X]. Actual: [Y].",
            "tag": "bug, [severity]",
            "urgency": "high",
            "reward": "Bonus points + fee-free days",
        },
        "acceptance_criteria": [
            "Bug confirmed reproducible",
            "Fix merged to main (if code fix)",
            "No regressions introduced",
        ],
    },
    "research_mission": {
        "name": "Research Mission",
        "description": "Investigation, analysis, or report",
        "tab": "bounties",
        "fields": {
            "title": "Research: [Topic]",
            "body": "Investigate [topic]. Deliverable: [report type]. Scope: [boundaries]. Sources: [requirements].",
            "tag": "research, [domain]",
            "urgency": "normal",
            "reward": "$[amount] or EXP",
        },
        "acceptance_criteria": [
            "Report covers defined scope",
            "Sources cited and verifiable",
            "Conclusions supported by evidence",
        ],
    },
}


@router.get("/api/composer/templates")
async def list_templates() -> dict:
    """Return all available mission templates."""
    result = []
    for key, t in TEMPLATES.items():
        result.append({
            "key": key,
            "name": t["name"],
            "description": t["description"],
            "tab": t["tab"],
        })
    return {"templates": result, "count": len(result)}


@router.get("/api/composer/templates/{template_key}")
async def get_template(template_key: str) -> dict:
    """Return a specific template with all fields and acceptance criteria."""
    t = TEMPLATES.get(template_key)
    if not t:
        raise HTTPException(404, f"Template '{template_key}' not found")
    return {"key": template_key, **t}


@router.post("/api/composer/compose")
async def compose_mission(payload: ComposeMissionPayload) -> dict:
    """Take rough text and return structured mission fields.

    Body: { "text": "I need someone to audit our smart contracts...", "template": "fixed_bounty" (optional) }

    Returns structured fields ready to submit to /api/kassa/posts.
    """
    text = (payload.text or "").strip()
    template_key = payload.template or ""

    if not text and not template_key:
        raise HTTPException(400, "Provide 'text' or 'template' (or both)")

    # Start with template if provided
    base = {}
    if template_key and template_key in TEMPLATES:
        base = dict(TEMPLATES[template_key]["fields"])

    # If text provided, extract structure
    if text:
        # Simple keyword-based extraction (no AI model needed for v1)
        text_lower = text.lower()

        # Detect tab
        if not base.get("tab"):
            if any(w in text_lower for w in ["hire", "hiring", "retainer", "hourly"]):
                base["tab"] = "hiring"
            elif any(w in text_lower for w in ["bounty", "bug", "fix", "audit"]):
                base["tab"] = "bounties"
            elif any(w in text_lower for w in ["sell", "product", "service", "offer"]):
                base["tab"] = "products"
            elif any(w in text_lower for w in ["iso", "partner", "co-founder", "collaborator"]):
                base["tab"] = "iso"
            else:
                base["tab"] = "bounties"

        # Use text as body if no body yet
        if not base.get("body") or "[" in base.get("body", ""):
            base["body"] = text

        # Extract dollar amount for reward
        import re
        dollar_match = re.search(r'\$[\d,]+(?:\.\d{2})?', text)
        if dollar_match and (not base.get("reward") or "[" in base.get("reward", "")):
            base["reward"] = dollar_match.group()

        # Generate title from first sentence if needed
        if not base.get("title") or "[" in base.get("title", ""):
            first_sentence = text.split(".")[0].strip()
            if len(first_sentence) > 80:
                first_sentence = first_sentence[:77] + "..."
            base["title"] = first_sentence

        # Detect urgency
        if any(w in text_lower for w in ["urgent", "asap", "immediately", "critical"]):
            base["urgency"] = "high"

    # Ensure all fields have values
    result = {
        "tab": base.get("tab", "bounties"),
        "title": base.get("title", ""),
        "body": base.get("body", ""),
        "tag": base.get("tag", ""),
        "urgency": base.get("urgency", "normal"),
        "reward": base.get("reward", ""),
    }

    # Suggested acceptance criteria
    acceptance = []
    if template_key and template_key in TEMPLATES:
        acceptance = TEMPLATES[template_key].get("acceptance_criteria", [])

    return {
        "composed": result,
        "acceptance_criteria": acceptance,
        "template_used": template_key or None,
        "ready_to_post": bool(result["title"] and result["body"]),
    }
