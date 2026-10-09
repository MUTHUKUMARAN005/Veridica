# Decisions

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