from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.main import create_app
from app.models import Base


def client():
    settings = Settings(_env_file=None)
    app = create_app(settings)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return TestClient(app)


def payload(title="Campus Compass"):
    return {
        "title": title,
        "category": "Education",
        "problem": "Students need a better way to prepare for placements.",
        "solution": "A guided workspace for preparation and opportunity discovery.",
        "audience": "College students",
        "features": ["Matching", "Roadmap"],
        "constraints": "No live integrations yet.",
    }


def test_registration_login_and_owner_scoped_ideas():
    with client() as first:
        registered = first.post(
            "/api/v1/auth/register",
            json={"email": "owner@example.com", "password": "a-secure-password"},
        )
        assert registered.status_code == 201
        token = registered.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        created = first.post("/api/v1/ideas", json=payload(), headers=headers)
        assert created.status_code == 201
        idea_id = created.json()["id"]
        version = first.post(
            f"/api/v1/ideas/{idea_id}/versions",
            json=payload("Campus Compass V2"),
            headers=headers,
        )
        assert version.status_code == 201
        assert version.json()["version"] == 2
        detail = first.get(f"/api/v1/ideas/{idea_id}", headers=headers)
        assert [item["version"] for item in detail.json()["versions"]] == [1, 2]
        duplicate = first.post(
            "/api/v1/auth/register",
            json={"email": "owner@example.com", "password": "a-secure-password"},
        )
        assert duplicate.status_code == 409


def test_authentication_is_required():
    with client() as test_client:
        assert test_client.get("/api/v1/ideas").status_code == 401
        response = test_client.post(
            "/api/v1/auth/register",
            json={"email": "bad@example.com", "password": "short"},
        )
        assert response.status_code == 422
