from __future__ import annotations

import re

from .models import EvolutionEvent, ExtractedItem, ThreadLedger


_TRACKED_CATEGORIES = {"IDEA", "SUGGESTION", "DECISION", "CANON_UPDATE", "CORRECTION", "ACTION"}
_ACCEPTED = {"ACCEPTED", "IMPLICITLY_ACCEPTED", "VERIFIED", "IMPLEMENTED_REPORTED"}
_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "that", "this",
    "it", "i", "we", "you", "is", "are", "be", "then", "also", "add", "build", "please",
    "implemented", "verified", "actually", "correct", "wrong", "should", "would", "could",
}


def _keywords(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9§]+", text.lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def _overlap(a: str, b: str) -> float:
    left, right = _keywords(a), _keywords(b)
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, min(len(left), len(right)))


def _turn_number(turn_id: str) -> int:
    try:
        return int(turn_id.lstrip("T"))
    except ValueError:
        return 0


def _flow_to(ledger: ThreadLedger, turn_id: str):
    return next((flow for flow in ledger.flows if flow.to_turn == turn_id), None)


def _initial_state(item: ExtractedItem) -> tuple[str, str, float]:
    if item.authority == "USER_BUILDS_ON_ASSISTANT_PROPOSAL":
        return "PROPOSED", "ASSISTANT_PROPOSED", 0.30
    if item.status in {"VERIFIED", "IMPLEMENTED_REPORTED"} and item.category == "ACTION":
        return "OPEN", item.authority, item.authority_weight
    if item.status == "CHALLENGED" and item.authority.startswith("ASSISTANT"):
        return "PROPOSED", item.authority, item.authority_weight
    return item.status, item.authority, item.authority_weight


def _append(
    item: ExtractedItem,
    *,
    turn_id: str,
    event: str,
    status: str,
    authority: str,
    authority_weight: float,
    confidence: float,
    note: str,
) -> None:
    signature = (turn_id, event, status, authority)
    if any((e.turn_id, e.event, e.status, e.authority) == signature for e in item.evolution):
        return
    item.evolution.append(EvolutionEvent(
        turn_id=turn_id,
        event=event,
        status=status,
        authority=authority,
        authority_weight=authority_weight,
        confidence=confidence,
        note=note,
    ))


def _reconstruct_item_history(ledger: ThreadLedger, item: ExtractedItem) -> None:
    initial_status, initial_authority, initial_weight = _initial_state(item)
    _append(
        item,
        turn_id=item.introduced_at,
        event="INTRODUCED",
        status=initial_status,
        authority=initial_authority,
        authority_weight=initial_weight,
        confidence=item.confidence,
        note="Initial thread-local classification; later turns may strengthen, challenge, implement, or supersede it.",
    )

    for turn_id in item.related_turns:
        flow = _flow_to(ledger, turn_id)
        relation = flow.relation if flow else "RELATED_EVIDENCE"
        if relation in {"ACCEPT_BY_CONTINUATION", "BUILD_ON"} and item.status == "IMPLICITLY_ACCEPTED":
            _append(
                item,
                turn_id=turn_id,
                event="AUTHORITY_LIFT_BY_CONTINUATION",
                status="IMPLICITLY_ACCEPTED",
                authority="USER_BUILDS_ON_ASSISTANT_PROPOSAL",
                authority_weight=item.authority_weight,
                confidence=flow.confidence if flow else item.confidence,
                note="The user continued by building on this specific proposal. This is scoped behavioral adoption, not blanket approval of the prior assistant turn.",
            )
        elif relation == "CORRECTION" or item.status == "CHALLENGED":
            _append(
                item,
                turn_id=turn_id,
                event="CHALLENGED",
                status="CHALLENGED",
                authority=item.authority,
                authority_weight=item.authority_weight,
                confidence=flow.confidence if flow else item.confidence,
                note="A later user turn challenged or corrected this item.",
            )
        elif item.status in {"VERIFIED", "IMPLEMENTED_REPORTED"}:
            _append(
                item,
                turn_id=turn_id,
                event="VERIFIED" if item.status == "VERIFIED" else "IMPLEMENTATION_REPORTED",
                status=item.status,
                authority=item.authority,
                authority_weight=item.authority_weight,
                confidence=item.confidence,
                note="Later implementation or verification evidence advanced the action lifecycle.",
            )

    if item.category == "DEFERRED_ERROR" and item.status == "OPEN":
        _append(
            item,
            turn_id=item.introduced_at,
            event="DEFERRED_UNRESOLVED",
            status="OPEN",
            authority=item.authority,
            authority_weight=item.authority_weight,
            confidence=item.confidence,
            note="The issue was acknowledged but intentionally deferred to preserve conversational flow.",
        )


def _link_supersession(ledger: ThreadLedger) -> None:
    candidates = [
        item for item in ledger.items
        if item.category in {"DECISION", "CANON_UPDATE", "CORRECTION"}
        and item.status in _ACCEPTED
        and item.authority_weight >= 0.80
    ]
    for newer in sorted(candidates, key=lambda item: _turn_number(item.introduced_at)):
        earlier = [
            item for item in ledger.items
            if _turn_number(item.introduced_at) < _turn_number(newer.introduced_at)
            and item.category in _TRACKED_CATEGORIES
            and item.status in _ACCEPTED | {"CHALLENGED"}
            and item.item_id not in newer.supersedes
            and 0 < _turn_number(newer.introduced_at) - _turn_number(item.introduced_at) <= 80
        ]
        if not earlier:
            continue
        ranked = sorted(((_overlap(item.statement, newer.statement), item) for item in earlier), key=lambda pair: pair[0], reverse=True)
        score, prior = ranked[0]
        if score < 0.38:
            continue

        newer.supersedes.append(prior.item_id)
        prior_status_before = prior.status
        if prior.status in _ACCEPTED:
            prior.status = "SUPERSEDED"
        _append(
            prior,
            turn_id=newer.introduced_at,
            event="SUPERSEDED",
            status=prior.status,
            authority=prior.authority,
            authority_weight=prior.authority_weight,
            confidence=min(0.92, 0.55 + score / 2),
            note=f"{newer.item_id} materially overlaps this earlier item (lexical overlap={score:.2f}) and carries later high-authority user evidence; previous status was {prior_status_before}.",
        )
        _append(
            newer,
            turn_id=newer.introduced_at,
            event="SUPERSEDES_PRIOR",
            status=newer.status,
            authority=newer.authority,
            authority_weight=newer.authority_weight,
            confidence=min(0.92, 0.55 + score / 2),
            note=f"Linked to earlier item {prior.item_id} as an evolution/supersession candidate (lexical overlap={score:.2f}).",
        )


def enrich_evolution(ledger: ThreadLedger) -> ThreadLedger:
    """Populate an auditable authority/evolution history without promoting parser inference to canon.

    The operation is idempotent. It reconstructs lifecycle transitions already evidenced by
    the thread ledger and conservatively links later high-authority decisions/canon updates
    to materially overlapping prior items. Supersession links are parser inferences and must
    remain reviewable; they are not automatic global-canon writes.
    """
    for item in ledger.items:
        _reconstruct_item_history(ledger, item)
    _link_supersession(ledger)
    ledger.schema_version = "0.2.0"
    ledger.metadata["evolution_enriched"] = True
    ledger.metadata["authority_model"] = "thread-local evidence hierarchy; user explicit > user continuation > tool evidence > assistant evidence > assistant proposal/inference"
    ledger.metadata["canon_promotion"] = "disabled"
    return ledger
