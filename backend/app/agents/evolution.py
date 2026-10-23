from app.agents.ai_builder import supports_education_placement
from app.models import IdeaReview, IdeaVersion
from app.schemas import (
    EvolutionRisk,
    EvolutionSuggestion,
    FeedbackAnalysisOutput,
    RequirementSpecification,
)

PROMPT_VERSION = "evolution-evidence-proposals-v1"


def propose_evidence_changes(
    version: IdeaVersion,
    requirements: RequirementSpecification,
    analysis: FeedbackAnalysisOutput,
    reviews: list[IdeaReview],
) -> list[EvolutionSuggestion]:
    evidence_by_id = {review.id: review for review in reviews}
    analysis_ids = set(analysis.source_feedback_ids)
    validation_criteria = [item.text for item in requirements.acceptance_criteria]
    suggestions = []
    for priority in analysis.priorities:
        cited_ids = list(dict.fromkeys(priority.feedback_ids))
        if not cited_ids or not set(cited_ids) <= analysis_ids:
            continue
        cited_reviews = [evidence_by_id[item] for item in cited_ids if item in evidence_by_id]
        if len(cited_reviews) != len(cited_ids):
            continue
        suggestions.append(
            EvolutionSuggestion(
                rank=priority.rank,
                priority=priority.priority,
                title=priority.title,
                rationale=priority.rationale,
                source_feedback_ids=cited_ids,
                expected_benefit={
                    "interpretation": priority.impact_rationale,
                    "qualitative_impact": priority.impact,
                    "weighted_support": priority.weighted_support,
                },
                assumptions=priority.assumptions,
                risks=[
                    EvolutionRisk(feedback_id=review.id, concern=review.concerns)
                    for review in cited_reviews
                    if review.concerns and review.concerns.strip()
                ],
                validation_criteria=validation_criteria,
                validation_note=(
                    "Owner and reviewers must validate this change against the cited "
                    "feedback; no outcome is measured by this proposal."
                ),
                feasibility=priority.feasibility,
                feasibility_rationale=priority.feasibility_rationale,
                missing_inputs=priority.missing_inputs,
                builder_supported=supports_education_placement(
                    version.category,
                    version.title,
                    version.problem,
                    version.solution,
                    version.audience,
                    list(version.features),
                ),
            )
        )
    return suggestions
