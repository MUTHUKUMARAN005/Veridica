# Setup Verification

## Current: 2026-10-09 Free-local auth and idea slice

- Recreated the moved Windows Python virtual environment successfully.
- Backend development dependencies install from `backend/requirements-dev.txt`.
- 27 backend non-integration tests passed; one integration test was deselected.
- Backend Ruff check passed with no errors.
- Frontend lint passed with no warnings or errors.
- 14 frontend unit tests passed.
- Frontend TypeScript production build passed.
- Vite preview runs locally at the selected available port, including `5174` when
  `5173` is already occupied.
- Added local API registration/login, in-memory access-token handling, sign-out,
  API identity display, API idea listing, and API idea creation.
- Offline browser preview remains available and is explicitly labeled.

Still required for the next acceptance gate: a real local PostgreSQL/pgvector
service, Redis service, Alembic upgrade against PostgreSQL, Celery worker execution,
and an end-to-end API-mode browser check. Ollama is not required for the current
auth/idea slice and remains optional until AI workflows are implemented.

## Current: 2026-09-30 Comment-First Feedback

- Added reviewer comments, testing context, useful votes and optional detailed ratings.
- Added idea-interest likes and unique successful link-copy discovery signals.
- Added owner/admin impact/effort assessment, blockers and ordered P1/P2/P3 proposals.
- Questions and unestimated/blocked changes cannot enter version proposals.
- Proposal snapshots retain evidence, estimates and formula version; V1 is unchanged.
- Existing browser data migrates without losing ideas or detailed reviews.
- 14 unit tests and all 13 browser acceptance tests passed; lint and build passed.
- Browser tests cover the full mobile comment-to-priority-to-proposal flow, source
  evidence navigation, link-copy deduplication and legacy preview storage migration.
- All new behavior remains explicitly browser-local. Production identity, Python
  persistence/analysis, and validated AI-generated V2 artifacts remain pending.

## Current: 2026-09-30 Social-Style Frontend

- Replaced the KPI-first dashboard with a visual, Instagram-inspired idea feed.
- Added story-style project links, local saved collections, share-link dialogs,
  actual sample-prototype screenshot assets, bundled DM Sans typography, and mobile bottom navigation.
- Retained owner/reviewer/admin workflows and explicit sample-data labeling.
- All 10 browser tests passed, including new social-feed and 360px navigation checks.
- All 9 frontend state/client tests passed, lint was clean, and the production build passed.
- Follow-up reset acceptance passed after extending reset to clear saved ideas.
- No social action generates a trust score, fake engagement count, or AI analysis.
- The existing development server continues to serve http://127.0.0.1:5173/.

## Current: 2026-09-30 Python Foundation Increment

- Backend runtime and development dependency installation now succeeds.
- Added APP_ENV validation and explicit credentialed-CORS origin checks.
- The database URL must use postgresql+psycopg, matching the synchronous services.
- Production settings reject HTTP CORS origins, missing/sample database passwords,
  and non-TLS Redis URLs. Validation error text excludes configuration input values.
- 25 backend tests passed; the one real-service integration test was excluded.
- Backend Ruff lint and changed-file editor diagnostics passed.
- FastAPI started natively at http://127.0.0.1:8000 without Docker.
- Live HTTP smoke checks returned 200 for liveness and 503 for readiness, reporting
  PostgreSQL and Redis unavailable. No listeners were found on their standard local ports.
- Test output includes one upstream Starlette/httpx deprecation warning; no test failed.

Still required: provision real PostgreSQL/pgvector and Redis, apply migrations,
execute a real Celery task, then implement authentication and persistent business
APIs. These configuration checks alone are not a production security certification.

## Current: 2026-09-30 Frontend Preview

- Offline dependency installation succeeded. Frontend runs at http://127.0.0.1:5173/.
- No Docker or backend process is needed for the frontend preview.
- Owner, reviewer and admin preview routes are connected and functional locally.
- 9 Node unit tests passed; 8 Playwright acceptance tests passed.
- TypeScript/production build and Oxlint passed without errors or warnings.
- Desktop (1440px) and mobile (390px) browser checks passed with no horizontal overflow.
- All owner routes rendered without browser console errors during acceptance tests.
- Tests verify idea creation/persistence, sample prototype interactions, local review
  submission, charts, raw consensus inputs, V1 preservation, report export, assignments,
  reset confirmation, mobile navigation, publishing and credential-free auth preview.
- The npm lockfile is generated. CI now uses npm ci and includes browser tests.
- The backend remains Python; future AI agents will use Python, LangGraph and Bedrock.

Still pending: authenticated portals, production API integration, PostgreSQL feedback
persistence, Python workflows, actual AI prototype generation, trust/quality results,
embeddings, weighted consensus, validated V2 builds, AWS deployment and real MVP E2E.
Browser-local fixtures do not satisfy those backend acceptance gates. GitHub CI itself
has not been executed in this session. The old networking notes below are historical;
frontend package installation was recovered using the local cache.

## Historical: 2026-09-29 Foundation

- The existing workspace folder was empty; no user code was replaced.
- Node 24.18.0 and Python 3.12 are available.
- React/TypeScript scaffolding succeeded and the backend virtual environment was created.
- Backend and migration Python syntax compilation passed.
- Four direct Node checks passed for the TypeScript health client: connected,
  degraded, offline and malformed API response states.
- Workspace JSON and the required frontend major-version declarations passed validation.

## Blocked Gates

- Docker was not found on PATH; container builds, Compose startup, migrations against
  PostgreSQL and the real Redis/Celery integration test have not run.
- Python installation failed with DNS resolution errors and then no available packages
  from the public index. Backend pytest and Ruff checks could not run.
- npm installation failed with ENOTFOUND for registry.npmjs.org. The frontend
  production build, Vitest suite and browser verification have not run.
- The development server launch failed because Vite is not installed. No preview
  server is running. Final editor diagnostics report missing Node/Vite type
  definitions and ENOTFOUND for the external TypeScript JSON schema host.
- No frontend lockfile is generated yet. CI temporarily uses npm install; after
  a successful install, review the generated lockfile and change CI to npm ci.
- No AWS resources are provisioned. No production security/deployment claim is made.

Restore package registry connectivity and install/start Docker Desktop, then run the
README checks. P0 and the single-idea MVP acceptance test are not marked complete.