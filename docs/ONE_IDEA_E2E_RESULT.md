# One-Idea E2E Verification

**Run date:** 2026-10-23  
**Environment:** Local Codespaces services; no AWS or paid services used

## Result

The one-idea workflow passed the available browser and PostgreSQL-backed
acceptance checks.

| Check | Result | Evidence |
| --- | --- | --- |
| Authenticated browser persistence | Passed | Playwright Chromium: `1 passed`. Registered an owner, created an idea through the UI/API, reloaded, signed in again, and retrieved the same persisted idea. |
| Persisted workflow | Passed | PostgreSQL acceptance test: `1 passed`. Covered idea/version creation, requirements, publication and reviewer assignment, feedback submission/retry, analysis, evolution, report persistence, and authorization boundaries. |
| Database and migration state | Passed | PostgreSQL with pgvector was ready; Alembic current and head were both `0010`. |
| Queue service | Passed | Redis was ready and the Celery worker responded to a live ping. |
| Restored local application | Passed | Frontend and API documentation returned HTTP 200; API readiness reported PostgreSQL and Redis connected. |

## Limitations

- AI workflow outputs in the persisted workflow test used deterministic test
  doubles. This verifies the application workflow and persistence, not live model
  inference. No Ollama or Gemini model call was verified.
- Generated prototype source remains statically validated only. Building or
  previewing generated code is blocked until a separately restricted execution
  boundary is available; no generated code was executed.
- This is local development verification, not production deployment, reliability,
  or availability evidence.

## Re-run

From the repository root, with PostgreSQL, Redis, and the backend virtual
environment configured:

```bash
cd backend
RUN_INTEGRATION=1 .venv/bin/pytest tests/test_phase8_acceptance.py -q
cd ../frontend
npm run test:e2e:api
```
