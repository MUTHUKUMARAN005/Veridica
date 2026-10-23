# Veridica: Detailed Remaining Work

**Updated:** 2026-10-23
**Purpose:** Implementation checklist from the current local foundation to the
verified single-idea MVP. Cloud deployment is a later, separately approved phase.
**Current milestone:** Phases 1-7 are implemented with acceptance limitations
documented; Phase 8's local persisted-workflow integration test and available
service checks pass. The Builder cannot execute/build/publish without a reviewed
isolation boundary. Phase 8's end-to-end test uses deterministic provider doubles;
live model inference is unverified. Trust has only partial feedback-level evidence.
V2 remains Draft/source-only. Audited role provisioning, live-provider analysis,
isolated builds, deployment-grade reports, complete trust evidence, and production
data protections remain outstanding.

## 1. Read This First

The frontend is ready to explore, but the complete Veridica application is not finished.
Phase 7 includes owner-approved evidence-linked candidate creation and persisted
decision reports. Phase 8 verified the local integration flow and restarted the
stale worker with the current tasks. Remaining acceptance blockers are a verified
real model provider, audited role provisioning, the reviewed prototype build
boundary, and production data-protection controls. Generated source must not be
executed, reviewed as a working prototype, or published before isolation exists.
Idea APIs, version history, review cycles, assignments, sessions, feedback,
requirement runs, prototype source records, feedback analysis, evolution proposals,
and report snapshots are database-backed; local asset/source storage remains
development-only.

The architecture source of truth is [PROJECT_SPEC.md](PROJECT_SPEC.md).
User-requested adjustments are recorded in [DECISIONS.md](DECISIONS.md).
Previous verification results are in [SETUP_STATUS.md](SETUP_STATUS.md).
This checklist does not replace those documents or claim unimplemented features are complete.

**Free-local implementation update:** the [README](../README.md) defines the active
no-AWS stack: native PostgreSQL/pgvector, Redis, Celery, and Ollama. Ollama is the
default development provider; Gemini Developer API is available only as a backend
development opt-in because the master blueprint prohibits Gemini as a production
provider. Requirement outputs are typed and persisted, but actual provider output
remains unverified until a real configured model call succeeds.

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
| Offline preview selector chooses a sample role | A controlled admin bootstrap and audited role-change process |
| Preview ideas and reviews live in localStorage | Persistent assets, prototype sessions, and later analysis workflows |
| Upload selection keeps filenames | Validated uploads, S3 objects, and asset metadata |
| Preview prototype screens include hand-authored samples | Persisted Requirement Agent and safe Builder source generation are implemented; an isolated build/preview boundary is still missing |
| Offline preview publication, assignments, and reviews are browser-local | These fixtures remain separate from authenticated API records |
| Authenticated reviewers submit structured feedback for an assigned immutable idea version | Real prototype access and human moderation; quality/NLP analysis and version-scoped analytics are implemented |
| Ratings produce simple local averages | Broader prototype access and human moderation; version-scoped feedback analytics are implemented |
| Authenticated trust/quality pages show persisted results and workflow states | Live provider verification and five unsupported trust factors remain unavailable |
| Consensus shows raw support | Version-scoped weighted consensus and an explicitly uncalibrated uncertainty indicator are implemented |
| Preview Evolution copies selected suggestions into a local proposal | Owner-scoped evidence-linked proposal, explicit approval, and immutable Draft candidate; isolated validated V2 is blocked |
| Preview report export summarizes local records | Persisted owner-scoped decision report snapshot from versioned evidence; exports and report-diff verification remain |
| Activity view shows local events | Workflow runs, live events, durable audit, and failure recovery |

The backend exposes health, authentication, owner-scoped idea/version routes,
version publication, exact-version reviewer assignments and sessions, idempotent
structured feedback, owner-authorized analysis routes, and narrow admin assignment
operations from [main.py](../backend/app/main.py). Current business entities live
in [entities.py](../backend/app/models/entities.py). Analysis runs and embedding
records are persisted; standalone workflow events, generalized live progress,
complete trust evidence and generalized workflow event entities remain pending.

## 4. Recommended Implementation Order

| Order | Blueprint phase | Main deliverable | Depends on |
| --- | --- | --- | --- |
| 1 | P1 | Real reviewer/admin authorization, ownership policy, and security acceptance tests — implemented; admin provisioning remains blocked | Verified P0 services and existing owner-auth slice |
| 2 | P2 | Persistent idea lifecycle, pagination, version history, and local private assets — implemented; production scanning/storage remain blocked | P1 and PostgreSQL |
| 3 | P3 | Validated, persisted Requirement Agent outputs, owner-scoped API, Celery execution, and connected UI — implemented; real model integration remains unverified | P2 and configured AI provider |
| 4 | P4 | Safe source generation for one supported category is implemented; isolated execution, build, and reviewable preview remain blocked | P3; sandbox must be separately approved |
| 5 | P5 | Prototype publishing/access; idea-version review publishing, assignments, sessions, and durable feedback foundation implemented | P4 isolated artifact for generated prototype access |
| 6 | P6-P9 | Persisted quality/NLP analysis, partial deterministic trust, pgvector similarity, weighted consensus, and evidence-linked priorities — implemented; live model and unsupported trust factors remain unverified | Durable feedback and configured worker |
| 7 | P10-P11 | Owner-approved evidence-linked evolution candidates and persisted decision-report snapshots — implemented; validated working V2 and report export/reproduction hardening remain blocked | P6-P9; isolated prototype build boundary |
| 8 | P12 | Separately approved deployment architecture and staging/production | Security gates and real E2E |
| 9 | P13 | Reproducible research evaluation | Stable product and labeled datasets |

Connect each frontend feature as its backend phase becomes usable. Do not wait until
all backend modules exist, and do not mark a phase done merely because its screen exists.
Bedrock and S3 access may be needed before the full AWS deployment phase.

## 5. P0: Finish the Python Development Foundation

**Local acceptance status (2026-10-23): passed.** PostgreSQL/pgvector, Redis,
migrations, FastAPI readiness, and a real Celery task were verified using the
existing local services. Backend unit/integration tests, Ruff, frontend tests,
lint, typecheck, build, and browser acceptance tests passed. This does not complete
production hardening or verify service-restart persistence.

### Environment and Services

- [x] Recheck Python package installation and network/DNS access; installation succeeded on 2026-09-30.
- [x] Install backend development dependencies into the existing virtual environment.
- [x] Verify the existing local PostgreSQL service and usable pgvector extension; no database or cluster was recreated.
- [x] Verify the existing local Redis service.
- [x] Configure development DATABASE_URL and REDIS_URL in ignored local `.env`; keep secrets untracked.
- [ ] Replace sample credentials for any shared or remotely reachable environment.
- [x] Verify Alembic revision `0003` on the configured development database and run `upgrade head` without resetting data.
- [x] Start FastAPI directly with Python/Uvicorn.
- [x] Run Celery under the Linux Codespace environment.
- [x] Verify native API liveness and honest unavailable-dependency readiness responses.
- [x] Verify readiness with real PostgreSQL/Redis and execute the live Celery integration task.
- [ ] Add reproducible Python dependency locking and review dependency vulnerabilities.
- [ ] Separate development, test, staging, and production configuration.
- [x] Add startup validation for APP_ENV, the synchronous database driver, explicit CORS origins, non-sample production database credentials, and Redis TLS in production.
- [x] Hide configuration inputs in validation error text and test secret redaction.
- [ ] Add feature-specific startup validation for future auth/AWS settings and audit all logging for sensitive values.

### Exit Criteria

- [x] A real database connection succeeds and pgvector is available and usable.
- [x] Redis responds and a queued task is executed by a separate Python worker.
- [x] Backend unit and integration tests pass against the available service versions.
- [ ] Services can restart without losing database records.
- [x] No Docker command is needed for the selected development setup.

## 6. P1: Authentication and Real Portals

**Implementation status (2026-10-23):** Backend ownership checks, reviewer
assignment-scoped version access, persisted review submission, and restricted admin
assignment operations are implemented and tested. Authenticated owner/reviewer/admin
screens consume server-backed results. Admin bootstrap/audited role changes and
production account lifecycle flows remain blocked.

### Identity and Authorization

- [x] Decide and document current owner/resource boundaries; multi-organization access remains future scope.
- [x] Add the initial user model, migration, schema, and session boundary.
- [x] Implement registration, login, and scrypt password hashing for local development.
- [x] Document signed bearer token expiry and in-memory frontend token handling.
- [ ] Implement account verification and recovery flows needed for the launch scope.
- [x] Prevent public registration from granting elevated privileges; unexpected role input is rejected.
- [x] Implement server-side owner/resource authorization for the idea endpoints.
- [ ] Enforce organization/resource ownership on every protected endpoint.
- [x] Limit reviewer access to exact active assignments and version-bound structured reviews.
- [ ] Provide a reviewed, audited operator process for provisioning reviewer/admin roles.
- [ ] Add authentication rate limits and appropriate handling of repeated failed attempts.
- [ ] Record security events without logging passwords or tokens.

### Frontend Connection

- [x] Connect sign-in/register forms to Python APIs.
- [x] Show API identity and preserve a separate offline preview mode.
- [ ] Add session loading, expired-session, forbidden, and signed-out states.
- [x] Add authenticated role-aware route guards for usability, while keeping the server as the security boundary.
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
- [x] Specify that content edits create a new version with expected-version concurrency checks and a change summary.
- [x] Preserve immutable version snapshots with database-enforced update/delete protection and source lineage.
- [x] Add row locking and conflict handling for concurrent version creation.
- [x] Make supported Draft/Archived lifecycle transitions explicit; block archiving with active reviewer assignments.
- [x] Add pagination, status/category/text filtering, and stable ordering.
- [x] Define non-destructive archiving and restoration; hard deletion is not exposed.
- [x] Store title, problem, target users, solution, features, constraints, category, owner, and timestamps with server validation.

### Real File Handling

- [ ] Configure private S3 upload storage and least-privilege permissions.
- [x] Validate supported file types, file signatures, sizes, and filenames on the server; uploads are limited to one file per request and capped at 10 MiB.
- [ ] Add malware scanning/quarantine or an equivalent reviewed file-safety policy.
- [x] Authorize private downloads through the authenticated API; files are not exposed through public URLs.
- [x] Store per-version asset metadata and checksums in PostgreSQL. Local file storage uses opaque keys and restrictive permissions.
- [ ] Add malware scanning/quarantine, production S3 storage, orphan cleanup, upload idempotency, and durable retry handling.
- [ ] Extract document/image content using an approved ingestion path before requirement analysis.
- [x] Connect authenticated uploads with busy/error states and retry by re-uploading from idea details; preview mode remains filename-only.

**Local acceptance verified:** an owner can create an idea, upload a supported reference,
refresh or use another authenticated session, and retrieve authorized version/asset
records from PostgreSQL and local private storage. Production object storage and
malware-safety acceptance remain blocked.

## 8. P3: Python Requirement Agent

- [ ] Configure the approved production Bedrock model, region, permissions, and invocation limits.
- [x] Keep provider calls behind a Python adapter with bounded timeouts and classified retry handling (local Ollama default; optional Gemini adapter is development-only).
- [x] Define a typed requirement-output schema for problem, target users, user journeys, core features, constraints, assumptions, acceptance criteria, and open questions.
- [ ] Treat uploaded text and images as untrusted input, not agent instructions.
- [ ] Separate system instructions, user content, and retrieved material in prompts.
- [x] Validate structured output and reject malformed or unsupported specifications.
- [x] Persist validated results and analysis-run status in PostgreSQL rather than worker memory alone.
- [x] Persist workflow_run_id, provider/model, prompt_version, source idea version, status, timestamps, validation state, attempts, and errors.
- [x] Add a versioned prompt and deterministic tests for schema validation, failures, authorization, retries, and persistence.
- [x] Run analysis asynchronously through Celery with visible status and retry states.
- [x] Connect the Requirements tab to persisted results and provenance.
- [ ] Keep owner-written requirements visibly distinct from agent-generated requirements.

**Local implementation:** The workflow, APIs, persistence, and frontend integration
are implemented. Mocked provider tests validate the workflow without a paid call.
Production Bedrock integration, an actual live model invocation, and content
extraction from uploaded assets remain unverified or incomplete; do not claim that a
mocked output proves real-provider acceptance.

## 9. P4: Python AI Builder and Isolated Prototype Generation

### Controlled MVP Scope

- [x] Start with one supported category: education placement preparation.
- [x] Define one fixed template, component plan, React/TypeScript/Vite dependency set, scripts, and local-only interactions.
- [x] Implement deterministic Python generation around a completed, validated Requirement Agent result linked to an immutable source version.
- [x] Generate typed screen/component plans, a manifest, and separate React/TypeScript/JSON/CSS source.
- [x] Store explicit features, requirements provenance, limitations, source hashes, and source metadata.
- [x] Validate file paths, traversal, source capabilities/imports, scripts, dependencies, required files, and source size.

### Isolation: Required Before Any Generated Build Runs

- [ ] Approve a sandbox design compatible with the no-Docker requirement.
- [ ] Evaluate an isolated VM or equivalent reviewed execution boundary; this is a proposal, not a selected architecture.
- [ ] Separate sandbox compute, identity, filesystem, and network access from the API and normal worker.
- [ ] Deny access to application secrets, database credentials, and instance metadata credentials.
- [ ] Restrict network egress and dependency installation to the approved policy.
- [ ] Enforce CPU, memory, disk, process, runtime, and artifact-size limits.
- [ ] Use nonprivileged execution and clean up the environment after each build.
- [ ] Never run generated server code or user-provided commands in FastAPI.

**Codespaces status:** No approved disposable isolation boundary is available. The
implemented Builder stops at private source generation and static validation. It
does not run Node/npm/Vite, does not claim source is a working prototype, and cannot
test real build timeouts or resource limits until a sandbox exists.

### Build and Delivery

- [ ] Run dependency validation, lint, typecheck, production build, and supported interaction checks.
- [ ] Capture build/test output, errors, timing, and retry count.
- [x] Persist prototype build records with immutable idea and requirement source IDs, template/workflow versions, validation results, source metadata, and blocked build/publish states.
- [ ] Enforce DRAFT -> BUILDING -> VALIDATING -> READY or FAILED transitions.
- [ ] Publish only validated, versioned static artifacts to S3.
- [ ] Serve previews on an isolated origin with an appropriate CSP and access policy.
- [ ] Add authorized preview URLs and expiration/access behavior.
- [x] Connect generated-source status, validation, failure, limitation, and safe source inspection to the authenticated owner UI.
- [ ] Never show a successful build or preview URL unless the real artifact exists.

**Acceptance still blocked:** The owner can generate an immutable-version-linked
source artifact and inspect static validation results. It is not a built prototype;
an isolated build, browser interaction test, private preview, and reviewer launch
remain unimplemented until the required boundary is provided. Unsupported ideas
receive an honest persisted unsupported state.

## 10. P5: Publishing, Assignments, and Review Sessions

- [ ] Implement server-side project publishing only for a validated prototype.
- [ ] Freeze the specific idea/prototype version when its review cycle opens.
- [ ] Persist reviewer profiles and prototype-bound review sessions.
- [x] Implement version-specific admin assignments with duplicate prevention and actor/timestamp fields.
- [x] Expose the reviewer queue for active assignments and exact assigned versions.
- [ ] Start a review session tied to reviewer, assignment, idea version, and prototype version.
- [ ] Record permitted session activity and journey progress under a documented privacy policy.
- [ ] Define abandonment, timeout, resume, completion, and closed-cycle behavior.
- [ ] Add reviewer matching with a keyword baseline, then evaluate Bedrock embedding matching.
- [ ] Keep manual admin assignment available while matching is evaluated.
- [ ] Connect queue, launch, journey, session, and completion UI states to the backend.

**Acceptance:** An assigned reviewer in a separate authenticated session can launch
the correct immutable prototype. An unassigned user cannot obtain access by guessing IDs.

## 11. P6: Real Feedback and Durable Submission — implemented

- [x] Create feedback records with actor, session, assignment, idea, and exact-version references.
- [x] Persist required ratings, would-use response, bounded text, strengths, concerns, improvements, and usage context.
- [x] Enforce rating ranges, content limits, ownership, session validity, and open-cycle rules in Python.
- [x] Define idempotent submission and same-key replay behavior.
- [x] Commit feedback and outbox records before queue dispatch; retain a retry path after queue failure.
- [x] Return persisted feedback IDs/receipts and preserve submission/retry states in the UI.
- [x] Keep browser preview samples separate from authenticated production evidence.

**Acceptance:** Double-clicking Submit or retrying after a network interruption does
not create duplicate feedback. A queue outage does not lose committed feedback or
permanently prevent its later analysis.

## 12. P7: Python Workflows, Celery, and Live Updates — partially implemented

- [x] Implement typed LangGraph nodes for feedback quality, NLP analysis, and prioritization.
- [x] Run requirement analysis and feedback analysis through Celery; persist status and provenance.
- [ ] Generalize all runs into shared `workflow_runs` and `workflow_events` records.
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

## 13. P8: Feedback Quality and Deterministic Trust — implemented with evidence limits

### Python Quality Agent

- [x] Define typed relevance, originality, constructiveness, consistency, spam risk, authenticity-indicator, confidence, and explanation fields.
- [x] Ground analysis in persisted source feedback and exact-version context; reviewer history is not yet available.
- [x] Persist evidence IDs and model/prompt/workflow provenance.
- [ ] Add handling for empty, irrelevant, duplicate, adversarial, and ambiguous feedback.
- [ ] Provide appropriate human moderation/review paths.
- [x] Never label a person or review as proven fake based on AI output.

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

- [x] Normalize supported factors to [0, 1] and validate numerical inputs.
- [x] Document evidence sources and explicitly leave unsupported factors missing; no historical accuracy is invented.
- [ ] Distinguish measured, inferred, unavailable, and overridden factors.
- [x] Keep the formula deterministic; the LLM does not choose the final numerical score.
- [ ] Persist independently versioned reviewer `trust_snapshots`; current persisted score is feedback-level and partial.
- [ ] Version formula changes and retain old snapshots for reproducibility.
- [ ] Prevent reviewers and owners from changing trust scores.
- [ ] Audit any approved administrative override.
- [ ] Connect trust factor breakdowns, evidence links, and quality/confidence views.

**Acceptance:** The same validated factor inputs produce the same score. Tests cover
boundaries, missing evidence, formula versions, and unauthorized modifications.

## 14. P9: Embeddings, Clustering, Consensus, and Priorities — implemented with limits

### Semantic Analysis

- [ ] Verify live embeddings with the configured local Ollama model; tests use deterministic vectors.
- [x] Store vectors and source metadata in feedback embeddings using pgvector.
- [x] Fix and validate embedding dimensions and model/version compatibility.
- [x] Query cosine similarity for same-version evidence; index/performance evaluation remains.
- [x] Generate version-scoped themes and likely-similar feedback groups; these are not proof of duplication.
- [ ] Define clustering thresholds and minimum-data behavior using evaluation evidence.
- [ ] Retain supporting feedback IDs for every theme and cluster.
- [ ] Show insufficient-data and uncertainty states rather than forcing clusters.

### Consensus

```text
Feedback weight = Trust score * Authenticity score * Relevance score
Normalized weight = Feedback weight / Sum of eligible feedback weights
```

- [x] Define how quality indicators map to bounded aggregation inputs.
- [x] Compute raw support and trust-weighted support separately.
- [x] Handle missing factors, empty feedback, and zero total weight explicitly.
- [x] Define and test confidence/coverage as an uncalibrated indicator.
- [x] Persist consensus, evidence IDs, source versions, formula/config version, and workflow metadata in analysis-run output.
- [ ] Keep disagreement and minority concerns visible.

### Prioritization

- [x] Define deterministic ordinal ranking for P1/P2/P3 feature improvements.
- [x] Combine evidence-linked support with qualitative impact/feasibility; mark missing inputs unknown.
- [ ] Keep agent rationale separate from deterministic numeric calculations.
- [ ] Persist feature_priorities, rank, rationale, evidence IDs, and provenance.
- [ ] Connect semantic themes, trust distribution, raw/weighted charts, and the feature-priority matrix.

**Acceptance:** Stored evidence reproduces reported aggregates. A zero-weight dataset
returns null weighted support and cannot produce a misleading confidence claim or
divide-by-zero failure. Live provider inference and full trust-factor coverage are
not acceptance claims for the current implementation.

## 15. P10: Evidence-linked Evolution — partially implemented

- [x] Make evolution owner-authorized and explicitly approved, never an automatic overwrite.
- [x] Load immutable source-version requirements, validated feedback analysis, trust/consensus and priorities.
- [x] Persist typed suggestions with source feedback IDs, expected benefit, assumptions, risks, validation criteria and provenance.
- [x] Reject stale source versions, invalid ranks, missing evidence and unsupported Builder categories.
- [x] Create a separate immutable target-version candidate and preserve the original version/reviews.
- [x] Invoke the existing source-only Builder for supported approved candidates and label build/publish status honestly.
- [ ] Obtain a reviewed isolated build boundary, build/test V2 artifact, and validate before marking a prototype ready.
- [ ] Add a dedicated model invocation for new Evolution reasoning; current agent shapes the persisted Phase 6 prioritized suggestions and does not claim a separate LLM call.
- [ ] Add a rich V1/V2 comparison and evidence navigation for authenticated records.
- [ ] Add recovery/retry controls for candidate or source-generation failures.

**Acceptance status:** V1 remains immutable and approved changes are linked to cited
feedback. A validated working V2 prototype is blocked by the unavailable isolation
boundary and is not claimed.

## 16. P11: Decision Intelligence — partially implemented

- [x] Build an owner-authorized structured report from persisted versioned evidence.
- [x] Include requirements, prototype/build status, sample size/coverage, quality findings, themes, trust, consensus, priorities, evolution, risks and next steps.
- [x] Store source version, requirement and feedback analysis run IDs, proposal ID, and source feedback IDs in immutable report snapshots.
- [x] Distinguish observed inputs, model interpretations, deterministic calculations, assumptions, recommendations and missing evidence.
- [x] Connect authenticated report UI to saved report snapshots; keep preview report fixtures separate.
- [ ] Add stable report-input digest/reproduction verifier and downloadable signed/export artifacts.
- [ ] Add direct evidence links, report diff/staleness indication, and report regeneration comparison.
- [ ] Complete the dashboard charts using versioned persisted API data rather than browser preview state.
- [x] Keep uncertainty visible and prohibit fabricated outcome metrics.

**Acceptance status:** Owners can retrieve persisted snapshots tied to exact source
records; their report JSON and formulas do not claim business success. Signed
exports, byte-for-byte re-rendering guarantees, and isolated V2 evidence remain
future hardening.

## 17. Database Work by Phase

Do not create placeholder tables merely to match a diagram. Add models, constraints,
migrations, repositories, and database tests with the phase that uses them.

| Entity group | Phase | Important constraints |
| --- | --- | --- |
| users, organizations | P1 | Unique identities, roles, ownership/tenant isolation |
| reviewer_assignments, idea_reviews | P1 | Exact immutable-version scope, role authorization, one review per assignment |
| ideas, idea_versions, idea_assets, idea_status_events | P2 | Version uniqueness, immutable snapshots, authorized assets, append-only lifecycle audit |
| requirement_specs | P3 | Source version and workflow/model/prompt provenance |
| prototypes, prototype_builds, prototype_events | P4 | Versioned artifacts, validated transitions, logs |
| reviewer_profiles, review_sessions | P5 | Prototype/version/session integrity; assignment rows are already introduced in P1 |
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
| Ideas | `POST/GET /api/v1/ideas`, `GET/PATCH /api/v1/ideas/{id}`, `POST /api/v1/ideas/{id}/versions` | Persistent submission/list/detail, archive/restore, and immutable version history |
| Idea assets | `POST /api/v1/ideas/{id}/versions/{version}/assets`, authorized `GET` download | Private upload, metadata, and scoped download |
| Build | `POST /api/v1/ideas/{id}/build` | Start generation and monitor progress |
| Prototype | `GET /api/v1/ideas/{id}/prototype`, `GET /api/v1/ideas/{id}/prototype/preview` | Manifest, status and authorized artifact launch |
| Publish | `POST /api/v1/projects/{id}/publish` | Open a valid review cycle |
| Assignments | `POST /api/v1/assignments`, `GET /api/v1/reviewer/projects` | Admin assignment and reviewer queue |
| Sessions | `POST /api/v1/reviewer/{id}/start` | Version-linked review session |
| Feedback | `POST/GET /api/v1/ideas/{id}/feedback` | Durable submission and evidence lists |
| Analytics | `GET /api/v1/ideas/{id}/analytics` | Real metrics and chart data |
| Trust | `GET /api/v1/ideas/{id}/trust` | Factor history and quality context |
| Consensus | `GET /api/v1/ideas/{id}/consensus` | Raw/weighted results and evidence |
| Evolution | `POST/GET /api/v1/ideas/{id}/versions/{version}/evolution`, `POST .../evolution/{proposal_id}/approve` | Evidence-linked suggestions, explicit owner approval, Draft candidate; working build blocked |
| Workflows | `GET /api/v1/workflows/{run_id}` | Run state, failures and recovery |
| Reports | `POST/GET /api/v1/ideas/{id}/versions/{version}/decision-reports` | Persisted version-scoped report snapshots; file export not implemented |
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

**Phase 8 verification (2026-10-23):** the enabled backend suite passed against
PostgreSQL/pgvector/Redis/Celery, including one full API/database workflow test
using deterministic requirement, quality/NLP, and embedding test doubles. The real
worker ping and review outbox handoff passed; the active worker was restarted and
task registrations were inspected. Frontend unit, lint, typecheck, build, and
preview Playwright suites passed. An additional authenticated owner browser test
registers, creates an idea through the API, reloads, signs in again, and retrieves
the persisted PostgreSQL record; test writes are rolled back at server shutdown.
Reviewer/admin browser workflows and the full browser-driven feedback/analysis
journey are still unverified. This does not verify live model inference,
generated-code execution, or production deployment.

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
- [x] Add an API-backed browser test for owner registration, idea persistence, and retrieval after a new login.
- [ ] Extend API-backed browser tests to reviewer/admin workflows and the complete review/analysis journey.
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
The Phase 8 rollback-isolated acceptance test covers the persisted API journey using
deterministic providers; it does not satisfy the real-provider or isolated-prototype
requirements below.

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

Continue with the remaining release blockers rather than restarting Phase 1:

1. Add a reviewed, auditable operator flow for provisioning reviewer/admin roles.
2. Configure and verify a real development AI provider; keep live-provider tests
   distinct from deterministic test doubles.
3. Supply and review a disposable, restricted prototype build/preview boundary.
4. Resolve Tailwind 3 development dependency advisories and add a backend
   vulnerability-database scan.
5. Extend authenticated browser E2E to reviewer/admin and review/analysis flows;
   complete multi-review confidence/evidence coverage, production storage/privacy
   controls, and recovery testing.

Do not provision paid cloud resources, claim 24/7 availability, release production
traffic, or execute generated code until the corresponding cost, security, privacy,
and isolation gates are approved and verified.