# Decisions

## 2026-10-23: Phase 8 single-idea integration verification

Phase 8 adds a PostgreSQL-backed acceptance test for the complete available
single-idea workflow: authenticated owner/reviewer/admin sessions, immutable V1,
validated requirements, source-only Builder, exact-version assignment and
idempotent review, persisted quality/NLP/trust/consensus/priorities, owner-approved
V2 candidate, report snapshot, reload from a new API app/session, and cross-user
access denial. The test uses deterministic chat and embedding doubles and is not a
live-provider integration result. It leaves its data inside a rollback transaction.

The existing stale Celery worker was stopped and restarted with the current
application code. The restarted worker registers requirement and feedback-analysis
tasks; PostgreSQL/pgvector, Redis, a real worker ping, and the outbox-to-worker
handoff were verified by the enabled integration suite. This is local development
verification only, not a durable service manager or availability guarantee.

This environment has no running Ollama service and no configured Gemini key.
Accordingly, provider inference is not verified, and the product workflow test
executes deterministic providers inside its test process rather than representing
their output as real model work. The supported Builder still cannot execute,
build, or preview generated source because a reviewed isolation boundary is absent.
No production release is authorized by these local checks.

`npm audit fix` applied compatible frontend lockfile updates. Remaining advisories
are in the Tailwind 3 development toolchain; the suggested complete fix requires a
Tailwind major upgrade, which is not included in this integration phase. Production
dependencies are checked separately. No security scanner was available for a
backend vulnerability database audit; `pip check` is dependency-consistency only.

## 2026-10-23: Phase 7 owner-approved evolution and report snapshots

The Phase 7 request combines blueprint phases P10 (Evolution) and P11 (Decision
Intelligence), so both are implemented as one local product slice. Revision `0010`
adds `evolution_proposals` and `decision_reports`; both retain exact idea-version
references, and reports additionally pin requirement/feedback run IDs, proposal ID,
and source feedback IDs.

Evolution requires completed, schema-valid requirements and a completed,
schema-valid Phase 6 analysis for the exact source version. Every cited feedback ID
is checked against persisted submitted reviews for that version. The Python
Evolution Agent currently converts the persisted model-ranked Phase 6 priorities
into typed suggestions; it does not make a second model call or invent new evidence.
Suggestions record rationale, qualitative benefit, assumptions, reviewer concerns,
criteria, missing inputs, model provenance, and whether the existing Builder scope
supports them. They remain proposals until the owner explicitly approves selected
priority ranks.

Approval checks the expected/current source version, rejects unknown ranks and
unsupported Builder categories, and inserts a new immutable child version. It does
not edit V1. The owner-approved feature additions are preserved in a separately
validated requirement record for that candidate. The existing Builder generates
allowlisted source only and records static validation. As no isolated executor is
available, the candidate remains Draft and the artifact remains blocked from build
and publication; source generation is not represented as a valid working V2.

Decision reports are immutable JSON snapshots built from PostgreSQL records, not a
free-form LLM summary. They label owner-provided facts, model interpretations,
deterministic trust/consensus calculations, explicit requirement assumptions,
recommendations, source IDs, sample size, coverage, and uncertainty. Missing records
remain visible and no adoption, product-market-fit, or business-outcome metrics are
generated. Reports can be regenerated as new snapshots, while their source
version/run/evidence references remain pinned.

Authenticated Evolution and Reports pages use owner-scoped APIs; browser preview
continues to use separate local fixtures. No public report artifact/download or
independent report digest/reproduction verifier was added. At Phase 7 completion,
the active Celery worker did not register Phase 6 analysis execution; Phase 8
restarted and verified the worker. Live model inference and isolated V2 build
acceptance remain unverified.

## 2026-10-23: Phase 6 persisted feedback intelligence and evidence limits

Phase 6 consumes only committed `idea_reviews` for the exact immutable idea version.
An input digest snapshots ordered source feedback IDs; repeated requests reuse active
or completed work for that snapshot, and a changed evidence set creates a new run.
The existing review outbox handoff now queues this version-scoped workflow. Analysis
status, results, source IDs, provider/model, embedding model, prompt version,
validation, attempts, and errors persist in PostgreSQL. Celery runs the workflow and
LangGraph sequences typed Feedback Quality, NLP Analysis, and Prioritization steps.
Provider failures or schema/source-ID mismatches remain failed/queued, never an empty
successful report.

The Quality Agent returns relevance, constructiveness, originality within the
snapshot, internal consistency, spam risk, an uncertain authenticity indicator,
self-reported confidence, explanations, and uncertainty. Deterministic text-length,
required-rating completeness, and exact-duplicate checks are stored separately.
No LLM label proves that a reviewer or comment is authentic or fraudulent.

Trust formula version `trust-baseline-partial-v1` follows the blueprint's six
weights. Review Quality is the mean of relevance, constructiveness, originality,
internal consistency, and `1 - spam risk`. The current database has no verified
historical outcome, stable reviewer-alignment baseline, behavioral review history,
verified-expertise record, or auditable community-validation evidence. Those factors
remain null; the partial score renormalizes only supported weights and reports
evidence coverage (currently 0.30). It is a feedback-level estimate, not a reviewer
reputation score. The model's self-rated confidence is not calibrated.

Ollama embeddings use the configured embedding model and a fixed 768-dimensional
pgvector column; mismatched dimensions fail validation. Cosine similarity is
calculated by pgvector in PostgreSQL. Pair similarity at or above 0.88 is a
versioned heuristic for likely similarity, not a determination of copied or
fraudulent feedback. Embeddings are keyed by immutable feedback ID/model and content
hash.

Consensus uses raw review count/support and deterministic
`weight = partial trust × authenticity indicator × relevance`. Weighted support is
`sum(weight × would_use) / sum(weight)`; a zero denominator yields `null`, never a
synthetic zero or perfect result. Confidence is explicitly an uncalibrated indicator:
mean model self-reported quality confidence × `n/(n+5)` × analyzed evidence
coverage. Sample size, denominator, normalized per-feedback weights, uncertainty,
coverage, and evidence IDs are returned and persisted.

Prioritization proposals cite feature-request themes and source review IDs.
Qualitative impact and feasibility are ranked (impact, normalized review support,
then feasibility); absent inputs are `unknown`, with assumptions and missing data
listed. P1/P2/P3 are ordinal ranks, not measured impact claims. Authenticated
feedback/analytics/trust/consensus screens show PostgreSQL-backed data; local
preview fixtures remain separate.

No live provider response was established by the unit or PostgreSQL tests; they use
deterministic doubles. A real Ollama chat+embedding workflow remains a separate
integration check. LangGraph was added at this phase because the quality/NLP/
prioritization steps now form an explicit workflow; it was not needed for earlier
single-agent phases.

## 2026-10-23: Safe AI Builder source generation without a sandbox

The requested Builder increment supports only education placement preparation using
a fixed React/TypeScript/Vite template. It consumes a completed, schema-validated
Requirement Agent result for the exact immutable idea version. Model output is data,
not source code: it is serialized into JSON and rendered as text by a trusted,
allowlisted scaffold. Generated source is stored under ignored private local storage
with path, dependency, script, capability, size, and hash validation and owner-only
API access.

This Codespaces environment has no reviewed disposable build boundary. The API and
normal Celery worker therefore do not run Node, npm, generated source, or build
scripts. A successful static source check is not a build, runtime test, security
review, or publish approval. Build status is persisted as `blocked_isolation`;
there is no compiled artifact, preview URL, or publish path. The generated scaffold
is separate from trusted application source and has no injected credentials or
environment access. Enabling build/preview requires an independently reviewed
nonprivileged executor with network, resource, filesystem, credential, and cleanup
controls.

## 2026-10-23: Phase 4 Requirement Agent provider boundary

The Requirement Agent is an owner-authorized, Celery-dispatched workflow over an
immutable idea version. Its Pydantic-validated output and provider/model, workflow,
prompt, source-version, attempt, validation, timestamp, and error provenance are
persisted in PostgreSQL. The default provider remains Ollama, matching the existing
local configuration. A backend-only Gemini Developer API adapter is an opt-in
development provider, rejected in production configuration; it does not replace the
master blueprint's production Bedrock provider. No Bedrock or LangGraph dependency
was added because neither is part of the existing local architecture. Real provider
output remains unverified until an explicitly configured live invocation succeeds.

## 2026-10-23: Phase 3 exact-version review and durable feedback handoff

An owner opens a review cycle for one immutable idea version. Admin assignments must
reference that open cycle; reviewers receive an assignment-scoped session whose idea
and version are fixed at session creation. Feedback stores the assignment, reviewer,
session, idea, and exact version references. Submission requires complete bounded
ratings/text and an `Idempotency-Key`; a matching retry returns the existing feedback,
while key reuse with different content conflicts.

The API commits feedback and an analysis-outbox row in one PostgreSQL transaction
before dispatching Celery. Queue-dispatch failure does not roll back or hide accepted
feedback; a repeated same-key submission can retry the handoff. At the Phase 3 release point, the worker only acknowledged outbox receipt. Phase 6
replaced that behavior with the persisted, version-scoped analysis workflow documented
above. The browser-local preview remains a separate fixture mode.

## 2026-10-23: Phase 2 persistent idea lifecycle and local private assets

Idea content is stored as versioned PostgreSQL snapshots. Creating a changed idea
requires an explicit version request with the expected current version and a change
summary; a database trigger rejects direct update/delete attempts against version
records. Owners may list with pagination and filters, retrieve history, and transition
only between Draft and Archived. Archiving is blocked while any reviewer assignment
is active; archived ideas can be restored but not edited until restored. Initial state
and each transition are recorded in per-idea ordered, append-only status history with
the actor and timestamp.

The local environment uses generated opaque file keys in an ignored private directory,
with file metadata/checksums in PostgreSQL and authorized API streaming for downloads.
Files are capped at 10 MiB and limited to PDF/PNG/JPEG with filename and signature
checks. This is a local development boundary, not S3, malware scanning/quarantine,
content extraction, or a production storage design. No AWS resources or public asset
URLs are introduced.

## 2026-10-23: Phase 1 backend authorization

Roles are read from the PostgreSQL user row on each authenticated request; registration
always creates an owner and rejects extra role fields. Owner access is scoped to owned
ideas and versions. Reviewer access is scoped to an active assignment for an exact
immutable version, and one persisted structured review is allowed per assignment.
Cross-user and unassigned-resource lookups return 404; authenticated role misuse
returns 403.

Admin authority is intentionally narrow: list, create, and revoke reviewer assignments
for exact idea versions. Admins do not inherit private idea read access. Assignment
records retain the assigning/revoking admin IDs and timestamps. Admin account
provisioning and audited role changes are not exposed by public APIs and remain an
operational security blocker pending a separately reviewed bootstrap process.

The authenticated reviewer UI records ratings and textual feedback about an assigned
idea brief only. It does not claim that a generated prototype exists. Browser-local
preview roles and records remain separate from authenticated API identity and data.

## 2026-09-30: Comment-first feedback with feasibility-aware proposals

The user requested social-style reviewer comments that contribute to priority-based
idea evolution, with a meaningful but limited role for likes and sharing.

The frontend now supports version-linked comments with testing context, optional
detailed rating reviews, per-comment useful votes, idea-interest likes, and unique
successful link-copy signals. These are browser-local preview identities and actions,
not authenticated production engagement. No AI result or missing rating is invented.

Discovery order uses likes and capped unique link copies; neither changes trust or
consensus. Implementation priorities use owner/admin impact and effort estimates,
with capped useful-comment votes. Unknown estimates, questions and blockers are
excluded from proposal selection. The explicit heuristic and thresholds are recorded
in the frontend README. Each new proposal stores its priority snapshot and formula
version, preserving the original idea version and its evidence.

This is a preview prioritization policy, not an approved replacement for the master
blueprint's production trust-weighted analytical pipeline. Python/SQLAlchemy schemas,
authenticated actor identity, authorization, durable audit, idempotency, anti-abuse,
moderation and provider-backed evolution remain necessary before production use.
The feedback API must explicitly distinguish unrated comments from structured reviews;
do not fill absent rating fields with fabricated defaults.

## 2026-09-30: AWS-first recommendation and production roadmap

The user asked whether AWS can replace local data services and support agents,
database, deployment and production, and requested an end-to-end README plan.
The README now recommends private RDS PostgreSQL/pgvector, node-based ElastiCache
Redis OSS with cluster mode disabled initially, Python Bedrock/LangGraph agents,
and native EC2 API/worker fleets supervised by systemd. S3/CloudFront, ALB, Route 53,
ACM, IAM, Secrets Manager, Systems Manager, CloudWatch and CloudTrail support the plan.

Status: recommendation only. No resources were created; region, budget, account
access and production provisioning are not approved by writing this plan.
Native EC2 is the proposed no-Docker alternative to the master blueprint's
ECS/Fargate/ECR compute path. EC2 operational ownership and a separately reviewed
generated-code sandbox remain required; the base blueprint is not silently rewritten.

Cognito User Pools is proposed as managed identity, subject to explicit selection
before implementing auth. If selected, it replaces custom password/session ownership;
FastAPI still validates access tokens and enforces PostgreSQL-backed resource/role
permissions. The auth API contract, frontend callback routing and related roadmap
tasks must then be updated. Do not implement both password authorities in parallel.

Bedrock model inference does not replace Python agents or LangGraph orchestration.
Bedrock Agents/AgentCore, another queue, Step Functions, or SageMaker are not added
to this baseline. Redis transport/TLS/failover compatibility must be tested before
selecting a different engine or serverless/cluster-mode configuration.

## 2026-09-30: Frontend first; no Docker in the active workflow

The user requested a complete frontend experience before backend integration,
without Docker, and with Python backend and AI agents for eventual AWS deployment.
This overrides the older local Compose-first instructions. The existing container
files remain historical scaffolding, but current launch instructions and CI do not
invoke Docker. Native/managed PostgreSQL and Redis integration is a later gate.
The blueprint's ECS/Fargate deployment detail conflicts with a container-free
preference; the AWS compute target will be agreed in the deployment phase rather
than silently introducing a new architecture now.

The UI uses an explicitly labeled browser-local preview store, never production
JSON persistence. Mock identities are not authentication. Sample templates are
hand-authored React experiences, not generated builds. AI outputs and confidence
remain unavailable until Python services provide auditable results. Evolution
creates only a manual evidence-linked proposal; V1 is never overwritten.

Cached dependencies enabled an offline install without changing the required
React 19 / TypeScript 6 / Vite 8 / Tailwind 3 major versions. Node's built-in test
runner replaces uncached Vitest. Playwright tests use installed Edge on Windows.
The npm lockfile is generated and CI uses npm ci. Hash routing supports static
preview hosting on S3/CloudFront. Application services and AI agents remain Python.

## 2026-09-29: Foundation scope

The supplied v3 master blueprint is preserved verbatim in PROJECT_SPEC.md.
There were no pre-existing repository files or conflicting architecture documents.
This setup implements the P0 scaffold, not the P1-P13 product or an MVP claim.
Business modules and database tables will be added with their acceptance tests.

React 19, TypeScript 6, Vite 8 and Tailwind 3 remain the frontend majors.
PostgreSQL is the transactional source of truth; no SQLite or JSON fallback is supplied.
The status page reports actual API connectivity, not product analytics.
The API readiness check covers PostgreSQL, pgvector, migration presence and Redis;
Celery worker execution is checked separately by the integration test.

Compose is local-only. Development credentials must never be used in production.
Generated code execution and AWS deployment are intentionally absent until their
security and acceptance gates can be implemented. The builder has no runnable
container yet, preventing an unisolated placeholder from being used accidentally.

The initial Alembic downgrade retains pgvector because the extension can be shared
by later migrations or other applications; it does not delete stored vectors.

Python dependencies use bounded compatible ranges during setup. Produce and review
a reproducible lock with security scanning before production deployment.