"""GET /api/principal -- who am I, through which door (P4 slice 2).

Read-only introspection of the one-principal resolver. Adds no gate: it only
reports what the presented credential resolves to, so clients and the shell can
show the acting principal and the credential type receipts will name.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.deps import state
from app.principal import resolve_principal

router = APIRouter(tags=["principal"])


@router.get("/api/principal")
async def whoami(request: Request) -> dict:
    p = resolve_principal(request, state, allow_magic=True)
    return {**p.as_dict(), "ref": p.ref}
