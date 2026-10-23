import json
import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from kombu.exceptions import OperationalError
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.ai_builder import PrototypeValidationError, read_source_files
from app.agents.evolution import PROMPT_VERSION as EVOLUTION_PROMPT_VERSION
from app.agents.evolution import propose_evidence_changes
from app.api import current_user, require_role
from app.config import Settings
from app.db import request_session, session_factory
from app.models import (
    DecisionReport,
    EvolutionProposal,
    FeedbackAnalysisOutbox,
    FeedbackAnalysisRun,
    Idea,
    IdeaAsset,
    IdeaReview,
    IdeaStatusEvent,
    IdeaVersion,
    PrototypeBuild,
    RequirementAnalysisRun,
    ReviewCycle,
    ReviewerAssignment,
    ReviewSession,
    User,
)
from app.providers import build_chat_provider
from app.providers.base import ProviderConfigurationError
from app.schemas import (
    AdminAssignmentCreate,
    AdminAssignmentResponse,
    AuthResponse,
    DecisionReportResponse,
    EvolutionApprovalRequest,
    EvolutionProposalResponse,
    FeedbackAnalysisOutput,
    FeedbackAnalysisResponse,
    IdeaCreate,
    IdeaDetail,
    IdeaPage,
    IdeaResponse,
    IdeaStatusEventResponse,
    IdeaStatusUpdate,
    IdeaVersionCreate,
    LoginRequest,
    PrototypeBuildResponse,
    PrototypeGenerationRequest,
    PrototypePreviewSpec,
    PrototypeSourceResponse,
    RegisterRequest,
    RequirementAnalysisResponse,
    RequirementFact,
    RequirementSpecification,
    ReviewerPrototypePreviewResponse,
    ReviewCycleResponse,
    ReviewerAssignmentResponse,
    ReviewResponse,
    ReviewSessionResponse,
    ReviewSubmission,
    UserResponse,
)
from app.security import create_access_token, hash_password, verify_password
from app.services import health
from app.services.decision_intelligence import (
    build_decision_report,
    report_record,
)
from app.services.feedback_analysis import (
    create_analysis_run,
)
from app.services.idea_assets import store_private_asset
from app.services.prototypes import (
    create_prototype_source,
    get_requirement_run_for_version,
    mark_source_missing,
)
from app.services.requirements import configured_model
from app.workers.celery_app import (
    analyze_feedback_run,
    analyze_requirement_run,
    receive_feedback_analysis_request,
)


class FeedbackBodySizeLimitMiddleware:
    def __init__(self, app, max_bytes: int = 32 * 1024):
        self.app = app
        self.max_bytes = max_bytes
        self.path_pattern = re.compile(r"^/api/v1/reviewer/assignments/[^/]+/reviews$")

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or not self.path_pattern.fullmatch(scope["path"])
        ):
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope["headers"]}
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send, status=400, detail="Invalid Content-Length header.")
                return

        total = 0

        async def limited_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    raise RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLarge:
            await self._reject(send)

    async def _reject(
        self,
        send,
        status: int = 413,
        detail: str = "Feedback request is too large.",
    ):
        body = json.dumps({"detail": detail}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class RequestTooLarge(Exception):
    pass


class Readiness(BaseModel):
    status: Literal["ready", "unavailable"]
    services: dict[str, Literal["connected", "unavailable"]]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    application = FastAPI(title="Veridica API", version="0.1.0")
    application.state.settings = settings
    application.state.session_factory = session_factory(settings)
    def dispatch_feedback_analysis(outbox_id: str) -> None:
        receive_feedback_analysis_request.apply_async(args=[outbox_id], task_id=outbox_id)

    application.state.feedback_dispatcher = dispatch_feedback_analysis

    def dispatch_feedback_analysis_run(run_id: str, workflow_run_id: str) -> None:
        analyze_feedback_run.apply_async(args=[run_id], task_id=workflow_run_id)

    application.state.feedback_analysis_dispatcher = dispatch_feedback_analysis_run

    def dispatch_requirement_analysis(analysis_id: str, workflow_run_id: str) -> None:
        analyze_requirement_run.apply_async(
            args=[analysis_id],
            task_id=workflow_run_id,
        )

    application.state.requirement_dispatcher = dispatch_requirement_analysis
    application.add_middleware(FeedbackBodySizeLimitMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    @application.get("/api/v1/health/live", tags=["Health"])
    def live() -> dict[str, str]:
        return {"status": "ok", "service": "veridica-api"}

    @application.post(
        "/api/v1/auth/register", response_model=AuthResponse, status_code=201, tags=["Auth"]
    )
    def register(
        payload: RegisterRequest, session: Annotated[Session, Depends(request_session)]
    ) -> AuthResponse:
        email = payload.email.strip().lower()
        if session.scalar(select(User).where(User.email == email)):
            raise HTTPException(
                status_code=409, detail="An account with this email already exists."
            )
        user = User(email=email, password_hash=hash_password(payload.password), role="owner")
        session.add(user)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                status_code=409, detail="An account with this email already exists."
            ) from error
        session.refresh(user)
        return _auth_response(user, settings)

    @application.post("/api/v1/auth/login", response_model=AuthResponse, tags=["Auth"])
    def login(
        payload: LoginRequest, session: Annotated[Session, Depends(request_session)]
    ) -> AuthResponse:
        user = session.scalar(
            select(User).where(User.email == payload.email.strip().lower())
        )
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        return _auth_response(user, settings)

    @application.get("/api/v1/auth/me", response_model=UserResponse, tags=["Auth"])
    def me(user: Annotated[User, Depends(current_user)]) -> User:
        return user

    @application.post(
        "/api/v1/ideas", response_model=IdeaResponse, status_code=201, tags=["Ideas"]
    )
    def create_idea(
        payload: IdeaCreate,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> IdeaResponse:
        idea = Idea(owner_id=user.id, status="Draft", current_version=1)
        idea.versions.append(
            _version_from_payload(
                payload,
                version=1,
                created_by_id=user.id,
                source_version_id=None,
                change_summary="Initial idea submission",
            )
        )
        try:
            session.add(idea)
            session.flush()
            session.add(
                IdeaStatusEvent(
                    idea_id=idea.id,
                    changed_by_id=user.id,
                    sequence=1,
                    from_status=None,
                    to_status=idea.status,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        session.refresh(idea)
        return _idea_response(idea, idea.versions[0])

    @application.get("/api/v1/ideas", response_model=IdeaPage, tags=["Ideas"])
    def list_ideas(
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
        status: str | None = None,
        category: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
        q: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    ) -> IdeaPage:
        if status is not None and status not in {
            "Draft",
            "Ready for review",
            "Review open",
            "Evolution ready",
            "Archived",
        }:
            raise HTTPException(status_code=422, detail="Unsupported idea status filter.")

        filters = [
            Idea.owner_id == user.id,
            IdeaVersion.version == Idea.current_version,
        ]
        if status is not None:
            filters.append(Idea.status == status)
        if category is not None:
            filters.append(func.lower(IdeaVersion.category) == category.strip().lower())
        if q is not None:
            escaped_query = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped_query}%"
            filters.append(
                func.lower(IdeaVersion.title).like(pattern.lower(), escape="\\")
                | func.lower(IdeaVersion.problem).like(pattern.lower(), escape="\\")
                | func.lower(IdeaVersion.solution).like(pattern.lower(), escape="\\")
            )
        query = (
            select(Idea, IdeaVersion)
            .join(IdeaVersion, IdeaVersion.idea_id == Idea.id)
            .where(*filters)
        )
        total = session.scalar(
            select(func.count()).select_from(Idea).join(
                IdeaVersion, IdeaVersion.idea_id == Idea.id
            ).where(*filters)
        ) or 0
        records = session.execute(
            query.order_by(Idea.updated_at.desc(), Idea.id).limit(limit).offset(offset)
        ).all()
        return IdeaPage(
            items=[_idea_response(idea, version) for idea, version in records],
            total=total,
            limit=limit,
            offset=offset,
        )

    @application.get("/api/v1/ideas/{idea_id}", response_model=IdeaDetail, tags=["Ideas"])
    def get_idea(
        idea_id: str,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> IdeaDetail:
        idea = session.scalar(select(Idea).where(Idea.id == idea_id, Idea.owner_id == user.id))
        if idea is None:
            raise HTTPException(status_code=404, detail="Idea not found.")
        return IdeaDetail(
            **_idea_response(idea, idea.versions[-1]).model_dump(),
            versions=[_idea_response(idea, version) for version in idea.versions],
            status_history=[
                IdeaStatusEventResponse.model_validate(event)
                for event in session.scalars(
                    select(IdeaStatusEvent)
                    .where(IdeaStatusEvent.idea_id == idea.id)
                    .order_by(IdeaStatusEvent.sequence)
                )
            ],
        )

    @application.post(
        "/api/v1/ideas/{idea_id}/versions/{version}/feedback-analysis",
        response_model=FeedbackAnalysisResponse,
        status_code=202,
        tags=["Feedback Analysis"],
    )
    def start_feedback_analysis(
        idea_id: str,
        version: int,
        request: Request,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> FeedbackAnalysisResponse:
        record = session.execute(
            select(Idea, IdeaVersion)
            .join(IdeaVersion, IdeaVersion.idea_id == Idea.id)
            .where(
                Idea.id == idea_id,
                Idea.owner_id == user.id,
                IdeaVersion.version == version,
            )
            .with_for_update(of=Idea)
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Idea version not found.")
        idea, idea_version = record
        try:
            run, _created = create_analysis_run(
                session, idea, idea_version, user.id, settings
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        session.commit()
        session.refresh(run)
        if run.status == "queued":
            try:
                request.app.state.feedback_analysis_dispatcher(run.id, run.workflow_run_id)
            except OperationalError:
                run.status = "failed"
                run.validation_status = "not_run"
                run.error_message = "The background worker queue is unavailable."
                run.completed_at = datetime.now(UTC)
                session.commit()
                session.refresh(run)
        return FeedbackAnalysisResponse.model_validate(run)

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/feedback-analysis",
        response_model=FeedbackAnalysisResponse | None,
        tags=["Feedback Analysis"],
    )
    def get_latest_feedback_analysis(
        idea_id: str,
        version: int,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> FeedbackAnalysisResponse | None:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        run = session.scalar(
            select(FeedbackAnalysisRun)
            .where(FeedbackAnalysisRun.idea_version_id == idea_version.id)
            .order_by(FeedbackAnalysisRun.created_at.desc())
        )
        return FeedbackAnalysisResponse.model_validate(run) if run is not None else None

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/feedback-analysis/{analysis_id}",
        response_model=FeedbackAnalysisResponse,
        tags=["Feedback Analysis"],
    )
    def get_feedback_analysis(
        idea_id: str,
        version: int,
        analysis_id: str,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> FeedbackAnalysisResponse:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        run = session.scalar(
            select(FeedbackAnalysisRun).where(
                FeedbackAnalysisRun.id == analysis_id,
                FeedbackAnalysisRun.idea_version_id == idea_version.id,
            )
        )
        if run is None:
            raise HTTPException(status_code=404, detail="Feedback analysis run not found.")
        return FeedbackAnalysisResponse.model_validate(run)

    @application.post(
        "/api/v1/ideas/{idea_id}/versions/{version}/evolution",
        response_model=EvolutionProposalResponse,
        status_code=201,
        tags=["Evolution"],
    )
    def create_evolution_proposal(
        idea_id: str,
        version: int,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> EvolutionProposalResponse:
        record = session.execute(
            select(Idea, IdeaVersion)
            .join(IdeaVersion, IdeaVersion.idea_id == Idea.id)
            .where(
                Idea.id == idea_id,
                Idea.owner_id == user.id,
                IdeaVersion.version == version,
            )
            .with_for_update(of=Idea)
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Idea version not found.")
        _idea, idea_version = record
        requirement_run = session.scalar(
            select(RequirementAnalysisRun)
            .where(
                RequirementAnalysisRun.idea_version_id == idea_version.id,
                RequirementAnalysisRun.status == "completed",
                RequirementAnalysisRun.validation_status == "valid",
                RequirementAnalysisRun.result.is_not(None),
            )
            .order_by(RequirementAnalysisRun.created_at.desc())
        )
        analysis_run = session.scalar(
            select(FeedbackAnalysisRun)
            .where(
                FeedbackAnalysisRun.idea_version_id == idea_version.id,
                FeedbackAnalysisRun.status == "completed",
                FeedbackAnalysisRun.validation_status == "valid",
                FeedbackAnalysisRun.result.is_not(None),
            )
            .order_by(FeedbackAnalysisRun.created_at.desc())
        )
        if requirement_run is None or analysis_run is None:
            raise HTTPException(
                status_code=409,
                detail="Validated requirements and completed feedback analysis are required.",
            )
        existing = session.scalar(
            select(EvolutionProposal).where(
                EvolutionProposal.idea_version_id == idea_version.id,
                EvolutionProposal.feedback_analysis_run_id == analysis_run.id,
            )
        )
        if existing is not None:
            return EvolutionProposalResponse.model_validate(existing)

        source_ids = list(analysis_run.source_feedback_ids)
        reviews = list(
            session.scalars(
                select(IdeaReview).where(
                    IdeaReview.idea_version_id == idea_version.id,
                    IdeaReview.id.in_(source_ids),
                )
            )
        )
        if not source_ids or {review.id for review in reviews} != set(source_ids):
            raise HTTPException(
                status_code=409,
                detail=(
                    "The analysis evidence no longer matches submitted reviews for this version."
                ),
            )
        try:
            suggestions = propose_evidence_changes(
                idea_version,
                RequirementSpecification.model_validate(requirement_run.result),
                FeedbackAnalysisOutput.model_validate(analysis_run.result),
                reviews,
            )
        except (ValueError, ValidationError) as error:
            raise HTTPException(
                status_code=409,
                detail="The persisted analysis inputs failed validation for evolution.",
            ) from error
        if not suggestions:
            raise HTTPException(
                status_code=409,
                detail="No ranked improvement has sufficient linked reviewer evidence.",
            )
        proposal = EvolutionProposal(
            idea_id=idea_id,
            idea_version_id=idea_version.id,
            source_version=idea_version.version,
            requirement_analysis_run_id=requirement_run.id,
            feedback_analysis_run_id=analysis_run.id,
            source_feedback_ids=source_ids,
            suggestions=[item.model_dump(mode="json") for item in suggestions],
            status="proposed",
            requested_by_id=user.id,
            provider=analysis_run.provider,
            model_version=analysis_run.model_version,
            prompt_version=EVOLUTION_PROMPT_VERSION,
            validation_results={
                "requirements_validated": True,
                "feedback_analysis_validated": True,
                "source_feedback_ids_verified": True,
                "owner_approval_required": True,
                "builder_execution": "not_started",
                "builder_isolation_available": False,
            },
        )
        session.add(proposal)
        session.commit()
        session.refresh(proposal)
        return EvolutionProposalResponse.model_validate(proposal)

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/evolution",
        response_model=EvolutionProposalResponse | None,
        tags=["Evolution"],
    )
    def get_evolution_proposal(
        idea_id: str,
        version: int,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> EvolutionProposalResponse | None:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        proposal = session.scalar(
            select(EvolutionProposal)
            .where(
                (EvolutionProposal.idea_version_id == idea_version.id)
                | (EvolutionProposal.target_version_id == idea_version.id)
            )
            .order_by(EvolutionProposal.created_at.desc())
        )
        return EvolutionProposalResponse.model_validate(proposal) if proposal else None

    @application.post(
        "/api/v1/ideas/{idea_id}/versions/{version}/evolution/{proposal_id}/approve",
        response_model=EvolutionProposalResponse,
        tags=["Evolution"],
    )
    def approve_evolution_proposal(
        idea_id: str,
        version: int,
        proposal_id: str,
        payload: EvolutionApprovalRequest,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> EvolutionProposalResponse:
        record = session.execute(
            select(Idea, IdeaVersion, EvolutionProposal)
            .join(IdeaVersion, IdeaVersion.idea_id == Idea.id)
            .join(
                EvolutionProposal,
                EvolutionProposal.idea_version_id == IdeaVersion.id,
            )
            .where(
                Idea.id == idea_id,
                Idea.owner_id == user.id,
                IdeaVersion.version == version,
                EvolutionProposal.id == proposal_id,
            )
            .with_for_update(of=Idea)
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Evolution proposal not found.")
        idea, source, proposal = record
        if proposal.status == "approved":
            approved_ranks = proposal.validation_results.get("approved_ranks", [])
            if (
                payload.expected_source_version != proposal.source_version
                or sorted(payload.selected_ranks) != sorted(approved_ranks)
            ):
                raise HTTPException(
                    status_code=409,
                    detail="This proposal was already approved with a different change selection.",
                )
            return EvolutionProposalResponse.model_validate(proposal)
        if proposal.status != "proposed":
            raise HTTPException(status_code=409, detail="This proposal is no longer approvable.")
        if payload.expected_source_version != version or idea.current_version != version:
            raise HTTPException(
                status_code=409,
                detail="The source version is stale; refresh before approving this proposal.",
            )
        selected = [
            suggestion
            for suggestion in proposal.suggestions
            if suggestion["rank"] in payload.selected_ranks
        ]
        if len(selected) != len(payload.selected_ranks):
            raise HTTPException(status_code=422, detail="A selected priority rank does not exist.")
        unsupported = [item["title"] for item in selected if not item["builder_supported"]]
        if unsupported:
            raise HTTPException(
                status_code=409,
                detail="Selected changes exceed the currently supported prototype category.",
            )
        candidate_features = list(source.features)
        for item in selected:
            if item["title"] not in candidate_features:
                candidate_features.append(item["title"])
        if len(candidate_features) > 30:
            raise HTTPException(
                status_code=409, detail="Selected changes exceed the supported feature limit."
            )

        candidate = IdeaVersion(
            idea_id=idea.id,
            created_by_id=user.id,
            source_version_id=source.id,
            version=version + 1,
            title=source.title,
            category=source.category,
            problem=source.problem,
            solution=source.solution,
            audience=source.audience,
            features=candidate_features,
            constraints=source.constraints,
            change_summary="Owner-approved evidence changes: "
            + "; ".join(
                f"{item['title']} (feedback: {', '.join(item['source_feedback_ids'])})"
                for item in selected
            ),
        )
        session.add(candidate)
        session.flush()

        source_requirement = session.get(
            RequirementAnalysisRun, proposal.requirement_analysis_run_id
        )
        if (
            source_requirement is None
            or source_requirement.status != "completed"
            or source_requirement.validation_status != "valid"
            or source_requirement.result is None
        ):
            raise HTTPException(
                status_code=409,
                detail="The validated source requirements are no longer available.",
            )
        approved_requirements = RequirementSpecification.model_validate(
            source_requirement.result
        )
        for item in selected:
            approved_requirements.core_features.append(
                RequirementFact(
                    text=item["title"],
                    basis="explicit",
                    source_fields=["features"],
                )
            )
        requirement_run = RequirementAnalysisRun(
            idea_id=idea.id,
            idea_version_id=candidate.id,
            source_version=candidate.version,
            requested_by_id=user.id,
            workflow_run_id=str(uuid4()),
            provider="owner_approved_evolution",
            model_version="not_used",
            prompt_version="evolution-approved-change-v1",
            status="completed",
            validation_status="valid",
            result=approved_requirements.model_dump(mode="json"),
            attempt_count=0,
            completed_at=datetime.now(UTC),
        )
        session.add(requirement_run)
        prior_status = idea.status
        idea.current_version = candidate.version
        idea.status = "Draft"
        proposal.status = "approved"
        proposal.approved_by_id = user.id
        proposal.approved_at = datetime.now(UTC)
        proposal.target_version_id = candidate.id
        approved_ranks = sorted(payload.selected_ranks)
        proposal.validation_results = {
            **proposal.validation_results,
            "approved_ranks": approved_ranks,
            "approved_change_titles": [item["title"] for item in selected],
            "target_version": candidate.version,
            "candidate_status": "Draft",
            "prototype_build": "pending_safe_source_generation",
            "working_prototype_validated": False,
        }
        if prior_status == "Review open":
            sequence = (
                session.scalar(
                    select(func.max(IdeaStatusEvent.sequence)).where(
                        IdeaStatusEvent.idea_id == idea.id
                    )
                )
                or 0
            ) + 1
            session.add(
                IdeaStatusEvent(
                    idea_id=idea.id,
                    changed_by_id=user.id,
                    sequence=sequence,
                    from_status="Review open",
                    to_status="Draft",
                )
            )
        session.commit()
        session.refresh(candidate)
        session.refresh(requirement_run)
        prototype = create_prototype_source(
            session,
            candidate,
            requirement_run,
            str(settings.prototype_source_storage_dir),
        )
        proposal.prototype_build_id = prototype.id
        proposal.validation_results = {
            **proposal.validation_results,
            "candidate_requirement_analysis_id": requirement_run.id,
            "prototype_build_id": prototype.id,
            "prototype_source_status": prototype.status,
            "prototype_validation_status": prototype.validation_status,
            "prototype_build_status": prototype.build_status,
            "prototype_publish_status": prototype.publish_status,
            "working_prototype_validated": False,
        }
        session.commit()
        session.refresh(proposal)
        return EvolutionProposalResponse.model_validate(proposal)

    @application.post(
        "/api/v1/ideas/{idea_id}/versions/{version}/decision-reports",
        response_model=DecisionReportResponse,
        status_code=201,
        tags=["Decision intelligence"],
    )
    def create_decision_report(
        idea_id: str,
        version: int,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> DecisionReportResponse:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        idea = session.get(Idea, idea_id)
        if idea is None:
            raise HTTPException(status_code=404, detail="Idea not found.")
        requirements = session.scalar(
            select(RequirementAnalysisRun)
            .where(RequirementAnalysisRun.idea_version_id == idea_version.id)
            .order_by(RequirementAnalysisRun.created_at.desc())
        )
        analysis_run = session.scalar(
            select(FeedbackAnalysisRun)
            .where(FeedbackAnalysisRun.idea_version_id == idea_version.id)
            .order_by(FeedbackAnalysisRun.created_at.desc())
        )
        feedback_ids = list(
            session.scalars(
                select(IdeaReview.id)
                .where(IdeaReview.idea_version_id == idea_version.id)
                .order_by(IdeaReview.created_at, IdeaReview.id)
            )
        )
        proposal = session.scalar(
            select(EvolutionProposal)
            .where(
                (EvolutionProposal.idea_version_id == idea_version.id)
                | (EvolutionProposal.target_version_id == idea_version.id)
            )
            .order_by(EvolutionProposal.created_at.desc())
        )
        prototype = session.scalar(
            select(PrototypeBuild)
            .where(PrototypeBuild.idea_version_id == idea_version.id)
            .order_by(PrototypeBuild.created_at.desc())
        )
        proposal_data = None
        if proposal is not None:
            proposal_data = {
                "proposal_id": proposal.id,
                "status": proposal.status,
                "source_version": proposal.source_version,
                "target_version_id": proposal.target_version_id,
                "suggestions": proposal.suggestions,
                "approved_changes": proposal.validation_results.get("approved_change_titles", []),
                "source_feedback_ids": proposal.source_feedback_ids,
                "validation_results": proposal.validation_results,
            }
        report = build_decision_report(
            idea,
            idea_version,
            requirements,
            analysis_run,
            proposal_data,
            prototype,
            feedback_ids,
        )
        snapshot = report_record(
            idea,
            idea_version,
            report,
            user.id,
            requirements,
            analysis_run,
            proposal.id if proposal else None,
            feedback_ids,
        )
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
        return DecisionReportResponse.model_validate(snapshot)

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/decision-reports",
        response_model=DecisionReportResponse | None,
        tags=["Decision intelligence"],
    )
    def get_latest_decision_report(
        idea_id: str,
        version: int,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> DecisionReportResponse | None:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        snapshot = session.scalar(
            select(DecisionReport)
            .where(DecisionReport.idea_version_id == idea_version.id)
            .order_by(DecisionReport.created_at.desc())
        )
        return DecisionReportResponse.model_validate(snapshot) if snapshot else None

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/feedback",
        response_model=list[ReviewResponse],
        tags=["Feedback Analysis"],
    )
    def list_persisted_feedback(
        idea_id: str,
        version: int,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> list[ReviewResponse]:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        records = session.execute(
            select(IdeaReview, FeedbackAnalysisOutbox)
            .outerjoin(
                FeedbackAnalysisOutbox,
                FeedbackAnalysisOutbox.feedback_id == IdeaReview.id,
            )
            .where(IdeaReview.idea_version_id == idea_version.id)
            .order_by(IdeaReview.created_at, IdeaReview.id)
        ).all()
        return [
            ReviewResponse(
                **_review_response_values(review),
                analysis_status=outbox.status if outbox else "pending",
                analysis_error=outbox.last_error if outbox else None,
            )
            for review, outbox in records
        ]

    @application.post(
        "/api/v1/ideas/{idea_id}/versions/{version}/requirements",
        response_model=RequirementAnalysisResponse,
        status_code=202,
        tags=["Requirements"],
    )
    def start_requirement_analysis(
        idea_id: str,
        version: int,
        request: Request,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> RequirementAnalysisResponse:
        record = session.execute(
            select(Idea, IdeaVersion)
            .join(IdeaVersion, IdeaVersion.idea_id == Idea.id)
            .where(
                Idea.id == idea_id,
                Idea.owner_id == user.id,
                IdeaVersion.version == version,
            )
            .with_for_update(of=Idea)
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Idea version not found.")
        idea, idea_version = record
        active_run = session.scalar(
            select(RequirementAnalysisRun)
            .where(
                RequirementAnalysisRun.idea_version_id == idea_version.id,
                RequirementAnalysisRun.status.in_(["queued", "running"]),
            )
            .order_by(RequirementAnalysisRun.created_at.desc())
        )
        if active_run is not None:
            return RequirementAnalysisResponse.model_validate(active_run)

        run = RequirementAnalysisRun(
            idea_id=idea.id,
            idea_version_id=idea_version.id,
            source_version=idea_version.version,
            requested_by_id=user.id,
            workflow_run_id=str(uuid4()),
            provider=settings.ai_provider,
            model_version=configured_model(settings),
            prompt_version="requirement-spec-v1",
        )
        try:
            build_chat_provider(settings)
        except ProviderConfigurationError as error:
            run.status = "failed"
            run.validation_status = "not_run"
            run.error_message = str(error)
            run.completed_at = datetime.now(UTC)
        session.add(run)
        session.commit()
        session.refresh(run)
        if run.status == "queued":
            try:
                request.app.state.requirement_dispatcher(run.id, run.workflow_run_id)
            except OperationalError:
                run.status = "failed"
                run.validation_status = "not_run"
                run.error_message = "The background worker queue is unavailable."
                run.completed_at = datetime.now(UTC)
                session.commit()
                session.refresh(run)
        return RequirementAnalysisResponse.model_validate(run)

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/requirements",
        response_model=RequirementAnalysisResponse | None,
        tags=["Requirements"],
    )
    def get_latest_requirement_analysis(
        idea_id: str,
        version: int,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> RequirementAnalysisResponse | None:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        run = session.scalar(
            select(RequirementAnalysisRun)
            .where(RequirementAnalysisRun.idea_version_id == idea_version.id)
            .order_by(RequirementAnalysisRun.created_at.desc())
        )
        return RequirementAnalysisResponse.model_validate(run) if run is not None else None

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/requirements/{analysis_id}",
        response_model=RequirementAnalysisResponse,
        tags=["Requirements"],
    )
    def get_requirement_analysis(
        idea_id: str,
        version: int,
        analysis_id: str,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> RequirementAnalysisResponse:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        run = session.scalar(
            select(RequirementAnalysisRun).where(
                RequirementAnalysisRun.id == analysis_id,
                RequirementAnalysisRun.idea_version_id == idea_version.id,
            )
        )
        if run is None:
            raise HTTPException(status_code=404, detail="Requirement analysis not found.")
        return RequirementAnalysisResponse.model_validate(run)

    @application.post(
        "/api/v1/ideas/{idea_id}/versions/{version}/prototypes",
        response_model=PrototypeBuildResponse,
        status_code=202,
        tags=["Prototype builder"],
    )
    def generate_prototype_source(
        idea_id: str,
        version: int,
        payload: PrototypeGenerationRequest,
        response: Response,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> PrototypeBuildResponse:
        record = session.execute(
            select(Idea, IdeaVersion)
            .join(IdeaVersion, IdeaVersion.idea_id == Idea.id)
            .where(
                Idea.id == idea_id,
                Idea.owner_id == user.id,
                IdeaVersion.version == version,
            )
            .with_for_update(of=Idea)
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Idea version not found.")
        idea, idea_version = record
        requirement_run = get_requirement_run_for_version(
            session,
            idea_version.id,
            payload.requirement_analysis_id,
        )
        if requirement_run is None:
            raise HTTPException(
                status_code=409,
                detail="A completed, validated Requirement Agent result is required.",
            )
        existing = session.scalar(
            select(PrototypeBuild).where(
                PrototypeBuild.requirement_analysis_run_id == requirement_run.id
            )
        )
        if existing is not None:
            response.status_code = 200
            return PrototypeBuildResponse.model_validate(existing)
        # Enqueue prototype generation as a Celery task
        from app.workers.celery_app import celery_app

        task = celery_app.send_task(
            "veridica.prototype.generate",
            args=[requirement_run.id, idea_version.id, str(settings.prototype_source_storage_dir)],
        )
        # Return 202 Accepted with task ID for status polling
        response.status_code = 202
        headers = {"X-Task-Id": task.id}
        return PrototypeBuildResponse(
            id=task.id,
            requirement_analysis_run_id=requirement_run.id,
            idea_version_id=idea_version.id,
            status="queued",
            task_id=task.id,
            created_at=datetime.now(UTC),
            **{k: v for k, v in PrototypeBuildResponse.model_fields.items() if k not in ["id", "requirement_analysis_run_id", "idea_version_id", "status", "task_id", "created_at"]},
        )

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/prototypes",
        response_model=PrototypeBuildResponse | None,
        tags=["Prototype builder"],
    )
    def get_latest_prototype_source(
        idea_id: str,
        version: int,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> PrototypeBuildResponse | None:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        build = session.scalar(
            select(PrototypeBuild)
            .where(PrototypeBuild.idea_version_id == idea_version.id)
            .order_by(PrototypeBuild.created_at.desc())
        )
        return PrototypeBuildResponse.model_validate(build) if build is not None else None

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/prototypes/{prototype_id}",
        response_model=PrototypeBuildResponse,
        tags=["Prototype builder"],
    )
    def get_prototype_source_record(
        idea_id: str,
        version: int,
        prototype_id: str,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> PrototypeBuildResponse:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        build = session.scalar(
            select(PrototypeBuild).where(
                PrototypeBuild.id == prototype_id,
                PrototypeBuild.idea_version_id == idea_version.id,
            )
        )
        if build is None:
            raise HTTPException(status_code=404, detail="Prototype source not found.")
        return PrototypeBuildResponse.model_validate(build)

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/prototypes/{prototype_id}/source",
        response_model=PrototypeSourceResponse,
        tags=["Prototype builder"],
    )
    def get_prototype_source_files(
        idea_id: str,
        version: int,
        prototype_id: str,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> PrototypeSourceResponse:
        idea_version = _owned_idea_version(session, idea_id, version, user.id)
        build = session.scalar(
            select(PrototypeBuild).where(
                PrototypeBuild.id == prototype_id,
                PrototypeBuild.idea_version_id == idea_version.id,
            )
        )
        if build is None:
            raise HTTPException(status_code=404, detail="Prototype source not found.")
        if build.status != "source_generated" or build.source_storage_key is None:
            raise HTTPException(
                status_code=409,
                detail="Generated source is unavailable because static validation did not pass.",
            )
        try:
            files = read_source_files(
                str(settings.prototype_source_storage_dir),
                build.source_storage_key,
                build.source_files,
            )
        except (FileNotFoundError, PrototypeValidationError):
            mark_source_missing(session, build)
            raise HTTPException(
                status_code=410,
                detail="Generated source is missing or failed integrity verification.",
            ) from None
        return PrototypeSourceResponse(prototype_build_id=build.id, files=files)

    @application.post(
        "/api/v1/ideas/{idea_id}/versions",
        response_model=IdeaResponse,
        status_code=201,
        tags=["Ideas"],
    )
    def create_idea_version(
        idea_id: str,
        payload: IdeaVersionCreate,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> IdeaResponse:
        return _create_idea_version(idea_id, payload, user, session)

    @application.put(
        "/api/v1/ideas/{idea_id}",
        response_model=IdeaResponse,
        status_code=201,
        tags=["Ideas"],
    )
    def update_idea(
        idea_id: str,
        payload: IdeaVersionCreate,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> IdeaResponse:
        return _create_idea_version(idea_id, payload, user, session)

    @application.patch(
        "/api/v1/ideas/{idea_id}",
        response_model=IdeaResponse,
        tags=["Ideas"],
    )
    def transition_idea(
        idea_id: str,
        payload: IdeaStatusUpdate,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> IdeaResponse:
        idea = session.scalar(
            select(Idea)
            .where(Idea.id == idea_id, Idea.owner_id == user.id)
            .with_for_update()
        )
        if idea is None:
            raise HTTPException(status_code=404, detail="Idea not found.")
        allowed = {
            ("Draft", "Archived"),
            ("Archived", "Draft"),
        }
        if (idea.status, payload.status) not in allowed:
            raise HTTPException(
                status_code=409,
                detail="Only draft ideas can be archived, and only archived ideas can be restored.",
            )
        if payload.status == "Archived":
            active_assignment = session.scalar(
                select(ReviewerAssignment.id)
                .join(IdeaVersion, ReviewerAssignment.idea_version_id == IdeaVersion.id)
                .where(
                    IdeaVersion.idea_id == idea.id,
                    ReviewerAssignment.active.is_(True),
                )
                .limit(1)
            )
            if active_assignment is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Revoke active reviewer assignments before archiving this idea.",
                )
        previous_status = idea.status
        idea.status = payload.status
        next_sequence = (
            session.scalar(
                select(func.max(IdeaStatusEvent.sequence)).where(
                    IdeaStatusEvent.idea_id == idea.id
                )
            )
            or 0
        ) + 1
        session.add(
            IdeaStatusEvent(
                idea_id=idea.id,
                changed_by_id=user.id,
                sequence=next_sequence,
                from_status=previous_status,
                to_status=payload.status,
            )
        )
        session.commit()
        session.refresh(idea)
        version = session.scalar(
            select(IdeaVersion).where(
                IdeaVersion.idea_id == idea.id,
                IdeaVersion.version == idea.current_version,
            )
        )
        if version is None:
            raise HTTPException(status_code=500, detail="The current idea version is missing.")
        return _idea_response(idea, version)

    @application.post(
        "/api/v1/ideas/{idea_id}/versions/{version}/assets",
        response_model=IdeaResponse,
        status_code=201,
        tags=["Idea assets"],
    )
    async def upload_idea_asset(
        idea_id: str,
        version: int,
        request: Request,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
        filename: Annotated[str, Query(min_length=1, max_length=255)],
    ) -> IdeaResponse:
        record = session.execute(
            select(Idea, IdeaVersion)
            .join(IdeaVersion, IdeaVersion.idea_id == Idea.id)
            .where(
                Idea.id == idea_id,
                Idea.owner_id == user.id,
                IdeaVersion.version == version,
            )
            .with_for_update()
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Idea version not found.")
        idea, idea_version = record
        if idea.status != "Draft" or idea.current_version != version:
            raise HTTPException(
                status_code=409, detail="Assets can only be added to the current draft version."
            )
        safe_name, content_type, size_bytes, sha256, storage_key = await store_private_asset(
            request, filename, settings.idea_asset_storage_dir
        )
        asset = IdeaAsset(
            idea_version_id=idea_version.id,
            filename=safe_name,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256,
            storage_key=storage_key,
        )
        session.add(asset)
        try:
            session.commit()
        except Exception:
            session.rollback()
            (settings.idea_asset_storage_dir / storage_key).unlink(missing_ok=True)
            raise
        session.refresh(asset)
        session.refresh(idea_version)
        return _idea_response(idea, idea_version)

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}/assets/{asset_id}",
        tags=["Idea assets"],
    )
    def download_idea_asset(
        idea_id: str,
        version: int,
        asset_id: str,
        user: Annotated[User, Depends(require_role("owner", "reviewer"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> FileResponse:
        record = session.execute(
            select(IdeaAsset, IdeaVersion, Idea)
            .join(IdeaVersion, IdeaAsset.idea_version_id == IdeaVersion.id)
            .join(Idea, IdeaVersion.idea_id == Idea.id)
            .where(
                IdeaAsset.id == asset_id,
                Idea.id == idea_id,
                IdeaVersion.version == version,
            )
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Asset not found.")
        asset, idea_version, idea = record
        if user.role == "owner":
            if idea.owner_id != user.id:
                raise HTTPException(status_code=404, detail="Asset not found.")
        elif session.scalar(
            select(ReviewerAssignment.id).where(
                ReviewerAssignment.reviewer_id == user.id,
                ReviewerAssignment.idea_version_id == idea_version.id,
                ReviewerAssignment.active.is_(True),
            )
        ) is None:
            raise HTTPException(status_code=404, detail="Asset not found.")
        path = settings.idea_asset_storage_dir / asset.storage_key
        if not path.is_file():
            raise HTTPException(status_code=503, detail="Private asset storage is unavailable.")
        return FileResponse(
            path,
            media_type="application/octet-stream",
            filename=asset.filename,
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @application.get(
        "/api/v1/ideas/{idea_id}/versions/{version}",
        response_model=IdeaResponse,
        tags=["Ideas"],
    )
    def get_idea_version(
        idea_id: str,
        version: int,
        user: Annotated[User, Depends(require_role("owner", "reviewer"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> IdeaResponse:
        record = session.execute(
            select(Idea, IdeaVersion)
            .join(IdeaVersion, IdeaVersion.idea_id == Idea.id)
            .where(Idea.id == idea_id, IdeaVersion.version == version)
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Idea version not found.")
        idea, idea_version = record
        if user.role == "owner" and idea.owner_id == user.id:
            return _idea_response(idea, idea_version)
        if user.role == "reviewer":
            assigned = session.scalar(
                select(ReviewerAssignment.id).where(
                    ReviewerAssignment.reviewer_id == user.id,
                    ReviewerAssignment.idea_version_id == idea_version.id,
                    ReviewerAssignment.active.is_(True),
                )
            )
            if assigned is not None:
                return _idea_response(idea, idea_version)
        raise HTTPException(status_code=404, detail="Idea version not found.")

    @application.post(
        "/api/v1/ideas/{idea_id}/versions/{version}/publish",
        response_model=ReviewCycleResponse,
        status_code=201,
        tags=["Review cycles"],
    )
    def publish_idea_version(
        idea_id: str,
        version: int,
        user: Annotated[User, Depends(require_role("owner"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> ReviewCycleResponse:
        record = session.execute(
            select(Idea, IdeaVersion)
            .join(IdeaVersion, IdeaVersion.idea_id == Idea.id)
            .where(
                Idea.id == idea_id,
                Idea.owner_id == user.id,
                IdeaVersion.version == version,
            )
            .with_for_update()
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Idea version not found.")
        idea, idea_version = record
        if idea.status == "Archived":
            raise HTTPException(status_code=409, detail="Restore the idea before publishing.")
        cycle = session.scalar(
            select(ReviewCycle)
            .where(ReviewCycle.idea_version_id == idea_version.id)
            .with_for_update()
        )
        if cycle is not None:
            if cycle.status != "open":
                raise HTTPException(
                    status_code=409, detail="This idea version's review cycle is closed."
                )
            return _review_cycle_response(cycle, idea, idea_version)
        if idea.status not in {"Draft", "Review open"}:
            raise HTTPException(
                status_code=409,
                detail="Only draft or already-published ideas can open a review cycle.",
            )
        cycle = ReviewCycle(
            idea_version_id=idea_version.id,
            opened_by_id=user.id,
            status="open",
        )
        session.add(cycle)
        if idea.status == "Draft":
            idea.status = "Review open"
            sequence = (
                session.scalar(
                    select(func.max(IdeaStatusEvent.sequence)).where(
                        IdeaStatusEvent.idea_id == idea.id
                    )
                )
                or 0
            ) + 1
            session.add(
                IdeaStatusEvent(
                    idea_id=idea.id,
                    changed_by_id=user.id,
                    sequence=sequence,
                    from_status="Draft",
                    to_status="Review open",
                )
            )
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                status_code=409, detail="A review cycle already exists for this version."
            ) from error
        session.refresh(cycle)
        return _review_cycle_response(cycle, idea, idea_version)

    @application.get(
        "/api/v1/reviewer/assignments",
        response_model=list[ReviewerAssignmentResponse],
        tags=["Reviewer"],
    )
    def list_reviewer_assignments(
        user: Annotated[User, Depends(require_role("reviewer"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> list[ReviewerAssignmentResponse]:
        records = session.execute(
            select(ReviewerAssignment, Idea, IdeaVersion, IdeaReview)
            .join(IdeaVersion, ReviewerAssignment.idea_version_id == IdeaVersion.id)
            .join(Idea, IdeaVersion.idea_id == Idea.id)
            .outerjoin(IdeaReview, IdeaReview.assignment_id == ReviewerAssignment.id)
            .where(
                ReviewerAssignment.reviewer_id == user.id,
                ReviewerAssignment.active.is_(True),
            )
            .order_by(ReviewerAssignment.assigned_at.desc())
        ).all()
        return [
            _reviewer_assignment_response(assignment, idea, version, review, session)
            for assignment, idea, version, review in records
        ]

    @application.get(
        "/api/v1/reviewer/assignments/{assignment_id}",
        response_model=ReviewerAssignmentResponse,
        tags=["Reviewer"],
    )
    def get_reviewer_assignment(
        assignment_id: str,
        user: Annotated[User, Depends(require_role("reviewer"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> ReviewerAssignmentResponse:
        record = _reviewer_assignment_record(session, assignment_id, user.id)
        if record is None:
            raise HTTPException(status_code=404, detail="Assignment not found.")
        assignment, idea, version, review = record
        return _reviewer_assignment_response(assignment, idea, version, review, session)

    @application.get(
        "/api/v1/reviewer/assignments/{assignment_id}/prototype",
        response_model=ReviewerPrototypePreviewResponse | None,
        tags=["Reviewer"],
    )
    def get_reviewer_prototype_preview(
        assignment_id: str,
        user: Annotated[User, Depends(require_role("reviewer"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> ReviewerPrototypePreviewResponse | None:
        record = _reviewer_assignment_record(session, assignment_id, user.id)
        if record is None:
            raise HTTPException(status_code=404, detail="Assignment not found.")
        assignment, _idea, version, _review = record
        build = session.scalar(
            select(PrototypeBuild)
            .where(PrototypeBuild.idea_version_id == assignment.idea_version_id)
            .order_by(PrototypeBuild.created_at.desc())
        )
        if build is None or build.status != "source_generated" or build.validation_status != "passed":
            return None
        try:
            preview_spec = PrototypePreviewSpec.model_validate(
                (build.plan or {}).get("preview_spec")
            )
        except ValidationError as error:
            raise HTTPException(
                status_code=500,
                detail="The saved prototype preview specification failed validation.",
            ) from error
        return ReviewerPrototypePreviewResponse(
            prototype_build_id=build.id,
            idea_version_id=version.id,
            source_version=version.version,
            requirement_analysis_run_id=build.requirement_analysis_run_id,
            preview_spec=preview_spec,
        )

    @application.post(
        "/api/v1/reviewer/assignments/{assignment_id}/sessions",
        response_model=ReviewSessionResponse,
        status_code=201,
        tags=["Reviewer"],
    )
    def start_review_session(
        assignment_id: str,
        user: Annotated[User, Depends(require_role("reviewer"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> ReviewSessionResponse:
        assignment = session.scalar(
            select(ReviewerAssignment)
            .where(
                ReviewerAssignment.id == assignment_id,
                ReviewerAssignment.reviewer_id == user.id,
                ReviewerAssignment.active.is_(True),
            )
            .with_for_update()
        )
        if assignment is None:
            raise HTTPException(status_code=404, detail="Assignment not found.")
        existing = session.scalar(
            select(ReviewSession).where(ReviewSession.assignment_id == assignment.id)
        )
        if existing is not None:
            return ReviewSessionResponse.model_validate(existing)
        if assignment.status != "assigned":
            raise HTTPException(status_code=409, detail="This assignment cannot be started.")
        cycle = session.get(ReviewCycle, assignment.review_cycle_id)
        if cycle is None or cycle.status != "open":
            raise HTTPException(status_code=409, detail="This review cycle is no longer open.")
        record = session.execute(
            select(IdeaVersion, Idea)
            .join(Idea, IdeaVersion.idea_id == Idea.id)
            .where(IdeaVersion.id == assignment.idea_version_id)
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Assigned idea version not found.")
        idea_version, idea = record
        review_session = ReviewSession(
            assignment_id=assignment.id,
            idea_id=idea.id,
            idea_version_id=idea_version.id,
            reviewer_id=user.id,
            status="in_progress",
        )
        assignment.status = "in_progress"
        assignment.started_at = datetime.now(UTC)
        session.add(review_session)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            existing = session.scalar(
                select(ReviewSession).where(ReviewSession.assignment_id == assignment_id)
            )
            if existing is None:
                raise HTTPException(
                    status_code=409, detail="The review session could not be started."
                ) from error
            return ReviewSessionResponse.model_validate(existing)
        session.refresh(review_session)
        return ReviewSessionResponse.model_validate(review_session)

    @application.post(
        "/api/v1/reviewer/assignments/{assignment_id}/reviews",
        response_model=ReviewResponse,
        status_code=201,
        tags=["Reviewer"],
    )
    def submit_review(
        assignment_id: str,
        payload: ReviewSubmission,
        request: Request,
        idempotency_key: Annotated[
            str, Header(alias="Idempotency-Key", min_length=16, max_length=128)
        ],
        user: Annotated[User, Depends(require_role("reviewer"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> Response:
        assignment = session.scalar(
            select(ReviewerAssignment)
            .where(
                ReviewerAssignment.id == assignment_id,
                ReviewerAssignment.reviewer_id == user.id,
                ReviewerAssignment.active.is_(True),
            )
            .with_for_update()
        )
        if assignment is None:
            raise HTTPException(status_code=404, detail="Assignment not found.")
        existing = session.scalar(
            select(IdeaReview).where(
                IdeaReview.assignment_id == assignment.id,
                IdeaReview.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if not _review_matches_payload(existing, payload):
                raise HTTPException(
                    status_code=409,
                    detail="The idempotency key was already used with different feedback.",
                )
            outbox = session.scalar(
                select(FeedbackAnalysisOutbox).where(
                    FeedbackAnalysisOutbox.feedback_id == existing.id
                )
            )
            if outbox is not None and outbox.status == "pending":
                _dispatch_feedback_analysis(request, session, outbox)
            session.refresh(existing)
            outbox = session.scalar(
                select(FeedbackAnalysisOutbox).where(
                    FeedbackAnalysisOutbox.feedback_id == existing.id
                )
            )
            return Response(
                content=ReviewResponse(
                    **_review_response_values(existing),
                    analysis_status=outbox.status if outbox else "pending",
                    analysis_error=outbox.last_error if outbox else None,
                ).model_dump_json(),
                status_code=200,
                media_type="application/json",
            )
        if assignment.status != "in_progress":
            raise HTTPException(
                status_code=409, detail="Start this assigned review session before submitting."
            )
        cycle = session.get(ReviewCycle, assignment.review_cycle_id)
        if cycle is None or cycle.status != "open":
            raise HTTPException(status_code=409, detail="This review cycle is no longer open.")
        review_session = session.scalar(
            select(ReviewSession).where(
                ReviewSession.id == payload.session_id,
                ReviewSession.assignment_id == assignment.id,
                ReviewSession.reviewer_id == user.id,
            )
        )
        if (
            review_session is None
            or review_session.idea_version_id != assignment.idea_version_id
            or review_session.status != "in_progress"
        ):
            raise HTTPException(status_code=404, detail="Review session not found.")
        version = session.get(IdeaVersion, assignment.idea_version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="Assigned idea version not found.")
        review = IdeaReview(
            assignment_id=assignment.id,
            idea_id=version.idea_id,
            idea_version_id=version.id,
            reviewer_id=user.id,
            review_session_id=review_session.id,
            idempotency_key=idempotency_key,
            rating=payload.rating,
            feedback=payload.feedback_text,
            usability_score=payload.usability_score,
            usefulness_score=payload.usefulness_score,
            completeness_score=payload.completeness_score,
            feasibility_score=payload.feasibility_score,
            would_use=payload.would_use,
            strengths=payload.strengths,
            concerns=payload.concerns,
            suggested_improvements=payload.suggested_improvements,
            usage_context=payload.usage_context,
        )
        review_session.status = "submitted"
        review_session.completed_at = datetime.now(UTC)
        assignment.status = "submitted"
        assignment.completed_at = review_session.completed_at
        session.add(review)
        try:
            session.flush()
            outbox = FeedbackAnalysisOutbox(feedback_id=review.id, status="pending")
            session.add(outbox)
            session.commit()
        except IntegrityError as error:
            session.rollback()
            existing = session.scalar(
                select(IdeaReview).where(IdeaReview.assignment_id == assignment_id)
            )
            if existing is not None and existing.idempotency_key == idempotency_key:
                if not _review_matches_payload(existing, payload):
                    raise HTTPException(
                        status_code=409,
                        detail="The idempotency key was already used with different feedback.",
                    ) from error
                outbox = session.scalar(
                    select(FeedbackAnalysisOutbox).where(
                        FeedbackAnalysisOutbox.feedback_id == existing.id
                    )
                )
                if outbox is not None and outbox.status == "pending":
                    _dispatch_feedback_analysis(request, session, outbox)
                return Response(
                    content=ReviewResponse(
                        **_review_response_values(existing),
                        analysis_status=outbox.status if outbox else "pending",
                        analysis_error=outbox.last_error if outbox else None,
                    ).model_dump_json(),
                    status_code=200,
                    media_type="application/json",
                )
            raise HTTPException(
                status_code=409,
                detail="Feedback has already been submitted for this assignment.",
            ) from error
        session.refresh(review)
        outbox = session.get(FeedbackAnalysisOutbox, outbox.id)
        if outbox is None:
            raise HTTPException(status_code=500, detail="The feedback analysis request is missing.")
        _dispatch_feedback_analysis(request, session, outbox)
        session.refresh(review)
        session.refresh(outbox)
        return Response(
            content=ReviewResponse(
                **_review_response_values(review),
                analysis_status=outbox.status,
                analysis_error=outbox.last_error,
            ).model_dump_json(),
            status_code=201,
            media_type="application/json",
        )

    @application.get(
        "/api/v1/admin/assignments",
        response_model=list[AdminAssignmentResponse],
        tags=["Admin"],
    )
    def list_admin_assignments(
        _admin: Annotated[User, Depends(require_role("admin"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> list[AdminAssignmentResponse]:
        records = session.execute(
            select(ReviewerAssignment, Idea, IdeaVersion, User, IdeaReview)
            .join(IdeaVersion, ReviewerAssignment.idea_version_id == IdeaVersion.id)
            .join(Idea, IdeaVersion.idea_id == Idea.id)
            .join(User, ReviewerAssignment.reviewer_id == User.id)
            .outerjoin(IdeaReview, IdeaReview.assignment_id == ReviewerAssignment.id)
            .order_by(ReviewerAssignment.assigned_at.desc())
        ).all()
        return [
            _admin_assignment_response(assignment, idea, version, reviewer, review is not None)
            for assignment, idea, version, reviewer, review in records
        ]

    @application.post(
        "/api/v1/admin/assignments",
        response_model=AdminAssignmentResponse,
        status_code=201,
        tags=["Admin"],
    )
    def create_admin_assignment(
        payload: AdminAssignmentCreate,
        admin: Annotated[User, Depends(require_role("admin"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> AdminAssignmentResponse:
        reviewer = session.scalar(
            select(User).where(User.email == payload.reviewer_email, User.role == "reviewer")
        )
        record = session.execute(
            select(Idea, IdeaVersion)
            .join(IdeaVersion, IdeaVersion.idea_id == Idea.id)
            .where(Idea.id == payload.idea_id, IdeaVersion.version == payload.version)
        ).first()
        if reviewer is None or record is None:
            raise HTTPException(status_code=404, detail="Idea version or reviewer not found.")
        idea, version = record
        review_cycle = session.scalar(
            select(ReviewCycle).where(
                ReviewCycle.idea_version_id == version.id,
                ReviewCycle.status == "open",
            )
        )
        if review_cycle is None:
            raise HTTPException(
                status_code=409,
                detail="Publish this exact idea version before assigning reviewers.",
            )
        if idea.status == "Archived":
            raise HTTPException(
                status_code=409,
                detail="Restore the idea before assigning reviewers.",
            )
        assignment = session.scalar(
            select(ReviewerAssignment).where(
                ReviewerAssignment.idea_version_id == version.id,
                ReviewerAssignment.reviewer_id == reviewer.id,
            )
        )
        if assignment is not None and assignment.active:
            raise HTTPException(status_code=409, detail="Reviewer is already assigned.")
        if assignment is not None and session.scalar(
            select(ReviewSession.id).where(ReviewSession.assignment_id == assignment.id)
        ):
            raise HTTPException(
                status_code=409,
                detail="A started or completed assignment cannot be reassigned.",
            )
        if assignment is None:
            assignment = ReviewerAssignment(
                idea_version_id=version.id,
                reviewer_id=reviewer.id,
                assigned_by_id=admin.id,
                review_cycle_id=review_cycle.id,
                status="assigned",
            )
            session.add(assignment)
        else:
            assignment.active = True
            assignment.status = "assigned"
            assignment.assigned_at = datetime.now(UTC)
            assignment.review_cycle_id = review_cycle.id
            assignment.revoked_at = None
            assignment.revoked_by_id = None
            assignment.assigned_by_id = admin.id
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(status_code=409, detail="Reviewer is already assigned.") from error
        session.refresh(assignment)
        return _admin_assignment_response(assignment, idea, version, reviewer, False)

    @application.delete(
        "/api/v1/admin/assignments/{assignment_id}",
        response_model=AdminAssignmentResponse,
        tags=["Admin"],
    )
    def revoke_admin_assignment(
        assignment_id: str,
        admin: Annotated[User, Depends(require_role("admin"))],
        session: Annotated[Session, Depends(request_session)],
    ) -> AdminAssignmentResponse:
        record = session.execute(
            select(ReviewerAssignment, Idea, IdeaVersion, User, IdeaReview)
            .join(IdeaVersion, ReviewerAssignment.idea_version_id == IdeaVersion.id)
            .join(Idea, IdeaVersion.idea_id == Idea.id)
            .join(User, ReviewerAssignment.reviewer_id == User.id)
            .outerjoin(IdeaReview, IdeaReview.assignment_id == ReviewerAssignment.id)
            .where(ReviewerAssignment.id == assignment_id)
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Assignment not found.")
        assignment, idea, version, reviewer, review = record
        if assignment.active:
            assignment.active = False
            assignment.status = "revoked"
            assignment.revoked_at = datetime.now(UTC)
            assignment.revoked_by_id = admin.id
            session.commit()
        return _admin_assignment_response(assignment, idea, version, reviewer, review is not None)

    @application.get("/api/v1/health/ready", response_model=Readiness, tags=["Health"])
    def ready(response: Response) -> Readiness:
        checks = {
            "postgres": health.check_postgres(settings),
            "redis": health.check_redis(settings),
        }
        available = all(checks.values())
        response.status_code = 200 if available else 503
        return Readiness(
            status="ready" if available else "unavailable",
            services={
                name: "connected" if connected else "unavailable"
                for name, connected in checks.items()
            },
        )

    return application


def _create_idea_version(
    idea_id: str,
    payload: IdeaVersionCreate,
    user: User,
    session: Session,
) -> IdeaResponse:
    idea = session.scalar(
        select(Idea)
        .where(Idea.id == idea_id, Idea.owner_id == user.id)
        .with_for_update()
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found.")
    if idea.status == "Archived":
        raise HTTPException(status_code=409, detail="Restore the idea before creating a version.")
    if payload.expected_version != idea.current_version:
        raise HTTPException(
            status_code=409,
            detail="The idea changed since this version was loaded. Refresh and try again.",
        )
    source = session.scalar(
        select(IdeaVersion).where(
            IdeaVersion.idea_id == idea.id,
            IdeaVersion.version == idea.current_version,
        )
    )
    if source is None:
        raise HTTPException(status_code=500, detail="The current idea version is missing.")
    next_version = idea.current_version + 1
    previous_status = idea.status
    version = _version_from_payload(
        payload,
        version=next_version,
        created_by_id=user.id,
        source_version_id=source.id,
        change_summary=payload.change_summary,
    )
    idea.current_version = next_version
    idea.status = "Draft"
    idea.versions.append(version)
    if previous_status == "Review open":
        sequence = (
            session.scalar(
                select(func.max(IdeaStatusEvent.sequence)).where(
                    IdeaStatusEvent.idea_id == idea.id
                )
            )
            or 0
        ) + 1
        session.add(
            IdeaStatusEvent(
                idea_id=idea.id,
                changed_by_id=user.id,
                sequence=sequence,
                from_status="Review open",
                to_status="Draft",
            )
        )
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="The idea was updated concurrently; refresh and retry."
        ) from error
    session.refresh(idea)
    session.refresh(version)
    return _idea_response(idea, version)


def _version_from_payload(
    payload: IdeaCreate,
    version: int,
    created_by_id: str,
    source_version_id: str | None,
    change_summary: str,
) -> IdeaVersion:
    return IdeaVersion(
        created_by_id=created_by_id,
        source_version_id=source_version_id,
        version=version,
        title=payload.title.strip(),
        category=payload.category.strip(),
        problem=payload.problem.strip(),
        solution=payload.solution.strip(),
        audience=payload.audience.strip(),
        features=list(payload.features),
        constraints=payload.constraints.strip(),
        change_summary=change_summary,
    )


def _idea_response(idea: Idea, version: IdeaVersion) -> IdeaResponse:
    return IdeaResponse(
        id=idea.id,
        owner_id=idea.owner_id,
        version_id=version.id,
        source_version_id=version.source_version_id,
        created_by_id=version.created_by_id,
        change_summary=version.change_summary,
        title=version.title,
        category=version.category,
        problem=version.problem,
        solution=version.solution,
        audience=version.audience,
        features=version.features,
        constraints=version.constraints,
        version=version.version,
        status=idea.status,
        created_at=idea.created_at,
        updated_at=idea.updated_at,
        version_created_at=version.created_at,
        assets=[
            {
                "id": asset.id,
                "idea_version_id": asset.idea_version_id,
                "filename": asset.filename,
                "content_type": asset.content_type,
                "size_bytes": asset.size_bytes,
                "sha256": asset.sha256,
                "created_at": asset.created_at,
            }
            for asset in version.assets
        ],
    )


def _auth_response(user: User, settings: Settings) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(
            user.id, user.role, settings.jwt_secret, settings.access_token_minutes
        ),
        user=UserResponse.model_validate(user),
    )


def _reviewer_assignment_record(
    session: Session, assignment_id: str, reviewer_id: str
) -> tuple[ReviewerAssignment, Idea, IdeaVersion, IdeaReview | None] | None:
    return session.execute(
        select(ReviewerAssignment, Idea, IdeaVersion, IdeaReview)
        .join(IdeaVersion, ReviewerAssignment.idea_version_id == IdeaVersion.id)
        .join(Idea, IdeaVersion.idea_id == Idea.id)
        .outerjoin(IdeaReview, IdeaReview.assignment_id == ReviewerAssignment.id)
        .where(
            ReviewerAssignment.id == assignment_id,
            ReviewerAssignment.reviewer_id == reviewer_id,
            ReviewerAssignment.active.is_(True),
        )
    ).first()


def _reviewer_assignment_response(
    assignment: ReviewerAssignment,
    idea: Idea,
    version: IdeaVersion,
    review: IdeaReview | None,
    session: Session,
) -> ReviewerAssignmentResponse:
    review_session = session.scalar(
        select(ReviewSession).where(ReviewSession.assignment_id == assignment.id)
    )
    feedback = None
    if review is not None:
        outbox = session.scalar(
            select(FeedbackAnalysisOutbox).where(
                FeedbackAnalysisOutbox.feedback_id == review.id
            )
        )
        feedback = ReviewResponse(
            **_review_response_values(review),
            analysis_status=outbox.status if outbox else "pending",
            analysis_error=outbox.last_error if outbox else None,
        )
    return ReviewerAssignmentResponse(
        id=assignment.id,
        idea_id=idea.id,
        idea_title=version.title,
        version=version.version,
        problem=version.problem,
        solution=version.solution,
        audience=version.audience,
        features=version.features,
        constraints=version.constraints,
        assigned_at=assignment.assigned_at,
        started_at=assignment.started_at,
        completed_at=assignment.completed_at,
        status=assignment.status,
        review_submitted=review is not None,
        review_session=(
            ReviewSessionResponse.model_validate(review_session)
            if review_session is not None
            else None
        ),
        feedback=feedback,
        assets=[
            {
                "id": asset.id,
                "idea_version_id": asset.idea_version_id,
                "filename": asset.filename,
                "content_type": asset.content_type,
                "size_bytes": asset.size_bytes,
                "sha256": asset.sha256,
                "created_at": asset.created_at,
            }
            for asset in version.assets
        ],
    )


def _admin_assignment_response(
    assignment: ReviewerAssignment,
    idea: Idea,
    version: IdeaVersion,
    reviewer: User,
    review_submitted: bool,
) -> AdminAssignmentResponse:
    return AdminAssignmentResponse(
        id=assignment.id,
        idea_id=idea.id,
        idea_title=version.title,
        version=version.version,
        reviewer_email=reviewer.email,
        active=assignment.active,
        status=assignment.status,
        assigned_at=assignment.assigned_at,
        started_at=assignment.started_at,
        completed_at=assignment.completed_at,
        revoked_at=assignment.revoked_at,
        review_submitted=review_submitted,
    )


def _review_cycle_response(
    cycle: ReviewCycle, idea: Idea, version: IdeaVersion
) -> ReviewCycleResponse:
    return ReviewCycleResponse(
        id=cycle.id,
        idea_id=idea.id,
        idea_version_id=version.id,
        version=version.version,
        status=cycle.status,
        opened_by_id=cycle.opened_by_id,
        opened_at=cycle.opened_at,
        closed_at=cycle.closed_at,
    )


def _review_response_values(review: IdeaReview) -> dict:
    return {
        "id": review.id,
        "assignment_id": review.assignment_id,
        "idea_id": review.idea_id,
        "idea_version_id": review.idea_version_id,
        "reviewer_id": review.reviewer_id,
        "review_session_id": review.review_session_id,
        "idempotency_key": review.idempotency_key,
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
        "created_at": review.created_at,
    }


def _owned_idea_version(
    session: Session, idea_id: str, version: int, owner_id: str
) -> IdeaVersion:
    idea_version = session.scalar(
        select(IdeaVersion)
        .join(Idea, IdeaVersion.idea_id == Idea.id)
        .where(
            Idea.id == idea_id,
            Idea.owner_id == owner_id,
            IdeaVersion.version == version,
        )
    )
    if idea_version is None:
        raise HTTPException(status_code=404, detail="Idea version not found.")
    return idea_version


def _review_matches_payload(review: IdeaReview, payload: ReviewSubmission) -> bool:
    return (
        review.review_session_id == payload.session_id
        and review.rating == payload.rating
        and review.usability_score == payload.usability_score
        and review.usefulness_score == payload.usefulness_score
        and review.completeness_score == payload.completeness_score
        and review.feasibility_score == payload.feasibility_score
        and review.would_use == payload.would_use
        and review.feedback == payload.feedback_text
        and review.strengths == payload.strengths
        and review.concerns == payload.concerns
        and review.suggested_improvements == payload.suggested_improvements
        and review.usage_context == payload.usage_context
    )


def _dispatch_feedback_analysis(
    request: Request, session: Session, outbox: FeedbackAnalysisOutbox
) -> None:
    if outbox.status != "pending":
        return
    outbox.attempt_count += 1
    outbox.last_attempt_at = datetime.now(UTC)
    session.commit()
    session.refresh(outbox)
    try:
        request.app.state.feedback_dispatcher(outbox.id)
    except OperationalError:
        latest = session.scalar(
            select(FeedbackAnalysisOutbox)
            .where(FeedbackAnalysisOutbox.id == outbox.id)
            .with_for_update()
        )
        if latest is not None and latest.status != "received":
            latest.status = "pending"
            latest.last_error = "The background queue is unavailable; retry submission safely."
            session.commit()
        return
    latest = session.scalar(
        select(FeedbackAnalysisOutbox)
        .where(FeedbackAnalysisOutbox.id == outbox.id)
        .with_for_update()
    )
    if latest is not None and latest.status == "pending":
        latest.status = "queued"
        latest.last_error = None
        session.commit()


app = create_app()