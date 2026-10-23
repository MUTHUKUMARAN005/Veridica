from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.agents.requirement_agent import (
    RequirementOutputValidationError,
    RequirementSourceVersion,
    analyze_requirements,
)
from app.config import Settings
from app.models import IdeaVersion, RequirementAnalysisRun
from app.providers import build_chat_provider
from app.providers.base import (
    ChatProvider,
    ProviderConfigurationError,
    ProviderError,
    RetryableProviderError,
)

ProviderFactory = Callable[[Settings], ChatProvider]


def configured_model(settings: Settings) -> str:
    if settings.ai_provider == "gemini":
        return settings.gemini_model or "unconfigured"
    return settings.ollama_chat_model


def mark_requirement_failed(
    factory: sessionmaker[Session],
    analysis_id: str,
    message: str,
    validation_status: str = "not_run",
) -> None:
    with factory() as session:
        analysis = session.get(RequirementAnalysisRun, analysis_id)
        if analysis is None:
            raise ValueError("Requirement analysis run was not found.")
        analysis.status = "failed"
        analysis.validation_status = validation_status
        analysis.error_message = message
        analysis.completed_at = datetime.now(UTC)
        session.commit()


def execute_requirement_analysis(
    factory: sessionmaker[Session],
    settings: Settings,
    analysis_id: str,
    provider_factory: ProviderFactory = build_chat_provider,
) -> dict[str, str]:
    with factory() as session:
        analysis = session.get(RequirementAnalysisRun, analysis_id)
        if analysis is None:
            raise ValueError("Requirement analysis run was not found.")
        if analysis.status in {"completed", "failed", "running"}:
            return {"status": analysis.status, "workflow_run_id": analysis.workflow_run_id}
        workflow_run_id = analysis.workflow_run_id
        version = session.scalar(
            select(IdeaVersion).where(
                IdeaVersion.id == analysis.idea_version_id,
                IdeaVersion.idea_id == analysis.idea_id,
                IdeaVersion.version == analysis.source_version,
            )
        )
        if version is None:
            analysis.status = "failed"
            analysis.validation_status = "not_run"
            analysis.error_message = "The source idea version is unavailable."
            analysis.completed_at = datetime.now(UTC)
            session.commit()
            return {"status": "failed", "workflow_run_id": analysis.workflow_run_id}
        version_values = {
            "id": version.id,
            "idea_id": version.idea_id,
            "version": version.version,
            "title": version.title,
            "problem": version.problem,
            "solution": version.solution,
            "audience": version.audience,
            "features": list(version.features),
            "constraints": version.constraints,
        }
        analysis.status = "running"
        analysis.attempt_count += 1
        analysis.started_at = analysis.started_at or datetime.now(UTC)
        analysis.error_message = None
        session.commit()

    version_snapshot = RequirementSourceVersion(
        title=version_values["title"],
        problem=version_values["problem"],
        solution=version_values["solution"],
        audience=version_values["audience"],
        features=version_values["features"],
        constraints=version_values["constraints"],
    )
    try:
        provider = provider_factory(settings)
        result = analyze_requirements(version_snapshot, provider)
    except RetryableProviderError as error:
        with factory() as session:
            analysis = session.get(RequirementAnalysisRun, analysis_id)
            if analysis is None:
                raise ValueError("Requirement analysis run was not found.") from error
            analysis.status = "queued"
            analysis.error_message = str(error)
            session.commit()
        raise
    except ProviderConfigurationError as error:
        mark_requirement_failed(factory, analysis_id, str(error))
        return {"status": "failed", "workflow_run_id": workflow_run_id}
    except ProviderError as error:
        mark_requirement_failed(factory, analysis_id, str(error))
        return {"status": "failed", "workflow_run_id": workflow_run_id}
    except RequirementOutputValidationError as error:
        mark_requirement_failed(factory, analysis_id, str(error), "invalid")
        return {"status": "failed", "workflow_run_id": workflow_run_id}
    except Exception:
        mark_requirement_failed(
            factory,
            analysis_id,
            "The requirement workflow encountered an unexpected internal error.",
        )
        raise

    with factory() as session:
        analysis = session.get(RequirementAnalysisRun, analysis_id)
        if analysis is None:
            raise ValueError("Requirement analysis run was not found.")
        analysis.result = result.model_dump(mode="json")
        analysis.status = "completed"
        analysis.validation_status = "valid"
        analysis.error_message = None
        analysis.completed_at = datetime.now(UTC)
        session.commit()
        return {"status": analysis.status, "workflow_run_id": analysis.workflow_run_id}
