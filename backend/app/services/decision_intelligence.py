from datetime import UTC, datetime
from uuid import uuid4

from app.models import (
    DecisionReport,
    FeedbackAnalysisRun,
    Idea,
    IdeaVersion,
    PrototypeBuild,
    RequirementAnalysisRun,
)
from app.schemas import (
    DecisionReportDocument,
    FeedbackAnalysisOutput,
    RequirementSpecification,
)

DECISION_REPORT_VERSION = "decision-report-v1"


def build_decision_report(
    idea: Idea,
    version: IdeaVersion,
    requirements: RequirementAnalysisRun | None,
    analysis_run: FeedbackAnalysisRun | None,
    proposal: dict | None,
    prototype: PrototypeBuild | None,
    source_feedback_ids: list[str],
) -> dict:
    valid_requirements = (
        requirements
        if requirements is not None
        and requirements.status == "completed"
        and requirements.validation_status == "valid"
        else None
    )
    valid_analysis = (
        analysis_run
        if analysis_run is not None
        and analysis_run.status == "completed"
        and analysis_run.validation_status == "valid"
        else None
    )
    requirement_result = (
        RequirementSpecification.model_validate(valid_requirements.result).model_dump(mode="json")
        if valid_requirements is not None and valid_requirements.result is not None
        else None
    )
    analysis = (
        FeedbackAnalysisOutput.model_validate(valid_analysis.result).model_dump(mode="json")
        if valid_analysis is not None and valid_analysis.result is not None
        else None
    )
    available_feedback_ids = set(source_feedback_ids)
    analyzed_feedback_ids = (
        [
            feedback_id
            for feedback_id in valid_analysis.source_feedback_ids
            if feedback_id in available_feedback_ids
        ]
        if valid_analysis is not None
        else []
    )
    feedback_coverage = (
        len(analyzed_feedback_ids) / len(source_feedback_ids)
        if source_feedback_ids
        else 0.0
    )
    analysis_uncertainty = (
        [analysis["consensus"]["uncertainty"]]
        if analysis
        else ["Persisted feedback analysis is unavailable."]
    )
    document = {
        "idea": {
            "title": version.title,
            "source_version": version.version,
            "parent_version_id": version.source_version_id,
            "problem_summary": {
                "value": version.problem,
                "classification": "observed_owner_input",
                "source_record_ids": [version.id],
            },
            "audience": {
                "value": version.audience,
                "classification": "observed_owner_input",
                "source_record_ids": [version.id],
            },
            "constraints": version.constraints,
        },
        "requirements": {
            "status": requirements.status if requirements else "missing",
            "validation_status": requirements.validation_status if requirements else "missing",
            "result": requirement_result,
            "analysis_run_id": requirements.id if requirements else None,
            "source_record_ids": [version.id],
            "assumptions": (
                {
                    "classification": "explicitly_marked_requirement_assumptions",
                    "items": requirement_result["assumptions"],
                }
                if requirement_result
                else {"classification": "unavailable", "items": []}
            ),
            "uncertainty": (
                requirement_result["open_questions"]
                if requirement_result
                else ["No validated requirement result."]
            ),
        },
        "prototype": {
            "status": prototype.status if prototype else "missing",
            "validation_status": prototype.validation_status if prototype else "not_run",
            "build_status": prototype.build_status if prototype else "not_started",
            "publish_status": prototype.publish_status if prototype else "unpublished",
            "prototype_build_id": prototype.id if prototype else None,
            "limitations": (
                prototype.validation_results
                if prototype is not None
                else {"reason": "No source-generation record exists."}
            ),
            "classification": "static_source_only_not_a_working_prototype",
        },
        "reviews": {
            "sample_size": len(source_feedback_ids),
            "analyzed_sample_size": len(analyzed_feedback_ids),
            "source_feedback_ids": source_feedback_ids,
            "analyzed_feedback_ids": analyzed_feedback_ids,
            "analysis_run_id": analysis_run.id if analysis_run else None,
            "coverage": feedback_coverage,
            "analysis_evidence_coverage": (
                analysis["consensus"]["evidence_coverage"] if analysis else 0.0
            ),
            "quality_findings": {
                "classification": "model_generated_interpretations",
                "items": analysis["quality"] if analysis else [],
            },
            "themes": {
                "classification": "model_generated_interpretations",
                "items": analysis["themes"] if analysis else [],
            },
            "trust": {
                "classification": "deterministic_partial_calculation",
                "items": analysis["trust"] if analysis else [],
            },
            "consensus": {
                "classification": "deterministic_calculation",
                "value": analysis["consensus"] if analysis else None,
            },
            "uncertainty": (
                analysis["consensus"]["uncertainty"]
                if analysis
                else "Feedback has not been analyzed."
            ),
        },
        "prioritized_improvements": {
            "classification": "model_suggestions_with_deterministic_ordinal_rank",
            "items": analysis["priorities"] if analysis else [],
        },
        "evolution": proposal,
        "v1_to_v2_changes": {
            "status": (
                proposal["status"] if proposal else "no_proposal"
            ),
            "changes": proposal.get("approved_changes", []) if proposal else [],
            "source_feedback_ids": (
                proposal.get("source_feedback_ids", []) if proposal else []
            ),
            "validated_prototype": False,
        },
        "risks_and_missing_evidence": [
            *(
                requirement_result["open_questions"]
                if requirement_result
                else ["Validated requirements are unavailable."]
            ),
            *analysis_uncertainty,
            "The prototype has not been built or published in an isolated execution boundary.",
            "This report contains no product-market-fit, adoption, or business-outcome claim.",
        ],
        "recommended_next_steps": [
            (
                "Review each evidence-linked proposed change and approve only changes "
                "within the supported scope."
            ),
            "Validate any new immutable version with reviewers before making outcome claims.",
        ],
        "source_records": {
            "idea_version_id": version.id,
            "source_version": version.version,
            "requirement_analysis_run_id": requirements.id if requirements else None,
            "feedback_analysis_run_id": analysis_run.id if analysis_run else None,
            "source_feedback_ids": source_feedback_ids,
        },
        "generated_at": datetime.now(UTC).isoformat(),
        "report_version": DECISION_REPORT_VERSION,
        "owner_idea_id": idea.id,
    }
    return DecisionReportDocument.model_validate(document).model_dump(mode="json")


def report_record(
    idea: Idea,
    version: IdeaVersion,
    report: dict,
    created_by_id: str,
    requirements: RequirementAnalysisRun | None,
    analysis_run: FeedbackAnalysisRun | None,
    proposal_id: str | None,
    feedback_ids: list[str],
) -> DecisionReport:
    return DecisionReport(
        id=str(uuid4()),
        idea_id=idea.id,
        idea_version_id=version.id,
        source_version=version.version,
        requirement_analysis_run_id=requirements.id if requirements else None,
        feedback_analysis_run_id=analysis_run.id if analysis_run else None,
        evolution_proposal_id=proposal_id,
        source_feedback_ids=feedback_ids,
        report_version=DECISION_REPORT_VERSION,
        report=report,
        created_by_id=created_by_id,
    )
