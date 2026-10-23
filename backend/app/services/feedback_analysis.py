import json
import math
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.agents.feedback_analysis import (
    PROMPT_VERSION,
    SIMILARITY_THRESHOLD,
    FeedbackAnalysisValidationError,
    build_analysis_output,
    cosine_similarity,
    embedding_content_hash,
    feedback_text,
    run_feedback_agent_graph,
    validate_embedding,
)
from app.config import Settings
from app.models import (
    FeedbackAnalysisRun,
    FeedbackEmbedding,
    Idea,
    IdeaReview,
    IdeaVersion,
)
from app.providers import build_chat_provider
from app.providers.base import (
    ChatProvider,
    ProviderConfigurationError,
    ProviderError,
    RetryableProviderError,
)
from app.providers.ollama import OllamaProvider
from app.schemas import FeedbackDuplicatePair

ChatProviderFactory = Callable[[Settings], ChatProvider]
EmbeddingProviderFactory = Callable[[Settings], OllamaProvider]


def configured_model(settings: Settings) -> str:
    if settings.ai_provider == "gemini":
        return settings.gemini_model or "unconfigured"
    return settings.ollama_chat_model


def source_evidence(review: IdeaReview) -> dict:
    return {
        "feedback_id": review.id,
        "rating": review.rating,
        "usability_score": review.usability_score,
        "usefulness_score": review.usefulness_score,
        "completeness_score": review.completeness_score,
        "feasibility_score": review.feasibility_score,
        "would_use": review.would_use,
        "feedback_text": review.feedback,
        "strengths": review.strengths,
        "concerns": review.concerns,
        "suggested_improvements": review.suggested_improvements,
        "usage_context": review.usage_context,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }


def create_analysis_run(
    session: Session,
    idea: Idea,
    version: IdeaVersion,
    requested_by_id: str,
    settings: Settings,
) -> tuple[FeedbackAnalysisRun, bool]:
    reviews = list(
        session.scalars(
            select(IdeaReview)
            .where(IdeaReview.idea_version_id == version.id)
            .order_by(IdeaReview.id)
        )
    )
    if not reviews:
        raise ValueError("No persisted feedback exists for this immutable idea version.")
    feedback_ids = [review.id for review in reviews]
    digest = sha256(
        json.dumps(
            {"idea_version_id": version.id, "feedback_ids": feedback_ids},
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    existing = session.scalar(
        select(FeedbackAnalysisRun)
        .where(
            FeedbackAnalysisRun.input_digest == digest,
            FeedbackAnalysisRun.status.in_(["queued", "running", "completed"]),
        )
        .order_by(FeedbackAnalysisRun.created_at.desc())
    )
    if existing is not None:
        return existing, False
    run = FeedbackAnalysisRun(
        idea_id=idea.id,
        idea_version_id=version.id,
        source_version=version.version,
        requested_by_id=requested_by_id,
        workflow_run_id=str(uuid4()),
        input_digest=digest,
        source_feedback_ids=feedback_ids,
        provider=settings.ai_provider,
        model_version=configured_model(settings),
        embedding_model_version=settings.ollama_embedding_model,
        prompt_version=PROMPT_VERSION,
    )
    session.add(run)
    session.flush()
    return run, True


def _mark_failed(
    factory: sessionmaker[Session],
    run_id: str,
    message: str,
    validation_status: str = "not_run",
) -> None:
    with factory() as session:
        run = session.get(FeedbackAnalysisRun, run_id)
        if run is None:
            raise ValueError("Feedback analysis run was not found.")
        run.status = "failed"
        run.validation_status = validation_status
        run.error_message = message
        run.completed_at = datetime.now(UTC)
        session.commit()


def mark_feedback_analysis_failed(
    factory: sessionmaker[Session],
    run_id: str,
    message: str,
) -> None:
    _mark_failed(factory, run_id, message)


def _load_embeddings(
    session: Session,
    evidence: list[dict],
    settings: Settings,
    embedding_provider_factory: EmbeddingProviderFactory,
) -> dict[str, list[float]]:
    provider = embedding_provider_factory(settings)
    vectors: dict[str, list[float]] = {}
    for item in evidence:
        content_hash = embedding_content_hash(item)
        record = session.scalar(
            select(FeedbackEmbedding).where(
                FeedbackEmbedding.feedback_id == item["feedback_id"],
                FeedbackEmbedding.model_version == settings.ollama_embedding_model,
            )
        )
        if record is not None and record.content_sha256 == content_hash:
            values = validate_embedding(record.embedding, settings.ollama_embedding_dimensions)
        else:
            if record is not None:
                raise FeedbackAnalysisValidationError(
                    "Immutable feedback content does not match its persisted embedding hash."
                )
            values = validate_embedding(
                provider.embed(feedback_text(item)),
                settings.ollama_embedding_dimensions,
            )
            record = FeedbackEmbedding(
                feedback_id=item["feedback_id"],
                provider="ollama",
                model_version=settings.ollama_embedding_model,
                dimension=settings.ollama_embedding_dimensions,
                content_sha256=content_hash,
                embedding=values,
            )
            session.add(record)
        vectors[item["feedback_id"]] = values
    session.flush()
    return vectors


def _semantic_duplicates(
    session: Session,
    vectors: dict[str, list[float]],
    model_version: str,
) -> list[FeedbackDuplicatePair]:
    feedback_ids = list(vectors)
    dialect = session.get_bind().dialect.name
    duplicate_pairs = []
    for index, left_id in enumerate(feedback_ids):
        for right_id in feedback_ids[index + 1 :]:
            if dialect == "postgresql":
                distance = session.scalar(
                    select(FeedbackEmbedding.embedding.cosine_distance(vectors[right_id])).where(
                        FeedbackEmbedding.feedback_id == left_id,
                        FeedbackEmbedding.model_version == model_version,
                    )
                )
                if distance is None or not math.isfinite(float(distance)):
                    raise FeedbackAnalysisValidationError(
                        "pgvector could not calculate a finite cosine distance."
                    )
                similarity = 1 - float(distance)
                method = "pgvector_cosine"
            else:
                similarity = cosine_similarity(vectors[left_id], vectors[right_id])
                method = "deterministic_test_cosine"
            if similarity >= SIMILARITY_THRESHOLD:
                duplicate_pairs.append(
                    FeedbackDuplicatePair(
                        feedback_ids=[left_id, right_id],
                        cosine_similarity=max(-1.0, min(1.0, similarity)),
                        method=method,
                    )
                )
    return duplicate_pairs


def execute_feedback_analysis(
    factory: sessionmaker[Session],
    settings: Settings,
    run_id: str,
    provider_factory: ChatProviderFactory = build_chat_provider,
    embedding_provider_factory: EmbeddingProviderFactory = OllamaProvider,
) -> dict[str, str]:
    with factory() as session:
        run = session.get(FeedbackAnalysisRun, run_id)
        if run is None:
            raise ValueError("Feedback analysis run was not found.")
        if run.status in {"completed", "failed", "running"}:
            return {"status": run.status, "workflow_run_id": run.workflow_run_id}
        reviews = list(
            session.scalars(
                select(IdeaReview)
                .where(
                    IdeaReview.idea_version_id == run.idea_version_id,
                    IdeaReview.id.in_(run.source_feedback_ids),
                )
                .order_by(IdeaReview.id)
            )
        )
        if [review.id for review in reviews] != run.source_feedback_ids:
            _mark_failed(
                factory,
                run.id,
                "The persisted source feedback snapshot is incomplete or changed.",
                "invalid",
            )
            return {"status": "failed", "workflow_run_id": run.workflow_run_id}
        version = session.get(IdeaVersion, run.idea_version_id)
        if version is None or version.version != run.source_version:
            _mark_failed(
                factory,
                run.id,
                "The immutable source idea version is unavailable.",
                "invalid",
            )
            return {"status": "failed", "workflow_run_id": run.workflow_run_id}
        idea_context = {
            "title": version.title,
            "category": version.category,
            "problem": version.problem,
            "solution": version.solution,
            "audience": version.audience,
            "features": list(version.features),
            "constraints": version.constraints,
        }
        evidence = [source_evidence(review) for review in reviews]
        workflow_run_id = run.workflow_run_id
        run.status = "running"
        run.attempt_count += 1
        run.started_at = run.started_at or datetime.now(UTC)
        run.error_message = None
        session.commit()

    try:
        chat_provider = provider_factory(settings)
        agents = run_feedback_agent_graph(
            provider=chat_provider,
            evidence=evidence,
            idea_context=idea_context,
        )
        with factory() as session:
            vectors = _load_embeddings(
                session, evidence, settings, embedding_provider_factory
            )
            duplicates = _semantic_duplicates(
                session, vectors, settings.ollama_embedding_model
            )
            session.commit()
        result = build_analysis_output(
            source_feedback_ids=run.source_feedback_ids,
            evidence=evidence,
            quality_items=agents["quality"].items,
            themes=agents["themes"],
            contradictions=agents["contradictions"],
            duplicate_pairs=duplicates,
            proposals=agents["proposals"],
        )
    except RetryableProviderError as error:
        with factory() as session:
            run = session.get(FeedbackAnalysisRun, run_id)
            if run is None:
                raise ValueError("Feedback analysis run was not found.") from error
            run.status = "queued"
            run.error_message = str(error)
            session.commit()
        raise
    except ProviderConfigurationError as error:
        _mark_failed(factory, run_id, str(error))
        return {"status": "failed", "workflow_run_id": workflow_run_id}
    except ProviderError as error:
        _mark_failed(factory, run_id, str(error))
        return {"status": "failed", "workflow_run_id": workflow_run_id}
    except FeedbackAnalysisValidationError as error:
        _mark_failed(factory, run_id, str(error), "invalid")
        return {"status": "failed", "workflow_run_id": workflow_run_id}
    except Exception:
        _mark_failed(
            factory,
            run_id,
            "The feedback intelligence workflow encountered an unexpected internal error.",
        )
        raise

    with factory() as session:
        run = session.get(FeedbackAnalysisRun, run_id)
        if run is None:
            raise ValueError("Feedback analysis run was not found.")
        run.result = result.model_dump(mode="json")
        run.status = "completed"
        run.validation_status = "valid"
        run.error_message = None
        run.completed_at = datetime.now(UTC)
        session.commit()
        return {"status": run.status, "workflow_run_id": workflow_run_id}
