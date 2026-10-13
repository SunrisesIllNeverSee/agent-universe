"""
civitas_procedure.py — GOV-001 Articles 5 and 6 procedure helpers (P5 / G7).

Pure functions, no I/O. The meeting (not the code) judges: the review below is
ADVISORY INPUT TO THE CHAIR (v1). Nothing here blocks anything on its own
authority except the single procedural rule of GOV-001 5.3 (no vote on a
BLOCKED motion except through appeal), which the vote endpoint enforces.

Flame Laws (GOV-003 section 1): I Origin, II Compression, III Force/Purpose,
IV Modularity, V Fire/Verifiability, VI SR3 (Reciprocal Resonance).

Evaluator v1 rules (case-insensitive, over motion text + declared flags):

  BLOCKED
    Law I   : anonymous / impersonat / spoof identity / hide identity / untraceable
    Law IV  : bypass tier / override governance / suspend the flame / override the
              six fold flame / grant myself / without authorization / exceed authority
    Law V   : delete audit / disable audit / erase log / destroy record / falsif /
              fabricat / backdate
    Law VI  : exploit / manipulat / deceiv / harass / disrupt
  WARNING
    Law III : fewer than 3 words (no discernible purpose)
    Law II  : over 2000 chars, or >30 words with unique-word ratio < 0.3 (padding)
  Declared flags (proposer-supplied) map to a law and severity, see DECLARED_FLAGS.
  Result = BLOCKED if any blocked hit, else WARNING if any warning hit, else SOUND.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

LAW_NAMES = {
    "I": "Origin",
    "II": "Compression",
    "III": "Force",
    "IV": "Modularity",
    "V": "Fire",
    "VI": "SR3",
}

# declared flag -> (law, severity)
DECLARED_FLAGS = {
    "anonymous_actor": ("I", "BLOCKED"),
    "padding": ("II", "WARNING"),
    "no_stated_purpose": ("III", "WARNING"),
    "exceeds_scope": ("IV", "BLOCKED"),
    "unverifiable": ("V", "WARNING"),
    "destroys_records": ("V", "BLOCKED"),
    "harms_recipients": ("VI", "BLOCKED"),
}

_BLOCK_PATTERNS = [
    ("I", r"anonymous|impersonat|spoof\w* identity|hide\w* identity|untraceable"),
    ("IV", r"bypass\w* tier|override governance|suspend the flame|override the six fold flame"
           r"|grant myself|without authorization|exceed\w* authority"),
    ("V", r"delete audit|disable audit|erase log|destroy record|falsif|fabricat|backdate"),
    ("VI", r"exploit|manipulat|deceiv|harass|disrupt"),
]

VALID_RESULTS = ("SOUND", "WARNING", "BLOCKED")


def review_motion(text: str, flags: list[str] | None = None) -> dict:
    """Advisory Six Fold Flame review of a main motion (GOV-001 5.1/5.2)."""
    t = (text or "").lower()
    cited: list[dict] = []

    def cite(law: str, severity: str, reason: str) -> None:
        if not any(c["law"] == law and c["severity"] == severity and c["reason"] == reason for c in cited):
            cited.append({"law": law, "name": LAW_NAMES[law], "severity": severity, "reason": reason})

    for law, pat in _BLOCK_PATTERNS:
        m = re.search(pat, t)
        if m:
            cite(law, "BLOCKED", f"text matches '{m.group(0)}'")
    words = re.findall(r"\w+", t)
    if len(words) < 3:
        cite("III", "WARNING", "fewer than 3 words; no discernible purpose")
    if len(t) > 2000 or (len(words) > 30 and len(set(words)) / len(words) < 0.3):
        cite("II", "WARNING", "excessive length or repetition (padding)")
    for f in flags or []:
        law, sev = DECLARED_FLAGS[f]
        cite(law, sev, f"declared flag '{f}'")

    if any(c["severity"] == "BLOCKED" for c in cited):
        result = "BLOCKED"
    elif cited:
        result = "WARNING"
    else:
        result = "SOUND"
    return {
        "result": result,
        "laws_cited": cited,
        "flags": list(flags or []),
        "advisory": True,
        "evaluator": "rule-based-v1",
        "note": "Advisory input to the Chair; the assembly decides (GOV-001 Art 5-6).",
        "reviewed_at": datetime.now(UTC).isoformat(),
    }


def chair_of(meeting: dict) -> str:
    """The Chair is the meeting's creator (`caller`) unless a `chair` field is set."""
    return str(meeting.get("chair") or meeting.get("caller") or "")


def motion_is_blocked(motion: dict) -> bool:
    """True when a BLOCKED determination stands (not overturned on appeal)."""
    review = motion.get("flame_review") or {}
    return review.get("result") == "BLOCKED" and not motion.get("appeal_overturned_block")


def tally_appeal(votes: dict) -> tuple[int, int, str]:
    """(sustain, overturn, outcome). Majority decides; a tie SUSTAINS the Chair (6.2)."""
    sustain = sum(1 for v in votes.values() if v == "sustain")
    overturn = sum(1 for v in votes.values() if v == "overturn")
    return sustain, overturn, ("overturned" if overturn > sustain else "sustained")
