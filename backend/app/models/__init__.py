from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.entities import (  # noqa: E402,F401
    DecisionReport,
    EvolutionProposal,
    FeedbackAnalysisOutbox,
    FeedbackAnalysisRun,
    FeedbackEmbedding,
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
