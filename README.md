# Veridica

**Trust-aware idea validation and decision intelligence.**

Veridica helps an idea owner capture an idea, define requirements, collect
version-specific reviewer feedback, analyze evidence, and make traceable
improvement decisions.

> **Project status:** Veridica has a working local development implementation,
> but it is not production-ready. The persisted workflow and authenticated owner
> browser flow have passed local acceptance tests. Live AI inference is not
> verified, and generated prototype code cannot be built or previewed until a
> separately restricted execution environment is available.

## What is implemented

- FastAPI authentication and role-aware, owner-scoped idea APIs.
- PostgreSQL persistence, immutable idea versions, and versioned Alembic
  migrations.
- Version-specific reviewer assignments, review sessions, and idempotent
  feedback submission.
- Asynchronous requirement and feedback-analysis workflows using Celery and
  Redis, with persisted result and provenance records.
- Deterministic trust, consensus, and evidence-linked prioritization.
- Owner-approved evolution candidates and persisted decision-report snapshots.
- React/TypeScript frontend with authenticated API mode and a separate offline
  preview mode.

Generated prototype source is statically validated and stored separately from
the trusted application. It is **not** executed by FastAPI or the normal Celery
worker. Do not treat source generation as a built or working prototype.

## Technology

- Frontend: React, TypeScript, Vite, Tailwind CSS
- API and agents: Python, FastAPI, Pydantic, SQLAlchemy, Alembic, LangGraph
- Durable database: PostgreSQL with pgvector
- Background jobs: Redis and Celery
- AI providers: Ollama for local development; Gemini Developer API is an
  optional development-only adapter

PostgreSQL is the source of truth. Redis is used for job transport, not durable
business records. No Docker or AWS service is required for the local workflow.

## Requirements

- Node.js and npm
- Python 3.12 or later
- A running PostgreSQL instance with the `vector` extension
- A running Redis instance
- Ollama and the configured models only if you want to attempt live local AI
  analysis

The default local configuration expects PostgreSQL on `127.0.0.1:5433` and
Redis on `127.0.0.1:6379`. Configure `.env` for your services as described
below. The application does not start or provision PostgreSQL or Redis for you.

## Local setup

From the repository root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
```

Create a root `.env` using [.env.example](.env.example) as a variable reference.
Set a database URL using the `postgresql+psycopg` driver, a strong random
development `JWT_SECRET`, and the correct Redis URL. Do not copy sample
credentials into a shared or production environment. `.env` is ignored by Git;
never commit it or paste secrets into logs, issues, or chat.

Make sure your PostgreSQL database has pgvector available, then apply migrations:

```bash
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/alembic -c backend/alembic.ini current
```

The current schema head is `0011`. Migrations are forward-only for the normal
development workflow; do not drop or reinitialize an existing database.

## Run Veridica

Start each process in its own terminal from the repository root.

**Terminal 1 — API:**

```bash
backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

**Terminal 2 — Celery worker:**

```bash
backend/.venv/bin/celery -A app.workers.celery_app:celery_app worker --loglevel=INFO --concurrency=1
```

**Terminal 3 — frontend:**

```bash
npm --prefix frontend run dev -- --host 127.0.0.1
```

Open the frontend at <http://127.0.0.1:5173>. The API is at
<http://127.0.0.1:8000>, interactive API documentation at
<http://127.0.0.1:8000/docs>, and readiness status at
<http://127.0.0.1:8000/api/v1/health/ready>.

The frontend offers an explicit offline preview as well as authenticated API
mode. Preview records are browser-local fixtures; they are not PostgreSQL
business records. New public registrations receive the owner role. Reviewer and
admin role changes are available only through the audited backend operator CLI;
there is no public self-promotion API. After creating an account, an operator
with database access bootstraps the first admin once:

```bash
cd backend
.venv/bin/python -m app.cli.manage_user_role \
  --email admin@example.com \
  --role admin \
  --reason "Initial project operator bootstrap" \
  --bootstrap-admin
```

After an admin exists, role changes require that admin's account as actor:

```bash
.venv/bin/python -m app.cli.manage_user_role \
  --email reviewer@example.com \
  --role reviewer \
  --actor-email admin@example.com \
  --reason "Approved reviewer account"
```

The CLI refuses repeated bootstrap, unknown accounts, non-admin actors,
role-preserving changes, blank reasons, and demotion of the final admin. Each
accepted change is committed with an append-only PostgreSQL audit event.

## AI and prototype limitations

- `AI_PROVIDER=ollama` requires a reachable Ollama service and the configured
  chat and embedding models. Without them, a live provider workflow cannot
  complete. Unit and acceptance tests use deterministic test doubles and do not
  claim real model output.
- The Gemini adapter is development-only and requires backend-only
  `GEMINI_API_KEY` and `GEMINI_MODEL` configuration. Never expose provider
  credentials to the frontend.
- Prototype generation currently stops at statically validated source. A
  restricted disposable build/preview boundary has not been supplied, so no
  generated source is executed and no working generated prototype is claimed.

## Tests and checks

```bash
# Backend unit tests
backend/.venv/bin/pytest backend/tests -q

# PostgreSQL/pgvector/Redis/Celery integration suite (requires live services)
RUN_INTEGRATION=1 backend/.venv/bin/pytest backend/tests -q

# Frontend unit tests and quality checks
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build

# Offline preview browser regression tests
npm --prefix frontend run test:e2e

# Authenticated browser E2E against PostgreSQL (requires configured DB/services)
npm --prefix frontend run test:e2e:api
```

The API-mode browser test runs a test-only API process inside a PostgreSQL
transaction and rolls back test writes when that process shuts down. The broader
persisted workflow acceptance test uses deterministic AI test doubles.

## Latest one-idea verification

On 2026-10-23:

- Authenticated Playwright Chromium persistence journey: **1 passed**.
- PostgreSQL-backed full workflow acceptance test: **1 passed**.
- Preview browser regression suite: **14 passed**.
- Frontend unit tests: **16 passed**.
- Backend integration suite: **80 passed** in the recorded Phase 8 run.
- PostgreSQL/pgvector, Redis, migration head `0010`, and a Celery worker ping
  were verified during the recorded E2E run. The database is now at `0011`
  after adding the role-provisioning audit table.

These results verify the tested local workflow, not live AI inference,
generated-code execution, deployment, or production reliability. See the
[full one-idea E2E report](docs/ONE_IDEA_E2E_RESULT.md) and
[current setup verification](docs/SETUP_STATUS.md).

## Project documentation

- [Master architecture specification](docs/PROJECT_SPEC.md)
- [Setup and verification status](docs/SETUP_STATUS.md)
- [Remaining work and acceptance checklist](docs/REMAINING_WORK.md)
- [Architecture decisions](docs/DECISIONS.md)
- [One-idea E2E verification report](docs/ONE_IDEA_E2E_RESULT.md)

## Security and production readiness

Do not use this local development setup for production traffic. Production
release remains blocked on a reviewed isolated prototype build/preview
environment, auditable reviewer/admin provisioning, verified live AI-provider
behavior, production data-protection and storage controls, dependency-security
remediation, and deployment/recovery testing. No 24/7 availability or managed
free-tier service is claimed.
