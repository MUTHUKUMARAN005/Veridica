# VERIDICA --- MASTER E2E IMPLEMENTATION BLUEPRINT

## AI-Powered Trust-Aware Product Idea Validation, Prototype Testing & Idea Evolution Platform

**Version:** 3.0\
**Date:** September 2026\
**Purpose:** Single source of truth for the AI coding/building agent
implementing Veridica end-to-end.

------------------------------------------------------------------------

## 0. SOURCE-OF-TRUTH RULES

1.  This file is the implementation master plan.
2.  Read this file before changing architecture or creating major
    modules.
3.  If an older README, PPT, prototype, or document conflicts with this
    file, follow this file and record the conflict in
    `docs/DECISIONS.md`.
4.  Do not introduce a second backend framework, database, LLM provider,
    queue, or orchestration framework.
5.  PostgreSQL is the source of truth. Redis is not.
6.  Never use static JSON as the production source of truth.
7.  Never hardcode dashboard KPIs as measured results.
8.  Never overwrite an original idea/version.
9.  AI authenticity analysis produces indicators and confidence; it does
    not prove that a person or feedback item is fake.
10. Every important AI result must store workflow run, model version,
    and prompt version.
11. Build incrementally and test every phase.

------------------------------------------------------------------------

# 1. PRODUCT DEFINITION

### Product

**Veridica**

### Title

**Veridica: AI-Powered Trust Analytics for Idea Validation and Decision
Intelligence**

### Core positioning

Veridica transforms an idea into a **visual, reviewable functional
prototype**, lets reviewers interact with that prototype, collects real
structured and textual feedback, evaluates feedback quality and reviewer
trust, extracts collective intelligence, and evolves the idea/prototype
into an improved version.

### Central principle

> Do not ask reviewers to only read an idea. Give them something visual
> and interactive to test.

Therefore:

``` text
Idea
 ↓
Requirements
 ↓
Code
 ↓
Functional Visual Demo V1
 ↓
Real Reviewer Usage
 ↓
Real Feedback
 ↓
Trust + AI Analysis
 ↓
Consensus
 ↓
Feature Prioritization
 ↓
V2
 ↓
Decision Intelligence
```

The AI Builder is a **validation-enabling component**, not the whole
product and not an unrestricted generic AI coding platform.

------------------------------------------------------------------------

# 2. FINAL E2E LOOP

``` text
IDEA SUBMISSION
      ↓
DOCUMENT / TEXT / IMAGE INGESTION
      ↓
REQUIREMENT ANALYSIS AGENT
      ↓
STRUCTURED REQUIREMENT SPECIFICATION
      ↓
AI BUILDER AGENT
      ↓
CODE / COMPONENT GENERATION
      ↓
BUILD + LINT + TEST + SAFETY VALIDATION
      ↓
FUNCTIONAL REVIEWABLE WEB PROTOTYPE V1
      ↓
PUBLISH / ASSIGN
      ↓
REVIEWER PORTAL
      ↓
REVIEWER OPENS AND USES DEMO
      ↓
STRUCTURED RATING + EVIDENCE-BASED FEEDBACK
      ↓
POSTGRESQL PERSISTENCE
      ↓
REDIS EVENT
      ↓
CELERY BACKGROUND JOB
      ↓
LANGGRAPH WORKFLOW
      ↓
AUTHENTICITY / QUALITY ANALYSIS
      ↓
DETERMINISTIC TRUST ENGINE
      ↓
NLP + EMBEDDINGS + SEMANTIC CLUSTERING
      ↓
TRUST-WEIGHTED CONSENSUS
      ↓
FEATURE PRIORITIZATION
      ↓
IDEA EVOLUTION AGENT
      ↓
V2 REQUIREMENT / CHANGE SET
      ↓
V2 PROTOTYPE
      ↓
DECISION INTELLIGENCE
```

------------------------------------------------------------------------

# 3. IMPORTANT NEW UPDATE --- IDEA TO VISUAL DEMO

## 3.1 Required capability

When an Idea Owner submits an idea, Veridica must attempt to transform
it into a **visual, interactive, reviewable web prototype** before the
main review cycle.

Examples:

-   AI College Placement Assistant → dashboard, job matching, resume
    analysis, preparation roadmap
-   Smart Waste Management → reporting, pickup scheduling, analytics
-   Campus Lost & Found → item reporting, search, match results
-   Crop Monitoring → farm dashboard, crop health cards, alerts
-   Product idea → landing page, core feature screens, user journey

## 3.2 Input

The Idea Owner can submit:

-   title
-   problem statement
-   target users
-   proposed solution
-   features
-   constraints
-   category/domain
-   documents
-   reference images/screenshots

Documents/images are stored in **Amazon S3**; metadata is stored in
PostgreSQL.

## 3.3 Builder output

The system must produce:

1.  Requirement specification
2.  UI/UX screen specification
3.  Component plan
4.  Prototype manifest
5.  Generated React/TypeScript code
6.  Build artifact
7.  Prototype version
8.  Preview URL
9.  Build/test logs
10. Feature list
11. Known limitations
12. Generation metadata

## 3.4 MVP prototype scope

Initially support controlled web application templates/components:

-   responsive React UI
-   navigation
-   dashboards
-   cards
-   forms
-   tables
-   charts
-   search/filter
-   detail pages
-   local/demo state
-   safe demo data
-   clearly labelled prototype-only integrations

The prototype is **reviewable software**, not automatically production
software.

------------------------------------------------------------------------

# 4. FINAL FIXED TECH STACK

## Frontend

  Technology                   Purpose
  ---------------------------- ----------------------
  React 19                     Web application
  TypeScript 6                 Type safety
  Vite 8                       Build/dev
  Tailwind CSS 3               UI system
  React Router                 Routing
  React Hook Form              Forms
  Chart.js + react-chartjs-2   Analytics
  Lucide React                 Icons
  Framer Motion                Controlled animation

## Backend

  Technology     Purpose
  -------------- ------------------
  Python 3.12+   Runtime
  FastAPI        REST + WebSocket
  Pydantic       Validation
  SQLAlchemy 2   ORM
  Alembic        Migrations

## Data

  Technology   Purpose
  ------------ --------------------------------
  PostgreSQL   Primary transactional database
  pgvector     Embeddings/vector search
  Redis        Queue/event/cache backend
  Celery       Async jobs

## AI / NLP

  Technology                  Purpose
  --------------------------- ---------------------------------
  LangGraph                   Stateful workflow orchestration
  Amazon Bedrock              LLM runtime
  Amazon Bedrock embeddings   Semantic embeddings
  scikit-learn                Classical ML
  Transformers                Transformer NLP
  spaCy                       NLP
  Pandas                      Analytics
  NumPy                       Numerical processing

## AWS

  Technology          Purpose
  ------------------- -----------------------------
  ECS + Fargate       API/worker compute
  RDS PostgreSQL      Managed DB
  ElastiCache Redis   Managed Redis
  S3                  Uploads, artifacts, reports
  ECR                 Container registry
  ALB                 HTTPS/API routing
  CloudFront          Frontend/CDN
  Route 53            DNS
  ACM                 TLS
  IAM                 Permissions
  Secrets Manager     Secrets
  CloudWatch          Logs/metrics/alarms
  GitHub Actions      CI/CD

### Do not introduce

-   Flask
-   Django
-   MySQL as primary DB
-   Gemini as production LLM provider
-   MongoDB
-   LangChain as the main orchestration framework
-   another queue system
-   another production cloud architecture

------------------------------------------------------------------------

# 5. REPOSITORY STRUCTURE

``` text
veridica/
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/
│       │   ├── layout/
│       │   ├── ui/
│       │   ├── prototype/
│       │   ├── feedback/
│       │   ├── analytics/
│       │   └── workflow/
│       ├── pages/
│       │   ├── LandingPage.tsx
│       │   ├── Auth.tsx
│       │   ├── Dashboard.tsx
│       │   ├── IdeaSubmission.tsx
│       │   ├── IdeaDetails.tsx
│       │   ├── PrototypeWorkspace.tsx
│       │   ├── ReviewQueue.tsx
│       │   ├── ReviewWorkspace.tsx
│       │   ├── TrustEngine.tsx
│       │   ├── Authenticity.tsx
│       │   ├── Consensus.tsx
│       │   ├── AIEvolution.tsx
│       │   ├── Analytics.tsx
│       │   ├── Reports.tsx
│       │   ├── WorkflowMonitor.tsx
│       │   └── AdminPanel.tsx
│       ├── lib/
│       ├── hooks/
│       ├── services/
│       ├── types/
│       ├── App.tsx
│       └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/v1/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── agents/
│   │   ├── workflows/
│   │   ├── workers/
│   │   ├── websocket/
│   │   ├── events/
│   │   └── security/
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── prototype-builder/
│   ├── templates/
│   ├── component-library/
│   ├── generator/
│   ├── validators/
│   └── Dockerfile
│
├── docs/
│   ├── PROJECT_SPEC.md
│   ├── AGENT_SPEC.md
│   ├── DATABASE_SCHEMA.md
│   ├── API_SPEC.md
│   ├── WORKFLOW_SPEC.md
│   ├── PROTOTYPE_BUILDER_SPEC.md
│   ├── SECURITY.md
│   ├── EVALUATION.md
│   ├── DEPLOYMENT.md
│   └── DECISIONS.md
│
├── tests/
├── docker-compose.yml
├── .env.example
├── README.md
├── CLAUDE.md
└── .github/workflows/
```

------------------------------------------------------------------------

# 6. ROLES

## Idea Owner

Can create ideas, upload requirements, monitor builder, view prototype,
publish review cycle, view analytics, view evolution and decision
reports.

Cannot manipulate trust scores or analytical results.

## Reviewer

Can access assigned projects, launch prototypes, perform test journeys,
submit structured ratings and evidence-based feedback.

Cannot modify owner data or own trust.

## Admin

Manages users, reviewers, assignments, lifecycle, moderation, workflow
monitoring and audit.

Admin overrides require audit logging.

------------------------------------------------------------------------

# 7. MODULES

  ID    Module                  Responsibility
  ----- ----------------------- ---------------------------------
  M01   Authentication & RBAC   Identity/permissions
  M02   Idea Management         Idea/version management
  M03   Requirement Agent       Structured requirements
  M04   AI Builder              Visual prototype generation
  M05   Prototype Workspace     Preview/version/status
  M06   Reviewer Matching       Reviewer assignment
  M07   Feedback Collection     Real review data
  M08   Feedback Quality        Quality/authenticity indicators
  M09   Trust Engine            Deterministic trust
  M10   NLP/Semantic            Embeddings/topics/clusters
  M11   Consensus               Raw + trust-weighted consensus
  M12   Prioritization          Improvement ranking
  M13   Evolution               V2/V3 generation
  M14   Decision Intelligence   Traceable report
  M15   Real-Time Layer         Redis/Celery/WebSocket
  M16   Audit/Observability     Governance

------------------------------------------------------------------------

# 8. IDEA SUBMISSION

Persist:

``` text
ideas
idea_versions
idea_assets
```

Example:

``` json
{
  "title": "AI College Placement Assistant",
  "problem_statement": "...",
  "target_users": ["students"],
  "proposed_solution": "...",
  "features": ["job matching", "resume analysis"],
  "constraints": [],
  "category": "education"
}
```

Initial status:

`SUBMITTED`

------------------------------------------------------------------------

# 9. REQUIREMENT ANALYSIS AGENT

Input:

-   idea
-   uploaded documents
-   reference images
-   domain

Output:

``` json
{
  "problem": "...",
  "target_users": [],
  "user_journeys": [],
  "functional_requirements": [],
  "non_functional_requirements": [],
  "core_features": [],
  "screens": [],
  "navigation": [],
  "prototype_scope": [],
  "constraints": [],
  "assumptions": []
}
```

Persist in:

`requirement_specs`

Status flow:

``` text
SUBMITTED → ANALYZING → BUILDING
```

------------------------------------------------------------------------

# 10. AI BUILDER AGENT

## Responsibility

Convert the validated requirement specification into a reviewable
prototype.

Steps:

``` text
Select template
 ↓
Create project manifest
 ↓
Generate UI structure
 ↓
Generate React/TypeScript components
 ↓
Add safe demo data
 ↓
Validate dependencies/components
 ↓
Run lint
 ↓
Run type check
 ↓
Run production build
 ↓
Publish artifact
 ↓
Create preview URL
```

## Builder output

``` json
{
  "prototype_id": "...",
  "idea_id": "...",
  "version": 1,
  "template": "dashboard",
  "screens": [],
  "features": [],
  "artifact_uri": "...",
  "preview_url": "...",
  "build_status": "READY",
  "test_status": "PASSED",
  "limitations": [],
  "build_run_id": "..."
}
```

------------------------------------------------------------------------

# 11. PROTOTYPE SAFETY

The AI Builder must **not** become an unrestricted autonomous code
execution server.

MVP rules:

-   controlled templates
-   approved component library
-   generated React/TypeScript
-   isolated build environment
-   limited dependencies
-   no privileged containers
-   restricted network access
-   resource limits
-   versioned artifacts
-   build logs
-   audit records

Generated prototype code must never execute inside the FastAPI process.

Prototype states:

``` text
DRAFT
BUILDING
VALIDATING
READY
PUBLISHED
FAILED
ARCHIVED
```

Once review begins, V1 is immutable.

------------------------------------------------------------------------

# 12. PROTOTYPE HOSTING

Preferred MVP:

``` text
Builder
 ↓
Generated React project
 ↓
Build
 ↓
Validation
 ↓
Static artifact
 ↓
S3
 ↓
CloudFront
 ↓
Preview URL
```

If backend behavior is required, use approved backend templates and
isolated runtime services. Never expose arbitrary generated server code.

------------------------------------------------------------------------

# 13. REVIEWER EXPERIENCE --- VISUAL FIRST

The reviewer should see:

``` text
Project
Prototype V1 — READY
[ OPEN DEMO ]

Interactive Prototype

Test Journey
1. Open dashboard
2. Perform task
3. Try feature
4. Check result

Rating
Usability       ★★★★★
Usefulness      ★★★★★
Feasibility     ★★★★★

What worked?
[........................]

What should improve?
[........................]

[ Submit Review ]
```

The reviewer should understand the idea primarily through:

-   prototype screens
-   interactive flows
-   cards
-   charts
-   visual metrics
-   feature previews

Text remains available but is not the only presentation method.

------------------------------------------------------------------------

# 14. REAL FEEDBACK FLOW

Fields:

``` text
rating
usability_score
usefulness_score
completeness_score
feasibility_score
would_use
feedback_text
strengths
concerns
suggested_improvements
usage_context
session_id
```

Submission flow:

``` text
React
 ↓
FastAPI
 ↓
Auth + validation + authorization
 ↓
Idempotency check
 ↓
PostgreSQL COMMIT
 ↓
Redis event
 ↓
Celery job
 ↓
LangGraph
```

Feedback must be persisted before asynchronous analysis.

------------------------------------------------------------------------

# 15. REAL-TIME EVENTS

Events:

``` text
feedback.received
feedback.analysis.started
feedback.analysis.completed
trust.updated
consensus.updated
feature_priorities.updated
evolution.started
evolution.completed
dashboard.metrics.updated
workflow.failed
```

Browser receives events over:

``` text
WS /ws/ideas/{id}
```

------------------------------------------------------------------------

# 16. LANGGRAPH WORKFLOW

## Full workflow

``` text
START
 ↓
load_project
 ↓
requirement_analysis
 ↓
prototype_build
 ↓
prototype_validation
 ↓
WAIT_FOR_REVIEW
 ↓
feedback_received
 ↓
feedback_quality_analysis
 ↓
trust_update
 ↓
nlp_analysis
 ↓
semantic_clustering
 ↓
consensus
 ↓
feature_prioritization
 ↓
evolution
 ↓
v2_validation
 ↓
decision_intelligence
 ↓
persist_results
 ↓
END
```

## Feedback-only workflow

``` text
START
 ↓
load_feedback
 ↓
quality_analysis
 ↓
trust_update
 ↓
NLP
 ↓
consensus
 ↓
prioritization
 ↓
END
```

Evolution is an explicit workflow stage, not an automatic overwrite.

------------------------------------------------------------------------

# 17. AGENTS

## Requirement Agent

Input: idea/assets.\
Output: structured requirements, users, journeys, screens, features.

## Builder Agent

Input: requirements.\
Output: prototype manifest, generated project, build artifact, preview
URL.

## Feedback Quality Agent

Input: feedback/context/history.\
Output: relevance, originality, constructiveness, consistency, spam
risk, bias risk, authenticity indicator, confidence.

Never say:

`Reviewer is fake.`

Use:

`Authenticity/quality risk indicator + confidence.`

## NLP Agent

Output:

-   sentiment
-   topics
-   embeddings
-   issue categories
-   recurring suggestions
-   agreement/disagreement
-   clusters

## Consensus Agent

Output:

-   raw consensus
-   trust-weighted consensus
-   confidence
-   evidence IDs

## Prioritization Agent

Output:

-   P1/P2/P3 improvements
-   rationale
-   evidence IDs

## Evolution Agent

Input: V1 + priorities + feedback + consensus.\
Output: V2 change set + V2 requirements + rationale + evidence IDs.

## Decision Agent

Output:

-   validation summary
-   strengths
-   concerns
-   consensus
-   priorities
-   evolution summary
-   next steps
-   evidence links

------------------------------------------------------------------------

# 18. TRUST ENGINE

Trust is deterministic.

Baseline:

``` text
Trust Score =
0.30 × Review Quality
+ 0.20 × Historical Accuracy
+ 0.15 × Peer Alignment
+ 0.15 × Consistency
+ 0.10 × Verified Expertise
+ 0.10 × Community Validation
```

Normalize every factor to \[0,1\].

Persist:

``` text
score
factor_json
formula_version
created_at
```

LLM may classify evidence but must not arbitrarily invent the numerical
trust score.

------------------------------------------------------------------------

# 19. TRUST-WEIGHTED CONSENSUS

Baseline:

``` text
Feedback Weight =
Trust Score
× Authenticity Score
× Relevance Score
```

Normalize weights before aggregation.

Expose:

-   raw support
-   weighted support
-   confidence
-   supporting feedback IDs

------------------------------------------------------------------------

# 20. NLP + VECTOR SEARCH

Use:

-   Bedrock embeddings
-   pgvector
-   cosine similarity
-   semantic clustering
-   near-duplicate detection
-   topic grouping

Example:

``` text
Cluster 1 → usability
Cluster 2 → pricing
Cluster 3 → performance
Cluster 4 → missing feature
Cluster 5 → onboarding
```

------------------------------------------------------------------------

# 21. IDEA EVOLUTION

Original:

`V1`

Feedback:

``` text
Login is confusing.
Dashboard needs notifications.
Mobile experience needs improvement.
```

Possible V2 change set:

``` text
Simplified onboarding
Notification center
Responsive mobile layout
Improved navigation
```

Persist:

``` json
{
  "source_version": 1,
  "target_version": 2,
  "change_set": [],
  "evidence_ids": [],
  "model_version": "...",
  "prompt_version": "...",
  "created_at": "..."
}
```

V1 is never overwritten.

------------------------------------------------------------------------

# 22. DATABASE ENTITIES

``` text
users
organizations
ideas
idea_versions
idea_assets
requirement_specs
prototypes
prototype_builds
prototype_events
reviewer_profiles
review_assignments
review_sessions
feedback
feedback_analysis
feedback_embeddings
trust_snapshots
consensus_results
feature_priorities
evolution_results
workflow_runs
workflow_events
audit_logs
notifications
reports
```

### Ownership

PostgreSQL:

-   users
-   ideas
-   feedback
-   trust
-   consensus
-   evolution
-   workflow metadata
-   audit records

S3:

-   documents
-   images
-   prototype artifacts
-   reports

Redis:

-   queues
-   events
-   temporary state
-   cache

------------------------------------------------------------------------

# 23. API CONTRACT

``` text
POST /api/v1/auth/register
POST /api/v1/auth/login

POST /api/v1/ideas
GET  /api/v1/ideas/{id}
PUT  /api/v1/ideas/{id}

POST /api/v1/ideas/{id}/build
GET  /api/v1/ideas/{id}/prototype
GET  /api/v1/ideas/{id}/prototype/preview

POST /api/v1/projects/{id}/publish

POST /api/v1/assignments
GET  /api/v1/reviewer/projects
POST /api/v1/reviewer/{id}/start

POST /api/v1/ideas/{id}/feedback
GET  /api/v1/ideas/{id}/feedback

GET /api/v1/ideas/{id}/analytics
GET /api/v1/ideas/{id}/trust
GET /api/v1/ideas/{id}/consensus
GET /api/v1/ideas/{id}/evolution

POST /api/v1/ideas/{id}/evolve

GET /api/v1/workflows/{run_id}
GET /api/v1/reports/{idea_id}

WS /ws/ideas/{id}
```

------------------------------------------------------------------------

# 24. WORKFLOW STATES

``` text
DRAFT
 ↓
SUBMITTED
 ↓
ANALYZING
 ↓
BUILDING
 ↓
VALIDATING
 ↓
READY
 ↓
REVIEW_OPEN
 ↓
RECEIVED
 ↓
ANALYZING_FEEDBACK
 ↓
TRUST_UPDATED
 ↓
CONSENSUS_UPDATED
 ↓
EVOLUTION_READY
```

Failure:

``` text
FAILED
```

Store error, workflow run ID, timestamp and retry count.

------------------------------------------------------------------------

# 25. VISUAL UI REQUIREMENTS

## Landing page

Hero:

> **Turn Ideas into Trusted Innovation**

Show:

-   submit idea
-   AI builds visual demo
-   reviewers test it
-   trust-aware feedback
-   evolved solution

## Idea details

Show:

-   title
-   problem
-   target users
-   status
-   prototype V1
-   Launch Demo button
-   feature cards
-   user journey
-   review progress
-   feedback themes
-   trust metrics
-   consensus
-   evolution timeline

## Analytics

Use:

-   donut charts
-   bar charts
-   trend charts
-   semantic cluster cards
-   trust distribution
-   feature priority matrix

## Evolution

Show:

``` text
V1
 ↓
Feedback
 ↓
Consensus
 ↓
Priorities
 ↓
V2
 ↓
[ Launch V2 Demo ]
```

Provide V1/V2 comparison.

## Decision report

Show visual cards for:

-   validation status
-   consensus
-   trust coverage
-   top strengths
-   top concerns
-   priority features
-   recommended actions
-   evidence

------------------------------------------------------------------------

# 26. FINAL DEMO SCRIPT

1.  Open User Portal.
2.  Register/login.
3.  Submit an idea.
4.  Upload optional requirements/reference image.
5.  Show Requirement Agent output.
6.  Start prototype build.
7.  Show live build progress.
8.  Open generated visual prototype.
9.  Demonstrate multiple screens.
10. Open Reviewer Portal in another session.
11. Reviewer launches prototype.
12. Reviewer performs a real task.
13. Reviewer submits rating and feedback.
14. Show immediate persistence.
15. Show live `ANALYZING_FEEDBACK`.
16. Show quality/authenticity indicators.
17. Show trust update.
18. Submit multiple real reviews.
19. Show semantic clusters.
20. Show raw vs trust-weighted consensus.
21. Show feature priorities.
22. Run evolution.
23. Show V1 → V2 change set.
24. Open V2 prototype.
25. Show improved UI.
26. Open Decision Intelligence.
27. Inspect evidence links.

This is the presentation story.

------------------------------------------------------------------------

# 27. SECURITY

Required:

-   JWT/session authentication
-   RBAC
-   endpoint authorization
-   password hashing
-   HTTPS
-   CORS policy
-   rate limiting
-   input validation
-   output sanitization
-   upload validation
-   private S3 objects when needed
-   signed URLs
-   Secrets Manager
-   IAM least privilege
-   audit logs
-   feedback idempotency
-   prototype isolation
-   resource limits
-   restricted prototype network access

------------------------------------------------------------------------

# 28. ERROR RECOVERY

## Prototype failure

``` text
BUILD_FAILED
 ↓
store error
 ↓
notify
 ↓
retry
 ↓
manual review if repeated
```

## Feedback analysis failure

``` text
feedback remains RECEIVED
 ↓
retry
 ↓
reuse same feedback_id
 ↓
no duplicate feedback
```

## Evolution failure

``` text
V1 remains unchanged
 ↓
store failure
 ↓
retry
 ↓
create V2 only after validation
```

------------------------------------------------------------------------

# 29. LOCAL DEVELOPMENT

``` bash
docker compose up -d postgres redis

cd backend
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload

celery -A app.workers.celery_app worker --loglevel=INFO

cd frontend
npm install
npm run dev
```

------------------------------------------------------------------------

# 30. ENVIRONMENT

`.env.example` should define categories such as:

``` text
DATABASE_URL
REDIS_URL
JWT_SECRET
AWS_REGION
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
S3_BUCKET
BEDROCK_MODEL_ID
BEDROCK_EMBEDDING_MODEL_ID
PROTOTYPE_BUCKET
CORS_ORIGINS
```

Production secrets must be in AWS Secrets Manager.

------------------------------------------------------------------------

# 31. AWS PRODUCTION ARCHITECTURE

``` text
                         Internet
                            │
                         Route 53
                            │
                           ACM
                            │
                       CloudFront
                            │
                      React + S3

User / Reviewer
      │
      │ HTTPS
      ▼
     ALB
      │
 ┌────┴───────────────┐
 ▼                    ▼
ECS/Fargate API   ECS/Fargate Worker
      │                    │
      │               Celery/LangGraph
      │                    │
 ┌────┼────────────┬───────┘
 ▼    ▼            ▼
RDS  Redis       Bedrock
 │    │
pgvector
 │
S3
 │
prototype artifacts / reports / uploads

ECR → images
CloudWatch → logs/metrics/alarms
IAM → permissions
Secrets Manager → secrets
```

------------------------------------------------------------------------

# 32. CI/CD

## CI

``` text
Install
 ↓
Lint
 ↓
Type Check
 ↓
Unit Tests
 ↓
Backend Tests
 ↓
Frontend Build
 ↓
Docker Build
```

Main branch also:

``` text
Integration Tests
 ↓
Security Checks
 ↓
Container Scan
```

## CD

``` text
Git Push
 ↓
GitHub Actions
 ↓
Test
 ↓
Docker Build
 ↓
ECR
 ↓
Staging
 ↓
Smoke Test
 ↓
Approval
 ↓
Production
```

------------------------------------------------------------------------

# 33. TESTING

Backend:

-   unit tests
-   API tests
-   authorization tests
-   trust calculation tests
-   workflow tests
-   database tests

Frontend:

-   component tests
-   route tests
-   form validation
-   WebSocket handling

E2E:

``` text
Register
 ↓
Create Idea
 ↓
Requirement Analysis
 ↓
Build Prototype
 ↓
Open Prototype
 ↓
Publish
 ↓
Assign Reviewer
 ↓
Use Prototype
 ↓
Submit Feedback
 ↓
Analyze
 ↓
Trust
 ↓
Consensus
 ↓
Prioritize
 ↓
Evolve
 ↓
V2 Prototype
 ↓
Decision Report
```

------------------------------------------------------------------------

# 34. RESEARCH / JOURNAL EVALUATION

## Reviewer Matching

Baselines:

-   keyword matching
-   embedding matching

Metrics:

-   Precision@K
-   Recall@K
-   MRR

## Feedback Quality

Compare:

-   rule-based
-   ML
-   LLM-assisted
-   hybrid

Metrics:

-   accuracy
-   precision
-   recall
-   F1
-   ROC-AUC

## Consensus

Compare:

-   simple majority
-   trust-weighted aggregation

Metrics:

-   agreement with expert labels
-   ranking correlation
-   consensus stability

## Clustering

Metrics:

-   Silhouette Score
-   Davies-Bouldin Index

## Idea Evolution

Human/expert evaluation:

-   relevance
-   completeness
-   feedback coverage
-   actionability
-   consistency

Only report actual measured results.

------------------------------------------------------------------------

# 35. OBSERVABILITY

Persist:

``` text
workflow_run_id
entity_id
actor_id
timestamp
status
model_version
prompt_version
duration
error
```

CloudWatch:

-   API logs
-   worker logs
-   prototype build logs
-   errors
-   latency metrics
-   workflow failures

------------------------------------------------------------------------

# 36. AUDIT

Audit:

-   login/security events
-   idea creation
-   idea versioning
-   prototype builds
-   publishing
-   assignments
-   feedback
-   trust changes
-   consensus changes
-   evolution
-   admin overrides

Record:

``` json
{
  "actor_id": "...",
  "action": "...",
  "entity_type": "...",
  "entity_id": "...",
  "before": {},
  "after": {},
  "timestamp": "..."
}
```

------------------------------------------------------------------------

# 37. IMPLEMENTATION ROADMAP

## P0 Foundation

Docker, environment, PostgreSQL, Redis, CI.

**Exit:** all services run locally.

## P1 Auth + Portals

User, Reviewer, Admin + RBAC.

**Exit:** correct permissions.

## P2 Idea Management

Idea CRUD, V1, uploads, S3.

**Exit:** idea persists.

## P3 Requirement Agent

Structured requirement extraction.

**Exit:** valid requirement spec.

## P4 AI Builder MVP

Templates, manifest, React generation, build/validation, artifact,
preview.

**Exit:** one supported idea category produces a usable visual
prototype.

## P5 Reviewer System

Assignments, sessions, prototype launch.

**Exit:** reviewer can use a real prototype.

## P6 Real Feedback

Feedback form, PostgreSQL, idempotency, Redis.

**Exit:** real feedback persists.

## P7 Async + Real-Time

Celery, LangGraph, WebSocket.

**Exit:** live state updates.

## P8 Quality + Trust

Quality analysis + deterministic trust.

**Exit:** persisted analysis and trust snapshots.

## P9 NLP + Consensus

Embeddings, pgvector, clusters, consensus, prioritization.

**Exit:** visual consensus and priorities.

## P10 Evolution

V2 change set + V2 prototype.

**Exit:** V1 preserved and V2 created.

## P11 Decision Intelligence

Dashboard, report, evidence links.

**Exit:** traceable recommendations.

## P12 AWS

ECR, ECS/Fargate, RDS, ElastiCache, S3, CloudFront, ALB, IAM, Secrets
Manager, CloudWatch, Route 53, ACM.

**Exit:** production-like deployment.

## P13 Research

Datasets, baselines, metrics, reproducible experiments.

**Exit:** paper-ready evaluation artifacts.

------------------------------------------------------------------------

# 38. MVP DEFINITION

MVP must prove:

-   3 authenticated portals
-   1 supported prototype category
-   Requirement Agent
-   AI Builder
-   functional visual prototype
-   reviewer interaction
-   real feedback
-   PostgreSQL persistence
-   Redis/Celery
-   LangGraph
-   quality/authenticity analysis
-   deterministic trust
-   embeddings + pgvector
-   trust-weighted consensus
-   feature prioritization
-   V1 → V2 evolution
-   WebSocket updates
-   traceable decision report

------------------------------------------------------------------------

# 39. SINGLE-IDEA ACCEPTANCE TEST

Use one complete idea to prove the platform.

Example:

**AI College Placement Assistant**

Input:

``` text
Problem:
Students struggle to find relevant placement opportunities and
prepare efficiently for company-specific recruitment.

Target users:
College students.

Core features:
- job matching
- resume analysis
- preparation roadmap
- company-specific practice
- progress dashboard
```

Expected:

``` text
Idea
 ↓
Requirement Specification
 ↓
Visual V1
 ├── Landing
 ├── Student Dashboard
 ├── Job Matching
 ├── Resume Analysis
 ├── Preparation Roadmap
 └── Progress Analytics
 ↓
Reviewer Usage
 ↓
Real Feedback
 ↓
Trust + Quality
 ↓
Consensus
 ↓
Feature Priorities
 ↓
V2
 ↓
V2 Prototype
 ↓
Decision Report
```

The example is only a demonstration scenario. The builder architecture
must remain template-driven and extensible.

------------------------------------------------------------------------

# 40. CLAUDE / AI CODING AGENT RULES

Create `CLAUDE.md` containing:

``` text
Read README and docs before coding.
Treat this master blueprint as the architecture source of truth.
Use React + TypeScript + Vite + Tailwind.
Use Python + FastAPI + Pydantic + SQLAlchemy + Alembic.
Use PostgreSQL + pgvector.
Use Redis + Celery.
Use LangGraph.
Use Amazon Bedrock.
Keep trust deterministic.
Separate deterministic logic from LLM reasoning.
Persist important AI outputs.
Store model_version and prompt_version.
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
If older documents conflict with this blueprint, follow this blueprint and record the conflict in docs/DECISIONS.md.
```

------------------------------------------------------------------------

# 41. DEFINITION OF DONE

A feature is complete only after:

``` text
Requirement
 ↓
DB model if required
 ↓
Pydantic schema
 ↓
Service
 ↓
API
 ↓
Authorization
 ↓
Frontend
 ↓
Persistence
 ↓
Error handling
 ↓
Logging/audit where required
 ↓
Tests
 ↓
E2E verification
 ↓
Documentation
```

------------------------------------------------------------------------

# 42. FINAL ARCHITECTURE

``` text
                         VERIDICA
                            │
                     USER / OWNER
                            │
                       Submit Idea
                            ↓
                 REQUIREMENT AGENT
                            ↓
                  Requirement Spec
                            ↓
                    AI BUILDER
                            ↓
                Build / Test / Validate
                            ↓
                  VISUAL DEMO V1
                            ↓
                 Publish / Assign
                            ↓
                  REVIEWER PORTAL
                            ↓
              Use / Test Interactive Demo
                            ↓
                    REAL FEEDBACK
                            ↓
                      POSTGRESQL
                            ↓
                       REDIS EVENT
                            ↓
                     CELERY WORKER
                            ↓
                    LANGGRAPH FLOW
                            ↓
       ┌────────────────────┼────────────────────┐
       ↓                    ↓                    ↓
 Authenticity          Trust Engine       NLP/Embeddings
       └────────────────────┼────────────────────┘
                            ↓
                  CONSENSUS ENGINE
                            ↓
                FEATURE PRIORITIZATION
                            ↓
                   EVOLUTION AGENT
                            ↓
                       V2 PROTOTYPE
                            ↓
                 DECISION INTELLIGENCE
                            ↓
               ┌────────────┴────────────┐
               ↓                         ↓
        USER DASHBOARD             ADMIN MONITOR
```

------------------------------------------------------------------------

# 43. FINAL ONE-LINE ARCHITECTURE

``` text
React + TypeScript
→ FastAPI
→ PostgreSQL/pgvector + Redis
→ Celery
→ LangGraph
→ Amazon Bedrock
→ Visual Prototype Builder
→ Real Reviewer Feedback
→ Trust + Consensus
→ Idea Evolution
→ WebSocket Dashboard
→ AWS ECS/Fargate + RDS + ElastiCache + S3 + CloudFront
```

------------------------------------------------------------------------

# 44. FINAL IMPLEMENTATION PRINCIPLE

Veridica is complete only when this real loop works:

**Idea → Requirements → Code → Visual Demo → Real Usage → Real Feedback
→ Trust Analysis → Consensus → V2 → Decision Intelligence**

The reviewer should be able to **see the idea, interact with it, test
it, give evidence-based feedback, and see how feedback contributes to
the next version**.

The dashboard is not the product by itself.

The **Idea → Code → Demo → Review → Trust → Evolution** loop is the
product.
