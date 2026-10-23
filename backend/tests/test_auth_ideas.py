import os
from time import monotonic, sleep
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from kombu.exceptions import OperationalError as KombuOperationalError
from sqlalchemy import create_engine, delete, event, select, update
from sqlalchemy.exc import OperationalError as SqlAlchemyOperationalError
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.main import create_app
from app.models import (
    Base,
    FeedbackAnalysisOutbox,
    IdeaAsset,
    IdeaReview,
    IdeaStatusEvent,
    IdeaVersion,
    ReviewerAssignment,
    ReviewSession,
    User,
)
from app.security import create_access_token


def client(asset_dir=None):
    settings = Settings(_env_file=None)
    if asset_dir is not None:
        settings.idea_asset_storage_dir = asset_dir
    app = create_app(settings)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.feedback_dispatcher = lambda _outbox_id: None
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


def version_payload(title="Campus Compass V2", expected_version=1):
    return {
        **payload(title),
        "expected_version": expected_version,
        "change_summary": f"Update for {title}",
    }


def feedback_payload(session_id):
    return {
        "session_id": session_id,
        "rating": 5,
        "usability_score": 4,
        "usefulness_score": 5,
        "completeness_score": 4,
        "feasibility_score": 3,
        "would_use": True,
        "feedback_text": "The assigned idea version is clear and easy to assess.",
        "strengths": "The proposed direction is concise and understandable.",
        "concerns": "The opportunity data source is not explained yet.",
        "suggested_improvements": "Explain how each opportunity would be selected.",
        "usage_context": "I reviewed the assigned brief on a laptop.",
    }


def publish_version(test_client, idea_id, version, owner_headers):
    response = test_client.post(
        f"/api/v1/ideas/{idea_id}/versions/{version}/publish",
        headers=owner_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def prepare_review_assignment(test_client, prefix="review"):
    owner_id, owner_headers = account(test_client, f"{prefix}-owner@example.com")
    reviewer_id, reviewer_headers = account(
        test_client, f"{prefix}-reviewer@example.com", role="reviewer"
    )
    _, other_reviewer_headers = account(
        test_client, f"{prefix}-other-reviewer@example.com", role="reviewer"
    )
    _, admin_headers = account(test_client, f"{prefix}-admin@example.com", role="admin")
    idea = test_client.post("/api/v1/ideas", json=payload(), headers=owner_headers).json()
    publish_version(test_client, idea["id"], 1, owner_headers)
    assignment = test_client.post(
        "/api/v1/admin/assignments",
        json={
            "idea_id": idea["id"],
            "version": 1,
            "reviewer_email": f"{prefix}-reviewer@example.com",
        },
        headers=admin_headers,
    ).json()
    session = test_client.post(
        f"/api/v1/reviewer/assignments/{assignment['id']}/sessions",
        headers=reviewer_headers,
    ).json()
    return {
        "idea": idea,
        "assignment": assignment,
        "session": session,
        "owner_id": owner_id,
        "owner_headers": owner_headers,
        "reviewer_id": reviewer_id,
        "reviewer_headers": reviewer_headers,
        "other_reviewer_headers": other_reviewer_headers,
        "admin_headers": admin_headers,
    }


def account(test_client, email, role="owner"):
    response = test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "a-secure-password"},
    )
    assert response.status_code == 201
    result = response.json()
    if role != "owner":
        with test_client.app.state.session_factory() as session:
            user = session.get(User, result["user"]["id"])
            user.role = role
            session.commit()
    return result["user"]["id"], {"Authorization": f"Bearer {result['access_token']}"}


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
            json=version_payload("Campus Compass V2"),
            headers=headers,
        )
        assert version.status_code == 201
        assert version.json()["version"] == 2
        detail = first.get(f"/api/v1/ideas/{idea_id}", headers=headers)
        assert [item["version"] for item in detail.json()["versions"]] == [1, 2]
        assert detail.json()["versions"][0]["title"] == "Campus Compass"
        assert detail.json()["versions"][1]["source_version_id"] == created.json()["version_id"]
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


def test_public_registration_cannot_select_an_elevated_role():
    with client() as test_client:
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "password": "a-secure-password",
                "role": "admin",
            },
        )
        assert response.status_code == 422


def test_owner_cannot_access_another_owners_ideas_or_admin_operations():
    with client() as test_client:
        owner_id, owner_headers = account(test_client, "owner@example.com")
        _, other_headers = account(test_client, "other@example.com")
        created = test_client.post(
            "/api/v1/ideas", json=payload(), headers=owner_headers
        )
        assert created.status_code == 201
        idea_id = created.json()["id"]

        assert test_client.get("/api/v1/ideas", headers=other_headers).json()["items"] == []
        assert test_client.get(f"/api/v1/ideas/{idea_id}", headers=other_headers).status_code == 404
        assert (
            test_client.get(
                f"/api/v1/ideas/{idea_id}/versions/1", headers=other_headers
            ).status_code
            == 404
        )
        assert (
            test_client.post(
                f"/api/v1/ideas/{idea_id}/versions",
                json=version_payload("Unauthorized version"),
                headers=other_headers,
            ).status_code
            == 404
        )
        assert (
            test_client.get("/api/v1/admin/assignments", headers=owner_headers).status_code
            == 403
        )
        assert (
            test_client.get("/api/v1/reviewer/assignments", headers=owner_headers).status_code
            == 403
        )
        assert owner_id


def test_idea_pagination_search_filtering_and_immutable_version_conflicts():
    with client() as test_client:
        _, headers = account(test_client, "owner@example.com")
        first = test_client.post("/api/v1/ideas", json=payload(), headers=headers).json()
        second_payload = payload("Community Garden")
        second_payload["category"] = "Community"
        second = test_client.post("/api/v1/ideas", json=second_payload, headers=headers).json()
        third = test_client.post(
            "/api/v1/ideas", json=payload("Campus Compass Extension"), headers=headers
        ).json()

        page = test_client.get("/api/v1/ideas?limit=2&offset=1", headers=headers)
        assert page.status_code == 200
        assert page.json()["total"] == 3
        assert page.json()["limit"] == 2
        assert page.json()["offset"] == 1
        assert len(page.json()["items"]) == 2
        assert test_client.get(
            "/api/v1/ideas?category=community", headers=headers
        ).json()["items"][0]["id"] == second["id"]
        assert test_client.get(
            "/api/v1/ideas?q=extension", headers=headers
        ).json()["items"][0]["id"] == third["id"]
        assert test_client.get(
            "/api/v1/ideas?status=invalid", headers=headers
        ).status_code == 422

        version = test_client.post(
            f"/api/v1/ideas/{first['id']}/versions",
            json=version_payload("Campus Compass V2"),
            headers=headers,
        )
        assert version.status_code == 201
        assert version.json()["source_version_id"] == first["version_id"]
        assert version.json()["change_summary"] == "Update for Campus Compass V2"
        stale = test_client.post(
            f"/api/v1/ideas/{first['id']}/versions",
            json=version_payload("Stale edit"),
            headers=headers,
        )
        assert stale.status_code == 409
        detail = test_client.get(f"/api/v1/ideas/{first['id']}", headers=headers).json()
        assert [item["title"] for item in detail["versions"]] == [
            "Campus Compass",
            "Campus Compass V2",
        ]


def test_idea_lifecycle_transitions_and_assignment_guard():
    with client() as test_client:
        owner_id, owner_headers = account(test_client, "owner@example.com")
        _, reviewer_headers = account(test_client, "reviewer@example.com", role="reviewer")
        _, admin_headers = account(test_client, "admin@example.com", role="admin")
        created = test_client.post("/api/v1/ideas", json=payload(), headers=owner_headers).json()
        idea_id = created["id"]

        transition = test_client.patch(
            f"/api/v1/ideas/{idea_id}",
            json={"status": "Archived"},
            headers=owner_headers,
        )
        assert transition.status_code == 200
        assert transition.json()["status"] == "Archived"
        assert test_client.post(
            f"/api/v1/ideas/{idea_id}/versions",
            json=version_payload("Archived edit"),
            headers=owner_headers,
        ).status_code == 409
        assert test_client.patch(
            f"/api/v1/ideas/{idea_id}",
            json={"status": "Ready for review"},
            headers=owner_headers,
        ).status_code == 422
        restored = test_client.patch(
            f"/api/v1/ideas/{idea_id}",
            json={"status": "Draft"},
            headers=owner_headers,
        )
        assert restored.status_code == 200
        assert test_client.patch(
            f"/api/v1/ideas/{idea_id}",
            json={"status": "Archived"},
            headers=reviewer_headers,
        ).status_code == 403

        publish_version(test_client, idea_id, 1, owner_headers)
        assignment = test_client.post(
            "/api/v1/admin/assignments",
            json={
                "idea_id": idea_id,
                "version": 1,
                "reviewer_email": "reviewer@example.com",
            },
            headers=admin_headers,
        )
        assert assignment.status_code == 201
        blocked_archive = test_client.patch(
            f"/api/v1/ideas/{idea_id}",
            json={"status": "Archived"},
            headers=owner_headers,
        )
        assert blocked_archive.status_code == 409
        detail = test_client.get(f"/api/v1/ideas/{idea_id}", headers=owner_headers).json()
        history = detail["status_history"]
        assert [event["sequence"] for event in history] == [1, 2, 3, 4]
        assert [event["from_status"] for event in history] == [
            None,
            "Draft",
            "Archived",
            "Draft",
        ]
        assert [event["to_status"] for event in history] == [
            "Draft",
            "Archived",
            "Draft",
            "Review open",
        ]
        assert {event["changed_by_id"] for event in history} == {owner_id}


def test_private_asset_upload_validation_and_assignment_scoped_download(tmp_path):
    with client(tmp_path) as test_client:
        _, owner_headers = account(test_client, "owner@example.com")
        _, other_headers = account(test_client, "other@example.com")
        _, reviewer_headers = account(test_client, "reviewer@example.com", role="reviewer")
        _, other_reviewer_headers = account(
            test_client, "other-reviewer@example.com", role="reviewer"
        )
        _, admin_headers = account(test_client, "admin@example.com", role="admin")
        created = test_client.post("/api/v1/ideas", json=payload(), headers=owner_headers).json()
        idea_id = created["id"]
        body = b"%PDF-1.4\nVeridica private test asset\n"
        upload = test_client.post(
            f"/api/v1/ideas/{idea_id}/versions/1/assets?filename=brief.pdf",
            content=body,
            headers={**owner_headers, "Content-Type": "application/pdf"},
        )
        assert upload.status_code == 201
        asset = upload.json()["assets"][0]
        assert asset["filename"] == "brief.pdf"
        assert asset["size_bytes"] == len(body)
        with test_client.app.state.session_factory() as session:
            stored_asset = session.get(IdeaAsset, asset["id"])
            assert stored_asset is not None
            stored_path = tmp_path / stored_asset.storage_key
            assert stored_path.is_file()
            assert stored_path.stat().st_mode & 0o777 == 0o600

        invalid_type = test_client.post(
            f"/api/v1/ideas/{idea_id}/versions/1/assets?filename=brief.txt",
            content=body,
            headers={**owner_headers, "Content-Type": "text/plain"},
        )
        assert invalid_type.status_code == 415
        traversal = test_client.post(
            f"/api/v1/ideas/{idea_id}/versions/1/assets?filename=..%2Fsecret.pdf",
            content=body,
            headers={**owner_headers, "Content-Type": "application/pdf"},
        )
        assert traversal.status_code == 422
        oversized = test_client.post(
            f"/api/v1/ideas/{idea_id}/versions/1/assets?filename=large.pdf",
            content=b"x" * (10 * 1024 * 1024 + 1),
            headers={**owner_headers, "Content-Type": "application/pdf"},
        )
        assert oversized.status_code == 413

        path = f"/api/v1/ideas/{idea_id}/versions/1/assets/{asset['id']}"
        owner_download = test_client.get(path, headers=owner_headers)
        assert owner_download.status_code == 200
        assert owner_download.content == body
        assert owner_download.headers["cache-control"] == "private, no-store"
        assert test_client.get(path, headers=other_headers).status_code == 404
        assert test_client.get(path, headers=reviewer_headers).status_code == 404
        assert test_client.get(path, headers=admin_headers).status_code == 403

        publish_version(test_client, idea_id, 1, owner_headers)
        assignment = test_client.post(
            "/api/v1/admin/assignments",
            json={
                "idea_id": idea_id,
                "version": 1,
                "reviewer_email": "reviewer@example.com",
            },
            headers=admin_headers,
        )
        assert assignment.status_code == 201
        assigned = test_client.get(path, headers=reviewer_headers)
        assert assigned.status_code == 200
        assert assigned.content == body
        assert test_client.get(path, headers=other_reviewer_headers).status_code == 404
        reviewer_assignment = test_client.get(
            "/api/v1/reviewer/assignments", headers=reviewer_headers
        )
        assert reviewer_assignment.json()[0]["assets"][0]["id"] == asset["id"]


def test_admin_manages_version_assignments_and_reviewer_can_submit_one_review():
    with client() as test_client:
        owner_id, owner_headers = account(test_client, "owner@example.com")
        reviewer_id, reviewer_headers = account(
            test_client, "reviewer@example.com", role="reviewer"
        )
        _, other_reviewer_headers = account(
            test_client, "other-reviewer@example.com", role="reviewer"
        )
        admin_id, admin_headers = account(test_client, "admin@example.com", role="admin")

        created = test_client.post(
            "/api/v1/ideas", json=payload(), headers=owner_headers
        )
        idea_id = created.json()["id"]
        create_assignment = {
            "idea_id": idea_id,
            "version": 1,
            "reviewer_email": "REVIEWER@example.com",
        }

        assert test_client.get("/api/v1/ideas", headers=reviewer_headers).status_code == 403
        assert test_client.get(f"/api/v1/ideas/{idea_id}", headers=admin_headers).status_code == 403
        assert (
            test_client.post(
                "/api/v1/admin/assignments",
                json=create_assignment,
                headers=owner_headers,
            ).status_code
            == 403
        )
        assert (
            test_client.post(
                "/api/v1/admin/assignments",
                json=create_assignment,
                headers=admin_headers,
            ).status_code
            == 409
        )
        publish_version(test_client, idea_id, 1, owner_headers)

        assignment_response = test_client.post(
            "/api/v1/admin/assignments",
            json=create_assignment,
            headers=admin_headers,
        )
        assert assignment_response.status_code == 201
        assignment = assignment_response.json()
        assignment_id = assignment["id"]
        assert assignment["reviewer_email"] == "reviewer@example.com"
        assert assignment["active"] is True
        assert assignment["status"] == "assigned"
        assert assignment["review_submitted"] is False
        assert assignment["idea_title"] == "Campus Compass"
        assert assignment["version"] == 1
        assert (
            test_client.post(
                "/api/v1/admin/assignments",
                json=create_assignment,
                headers=admin_headers,
            ).status_code
            == 409
        )

        reviewer_assignments = test_client.get(
            "/api/v1/reviewer/assignments", headers=reviewer_headers
        )
        assert reviewer_assignments.status_code == 200
        assert [item["id"] for item in reviewer_assignments.json()] == [assignment_id]
        assert reviewer_assignments.json()[0]["status"] == "assigned"
        assert (
            test_client.get(
                f"/api/v1/reviewer/assignments/{assignment_id}",
                headers=other_reviewer_headers,
            ).status_code
            == 404
        )
        assert (
            test_client.get(
                f"/api/v1/ideas/{idea_id}/versions/1", headers=reviewer_headers
            ).status_code
            == 200
        )
        assert (
            test_client.get(
                f"/api/v1/ideas/{idea_id}/versions/1", headers=other_reviewer_headers
            ).status_code
            == 404
        )
        new_version = test_client.post(
            f"/api/v1/ideas/{idea_id}/versions",
            json=version_payload("Unassigned version"),
            headers=owner_headers,
        )
        assert new_version.status_code == 201
        assert (
            test_client.get(
                f"/api/v1/ideas/{idea_id}/versions/2", headers=reviewer_headers
            ).status_code
            == 404
        )
        assert (
            test_client.post(
                "/api/v1/ideas",
                json=payload("Reviewer idea"),
                headers=reviewer_headers,
            ).status_code
            == 403
        )

        started = test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/sessions",
            headers=reviewer_headers,
        )
        assert started.status_code == 201
        review_session_id = started.json()["id"]
        assert started.json()["idea_version_id"] == created.json()["version_id"]
        assert test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/sessions",
            headers=reviewer_headers,
        ).json()["id"] == review_session_id
        assert test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/sessions",
            headers=other_reviewer_headers,
        ).status_code == 404

        version_two_publish = publish_version(test_client, idea_id, 2, owner_headers)
        assert version_two_publish["version"] == 2
        second_assignment = test_client.post(
            "/api/v1/admin/assignments",
            json={**create_assignment, "version": 2},
            headers=admin_headers,
        )
        assert second_assignment.status_code == 201
        wrong_session = test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
            json=feedback_payload(
                test_client.post(
                    f"/api/v1/reviewer/assignments/{second_assignment.json()['id']}/sessions",
                    headers=reviewer_headers,
                ).json()["id"]
            ),
            headers={
                **reviewer_headers,
                "Idempotency-Key": "phase3-wrong-session-1",
            },
        )
        assert wrong_session.status_code == 404

        review_payload = feedback_payload(review_session_id)
        idem_headers = {
            **reviewer_headers,
            "Idempotency-Key": "phase3-idempotency-0001",
        }
        missing_fields = test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
            json={"session_id": review_session_id, "rating": 5},
            headers=idem_headers,
        )
        assert missing_fields.status_code == 422
        submitted = test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
            json=review_payload,
            headers=idem_headers,
        )
        assert submitted.status_code == 201, submitted.text
        assert submitted.json()["rating"] == 5
        assert submitted.json()["assignment_id"] == assignment_id
        assert submitted.json()["idea_version_id"] == started.json()["idea_version_id"]
        assert submitted.json()["reviewer_id"] == reviewer_id
        assert submitted.json()["review_session_id"] == review_session_id
        retried = test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
            json=review_payload,
            headers=idem_headers,
        )
        assert retried.status_code == 200
        assert retried.json()["id"] == submitted.json()["id"]
        conflict = test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
            json={**review_payload, "rating": 4},
            headers=idem_headers,
        )
        assert conflict.status_code == 409
        distinct_key = test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
            json=review_payload,
            headers={**reviewer_headers, "Idempotency-Key": "phase3-distinct-key-0001"},
        )
        assert distinct_key.status_code == 409
        assert (
            test_client.post(
                f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
                json=review_payload,
                headers={**other_reviewer_headers, "Idempotency-Key": "other-reviewer-key-001"},
            ).status_code
            == 404
        )
        assert (
            test_client.post(
                f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
                json=review_payload,
                headers={**admin_headers, "Idempotency-Key": "admin-submission-key-0001"},
            ).status_code
            == 403
        )
        persisted = test_client.get(
            f"/api/v1/reviewer/assignments/{assignment_id}", headers=reviewer_headers
        ).json()
        assert persisted["status"] == "submitted"
        assert persisted["feedback"]["id"] == submitted.json()["id"]
        assert persisted["feedback"]["feedback_text"] == review_payload["feedback_text"]
        listed_admin_assignments = test_client.get(
            "/api/v1/admin/assignments", headers=admin_headers
        )
        assert listed_admin_assignments.status_code == 200
        completed_admin_assignment = next(
            entry for entry in listed_admin_assignments.json() if entry["id"] == assignment_id
        )
        assert completed_admin_assignment["status"] == "submitted"
        assert completed_admin_assignment["review_submitted"] is True

        revoked = test_client.delete(
            f"/api/v1/admin/assignments/{assignment_id}", headers=admin_headers
        )
        assert revoked.status_code == 200
        assert revoked.json()["active"] is False
        assert (
            test_client.get(
                f"/api/v1/reviewer/assignments/{assignment_id}",
                headers=reviewer_headers,
            ).status_code
            == 404
        )
        assert (
            test_client.post(
                f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
                json=review_payload,
                headers={
                    **reviewer_headers,
                    "Idempotency-Key": "phase3-revoked-assignment-0001",
                },
            ).status_code
            == 404
        )
        assert owner_id and reviewer_id and admin_id


def test_feedback_is_committed_before_queue_and_queue_failure_can_be_retried():
    with client() as test_client:
        workflow = prepare_review_assignment(test_client)
        outbox_ids = []
        should_fail = True

        def dispatch(outbox_id):
            nonlocal should_fail
            with test_client.app.state.session_factory() as session:
                outbox = session.get(FeedbackAnalysisOutbox, outbox_id)
                assert outbox is not None
                assert session.get(IdeaReview, outbox.feedback_id) is not None
                outbox_ids.append(outbox_id)
            if should_fail:
                should_fail = False
                raise KombuOperationalError("Redis is unavailable")

        test_client.app.state.feedback_dispatcher = dispatch
        feedback = feedback_payload(workflow["session"]["id"])
        headers = {
            **workflow["reviewer_headers"],
            "Idempotency-Key": "queue-retry-idempotency-key-0001",
        }
        first = test_client.post(
            f"/api/v1/reviewer/assignments/{workflow['assignment']['id']}/reviews",
            json=feedback,
            headers=headers,
        )
        assert first.status_code == 201, first.text
        assert first.json()["analysis_status"] == "pending"
        assert "queue is unavailable" in first.json()["analysis_error"]
        with test_client.app.state.session_factory() as session:
            review = session.scalar(select(IdeaReview))
            assert review is not None
            outbox = session.scalar(
                select(FeedbackAnalysisOutbox).where(
                    FeedbackAnalysisOutbox.feedback_id == review.id
                )
            )
            assert outbox is not None
            assert outbox.status == "pending"
            assert outbox.attempt_count == 1
            assert outbox.last_error

        retry = test_client.post(
            f"/api/v1/reviewer/assignments/{workflow['assignment']['id']}/reviews",
            json=feedback,
            headers=headers,
        )
        assert retry.status_code == 200
        assert retry.json()["id"] == first.json()["id"]
        assert retry.json()["analysis_status"] == "queued"
        assert len(outbox_ids) == 2
        with test_client.app.state.session_factory() as session:
            assert len(session.scalars(select(IdeaReview)).all()) == 1
            outbox = session.scalar(select(FeedbackAnalysisOutbox))
            assert outbox is not None
            assert outbox.status == "queued"
            assert outbox.attempt_count == 2


def test_feedback_database_failure_does_not_dispatch_or_complete_session():
    with client() as test_client:
        workflow = prepare_review_assignment(test_client, "db-failure")
        dispatched = []
        test_client.app.state.feedback_dispatcher = dispatched.append
        engine = test_client.app.state.session_factory.kw["bind"]

        def fail_feedback_insert(_connection, _cursor, statement, _parameters, _context, _many):
            if statement.lstrip().upper().startswith("INSERT INTO IDEA_REVIEWS"):
                raise SqlAlchemyOperationalError(
                    statement, _parameters, RuntimeError("simulated database failure")
                )

        event.listen(engine, "before_cursor_execute", fail_feedback_insert)
        try:
            with pytest.raises(SqlAlchemyOperationalError):
                test_client.post(
                    f"/api/v1/reviewer/assignments/{workflow['assignment']['id']}/reviews",
                    json=feedback_payload(workflow["session"]["id"]),
                    headers={
                        **workflow["reviewer_headers"],
                        "Idempotency-Key": "database-failure-idempotency-01",
                    },
                )
        finally:
            event.remove(engine, "before_cursor_execute", fail_feedback_insert)

        assert dispatched == []
        with test_client.app.state.session_factory() as session:
            assert session.scalar(select(IdeaReview)) is None
            assert session.scalar(select(FeedbackAnalysisOutbox)) is None
            assignment = session.get(ReviewerAssignment, workflow["assignment"]["id"])
            assert assignment is not None
            assert assignment.status == "in_progress"


def test_feedback_requires_idempotency_key_valid_fields_and_bounded_body():
    with client() as test_client:
        workflow = prepare_review_assignment(test_client, "validation")
        path = f"/api/v1/reviewer/assignments/{workflow['assignment']['id']}/reviews"
        feedback = feedback_payload(workflow["session"]["id"])
        assert test_client.post(
            path, json=feedback, headers=workflow["reviewer_headers"]
        ).status_code == 422
        assert test_client.post(
            path,
            json={**feedback, "strengths": "   "},
            headers={
                **workflow["reviewer_headers"],
                "Idempotency-Key": "validation-idempotency-key-0001",
            },
        ).status_code == 422
        oversized_body = (
            b'{"session_id":"' + workflow["session"]["id"].encode()
            + b'","rating":5,"unused":"' + b"x" * (33 * 1024) + b'"}'
        )
        oversized = test_client.post(
            path,
            content=oversized_body,
            headers={
                **workflow["reviewer_headers"],
                "Idempotency-Key": "oversized-idempotency-key-0001",
                "Content-Type": "application/json",
            },
        )
        assert oversized.status_code == 413


def test_invalid_expired_and_forged_role_tokens_are_rejected():
    with client() as test_client:
        owner_id, _ = account(test_client, "owner@example.com")
        reviewer_id, _ = account(test_client, "reviewer@example.com", role="reviewer")
        settings = test_client.app.state.settings
        expired = create_access_token(owner_id, "owner", settings.jwt_secret, -1)
        forged_admin_role = create_access_token(
            reviewer_id, "admin", settings.jwt_secret, settings.access_token_minutes
        )

        assert test_client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid"}
        ).status_code == 401
        assert test_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}
        ).status_code == 401
        assert test_client.get(
            "/api/v1/admin/assignments",
            headers={"Authorization": f"Bearer {forged_admin_role}"},
        ).status_code == 403


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="Requires the configured PostgreSQL database"
)
def test_postgres_owner_reviewer_admin_authorization_flow():
    test_client = TestClient(create_app(Settings()))
    session_factory = test_client.app.state.session_factory
    user_ids: list[str] = []
    assignment_ids: list[str] = []
    idea_owner_id: str | None = None
    unique = uuid4().hex

    def register(email: str, role: str = "owner"):
        response = test_client.post(
            "/api/v1/auth/register",
            json={"email": f"{email}-{unique}@example.invalid", "password": "a-secure-password"},
        )
        assert response.status_code == 201, response.text
        result = response.json()
        user_ids.append(result["user"]["id"])
        if role != "owner":
            with session_factory() as session:
                user = session.get(User, result["user"]["id"])
                assert user is not None
                user.role = role
                session.commit()
        return result["user"]["id"], {"Authorization": f"Bearer {result['access_token']}"}

    try:
        idea_owner_id, owner_headers = register("owner")
        reviewer_id, reviewer_headers = register("reviewer", "reviewer")
        _, other_reviewer_headers = register("other-reviewer", "reviewer")
        _, admin_headers = register("admin", "admin")
        created = test_client.post("/api/v1/ideas", json=payload(), headers=owner_headers)
        assert created.status_code == 201, created.text
        created_idea = created.json()
        idea_id = created_idea["id"]
        version = test_client.post(
            f"/api/v1/ideas/{idea_id}/versions",
            json=version_payload("Persisted PostgreSQL version"),
            headers=owner_headers,
        )
        assert version.status_code == 201, version.text
        assert version.json()["features"] == ["Matching", "Roadmap"]
        with pytest.raises(ProgrammingError):
            with session_factory() as session:
                session.execute(
                    update(IdeaVersion).where(
                        IdeaVersion.id == created_idea["version_id"]
                    ).values(title="Attempted overwrite")
                )
                session.commit()
        with session_factory() as session:
            original = session.get(IdeaVersion, created_idea["version_id"])
            assert original is not None
            assert original.title == "Campus Compass"
            status_event = session.scalar(
                select(IdeaStatusEvent).where(IdeaStatusEvent.idea_id == idea_id)
            )
            assert status_event is not None
            status_event_id = status_event.id
        with pytest.raises(ProgrammingError):
            with session_factory() as session:
                session.execute(
                    update(IdeaStatusEvent)
                    .where(IdeaStatusEvent.id == status_event_id)
                    .values(to_status="Archived")
                )
                session.commit()

        other_owner_headers = register("other-owner")[1]
        assert (
            test_client.get(f"/api/v1/ideas/{idea_id}", headers=other_owner_headers).status_code
            == 404
        )
        publish_version(test_client, idea_id, 1, owner_headers)
        assignment = test_client.post(
            "/api/v1/admin/assignments",
            json={
                "idea_id": idea_id,
                "version": 1,
                "reviewer_email": f"reviewer-{unique}@example.invalid",
            },
            headers=admin_headers,
        )
        assert assignment.status_code == 201, assignment.text
        assignment_id = assignment.json()["id"]
        assignment_ids.append(assignment_id)
        assert (
            test_client.get(
                "/api/v1/reviewer/assignments", headers=reviewer_headers
            ).status_code
            == 200
        )
        assert (
            test_client.get(
                f"/api/v1/reviewer/assignments/{assignment_id}",
                headers=other_reviewer_headers,
            ).status_code
            == 404
        )
        started = test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/sessions",
            headers=reviewer_headers,
        )
        assert started.status_code == 201, started.text
        review_payload_data = feedback_payload(started.json()["id"])
        review = test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
            json=review_payload_data,
            headers={
                **reviewer_headers,
                "Idempotency-Key": "postgres-feedback-idempotency-01",
            },
        )
        assert review.status_code == 201, review.text
        assert review.json()["idea_id"] == idea_id
        assert review.json()["idea_version_id"] == created_idea["version_id"]
        assert review.json()["reviewer_id"] == reviewer_id
        assert review.json()["analysis_status"] in {"queued", "received"}
        deadline = monotonic() + 15
        outbox_status = "pending"
        while monotonic() < deadline:
            with session_factory() as session:
                outbox = session.scalar(
                    select(FeedbackAnalysisOutbox).where(
                        FeedbackAnalysisOutbox.feedback_id == review.json()["id"]
                    )
                )
                assert outbox is not None
                outbox_status = outbox.status
            if outbox_status == "received":
                break
            sleep(0.1)
        assert outbox_status == "received"
        replay = test_client.post(
            f"/api/v1/reviewer/assignments/{assignment_id}/reviews",
            json=review_payload_data,
            headers={
                **reviewer_headers,
                "Idempotency-Key": "postgres-feedback-idempotency-01",
            },
        )
        assert replay.status_code == 200
        assert replay.json()["id"] == review.json()["id"]
    finally:
        with session_factory() as session:
            if assignment_ids:
                feedback_ids = select(IdeaReview.id).where(
                    IdeaReview.assignment_id.in_(assignment_ids)
                )
                session.execute(
                    delete(FeedbackAnalysisOutbox).where(
                        FeedbackAnalysisOutbox.feedback_id.in_(feedback_ids)
                    )
                )
                session.execute(
                    delete(IdeaReview).where(IdeaReview.assignment_id.in_(assignment_ids))
                )
                session.execute(
                    delete(ReviewSession).where(
                        ReviewSession.assignment_id.in_(assignment_ids)
                    )
                )
                session.execute(
                    delete(ReviewerAssignment).where(ReviewerAssignment.id.in_(assignment_ids))
                )
            if user_ids:
                session.execute(
                    delete(User).where(
                        User.id.in_(user_ids),
                        User.id != idea_owner_id,
                    )
                )
            session.commit()
        test_client.close()
