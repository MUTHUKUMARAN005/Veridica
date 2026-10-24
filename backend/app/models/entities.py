from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'reviewer', 'admin')", name="ck_users_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ideas: Mapped[list["Idea"]] = relationship(back_populates="owner")


class RoleChangeEvent(Base):
    __tablename__ = "role_change_events"
    __table_args__ = (
        CheckConstraint(
            "previous_role IN ('owner', 'reviewer', 'admin')",
            name="ck_role_change_events_previous_role",
        ),
        CheckConstraint(
            "new_role IN ('owner', 'reviewer', 'admin')",
            name="ck_role_change_events_new_role",
        ),
        CheckConstraint("previous_role <> new_role", name="ck_role_change_events_role_changed"),
        CheckConstraint("length(trim(reason)) > 0", name="ck_role_change_events_reason_nonempty"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    target_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    previous_role: Mapped[str] = mapped_column(String(20), nullable=False)
    new_role: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Idea(Base):
    __tablename__ = "ideas"
    __table_args__ = (
        CheckConstraint("current_version >= 1", name="ck_ideas_current_version_positive"),
        CheckConstraint(
            "status IN ('Draft', 'Ready for review', 'Review open', 'Evolution ready', 'Archived')",
            name="ck_ideas_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    owner: Mapped[User] = relationship(back_populates="ideas")
    versions: Mapped[list["IdeaVersion"]] = relationship(
        back_populates="idea", cascade="all, delete-orphan", order_by="IdeaVersion.version"
    )
    status_events: Mapped[list["IdeaStatusEvent"]] = relationship(
        back_populates="idea", order_by="IdeaStatusEvent.created_at"
    )


class IdeaStatusEvent(Base):
    __tablename__ = "idea_status_events"
    __table_args__ = (
        UniqueConstraint(
            "idea_id", "sequence", name="uq_idea_status_events_idea_sequence"
        ),
        CheckConstraint("sequence >= 1", name="ck_idea_status_events_sequence_positive"),
        CheckConstraint(
            "to_status IN ('Draft', 'Ready for review', 'Review open', "
            "'Evolution ready', 'Archived')",
            name="ck_idea_status_events_to_status",
        ),
        CheckConstraint(
            "from_status IS NULL OR "
            "(from_status = 'Draft' AND to_status = 'Archived') OR "
            "(from_status = 'Archived' AND to_status = 'Draft') OR "
            "(from_status = 'Draft' AND to_status = 'Review open') OR "
            "(from_status = 'Review open' AND to_status = 'Draft')",
            name="ck_idea_status_events_transition",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False, index=True)
    changed_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    idea: Mapped[Idea] = relationship(back_populates="status_events")


class IdeaVersion(Base):
    __tablename__ = "idea_versions"
    __table_args__ = (
        UniqueConstraint("idea_id", "version"),
        CheckConstraint("version >= 1", name="ck_idea_versions_version_positive"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("idea_versions.id"))
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80))
    problem: Mapped[str] = mapped_column(Text)
    solution: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(Text)
    features: Mapped[list[str]] = mapped_column(JSON)
    constraints: Mapped[str] = mapped_column(Text, default="")
    change_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    idea: Mapped[Idea] = relationship(back_populates="versions")
    assets: Mapped[list["IdeaAsset"]] = relationship(
        back_populates="idea_version", cascade="all, delete-orphan"
    )
    requirement_analyses: Mapped[list["RequirementAnalysisRun"]] = relationship(
        back_populates="idea_version"
    )
    prototype_builds: Mapped[list["PrototypeBuild"]] = relationship(
        back_populates="idea_version"
    )


class RequirementAnalysisRun(Base):
    __tablename__ = "requirement_analysis_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_requirement_analysis_runs_status",
        ),
        CheckConstraint(
            "validation_status IN ('pending', 'valid', 'invalid', 'not_run')",
            name="ck_requirement_analysis_runs_validation_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_requirement_analysis_runs_attempts"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False, index=True)
    idea_version_id: Mapped[str] = mapped_column(
        ForeignKey("idea_versions.id"), nullable=False, index=True
    )
    source_version: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    workflow_run_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model_version: Mapped[str] = mapped_column(String(160), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage: Mapped[dict | None] = mapped_column(JSON)
    failure_category: Mapped[str | None] = mapped_column(String(80))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    idea_version: Mapped[IdeaVersion] = relationship(back_populates="requirement_analyses")


class PrototypeBuild(Base):
    __tablename__ = "prototype_builds"
    __table_args__ = (
        CheckConstraint(
            "status IN ('source_generated', 'validation_failed', "
            "'unsupported_category', 'generation_failed', 'source_missing')",
            name="ck_prototype_builds_status",
        ),
        CheckConstraint(
            "validation_status IN ('passed', 'failed', 'not_run')",
            name="ck_prototype_builds_validation_status",
        ),
        CheckConstraint(
            "build_status = 'blocked_isolation'",
            name="ck_prototype_builds_build_status",
        ),
        CheckConstraint(
            "publish_status = 'unpublished'",
            name="ck_prototype_builds_publish_status",
        ),
        CheckConstraint("source_version >= 1", name="ck_prototype_builds_source_version"),
        UniqueConstraint(
            "requirement_analysis_run_id",
            name="uq_prototype_builds_requirement_analysis_run",
        ),
        UniqueConstraint("workflow_run_id", name="uq_prototype_builds_workflow_run"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False, index=True)
    idea_version_id: Mapped[str] = mapped_column(
        ForeignKey("idea_versions.id"), nullable=False, index=True
    )
    source_version: Mapped[int] = mapped_column(Integer, nullable=False)
    requirement_analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_analysis_runs.id"), nullable=False
    )
    workflow_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(80))
    template_version: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    build_status: Mapped[str] = mapped_column(
        String(30), default="blocked_isolation", nullable=False
    )
    publish_status: Mapped[str] = mapped_column(
        String(20), default="unpublished", nullable=False
    )
    plan: Mapped[dict | None] = mapped_column(JSON)
    manifest: Mapped[dict | None] = mapped_column(JSON)
    validation_results: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_files: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    artifact_metadata: Mapped[dict | None] = mapped_column(JSON)
    source_storage_key: Mapped[str | None] = mapped_column(String(36))
    preview_url: Mapped[str | None] = mapped_column(String(2048))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idea_version: Mapped[IdeaVersion] = relationship(back_populates="prototype_builds")


class IdeaAsset(Base):
    __tablename__ = "idea_assets"
    __table_args__ = (
        CheckConstraint("size_bytes > 0 AND size_bytes <= 10485760", name="ck_idea_assets_size"),
        CheckConstraint(
            "content_type IN ('application/pdf', 'image/png', 'image/jpeg')",
            name="ck_idea_assets_content_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idea_version_id: Mapped[str] = mapped_column(
        ForeignKey("idea_versions.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    idea_version: Mapped[IdeaVersion] = relationship(back_populates="assets")


class ReviewerAssignment(Base):
    __tablename__ = "reviewer_assignments"
    __table_args__ = (
        UniqueConstraint(
            "idea_version_id", "reviewer_id", name="uq_reviewer_assignments_version_reviewer"
        ),
        CheckConstraint(
            "status IN ('assigned', 'in_progress', 'submitted', 'revoked')",
            name="ck_reviewer_assignments_status",
        ),
        CheckConstraint(
            "(active AND status != 'revoked') OR (NOT active AND status = 'revoked')",
            name="ck_reviewer_assignments_active_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idea_version_id: Mapped[str] = mapped_column(ForeignKey("idea_versions.id"), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    review_cycle_id: Mapped[str] = mapped_column(ForeignKey("review_cycles.id"), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False, server_default="true")
    status: Mapped[str] = mapped_column(
        String(20), default="assigned", nullable=False, server_default="assigned"
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class ReviewCycle(Base):
    __tablename__ = "review_cycles"
    __table_args__ = (
        UniqueConstraint("idea_version_id", name="uq_review_cycles_idea_version"),
        CheckConstraint("status IN ('open', 'closed')", name="ck_review_cycles_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idea_version_id: Mapped[str] = mapped_column(
        ForeignKey("idea_versions.id"), nullable=False, index=True
    )
    opened_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewSession(Base):
    __tablename__ = "review_sessions"
    __table_args__ = (
        UniqueConstraint("assignment_id", name="uq_review_sessions_assignment"),
        CheckConstraint(
            "status IN ('in_progress', 'submitted')", name="ck_review_sessions_status"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("reviewer_assignments.id"), nullable=False
    )
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False)
    idea_version_id: Mapped[str] = mapped_column(
        ForeignKey("idea_versions.id"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IdeaReview(Base):
    __tablename__ = "idea_reviews"
    __table_args__ = (
        UniqueConstraint("assignment_id", name="uq_idea_reviews_assignment"),
        UniqueConstraint(
            "assignment_id", "idempotency_key", name="uq_idea_reviews_assignment_idempotency"
        ),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_idea_reviews_rating"),
        CheckConstraint(
            "usability_score IS NULL OR usability_score BETWEEN 1 AND 5",
            name="ck_idea_reviews_usability_score",
        ),
        CheckConstraint(
            "usefulness_score IS NULL OR usefulness_score BETWEEN 1 AND 5",
            name="ck_idea_reviews_usefulness_score",
        ),
        CheckConstraint(
            "completeness_score IS NULL OR completeness_score BETWEEN 1 AND 5",
            name="ck_idea_reviews_completeness_score",
        ),
        CheckConstraint(
            "feasibility_score IS NULL OR feasibility_score BETWEEN 1 AND 5",
            name="ck_idea_reviews_feasibility_score",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("reviewer_assignments.id"), nullable=False
    )
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False)
    idea_version_id: Mapped[str] = mapped_column(
        ForeignKey("idea_versions.id"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    review_session_id: Mapped[str] = mapped_column(
        ForeignKey("review_sessions.id"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    usability_score: Mapped[int | None] = mapped_column(Integer)
    usefulness_score: Mapped[int | None] = mapped_column(Integer)
    completeness_score: Mapped[int | None] = mapped_column(Integer)
    feasibility_score: Mapped[int | None] = mapped_column(Integer)
    would_use: Mapped[bool | None] = mapped_column()
    strengths: Mapped[str | None] = mapped_column(Text)
    concerns: Mapped[str | None] = mapped_column(Text)
    suggested_improvements: Mapped[str | None] = mapped_column(Text)
    usage_context: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FeedbackAnalysisOutbox(Base):
    __tablename__ = "feedback_analysis_outbox"
    __table_args__ = (
        UniqueConstraint("feedback_id", name="uq_feedback_analysis_outbox_feedback"),
        CheckConstraint(
            "status IN ('pending', 'queued', 'received')",
            name="ck_feedback_analysis_outbox_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    feedback_id: Mapped[str] = mapped_column(
        ForeignKey("idea_reviews.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class FeedbackAnalysisRun(Base):
    __tablename__ = "feedback_analysis_runs"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", name="uq_feedback_analysis_runs_workflow_run"),
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_feedback_analysis_runs_status",
        ),
        CheckConstraint(
            "validation_status IN ('pending', 'valid', 'invalid', 'not_run')",
            name="ck_feedback_analysis_runs_validation_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_feedback_analysis_runs_attempts"),
        CheckConstraint("source_version >= 1", name="ck_feedback_analysis_runs_source_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False, index=True)
    idea_version_id: Mapped[str] = mapped_column(
        ForeignKey("idea_versions.id"), nullable=False, index=True
    )
    source_version: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    workflow_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    source_feedback_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model_version: Mapped[str] = mapped_column(String(160), nullable=False)
    embedding_model_version: Mapped[str] = mapped_column(String(160), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage: Mapped[dict | None] = mapped_column(JSON)
    failure_category: Mapped[str | None] = mapped_column(String(80))


class FeedbackEmbedding(Base):
    __tablename__ = "feedback_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "feedback_id", "model_version", name="uq_feedback_embeddings_feedback_model"
        ),
        CheckConstraint("dimension = 768", name="ck_feedback_embeddings_dimension"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    feedback_id: Mapped[str] = mapped_column(
        ForeignKey("idea_reviews.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model_version: Mapped[str] = mapped_column(String(160), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(768).with_variant(JSON(), "sqlite"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EvolutionProposal(Base):
    __tablename__ = "evolution_proposals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected')",
            name="ck_evolution_proposals_status",
        ),
        CheckConstraint("source_version >= 1", name="ck_evolution_proposals_source_version"),
        UniqueConstraint(
            "idea_version_id",
            "feedback_analysis_run_id",
            name="uq_evolution_proposals_version_analysis",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False, index=True)
    idea_version_id: Mapped[str] = mapped_column(
        ForeignKey("idea_versions.id"), nullable=False, index=True
    )
    source_version: Mapped[int] = mapped_column(Integer, nullable=False)
    requirement_analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_analysis_runs.id"), nullable=False
    )
    feedback_analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("feedback_analysis_runs.id"), nullable=False
    )
    source_feedback_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    suggestions: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed", nullable=False)
    target_version_id: Mapped[str | None] = mapped_column(ForeignKey("idea_versions.id"))
    prototype_build_id: Mapped[str | None] = mapped_column(ForeignKey("prototype_builds.id"))
    requested_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model_version: Mapped[str] = mapped_column(String(160), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    validation_results: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DecisionReport(Base):
    __tablename__ = "decision_reports"
    __table_args__ = (
        CheckConstraint("source_version >= 1", name="ck_decision_reports_source_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), nullable=False, index=True)
    idea_version_id: Mapped[str] = mapped_column(
        ForeignKey("idea_versions.id"), nullable=False, index=True
    )
    source_version: Mapped[int] = mapped_column(Integer, nullable=False)
    requirement_analysis_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("requirement_analysis_runs.id")
    )
    feedback_analysis_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("feedback_analysis_runs.id")
    )
    evolution_proposal_id: Mapped[str | None] = mapped_column(
        ForeignKey("evolution_proposals.id")
    )
    source_feedback_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    report_version: Mapped[str] = mapped_column(String(80), nullable=False)
    report: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
