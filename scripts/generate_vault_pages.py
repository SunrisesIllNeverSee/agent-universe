#!/usr/bin/env python3
"""Generate static vault HTML pages from governance markdown sources.

Each page gets:
- Unique <title> with document name
- Self-referencing canonical
- Meta description with doc metadata
- <h1> with document title
- SSR plain-text content block (visible to crawlers)
- JSON-LD ScholarlyArticle schema
- The JS renderer remains as progressive enhancement
"""

import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOV_DIR = ROOT / "docs" / "governance"
TEMPLATE = ROOT / "frontend" / "vault" / "gov-001.html"  # use any as base
OUTPUT_DIR = ROOT / "frontend" / "vault"

DOCS = {
    "gov-001": "GOV-001-standing-rules.md",
    "gov-002": "GOV-002-civitas-bylaws.md",
    "gov-003": "GOV-003-agent-conduct-code.md",
    "gov-004": "GOV-004-dispute-resolution.md",
    "gov-005": "GOV-005-voting-mechanics.md",
    "gov-006": "GOV-006-mission-charter.md",
}


def parse_meta(text: str) -> dict:
    meta = {
        "doc_id": "",
        "status": "DRAFT",
        "version": "1.0",
        "date": "",
        "title": "",
        "author": "",
        "flame": "6/6",
    }
    lines = text.split("\n")
    for line in lines:
        if line.startswith("# "):
            meta["title"] = line[2:].strip()
        elif line.startswith("**Document ID:**"):
            meta["doc_id"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Version:**"):
            meta["version"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Status:**"):
            meta["status"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Date:**"):
            meta["date"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Author:**"):
            meta["author"] = line.split(":**", 1)[1].strip()
        elif line.startswith("**Six Fold Flame"):
            raw = line.split(":**", 1)[1].strip()
            meta["flame"] = "6/6" if "six" in raw.lower() or "all" in raw.lower() else raw
    return meta


def md_to_plain_text(md: str, max_lines: int = 200) -> str:
    """Convert markdown to plain text for SSR/crawler content."""
    plain = []
    for line in md.split("\n"):
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
        clean = re.sub(r"^\|.*\|$", "", clean)
        clean = re.sub(r"^#+\s*", "", clean)
        clean = re.sub(r"^-\s+", "", clean)
        if clean.strip():
            plain.append(clean)
    return "\n".join(plain[:max_lines])


def build_page(doc_id: str, md_filename: str, template_html: str) -> str:
    md_path = GOV_DIR / md_filename
    text = md_path.read_text(encoding="utf-8")
    meta = parse_meta(text)

    # Find body (after metadata block)
    lines = text.split("\n")
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("## ") and body_start == 0:
            body_start = i
            break
    body_md = "\n".join(lines[body_start:]) if body_start else text
    plain_text = md_to_plain_text(body_md)

    # Build SEO elements
    full_title = meta["title"] or meta["doc_id"]
    colon_idx = full_title.find(":")
    short_title = full_title[colon_idx + 1:].strip() if 0 < colon_idx < 10 else full_title
    seo_title = f"{short_title} — The Vault | SIGNOMY"
    canonical_url = f"https://signomy.xyz/vault/{doc_id}"
    meta_desc = f"{meta['doc_id']}: {short_title}. {meta['status'].lower()} document v{meta['version']} ({meta['date']}). Part of the six-document constitutional archive governing AI agent operations under MO§ES."
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152] + "..."

    # JSON-LD
    jsonld = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": short_title,
        "identifier": {"@type": "PropertyValue", "propertyID": "DOI", "value": meta["doc_id"]},
        "author": {
            "@type": "Person",
            "name": "Deric J. McHenry",
            "sameAs": "https://orcid.org/0009-0002-9904-5390",
        },
        "datePublished": meta["date"],
        "version": meta["version"],
        "publisher": {
            "@type": "Organization",
            "name": "SIGNOMY",
            "url": "https://signomy.xyz",
        },
        "isPartOf": {
            "@type": "PublicationIssue",
            "name": "CIVITAE Constitutional Archive",
        },
        "url": canonical_url,
    }

    # SSR content block
    ssr_html = f"""<div class="doc-header">
  <div class="doc-meta-row">
    <span class="doc-id-badge">{meta['doc_id']}</span>
    <span class="status-badge status-{meta['status'].lower()}">{meta['status']}</span>
    <span class="flame-badge"><span class="dot"></span> {meta['flame']} Flame</span>
    <span class="version-badge">v{meta['version']} · {meta['date']}</span>
  </div>
  <h1 class="doc-title">{short_title}</h1>
  <div class="doc-author">{meta['author']}</div>
</div>
<div class="doc-body">
  <div class="doc-section"><div class="doc-para" style="white-space: pre-wrap;">{plain_text}</div></div>
</div>"""

    # Apply replacements
    html = template_html
    html = html.replace(
        '<link rel="canonical" href="https://signomy.xyz/vault" />',
        f'<link rel="canonical" href="{canonical_url}" />',
    )
    # If no canonical in template, add one after viewport
    if canonical_url not in html:
        html = html.replace(
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<link rel="canonical" href="{canonical_url}" />',
        )

    html = html.replace(
        "<title>Document — The Vault</title>",
        f"<title>{seo_title}</title>",
    )

    # Add meta description after canonical
    html = html.replace(
        f'<link rel="canonical" href="{canonical_url}" />',
        f'<link rel="canonical" href="{canonical_url}" />\n<meta name="description" content="{meta_desc}" />',
    )

    # Add JSON-LD before </head>
    jsonld_block = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>\n</head>'
    html = html.replace("</head>", jsonld_block, 1)

    # Replace loading state with SSR content
    html = html.replace(
        '<div class="loading-state" id="doc-loading">Loading document&hellip;</div>',
        ssr_html,
    )

    return html


def main():
    template_html = TEMPLATE.read_text(encoding="utf-8")
    for doc_id, md_filename in DOCS.items():
        html = build_page(doc_id, md_filename, template_html)
        out_path = OUTPUT_DIR / f"{doc_id}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"  Generated: {out_path.name} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
