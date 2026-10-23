from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.ai_builder import (
    PrototypeValidationError,
    UnsupportedPrototypeCategory,
    validate_generated_files,
    write_source_files,
)
from app.models import IdeaVersion, PrototypeBuild, RequirementAnalysisRun
from app.schemas import (
    PrototypePreviewSpec,
    RequirementSpecification,
)


def _build_preview_spec(
    idea: IdeaVersion,
    requirements: RequirementAnalysisRun,
) -> dict:
    specification = RequirementSpecification.model_validate(requirements.result)
    spec = PrototypePreviewSpec(
        schema_version="1",
        source_version=idea.version,
        requirement_analysis_id=requirements.id,
        title=idea.title,
        screens=[
            {
                "key": "overview",
                "title": "Overview",
                "components": [
                    {"type": "heading", "text": idea.title},
                    {
                        "type": "text",
                        "text": next(
                            (fact.text for fact in specification.problem),
                            idea.problem,
                        ),
                    },
                    {
                        "type": "card",
                        "title": "Designed for",
                        "body": idea.audience,
                    },
                    {
                        "type": "button",
                        "label": "Mark prototype as explored",
                        "action": "mark-complete",
                    },
                ],
            },
            {
                "key": "features",
                "title": "Features",
                "components": [
                    {
                        "type": "search",
                        "label": "Search validated features",
                        "items": [
                            fact.text
                            for fact in specification.core_features
                            if fact.basis == "explicit"
                        ],
                    }
                ],
            },
            {
                "key": "journeys",
                "title": "Journeys",
                "components": [
                    {
                        "type": "checklist",
                        "title": "Validated journey steps",
                        "items": [
                            step
                            for journey in specification.user_journeys
                            for step in journey.steps
                        ],
                    }
                ],
            },
            {
                "key": "questions",
                "title": "Questions",
                "components": [
                    *[
                        {
                            "type": "card",
                            "title": f"Open question {index + 1}",
                            "body": question,
                        }
                        for index, question in enumerate(
                            specification.open_questions
                        )
                    ],
                    {
                        "type": "form",
                        "label": "Try a local prototype note",
                        "placeholder": "Write a note for this session",
                        "submit_label": "Save note locally",
                    },
                ],
            },
        ],
    )
    return spec.model_dump(mode="json")


def _static_validation_results(source_files: list) -> dict:
    return {
        "scope": "static source and manifest validation only; generated source was not executed",
        "checks": [
            {"name": "allowlisted_paths", "status": "passed"},
            {"name": "allowlisted_dependencies_and_scripts", "status": "passed"},
            {"name": "disallowed_source_capabilities", "status": "passed"},
            {"name": "required_source_files", "status": "passed"},
            {"name": "source_size_limit", "status": "passed"},
            {"name": "source_hashes", "status": "passed"},
        ],
        "source_file_count": len(source_files),
        "source_bytes": sum(item.size_bytes for item in source_files),
        "build_boundary_available": False,
        "built_artifact_available": False,
    }


def create_prototype_source(
    session: Session,
    idea: IdeaVersion,
    requirements: RequirementAnalysisRun,
    storage_dir: str,
) -> PrototypeBuild:
    build = PrototypeBuild(
        id=str(uuid4()),
        idea_id=idea.idea_id,
        idea_version_id=idea.id,
        source_version=idea.version,
        requirement_analysis_run_id=requirements.id,
        workflow_run_id=str(uuid4()),
        status="generation_failed",
        validation_status="not_run",
        build_status="blocked_isolation",
        publish_status="unpublished",
        validation_results={
            "scope": "static source validation",
            "checks": [],
            "build_boundary_available": False,
            "built_artifact_available": False,
        },
        source_files=[],
    )
    session.add(build)
    session.flush()

    try:
        from app.agents.ai_builder import generate_education_placement_prototype

        result = generate_education_placement_prototype(
            category=idea.category,
            title=idea.title,
            problem=idea.problem,
            solution=idea.solution,
            audience=idea.audience,
            features=list(idea.features),
            source_version=idea.version,
            requirements=RequirementSpecification.model_validate(requirements.result),
        )
        source_files = validate_generated_files(result.files)
    except UnsupportedPrototypeCategory as error:
        build.status = "unsupported_category"
        build.validation_status = "not_run"
        build.error_message = str(error)
        build.validation_results = {
            **build.validation_results,
            "checks": [{"name": "supported_category", "status": "not_run"}],
        }
        build.completed_at = datetime.now(UTC)
        session.commit()
        session.refresh(build)
        return build
    except PrototypeValidationError as error:
        build.status = "validation_failed"
        build.validation_status = "failed"
        build.error_message = str(error)
        build.validation_results = {
            **build.validation_results,
            "checks": [{"name": "static_source_validation", "status": "failed"}],
        }
        build.completed_at = datetime.now(UTC)
        session.commit()
        session.refresh(build)
        return build
    except ValidationError:
        build.status = "validation_failed"
        build.validation_status = "failed"
        build.error_message = "The persisted requirement output failed schema validation."
        build.validation_results = {
            **build.validation_results,
            "checks": [{"name": "requirement_output", "status": "failed"}],
        }
        build.completed_at = datetime.now(UTC)
        session.commit()
        session.refresh(build)
        return build

    build.plan = {
        **result.plan.model_dump(mode="json"),
        "preview_spec": _build_preview_spec(idea, requirements),
    }
    build.manifest = result.manifest.model_dump(mode="json")
    build.validation_results = _static_validation_results(source_files)
    build.template_id = result.plan.template_id
    build.template_version = result.plan.template_version
    build.source_files = [item.as_dict() for item in source_files]
    build.source_storage_key = build.id
    try:
        write_source_files(storage_dir, build.id, result.files, source_files)
    except (OSError, PrototypeValidationError):
        build.status = "generation_failed"
        build.validation_status = "failed"
        build.error_message = "Generated source could not be stored in private storage."
        build.source_storage_key = None
        build.source_files = []
        build.artifact_metadata = None
        build.validation_results = {
            **build.validation_results,
            "checks": [
                *build.validation_results["checks"],
                {"name": "private_source_storage", "status": "failed"},
            ],
        }
        build.completed_at = datetime.now(UTC)
        session.commit()
        session.refresh(build)
        return build

    source_digest = sha256()
    for item in source_files:
        source_digest.update(item.path.encode("utf-8"))
        source_digest.update(item.sha256.encode("ascii"))
    build.artifact_metadata = {
        "artifact_type": "generated_source",
        "file_count": len(source_files),
        "total_size_bytes": sum(item.size_bytes for item in source_files),
        "source_sha256": source_digest.hexdigest(),
        "built_artifact_available": False,
    }
    build.status = "source_generated"
    build.validation_status = "passed"
    build.error_message = None
    build.completed_at = datetime.now(UTC)
    session.commit()
    session.refresh(build)
    return build


def get_requirement_run_for_version(
    session: Session,
    idea_version_id: str,
    requirement_run_id: str,
) -> RequirementAnalysisRun | None:
    return session.scalar(
        select(RequirementAnalysisRun).where(
            RequirementAnalysisRun.id == requirement_run_id,
            RequirementAnalysisRun.idea_version_id == idea_version_id,
            RequirementAnalysisRun.status == "completed",
            RequirementAnalysisRun.validation_status == "valid",
            RequirementAnalysisRun.result.is_not(None),
        )
    )


def mark_source_missing(session: Session, build: PrototypeBuild) -> None:
    build.status = "source_missing"
    build.validation_status = "failed"
    build.error_message = "Generated source is missing or failed integrity verification."
    build.validation_results = {
        **build.validation_results,
        "checks": [
            *build.validation_results.get("checks", []),
            {"name": "source_integrity", "status": "failed"},
        ],
    }
    build.completed_at = datetime.now(UTC)
    session.commit()
