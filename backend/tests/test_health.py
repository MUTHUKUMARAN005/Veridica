import os

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services import health
from app.workers.celery_app import celery_app, ping


@pytest.fixture
def client():
    with TestClient(create_app(Settings(_env_file=None))) as test_client:
        yield test_client


def test_liveness_does_not_require_database(client):
    assert client.get("/api/v1/health/live").json() == {
        "status": "ok", "service": "veridica-api"
    }


@pytest.mark.parametrize(
    "postgres,redis", [(True, True), (False, True), (True, False), (False, False)]
)
def test_readiness_reports_real_dependency_state(client, monkeypatch, postgres, redis):
    monkeypatch.setattr(health, "check_postgres", lambda settings: postgres)
    monkeypatch.setattr(health, "check_redis", lambda settings: redis)
    response = client.get("/api/v1/health/ready")
    assert response.status_code == (200 if postgres and redis else 503)
    assert response.json()["services"] == {
        "postgres": "connected" if postgres else "unavailable",
        "redis": "connected" if redis else "unavailable",
    }


def test_cors_rejects_unknown_origin(client):
    response = client.options(
        "/api/v1/health/live",
        headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_accepts_local_frontend(client):
    response = client.get("/api/v1/health/live", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_worker_only_accepts_json():
    assert celery_app.conf.accept_content == ["json"]
    assert ping.run() == {"status": "ok", "service": "veridica-worker"}


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires PostgreSQL and Redis")
def test_live_dependencies_and_worker(client):
    assert client.get("/api/v1/health/ready").status_code == 200
    assert ping.delay().get(timeout=15) == {"status": "ok", "service": "veridica-worker"}