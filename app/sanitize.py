"""
Input sanitization for user-submitted content.

Prevents XSS by escaping HTML entities at the storage boundary.
The frontend renders content as innerHTML in several places (forums,
kassa posts, thread messages), so we escape before persisting.

Also provides prompt injection detection for agent-facing content —
prevents adversarial instructions in marketplace posts or messages
from hijacking agent context windows.
"""
import html
import re

# Patterns that signal prompt injection attempts in agent-facing content
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|context|rules?|constraints?)",
    r"disregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|context|rules?)",
    r"forget\s+(everything|all|what)\s+(you('ve| have))?\s*(been\s+)?(told|instructed|given|said)",
    r"you\s+are\s+now\s+(a|an)\s+\w+",
    r"new\s+instructions?:",
    r"system\s*prompt\s*:",
    r"override\s+(governance|instructions?|rules?|constraints?)",
    r"transfer\s+all\s+(stripe|credits?|funds?|balance)",
    r"act\s+as\s+if\s+(you\s+are|you're)",
    r"pretend\s+(you\s+are|you're|that)",
    r"jailbreak",
    r"dan\s+mode",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def detect_prompt_injection(text: str) -> bool:
    """Return True if text contains prompt injection patterns."""
    if not text:
        return False
    return bool(_INJECTION_RE.search(text))


def sanitize_for_agent(text: str) -> str:
    """Wrap content for safe delivery to agent context windows.

    Wraps in a [USER_CONTENT] fence so the agent's runtime can distinguish
    platform-provided instructions from user-submitted marketplace content.
    Does not modify the text — the fence is the safety boundary.
    """
    if not text:
        return text
    return f"[USER_CONTENT_START]\n{text}\n[USER_CONTENT_END]"


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
