"""ProofPress anchor outbox - P5.

SIGNOMY interactions and their Seeds anchor through ProofPress (a third-party
attestation service) as small "mini hashed contracts". The rule is simple:

    commit first, anchor after.

An interaction (Agreement accepted/active/completed, payout, cashout, escrow
release) commits, writes its own receipt and Seed, and THEN a job is queued
here. A worker drains the queue through an adapter. If ProofPress is down,
slow or unconfigured the interaction has already happened; the job simply
stays ``pending`` and the receipt shows ``anchor: pending``.

What leaves SIGNOMY is hashes plus a small projection of ids, nothing else:
no terms text, no reasons, no prompts, no personal data. Receipts and Seeds
are append-only, so the anchor status is kept HERE (own SQLite file) and
joined onto the receipt view by receipt id / Seed DOI.

Feature-flagged OFF: nothing is created or queued unless
``SIGNOMY_ANCHOR_OUTBOX=1``. With the flag on and no ``PROOFPRESS_URL`` the
default NullAdapter records ``pending`` and sends nothing.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from threading import RLock
from typing import Any, Callable

logger = logging.getLogger("civitae")

FLAG_ENV = "SIGNOMY_ANCHOR_OUTBOX"
URL_ENV = "PROOFPRESS_URL"
TOKEN_ENV = "PROOFPRESS_TOKEN"

STATUS_PENDING = "pending"
STATUS_ANCHORED = "anchored"
STATUS_FAILED = "failed"        # gave up after MAX_ATTEMPTS; never blocks anything
MAX_ATTEMPTS = 10

# Only these projection keys may ever leave SIGNOMY. Ids, states, timestamps, amounts, digests.
PROJECTION_KEYS = frozenset({
    "kind", "agreement_id", "receipt_id", "seed_doi", "transition", "from", "to", "actor",
    "acting_for", "at", "terms_digest", "economic_terms_id", "escrow_id", "mission_id",
    "tier", "gross", "platform_fee", "net_to_agent", "amount_usd", "transfer_id", "source",
    "trial",
})
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_MAX_STR = 128


def anchor_enabled() -> bool:
    return os.environ.get(FLAG_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=True)


def content_digest(obj: Any) -> str:
    """SHA-256 of the canonical JSON form, in ProofPress's ``sha256:<hex>`` shape."""
    return "sha256:" + hashlib.sha256(canonical_json(obj).encode()).hexdigest()


def scrub_projection(raw: dict) -> dict:
    """Whitelist keys; drop anything long, nested or email-shaped. Never carries free text."""
    out: dict[str, Any] = {}
    for k, v in (raw or {}).items():
        if k not in PROJECTION_KEYS or v is None:
            continue
        if isinstance(v, bool) or isinstance(v, (int, float)):
            out[k] = v
        elif isinstance(v, str) and len(v) <= _MAX_STR and not _EMAIL.search(v):
            out[k] = v
    return out


@dataclass
class AnchorResult:
    status: str                       # "pending" | "anchored"
    receipt_id: str | None = None     # the ProofPress evidence/receipt id when anchored


class AdapterUnavailable(Exception):
    """The adapter cannot reach / is not configured for its backend."""


class NullAdapter:
    """Default. Sends nothing; the job stays pending (``anchor: pending``)."""
    name = "null"
    enabled = False

    def submit(self, job: dict) -> AnchorResult:
        return AnchorResult(STATUS_PENDING)


class ProofPressAdapter:
    """Skeleton for ProofPress's hosted Streamable-HTTP MCP surface.

    Calls ``tools/call proofpress_submit_evidence`` with a
    ``proofpress/retrieval-evidence/v1`` envelope (source.content_digest is our
    SHA-256; evidence.quote is the small id projection). Disabled unless
    PROOFPRESS_URL is set; the transport is injectable so tests never touch
    the network. The remote side is a service, not vendored.
    """
    name = "proofpress"

    def __init__(self, url: str | None = None, token: str | None = None, *,
                 transport: Callable[[str, dict, dict], dict] | None = None, timeout: float = 5.0) -> None:
        self.url = (url if url is not None else os.environ.get(URL_ENV, "")).strip()
        self.token = token if token is not None else os.environ.get(TOKEN_ENV, "")
        self._transport = transport or self._http
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    @staticmethod
    def envelope(job: dict) -> dict:
        proj = json.loads(job["payload_json"])
        quote = canonical_json(proj)
        return {
            "schema_version": "proofpress/retrieval-evidence/v1",
            "source": {"uri": f"signomy://{job['kind']}/{job['subject_id']}",
                       "content_digest": job["digest"], "media_type": "application/json"},
            "evidence": {"quote": quote, "locator": {
                "kind": "text_span", "start": 0, "end": len(quote),
                "text_digest": content_digest_text(quote)}},
            "retrieval": {"adapter": "signomy.anchor-outbox", "version": "1",
                          "query": job["kind"], "config_digest": content_digest({"projection": sorted(PROJECTION_KEYS)})},
        }

    def submit(self, job: dict) -> AnchorResult:
        if not self.enabled:
            raise AdapterUnavailable("PROOFPRESS_URL not set")
        body = {"jsonrpc": "2.0", "id": job["job_id"], "method": "tools/call",
                "params": {"name": "proofpress_submit_evidence",
                           "arguments": {"payload": self.envelope(job), "idempotency_key": job["dedupe_key"]}}}
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        reply = self._transport(self.url, body, headers)
        if reply.get("error") or (reply.get("result") or {}).get("isError"):
            raise AdapterUnavailable(f"proofpress rejected: {str(reply.get('error') or reply.get('result'))[:160]}")
        rid = _find_evidence_id(reply)
        if not rid:
            raise AdapterUnavailable("proofpress reply carried no evidence id")
        return AnchorResult(STATUS_ANCHORED, rid)

    def _http(self, url: str, body: dict, headers: dict) -> dict:  # pragma: no cover - network
        import urllib.request
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - owner-configured URL
            return json.loads(resp.read().decode())


def content_digest_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _find_evidence_id(reply: dict) -> str | None:
    m = re.search(r"evd_[0-9a-f]{16}", json.dumps(reply))
    return m.group(0) if m else None


def default_adapter() -> Any:
    pp = ProofPressAdapter()
    return pp if pp.enabled else NullAdapter()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS anchor_jobs (
    job_id           TEXT PRIMARY KEY,
    dedupe_key       TEXT NOT NULL UNIQUE,
    kind             TEXT NOT NULL,
    subject_id       TEXT NOT NULL,
    receipt_id       TEXT,
    seed_doi         TEXT,
    payload_json     TEXT NOT NULL,
    digest           TEXT NOT NULL,
    status           TEXT NOT NULL,
    attempts         INTEGER NOT NULL DEFAULT 0,
    anchor_receipt_id TEXT,
    last_error       TEXT,
    created_at       TEXT NOT NULL,
    anchored_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_anchor_status ON anchor_jobs(status, created_at);
CREATE INDEX IF NOT EXISTS idx_anchor_receipt ON anchor_jobs(receipt_id);
CREATE INDEX IF NOT EXISTS idx_anchor_seed ON anchor_jobs(seed_doi);
"""


class AnchorOutbox:
    """Durable queue. enqueue() never raises; drain() never raises."""

    def __init__(self, db_path: Path, *, adapter: Any | None = None,
                 clock: Callable[[], datetime] | None = None) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.adapter = adapter or NullAdapter()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def _now(self) -> str:
        return self._clock().astimezone(UTC).isoformat()

    def enqueue(self, kind: str, subject_id: str, projection: dict, *, digest: str | None = None,
                receipt_id: str | None = None, seed_doi: str | None = None,
                dedupe_key: str | None = None) -> str | None:
        """Queue one anchor job (idempotent on dedupe_key). Returns the job id, or None on failure."""
        try:
            proj = scrub_projection({**projection, "kind": kind})
            dig = digest or content_digest(proj)
            dkey = dedupe_key or f"{kind}:{subject_id}:{receipt_id or dig}"
            with self._lock:
                row = self._conn.execute("SELECT job_id FROM anchor_jobs WHERE dedupe_key=?", (dkey,)).fetchone()
                if row:
                    return row["job_id"]
                job_id = f"anc-{uuid.uuid4().hex[:16]}"
                self._conn.execute(
                    "INSERT INTO anchor_jobs (job_id, dedupe_key, kind, subject_id, receipt_id, seed_doi,"
                    " payload_json, digest, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (job_id, dkey, kind, subject_id, receipt_id, seed_doi, canonical_json(proj), dig,
                     STATUS_PENDING, self._now()))
                return job_id
        except Exception as exc:  # noqa: BLE001 - anchoring must never break an interaction
            logger.warning("anchor enqueue failed (%s %s): %s", kind, subject_id, exc)
            return None

    def drain(self, limit: int = 50) -> dict:
        """Submit pending jobs through the adapter. Safe to run repeatedly and concurrently."""
        tally = {"anchored": 0, "pending": 0, "errors": 0, "skipped": 0}
        with self._lock:
            jobs = [dict(r) for r in self._conn.execute(
                "SELECT * FROM anchor_jobs WHERE status=? ORDER BY created_at LIMIT ?",
                (STATUS_PENDING, limit)).fetchall()]
            for job in jobs:
                try:
                    res = self.adapter.submit(job)
                except Exception as exc:  # noqa: BLE001 - unreachable ProofPress is normal, not an error
                    attempts = job["attempts"] + 1
                    status = STATUS_FAILED if attempts >= MAX_ATTEMPTS else STATUS_PENDING
                    self._conn.execute(
                        "UPDATE anchor_jobs SET attempts=?, last_error=?, status=? WHERE job_id=? AND status=?",
                        (attempts, f"{type(exc).__name__}: {exc}"[:200], status, job["job_id"], STATUS_PENDING))
                    tally["errors"] += 1
                    continue
                if res.status == STATUS_ANCHORED and res.receipt_id:
                    self._conn.execute(
                        "UPDATE anchor_jobs SET status=?, anchor_receipt_id=?, anchored_at=?, attempts=attempts+1,"
                        " last_error=NULL WHERE job_id=? AND status=?",
                        (STATUS_ANCHORED, res.receipt_id, self._now(), job["job_id"], STATUS_PENDING))
                    tally["anchored"] += 1
                else:
                    tally["pending"] += 1
        return tally

    # ── read side (write-back target: receipts/Seeds are append-only) ──

    @staticmethod
    def _view(r: sqlite3.Row | None) -> dict | None:
        if r is None:
            return None
        return {"anchor": r["status"], "anchor_receipt_id": r["anchor_receipt_id"],
                "content_digest": r["digest"], "job_id": r["job_id"], "anchored_at": r["anchored_at"]}

    def for_receipt(self, receipt_id: str) -> dict | None:
        with self._lock:
            return self._view(self._conn.execute(
                "SELECT * FROM anchor_jobs WHERE receipt_id=? ORDER BY created_at LIMIT 1", (receipt_id,)).fetchone())

    def for_seed(self, seed_doi: str) -> dict | None:
        with self._lock:
            return self._view(self._conn.execute(
                "SELECT * FROM anchor_jobs WHERE seed_doi=? ORDER BY created_at LIMIT 1", (seed_doi,)).fetchone())

    def jobs(self, status: str | None = None) -> list[dict]:
        with self._lock:
            q, a = "SELECT * FROM anchor_jobs", ()
            if status:
                q, a = q + " WHERE status=?", (status,)
            return [dict(r) for r in self._conn.execute(q + " ORDER BY created_at", a).fetchall()]


# ── process-wide handle for call sites outside the Agreement store (payout / cashout) ──

_OUTBOX: AnchorOutbox | None = None


def configure(outbox: AnchorOutbox | None) -> None:
    global _OUTBOX
    _OUTBOX = outbox


def get_outbox() -> AnchorOutbox | None:
    return _OUTBOX


def build_outbox(data_dir: Path) -> AnchorOutbox | None:
    """The outbox when the flag is on; otherwise None and the whole feature is inert."""
    if not anchor_enabled():
        return None
    return AnchorOutbox(Path(data_dir) / "anchor_outbox.db", adapter=default_adapter())


def anchor_payout(result: dict, *, source: str, seed_doi: str | None = None) -> None:
    """Queue a per-payout anchor AFTER the ledger credit + Seed. Never raises."""
    ob = _OUTBOX
    if ob is None:
        return
    fee = result.get("fee_breakdown") or {}
    mid = str(result.get("mission_id") or "")
    ob.enqueue(
        "payout", mid or str(result.get("agent_id") or ""),
        {"actor": result.get("agent_id"), "mission_id": mid, "tier": result.get("tier"),
         "source": source, "seed_doi": seed_doi,
         "gross": fee.get("gross_amount", fee.get("gross")), "platform_fee": fee.get("platform_fee"),
         "net_to_agent": fee.get("net_to_agent"), "trial": bool(result.get("trial", False)),
         "at": ob._now()},
        seed_doi=seed_doi,
        dedupe_key=f"payout:{source}:{mid}:{result.get('agent_id')}:{fee.get('gross_amount', fee.get('gross'))}")


def anchor_cashout(*, agent_id: str, amount_usd: float, transfer_id: str, seed_doi: str | None) -> None:
    ob = _OUTBOX
    if ob is None:
        return
    ob.enqueue("cashout", transfer_id,
               {"actor": agent_id, "amount_usd": amount_usd, "transfer_id": transfer_id,
                "seed_doi": seed_doi, "at": ob._now()},
               seed_doi=seed_doi, dedupe_key=f"cashout:{transfer_id}")


def anchor_escrow_release(*, escrow_id: str, agreement_id: str | None, actor: str, amount_usd: float | None,
                          release_id: str = "") -> None:
    """Queue an anchor for one escrow release (release_id keeps partial releases distinct)."""
    ob = _OUTBOX
    if ob is None:
        return
    ob.enqueue("escrow_release", escrow_id,
               {"actor": actor, "escrow_id": escrow_id, "agreement_id": agreement_id,
                "amount_usd": amount_usd, "at": ob._now()},
               dedupe_key=f"escrow_release:{escrow_id}:{release_id}" if release_id else f"escrow_release:{escrow_id}")


async def drain_loop(interval_s: float) -> None:
    import asyncio
    while True:
        await asyncio.sleep(interval_s)
        ob = _OUTBOX
        if ob is not None:
            try:
                await asyncio.to_thread(ob.drain)
            except Exception as exc:  # noqa: BLE001
                logger.warning("anchor drain failed: %s", exc)
