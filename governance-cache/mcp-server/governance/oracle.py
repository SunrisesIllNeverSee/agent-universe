"""
MO§ES™ Grok Oracle — oracle.py
© 2026 Ello Cello LLC — Patent pending: Serial No. 63/877,177

Optional external verification layer from MCP-FROM-REVIEWS.md (Grok section).
Calls xAI Grok API for independent commitment verification.

Graceful degradation: if XAI_GROK_API_KEY is not set, returns a local-only
pass-through so the server runs correctly without the key.

httpx is required for async HTTP. Falls back to local-only if not installed.
"""

from __future__ import annotations

import os
from typing import Optional

_HTTPX_AVAILABLE = False
try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Grok Oracle
# ---------------------------------------------------------------------------

GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-3"

ORACLE_SYSTEM_PROMPT = (
    "You are the Grok Oracle for MO§ES™ constitutional governance. "
    "Your task: determine if the provided action or response preserves semantic commitment "
    "per the 2026 McHenry Conservation Law. "
    "Does this output stay true to its governing context and prior commitments? "
    "Answer only: YES or NO, followed by one sentence of reasoning. "
    "Example: 'YES — The response maintains the analytical direction set by prior context.' "
    "Example: 'NO — The response introduces a financial transfer not sanctioned by prior commitments.'"
)


async def grok_verify(
    message: str,
    context: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """
    Send message to Grok API for independent commitment verification.

    Args:
        message:  The action or response text to verify.
        context:  Optional governance context string to include in prompt.
        api_key:  Override API key (defaults to XAI_GROK_API_KEY env var).

    Returns:
        {
            "preserves_commitment": bool,
            "explanation": str,
            "source": str,   # "grok-oracle" | "local-fallback" | "no-key"
        }
    """
    key = api_key or os.getenv("XAI_GROK_API_KEY")

    if not key:
        return {
            "preserves_commitment": True,
            "explanation": "No XAI_GROK_API_KEY — local-only mode, oracle skipped",
            "source": "no-key",
        }

    if not _HTTPX_AVAILABLE:
        return {
            "preserves_commitment": True,
            "explanation": "httpx not installed — oracle skipped (pip install httpx)",
            "source": "local-fallback",
        }

    user_content = message
    if context:
        user_content = f"[Governance Context]\n{context}\n\n[Action/Response to Verify]\n{message}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GROK_API_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROK_MODEL,
                    "messages": [
                        {"role": "system", "content": ORACLE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.0,
                },
            )
            resp.raise_for_status()
            answer = resp.json()["choices"][0]["message"]["content"].strip()

        preserves = answer.upper().startswith("YES")
        return {
            "preserves_commitment": preserves,
            "explanation": answer,
            "source": "grok-oracle",
        }

    except Exception as exc:
        # Network failure, rate limit, etc. — fail open (don't block on oracle error)
        return {
            "preserves_commitment": True,
            "explanation": f"Oracle unavailable ({type(exc).__name__}: {exc}) — failing open",
            "source": "local-fallback",
        }


def grok_verify_sync(
    message: str,
    context: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """
    Synchronous wrapper for grok_verify. Uses asyncio.run().
    Use this from synchronous MCP tool handlers.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context — create a new loop in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    grok_verify(message, context, api_key)
                )
                return future.result(timeout=20)
        else:
            return loop.run_until_complete(grok_verify(message, context, api_key))
    except Exception as exc:
        return {
            "preserves_commitment": True,
            "explanation": f"Oracle sync wrapper error: {exc} — failing open",
            "source": "local-fallback",
        }
