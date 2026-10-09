# Veridica: Detailed Remaining Work

**Updated:** 2026-10-09  
**Purpose:** Implementation checklist from the current frontend preview to a working, secure, AWS-deployed product.  
**Current milestone:** Free/local auth and idea vertical slice implemented; frontend
API connection implemented; real PostgreSQL/Redis integration and remaining product
work are pending.

## 1. Read This First

The frontend is ready to explore, but the complete Veridica application is not finished.
The next major task is to implement the Python backend and connect the existing screens
to real accounts, database records, prototype artifacts, and AI workflows.

The architecture source of truth is [PROJECT_SPEC.md](PROJECT_SPEC.md).
User-requested adjustments are recorded in [DECISIONS.md](DECISIONS.md).
Previous verification results are in [SETUP_STATUS.md](SETUP_STATUS.md).
This checklist does not replace those documents or claim unimplemented features are complete.

**Free-local implementation update:** the [README](../README.md) now defines the
active no-AWS stack: native PostgreSQL/pgvector, Redis, Celery, and Ollama. AI
providers are isolated behind Python interfaces so a later deployment can add a
managed provider without coupling domain logic to it. The first real slice now
includes local authentication, owner authorization, persistent ideas, and immutable
idea versions.

### Fixed Requirements

- Keep the frontend in React, TypeScript, Vite, and Tailwind.
- Implement the API in Python with FastAPI, Pydantic, SQLAlchemy, and Alembic.
- Implement the AI agents and LangGraph workflows in Python.
- Use PostgreSQL/pgvector as the production source of truth.
- Use Redis and Celery for asynchronous processing; Redis is not the durable business database.
- Use the local Ollama provider for development LLM calls and embeddings; keep the
  provider boundary replaceable for a future deployment.
- Do not require Docker in the active development workflow.
- Plan eventual AWS deployment, but approve the container-free compute architecture first.
- Never run generated prototype code inside FastAPI or the general application worker.
- Never replace real feedback or analytical results with sample values in production.
- Never overwrite an original idea version or a prototype already under review.
- Keep deterministic trust calculations separate from LLM reasoning.

**Python clarification:** The API, agents, and workflow orchestration are Python.
Generated web prototypes remain React/TypeScript and require Node-based frontend build
tools inside an isolated build environment. This does not introduce a second API backend.

## 2. What Is Already Available

These items describe the current preview, not production acceptance.

### Frontend Preview

- [x] Owner, reviewer, and admin preview navigation.
- [x] Workspace overview and searchable idea library.
- [x] Idea submission with client-side validation and browser-local persistence.
- [x] Idea details, feature brief, feedback, and version views.
- [x] Hand-authored Campus Compass prototype with search, bookmarks, and checklists.
- [x] Hand-authored Circular City prototype with sample issue reporting.
- [x] Desktop/mobile prototype preview controls.
- [x] Reviewer assignment preview and interactive review workspace.
- [x] Structured ratings and evidence-based local feedback forms.
- [x] Charts calculated from displayed sample/local review records.
- [x] Raw consensus display and honest pending states for AI/trust results.
- [x] Manual, evidence-linked version proposals that preserve V1.
- [x] Preview decision reports and exports.
- [x] Local admin assignments, activity history, and reset confirmation.
- [x] Sign-in/register design previews that do not save or send credentials.

### Foundation Code

- [x] Python backend virtual environment and dependency declarations were created.
- [x] FastAPI liveness and dependency-readiness endpoints are implemented.
- [x] SQLAlchemy base and an initial pgvector migration are scaffolded.
- [x] Redis/Celery configuration and a worker health task are scaffolded.
- [x] Frontend lockfile and CI configuration exist.

### Previously Verified Frontend Checks

- [x] 9 Node unit tests passed on 2026-09-30.
- [x] 8 Playwright browser acceptance tests passed on 2026-09-30.
- [x] TypeScript and production build passed.
- [x] Frontend lint passed without warnings or errors.
- [x] Desktop and mobile navigation/layout checks passed at the tested viewports.

These checks do not prove authentication, PostgreSQL persistence, AI generation,
production security, AWS deployment, or the real single-idea acceptance loop.
GitHub-hosted CI execution has not been verified in this session.

### Backend Foundation Progress: 2026-09-30

- [x] Installed the declared Python runtime and development dependencies successfully.
- [x] Added tested APP_ENV, database-driver, CORS-origin, and production-settings validation.
- [x] Redacted input values from configuration validation error text.
- [x] Passed 25 backend tests that do not require live PostgreSQL or Redis.
- [x] Passed backend Ruff checks and editor diagnostics for the changed Python files.
- [x] Started FastAPI directly through Python/Uvicorn without Docker.
- [x] Verified live HTTP responses: liveness 200; readiness 503 with PostgreSQL/Redis unavailable.

One live-service integration test was deliberately excluded because PostgreSQL and
Redis were unavailable. An upstream Starlette warning deprecates the current httpx
test-client path; the tests still pass. No business API, database persistence, trust
score, or authenticated portal is claimed by this foundation increment.

### Free-local vertical slice: 2026-10-09

- [x] Added local password authentication with signed bearer access tokens.
- [x] Added owner-scoped `/auth` and `/ideas` API endpoints.
- [x] Added PostgreSQL migrations for users, ideas, and immutable idea versions.
- [x] Added request validation, duplicate-account handling, and concurrent-version conflict handling.
- [x] Added an optional Ollama chat/embedding provider boundary.
- [x] Added API tests using a shared in-memory SQLite test database.

The frontend still uses its explicitly labeled browser-local preview store. Connecting
its forms to these authenticated APIs is the next integration step; the backend slice
does not claim that the preview portal selector is authentication.

## 3. What Is Not Real Yet

| Current preview behavior | Production work still required |
| --- | --- |
| Portal selector chooses a sample role | Authentication and server-side RBAC |
| Ideas and reviews live in localStorage | Authorized APIs and PostgreSQL persistence |
| Upload selection keeps filenames | Validated uploads, S3 objects, and asset metadata |
| Prototype screens are hand-authored samples | Python requirement analysis and isolated AI builder |
| Publish and assignment actions are local | Audited lifecycle and assignment services |
| Review interaction is browser-local | Authorized, version-linked review sessions |
| Ratings produce simple local averages | Server-side analytics from persisted feedback |
| Trust/quality views show pending states | Persisted quality evidence and deterministic trust |
| Consensus shows raw support | Normalized trust-weighted consensus and confidence |
| Evolution copies selected suggestions into a proposal | Python evolution workflow and a validated V2 artifact |
| Report export summarizes local records | Persisted, evidence-linked decision intelligence |
| Activity view shows local events | Workflow runs, live events, durable audit, and failure recovery |

The backend now exposes health, authentication, and owner-scoped idea/version routes
from [main.py](../backend/app/main.py). The initial business entities live in
[entities.py](../backend/app/models/entities.py). Feedback, reviewer sessions, and
the remaining analytical entities are still pending.

## 4. Recommended Implementation Order

| Order | Blueprint phase | Main deliverable | Depends on |
| --- | --- | --- | --- |
| 1 | P0 remaining | Working native/managed PostgreSQL, Redis, API, and Python worker | Environment access |
| 2 | P1 | Reviewer/admin authorization, recovery, audit, and real session lifecycle | P0 and local auth slice |
| 3 | P2 | Persistent idea assets, pagination, lifecycle, and upload policy | P1 and PostgreSQL |
| 4 | P3 | Validated, persisted requirement specifications | P2 and Bedrock access |
| 5 | P4 | One supported idea category produces an isolated, reviewable prototype | P3 and approved sandbox |
| 6 | P5 | Publishing, assignments, sessions, and real prototype access | P4 |
| 7 | P6 | Durable feedback and idempotent submission | P5 |
| 8 | P7 | Reliable background workflows and live progress | P6; basic job support starts earlier |
| 9 | P8 | Quality analysis and deterministic trust snapshots | P7 |
| 10 | P9 | Embeddings, clusters, consensus, and priorities | P8 |
| 11 | P10 | Evidence-based evolution and validated V2 | P9 |
| 12 | P11 | Traceable decision reports and connected dashboards | P10 |
| 13 | P12 | Approved AWS architecture, staging, and production deployment | Security gates and real E2E |
| 14 | P13 | Reproducible research evaluation | Stable product and labeled datasets |

Connect each frontend feature as its backend phase becomes usable. Do not wait until
all backend modules exist, and do not mark a phase done merely because its screen exists.
Bedrock and S3 access may be needed before the full AWS deployment phase.

## 5. P0: Finish the Python Development Foundation

### Environment and Services

- [x] Recheck Python package installation and network/DNS access; installation succeeded on 2026-09-30.
- [x] Install backend development dependencies into the existing virtual environment.
- [ ] Provision PostgreSQL with a compatible pgvector extension, natively or as a managed service.
- [ ] Provision Redis natively under a suitable Linux environment, or use managed Redis.
- [ ] Configure development DATABASE_URL and REDIS_URL without committing credentials.
- [ ] Replace sample credentials for any shared or remotely reachable environment.
- [ ] Run Alembic migrations against a real development database.
- [x] Start FastAPI directly with Python/Uvicorn.
- [ ] Run Celery under Linux/WSL or suitable AWS compute; do not treat native Windows Celery as the production target.
- [x] Verify native API liveness and honest unavailable-dependency readiness responses.
- [ ] Verify readiness with real PostgreSQL/Redis and actual worker task execution.
- [ ] Add reproducible Python dependency locking and review dependency vulnerabilities.
- [ ] Separate development, test, staging, and production configuration.
- [x] Add startup validation for APP_ENV, the synchronous database driver, explicit CORS origins, non-sample production database credentials, and Redis TLS in production.
- [x] Hide configuration inputs in validation error text and test secret redaction.
- [ ] Add feature-specific startup validation for future auth/AWS settings and audit all logging for sensitive values.

### Exit Criteria

- [ ] A real database connection succeeds and pgvector is available.
- [ ] Redis responds and a queued task is executed by a separate Python worker.
- [ ] Backend unit and integration tests pass against the intended service versions.
- [ ] Services can restart without losing database records.
- [ ] No Docker command is needed for the selected development setup.

## 6. P1: Authentication and Real Portals

### Identity and Authorization

- [ ] Decide and document user/organization ownership boundaries before writing authorization rules.
- [x] Add the initial user model, migration, schema, and session boundary.
- [x] Implement registration, login, and scrypt password hashing for local development.
- [x] Document signed bearer token expiry and in-memory frontend token handling.
- [ ] Implement account verification and recovery flows needed for the launch scope.
- [ ] Prevent public registration from granting admin privileges.
- [x] Implement server-side owner/resource authorization for the idea endpoints.
- [ ] Enforce organization/resource ownership on every protected endpoint.
- [ ] Limit reviewer access to assigned projects, permitted prototype versions, and their own review records.
- [ ] Require an audited process for administrative role changes and overrides.
- [ ] Add authentication rate limits and appropriate handling of repeated failed attempts.
- [ ] Record security events without logging passwords or tokens.

### Frontend Connection

- [x] Connect sign-in/register forms to Python APIs.
- [x] Show API identity and preserve a separate offline preview mode.
- [ ] Add session loading, expired-session, forbidden, and signed-out states.
- [ ] Add route guards for usability, while keeping the server as the security boundary.
- [x] Add in-memory frontend logout; server token revocation remains pending.
- [x] Keep credentials and access tokens out of localStorage and application logs.

**Acceptance:** Three authenticated roles work in independent sessions; unauthorized
cross-user and cross-project requests fail even when sent directly to the API.

## 7. P2: Ideas, Versions, and Uploads

### Persistent Idea Management

- [x] Create ideas and idea_versions tables with a versioned migration.
- [ ] Store title, problem, target users, solution, features, constraints, category, owner, and timestamps.
- [ ] Define server-side request limits and Pydantic validation.
- [x] Implement authorized idea creation, listing, detail retrieval, and new-version creation.
- [ ] Specify which draft fields may change and which operations create a new version.
- [ ] Preserve the original V1 snapshot; never mutate a version that has entered review.
- [x] Add row locking and conflict handling for concurrent version creation.
- [ ] Make lifecycle transitions explicit and auditable.
- [ ] Add pagination, filtering, and stable ordering for growing workspaces.
- [ ] Define archiving/deletion and evidence-retention behavior before exposing destructive controls.

### Real File Handling

- [ ] Configure private S3 upload storage and least-privilege permissions.
- [ ] Validate supported file types, file signatures, sizes, filenames, and counts on the server.
- [ ] Add malware scanning/quarantine or an equivalent reviewed file-safety policy.
- [ ] Use short-lived signed upload/download access where appropriate.
- [ ] Store object metadata, ownership, processing status, and checksums in PostgreSQL.
- [ ] Handle interrupted uploads, duplicate requests, and orphaned objects.
- [ ] Extract document/image content using an approved ingestion path before requirement analysis.
- [ ] Replace filename-only preview behavior with progress, failure, retry, and removal states.

**Acceptance:** An owner can create an idea, upload a supported reference, refresh or
sign in on another device, and retrieve the same authorized V1 and asset records.

## 8. P3: Python Requirement Agent

- [ ] Configure approved Bedrock models, AWS region, permissions, and invocation limits.
- [ ] Add the Python Bedrock client with bounded timeouts and retry handling.
- [ ] Define a typed requirement-output schema matching the blueprint.
- [ ] Include problem, users, journeys, requirements, features, screens, navigation, scope, constraints, and assumptions.
- [ ] Treat uploaded text and images as untrusted input, not agent instructions.
- [ ] Separate system instructions, user content, and retrieved material in prompts.
- [ ] Validate structured output and reject malformed or unsupported specifications.
- [ ] Persist requirement_specs instead of storing the result only in worker memory.
- [ ] Persist workflow_run_id, model_version, prompt_version, source idea version, status, duration, and errors.
- [ ] Add versioned prompt templates and tests for representative idea categories.
- [ ] Run analysis asynchronously with visible status and retry controls.
- [ ] Connect the Requirements tab to the actual result and its provenance.
- [ ] Keep owner-written requirements visibly distinct from agent-generated requirements.

**Acceptance:** A submitted idea produces a schema-valid, persisted requirement spec
through a real Python/Bedrock invocation; failures are recorded and recoverable.

## 9. P4: Python AI Builder and Isolated Prototype Generation

### Controlled MVP Scope

- [ ] Start with one supported category, such as the placement-assistant example.
- [ ] Define allowed templates, components, packages, interactions, and integration placeholders.
- [ ] Implement Python planning/generation modules around the validated requirement spec.
- [ ] Generate screen specs, component plans, manifests, and React/TypeScript source.
- [ ] Store feature coverage and known limitations alongside generated artifacts.
- [ ] Validate filenames and paths; reject traversal, arbitrary shell commands, secrets, and unapproved dependencies.

### Isolation: Required Before Any Generated Build Runs

- [ ] Approve a sandbox design compatible with the no-Docker requirement.
- [ ] Evaluate an isolated VM or equivalent reviewed execution boundary; this is a proposal, not a selected architecture.
- [ ] Separate sandbox compute, identity, filesystem, and network access from the API and normal worker.
- [ ] Deny access to application secrets, database credentials, and instance metadata credentials.
- [ ] Restrict network egress and dependency installation to the approved policy.
- [ ] Enforce CPU, memory, disk, process, runtime, and artifact-size limits.
- [ ] Use nonprivileged execution and clean up the environment after each build.
- [ ] Never run generated server code or user-provided commands in FastAPI.

### Build and Delivery

- [ ] Run dependency validation, lint, typecheck, production build, and supported interaction checks.
- [ ] Capture build/test output, errors, timing, and retry count.
- [ ] Persist prototypes, prototype_builds, and prototype_events.
- [ ] Enforce DRAFT -> BUILDING -> VALIDATING -> READY or FAILED transitions.
- [ ] Publish only validated, versioned static artifacts to S3.
- [ ] Serve previews on an isolated origin with an appropriate CSP and access policy.
- [ ] Add authorized preview URLs and expiration/access behavior.
- [ ] Connect live build status, logs, failure handling, and artifact launch to the frontend.
- [ ] Never show a successful build or preview URL unless the real artifact exists.

**Acceptance:** One supported idea produces a usable multi-screen prototype from a
real requirement spec, passes validation in isolation, and can be launched by an
authorized user. Unsupported ideas receive an honest unsupported/failure state.

## 10. P5: Publishing, Assignments, and Review Sessions

- [ ] Implement server-side project publishing only for a validated prototype.
- [ ] Freeze the specific idea/prototype version when its review cycle opens.
- [ ] Persist reviewer_profiles, review_assignments, and review_sessions.
- [ ] Implement admin assignments with duplicate prevention and audit records.
- [ ] Expose an authorized reviewer project queue.
- [ ] Start a review session tied to reviewer, assignment, idea version, and prototype version.
- [ ] Record permitted session activity and journey progress under a documented privacy policy.
- [ ] Define abandonment, timeout, resume, completion, and closed-cycle behavior.
- [ ] Add reviewer matching with a keyword baseline, then evaluate Bedrock embedding matching.
- [ ] Keep manual admin assignment available while matching is evaluated.
- [ ] Connect queue, launch, journey, session, and completion UI states to the backend.

**Acceptance:** An assigned reviewer in a separate authenticated session can launch
the correct immutable prototype. An unassigned user cannot obtain access by guessing IDs.

## 11. P6: Real Feedback and Durable Submission

- [ ] Create the feedback table with actor, session, assignment, idea, and prototype-version references.
- [ ] Persist rating, usability, usefulness, completeness, feasibility, would_use, feedback_text, strengths, concerns, improvements, and usage context.
- [ ] Enforce rating ranges, content limits, ownership, session validity, and open-cycle rules in Python.
- [ ] Define whether a reviewer may submit once or revise feedback; preserve an audit trail either way.
- [ ] Use an idempotency key with a database constraint and a defined request-replay contract.
- [ ] Commit feedback to PostgreSQL before enqueueing any asynchronous analysis.
- [ ] Implement a transactional outbox or equivalent durable delivery design so a queue failure after commit does not lose analysis work.
- [ ] Handle duplicate delivery and replay safely in workers.
- [ ] Return a real feedback ID and receipt status to the frontend.
- [ ] Preserve user-entered form data on errors and prevent accidental double submission.
- [ ] Do not silently turn browser sample feedback into authenticated production evidence.

**Acceptance:** Double-clicking Submit or retrying after a network interruption does
not create duplicate feedback. A queue outage does not lose committed feedback or
permanently prevent its later analysis.

## 12. P7: Python Workflows, Celery, and Live Updates

- [ ] Implement Python LangGraph state schemas and explicit workflow nodes.
- [ ] Build requirement/build and feedback-analysis flows incrementally.
- [ ] Persist workflow_runs and workflow_events in PostgreSQL.
- [ ] Define durable checkpoints and restart/resume behavior.
- [ ] Add bounded retries, retry backoff, failure classification, and manual retry controls.
- [ ] Make every side-effecting node idempotent under Celery redelivery.
- [ ] Preserve input IDs, entity versions, provenance, timestamps, errors, and retry counts.
- [ ] Add authenticated WebSocket access at `/ws/ideas/{id}`.
- [ ] Authorize subscriptions against idea ownership or reviewer assignment.
- [ ] Emit persisted-state events only after the corresponding database transaction commits.
- [ ] Support feedback received/analysis, trust, consensus, priorities, evolution, dashboard, and failure events from the blueprint.
- [ ] Add event IDs/order handling, reconnect behavior, and API state resynchronization.
- [ ] Treat WebSocket messages as notifications, not the durable source of truth.
- [ ] Connect the workflow monitor to real runs and provide loading, failure, retry, and disconnected states.

**Acceptance:** A submitted review produces visible live status transitions. Killing
and restarting a worker does not lose the review or create duplicate analytical results.

## 13. P8: Feedback Quality and Deterministic Trust

### Python Quality Agent

- [ ] Define relevance, originality, constructiveness, consistency, spam risk, bias risk, authenticity indicator, and confidence schemas.
- [ ] Ground indicators in feedback, prototype context, and permitted reviewer history.
- [ ] Persist analysis evidence and model/prompt/workflow provenance.
- [ ] Add handling for empty, irrelevant, duplicate, adversarial, and ambiguous feedback.
- [ ] Provide appropriate human moderation/review paths.
- [ ] Never label a person or review as proven fake based on AI output.

### Deterministic Trust Engine

Implement the blueprint baseline in Python:

```text
Trust = 0.30 * Review Quality
      + 0.20 * Historical Accuracy
      + 0.15 * Peer Alignment
      + 0.15 * Consistency
      + 0.10 * Verified Expertise
      + 0.10 * Community Validation
```

- [ ] Normalize each factor to [0, 1] and validate numerical inputs.
- [ ] Define where every factor comes from and what evidence is required.
- [ ] Document cold-start and missing-factor behavior; do not invent historical accuracy for a new reviewer.
- [ ] Distinguish measured, inferred, unavailable, and overridden factors.
- [ ] Keep the formula deterministic; the LLM must not choose the final numerical score.
- [ ] Persist trust_snapshots with score, factor_json, formula_version, source evidence, and timestamps.
- [ ] Version formula changes and retain old snapshots for reproducibility.
- [ ] Prevent reviewers and owners from changing trust scores.
- [ ] Audit any approved administrative override.
- [ ] Connect trust factor breakdowns, evidence links, and quality/confidence views.

**Acceptance:** The same validated factor inputs produce the same score. Tests cover
boundaries, missing evidence, formula versions, and unauthorized modifications.

## 14. P9: Embeddings, Clustering, Consensus, and Priorities

### Semantic Analysis

- [ ] Generate embeddings with the approved Bedrock embedding model.
- [ ] Store vectors and source metadata in feedback_embeddings using pgvector.
- [ ] Fix and validate embedding dimensions and model/version compatibility.
- [ ] Add cosine-similarity queries, appropriate indexes, and tenant/project isolation.
- [ ] Implement near-duplicate detection, topic grouping, sentiment, and issue categories.
- [ ] Define clustering thresholds and minimum-data behavior using evaluation evidence.
- [ ] Retain supporting feedback IDs for every theme and cluster.
- [ ] Show insufficient-data and uncertainty states rather than forcing clusters.

### Consensus

```text
Feedback weight = Trust score * Authenticity score * Relevance score
Normalized weight = Feedback weight / Sum of eligible feedback weights
```

- [ ] Define how quality indicators map to bounded aggregation inputs.
- [ ] Compute raw support and trust-weighted support separately.
- [ ] Handle missing factors, empty feedback, and zero total weight explicitly.
- [ ] Define confidence and coverage with a documented, testable method.
- [ ] Persist consensus_results with evidence IDs, source versions, formula/config version, and workflow metadata.
- [ ] Keep disagreement and minority concerns visible.

### Prioritization

- [ ] Define the ranking policy for P1/P2/P3 feature improvements.
- [ ] Combine support, trust coverage, impact, feasibility, and constraints according to documented rules.
- [ ] Keep agent rationale separate from deterministic numeric calculations.
- [ ] Persist feature_priorities, rank, rationale, evidence IDs, and provenance.
- [ ] Connect semantic themes, trust distribution, raw/weighted charts, and the feature-priority matrix.

**Acceptance:** Stored evidence reproduces reported aggregates. A zero-weight dataset
cannot produce a misleading confidence claim or a divide-by-zero failure.

## 15. P10: Python Evolution Agent and Real V2

- [ ] Make evolution an explicit authorized action, not an automatic overwrite.
- [ ] Load the immutable source version, analyzed feedback, priorities, and consensus.
- [ ] Generate a typed change set and new requirements with per-change evidence IDs.
- [ ] Persist evolution_results, source/target versions, rationale, assumptions, and AI provenance.
- [ ] Reject unsupported or evidence-free changes according to the approved policy.
- [ ] Create a separate target-version candidate and use the isolated builder to produce V2.
- [ ] Validate the new artifact before exposing it as a ready V2 prototype.
- [ ] Preserve V1 and its review evidence if generation, building, or validation fails.
- [ ] Define retry/resume behavior without duplicate versions.
- [ ] Connect the comparison screen, timeline, evidence links, V1 launch, and V2 launch.
- [ ] Distinguish proposed, building, failed, and validated versions in the UI.

**Acceptance:** A real evidence-backed V2 prototype exists and demonstrates the
accepted changes. V1 remains accessible and unchanged throughout the process.

## 16. P11: Decision Intelligence and Real Dashboard Data

- [ ] Implement the Python Decision Agent using persisted evidence, not unrelated assumptions.
- [ ] Include validation summary, strengths, concerns, consensus, confidence, priorities, evolution, and next actions.
- [ ] Persist reports and provenance; place downloadable artifacts in the approved S3 location.
- [ ] Make each important statement traceable to authorized feedback/analysis/version records.
- [ ] Add report loading, pending, failure, stale-data, download, and print states.
- [ ] Replace preview counts and charts with typed analytics API responses.
- [ ] Show raw versus weighted results and analyzed versus unanalyzed coverage.
- [ ] Define cache invalidation and event-driven dashboard refresh behavior.
- [ ] Keep uncertainty and insufficient evidence visible in recommendations.
- [ ] Never show simulated evaluation metrics as measured KPIs.

**Acceptance:** The owner can inspect a report, follow its evidence links, reproduce
its numerical aggregates, and see exactly which idea and prototype versions it covers.

## 17. Database Work by Phase

Do not create placeholder tables merely to match a diagram. Add models, constraints,
migrations, repositories, and database tests with the phase that uses them.

| Entity group | Phase | Important constraints |
| --- | --- | --- |
| users, organizations | P1 | Unique identities, roles, ownership/tenant isolation |
| ideas, idea_versions, idea_assets | P2 | Version uniqueness, immutable snapshots, authorized assets |
| requirement_specs | P3 | Source version and workflow/model/prompt provenance |
| prototypes, prototype_builds, prototype_events | P4 | Versioned artifacts, validated transitions, logs |
| reviewer_profiles, review_assignments, review_sessions | P5 | Assignment uniqueness and version/session integrity |
| feedback | P6 | Idempotency, ownership, session and version links |
| workflow_runs, workflow_events | P3-P7 | Durable status, resume/retry, event ordering |
| feedback_analysis, trust_snapshots | P8 | Evidence, bounded inputs, formula/provenance history |
| feedback_embeddings, consensus_results, feature_priorities | P9 | Model-compatible vectors and reproducible aggregates |
| evolution_results | P10 | Separate source/target versions and evidence-backed changes |
| reports | P11 | Traceable evidence, authorized artifact access |
| audit_logs, notifications | Incrementally | Actor/action/entity context and delivery state |

A durable outbox/checkpoint schema may be needed as an implementation detail; document
it before adding it. Test upgrade paths, foreign keys, uniqueness, query indexes,
transaction rollback, and deletion/retention rules against real PostgreSQL.

## 18. API and Frontend Integration Checklist

The blueprint's API contracts must be implemented with typed requests, responses,
authorization, validation, and consistent error handling.

| API group | Required endpoint surface | Frontend connection |
| --- | --- | --- |
| Auth | `POST /api/v1/auth/register`, `POST /api/v1/auth/login` | Sign-in, registration, session identity |
| Ideas | `POST /api/v1/ideas`, `GET/PUT /api/v1/ideas/{id}` | Submission and version-aware details |
| Build | `POST /api/v1/ideas/{id}/build` | Start generation and monitor progress |
| Prototype | `GET /api/v1/ideas/{id}/prototype`, `GET /api/v1/ideas/{id}/prototype/preview` | Manifest, status and authorized artifact launch |
| Publish | `POST /api/v1/projects/{id}/publish` | Open a valid review cycle |
| Assignments | `POST /api/v1/assignments`, `GET /api/v1/reviewer/projects` | Admin assignment and reviewer queue |
| Sessions | `POST /api/v1/reviewer/{id}/start` | Version-linked review session |
| Feedback | `POST/GET /api/v1/ideas/{id}/feedback` | Durable submission and evidence lists |
| Analytics | `GET /api/v1/ideas/{id}/analytics` | Real metrics and chart data |
| Trust | `GET /api/v1/ideas/{id}/trust` | Factor history and quality context |
| Consensus | `GET /api/v1/ideas/{id}/consensus` | Raw/weighted results and evidence |
| Evolution | `GET /api/v1/ideas/{id}/evolution`, `POST /api/v1/ideas/{id}/evolve` | Proposals, validated versions and comparison |
| Workflows | `GET /api/v1/workflows/{run_id}` | Run state, failures and recovery |
| Reports | `GET /api/v1/reports/{idea_id}` | Decision report and artifact access |
| Events | `WS /ws/ideas/{id}` | Authorized live updates |

- [ ] Resolve ambiguous resource IDs, pagination, list/search endpoints, upload endpoints, and auth lifecycle endpoints in the API specification before coding them.
- [ ] Ensure PUT semantics do not overwrite immutable original versions.
- [ ] Generate or maintain TypeScript contracts aligned with FastAPI OpenAPI schemas.
- [ ] Add a centralized API client, session handling, cancellation, error mapping, and retry rules.
- [ ] Retry mutations only when their idempotency contract makes it safe.
- [ ] Keep preview and production data sources explicitly separate.
- [ ] Never fall back to fixtures automatically when the production API fails.
- [ ] Disable sample role switching, mock identities, and local-only mutation paths in production mode.
- [ ] Add loading, empty, validation, forbidden, expired-session, timeout, and retry states to each connected screen.
- [ ] Preserve filters/navigation and prevent stale responses from replacing the current view.
- [ ] Add accessible names, focus handling, keyboard navigation, contrast checks, and screen-reader announcements.
- [ ] Recheck layouts across small mobile, tablet, desktop, long text, and zoomed viewports.
- [ ] Add real upload progress and prototype sandbox/iframe policies where embedding is used.

Relevant current code: [preview actions](../frontend/src/services/preview.ts),
[workspace provider](../frontend/src/services/workspace.tsx), and
[browser acceptance tests](../frontend/tests/workspace.spec.ts).

## 19. Security, Privacy, and Audit Gates

These are incremental requirements, not a final cleanup phase.

- [ ] Require TLS for deployed APIs, WebSockets, uploads, and previews.
- [ ] Restrict CORS to approved origins; do not combine broad origins with credentials.
- [ ] Apply CSRF protection if the chosen session design uses cookies.
- [ ] Test object-level authorization and cross-organization isolation on every endpoint.
- [ ] Sanitize rendered model output and never execute returned HTML/scripts as trusted application code.
- [ ] Treat prompts, documents, feedback, and generated code as untrusted inputs.
- [ ] Implement rate limits, request-size limits, per-user quotas, and costly-operation budgets.
- [ ] Protect upload/download/preview URLs and document expiry behavior.
- [ ] Add private object storage and least-privilege IAM roles.
- [ ] Keep secrets in AWS Secrets Manager for production; never ship them in Vite environment variables.
- [ ] Mask or exclude sensitive information from logs, analytics, traces, and prompts.
- [ ] Define data consent, retention, account deletion, report retention, and reviewer privacy rules.
- [ ] Audit login events, version creation, builds, publishing, assignments, feedback, trust changes, consensus, evolution, and overrides.
- [ ] Record actor, action, entity, timestamp, before/after context, and workflow correlation where applicable.
- [ ] Restrict audit access and prevent ordinary users from changing audit history.
- [ ] Test sandbox escape boundaries, denied egress, resource exhaustion, and artifact cleanup before enabling AI builds.
- [ ] Add dependency and secret scanning to CI; add container scanning only if containers are later explicitly approved.

## 20. P12: AWS Deployment Without Assuming Docker

### Architecture Decision Required

The master blueprint lists ECS/Fargate and ECR, which are container-oriented.
The user's no-Docker direction is already recorded in [DECISIONS.md](DECISIONS.md).
Do not silently deploy containers or silently substitute a new compute architecture.

- [ ] Confirm whether the no-Docker constraint covers production as well as local development.
- [ ] Approve a Python API/worker compute option compatible with the confirmed constraint.
- [ ] If production must be container-free, evaluate native Python processes on managed Linux/EC2 as a candidate, not an already approved choice.
- [ ] Approve a separate isolated prototype-build environment.
- [ ] Document topology, scaling, deployment, patching, process supervision, and recovery responsibilities.

### AWS Services and Configuration

- [ ] Select region, account/environment separation, tags, budget, and cost alerts.
- [ ] Set up least-privilege IAM roles and separate API, worker, build, and deployment permissions.
- [ ] Configure VPC, private subnets, security groups, and required service connectivity.
- [ ] Provision RDS PostgreSQL and confirm pgvector/version compatibility.
- [ ] Provision ElastiCache Redis with appropriate authentication, encryption, and network restrictions.
- [ ] Create separate S3 storage boundaries for frontend, uploads, prototypes, and reports.
- [ ] Configure CloudFront with private S3 origins, cache behavior, invalidation/versioned assets, and error handling.
- [ ] Keep prototype hosting separate from the main application's origin and credentials.
- [ ] Enable approved Bedrock models and embedding access for the selected region.
- [ ] Configure Secrets Manager and rotation/access policies.
- [ ] Configure ALB/API routing, Route 53 DNS, and ACM certificates for the approved topology.
- [ ] Preserve support for long-running jobs and authenticated WebSocket connections.
- [ ] Configure CloudWatch logs, metrics, dashboards, retention, and alarms.
- [ ] Implement database backup, recovery, and tested restoration procedures.
- [ ] Define Redis outage behavior and recovery from PostgreSQL-backed durable work.
- [ ] Add infrastructure-as-code after selecting and documenting the deployment approach.

### Release Pipeline

- [ ] Use short-lived GitHub Actions AWS credentials through an approved identity-federation setup.
- [ ] Build and publish the frontend artifact to staging.
- [ ] Package and deploy Python API/worker code using the approved non-Docker path.
- [ ] Run migrations as a controlled deployment step, not independently from every API instance.
- [ ] Run smoke and integration tests against staging.
- [ ] Require production approval and define rollback behavior.
- [ ] Distinguish application rollback from database migration recovery.
- [ ] Validate a backup restore and a worker restart/recovery scenario before launch.
- [ ] Confirm no sample workspace records or preview-only authentication controls appear in production.

**Acceptance:** HTTPS frontend, API, worker, database, Redis, S3 artifacts, Bedrock,
events, monitoring, backup, and rollback all work on the approved AWS topology.

## 21. Testing and CI Work Still Required

### Backend

- [ ] Unit tests for services, validation, deterministic trust, and consensus edge cases.
- [ ] API contract tests for request/response schemas and error behavior.
- [ ] Authentication, role, ownership, and cross-tenant authorization tests.
- [ ] Real PostgreSQL tests for migrations, constraints, transactions, immutable versions, and vector operations.
- [ ] Real Redis/Celery tests for duplicate delivery, retries, outbox dispatch, and worker restarts.
- [ ] LangGraph tests for success, malformed output, provider failure, resume, and terminal failure states.
- [ ] Bedrock integration tests with controlled budgets, separated from offline unit tests.
- [ ] Upload validation, private asset access, and prototype sandbox security tests.
- [ ] Numerical reproducibility tests for weighted results and versioned formulas.

### Frontend and End to End

- [ ] Keep the existing preview tests passing as regression coverage.
- [ ] Add API-backed tests rather than treating localStorage tests as persistence acceptance.
- [ ] Test real sessions, expired sessions, denied access, and logout.
- [ ] Test upload failures, real build failures, retry, and validated artifact launch.
- [ ] Test feedback idempotency, disconnected submission, WebSocket reconnect, and state resync.
- [ ] Test evidence links across reports, consensus, priorities, and version comparisons.
- [ ] Test supported browser/device combinations, keyboard access, contrast, and screen-reader behavior.
- [ ] Test long lists, pagination, slow responses, empty datasets, and concurrent updates.
- [ ] Add staging smoke tests and the complete single-idea acceptance scenario.

### CI

- [ ] Execute and inspect the configured GitHub workflow on a real branch/PR.
- [ ] Provide a non-Docker integration-test environment or dedicated managed test services.
- [ ] Run migrations, backend tests, frontend lint/typecheck/tests/build, and browser tests.
- [ ] Add dependency/security checks and retain useful test artifacts without leaking secrets.
- [ ] Prevent deployment when required checks fail.

## 22. Single-Idea Acceptance Test: Required Before MVP Completion

Use the AI College Placement Assistant example with actual persisted data and real
provider calls. The current hand-authored Campus Compass preview is not a substitute.

1. [ ] Register/login as an idea owner.
2. [ ] Submit the problem, target users, solution, features, constraints, and an optional reference asset.
3. [ ] Confirm idea V1 and assets persist in PostgreSQL/S3.
4. [ ] Run the Python Requirement Agent and inspect its stored structured result.
5. [ ] Run the Python Builder workflow in the approved isolated environment.
6. [ ] Inspect real build/type/lint/test results and the versioned artifact.
7. [ ] Launch the generated V1 and complete a meaningful interaction across its screens.
8. [ ] Publish the immutable V1 review cycle.
9. [ ] Assign an authenticated reviewer and open another browser session.
10. [ ] Launch the assigned V1, perform a journey, and establish a real review session.
11. [ ] Submit structured feedback and confirm immediate PostgreSQL persistence.
12. [ ] Retry the same submission and confirm no duplicate feedback.
13. [ ] Observe Celery/LangGraph processing and authorized live UI updates.
14. [ ] Inspect quality indicators, confidence, and deterministic trust evidence.
15. [ ] Collect multiple real reviews and inspect embeddings/clusters.
16. [ ] Compare raw and trust-weighted consensus, including supporting feedback IDs.
17. [ ] Inspect prioritized improvements and their rationale.
18. [ ] Start evolution explicitly and inspect the persisted V2 change set.
19. [ ] Build and validate V2, confirming V1 is unchanged.
20. [ ] Launch V2 and verify the intended improvements actually exist.
21. [ ] Open a persisted decision report and follow its evidence links.
22. [ ] Verify role isolation and test at least one failure/retry path.
23. [ ] Repeat the important flow in AWS staging before production approval.

## 23. P13: Research and Evaluation

This is required for the blueprint's research deliverable, not a reason to invent
numbers on the product dashboard.

- [ ] Define consented/anonymized datasets, expert labels, splits, and evaluation protocols.
- [ ] Compare reviewer keyword matching with embedding matching using Precision@K, Recall@K, and MRR.
- [ ] Compare rule-based, ML, LLM-assisted, and hybrid quality analysis.
- [ ] Measure accuracy, precision, recall, F1, and ROC-AUC where the task and labels support them.
- [ ] Compare majority and trust-weighted consensus against expert labels.
- [ ] Evaluate ranking correlation, stability, cold-start behavior, and disagreement handling.
- [ ] Evaluate clustering using appropriate Silhouette and Davies-Bouldin measurements.
- [ ] Have humans evaluate evolution relevance, completeness, evidence coverage, actionability, and consistency.
- [ ] Record dataset versions, model/prompt versions, parameters, seeds, and experiment outputs.
- [ ] Avoid data leakage and report uncertainty, limitations, and failed cases.
- [ ] Publish only measurements actually produced by reproducible experiments.

## 24. Documentation Still to Write

Create these documents as their owning features are implemented. Planned filenames
below are not claims that the documents already exist.

| Planned document | Contents |
| --- | --- |
| `docs/DATABASE_SCHEMA.md` | Entities, ownership, constraints, indexes, migrations, retention |
| `docs/API_SPEC.md` | Typed endpoints, permissions, errors, pagination, idempotency |
| `docs/AGENT_SPEC.md` | Python agent inputs/outputs, providers, provenance, failure policy |
| `docs/WORKFLOW_SPEC.md` | LangGraph states, transactions, checkpoints, events, retries |
| `docs/PROTOTYPE_BUILDER_SPEC.md` | Templates, allowlists, sandbox, validation, artifacts, hosting |
| `docs/SECURITY.md` | Threat model, auth, uploads, prompt injection, isolation, privacy |
| `docs/DEPLOYMENT.md` | Approved no-Docker/AWS architecture, setup, release, rollback, recovery |
| `docs/EVALUATION.md` | Datasets, baselines, metrics, reproducibility, limitations |

Update [DECISIONS.md](DECISIONS.md) whenever an approved implementation choice differs
from the master blueprint. Update this checklist and [SETUP_STATUS.md](SETUP_STATUS.md)
with evidence after each phase passes its acceptance tests.

## 25. Definition of Done for Each Feature

- [ ] Requirement and ownership are clear.
- [ ] Required models, constraints, and versioned migrations exist.
- [ ] Pydantic schemas, repository/service logic, and API contracts are implemented.
- [ ] Server-side authorization and input validation are tested.
- [ ] Frontend uses real responses and has correct loading/error/empty states.
- [ ] Data survives refresh, worker restart, and relevant failure/retry scenarios.
- [ ] Important outputs have evidence, version, and workflow provenance.
- [ ] Audit/logging requirements are met without exposing secrets.
- [ ] Unit, integration, and applicable end-to-end acceptance tests pass.
- [ ] Documentation and known limitations are updated.
- [ ] No sample behavior is presented as a completed production capability.

## 26. Immediate Next Work Session

Focus on the smallest real vertical slice before adding more AI modules:

1. Select and provision native/managed PostgreSQL and Redis endpoints; Python dependencies are now installed.
2. Run the existing migrations and health/worker integration checks without Docker.
3. Specify user/organization ownership and implement the first auth models and endpoints.
4. Connect the existing sign-in screen to the real Python API.
5. Test owner/reviewer/admin authorization before moving to persistent idea submission.

Do not provision paid AWS resources, choose a replacement compute architecture, or
execute generated code merely because it appears on this checklist. Those actions
require the relevant environment, security design, and deployment decisions first.