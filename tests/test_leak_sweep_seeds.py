"""Leak sweep 2026-10-16: public Seed/provenance reads (/api/seeds, /api/seeds/{doi},
/api/seeds/{doi}/lineage, /api/traces/otel|dataset|sigrank) return the public seed projection.
Before: contact-form, advisory and KA§§A contact/post seeds carried the submitter's raw email
as creator_id (and their name in metadata) to any anonymous caller."""
import hashlib
import uuid

import pytest

from app.public_projection import creator_ref, public_seed


@pytest.fixture(autouse=True)
def _own_seed_file(tmp_path, monkeypatch):
    """Keep these reads small and independent of the shared repo-level seeds.jsonl."""
    from app import seeds
    monkeypatch.setattr(seeds, "SEEDS_FILE", str(tmp_path / "seeds.jsonl"))


def _uniq():
    return uuid.uuid4().hex[:8]


def test_contact_form_seed_hides_email_and_name(client):
    email, name = f"seedleak-{_uniq()}@example.com", f"Seed Person {_uniq()}"
    r = client.post("/api/contact", json={"name": name, "email": email, "subject": "s", "message": "m"},
                    headers={"x-forwarded-for": f"10.77.{uuid.uuid4().int % 250}.1"})
    assert r.status_code == 200
    cid = r.json()["id"]
    page = client.get("/api/seeds?limit=200&source_type=contact")
    mine = [s for s in page.json()["seeds"] if s["source_id"] == cid]
    assert mine, "contact seed must still be listed"
    seed = mine[0]
    ref = "bi:" + hashlib.sha256(email.lower().encode()).hexdigest()[:16]
    assert seed["creator_id"] == ref and "name" not in seed["metadata"]
    assert seed["metadata"].get("subject") == "s"
    for url in (f"/api/seeds/{seed['doi']}", f"/api/seeds/{seed['doi']}/lineage",
                "/api/traces/otel", "/api/traces/otel?anonymize=false", "/api/traces/sigrank"):
        body = client.get(url).text
        assert email not in body and name not in body, url


def test_advisory_aai_application_email_is_not_an_agent_id(client):
    email = f"aai-{_uniq()}@example.com"
    r = client.post("/api/advisory/apply", json={"seat_id": "seat-12", "name": f"N {_uniq()}",
                                                 "email": email, "type": "AAI", "message": "hi"})
    assert r.status_code in (200, 409)
    assert email not in client.get("/api/traces/sigrank").text


def test_projection_keeps_agent_and_platform_creators():
    seed = {"doi": "au:x", "creator_id": "agent-1234", "creator_type": "AAI", "metadata": {"name": "Bot"},
            "source_type": "registration", "internal_note": "x"}
    out = public_seed(seed)
    assert out["creator_id"] == "agent-1234" and out["metadata"] == {"name": "Bot"}
    assert "internal_note" not in out                   # explicit field list
    assert creator_ref("bot@signomy.xyz") == "bot@signomy.xyz"
    assert creator_ref("system") == "system"
    assert creator_ref("Person@Example.com") == creator_ref("person@example.com")
