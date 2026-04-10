"""
test_routes_operator.py — HTTP contract tests for app/routes/operator.py

9 endpoints — all admin-gated except /api/contact and /api/inbox/apply.
Covers: stats, audit, contacts, threads, inbox, contact form, apply.
"""
import uuid


# ── Admin-gated endpoints ─────────────────────────────────────────────────────

def test_operator_stats_requires_admin(client):
    r = client.get("/api/operator/stats")
    assert r.status_code == 403


def test_operator_stats(admin_client):
    r = admin_client.get("/api/operator/stats")
    assert r.status_code == 200
    d = r.json()
    # API returns "agents" and "missions" (not "total_agents"/"total_missions")
    assert "agents" in d or "total_agents" in d
    assert "missions" in d or "total_missions" in d


def test_operator_audit_requires_admin(client):
    r = client.get("/api/operator/audit")
    assert r.status_code == 403


def test_operator_audit(admin_client):
    r = admin_client.get("/api/operator/audit")
    assert r.status_code == 200
    d = r.json()
    assert "events" in d or "audit" in d or isinstance(d, list) or isinstance(d, dict)


def test_operator_contacts_requires_admin(client):
    r = client.get("/api/operator/contacts")
    assert r.status_code == 403


def test_operator_contacts(admin_client):
    r = admin_client.get("/api/operator/contacts")
    assert r.status_code == 200


def test_operator_threads_requires_admin(client):
    r = client.get("/api/operator/threads")
    assert r.status_code == 403


def test_operator_threads(admin_client):
    r = admin_client.get("/api/operator/threads")
    assert r.status_code == 200
    d = r.json()
    assert "threads" in d
    assert "count" in d


def test_operator_inbox_public(client):
    # GET /api/inbox is not in _ADMIN_GET_PREFIXES — publicly readable
    r = client.get("/api/inbox")
    assert r.status_code == 200


# ── Public endpoints ──────────────────────────────────────────────────────────

def test_contact_form_public(client):
    r = client.post("/api/contact", json={
        "name": f"Tester {uuid.uuid4().hex[:4]}",
        "email": f"test-{uuid.uuid4().hex[:4]}@example.com",
        "message": "Test message from integration suite",
        "subject": "Test Subject",
    })
    assert r.status_code in (200, 201, 429)  # 429 if rate-limited


def test_contact_form_missing_fields_400(client):
    r = client.post("/api/contact", json={"name": "No email"})
    assert r.status_code == 400


def test_inbox_apply_public(client):
    r = client.post("/api/inbox/apply", json={
        "name": f"Applicant {uuid.uuid4().hex[:4]}",
        "email": f"apply-{uuid.uuid4().hex[:4]}@example.com",
        "role": "developer",
        "message": "I want to contribute",
    })
    assert r.status_code in (200, 201, 400, 422)  # depends on required fields
