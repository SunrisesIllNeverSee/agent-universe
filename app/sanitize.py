"""
Input sanitization for user-submitted content.

Prevents XSS by escaping HTML entities at the storage boundary.
The frontend renders content as innerHTML in several places (forums,
kassa posts, thread messages), so we escape before persisting.
"""
import html
import re


def sanitize_text(text: str) -> str:
    """Escape HTML entities in user-submitted text.

    Preserves newlines and basic punctuation but neutralizes any
    HTML/script injection. Safe for display in innerHTML contexts.
    """
    if not text:
        return text
    # Escape HTML special characters
    cleaned = html.escape(text, quote=True)
    # Strip null bytes (common injection payload)
    cleaned = cleaned.replace("\x00", "")
    return cleaned


def sanitize_name(name: str, max_length: int = 120) -> str:
    """Sanitize a name/title field — escape HTML + collapse whitespace."""
    if not name:
        return name
    cleaned = sanitize_text(name)
    # Collapse internal whitespace to single spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_length]
