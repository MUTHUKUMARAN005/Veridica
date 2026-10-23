import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.providers.base import ChatProvider, ProviderResponseError
from app.schemas import RequirementSpecification, PrototypePlan, PrototypeManifest

PROMPT_VERSION = "prototype-spec-v1"

SYSTEM_PROMPT = """You are Veridica's Prototype Builder Agent.
Given a validated requirement specification, generate a structured prototype plan
and file contents that implement the idea. Return a JSON object with:
- plan: PrototypePlan schema
- manifest: PrototypeManifest schema  
- files: a dictionary of filename -> source code content

Use only explicit requirements as source. Mark all inferences as assumptions.
Never invent capabilities or features not in the requirements.
"""

PROTOTYPE_PROMPT = """Produce a structured prototype plan and source files for this 
requirement specification. The schema is:

{schema}

Requirement:
{requirement}
"""


@dataclass(frozen=True)
class PrototypeOutputValidationError(Exception):
    pass


def build_prototype_plan(
    requirement: RequirementSpecification,
    provider: ChatProvider,
) -> dict[str, Any]:
    """Generate a prototype plan and source files from a requirement specification."""
    schema_json = json.dumps(
        {
            "plan": PrototypePlan.model_json_schema(),
            "manifest": PrototypeManifest.model_json_schema(),
        },
        separators=(",", ":"),
    )
    prompt = (
        "Given the following requirement specification, produce a prototype plan "
        "and source files that implement it.\n"
        f"Schema:\n{schema_json}\n"
        f"Requirement:\n{requirement.model_dump_json(indent=2)}"
    )
    raw_output = provider.chat(prompt, SYSTEM_PROMPT)
    if not raw_output.strip():
        raise ProviderResponseError("The prototype builder returned empty output.")
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError as error:
        raise PrototypeOutputValidationError(
            "The prototype builder returned output that is not valid JSON."
        ) from error