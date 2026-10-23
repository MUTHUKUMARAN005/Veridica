import json
import os
import subprocess
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents import ai_builder
from app.agents.ai_builder import (
    PrototypeValidationError,
    generate_education_placement_prototype,
    read_source_files,
    validate_generated_files,
    write_source_files,
)
from app.config import Settings
from app.main import create_app
from app.models import (
    Base,
    PrototypeBuild,
    RequirementAnalysisRun,
    ReviewerAssignment,
    ReviewCycle,
    User,
)
from app.schemas import PrototypePreviewSpec, RequirementSpecification


def valid_requirements() -> RequirementSpecification:
    return RequirementSpecification.model_validate(
        {
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
            "user_journeys": [],
            "core_features": [
                {
                    "text": "Preparation roadmap.",
                    "basis": "explicit",
                    "source_fields": ["features"],
                },
                {
                    "text": "Possible opportunity matching.",
                    "basis": "assumption",
                    "source_fields": ["features"],
                },
            ],
            "constraints": [],
            "assumptions": [],
            "acceptance_criteria": [],
            "open_questions": ["Which placement data source is intended?"],
        }
    )


def generate():
    return generate_education_placement_prototype(
        category="Education",
        title="Campus Compass",
        problem="Students need a clearer placement preparation process.",
        solution="A guided workspace for career preparation.",
        audience="College students",
        features=["Preparation roadmap"],
        source_version=1,
        requirements=valid_requirements(),
    )


def test_builder_generates_only_allowlisted_static_source():
    generated = generate()
    metadata = validate_generated_files(generated.files)
    package = json.loads(generated.files["package.json"])

    assert generated.plan.template_id == "education-placement-preparation"
    assert generated.plan.category == "education-placement"
    assert {item.path for item in metadata} == set(generated.manifest.files)
    assert package["scripts"] == generated.manifest.scripts
    assert {**package["dependencies"], **package["devDependencies"]} == (
        generated.manifest.dependencies
    )
    assert generated.manifest.source_only is True
    assert generated.manifest.build_boundary == "unavailable"
    assert "Possible opportunity matching." not in generated.files["src/prototype.json"]
    assert "\\u003c" in generated.files["src/prototype.json"] or "<script>" not in (
        generated.files["src/prototype.json"]
    )


def test_builder_rejects_unsupported_category():
    with pytest.raises(ValueError, match="only supported builder category"):
        generate_education_placement_prototype(
            category="Sustainability",
            title="Campus Compass",
            problem="Students need placement preparation.",
            solution="A guided workspace.",
            audience="Students",
            features=["Roadmap"],
            source_version=1,
            requirements=valid_requirements(),
        )


def test_builder_rejects_traversal_paths_and_unapproved_dependencies():
    generated = generate()
    with pytest.raises(PrototypeValidationError, match="path is not allowed"):
        validate_generated_files({**generated.files, "../outside.txt": "no"})

    package = json.loads(generated.files["package.json"])
    package["dependencies"]["unapproved-package"] = "1.0.0"
    invalid = {**generated.files, "package.json": json.dumps(package)}
    with pytest.raises(PrototypeValidationError, match="unsupported dependencies"):
        validate_generated_files(invalid)


def test_builder_rejects_unsafe_source_and_missing_required_files():
    generated = generate()
    unsafe = {**generated.files, "src/Prototype.tsx": "eval('unexpected')"}
    with pytest.raises(PrototypeValidationError, match="file set is invalid"):
        validate_generated_files(
            {filename: content for filename, content in generated.files.items()
             if filename != "src/styles.css"}
        )
    with pytest.raises(PrototypeValidationError, match="disallowed capability"):
        validate_generated_files(unsafe)
    unapproved_import = {
        **generated.files,
        "src/Prototype.tsx": "import injected from 'unapproved-package'",
    }
    with pytest.raises(PrototypeValidationError, match="unapproved import"):
        validate_generated_files(unapproved_import)


def test_preview_spec_rejects_unknown_components_and_properties():
    base = {
        "schema_version": "1",
        "source_version": 1,
        "requirement_analysis_id": str(uuid4()),
        "title": "Campus Compass",
        "screens": [{
            "key": "overview",
            "title": "Overview",
            "components": [{"type": "text", "text": "Validated text."}],
        }],
    }
    assert PrototypePreviewSpec.model_validate(base).screens[0].components[0].type == "text"
    with pytest.raises(ValueError):
        PrototypePreviewSpec.model_validate({
            **base,
            "screens": [{
                "key": "overview",
                "title": "Overview",
                "components": [{"type": "script", "source": "alert(1)"}],
            }],
        })
    with pytest.raises(ValueError):
        PrototypePreviewSpec.model_validate({
            **base,
            "screens": [{
                "key": "overview",
                "title": "Overview",
                "components": [{
                    "type": "text",
                    "text": "Visible label",
                    "onClick": "alert(1)",
                }],
            }],
        })


def test_preview_spec_keeps_injection_like_content_as_plain_text():
    payload = {
        "schema_version": "1",
        "source_version": 1,
        "requirement_analysis_id": str(uuid4()),
        "title": "Example",
        "screens": [{
            "key": "overview",
            "title": "Overview",
            "components": [{
                "type": "text",
                "text": "<img src=x onerror=alert(1)>",
            }],
        }],
    }
    spec = PrototypePreviewSpec.model_validate(payload)
    assert spec.screens[0].components[0].text == "<img src=x onerror=alert(1)>"


def test_generated_source_integrity_reports_missing_artifact(tmp_path):
    generated = generate()
    metadata = validate_generated_files(generated.files)
    write_source_files(str(tmp_path), "prototype-key", generated.files, metadata)

    assert read_source_files(
        str(tmp_path),
        "prototype-key",
        [item.as_dict() for item in metadata],
    ) == generated.files
    (tmp_path / "prototype-key" / "src" / "Prototype.tsx").unlink()
    with pytest.raises(FileNotFoundError, match="missing"):
        read_source_files(
            str(tmp_path),
            "prototype-key",
            [item.as_dict() for item in metadata],
        )


def test_builder_never_executes_generated_source_even_when_runner_would_timeout(
    tmp_path,
    monkeypatch,
):
    def forbidden_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("generated-prototype", timeout=1)

    monkeypatch.setattr(subprocess, "run", forbidden_run)
    generated = generate()
    metadata = validate_generated_files(generated.files)
    write_source_files(str(tmp_path), "non-executed", generated.files, metadata)

    assert generated.manifest.build_boundary == "unavailable"
    assert generated.manifest.source_only


def make_client(storage_dir):
    settings = Settings(_env_file=None, prototype_source_storage_dir=storage_dir)
    application = create_app(settings)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    application.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return TestClient(application), application.state.session_factory


def register(client: TestClient, email: str, role: str = "owner"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "a-secure-password"},
    )
    assert response.status_code == 201, response.text
    with client.app.state.session_factory() as session:
        user = session.get(User, response.json()["user"]["id"])
        assert user is not None
        user.role = role
        session.commit()
    return {
        "id": response.json()["user"]["id"],
        "headers": {
            "Authorization": " ".join(("Bearer", response.json()["access_token"]))
        },
    }


def seed_valid_requirements(factory, idea: dict, owner_id: str) -> str:
    run_id = str(uuid4())
    with factory() as session:
        session.add(
            RequirementAnalysisRun(
                id=run_id,
                idea_id=idea["id"],
                idea_version_id=idea["version_id"],
                source_version=idea["version"],
                requested_by_id=owner_id,
                workflow_run_id=str(uuid4()),
                provider="ollama",
                model_version="deterministic-test-double",
                prompt_version="requirement-spec-v1",
                status="completed",
                validation_status="valid",
                result=valid_requirements().model_dump(mode="json"),
            )
        )
        session.commit()
    return run_id


def create_idea(client: TestClient, owner_headers: dict, category: str = "Education"):
    response = client.post(
        "/api/v1/ideas",
        headers=owner_headers,
        json={
            "title": "Campus Compass",
            "category": category,
            "problem": "Students need a clearer placement preparation process.",
            "solution": "A guided workspace for career preparation.",
            "audience": "College students",
            "features": ["Preparation roadmap"],
            "constraints": "No live integrations.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_prototype_api_is_owner_scoped_persisted_and_build_blocked(tmp_path):
    client, _factory = make_client(tmp_path)
    with client:
        owner = register(client, f"owner-{uuid4().hex}@example.invalid")
        other = register(client, f"other-{uuid4().hex}@example.invalid")
        reviewer = register(client, f"reviewer-{uuid4().hex}@example.invalid", role="reviewer")
        idea = create_idea(client, owner["headers"])
        requirement_id = seed_valid_requirements(
            client.app.state.session_factory, idea, owner["id"]
        )
        path = f"/api/v1/ideas/{idea['id']}/versions/1/prototypes"
        payload = {"requirement_analysis_id": requirement_id}

        assert client.post(path, json=payload).status_code == 401
        assert client.post(path, json=payload, headers=other["headers"]).status_code == 404
        assert client.post(path, json=payload, headers=reviewer["headers"]).status_code == 403
        created = client.post(path, json=payload, headers=owner["headers"])
        assert created.status_code == 201, created.text
        data = created.json()
        assert data["idea_version_id"] == idea["version_id"]
        assert data["requirement_analysis_run_id"] == requirement_id
        assert data["source_version"] == 1
        assert data["status"] == "source_generated"
        assert data["validation_status"] == "passed"
        assert data["build_status"] == "blocked_isolation"
        assert data["publish_status"] == "unpublished"
        assert data["preview_url"] is None
        assert data["artifact_metadata"]["built_artifact_available"] is False
        assert data["plan"]["preview_spec"]["source_version"] == 1
        assert data["plan"]["preview_spec"]["requirement_analysis_id"] == requirement_id
        assert data["plan"]["preview_spec"]["screens"][1]["components"][0]["type"] == "search"
        assert client.get(path, headers=owner["headers"]).json()["id"] == data["id"]
        assert client.get(
            f"{path}/{data['id']}/source",
            headers=owner["headers"],
        ).json()["files"]["src/Prototype.tsx"].startswith("import")

        replay = client.post(path, json=payload, headers=owner["headers"])
        assert replay.status_code == 200
        assert replay.json()["id"] == data["id"]
        assert client.get(
            f"{path}/{data['id']}",
            headers=other["headers"],
        ).status_code == 404
        assert client.get(
            f"{path}/{data['id']}",
            headers=reviewer["headers"],
        ).status_code == 403
        with client.app.state.session_factory() as session:
            persisted = session.get(PrototypeBuild, data["id"])
            assert persisted is not None
            assert persisted.build_status == "blocked_isolation"
            assert persisted.artifact_metadata["built_artifact_available"] is False


def test_reviewer_preview_requires_an_active_exact_version_assignment(tmp_path):
    client, factory = make_client(tmp_path)
    with client:
        owner = register(client, f"owner-{uuid4().hex}@example.invalid")
        assigned_reviewer = register(
            client, f"assigned-{uuid4().hex}@example.invalid", role="reviewer"
        )
        unassigned_reviewer = register(
            client, f"unassigned-{uuid4().hex}@example.invalid", role="reviewer"
        )
        idea = create_idea(client, owner["headers"])
        requirement_id = seed_valid_requirements(factory, idea, owner["id"])
        prototype_path = f"/api/v1/ideas/{idea['id']}/versions/1/prototypes"
        prototype_response = client.post(
            prototype_path,
            json={"requirement_analysis_id": requirement_id},
            headers=owner["headers"],
        )
        assert prototype_response.status_code == 201
        assignment_id = str(uuid4())
        cycle_id = str(uuid4())
        with factory() as session:
            session.add(
                ReviewCycle(
                    id=cycle_id,
                    idea_version_id=idea["version_id"],
                    opened_by_id=owner["id"],
                    status="open",
                )
            )
            session.add(
                ReviewerAssignment(
                    id=assignment_id,
                    idea_version_id=idea["version_id"],
                    reviewer_id=assigned_reviewer["id"],
                    assigned_by_id=owner["id"],
                    review_cycle_id=cycle_id,
                    active=True,
                    status="assigned",
                )
            )
            session.commit()

        path = f"/api/v1/reviewer/assignments/{assignment_id}/prototype"
        assert client.get(path).status_code == 401
        assert client.get(path, headers=owner["headers"]).status_code == 403
        assert client.get(path, headers=unassigned_reviewer["headers"]).status_code == 404
        preview = client.get(path, headers=assigned_reviewer["headers"])
        assert preview.status_code == 200, preview.text
        assert preview.json()["idea_version_id"] == idea["version_id"]
        assert preview.json()["source_version"] == 1
        assert preview.json()["requirement_analysis_run_id"] == requirement_id
        assert preview.json()["preview_spec"]["title"] == "Campus Compass"

        with factory() as session:
            assignment = session.get(ReviewerAssignment, assignment_id)
            assert assignment is not None
            assignment.active = False
            assignment.status = "revoked"
            session.commit()
        assert client.get(path, headers=assigned_reviewer["headers"]).status_code == 404


def test_prototype_generation_requires_validated_requirements_and_supported_category(tmp_path):
    client, _factory = make_client(tmp_path)
    with client:
        owner = register(client, f"owner-{uuid4().hex}@example.invalid")
        idea = create_idea(client, owner["headers"], category="Sustainability")
        requirement_id = seed_valid_requirements(
            client.app.state.session_factory, idea, owner["id"]
        )
        path = f"/api/v1/ideas/{idea['id']}/versions/1/prototypes"

        invalid_requirements = client.post(
            path,
            json={"requirement_analysis_id": str(uuid4())},
            headers=owner["headers"],
        )
        assert invalid_requirements.status_code == 409
        unsupported = client.post(
            path,
            json={"requirement_analysis_id": requirement_id},
            headers=owner["headers"],
        )
        assert unsupported.status_code == 201
        assert unsupported.json()["status"] == "unsupported_category"
        assert unsupported.json()["validation_status"] == "not_run"
        assert unsupported.json()["build_status"] == "blocked_isolation"
        next_version = client.post(
            f"/api/v1/ideas/{idea['id']}/versions",
            headers=owner["headers"],
            json={
                "title": "Sustainable campus V2",
                "category": "Sustainability",
                "problem": "Students need placement preparation and collection scheduling.",
                "solution": "A guided workspace for the campus.",
                "audience": "College students",
                "features": ["Preparation roadmap"],
                "constraints": "",
                "expected_version": 1,
                "change_summary": "Create another immutable source version.",
            },
        )
        assert next_version.status_code == 201
        wrong_version = client.post(
            f"/api/v1/ideas/{idea['id']}/versions/2/prototypes",
            json={"requirement_analysis_id": requirement_id},
            headers=owner["headers"],
        )
        assert wrong_version.status_code == 409


def test_missing_persisted_source_is_reported_and_build_never_succeeds(tmp_path):
    client, _factory = make_client(tmp_path)
    with client:
        owner = register(client, f"owner-{uuid4().hex}@example.invalid")
        idea = create_idea(client, owner["headers"])
        requirement_id = seed_valid_requirements(
            client.app.state.session_factory, idea, owner["id"]
        )
        path = f"/api/v1/ideas/{idea['id']}/versions/1/prototypes"
        created = client.post(
            path,
            json={"requirement_analysis_id": requirement_id},
            headers=owner["headers"],
        )
        prototype_id = created.json()["id"]
        (tmp_path / prototype_id / "src" / "prototype.json").unlink()

        response = client.get(
            f"{path}/{prototype_id}/source",
            headers=owner["headers"],
        )
        assert response.status_code == 410
        record = client.get(
            f"{path}/{prototype_id}",
            headers=owner["headers"],
        ).json()
        assert record["status"] == "source_missing"
        assert record["validation_status"] == "failed"
        assert record["build_status"] == "blocked_isolation"
        assert record["preview_url"] is None


def test_static_validation_failure_is_persisted_not_reported_as_a_build(tmp_path, monkeypatch):
    generated = generate()
    invalid_source = replace(
        generated,
        files={**generated.files, "src/Prototype.tsx": "eval('not allowed')"},
    )
    monkeypatch.setattr(
        ai_builder,
        "generate_education_placement_prototype",
        lambda **_kwargs: invalid_source,
    )
    client, _factory = make_client(tmp_path)
    with client:
        owner = register(client, f"owner-{uuid4().hex}@example.invalid")
        idea = create_idea(client, owner["headers"])
        requirement_id = seed_valid_requirements(
            client.app.state.session_factory, idea, owner["id"]
        )
        path = f"/api/v1/ideas/{idea['id']}/versions/1/prototypes"
        response = client.post(
            path,
            json={"requirement_analysis_id": requirement_id},
            headers=owner["headers"],
        )
        assert response.status_code == 201
        assert response.json()["status"] == "validation_failed"
        assert response.json()["validation_status"] == "failed"
        assert response.json()["build_status"] == "blocked_isolation"
        assert response.json()["artifact_metadata"] is None
        assert response.json()["preview_url"] is None


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="Requires the configured PostgreSQL database",
)
def test_postgres_persists_and_serves_private_generated_source(tmp_path):
    settings = Settings(prototype_source_storage_dir=tmp_path)
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
        with TestClient(application) as client:
            owner = register(client, f"postgres-{uuid4().hex}@example.invalid")
            idea = create_idea(client, owner["headers"])
            requirement_id = seed_valid_requirements(factory, idea, owner["id"])
            path = f"/api/v1/ideas/{idea['id']}/versions/1/prototypes"
            response = client.post(
                path,
                json={"requirement_analysis_id": requirement_id},
                headers=owner["headers"],
            )
            assert response.status_code == 201, response.text
            build = response.json()
            assert build["status"] == "source_generated"
            assert build["build_status"] == "blocked_isolation"
            source = client.get(
                f"{path}/{build['id']}/source",
                headers=owner["headers"],
            )
            assert source.status_code == 200
            assert "No live integrations" not in source.json()["files"]["src/prototype.json"]
            assert source.json()["files"]["src/Prototype.tsx"].startswith("import")
        transaction.rollback()
    engine.dispose()
