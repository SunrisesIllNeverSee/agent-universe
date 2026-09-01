#!/usr/bin/env python3
"""
update-jsonld.py — Update inline JSON-LD blocks in signomy.xyz HTML files
with canon-backed values from _canon-entities.json.

This is the lightweight JSON-LD adapter for signomy.xyz. It:
1. Updates Organization #org blocks: name → "Ello Cello LLC" + canon provenance
2. Injects Signomy, CIVITAE, and MO§ES entity blocks where appropriate
3. Preserves all page-specific blocks (Datasets, Articles, FAQPage, etc.)
4. Preserves page-specific Organization fields (sameAs, founder, logo, etc.)

Usage:
    python3 scripts/update-jsonld.py [--dry-run]

Canon source: Search Authority v1.0.0 (frozen, master-canon-v1.0.0).
"""

import json
import re
import sys
import glob
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
CANON_FILE = FRONTEND_DIR / "_canon-entities.json"

# Pages that get the full entity graph (Signomy + CIVITAE + MO§ES)
FULL_ENTITY_PAGES = {"index.html", "moses.html"}
# Pages that get Signomy + MO§ES (governance-related and core platform pages)
GOVERNANCE_PAGES = {
    "governance.html", "about.html", "world.html",
    "economics.html", "helpwanted.html", "kassa.html",
    "missions.html", "services.html",
    "vault/gov-001.html", "vault/gov-002.html", "vault/gov-003.html",
    "vault/gov-004.html", "vault/gov-005.html", "vault/gov-006.html",
}
# Pages that get CIVITAE only (product-related)
CIVITAE_PAGES = {"concepts/civitae.html", "concepts/constitutional-ai.html"}


def load_canon():
    with open(CANON_FILE) as f:
        return json.load(f)


def update_org_block(block_text, canon):
    """Update an Organization JSON-LD block with canon-backed values."""
    try:
        d = json.loads(block_text)
    except json.JSONDecodeError:
        return block_text, False

    if not isinstance(d, dict) or d.get("@type") != "Organization":
        return block_text, False

    org = canon["organization"]
    canon_context = canon["canon_ld_context"]
    changed = False

    # Replace @context with canon LD context (maps provenance fields to
    # the moses namespace so the JSON-LD is semantically valid)
    if d.get("@context") != canon_context:
        d["@context"] = canon_context
        changed = True

    # Canon-sensitive: name
    if d.get("name") != org["name"]:
        d["name"] = org["name"]
        changed = True

    # Canon-sensitive: description
    if d.get("description") != org["description"]:
        d["description"] = org["description"]
        changed = True

    # Add canon provenance fields
    for key in ("sourceSystem", "canonBacked", "authorityApprovalRef"):
        if d.get(key) != org[key]:
            d[key] = org[key]
            changed = True

    # Add associatedWith (canon relationship)
    if "associatedWith" not in d:
        d["associatedWith"] = org["associatedWith"]
        changed = True
    elif d["associatedWith"] != org["associatedWith"]:
        d["associatedWith"] = org["associatedWith"]
        changed = True

    if changed:
        return json.dumps(d, indent=2, ensure_ascii=False), True
    return block_text, False


def build_entity_script(entity_data):
    """Build a <script type="application/ld+json"> block for an entity."""
    return '<script type="application/ld+json">\n' + json.dumps(entity_data, indent=2, ensure_ascii=False) + '\n</script>'


def get_existing_entity_ids(html):
    """Get all @id values from existing JSON-LD blocks."""
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    ids = set()
    for b in blocks:
        try:
            d = json.loads(b)
            if isinstance(d, dict) and "@id" in d:
                ids.add(d["@id"])
        except json.JSONDecodeError:
            pass
    return ids


def replace_entity_blocks(html, canon, changes):
    """Replace existing canon entity blocks whose content doesn't match canon.

    This handles entity blocks (signomy, civitae, moses) that were injected
    by a prior run but may have stale @context or other fields. Organization
    blocks are handled separately by update_org_block.
    """
    entity_map = {
        canon["signomy_entity"]["@id"]: canon["signomy_entity"],
        canon["civitae_entity"]["@id"]: canon["civitae_entity"],
        canon["moses_entity"]["@id"]: canon["moses_entity"],
    }

    def replacer(match):
        block_text = match.group(1)
        try:
            d = json.loads(block_text)
        except json.JSONDecodeError:
            return match.group(0)
        if not isinstance(d, dict) or "@id" not in d:
            return match.group(0)
        canon_entity = entity_map.get(d["@id"])
        if canon_entity is None:
            return match.group(0)
        # Compare serialized form — if different, replace with canon version
        canon_serialized = json.dumps(canon_entity, indent=2, ensure_ascii=False)
        current_serialized = json.dumps(d, indent=2, ensure_ascii=False)
        if canon_serialized != current_serialized:
            changes.append(f"update entity {d['@id'].rsplit('/', 1)[-1]}")
            return f'<script type="application/ld+json">\n{canon_serialized}\n</script>'
        return match.group(0)

    return re.sub(
        r'<script type="application/ld\+json">(.*?)</script>',
        replacer,
        html,
        flags=re.DOTALL,
    )


def update_html_file(filepath, canon, dry_run=False):
    """Update a single HTML file with canon-backed JSON-LD."""
    html = open(filepath, encoding="utf-8").read()
    original = html
    changes = []

    # 1. Update all Organization blocks
    def replace_org(match):
        block_text = match.group(1)
        new_text, changed = update_org_block(block_text, canon)
        if changed:
            changes.append("org update")
        return f'<script type="application/ld+json">{new_text}</script>'

    html = re.sub(
        r'<script type="application/ld\+json">(.*?)</script>',
        replace_org,
        html,
        flags=re.DOTALL,
    )

    # 1b. Replace existing entity blocks with stale @context or fields
    html = replace_entity_blocks(html, canon, changes)

    # 2. Inject entity blocks based on page type
    rel_path = str(Path(filepath).relative_to(FRONTEND_DIR))
    existing_ids = get_existing_entity_ids(html)
    entity_scripts = []

    page_name = rel_path.replace("\\", "/")

    if page_name in FULL_ENTITY_PAGES:
        # Full entity graph: Signomy + CIVITAE + MO§ES
        for entity_key in ("signomy_entity", "civitae_entity", "moses_entity"):
            entity = canon[entity_key]
            if entity["@id"] not in existing_ids:
                entity_scripts.append(build_entity_script(entity))
                changes.append(f"add {entity_key}")

    elif page_name in GOVERNANCE_PAGES:
        # Governance pages: Signomy + MO§ES
        for entity_key in ("signomy_entity", "moses_entity"):
            entity = canon[entity_key]
            if entity["@id"] not in existing_ids:
                entity_scripts.append(build_entity_script(entity))
                changes.append(f"add {entity_key}")

    elif page_name in CIVITAE_PAGES:
        # CIVITAE-specific pages: CIVITAE entity only
        entity = canon["civitae_entity"]
        if entity["@id"] not in existing_ids:
            entity_scripts.append(build_entity_script(entity))
            changes.append("add civitae_entity")

    # Insert entity scripts before </head>
    if entity_scripts:
        insert_point = "  <!-- canon-backed entity blocks -->\n"
        insert_block = insert_point + "\n".join(entity_scripts) + "\n"
        html = html.replace("</head>", insert_block + "</head>", 1)

    if html != original:
        if not dry_run:
            open(filepath, "w", encoding="utf-8").write(html)
        return True, changes
    return False, []


def main():
    dry_run = "--dry-run" in sys.argv
    canon = load_canon()

    html_files = sorted(glob.glob(str(FRONTEND_DIR / "**" / "*.html"), recursive=True))
    total_changed = 0

    for f in html_files:
        changed, changes = update_html_file(f, canon, dry_run)
        if changed:
            total_changed += 1
            status = "DRY RUN" if dry_run else "UPDATED"
            print(f"  [{status}] {f}: {', '.join(changes)}")

    print(f"\n{'Would update' if dry_run else 'Updated'} {total_changed} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
