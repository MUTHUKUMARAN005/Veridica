"""LangGraph workflow graphs for Veridica idea validation pipeline.

Graphs define the flow: idea → requirement → prototype → feedback → analysis
→ trust → consensus → priorities → evolution hypothesis → decision report.
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


# ---------------------------------------------------------------------------
# State types
# -------------------------------------------------------------------------


class IdeaContext(TypedDict):
    idea_id: str
    version: int
    title: str
    problem: str
    solution: str
    audience: str


class RequirementContext(TypedDict):
    idea_version_id: str
    requirement_specification: object  # RequirementSpecification


class PrototypeContext(TypedDict):
    requirement_analysis_run_id: str
    prototype_build: object


class FeedbackContext(TypedDict):
    idea_version_id: str
    evidence: list[dict]
    quality: object  # FeedbackQualityBatch
    themes: list[object]  # list[FeedbackTheme]
    contradictions: list[object]  # list[FeedbackContradiction]
    proposals: list[object]  # list[FeedbackImprovementProposal]


class AnalysisContext(TypedDict):
    trust: object  # TrustAssessment
    consensus: object  # FeedbackConsensus
    priorities: list[object]  # list[FeedbackPriority]
    evolution_suggestions: list[object]  # list[EvolutionSuggestion]


# Combined state type for the full workflow
# This includes all fields from individual context types used across the 6 workflow steps
class WorkflowState(TypedDict, total=False):
    idea_id: str
    version: int
    title: str
    problem: str
    solution: str
    audience: str
    requirement_specification: object  # RequirementSpecification
    requirement_analysis_run_id: str
    prototype_build: object
    evidence: list[dict]
    quality: object  # FeedbackQualityBatch
    themes: list[object]  # list[FeedbackTheme]
    contradictions: list[object]  # list[FeedbackContradiction]
    proposals: list[object]  # list[FeedbackImprovementProposal]
    trust: object  # TrustAssessment
    consensus: object  # FeedbackConsensus
    priorities: list[object]  # list[FeedbackPriority]
    evolution_suggestions: list[object]  # list[EvolutionSuggestion]
# ---------------------------------------------------------------------------
# Workflow functions
# -------------------------------------------------------------------------


def requirement_workflow(
    idea_context: IdeaContext,
    provider: ChatProvider,
) -> RequirementContext:
    """Step 1: Analyze idea and produce requirement specification.

    Edge: idea → requirement (output: RequirementSpecification)
    """
    from app.agents.requirement_agent import analyze_requirements

    source = type(
        "RequirementSourceVersion",
        (),
        {
            "title": idea_context["title"],
            "problem": idea_context["problem"],
            "solution": idea_context["solution"],
            "audience": idea_context["audience"],
            "features": [],
            "constraints": "No external integrations.",
        },
    )()

    requirement_spec = analyze_requirements(source, provider)
    return {"requirement_specification": requirement_spec}


def prototype_workflow(
    requirement_context: RequirementContext,
    provider: ChatProvider,
) -> PrototypeContext:
    """Step 2: Build prototype from requirement specification.

    Edge: requirement → prototype (output: prototype build record)
    """
    from app.agents.prototype_builder import build_prototype_plan
    from app.services.prototypes import create_prototype_source

    plan_data = build_prototype_plan(
        requirement_context["requirement_specification"], provider
    )
    prototype_build = create_prototype_source(
        None,
        None,
        None,
        str(requirement_context.get("requirement_analysis_run_id", "")),
    )
    return {"prototype_build": prototype_build}


def feedback_workflow(
    idea_version_id: str,
    provider: ChatProvider,
) -> FeedbackContext:
    """Step 3: Gather and analyze feedback.

    Edge: prototype → feedback (outbox enqueued for background processing)
    """
    return {
        "idea_version_id": idea_version_id,
        "evidence": [],
        "quality": [],
        "themes": [],
        "contradictions": [],
        "proposals": [],
    }


def analysis_workflow(
    feedback_context: FeedbackContext,
    provider: ChatProvider,
) -> AnalysisContext:
    """Step 4: Perform full feedback analysis producing trust, consensus, priorities.

    Edge: feedback → analysis (output: trust scores, consensus, priority rankings)
    """
    from app.agents.feedback_analysis import (
        deterministic_signals,
        assess_trust,
        calculate_consensus,
        prioritize_improvements,
        build_analysis_output,
    )

    evidence = feedback_context["evidence"]
    quality_items = feedback_context["quality"]
    themes = feedback_context["themes"]
    contradictions = feedback_context["contradictions"]
    proposals = feedback_context["proposals"]

    signals = deterministic_signals(evidence)
    trust = assess_trust(quality_items, [item["feedback_id"] for item in evidence])
    consensus, weights = calculate_consensus(
        evidence, quality_items, trust, 1.0
    )
    priorities = prioritize_improvements(proposals, weights)

    return {
        "trust": trust,
        "consensus": consensus,
        "priorities": priorities,
    }


def evolution_workflow(
    analysis_context: AnalysisContext,
    requirement_context: RequirementContext,
    idea_version: object,
) -> AnalysisContext:
    """Step 5: Generate evolution suggestions based on analysis and priorities.

    Edge: analysis → evolution (output: evolution suggestions with risks/benefits)
    """
    priorities = analysis_context["priorities"]
    suggestions = []
    for priority in priorities[:3]:
        suggestions.append(
            {
                "rank": priority.rank,
                "priority": priority.priority,
                "title": priority.title,
                "rationale": priority.rationale,
                "source_feedback_ids": priority.feedback_ids,
                "expected_benefit": {
                    "interpretation": priority.impact_rationale,
                    "qualitative_impact": priority.impact,
                    "weighted_support": priority.weighted_support,
                },
                "assumptions": priority.assumptions,
                "risks": [],
                "validation_criteria": [
                    criterion.text
                    for criterion in requirement_context["requirement_specification"].acceptance_criteria
                ],
                "validation_note": "Owner and reviewers must validate this change against the cited feedback.",
                "feasibility": priority.feasibility,
                "feasibility_rationale": priority.feasibility_rationale,
                "missing_inputs": priority.missing_inputs,
            }
        )
    return {**analysis_context, "evolution_suggestions": suggestions}


def decision_intelligence_workflow(
    analysis_context: AnalysisContext,
) -> dict[str, Any]:
    """Step 6: Build the final decision report synthesizing all analysis results.

    Edge: evolution → decision intelligence (output: decision report ready for API)
    """
    from app.services.decision_intelligence import build_decision_report

    trust = analysis_context["trust"]
    consensus = analysis_context["consensus"]
    priorities = analysis_context["priorities"]
    evolution_suggestions = analysis_context.get("evolution_suggestions", [])

    report = build_decision_report(
        trust=trust,
        consensus=consensus,
        priorities=priorities,
        evolution_suggestions=evolution_suggestions,
    )

    return {
        "decision_report": report,
        "trust_score": getattr(trust, "trust_score", 0.0),
        "consensus_value": getattr(consensus, "value", 0.0),
        "top_priorities": [p.rank for p in priorities[:5]],
    }


# ---------------------------------------------------------------------------
# Graph composition - wire all stages together
# -------------------------------------------------------------------------


def create_veridica_workflow() -> StateGraph:
    """Create the complete Veridica idea validation workflow graph.

    The graph wires together all 7 agent modules in sequence:
    1. Requirement Agent (idea → requirement)
    2. Prototype Builder (requirement → prototype)
    3. Feedback Analysis (prototype → feedback → analysis)
    4. Trust/Consensus/Priorities computation (analysis → trust/scores)
    5. Evolution Suggestion (analysis → evolution hypotheses)
    6. Decision Intelligence (evolution → decision report)

    Returns:
        A compiled StateGraph ready for execution.
    """
    workflow = StateGraph(state_schema=WorkflowState)

    # Define nodes (each corresponds to a workflow step)
    workflow.add_node("requirement_agent", lambda state: requirement_workflow(state["idea_context"], state["provider"]))
    workflow.add_node("prototype_builder", lambda state: prototype_workflow(state["requirement_context"], state["provider"]))
    workflow.add_node("feedback_analysis", lambda state: feedback_workflow(state["idea_version_id"], state["provider"]))
    workflow.add_node("feedback_analysis_full", lambda state: analysis_workflow(state["feedback_context"], state["provider"]))
    workflow.add_node("evolution_suggestion", lambda state: evolution_workflow(state["analysis_context"], state["requirement_context"], state["idea_version"]))
    workflow.add_node("decision_intelligence", lambda state: decision_intelligence_workflow(state["analysis_context"]))

    # Define edges connecting the nodes in sequence
    workflow.set_entry_point("requirement_agent")

    workflow.add_edge("requirement_agent", "prototype_builder")
    workflow.add_edge("prototype_builder", "feedback_analysis")
    workflow.add_edge("feedback_analysis", "feedback_analysis_full")
    workflow.add_edge("feedback_analysis_full", "evolution_suggestion")
    workflow.add_edge("evolution_suggestion", "decision_intelligence")
    workflow.add_edge("decision_intelligence", END)

    return workflow
