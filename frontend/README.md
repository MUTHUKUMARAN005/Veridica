# Veridica Frontend Preview

For diagrams, a step-by-step explanation, benefits and an impact-measurement plan,
see [Data Flow, How It Works, Benefits and Impact](../docs/DATA_FLOW_AND_IMPACT.md).

## Comment-First Review and Evolution

Reviewers can now leave an improvement suggestion, problem, or question after
interacting with their assigned prototype. Detailed star ratings remain available
under an optional expanded review form. Actionable comments complete the local
review assignment; questions remain discussion items. Comments never generate
missing numeric ratings or change the detailed-rating denominator.

The feed and feedback page expose the same version-linked comment threads. Other
participants can mark a comment useful; authors cannot vote for themselves.

- Idea likes express interest. The Interest feed sorts by `2 * unique interested
  participants + min(unique link-copy participants, 3)` for the current version.
- Link copies are recorded only after a successful clipboard write and once per
  participant/version. They are not verified external shares, reach, or conversions.
- Useful-comment votes affect the specific suggestion's priority, capped at three.
- The owner/admin supplies impact (1-3), estimated effort, and any scope/blocker flag.
- Implementation score: `3 * impact + min(useful votes, 3) - effort cost`.
  Effort cost is 1 for small, 3 for medium, and 5 for large changes.
- P1 is score >= 7, P2 is 4-6, and P3 is below 4. Questions, unknown effort,
  and blocked changes cannot enter a proposal.
- Selected changes are stored in priority order with frozen assessments, rationale,
  evidence IDs and formula version `preview-impact-effort-v1`. V1 remains unchanged.

This is a transparent preview heuristic based on human estimates, not an AI trust
formula, measured feasibility score, or automatic production build. Likes and link
copies never affect trust, consensus, or implementation priority. A validated V2
prototype still requires the future Python builder/evolution workflow.

Existing browser records upgrade with empty comment/signal/assessment collections
without losing ideas or reviews. Comments and engagement are local preview records,
not authenticated production evidence. Reset preview clears these records.

Verification for this increment: 14 unit tests, 13 browser tests, lint and production
build passed. Browser coverage includes mobile comment submission, useful votes,
owner estimates, priority-based evolution, original-version preservation, source
links, share deduplication and existing-storage migration.

## Social-Style Interface

The home screen now uses an Instagram-inspired project feed: story-style idea
shortcuts, large screenshots of the actual sample prototypes, feedback/share/save
actions, a saved collection, and mobile bottom navigation. Veridica retains its own
branding and existing owner/reviewer/admin workflows.

Saved ideas use the browser-local key `veridica.saved-ideas.v1` and are cleared by
Reset preview. Bookmarks are not reviewer ratings, trust scores, or evidence of
validation. Share links reference the current local preview, not a published project.
Prototype screenshots are bundled in public/previews; fonts are bundled locally.

The redesign passed 10 browser acceptance tests, the 9 state/client tests, lint,
and production build. A subsequent focused reset test also confirms that bookmarks
are cleared with the sample workspace.

Run from the repository root: `npm --prefix frontend ci`, then
`npm --prefix frontend run dev`. No Docker, backend, login or AWS credentials are needed.
Open the Vite URL, normally http://127.0.0.1:5173/.

## Preview Flows

- Owner: dashboard, searchable ideas, validated submission, detail tabs, prototypes,
  device previews, publishing, and reference filenames (not uploaded file contents).
- Reviewer: assigned projects, interactive demos, test journey, ratings, structured
  evidence, local feedback submission and confirmation.
- Intelligence: feedback search, derived charts, trust/quality pending states, raw
  consensus, manual evidence-linked proposals preserving V1, and exported reports.
- Admin: sample reviewer directory, assignments, duplicate prevention and audit view.
- Settings: JSON export, confirmed reset, and credential-free sign-in/register previews.

Campus Compass supports job search/filtering, bookmarking, resume self-checks and
roadmap completion. Circular City supports sample issue requests and collection
preferences. These are hand-authored templates, not AI-generated artifacts.

## Data Boundaries

Preview records use localStorage key `veridica.frontend-preview.v1`; portal choice
uses sessionStorage key `veridica.preview-role`. Reset is available in Settings.
Role switching is not authentication. Do not enter sensitive data.

Python services will supply real authentication, persistence, requirements, builds,
trust, embeddings, consensus, prioritization and validated evolution. No fake AI
results are generated here. Reports and proposals are labeled preview outputs.

## Verification

```powershell
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Verified on 2026-09-30: 9 unit tests, 8 Playwright tests, clean lint and production
build. Tests cover both prototypes, owner/reviewer/admin flows, persistence, report
export, version preservation, authentication boundaries and mobile navigation.
Screenshots and failure traces are written to test-results/.

Playwright uses installed Edge on Windows and Chromium on Linux. Hash routes work
with static S3/CloudFront hosting; deployment itself is not configured yet.

## Original Scaffold Notes

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
