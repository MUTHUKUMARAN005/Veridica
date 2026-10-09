# Veridica Development Rules

Read README and docs before coding.
Treat docs/PROJECT_SPEC.md (the master blueprint v3) as the architecture source of truth.
Use React + TypeScript + Vite + Tailwind.
Use Python + FastAPI + Pydantic + SQLAlchemy + Alembic.
Use PostgreSQL + pgvector.
Use Redis + Celery.
Use LangGraph.
Use Amazon Bedrock.
Keep trust deterministic.
Separate deterministic logic from LLM reasoning.
Persist important AI outputs.
Store workflow_run_id, model_version and prompt_version.
Never overwrite original idea versions.
Never use static JSON as production source of truth.
Never hardcode measured-looking KPIs.
Never claim AI proves a reviewer is fake.
Keep prototype generation isolated.
Never execute generated code in FastAPI.
Build incrementally.
Test after every major phase.
Do not mark features complete without acceptance tests.
Keep API contracts typed.
Keep migrations versioned.
Keep state transitions auditable.
If older documents conflict with this blueprint, follow the blueprint and record the conflict in docs/DECISIONS.md.