"""API integration tests."""

import pytest
from fastapi.testclient import TestClient

from main import app
from services.security import Principal, require_admin, require_user

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_evidence_search():
    app.dependency_overrides[require_user] = lambda: Principal('00000000-0000-0000-0000-000000000001')
    r = client.post(
        "/api/v1/evidence/search",
        json={
            "query": "neonatal sepsis antibiotics benzylpenicillin",
            "active_guideline": "NICE",
            "limit": 5,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert data == []  # Unreviewed evidence must not become seed evidence.
    app.dependency_overrides.clear()


def test_rag_health():
    app.dependency_overrides[require_admin] = lambda: Principal('00000000-0000-0000-0000-000000000001', True)
    r = client.get("/api/v1/admin/rag/health")
    assert r.status_code == 200
    body = r.json()
    assert "embedding_model" in body
    assert "total_chunks" in body
    app.dependency_overrides.clear()
