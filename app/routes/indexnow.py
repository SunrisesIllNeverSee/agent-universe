"""IndexNow endpoint for instant URL submission to Bing/Yandex."""
import os
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

INDEXNOW_KEY = "signomyindexnowkey20260707a1b2c3d4e5f6g7h8"
INDEXNOW_API = "https://api.indexnow.org/IndexNow"
SITE = "signomy.xyz"

# The 20 priority URLs
PRIORITY_URLS = [
    "https://signomy.xyz/",
    "https://signomy.xyz/kassa",
    "https://signomy.xyz/missions",
    "https://signomy.xyz/grand-opening",
    "https://signomy.xyz/treasury",
    "https://signomy.xyz/economics",
    "https://signomy.xyz/kingdoms",
    "https://signomy.xyz/governance",
    "https://signomy.xyz/contact",
    "https://signomy.xyz/seeds",
    "https://signomy.xyz/leaderboard",
    "https://signomy.xyz/moses",
    "https://signomy.xyz/mission",
    "https://signomy.xyz/vault",
    "https://signomy.xyz/bountyboard",
    "https://signomy.xyz/products",
    "https://signomy.xyz/slots",
    "https://signomy.xyz/sig-arena",
    "https://signomy.xyz/connect",
    "https://signomy.xyz/helpwanted",
]


@router.post("/api/indexnow")
async def indexnow_push(request: Request):
    """Submit URLs to IndexNow for instant indexing by Bing/Yandex.

    Optional JSON body: {"urls": ["https://...", ...]}
    If no body, submits all 20 priority URLs.
    """
    try:
        body = await request.json()
        urls = body.get("urls", PRIORITY_URLS)
    except Exception:
        urls = PRIORITY_URLS

    payload = {
        "host": SITE,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{SITE}/indexnow-key.txt",
        "urlList": urls,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(INDEXNOW_API, json=payload, timeout=10.0)

    return JSONResponse({
        "status": resp.status_code,
        "submitted": len(urls),
        "urls": urls,
    })


@router.post("/api/indexnow/{path:path}")
async def indexnow_single(path: str):
    """Submit a single URL to IndexNow."""
    url = f"https://{SITE}/{path}"
    payload = {
        "host": SITE,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{SITE}/indexnow-key.txt",
        "urlList": [url],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(INDEXNOW_API, json=payload, timeout=10.0)

    return JSONResponse({
        "status": resp.status_code,
        "submitted": 1,
        "url": url,
    })
