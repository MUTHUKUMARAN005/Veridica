# Prototype Builder Boundary

The first controlled source generator lives in `backend/app/agents/ai_builder.py`.
It supports only education placement preparation and consumes a completed,
schema-validated Requirement Agent result for the exact immutable idea version.
Generation uses a fixed React/TypeScript/Vite scaffold, allowlisted file paths,
dependencies, scripts, components, and local-only behavior. Requirement content is
serialized as JSON data and rendered as text; it is not used as executable source.

The API stores generated files separately in ignored private storage, with hashes and
file metadata in PostgreSQL. Static checks cover paths, dependencies, scripts,
imports, disallowed capabilities, required files, and size. These checks do not run
the generated source and do not prove that it builds or is safe at runtime.

**Build and preview are blocked in the current Codespaces environment.** No
independently restricted disposable execution boundary is present, so neither
FastAPI nor the ordinary Celery worker invokes Node, npm, Vite, generated source, or
build scripts. Records remain `blocked_isolation` and `unpublished`, with no preview
URL or built artifact. Do not label source output a working prototype.

Before enabling builds, provide a separately reviewed nonprivileged executor with
denied network egress, no application credentials, CPU/memory/time/output limits,
allowlisted dependencies, cleanup, build/type/lint/test checks, versioned artifacts,
and audit records. Publish only validated static artifacts on a separate restricted
origin; never share application credentials with previews.