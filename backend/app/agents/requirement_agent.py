import json
from dataclasses import dataclass

from pydantic import ValidationError

from app.providers.base import ChatProvider, ProviderResponseError
from app.schemas import RequirementSpecification

PROMPT_VERSION = "requirement-spec-v1"
SYSTEM_PROMPT = """You are Veridica's Requirement Agent.
Analyze only the supplied immutable idea version. Return one JSON object matching the
provided schema, without markdown or additional keys. Use only explicit source facts
as explicit. Mark every inference as an assumption, list it in assumptions, and cite
the source fields that motivated it. Never invent users, constraints, capabilities,
or measurable targets. When source information is insufficient, leave the affected
list empty and add a focused open question. Acceptance criteria that are inferred
must be marked with basis=assumption."""


class RequirementOutputValidationError(Exception):
    pass


@dataclass(frozen=True)
class RequirementSourceVersion:
    title: str
    problem: str
    solution: str
    audience: str
    features: list[str]
    constraints: str


def analyze_requirements(
    idea_version: RequirementSourceVersion, provider: ChatProvider
) -> RequirementSpecification:
    source = {
        "title": idea_version.title,
        "problem": idea_version.problem,
        "solution": idea_version.solution,
        "audience": idea_version.audience,
        "features": idea_version.features,
        "constraints": idea_version.constraints,
    }
    prompt = (
        "Produce a structured requirement specification for this exact source version.\n"
        "The schema is:\n"
        f"{json.dumps(RequirementSpecification.model_json_schema(), separators=(',', ':'))}\n"
        "Source version:\n"
        f"{json.dumps(source, ensure_ascii=True, separators=(',', ':'))}"
    )
    raw_output = provider.chat(prompt, SYSTEM_PROMPT)
    if not raw_output.strip():
        raise ProviderResponseError("The model returned empty output.")
    try:
        return RequirementSpecification.model_validate_json(raw_output)
    except (ValidationError, ValueError) as error:
        raise RequirementOutputValidationError(
            "The model response did not match the requirement specification schema."
        ) from error
