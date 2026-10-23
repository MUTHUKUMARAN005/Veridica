from datetime import UTC, datetime

from celery import Celery
from kombu.exceptions import OperationalError
from sqlalchemy import select

from app.config import Settings

settings = Settings()
celery_app = Celery("veridica", broker=str(settings.redis_url), backend=str(settings.redis_url))
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_time_limit=300,
    task_soft_time_limit=270,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)


@celery_app.task(name="veridica.health.ping")
def ping() -> dict[str, str]:
    return {"status": "ok", "service": "veridica-worker"}


@celery_app.task(name="veridica.feedback.analysis.requested")
def receive_feedback_analysis_request(outbox_id: str) -> dict[str, str]:
    from app.db import session_factory
    from app.models import (
        FeedbackAnalysisOutbox,
        Idea,
        IdeaReview,
        IdeaVersion,
    )
    from app.services.feedback_analysis import create_analysis_run

    factory = session_factory(settings)
    with factory() as session:
        outbox = session.get(FeedbackAnalysisOutbox, outbox_id)
        if outbox is None:
            raise ValueError("Feedback analysis outbox record does not exist.")
        if outbox.status != "received":
            outbox.status = "received"
            outbox.received_at = datetime.now(UTC)
            outbox.last_error = None
        review = session.get(IdeaReview, outbox.feedback_id)
        if review is None:
            raise ValueError("Persisted feedback for the analysis outbox was not found.")
        version = session.get(IdeaVersion, review.idea_version_id)
        idea = session.scalar(
            select(Idea).where(Idea.id == review.idea_id).with_for_update()
        )
        if version is None or idea is None:
            raise ValueError("Persisted feedback source idea version was not found.")
        run, _created = create_analysis_run(
            session, idea, version, idea.owner_id, settings
        )
        session.commit()
        session.refresh(outbox)
        session.refresh(run)
        run_id = run.id
        workflow_run_id = run.workflow_run_id
        feedback_id = outbox.feedback_id

    if run.status == "queued":
        try:
            analyze_feedback_run.apply_async(args=[run_id], task_id=workflow_run_id)
        except OperationalError:
            from app.services.feedback_analysis import mark_feedback_analysis_failed

            mark_feedback_analysis_failed(
                factory, run_id, "The background worker queue is unavailable."
            )
            with factory() as session:
                outbox = session.get(FeedbackAnalysisOutbox, outbox_id)
                if outbox is not None:
                    outbox.last_error = "The background worker queue is unavailable."
                    session.commit()
    return {"status": "received", "feedback_id": feedback_id}


@celery_app.task(
    bind=True,
    name="veridica.requirements.analyze",
    max_retries=3,
)
def analyze_requirement_run(self, analysis_id: str) -> dict[str, str]:
    from app.db import session_factory
    from app.providers.base import RetryableProviderError
    from app.services.requirements import (
        execute_requirement_analysis,
        mark_requirement_failed,
    )

    factory = session_factory(settings)
    try:
        return execute_requirement_analysis(factory, settings, analysis_id)
    except RetryableProviderError as error:
        if self.request.retries >= self.max_retries:
            message = "The AI provider remained unavailable after repeated retries."
            mark_requirement_failed(factory, analysis_id, message)
            return {"status": "failed", "workflow_run_id": analysis_id}
        raise self.retry(
            exc=error,
            countdown=min(10 * (2**self.request.retries), 60),
        ) from error


@celery_app.task(
    bind=True,
    name="veridica.feedback.analyze",
    max_retries=3,
)
def analyze_feedback_run(self, analysis_id: str) -> dict[str, str]:
        
    pass
def generate_prototype_task(requirement_analysis_run_id: str, idea_version_id: str, storage_dir: str) -> dict[str, str]:
    """Celery task to generate prototype source code from requirement analysis."""
    from app.db import session_factory
    from app.services.prototypes import create_prototype_source, get_requirement_run_for_version

    factory = session_factory()
    with factory() as session:
        requirement_run = get_requirement_run_for_version(session, idea_version_id, requirement_analysis_run_id)
        if requirement_run is None:
            return {"status": "failed", "error": "Requirement analysis run not found"}

        idea_version = session.get(IdeaVersion, idea_version_id)
        if idea_version is None:
            return {"status": "failed", "error": "Idea version not found"}

        build = create_prototype_source(
            session,
            idea_version,
            requirement_run,
            storage_dir,
        )
        session.commit()
        session.refresh(build)
        return {"status": "completed", "prototype_id": str(build.id)}
    from app.db import session_factory
    from app.providers.base import RetryableProviderError
    from app.services.feedback_analysis import (
        execute_feedback_analysis,
        mark_feedback_analysis_failed,
    )

    factory = session_factory(settings)
    try:
        return execute_feedback_analysis(factory, settings, analysis_id)
    except RetryableProviderError as error:
        if self.request.retries >= self.max_retries:
            mark_feedback_analysis_failed(
                factory,
                analysis_id,
                "The AI or embedding provider remained unavailable after repeated retries.",
            )
            return {"status": "failed", "workflow_run_id": analysis_id}
        raise self.retry(
            exc=error,
            countdown=min(10 * (2**self.request.retries), 60),
        ) from error