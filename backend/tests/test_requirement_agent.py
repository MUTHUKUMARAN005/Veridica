import json
import os
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.requirement_agent import (
    RequirementOutputValidationError,
    RequirementSourceVersion,
    analyze_requirements,
)
from app.config import Settings
from app.main import create_app
from app.models import Base, Idea, IdeaVersion, RequirementAnalysisRun, User
from app.providers import build_chat_provider
from app.providers.base import (
    ProviderConfigurationError,
    ProviderResponseError,
    RetryableProviderError,
)
from app.providers.gemini import GeminiProvider
from app.schemas import RequirementSpecification


def requirement_result():
    return {
        "problem": [{
            "text": "Students need a clearer placement preparation process.",
            "basis": "explicit",
            "source_fields": ["problem"],
        }],
        "target_users": [{
            "text": "College students.",
            "basis": "explicit",
            "source_fields": ["audience"],
        }],
        "user_journeys": [{
            "actor": {
                "text": "College student.",
                "basis": "explicit",
                "source_fields": ["audience"],
            },
            "need": {
                "text": "Prepare for placement opportunities.",
                "basis": "explicit",
                "source_fields": ["problem", "solution"],
            },
            "steps": ["Review opportunities", "Follow a preparation roadmap"],
            "outcome": {
                "text": "Preparation steps are organized.",
                "basis": "assumption",
                "source_fields": ["solution"],
            },
        }],
        "core_features": [{
            "text": "Opportunity matching.",
            "basis": "explicit",
            "source_fields": ["features"],
        }],
        "constraints": [],
        "assumptions": ["Students can provide a placement profile."],
        "acceptance_criteria": [{
            "text": "The workspace displays the provided preparation roadmap.",
            "basis": "assumption",
            "source_fields": ["features"],
        }],
        "open_questions": ["Which placement data source is intended?"],
    }


class FakeProvider:
    model_id = "deterministic-test-double"

    def __init__(self, result: str):
        self.result = result
        self.prompt = ""

    def chat(self, prompt: str, system: str) -> str:
        assert "Requirement Agent" in system
        self.prompt = prompt
        return self.result


def test_requirement_specification_rejects_missing_and_malformed_fields():
    with pytest.raises(ValidationError):
        RequirementSpecification.model_validate({"problem": [{"text": ""}]})

    provider = FakeProvider('{"problem":')
    source = RequirementSourceVersion(
        title="Campus Compass",
        problem="Students need a clearer process.",
        solution="A guided workspace for preparation.",
        audience="College students",
        features=["Preparation roadmap"],
        constraints="",
    )
    with pytest.raises(RequirementOutputValidationError):
        analyze_requirements(source, provider)


def test_agent_uses_only_typed_source_and_accepts_valid_output():
    provider = FakeProvider(json.dumps(requirement_result()))
    source = RequirementSourceVersion(
        title="Campus Compass",
        problem="Students need a clearer process.",
        solution="A guided workspace for preparation.",
        audience="College students",
        features=["Preparation roadmap"],
        constraints="",
    )

    result = analyze_requirements(source, provider)

    assert result.problem[0].basis == "explicit"
    assert result.assumptions
    assert result.open_questions
    assert '"problem":"Students need a clearer process."' in provider.prompt
    assert "not supplied" not in provider.prompt


def test_empty_model_output_is_a_provider_response_error():
    source = RequirementSourceVersion(
        title="Idea",
        problem="A sufficiently detailed problem statement.",
        solution="A sufficiently detailed solution statement.",
        audience="Users",
        features=["A feature"],
        constraints="",
    )
    with pytest.raises(ProviderResponseError, match="empty output"):
        analyze_requirements(source, FakeProvider(" \n"))


def test_gemini_adapter_keeps_key_out_of_url_and_handles_retryable_status(monkeypatch):
    settings = Settings(
        _env_file=None,
        ai_provider="gemini",
        gemini_api_key="unit-test-secret",
        gemini_model="gemini-test",
    )
    requests = []

    def fake_post(url, **kwargs):
        requests.append((url, kwargs))
        return httpx.Response(
            200,
            json={
                "candidates": [{
                    "content": {"parts": [{"text": '{"problem":[]}'}]},
                }],
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = build_chat_provider(settings)
    assert isinstance(provider, GeminiProvider)
    assert provider.chat("prompt", "system") == '{"problem":[]}'
    assert "unit-test-secret" not in requests[0][0]
    assert requests[0][1]["headers"]["x-goog-api-key"] == "unit-test-secret"
    assert requests[0][1]["timeout"] == settings.ai_provider_timeout_seconds

    def quota_response(url, **_kwargs):
        return httpx.Response(429, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", quota_response)
    with pytest.raises(RetryableProviderError):
        provider.chat("prompt", "system")


def test_gemini_configuration_errors_are_explicit():
    with pytest.raises(ProviderConfigurationError, match="GEMINI_API_KEY"):
        build_chat_provider(
            Settings(_env_file=None, ai_provider="gemini", gemini_model="gemini-test")
        )
    with pytest.raises(ProviderConfigurationError, match="GEMINI_MODEL"):
        build_chat_provider(Settings(_env_file=None, ai_provider="gemini", gemini_api_key="key"))


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_GEMINI_E2E") != "1",
    reason="Set RUN_GEMINI_E2E=1 to make a real Gemini request.",
)
def test_live_gemini_requirement_analysis_is_validated_and_persisted():
    settings = Settings()
    if settings.ai_provider != "gemini":
        pytest.fail("Set AI_PROVIDER=gemini in the backend environment.")
    if not settings.gemini_api_key:
        pytest.fail("Configure GEMINI_API_KEY in the backend environment.")
    if not settings.gemini_model:
        pytest.fail("Configure a provider-verified GEMINI_MODEL in the backend environment.")

    from app.services.requirements import execute_requirement_analysis

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    user_id = str(uuid4())
    idea_id = str(uuid4())
    version_id = str(uuid4())
    analysis_id = str(uuid4())
    with factory() as session:
        session.add(User(id=user_id, email=f"{user_id}@example.invalid", password_hash="test"))
        session.add(Idea(id=idea_id, owner_id=user_id, status="Draft", current_version=1))
        session.add(
            IdeaVersion(
                id=version_id,
                idea_id=idea_id,
                created_by_id=user_id,
                version=1,
                title="Campus study planner",
                category="Education",
                problem="Students need a clearer way to organize study sessions.",
                solution="A simple planner that helps students arrange study tasks.",
                audience="College students",
                features=["Create a study checklist"],
                constraints="No external integrations.",
            )
        )
        session.add(
            RequirementAnalysisRun(
                id=analysis_id,
                idea_id=idea_id,
                idea_version_id=version_id,
                source_version=1,
                requested_by_id=user_id,
                workflow_run_id=str(uuid4()),
                provider="gemini",
                model_version=settings.gemini_model,
                prompt_version="requirement-spec-v1",
                status="queued",
                validation_status="pending",
                attempt_count=0,
            )
        )
        session.commit()

    result = execute_requirement_analysis(factory, settings, analysis_id)
    assert result["status"] == "completed", "Live Gemini analysis did not complete."
    with factory() as session:
        persisted = session.get(RequirementAnalysisRun, analysis_id)
        assert persisted is not None
        assert persisted.status == "completed"
        assert persisted.validation_status == "valid"
        assert persisted.provider == "gemini"
        assert persisted.model_version == settings.gemini_model
        assert persisted.prompt_version == "requirement-spec-v1"
        validated = RequirementSpecification.model_validate(persisted.result)
        assert validated.problem
        assert validated.core_features


def make_test_client(settings: Settings | None = None):
    settings = settings or Settings(_env_file=None)
    application = create_app(settings)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    application.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    enqueued: list[tuple[str, str]] = []
    application.state.requirement_dispatcher = lambda run_id, task_id: enqueued.append(
        (run_id, task_id)
    )
    return TestClient(application), application.state.session_factory, enqueued


def register(client: TestClient, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "a-secure-password"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": " ".join(("Bearer", response.json()["access_token"]))}


def idea_payload(title: str = "Campus Compass"):
    return {
        "title": title,
        "category": "Education",
        "problem": "Students need a clearer placement preparation process.",
        "solution": "A guided workspace for placement preparation.",
        "audience": "College students",
        "features": ["Preparation roadmap"],
        "constraints": "No external integrations are defined.",
    }


def test_owner_starts_and_reads_persisted_analysis_for_exact_version():
    client, factory, enqueued = make_test_client()
    owner_headers = register(client, f"owner-{uuid4().hex}@example.invalid")
    other_headers = register(client, f"other-{uuid4().hex}@example.invalid")
    created_idea = client.post(
        "/api/v1/ideas", json=idea_payload(), headers=owner_headers
    )
    assert created_idea.status_code == 201, created_idea.text
    idea = created_idea.json()
    version = client.post(
        f"/api/v1/ideas/{idea['id']}/versions",
        json={
            **idea_payload("Campus Compass V2"),
            "expected_version": 1,
            "change_summary": "Refine the preparation flow.",
        },
        headers=owner_headers,
    )
    assert version.status_code == 201

    denied = client.post(
        f"/api/v1/ideas/{idea['id']}/versions/1/requirements",
        headers=other_headers,
    )
    assert denied.status_code == 404
    assert client.post(
        f"/api/v1/ideas/{idea['id']}/versions/1/requirements"
    ).status_code == 401
    started = client.post(
        f"/api/v1/ideas/{idea['id']}/versions/1/requirements",
        headers=owner_headers,
    )
    assert started.status_code == 202, started.text
    data = started.json()
    assert data["source_version"] == 1
    assert data["idea_version_id"] == idea["version_id"]
    assert data["status"] == "queued"
    assert data["validation_status"] == "pending"
    assert enqueued == [(data["id"], data["workflow_run_id"])]
    duplicate = client.post(
        f"/api/v1/ideas/{idea['id']}/versions/1/requirements",
        headers=owner_headers,
    )
    assert duplicate.status_code == 202
    assert duplicate.json()["id"] == data["id"]
    assert len(enqueued) == 1

    provider = FakeProvider(json.dumps(requirement_result()))
    from app.services.requirements import execute_requirement_analysis

    execution = execute_requirement_analysis(
        factory,
        Settings(_env_file=None),
        data["id"],
        provider_factory=lambda _settings: provider,
    )
    assert execution["status"] == "completed"
    with client:
        retrieved = client.get(
            f"/api/v1/ideas/{idea['id']}/versions/1/requirements/{data['id']}",
            headers=owner_headers,
        )
        assert retrieved.status_code == 200
        persisted = retrieved.json()
        assert persisted["result"]["assumptions"] == requirement_result()["assumptions"]
        assert persisted["status"] == "completed"
        assert persisted["validation_status"] == "valid"
        assert persisted["workflow_run_id"] == data["workflow_run_id"]
        assert persisted["provider"] == "ollama"
        assert persisted["prompt_version"] == "requirement-spec-v1"
        latest = client.get(
            f"/api/v1/ideas/{idea['id']}/versions/1/requirements",
            headers=owner_headers,
        )
        assert latest.json()["id"] == data["id"]
        with factory() as session:
            row = session.get(RequirementAnalysisRun, data["id"])
            assert row is not None
            assert row.attempt_count == 1
            assert row.result is not None


def test_transient_provider_error_persists_queued_retry_state():
    client, factory, _ = make_test_client()
    owner_headers = register(client, f"retry-{uuid4().hex}@example.invalid")
    created_idea = client.post(
        "/api/v1/ideas", json=idea_payload(), headers=owner_headers
    )
    idea = created_idea.json()
    started = client.post(
        f"/api/v1/ideas/{idea['id']}/versions/1/requirements",
        headers=owner_headers,
    )
    run_id = started.json()["id"]

    class TemporarilyUnavailableProvider:
        model_id = "deterministic-test-double"

        def chat(self, _prompt: str, _system: str) -> str:
            raise RetryableProviderError("Ollama request timed out.")

    from app.services.requirements import execute_requirement_analysis

    with pytest.raises(RetryableProviderError):
        execute_requirement_analysis(
            factory,
            Settings(_env_file=None),
            run_id,
            provider_factory=lambda _settings: TemporarilyUnavailableProvider(),
        )
    with factory() as session:
        run = session.get(RequirementAnalysisRun, run_id)
        assert run is not None
        assert run.status == "queued"
        assert run.attempt_count == 1
        assert run.error_message == "Ollama request timed out."


def test_missing_gemini_credentials_are_persisted_as_configuration_failure():
    settings = Settings(
        _env_file=None,
        ai_provider="gemini",
        gemini_model="gemini-test",
    )
    client, factory, enqueued = make_test_client(settings)
    owner_headers = register(client, f"owner-{uuid4().hex}@example.invalid")
    created_idea = client.post(
        "/api/v1/ideas", json=idea_payload(), headers=owner_headers
    )
    assert created_idea.status_code == 201, created_idea.text
    idea = created_idea.json()
    response = client.post(
        f"/api/v1/ideas/{idea['id']}/versions/1/requirements",
        headers=owner_headers,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "failed"
    assert "GEMINI_API_KEY" in response.json()["error_message"]
    assert response.json()["validation_status"] == "not_run"
    assert enqueued == []
    with factory() as session:
        assert session.scalar(select(RequirementAnalysisRun)).status == "failed"


def test_requirement_task_retries_transient_provider_failures(monkeypatch):
    import app.services.requirements as requirements_service
    import app.workers.celery_app as tasks

    retry_arguments = {}

    def fail_workflow(*_args, **_kwargs):
        raise RetryableProviderError("Ollama request timed out.")

    def schedule_retry(**kwargs):
        retry_arguments.update(kwargs)
        return RuntimeError("retry scheduled")

    monkeypatch.setattr(requirements_service, "execute_requirement_analysis", fail_workflow)
    monkeypatch.setattr(tasks.analyze_requirement_run, "retry", schedule_retry)
    with pytest.raises(RuntimeError, match="retry scheduled"):
        tasks.analyze_requirement_run.run("analysis-id")
    assert retry_arguments["countdown"] == 10
    assert isinstance(retry_arguments["exc"], RetryableProviderError)


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="Requires the configured PostgreSQL database",
)
def test_postgres_persists_requirement_result_with_deterministic_provider():
    from app.services.requirements import execute_requirement_analysis

    settings = Settings()
    engine = create_engine(str(settings.database_url))
    with engine.connect() as connection:
        transaction = connection.begin()
        factory = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        application = create_app(settings)
        application.state.session_factory = factory
        application.state.requirement_dispatcher = lambda *_args: None
        with TestClient(application) as client:
            owner_headers = register(
                client, f"postgres-{uuid4().hex}@example.invalid"
            )
            created = client.post(
                "/api/v1/ideas",
                json=idea_payload("PostgreSQL Requirement Check"),
                headers=owner_headers,
            )
            assert created.status_code == 201, created.text
            idea = created.json()
            started = client.post(
                f"/api/v1/ideas/{idea['id']}/versions/1/requirements",
                headers=owner_headers,
            )
            assert started.status_code == 202, started.text
            run = started.json()
            provider = FakeProvider(json.dumps(requirement_result()))
            execution = execute_requirement_analysis(
                factory,
                settings,
                run["id"],
                provider_factory=lambda _settings: provider,
            )
            assert execution["status"] == "completed"
            retrieved = client.get(
                f"/api/v1/ideas/{idea['id']}/versions/1/requirements/{run['id']}",
                headers=owner_headers,
            )
            assert retrieved.status_code == 200
            persisted = retrieved.json()
            assert persisted["validation_status"] == "valid"
            assert persisted["result"]["open_questions"] == requirement_result()["open_questions"]
            assert persisted["source_version"] == 1
            assert persisted["workflow_run_id"] == run["workflow_run_id"]
        transaction.rollback()
    engine.dispose()
