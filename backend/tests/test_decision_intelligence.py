import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.config import Settings
from app.main import create_app
from app.models import (
    Base,
    DecisionReport,
    EvolutionProposal,
    FeedbackAnalysisRun,
    Idea,
    IdeaReview,
    IdeaVersion,
    RequirementAnalysisRun,
    ReviewCycle,
    ReviewerAssignment,
    ReviewSession,
    User,
)
from app.security import create_access_token, hash_password


def make_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def seed_complete_evidence(factory):
    owner = User(
        id=str(uuid4()),
        email=f"owner-{uuid4().hex}@example.invalid",
        password_hash=hash_password("a-secure-password"),
        role="owner",
    )
    reviewer = User(
        id=str(uuid4()),
        email=f"reviewer-{uuid4().hex}@example.invalid",
        password_hash=hash_password("a-secure-password"),
        role="reviewer",
    )
    idea = Idea(id=str(uuid4()), owner_id=owner.id, status="Review open", current_version=1)
    version = IdeaVersion(
        id=str(uuid4()),
        idea_id=idea.id,
        created_by_id=owner.id,
        version=1,
        title="Campus placement roadmap",
        category="Education",
        problem="Students need a clearer placement preparation process.",
        solution="A guided placement preparation workspace.",
        audience="College students",
        features=["Preparation roadmap"],
        constraints="No external integrations.",
        change_summary="Initial version",
    )
    cycle = ReviewCycle(
        id=str(uuid4()),
        idea_version_id=version.id,
        opened_by_id=owner.id,
        status="open",
    )
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
        id=str(uuid4()),
        assignment_id=assignment.id,
        idea_id=idea.id,
        idea_version_id=version.id,
        reviewer_id=reviewer.id,
        review_session_id=review_session.id,
        idempotency_key="review-key",
        rating=4,
        feedback="The roadmap needs clearer preparation steps.",
        usability_score=4,
        usefulness_score=4,
        completeness_score=3,
        feasibility_score=4,
        would_use=True,
        strengths="The guided experience is relevant.",
        concerns="The next steps remain unclear.",
        suggested_improvements="Add a staged preparation roadmap.",
        usage_context="Reviewed the assigned version on a laptop.",
    )
    requirement = RequirementAnalysisRun(
        id=str(uuid4()),
        idea_id=idea.id,
        idea_version_id=version.id,
        source_version=1,
        requested_by_id=owner.id,
        workflow_run_id=str(uuid4()),
        provider="ollama",
        model_version="test-model",
        prompt_version="requirement-spec-v1",
        status="completed",
        validation_status="valid",
        result={
            "problem": [],
            "target_users": [],
            "user_journeys": [],
            "core_features": [],
            "constraints": [],
            "assumptions": [],
            "acceptance_criteria": [],
            "open_questions": [],
        },
    )
    feedback_analysis = FeedbackAnalysisRun(
        id=str(uuid4()),
        idea_id=idea.id,
        idea_version_id=version.id,
        source_version=1,
        requested_by_id=owner.id,
        workflow_run_id=str(uuid4()),
        input_digest="a" * 64,
        source_feedback_ids=[review.id],
        provider="ollama",
        model_version="test-model",
        embedding_model_version="test-embedding",
        prompt_version="feedback-intelligence-v1",
        status="completed",
        validation_status="valid",
        result={
            "source_feedback_ids": [review.id],
            "quality": [],
            "deterministic_signals": [],
            "themes": [],
            "contradictions": [],
            "duplicate_pairs": [],
            "trust": [],
            "consensus": {
                "sample_size": 1,
                "evidence_coverage": 1,
                "raw_support_count": 1,
                "raw_support": 1,
                "normalized_weight_denominator": 0.5,
                "raw_feedback_weights": {review.id: 0.5},
                "normalized_feedback_weights": {review.id: 1},
                "weighted_support": 1,
                "confidence_indicator": 0.1,
                "confidence_method": "uncalibrated test indicator",
                "uncertainty": "One review is not definitive.",
                "evidence_ids": [review.id],
            },
            "priorities": [
                {
                    "rank": 1,
                    "priority": "P1",
                    "title": "Staged preparation roadmap",
                    "rationale": "The review asks for clearer steps.",
                    "feedback_ids": [review.id],
                    "theme_labels": ["Preparation roadmap"],
                    "evidence_count": 1,
                    "weighted_support": 1,
                    "impact": "medium",
                    "impact_rationale": "Addresses the cited concern.",
                    "feasibility": "unknown",
                    "feasibility_rationale": "No effort estimate exists.",
                    "assumptions": [],
                    "missing_inputs": ["Implementation effort"],
                }
            ],
        },
    )
    with factory() as session:
        session.add_all([owner, reviewer, idea, version])
        session.flush()
        session.add(cycle)
        session.flush()
        session.add(assignment)
        session.flush()
        session.add(review_session)
        session.flush()
        session.add_all([review, requirement, feedback_analysis])
        session.commit()
    return owner.id, idea.id, version.id, review.id


def make_client(factory, temp_dir):
    settings = Settings(_env_file=None, prototype_source_storage_dir=temp_dir)
    app = create_app(settings)
    app.state.session_factory = factory
    return settings, TestClient(app)


def test_evolution_requires_valid_evidence_and_is_owner_scoped(tmp_path):
    engine, factory = make_database()
    owner_id, idea_id, _version_id, _review_id = seed_complete_evidence(factory)
    settings, client = make_client(factory, tmp_path)
    owner_token = create_access_token(owner_id, "owner", settings.jwt_secret, 30)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    with factory() as session:
        other = User(
            id=str(uuid4()),
            email=f"other-{uuid4().hex}@example.invalid",
            password_hash=hash_password("a-secure-password"),
            role="owner",
        )
        session.add(other)
        session.commit()
        other_token = create_access_token(other.id, "owner", settings.jwt_secret, 30)
    other_headers = {"Authorization": f"Bearer {other_token}"}
    path = f"/api/v1/ideas/{idea_id}/versions/1/evolution"
    with client:
        assert client.post(path).status_code == 401
        assert client.post(path, headers=other_headers).status_code == 404
        created = client.post(path, headers=owner_headers)
        assert created.status_code == 201, created.text
        proposal = created.json()
        assert proposal["status"] == "proposed"
        assert proposal["source_feedback_ids"] == [_review_id]
        assert proposal["suggestions"][0]["builder_supported"] is True
        assert client.post(path, headers=owner_headers).json()["id"] == proposal["id"]
        assert client.get(path, headers=owner_headers).json()["id"] == proposal["id"]
        assert client.post(
            f"{path}/{proposal['id']}/approve",
            headers=other_headers,
            json={"expected_source_version": 1, "selected_ranks": [1]},
        ).status_code == 404

        stale = client.post(
            f"{path}/{proposal['id']}/approve",
            headers=owner_headers,
            json={"expected_source_version": 2, "selected_ranks": [1]},
        )
        assert stale.status_code == 409
        invalid = client.post(
            f"{path}/{proposal['id']}/approve",
            headers=owner_headers,
            json={"expected_source_version": 1, "selected_ranks": [99]},
        )
        assert invalid.status_code == 422
    engine.dispose()


def test_evolution_rejects_missing_analysis_and_out_of_scope_approval(tmp_path):
    engine, factory = make_database()
    owner_id, idea_id, _version_id, _review_id = seed_complete_evidence(factory)
    with factory() as session:
        run = session.scalar(select(FeedbackAnalysisRun))
        version = session.scalar(select(IdeaVersion))
        run.status = "failed"
        version.category = "Healthcare"
        session.commit()
    settings, client = make_client(factory, tmp_path)
    token = create_access_token(owner_id, "owner", settings.jwt_secret, 30)
    headers = {"Authorization": f"Bearer {token}"}
    path = f"/api/v1/ideas/{idea_id}/versions/1/evolution"
    with client:
        missing = client.post(path, headers=headers)
        assert missing.status_code == 409

        with factory() as session:
            run = session.scalar(select(FeedbackAnalysisRun))
            run.status = "completed"
            session.commit()
        proposal = client.post(path, headers=headers)
        assert proposal.status_code == 201
        assert proposal.json()["suggestions"][0]["builder_supported"] is False
        approval = client.post(
            f"{path}/{proposal.json()['id']}/approve",
            headers=headers,
            json={"expected_source_version": 1, "selected_ranks": [1]},
        )
        assert approval.status_code == 409
    engine.dispose()


def test_evolution_rejects_priority_citations_outside_persisted_reviews(tmp_path):
    engine, factory = make_database()
    owner_id, idea_id, _version_id, _review_id = seed_complete_evidence(factory)
    with factory() as session:
        run = session.scalar(select(FeedbackAnalysisRun))
        result = dict(run.result)
        result["priorities"] = [
            {**result["priorities"][0], "feedback_ids": ["not-a-submitted-review"]}
        ]
        run.result = result
        session.commit()
    settings, client = make_client(factory, tmp_path)
    headers = {
        "Authorization": (
            "Bearer " + create_access_token(owner_id, "owner", settings.jwt_secret, 30)
        )
    }
    with client:
        response = client.post(
            f"/api/v1/ideas/{idea_id}/versions/1/evolution",
            headers=headers,
        )
        assert response.status_code == 409
        assert "sufficient linked reviewer evidence" in response.json()["detail"]
    engine.dispose()


def test_owner_approval_creates_immutable_candidate_and_source_only_builder(tmp_path):
    engine, factory = make_database()
    owner_id, idea_id, version_id, review_id = seed_complete_evidence(factory)
    settings, client = make_client(factory, tmp_path)
    token = create_access_token(owner_id, "owner", settings.jwt_secret, 30)
    headers = {"Authorization": f"Bearer {token}"}
    path = f"/api/v1/ideas/{idea_id}/versions/1/evolution"
    with client:
        proposal = client.post(path, headers=headers).json()
        approved = client.post(
            f"{path}/{proposal['id']}/approve",
            headers=headers,
            json={"expected_source_version": 1, "selected_ranks": [1]},
        )
        assert approved.status_code == 200, approved.text
        result = approved.json()
        assert result["status"] == "approved"
        assert result["source_feedback_ids"] == [review_id]
        assert result["target_version_id"]
        assert result["prototype_build_id"]
        assert result["validation_results"]["working_prototype_validated"] is False
        assert client.get(
            f"/api/v1/ideas/{idea_id}/versions/2/evolution",
            headers=headers,
        ).json()["id"] == proposal["id"]
        repeated = client.post(
            f"{path}/{proposal['id']}/approve",
            headers=headers,
            json={"expected_source_version": 1, "selected_ranks": [1]},
        )
        assert repeated.status_code == 200
        changed = client.post(
            f"{path}/{proposal['id']}/approve",
            headers=headers,
            json={"expected_source_version": 1, "selected_ranks": [2]},
        )
        assert changed.status_code == 409
        with factory() as session:
            original = session.get(IdeaVersion, version_id)
            idea = session.get(Idea, idea_id)
            candidate = session.get(IdeaVersion, result["target_version_id"])
            proposal_record = session.get(EvolutionProposal, proposal["id"])
            assert original.version == 1
            assert original.features == ["Preparation roadmap"]
            assert idea.current_version == 2
            assert candidate.source_version_id == original.id
            assert candidate.version == 2
            assert candidate.features == [
                "Preparation roadmap",
                "Staged preparation roadmap",
            ]
            assert proposal_record.status == "approved"
    engine.dispose()


def test_decision_report_is_persisted_versioned_and_private(tmp_path):
    engine, factory = make_database()
    owner_id, idea_id, version_id, review_id = seed_complete_evidence(factory)
    settings, client = make_client(factory, tmp_path)
    owner_token = create_access_token(owner_id, "owner", settings.jwt_secret, 30)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    with factory() as session:
        other = User(
            id=str(uuid4()),
            email=f"other-{uuid4().hex}@example.invalid",
            password_hash=hash_password("a-secure-password"),
            role="owner",
        )
        session.add(other)
        session.commit()
        other_token = create_access_token(other.id, "owner", settings.jwt_secret, 30)
    path = f"/api/v1/ideas/{idea_id}/versions/1/decision-reports"
    with client:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=owner_headers).status_code == 200
        assert client.get(path, headers=owner_headers).json() is None
        assert (
            client.post(path, headers={"Authorization": f"Bearer {other_token}"}).status_code
            == 404
        )
        response = client.post(path, headers=owner_headers)
        assert response.status_code == 201, response.text
        report = response.json()
        assert report["source_version"] == 1
        assert report["source_feedback_ids"] == [review_id]
        assert report["report"]["reviews"]["sample_size"] == 1
        assert report["report"]["prototype"]["classification"] == (
            "static_source_only_not_a_working_prototype"
        )
        assert client.get(path, headers=owner_headers).json()["id"] == report["id"]
    with factory() as session:
        records = list(session.scalars(select(DecisionReport)))
        assert len(records) == 1
        assert records[0].idea_version_id == version_id
    engine.dispose()


def test_failed_analysis_is_reported_as_unavailable_not_successful_empty_analysis(tmp_path):
    engine, factory = make_database()
    owner_id, idea_id, _version_id, _review_id = seed_complete_evidence(factory)
    with factory() as session:
        analysis = session.scalar(select(FeedbackAnalysisRun))
        analysis.status = "failed"
        analysis.error_message = "Provider unavailable."
        session.commit()
    settings, client = make_client(factory, tmp_path)
    headers = {
        "Authorization": (
            "Bearer " + create_access_token(owner_id, "owner", settings.jwt_secret, 30)
        )
    }
    path = f"/api/v1/ideas/{idea_id}/versions/1/decision-reports"
    with client:
        response = client.post(path, headers=headers)
        assert response.status_code == 201, response.text
        report = response.json()["report"]
        assert report["reviews"]["analysis_run_id"]
        assert report["reviews"]["quality_findings"]["items"] == []
        assert report["reviews"]["consensus"]["value"] is None
        assert report["reviews"]["uncertainty"] == "Feedback has not been analyzed."
    engine.dispose()


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires PostgreSQL")
def test_postgres_persists_approved_version_and_report_snapshot(tmp_path):
    settings = Settings(_env_file=None, prototype_source_storage_dir=tmp_path)
    engine = create_engine(str(Settings().database_url), poolclass=NullPool)
    with engine.connect() as connection:
        transaction = connection.begin()
        factory = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        owner_id, idea_id, source_version_id, feedback_id = seed_complete_evidence(factory)
        settings, client = make_client(factory, tmp_path)
        headers = {
            "Authorization": (
                "Bearer "
                + create_access_token(owner_id, "owner", settings.jwt_secret, 30)
            )
        }
        path = f"/api/v1/ideas/{idea_id}/versions/1/evolution"
        with client:
            proposal = client.post(path, headers=headers)
            assert proposal.status_code == 201, proposal.text
            approved = client.post(
                f"{path}/{proposal.json()['id']}/approve",
                headers=headers,
                json={"expected_source_version": 1, "selected_ranks": [1]},
            )
            assert approved.status_code == 200, approved.text
            report = client.post(
                f"/api/v1/ideas/{idea_id}/versions/2/decision-reports",
                headers=headers,
            )
            assert report.status_code == 201, report.text
            assert report.json()["source_feedback_ids"] == []
        with factory() as session:
            original = session.get(IdeaVersion, source_version_id)
            candidate = session.get(IdeaVersion, approved.json()["target_version_id"])
            stored_report = session.get(DecisionReport, report.json()["id"])
            stored_proposal = session.get(EvolutionProposal, proposal.json()["id"])
            assert original.features == ["Preparation roadmap"]
            assert candidate.source_version_id == original.id
            assert stored_proposal.source_feedback_ids == [feedback_id]
            assert stored_report.report["source_records"]["source_version"] == 2
        transaction.rollback()
    engine.dispose()
