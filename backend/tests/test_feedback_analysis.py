import json
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.feedback_analysis import (
    FeedbackAnalysisValidationError,
    analyze_feedback_quality,
    build_analysis_output,
    cosine_similarity,
    validate_embedding,
)
from app.config import Settings
from app.main import create_app
from app.models import (
    Base,
    FeedbackAnalysisOutbox,
    FeedbackAnalysisRun,
    FeedbackEmbedding,
    Idea,
    IdeaReview,
    IdeaVersion,
    ReviewCycle,
    ReviewerAssignment,
    ReviewSession,
    User,
)
from app.providers.base import ProviderConfigurationError
from app.schemas import FeedbackNlpBatch, FeedbackPrioritizationBatch, FeedbackQualityBatch
from app.security import create_access_token, hash_password
from app.services.feedback_analysis import (
    create_analysis_run,
    execute_feedback_analysis,
)
from app.workers import celery_app as worker


def make_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def quality_item(feedback_id: str, **overrides):
    return {
        "feedback_id": feedback_id,
        "relevance": 0.8,
        "constructiveness": 0.6,
        "originality": 0.8,
        "internal_consistency": 0.9,
        "spam_risk": 0.1,
        "authenticity_indicator": 0.9,
        "self_reported_confidence": 0.8,
        "uncertainty": "Only this submitted review set was available.",
        "explanations": {
            "relevance": "Addresses the idea.",
            "constructiveness": "Contains a usable observation.",
            "originality": "Compared only with this evidence set.",
            "internal_consistency": "Statements do not contradict the ratings.",
            "spam_risk": "No obvious repetitive pattern.",
            "authenticity_indicator": "A weak indicator, not a verification.",
        },
        **overrides,
    }


def evidence(feedback_id: str, would_use: bool = True, content: str = "Useful feedback."):
    return {
        "feedback_id": feedback_id,
        "rating": 4,
        "usability_score": 4,
        "usefulness_score": 4,
        "completeness_score": 3,
        "feasibility_score": 4,
        "would_use": would_use,
        "feedback_text": content,
        "strengths": "The review names a useful strength.",
        "concerns": "The review identifies a concrete concern.",
        "suggested_improvements": "Add a clearer preparation roadmap.",
        "usage_context": "Reviewed the assigned version on a laptop.",
        "created_at": "2026-10-23T00:00:00+00:00",
    }


class SequenceChatProvider:
    model_id = "deterministic-analysis-test-double"

    def __init__(self, outputs: list[dict]):
        self.outputs = iter(outputs)

    def chat(self, prompt: str, system: str) -> str:
        assert "Veridica" in system
        return json.dumps(next(self.outputs))


class DeterministicEmbeddings:
    def embed(self, _text: str) -> list[float]:
        return [1.0] + [0.0] * 767


def add_database_review(session, idea, version, owner, reviewer_index: int, review_id: str):
    reviewer = User(
        id=str(uuid4()),
        email=f"reviewer-{reviewer_index}@example.invalid",
        password_hash=hash_password("a-secure-password"),
        role="reviewer",
    )
    session.add(reviewer)
    session.flush()
    cycle = session.scalar(
        select(ReviewCycle).where(ReviewCycle.idea_version_id == version.id)
    )
    if cycle is None:
        cycle = ReviewCycle(
            id=str(uuid4()),
            idea_version_id=version.id,
            opened_by_id=owner.id,
            status="open",
        )
        session.add(cycle)
        session.flush()
    assignment = ReviewerAssignment(
        id=str(uuid4()),
        idea_version_id=version.id,
        reviewer_id=reviewer.id,
        assigned_by_id=owner.id,
        review_cycle_id=cycle.id,
        active=True,
        status="submitted",
    )
    review_session = ReviewSession(
        id=str(uuid4()),
        assignment_id=assignment.id,
        idea_id=idea.id,
        idea_version_id=version.id,
        reviewer_id=reviewer.id,
        status="submitted",
    )
    review = IdeaReview(
        id=review_id,
        assignment_id=assignment.id,
        idea_id=idea.id,
        idea_version_id=version.id,
        reviewer_id=reviewer.id,
        review_session_id=review_session.id,
        idempotency_key=f"key-{review_id}",
        rating=4,
        feedback="The guided placement workflow is useful.",
        usability_score=4,
        usefulness_score=4,
        completeness_score=3,
        feasibility_score=4,
        would_use=reviewer_index % 2 == 1,
        strengths="The review names a useful strength.",
        concerns="The review identifies a concrete concern.",
        suggested_improvements="Add a clearer preparation roadmap.",
        usage_context="Reviewed the assigned version on a laptop.",
    )
    session.add(assignment)
    session.flush()
    session.add(review_session)
    session.flush()
    session.add(review)
    return review


def persisted_review_fixture(factory, review_count: int = 2):
    owner = User(
        id=str(uuid4()),
        email=f"owner-{uuid4().hex}@example.invalid",
        password_hash=hash_password("a-secure-password"),
        role="owner",
    )
    idea = Idea(id=str(uuid4()), owner_id=owner.id, status="Review open", current_version=1)
    version = IdeaVersion(
        id=str(uuid4()),
        idea_id=idea.id,
        created_by_id=owner.id,
        version=1,
        title="Campus Compass",
        category="Education",
        problem="Students need a clear placement preparation process.",
        solution="A guided preparation workspace.",
        audience="College students",
        features=["Preparation roadmap"],
        constraints="No external integrations are defined.",
        change_summary="Initial version",
    )
    with factory() as session:
        session.add_all([owner, idea, version])
        session.flush()
        reviews = [
            add_database_review(session, idea, version, owner, index, str(uuid4()))
            for index in range(1, review_count + 1)
        ]
        session.commit()
        session.refresh(owner)
        session.refresh(idea)
        session.refresh(version)
        return (
            owner.id,
            idea.id,
            version.id,
            version.version,
            sorted(review.id for review in reviews),
        )


def test_quality_schema_and_source_ids_are_validated():
    with pytest.raises(ValidationError):
        FeedbackQualityBatch.model_validate({"items": [quality_item("review-1", relevance=1.2)]})

    provider = SequenceChatProvider(
        [{"items": [quality_item("unknown-review")]}]
    )
    with pytest.raises(FeedbackAnalysisValidationError, match="each source review"):
        analyze_feedback_quality(provider, [evidence("known-review")])


def test_embedding_dimensions_and_cosine_are_checked():
    left = validate_embedding([1.0, 0.0], 2)
    right = validate_embedding([0.9, 0.1], 2)
    assert cosine_similarity(left, right) == pytest.approx(0.9938837347)
    with pytest.raises(FeedbackAnalysisValidationError, match="exactly 3"):
        validate_embedding([1.0, 0.0], 3)
    with pytest.raises(FeedbackAnalysisValidationError, match="zero vector"):
        validate_embedding([0.0, 0.0], 2)


def test_partial_trust_and_consensus_have_known_deterministic_results():
    first, second = "feedback-1", "feedback-2"
    quality = FeedbackQualityBatch.model_validate(
        {"items": [quality_item(first), quality_item(second)]}
    ).items
    output = build_analysis_output(
        [first, second],
        [evidence(first, True), evidence(second, False)],
        quality,
        [],
        [],
        [],
        [],
    )
    assert [item.score for item in output.trust] == pytest.approx([0.8, 0.8])
    assert [item.evidence_coverage for item in output.trust] == pytest.approx([0.3, 0.3])
    assert all("historical_accuracy" in item.missing_factors for item in output.trust)
    assert output.consensus.raw_support == pytest.approx(0.5)
    assert output.consensus.normalized_weight_denominator == pytest.approx(1.152)
    assert output.consensus.weighted_support == pytest.approx(0.5)
    assert output.consensus.normalized_feedback_weights == pytest.approx(
        {first: 0.5, second: 0.5}
    )
    assert output.consensus.confidence_indicator == pytest.approx(0.8 * 2 / 7)
    assert output.source_feedback_ids == [first, second]


def test_zero_consensus_weight_returns_unknown_not_success_shaped_zero():
    quality = FeedbackQualityBatch.model_validate(
        {"items": [quality_item(
            "feedback-zero",
            relevance=0,
            constructiveness=0,
            originality=0,
            internal_consistency=0,
            spam_risk=1,
            authenticity_indicator=0,
        )]}
    ).items
    output = build_analysis_output(
        ["feedback-zero"],
        [evidence("feedback-zero", True)],
        quality,
        [],
        [],
        [],
        [],
    )
    assert output.consensus.normalized_weight_denominator == 0
    assert output.consensus.weighted_support is None
    assert output.consensus.confidence_indicator is None


def test_priorities_are_source_linked_and_do_not_invent_impact_or_feasibility():
    first, second = "feedback-1", "feedback-2"
    quality = FeedbackQualityBatch.model_validate(
        {"items": [quality_item(first), quality_item(second)]}
    ).items
    output = build_analysis_output(
        [first, second],
        [evidence(first), evidence(second, False)],
        quality,
        FeedbackNlpBatch.model_validate({"themes": [
            {
                "label": "Clearer preparation roadmap",
                "kind": "feature_request",
                "summary": "Reviewers requested clearer preparation steps.",
                "feedback_ids": [first, second],
            }
        ], "contradictions": []}).themes,
        FeedbackNlpBatch.model_validate({"themes": [], "contradictions": []}).contradictions,
        [],
        FeedbackPrioritizationBatch.model_validate({"proposals": [
            {
                "title": "Clearer preparation roadmap",
                "rationale": "Both reviews request clearer preparation steps.",
                "feedback_ids": [first, second],
                "theme_labels": ["Clearer preparation roadmap"],
                "impact": "high",
                "impact_rationale": "It addresses the stated preparation problem.",
                "feasibility": "unknown",
                "feasibility_rationale": "No implementation effort estimate was supplied.",
                "assumptions": [],
                "missing_inputs": ["Owner impact estimate", "Implementation effort"],
            }
        ]}).proposals,
    )
    assert output.priorities[0].priority == "P1"
    assert output.priorities[0].feedback_ids == [first, second]
    assert output.priorities[0].impact == "high"
    assert output.priorities[0].feasibility == "unknown"
    assert output.priorities[0].evidence_count == 2


def test_persisted_workflow_stores_quality_embeddings_and_provenance():
    _, factory = make_database()
    owner_id, idea_id, version_id, _version, feedback_ids = persisted_review_fixture(factory)
    settings = Settings(_env_file=None)
    with factory() as session:
        idea = session.get(Idea, idea_id)
        version = session.get(IdeaVersion, version_id)
        run, created = create_analysis_run(session, idea, version, owner_id, settings)
        assert created
        session.commit()
        run_id = run.id

    chat = SequenceChatProvider(
        [
            {"items": [quality_item(feedback_id) for feedback_id in feedback_ids]},
            {
                "themes": [
                    {
                        "label": "Preparation roadmap",
                        "kind": "feature_request",
                        "summary": "Reviewers ask for clearer preparation steps.",
                        "feedback_ids": feedback_ids,
                    }
                ],
                "contradictions": [],
            },
            {
                "proposals": [
                    {
                        "title": "Clearer preparation roadmap",
                        "rationale": "Both reviews request clearer preparation steps.",
                        "feedback_ids": feedback_ids,
                        "theme_labels": ["Preparation roadmap"],
                        "impact": "high",
                        "impact_rationale": "It addresses the stated preparation problem.",
                        "feasibility": "unknown",
                        "feasibility_rationale": "Implementation effort is not recorded.",
                        "assumptions": [],
                        "missing_inputs": ["Owner impact estimate", "Implementation effort"],
                    }
                ]
            },
        ]
    )
    result = execute_feedback_analysis(
        factory,
        settings,
        run_id,
        provider_factory=lambda _settings: chat,
        embedding_provider_factory=lambda _settings: DeterministicEmbeddings(),
    )
    assert result["status"] == "completed"
    with factory() as session:
        run = session.get(FeedbackAnalysisRun, run_id)
        vectors = list(session.scalars(select(FeedbackEmbedding)))
        assert run.status == "completed"
        assert run.validation_status == "valid"
        assert run.provider == settings.ai_provider
        assert run.embedding_model_version == settings.ollama_embedding_model
        assert run.prompt_version == "feedback-intelligence-v1"
        assert run.result["source_feedback_ids"] == feedback_ids
        assert run.result["duplicate_pairs"][0]["cosine_similarity"] == pytest.approx(1)
        assert len(vectors) == 2
        assert all(vector.dimension == 768 for vector in vectors)


def test_provider_configuration_error_is_persisted_as_failed_not_empty_success():
    _, factory = make_database()
    owner_id, idea_id, version_id, _version, _ids = persisted_review_fixture(factory, 1)
    settings = Settings(_env_file=None)
    with factory() as session:
        run, _created = create_analysis_run(
            session,
            session.get(Idea, idea_id),
            session.get(IdeaVersion, version_id),
            owner_id,
            settings,
        )
        session.commit()
        run_id = run.id

    def no_provider(_settings):
        raise ProviderConfigurationError("The configured provider is missing credentials.")

    assert execute_feedback_analysis(
        factory,
        settings,
        run_id,
        provider_factory=no_provider,
    )["status"] == "failed"
    with factory() as session:
        run = session.get(FeedbackAnalysisRun, run_id)
        assert run.status == "failed"
        assert run.result is None
        assert "missing credentials" in run.error_message


def test_feedback_outbox_receipt_schedules_version_scoped_analysis(monkeypatch):
    _, factory = make_database()
    _owner_id, _idea_id, _version_id, _version, feedback_ids = persisted_review_fixture(factory, 1)
    with factory() as session:
        outbox = FeedbackAnalysisOutbox(feedback_id=feedback_ids[0], status="pending")
        session.add(outbox)
        session.commit()
        outbox_id = outbox.id

    settings = Settings(_env_file=None)
    scheduled = []
    monkeypatch.setattr("app.db.session_factory", lambda _settings: factory)
    monkeypatch.setattr(worker, "settings", settings)
    monkeypatch.setattr(
        worker.analyze_feedback_run,
        "apply_async",
        lambda **kwargs: scheduled.append(kwargs),
    )
    response = worker.receive_feedback_analysis_request.run(outbox_id)
    assert response == {"status": "received", "feedback_id": feedback_ids[0]}
    with factory() as session:
        outbox = session.get(FeedbackAnalysisOutbox, outbox_id)
        run = session.scalar(select(FeedbackAnalysisRun))
        assert outbox.status == "received"
        assert run.status == "queued"
        assert run.source_feedback_ids == feedback_ids
    assert scheduled == [{"args": [run.id], "task_id": run.workflow_run_id}]


def test_owner_routes_are_scoped_and_queue_only_persisted_evidence():
    engine, factory = make_database()
    settings = Settings(_env_file=None)
    application = create_app(settings)
    application.state.session_factory = factory
    queued = []
    application.state.feedback_analysis_dispatcher = lambda run_id, task_id: queued.append(
        (run_id, task_id)
    )
    with TestClient(application) as client:
        owner = client.post(
            "/api/v1/auth/register",
            json={"email": f"owner-{uuid4().hex}@example.invalid", "password": "a-secure-password"},
        )
        other = client.post(
            "/api/v1/auth/register",
            json={"email": f"other-{uuid4().hex}@example.invalid", "password": "a-secure-password"},
        )
        assert owner.status_code == other.status_code == 201
        owner_headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
        created = client.post(
            "/api/v1/ideas",
            json={
                "title": "Campus Compass",
                "category": "Education",
                "problem": "Students need a clear placement process.",
                "solution": "A guided preparation workspace.",
                "audience": "College students",
                "features": ["Preparation roadmap"],
                "constraints": "No external integrations.",
            },
            headers=owner_headers,
        )
        idea_id = created.json()["id"]
        path = f"/api/v1/ideas/{idea_id}/versions/1/feedback-analysis"
        assert client.get(path, headers=other_headers).status_code == 404
        assert client.post(path, headers=other_headers).status_code == 404
        assert client.post(path, headers=owner_headers).status_code == 409

        with factory() as session:
            owner_user = session.scalar(select(User).where(User.id == owner.json()["user"]["id"]))
            idea = session.get(Idea, idea_id)
            version = session.scalar(select(IdeaVersion).where(IdeaVersion.idea_id == idea_id))
            add_database_review(session, idea, version, owner_user, 1, str(uuid4()))
            reviewer = session.scalar(select(User).where(User.role == "reviewer"))
            session.commit()
            reviewer_id = reviewer.id
        reviewer_token = create_access_token(reviewer_id, "reviewer", settings.jwt_secret, 30)
        reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}
        assert client.post(path, headers=reviewer_headers).status_code == 403
        started = client.post(path, headers=owner_headers)
        assert started.status_code == 202, started.text
        assert started.json()["status"] == "queued"
        assert queued == [(started.json()["id"], started.json()["workflow_run_id"])]
        assert client.get(path, headers=owner_headers).json()["id"] == started.json()["id"]
        assert client.get(
            f"{path}/{started.json()['id']}", headers=other_headers
        ).status_code == 404
    engine.dispose()


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires PostgreSQL + pgvector")
def test_postgres_persists_feedback_analysis_with_pgvector_similarity():
    settings = Settings()
    engine = create_engine(str(settings.database_url))
    with engine.connect() as connection:
        transaction = connection.begin()
        factory = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        owner_id, idea_id, version_id, _version, feedback_ids = persisted_review_fixture(factory)
        with factory() as session:
            run, _created = create_analysis_run(
                session,
                session.get(Idea, idea_id),
                session.get(IdeaVersion, version_id),
                owner_id,
                settings,
            )
            session.commit()
            run_id = run.id
        chat = SequenceChatProvider(
            [
                {"items": [quality_item(feedback_id) for feedback_id in feedback_ids]},
                {"themes": [], "contradictions": []},
                {"proposals": []},
            ]
        )
        outcome = execute_feedback_analysis(
            factory,
            settings,
            run_id,
            provider_factory=lambda _settings: chat,
            embedding_provider_factory=lambda _settings: DeterministicEmbeddings(),
        )
        assert outcome["status"] == "completed"
        with factory() as session:
            run = session.get(FeedbackAnalysisRun, run_id)
            assert run.result["duplicate_pairs"][0]["method"] == "pgvector_cosine"
            assert run.result["duplicate_pairs"][0]["cosine_similarity"] == pytest.approx(1)
        transaction.rollback()
    engine.dispose()
