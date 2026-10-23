import json
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.main import create_app
from app.models import IdeaReview, IdeaVersion, User
from app.services.feedback_analysis import execute_feedback_analysis
from app.services.requirements import execute_requirement_analysis


class DeterministicChatProvider:
    model_id = "phase8-deterministic-test-double"

    def __init__(self, outputs: list[dict]):
        self.outputs = iter(outputs)

    def chat(self, _prompt: str, _system: str) -> str:
        return json.dumps(next(self.outputs))


class DeterministicEmbeddingProvider:
    def embed(self, _text: str) -> list[float]:
        return [1.0] + [0.0] * 767


def _requirement_result() -> dict:
    return {
        "problem": [
            {
                "text": "Students need a clearer placement preparation process.",
                "basis": "explicit",
                "source_fields": ["problem"],
            }
        ],
        "target_users": [
            {
                "text": "College students.",
                "basis": "explicit",
                "source_fields": ["audience"],
            }
        ],
        "user_journeys": [
            {
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
            }
        ],
        "core_features": [
            {
                "text": "Opportunity matching.",
                "basis": "explicit",
                "source_fields": ["features"],
            }
        ],
        "constraints": [],
        "assumptions": ["Students can provide a placement profile."],
        "acceptance_criteria": [
            {
                "text": "The workspace displays the provided preparation roadmap.",
                "basis": "assumption",
                "source_fields": ["features"],
            }
        ],
        "open_questions": ["Which placement data source is intended?"],
    }


def _quality_item(feedback_id: str) -> dict:
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
            "constructiveness": "Contains an actionable observation.",
            "originality": "Compared only with this evidence set.",
            "internal_consistency": "Statements align with the ratings.",
            "spam_risk": "No obvious repetitive pattern.",
            "authenticity_indicator": "An uncertain signal, not verification.",
        },
    }


def _register_and_login(client: TestClient, factory, email: str, role: str) -> dict:
    password = "a-secure-password"
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert registered.status_code == 201, registered.text
    user_id = registered.json()["user"]["id"]
    if role != "owner":
        # Reviewer/admin provisioning is currently an operator action, not public registration.
        with factory() as session:
            session.get(User, user_id).role = role
            session.commit()
    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert logged_in.status_code == 200, logged_in.text
    return {
        "id": user_id,
        "email": email,
        "headers": {"Authorization": f"Bearer {logged_in.json()['access_token']}"},
    }


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="Requires configured PostgreSQL and pgvector",
)
def test_single_idea_persisted_workflow_and_access_boundaries(tmp_path):
    settings = Settings()
    settings.prototype_source_storage_dir = tmp_path
    engine = create_engine(str(settings.database_url), poolclass=NullPool)

    with engine.connect() as connection:
        transaction = connection.begin()
        factory = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        app = create_app(settings)
        app.state.session_factory = factory
        app.state.requirement_dispatcher = lambda *_args: None
        app.state.feedback_dispatcher = lambda *_args: None
        app.state.feedback_analysis_dispatcher = lambda *_args: None

        with TestClient(app) as client:
            suffix = uuid4().hex
            owner = _register_and_login(
                client, factory, f"phase8-owner-{suffix}@example.invalid", "owner"
            )
            reviewer = _register_and_login(
                client, factory, f"phase8-reviewer-{suffix}@example.invalid", "reviewer"
            )
            admin = _register_and_login(
                client, factory, f"phase8-admin-{suffix}@example.invalid", "admin"
            )
            other_owner = _register_and_login(
                client, factory, f"phase8-outsider-{suffix}@example.invalid", "owner"
            )
            other_reviewer = _register_and_login(
                client, factory, f"phase8-other-reviewer-{suffix}@example.invalid", "reviewer"
            )

            created = client.post(
                "/api/v1/ideas",
                headers=owner["headers"],
                json={
                    "title": "Campus Compass",
                    "category": "Education",
                    "problem": "Students need a better way to prepare for placements.",
                    "solution": "A guided workspace for preparation and opportunity discovery.",
                    "audience": "College students",
                    "features": ["Preparation roadmap", "Opportunity matching"],
                    "constraints": "No live integrations yet.",
                },
            )
            assert created.status_code == 201, created.text
            idea = created.json()
            idea_id = idea["id"]
            assert idea["version"] == 1
            assert client.get(
                f"/api/v1/ideas/{idea_id}", headers=other_owner["headers"]
            ).status_code == 404
            assert client.get(
                f"/api/v1/ideas/{idea_id}", headers=admin["headers"]
            ).status_code == 403

            requirement_path = f"/api/v1/ideas/{idea_id}/versions/1/requirements"
            requirement_start = client.post(requirement_path, headers=owner["headers"])
            assert requirement_start.status_code == 202, requirement_start.text
            requirement_run = requirement_start.json()
            requirement_outcome = execute_requirement_analysis(
                factory,
                settings,
                requirement_run["id"],
                provider_factory=lambda _settings: DeterministicChatProvider(
                    [_requirement_result()]
                ),
            )
            assert requirement_outcome["status"] == "completed"
            requirement = client.get(requirement_path, headers=owner["headers"]).json()
            assert requirement["validation_status"] == "valid"
            assert requirement["source_version"] == 1

            prototype_path = f"/api/v1/ideas/{idea_id}/versions/1/prototypes"
            prototype_response = client.post(
                prototype_path,
                headers=owner["headers"],
                json={"requirement_analysis_id": requirement["id"]},
            )
            assert prototype_response.status_code == 201, prototype_response.text
            prototype = prototype_response.json()
            assert prototype["status"] == "source_generated"
            assert prototype["build_status"] == "blocked_isolation"
            assert prototype["publish_status"] == "unpublished"
            assert prototype["preview_url"] is None
            assert client.get(
                f"{prototype_path}/{prototype['id']}/source",
                headers=other_owner["headers"],
            ).status_code == 404
            assert client.get(
                f"{prototype_path}/{prototype['id']}/source",
                headers=reviewer["headers"],
            ).status_code == 403

            published = client.post(
                f"/api/v1/ideas/{idea_id}/versions/1/publish",
                headers=owner["headers"],
            )
            assert published.status_code == 201, published.text
            assigned = client.post(
                "/api/v1/admin/assignments",
                headers=admin["headers"],
                json={
                    "idea_id": idea_id,
                    "version": 1,
                    "reviewer_email": reviewer["email"],
                },
            )
            assert assigned.status_code == 201, assigned.text
            assignment_id = assigned.json()["id"]
            assert client.get(
                f"/api/v1/reviewer/assignments/{assignment_id}",
                headers=other_reviewer["headers"],
            ).status_code == 404
            assert client.get(
                f"/api/v1/ideas/{idea_id}/versions/1",
                headers=other_reviewer["headers"],
            ).status_code == 404
            assignment = client.get(
                f"/api/v1/reviewer/assignments/{assignment_id}",
                headers=reviewer["headers"],
            ).json()
            assert assignment["version"] == 1

            review_session = client.post(
                f"/api/v1/reviewer/assignments/{assignment_id}/sessions",
                headers=reviewer["headers"],
            )
            assert review_session.status_code == 201, review_session.text
            feedback_payload = {
                "session_id": review_session.json()["id"],
                "rating": 4,
                "usability_score": 4,
                "usefulness_score": 4,
                "completeness_score": 3,
                "feasibility_score": 4,
                "would_use": True,
                "feedback_text": "The preparation roadmap needs clearer staged steps.",
                "strengths": "The guided placement preparation is easy to understand.",
                "concerns": "The roadmap does not explain how opportunities are selected.",
                "suggested_improvements": "Add a staged preparation roadmap.",
                "usage_context": "Reviewed the assigned version using a desktop browser.",
            }
            review_headers = {
                **reviewer["headers"],
                "Idempotency-Key": f"phase8-{suffix}-feedback",
            }
            submitted = client.post(
                f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
                headers=review_headers,
                json=feedback_payload,
            )
            assert submitted.status_code == 201, submitted.text
            feedback_id = submitted.json()["id"]
            replay = client.post(
                f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
                headers=review_headers,
                json=feedback_payload,
            )
            assert replay.status_code == 200
            assert replay.json()["id"] == feedback_id
            assert client.get(
                f"/api/v1/ideas/{idea_id}/versions/1/feedback",
                headers=owner["headers"],
            ).json()[0]["id"] == feedback_id
            assert client.get(
                f"/api/v1/ideas/{idea_id}/versions/1/feedback",
                headers=other_owner["headers"],
            ).status_code == 404
            with factory() as session:
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(IdeaReview)
                        .where(IdeaReview.id == feedback_id)
                    )
                    == 1
                )

            analysis_path = f"/api/v1/ideas/{idea_id}/versions/1/feedback-analysis"
            analysis_start = client.post(analysis_path, headers=owner["headers"])
            assert analysis_start.status_code == 202, analysis_start.text
            analysis_run = analysis_start.json()
            feedback_analysis = execute_feedback_analysis(
                factory,
                settings,
                analysis_run["id"],
                provider_factory=lambda _settings: DeterministicChatProvider(
                    [
                        {"items": [_quality_item(feedback_id)]},
                        {
                            "themes": [
                                {
                                    "label": "Staged preparation roadmap",
                                    "kind": "feature_request",
                                    "summary": "The review requests clearer preparation steps.",
                                    "feedback_ids": [feedback_id],
                                }
                            ],
                            "contradictions": [],
                        },
                        {
                            "proposals": [
                                {
                                    "title": "Staged preparation roadmap",
                                    "rationale": "The review requests clearer preparation steps.",
                                    "feedback_ids": [feedback_id],
                                    "theme_labels": ["Staged preparation roadmap"],
                                    "impact": "medium",
                                    "impact_rationale": "It addresses the cited concern.",
                                    "feasibility": "unknown",
                                    "feasibility_rationale": "No implementation estimate exists.",
                                    "assumptions": [],
                                    "missing_inputs": ["Implementation effort"],
                                }
                            ]
                        },
                    ]
                ),
                embedding_provider_factory=lambda _settings: DeterministicEmbeddingProvider(),
            )
            assert feedback_analysis["status"] == "completed"
            analysis = client.get(analysis_path, headers=owner["headers"]).json()
            assert analysis["validation_status"] == "valid"
            assert analysis["result"]["source_feedback_ids"] == [feedback_id]
            assert analysis["result"]["consensus"]["sample_size"] == 1
            assert analysis["result"]["priorities"][0]["feedback_ids"] == [feedback_id]

            proposal_path = f"/api/v1/ideas/{idea_id}/versions/1/evolution"
            proposal_response = client.post(proposal_path, headers=owner["headers"])
            assert proposal_response.status_code == 201, proposal_response.text
            proposal = proposal_response.json()
            assert proposal["source_feedback_ids"] == [feedback_id]
            approved = client.post(
                f"{proposal_path}/{proposal['id']}/approve",
                headers=owner["headers"],
                json={"expected_source_version": 1, "selected_ranks": [1]},
            )
            assert approved.status_code == 200, approved.text
            assert approved.json()["status"] == "approved"
            assert approved.json()["validation_results"]["working_prototype_validated"] is False

            report_path = f"/api/v1/ideas/{idea_id}/versions/1/decision-reports"
            report_response = client.post(report_path, headers=owner["headers"])
            assert report_response.status_code == 201, report_response.text
            report = report_response.json()
            assert report["report"]["reviews"]["source_feedback_ids"] == [feedback_id]
            assert report["report"]["reviews"]["analyzed_feedback_ids"] == [feedback_id]
            assert report["report"]["evolution"]["status"] == "approved"
            assert report["report"]["prototype"]["build_status"] == "blocked_isolation"
            assert client.get(report_path, headers=other_owner["headers"]).status_code == 404
            assert client.get(report_path, headers=reviewer["headers"]).status_code == 403
            assert client.get(
                f"/api/v1/ideas/{idea_id}/versions/2",
                headers=reviewer["headers"],
            ).status_code == 404

            with factory() as session:
                original = session.scalar(
                    select(IdeaVersion).where(
                        IdeaVersion.idea_id == idea_id,
                        IdeaVersion.version == 1,
                    )
                )
                candidate = session.scalar(
                    select(IdeaVersion).where(
                        IdeaVersion.idea_id == idea_id,
                        IdeaVersion.version == 2,
                    )
                )
                assert original is not None and candidate is not None
                assert original.title == "Campus Compass"
                assert original.features == ["Preparation roadmap", "Opportunity matching"]
                assert candidate.source_version_id == original.id

        reloaded_app = create_app(settings)
        reloaded_app.state.session_factory = factory
        with TestClient(reloaded_app) as reloaded:
            persisted_idea = reloaded.get(
                f"/api/v1/ideas/{idea_id}", headers=owner["headers"]
            )
            assert persisted_idea.status_code == 200
            assert [item["version"] for item in persisted_idea.json()["versions"]] == [1, 2]
            assert reloaded.get(
                f"/api/v1/ideas/{idea_id}/versions/1/feedback",
                headers=owner["headers"],
            ).json()[0]["id"] == feedback_id
            assert reloaded.get(report_path, headers=owner["headers"]).json()["id"] == report["id"]

        transaction.rollback()
    engine.dispose()
