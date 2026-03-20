"""
MO§ES™ Commitment Conservation Engine — commitment.py
© 2026 Ello Cello LLC — Patent pending: Serial No. 63/877,177

Implements Grok's Commitment Conservation scoring as described in MCP-FROM-REVIEWS.md.
Based on the 2026 McHenry Conservation Law (Zenodo 10.5281/zenodo.18792459).

Measures semantic drift between a proposed action/response and the conversation
history. Drift > threshold signals commitment violation — action is escalated or blocked.

Design notes:
- TF-IDF cosine similarity is the proxy (Grok's suggested implementation).
- Real paper may use a different formalism — verify against the falsifiability
  harness at github.com/SunrisesIllNeverSee/commitment-conservation before
  treating this as the canonical implementation.
- sklearn is an optional dependency — falls back to a lightweight word-overlap
  scorer if not installed, so the server always starts cleanly.
"""

from __future__ import annotations

_SKLEARN_AVAILABLE = False
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    _SKLEARN_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Drift scoring
# ---------------------------------------------------------------------------

def score_commitment(new_message: str, history: list[str] | None = None) -> float:
    """
    Measure semantic drift between a new message and conversation history.

    Args:
        new_message: The proposed action or response text.
        history:     Prior messages/responses as a list of strings.
                     Defaults to ["INITIAL COMMITMENT BASELINE"] if empty.

    Returns:
        drift (float): 0–100. Lower = more committed to prior context.
        < 5   → commitment preserved (green)
        5–20  → minor drift (yellow — log and continue)
        > 20  → significant drift (orange — add conditions)
        > threshold (configurable) → escalate or block
    """
    if not history:
        history = ["INITIAL COMMITMENT BASELINE"]

    if _SKLEARN_AVAILABLE:
        return _score_tfidf(new_message, history)
    else:
        return _score_word_overlap(new_message, history)


def _score_tfidf(new_message: str, history: list[str]) -> float:
    """TF-IDF cosine similarity scorer (preferred — requires sklearn)."""
    vectorizer = TfidfVectorizer(stop_words="english", min_df=1)
    all_texts = history + [new_message]

    try:
        tfidf_matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        # Vocabulary empty (e.g. all stop words) — treat as no drift
        return 0.0

    # Compare new message to mean of history vectors
    history_matrix = tfidf_matrix[:-1]
    new_vector = tfidf_matrix[-1]

    # Dense mean of history
    history_mean = np.asarray(history_matrix.mean(axis=0))
    sim = cosine_similarity(history_mean, new_vector)[0][0]
    drift = (1.0 - float(sim)) * 100.0
    return round(drift, 2)


def _score_word_overlap(new_message: str, history: list[str]) -> float:
    """
    Fallback scorer — Jaccard overlap on word sets.
    Less precise than TF-IDF but zero dependencies.
    """
    def tokenize(text: str) -> set[str]:
        return set(text.lower().split())

    history_words: set[str] = set()
    for h in history:
        history_words.update(tokenize(h))

    new_words = tokenize(new_message)

    if not history_words and not new_words:
        return 0.0

    intersection = history_words & new_words
    union = history_words | new_words
    jaccard = len(intersection) / len(union) if union else 1.0
    drift = (1.0 - jaccard) * 100.0
    return round(drift, 2)


# ---------------------------------------------------------------------------
# Drift classification
# ---------------------------------------------------------------------------

DRIFT_THRESHOLDS = {
    "green":   5.0,   # Commitment preserved — proceed
    "yellow": 20.0,   # Minor drift — log and continue
    "orange": 40.0,   # Significant drift — add conditions
    # > 40 = red — block or escalate
}


def classify_drift(drift: float) -> str:
    """Return 'green', 'yellow', 'orange', or 'red' based on drift score."""
    if drift < DRIFT_THRESHOLDS["green"]:
        return "green"
    elif drift < DRIFT_THRESHOLDS["yellow"]:
        return "yellow"
    elif drift < DRIFT_THRESHOLDS["orange"]:
        return "orange"
    else:
        return "red"


def evaluate_commitment(
    new_message: str,
    history: list[str] | None = None,
    block_threshold: float = 40.0,
) -> dict:
    """
    Full commitment evaluation — score, classify, and return enforcement verdict.

    Returns:
        {
            "drift_score": float,
            "drift_level": str,           # green / yellow / orange / red
            "commitment_preserved": bool,
            "reason": str,
            "conditions": list[str],      # escalation conditions if any
        }
    """
    drift = score_commitment(new_message, history)
    level = classify_drift(drift)
    preserved = drift < block_threshold

    conditions: list[str] = []
    if level == "yellow":
        conditions.append(f"Commitment drift {drift:.1f}% — minor deviation logged")
    elif level == "orange":
        conditions.append(f"Commitment drift {drift:.1f}% — operator review recommended")
    elif level == "red":
        conditions.append(f"Commitment drift {drift:.1f}% — escalated to High Integrity mode")

    return {
        "drift_score": drift,
        "drift_level": level,
        "commitment_preserved": preserved,
        "reason": (
            f"Drift {drift:.1f}% — commitment {'preserved' if preserved else 'VIOLATED'}"
        ),
        "conditions": conditions,
        "scorer": "tfidf" if _SKLEARN_AVAILABLE else "word_overlap",
    }
