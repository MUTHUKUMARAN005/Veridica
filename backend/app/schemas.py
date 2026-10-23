from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(RegisterRequest):
    pass


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    role: Literal["owner", "reviewer", "admin"]


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse


class IdeaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=80)
    problem: str = Field(min_length=10, max_length=10_000)
    solution: str = Field(min_length=10, max_length=10_000)
    audience: str = Field(min_length=2, max_length=5_000)
    features: list[str] = Field(min_length=1, max_length=30)
    constraints: str = Field(default="", max_length=5_000)

    @field_validator(
        "title", "category", "problem", "solution", "audience", "constraints", mode="before"
    )
    @classmethod
    def trim_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("features", mode="before")
    @classmethod
    def normalize_features(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            return value
        normalized = [
            feature.strip()
            for feature in value
            if isinstance(feature, str) and feature.strip()
        ]
        if not normalized:
            raise ValueError("At least one non-empty feature is required.")
        if any("|" in feature for feature in normalized):
            raise ValueError("Features cannot contain the reserved pipe character.")
        return normalized


class IdeaVersionCreate(IdeaCreate):
    expected_version: int = Field(ge=1)
    change_summary: str = Field(min_length=1, max_length=5_000)

    @field_validator("change_summary", mode="before")
    @classmethod
    def trim_change_summary(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class IdeaStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["Draft", "Archived"]


class IdeaAssetResponse(BaseModel):
    id: str
    idea_version_id: str
    filename: str
    content_type: Literal["application/pdf", "image/png", "image/jpeg"]
    size_bytes: int
    sha256: str
    created_at: datetime


class IdeaResponse(IdeaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    owner_id: str
    version_id: str
    source_version_id: str | None
    created_by_id: str
    change_summary: str
    version: int
    status: str
    created_at: datetime
    updated_at: datetime
    version_created_at: datetime
    assets: list[IdeaAssetResponse] = Field(default_factory=list)


class IdeaPage(BaseModel):
    items: list[IdeaResponse]
    total: int
    limit: int
    offset: int


class IdeaStatusEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    changed_by_id: str
    sequence: int
    from_status: str | None
    to_status: str
    created_at: datetime


class IdeaDetail(IdeaResponse):
    versions: list[IdeaResponse]
    status_history: list[IdeaStatusEventResponse]


RequirementSourceField = Literal[
    "title", "problem", "solution", "audience", "features", "constraints"
]


class RequirementFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2_000)
    basis: Literal["explicit", "assumption"]
    source_fields: list[RequirementSourceField] = Field(min_length=1, max_length=6)

    @field_validator("text", mode="before")
    @classmethod
    def trim_requirement_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class RequirementJourney(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: RequirementFact
    need: RequirementFact
    steps: list[str] = Field(min_length=1, max_length=20)
    outcome: RequirementFact

    @field_validator("steps", mode="before")
    @classmethod
    def trim_journey_steps(cls, value: list[str]) -> list[str]:
        if isinstance(value, list):
            steps = [step.strip() if isinstance(step, str) else step for step in value]
            if any(not step for step in steps if isinstance(step, str)):
                raise ValueError("Journey steps cannot be empty.")
            return steps
        return value


class RequirementSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem: list[RequirementFact] = Field(max_length=20)
    target_users: list[RequirementFact] = Field(max_length=20)
    user_journeys: list[RequirementJourney] = Field(max_length=20)
    core_features: list[RequirementFact] = Field(max_length=30)
    constraints: list[RequirementFact] = Field(max_length=30)
    assumptions: list[str] = Field(max_length=30)
    acceptance_criteria: list[RequirementFact] = Field(max_length=30)
    open_questions: list[str] = Field(max_length=30)

    @field_validator("assumptions", "open_questions", mode="before")
    @classmethod
    def trim_requirement_lists(cls, value: list[str]) -> list[str]:
        if isinstance(value, list):
            items = [item.strip() if isinstance(item, str) else item for item in value]
            if any(not item for item in items if isinstance(item, str)):
                raise ValueError("Requirement entries cannot be empty.")
            return items
        return value


class RequirementAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idea_id: str
    idea_version_id: str
    source_version: int
    workflow_run_id: str
    provider: str
    model_version: str
    prompt_version: str
    status: Literal["queued", "running", "completed", "failed"]
    validation_status: Literal["pending", "valid", "invalid", "not_run"]
    result: RequirementSpecification | None
    error_message: str | None
    attempt_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime


class PrototypeComponentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal[
        "IdeaSummary",
        "FeatureSearch",
        "JourneySteps",
        "OpenQuestions",
        "PrototypeNotice",
    ]
    purpose: str = Field(min_length=1, max_length=180)


class PrototypeScreenPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Literal["overview", "features", "journeys", "questions"]
    title: str = Field(min_length=1, max_length=80)
    components: list[PrototypeComponentPlan] = Field(min_length=1, max_length=4)


class PrototypePlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: Literal["education-placement-preparation"]
    template_version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    framework: Literal["react-typescript-vite"]
    category: Literal["education-placement"]
    screens: list[PrototypeScreenPlan] = Field(min_length=4, max_length=4)
    limitations: list[str] = Field(min_length=1, max_length=8)


class PrototypeManifestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: Literal["education-placement-preparation"]
    template_version: str
    framework: Literal["react-typescript-vite"]
    dependencies: dict[str, str]
    scripts: dict[str, str]
    files: list[str]
    source_only: Literal[True]
    build_boundary: Literal["unavailable"]


class PrototypeSourceFileResponse(BaseModel):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(ge=0)


class PrototypeArtifactMetadataResponse(BaseModel):
    artifact_type: Literal["generated_source"]
    file_count: int = Field(ge=0)
    total_size_bytes: int = Field(ge=0)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    built_artifact_available: Literal[False]


class PrototypeGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_analysis_id: str = Field(min_length=36, max_length=36)


class PrototypeBuildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idea_id: str
    idea_version_id: str
    source_version: int
    requirement_analysis_run_id: str
    workflow_run_id: str
    template_id: str | None
    template_version: str | None
    status: Literal[
        "source_generated",
        "validation_failed",
        "unsupported_category",
        "generation_failed",
        "source_missing",
    ]
    validation_status: Literal["passed", "failed", "not_run"]
    build_status: Literal["blocked_isolation"]
    publish_status: Literal["unpublished"]
    plan: PrototypePlanResponse | None
    manifest: PrototypeManifestResponse | None
    validation_results: dict
    source_files: list[PrototypeSourceFileResponse]
    artifact_metadata: PrototypeArtifactMetadataResponse | None
    preview_url: None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class PrototypeSourceResponse(BaseModel):
    prototype_build_id: str
    files: dict[str, str]


class AdminAssignmentCreate(BaseModel):
    idea_id: str = Field(min_length=36, max_length=36)
    version: int = Field(ge=1)
    reviewer_email: str = Field(min_length=3, max_length=320)

    @field_validator("reviewer_email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        normalized = value.strip().lower()
        if "@" not in normalized or any(character.isspace() for character in normalized):
            raise ValueError("Enter a valid reviewer email.")
        return normalized


class AdminAssignmentResponse(BaseModel):
    id: str
    idea_id: str
    idea_title: str
    version: int
    reviewer_email: str
    active: bool
    status: Literal["assigned", "in_progress", "submitted", "revoked"]
    assigned_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    revoked_at: datetime | None
    review_submitted: bool


class ReviewSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assignment_id: str
    idea_id: str
    idea_version_id: str
    reviewer_id: str
    status: Literal["in_progress", "submitted"]
    started_at: datetime
    completed_at: datetime | None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assignment_id: str
    idea_id: str
    idea_version_id: str
    reviewer_id: str
    review_session_id: str
    idempotency_key: str | None
    rating: int
    usability_score: int | None
    usefulness_score: int | None
    completeness_score: int | None
    feasibility_score: int | None
    would_use: bool | None
    feedback_text: str
    strengths: str | None
    concerns: str | None
    suggested_improvements: str | None
    usage_context: str | None
    created_at: datetime
    analysis_status: Literal["pending", "queued", "received"]
    analysis_error: str | None = None


class ReviewerAssignmentResponse(BaseModel):
    id: str
    idea_id: str
    idea_title: str
    version: int
    problem: str
    solution: str
    audience: str
    features: list[str]
    constraints: str
    assigned_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    status: Literal["assigned", "in_progress", "submitted", "revoked"]
    review_submitted: bool
    review_session: ReviewSessionResponse | None = None
    feedback: ReviewResponse | None = None
    assets: list[IdeaAssetResponse] = Field(default_factory=list)


class ReviewSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=36, max_length=36)
    rating: int = Field(ge=1, le=5)
    usability_score: int = Field(ge=1, le=5)
    usefulness_score: int = Field(ge=1, le=5)
    completeness_score: int = Field(ge=1, le=5)
    feasibility_score: int = Field(ge=1, le=5)
    would_use: bool
    feedback_text: str = Field(min_length=10, max_length=5_000)
    strengths: str = Field(min_length=10, max_length=5_000)
    concerns: str = Field(min_length=10, max_length=5_000)
    suggested_improvements: str = Field(min_length=10, max_length=5_000)
    usage_context: str = Field(min_length=10, max_length=5_000)

    @field_validator(
        "feedback_text",
        "strengths",
        "concerns",
        "suggested_improvements",
        "usage_context",
        mode="before",
    )
    @classmethod
    def trim_feedback_text(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class ReviewCycleResponse(BaseModel):
    id: str
    idea_id: str
    idea_version_id: str
    version: int
    status: Literal["open", "closed"]
    opened_by_id: str
    opened_at: datetime
    closed_at: datetime | None


class FeedbackQualityItem(BaseModel):
    feedback_id: str
    relevance: float = Field(ge=0, le=1)
    constructiveness: float = Field(ge=0, le=1)
    originality: float = Field(ge=0, le=1)
    internal_consistency: float = Field(ge=0, le=1)
    spam_risk: float = Field(ge=0, le=1)
    authenticity_indicator: float = Field(ge=0, le=1)
    self_reported_confidence: float = Field(ge=0, le=1)
    uncertainty: str = Field(min_length=1, max_length=1_000)
    explanations: dict[str, str]

    @field_validator("uncertainty")
    @classmethod
    def validate_uncertainty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Uncertainty explanation cannot be blank.")
        return normalized

    @field_validator("explanations")
    @classmethod
    def validate_explanations(cls, value: dict[str, str]) -> dict[str, str]:
        required = {
            "relevance",
            "constructiveness",
            "originality",
            "internal_consistency",
            "spam_risk",
            "authenticity_indicator",
        }
        if not required <= value.keys() or any(
            not isinstance(value[key], str) or not value[key].strip() for key in required
        ):
            raise ValueError("Each quality judgment requires a non-empty explanation.")
        return value


class FeedbackQualityBatch(BaseModel):
    items: list[FeedbackQualityItem] = Field(min_length=1)


class FeedbackTheme(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    kind: Literal["feature_request", "complaint", "positive", "other"]
    summary: str = Field(min_length=1, max_length=1_000)
    feedback_ids: list[str] = Field(min_length=1)


class FeedbackContradiction(BaseModel):
    summary: str = Field(min_length=1, max_length=1_000)
    feedback_ids: list[str] = Field(min_length=2)


class FeedbackNlpBatch(BaseModel):
    themes: list[FeedbackTheme]
    contradictions: list[FeedbackContradiction]


class FeedbackImprovementProposal(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=1_000)
    feedback_ids: list[str] = Field(min_length=1)
    theme_labels: list[str]
    impact: Literal["high", "medium", "low", "unknown"]
    impact_rationale: str = Field(min_length=1, max_length=1_000)
    feasibility: Literal["high", "medium", "low", "unknown"]
    feasibility_rationale: str = Field(min_length=1, max_length=1_000)
    assumptions: list[str]
    missing_inputs: list[str]


class FeedbackPrioritizationBatch(BaseModel):
    proposals: list[FeedbackImprovementProposal]


class FeedbackTrustAssessment(BaseModel):
    feedback_id: str
    score: float | None = Field(ge=0, le=1)
    factor_json: dict[str, float | None]
    factor_weights: dict[str, float]
    formula_version: str
    evidence_coverage: float = Field(ge=0, le=1)
    missing_factors: list[str]
    interpretation: str


class FeedbackDeterministicSignals(BaseModel):
    feedback_id: str
    text_characters: int = Field(ge=0)
    structured_ratings_complete: bool
    exact_duplicate_of: str | None


class FeedbackDuplicatePair(BaseModel):
    feedback_ids: list[str] = Field(min_length=2, max_length=2)
    cosine_similarity: float = Field(ge=-1, le=1)
    method: Literal["pgvector_cosine", "deterministic_test_cosine"]


class FeedbackConsensus(BaseModel):
    sample_size: int = Field(ge=0)
    evidence_coverage: float = Field(ge=0, le=1)
    raw_support_count: int = Field(ge=0)
    raw_support: float | None = Field(ge=0, le=1)
    normalized_weight_denominator: float
    raw_feedback_weights: dict[str, float]
    normalized_feedback_weights: dict[str, float]
    weighted_support: float | None = Field(ge=0, le=1)
    confidence_indicator: float | None = Field(ge=0, le=1)
    confidence_method: str
    uncertainty: str
    evidence_ids: list[str]


class FeedbackPriority(BaseModel):
    rank: int = Field(ge=1)
    priority: Literal["P1", "P2", "P3"]
    title: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=1_000)
    feedback_ids: list[str] = Field(min_length=1)
    theme_labels: list[str]
    evidence_count: int = Field(ge=1)
    weighted_support: float = Field(ge=0)
    impact: Literal["high", "medium", "low", "unknown"]
    impact_rationale: str
    feasibility: Literal["high", "medium", "low", "unknown"]
    feasibility_rationale: str
    assumptions: list[str]
    missing_inputs: list[str]


class FeedbackAnalysisOutput(BaseModel):
    source_feedback_ids: list[str]
    quality: list[FeedbackQualityItem]
    deterministic_signals: list[FeedbackDeterministicSignals]
    themes: list[FeedbackTheme]
    contradictions: list[FeedbackContradiction]
    duplicate_pairs: list[FeedbackDuplicatePair]
    trust: list[FeedbackTrustAssessment]
    consensus: FeedbackConsensus
    priorities: list[FeedbackPriority]


class EvolutionApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_source_version: int = Field(ge=1)
    selected_ranks: list[int] = Field(min_length=1, max_length=30)

    @field_validator("selected_ranks")
    @classmethod
    def validate_selected_ranks(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Selected priority ranks must be unique.")
        return value


class EvolutionBenefit(BaseModel):
    interpretation: str
    qualitative_impact: Literal["high", "medium", "low", "unknown"]
    weighted_support: float = Field(ge=0)


class EvolutionRisk(BaseModel):
    feedback_id: str
    concern: str


class EvolutionSuggestion(BaseModel):
    rank: int = Field(ge=1)
    priority: Literal["P1", "P2", "P3"]
    title: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=1_000)
    source_feedback_ids: list[str] = Field(min_length=1)
    expected_benefit: EvolutionBenefit
    assumptions: list[str]
    risks: list[EvolutionRisk]
    validation_criteria: list[str]
    validation_note: str
    feasibility: Literal["high", "medium", "low", "unknown"]
    feasibility_rationale: str
    missing_inputs: list[str]
    builder_supported: bool


class EvolutionProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idea_id: str
    idea_version_id: str
    source_version: int
    requirement_analysis_run_id: str
    feedback_analysis_run_id: str
    source_feedback_ids: list[str]
    suggestions: list[EvolutionSuggestion]
    status: Literal["proposed", "approved", "rejected"]
    target_version_id: str | None
    prototype_build_id: str | None
    provider: str
    model_version: str
    prompt_version: str
    validation_results: dict
    created_at: datetime
    approved_at: datetime | None


class DecisionReportIdea(BaseModel):
    title: str
    source_version: int
    parent_version_id: str | None
    problem_summary: dict
    audience: dict
    constraints: str


class DecisionReportRequirements(BaseModel):
    status: str
    validation_status: str
    result: RequirementSpecification | None
    analysis_run_id: str | None
    source_record_ids: list[str]
    assumptions: dict
    uncertainty: list[str]


class DecisionReportPrototype(BaseModel):
    status: str
    validation_status: str
    build_status: str
    publish_status: str
    prototype_build_id: str | None
    limitations: dict
    classification: Literal["static_source_only_not_a_working_prototype"]


class DecisionReportClassifiedItems(BaseModel):
    classification: str
    items: list[dict]


class DecisionReportConsensus(BaseModel):
    classification: Literal["deterministic_calculation"]
    value: dict | None


class DecisionReportReviews(BaseModel):
    sample_size: int = Field(ge=0)
    analyzed_sample_size: int = Field(ge=0)
    source_feedback_ids: list[str]
    analyzed_feedback_ids: list[str]
    analysis_run_id: str | None
    coverage: float = Field(ge=0, le=1)
    analysis_evidence_coverage: float = Field(ge=0, le=1)
    quality_findings: DecisionReportClassifiedItems
    themes: DecisionReportClassifiedItems
    trust: DecisionReportClassifiedItems
    consensus: DecisionReportConsensus
    uncertainty: str


class DecisionReportEvolution(BaseModel):
    proposal_id: str
    status: str
    source_version: int
    target_version_id: str | None
    suggestions: list[dict]
    approved_changes: list[str]
    source_feedback_ids: list[str]
    validation_results: dict


class DecisionReportVersionChanges(BaseModel):
    status: str
    changes: list[str]
    source_feedback_ids: list[str]
    validated_prototype: bool


class DecisionReportSourceRecords(BaseModel):
    idea_version_id: str
    source_version: int
    requirement_analysis_run_id: str | None
    feedback_analysis_run_id: str | None
    source_feedback_ids: list[str]


class DecisionReportDocument(BaseModel):
    idea: DecisionReportIdea
    requirements: DecisionReportRequirements
    prototype: DecisionReportPrototype
    reviews: DecisionReportReviews
    prioritized_improvements: DecisionReportClassifiedItems
    evolution: DecisionReportEvolution | None
    v1_to_v2_changes: DecisionReportVersionChanges
    risks_and_missing_evidence: list[str]
    recommended_next_steps: list[str]
    source_records: DecisionReportSourceRecords
    generated_at: datetime
    report_version: str
    owner_idea_id: str


class DecisionReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idea_id: str
    idea_version_id: str
    source_version: int
    requirement_analysis_run_id: str | None
    feedback_analysis_run_id: str | None
    evolution_proposal_id: str | None
    source_feedback_ids: list[str]
    report_version: str
    report: DecisionReportDocument
    created_at: datetime


class FeedbackAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idea_id: str
    idea_version_id: str
    source_version: int
    workflow_run_id: str
    input_digest: str
    source_feedback_ids: list[str]
    provider: str
    model_version: str
    embedding_model_version: str
    prompt_version: str
    status: Literal["queued", "running", "completed", "failed"]
    validation_status: Literal["pending", "valid", "invalid", "not_run"]
    result: FeedbackAnalysisOutput | None
    error_message: str | None
    attempt_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
