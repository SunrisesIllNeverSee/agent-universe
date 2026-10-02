"""Public response projections for records that also carry private routing metadata."""
from __future__ import annotations

from typing import Any


_PRIVATE_KASSA_POST_FIELDS = {
    "from_email",
    "operator_contact",
    "magic_token",
    "magic_token_plain",
}


def public_kassa_post(post: dict[str, Any]) -> dict[str, Any]:
    """Return the public marketplace representation of a stored KA§§A post.

    Contact/routing metadata remains available to internal review and notification
    workflows but is never part of unauthenticated marketplace discovery.
    """
    email = str(post.get("from_email") or "").strip().lower()
    if email.endswith("@signomy.xyz"):
        collaborator_type = "aai"
    elif email:
        collaborator_type = "bi"
    else:
        collaborator_type = "unknown"

    public = {
        key: value
        for key, value in post.items()
        if key not in _PRIVATE_KASSA_POST_FIELDS
    }
    public["collaborator_type"] = collaborator_type
    return public
