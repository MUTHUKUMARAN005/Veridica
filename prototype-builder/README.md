# Prototype Builder Boundary

Implementation begins in P4, after requirements are validated in P3.
Follow ../docs/PROJECT_SPEC.md sections 3, 10, 11 and 12.

This directory is reserved for controlled templates, an approved component library,
generation and validators. It is deliberately not a runnable arbitrary-code service.
Generated React code must never execute in the API or general Celery worker.

Before enabling builds: provide a separate nonprivileged sandbox with denied network
egress, CPU/memory/time/output limits, an allowlisted dependency set, build/type/lint
checks, versioned S3 artifacts, logs and audit records. Publish only validated static
artifacts on a separate origin; never share application credentials with previews.