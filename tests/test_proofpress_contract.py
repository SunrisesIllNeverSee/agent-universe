"""Contract: the request our ProofPress client sends must satisfy ProofPress's own submission schema.

Facts below are copied (minimal, not vendored) from the ProofPress repo at
~/Developer/active/_external-review/proofpress (read-only), commit 47614fa:
  - src/proofpress/hosted/mcp_http.py   RETRIEVAL_EVIDENCE_SCHEMA, SHA256_PATTERN, EVIDENCE_ID_PATTERN,
                                         tool `proofpress_submit_evidence` inputSchema (payload, profile, idempotency_key),
                                         JSON-RPC `tools/call` handling
  - src/proofpress/kernel/operations.py  normalize_retrieval_evidence_v1 / _normalize_locator (text_span rules)
  - src/proofpress/hosted/service.py     Bearer auth, Content-Type application/json, endpoint path /mcp
When that checkout is present the real normalizer is also run against our request (read-only import).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from app import anchor_outbox as ao
from app.anchor_outbox import AnchorOutbox, ProofPressAdapter

# --- constants copied from ProofPress (see module docstring for file paths) ---
PP_SCHEMA_VERSION = "proofpress/retrieval-evidence/v1"
PP_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
PP_EVIDENCE_ID = re.compile(r"^evd_[0-9a-f]{16}$")
PP_TOP_REQUIRED = ("schema_version", "source", "evidence", "retrieval")
PP_SOURCE_REQUIRED = ("uri", "content_digest")
PP_EVIDENCE_REQUIRED = ("quote", "locator")
PP_RETRIEVAL_REQUIRED = ("adapter", "version", "query", "config_digest")
PP_TOOL = "proofpress_submit_evidence"
PP_TOOL_ARGS = {"payload", "profile", "idempotency_key"}      # inputSchema.properties; payload required


def _capture(tmp_path):
    seen = {}

    def transport(url, body, headers):
        seen.update(url=url, body=body, headers=headers)
        return {"jsonrpc": "2.0", "id": body["id"], "result": {"isError": False, "structuredContent":
                {"evidence_id": "evd_0123456789abcdef"}, "content": [{"type": "text", "text": "{}"}]}}

    ob = AnchorOutbox(tmp_path / "a.db", adapter=ProofPressAdapter("https://pp.example/mcp", "tok", transport=transport))
    ob.enqueue("agreement.completed", "agr-1", {"agreement_id": "agr-1", "receipt_id": "r1", "to": "completed",
                                                "terms_digest": "sha256:" + "a" * 64, "actor": "agent-a"})
    assert ob.drain()["anchored"] == 1
    return seen


def test_request_matches_proofpress_schema(tmp_path):
    seen = _capture(tmp_path)
    body = seen["body"]
    assert body["jsonrpc"] == "2.0" and body["method"] == "tools/call"
    assert body["params"]["name"] == PP_TOOL
    args = body["params"]["arguments"]
    assert set(args) <= PP_TOOL_ARGS and "payload" in args and "profile" not in args   # no profile => retrieval evidence
    assert isinstance(args["idempotency_key"], str) and args["idempotency_key"]
    env = args["payload"]
    assert env["schema_version"] == PP_SCHEMA_VERSION
    for key in PP_TOP_REQUIRED:
        assert key in env
    assert all(env["source"].get(k) for k in PP_SOURCE_REQUIRED)
    assert PP_SHA256.fullmatch(env["source"]["content_digest"])
    assert all(env["evidence"].get(k) for k in PP_EVIDENCE_REQUIRED)
    assert all(env["retrieval"].get(k) for k in PP_RETRIEVAL_REQUIRED)
    assert PP_SHA256.fullmatch(env["retrieval"]["config_digest"])
    loc, quote = env["evidence"]["locator"], env["evidence"]["quote"]
    assert loc["kind"] == "text_span" and loc["start"] == 0 and loc["end"] - loc["start"] == len(quote) > 0
    assert PP_SHA256.fullmatch(loc["text_digest"])
    assert seen["headers"]["Content-Type"] == "application/json"
    assert seen["headers"]["Authorization"] == "Bearer tok"


def test_request_carries_hashes_and_ids_only(tmp_path):
    env = _capture(tmp_path)["body"]["params"]["arguments"]["payload"]
    assert set(json.loads(env["evidence"]["quote"])) <= ao.PROJECTION_KEYS | {"kind"}
    assert not re.search(r"[^@\s]+@[^@\s]+\.[^@\s]+", json.dumps(env))
    assert env["source"]["uri"] == "signomy://agreement.completed/agr-1"


def test_reply_evidence_id_shape(tmp_path):
    ob_id = ao._find_evidence_id({"result": {"structuredContent": {"evidence_id": "evd_0123456789abcdef"}}})
    assert PP_EVIDENCE_ID.fullmatch(ob_id)


_PP_SRC = Path.home() / "Developer/active/_external-review/proofpress/src"


@pytest.mark.skipif(not _PP_SRC.is_dir(), reason="ProofPress checkout not present")
def test_request_passes_real_proofpress_normalizer(tmp_path):
    sys.dont_write_bytecode = True                      # read-only: never write __pycache__ into their repo
    sys.path.insert(0, str(_PP_SRC))
    try:
        from proofpress.kernel.operations import normalize_retrieval_evidence_v1
    except Exception as exc:                            # noqa: BLE001
        pytest.skip(f"cannot import ProofPress normalizer: {exc}")
    finally:
        sys.path.remove(str(_PP_SRC))
    env = _capture(tmp_path)["body"]["params"]["arguments"]["payload"]
    receipt = normalize_retrieval_evidence_v1(env)       # raises ValueError on any contract violation
    assert receipt["schema_version"] == PP_SCHEMA_VERSION
