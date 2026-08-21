"""Tests for app.api endpoints."""

from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["whisper_model"] == "large-v3-turbo"


def test_probe_nonexistent_file():
    response = client.post("/api/v1/probe", json={"path": "/tmp/nonexistent_file_xyz.mkv"})
    assert response.status_code == 404


def test_batch_missing_no_db():
    response = client.post("/api/v1/batch-missing", json={"limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()


def test_event_endpoint_ignored_test_payload():
    response = client.post("/api/v1/event", json={"eventType": "Test"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ignored"


def test_event_endpoint_with_bazarr_movie_structure():
    response = client.post(
        "/api/v1/event",
        json={"eventType": "Download", "movie": {"path": "/tmp/nonexistent_movie.mkv"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "not found" in data["details"].lower()


def test_guardian_audit_endpoint():
    response = client.post("/api/v1/guardian/audit?apply_cleanup=false")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "orphan_candidates" in data


