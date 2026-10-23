import { expect, test } from '@playwright/test'

test('desktop workspace, all owner routes, charts and console stay healthy', async ({ page }, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Your daily dose of possibility.' })).toBeVisible()
  await expect(page.locator('.post-media > img')).toHaveCount(2)
  await expect.poll(() => page.locator('.post-media > img').evaluateAll((images) => images.every((image) => (image as HTMLImageElement).naturalWidth > 0))).toBeTruthy()
  await page.screenshot({ path: testInfo.outputPath('dashboard-desktop.png'), fullPage: true })
  for (const route of ['/ideas', '/prototypes', '/feedback', '/analytics', '/trust', '/consensus', '/evolution', '/reports', '/workflows', '/settings']) {
    await page.goto(`/#${route}`)
    await expect(page.locator('h1')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Page not found' })).toHaveCount(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  }
  await page.goto('/#/analytics')
  await expect(page.locator('canvas')).toHaveCount(2)
  await expect(page.getByText('3.7/5', { exact: true })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('analytics-desktop.png'), fullPage: true })
  await page.getByLabel('Select idea').selectOption('found')
  await expect(page.getByRole('heading', { name: 'Analytics need feedback' })).toBeVisible()
  expect(errors).toEqual([])
})

test('idea form validation, local persistence, search and honest build state', async ({ page }) => {
  await page.goto('/#/ideas/new')
  await page.getByRole('button', { name: 'Save idea' }).click()
  await expect(page.getByText('Add a title.', { exact: true })).toBeVisible()
  await page.getByLabel('Idea title').fill('Neighborhood Library')
  await page.getByLabel('Target users').fill('Local readers and volunteers')
  await page.getByLabel('Problem statement').fill('Residents cannot easily discover and borrow books from neighbors.')
  await page.getByLabel('Proposed solution').fill('A local lending library with searchable listings and pickup requests.')
  await page.getByLabel('Core features').fill('Book search\nBorrow requests\nPickup scheduling')
  await page.getByRole('button', { name: 'Save idea' }).click()
  await expect(page.getByRole('heading', { name: 'Neighborhood Library', exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Neighborhood Library', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Prototype workspace', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'No generated prototype yet' })).toBeVisible()
  await page.goto('/#/ideas')
  await page.getByLabel('Search ideas').fill('Neighborhood')
  await expect(page.locator('.project-card')).toHaveCount(1)
})

test('reviewer uses a real sample prototype and submits version-linked local feedback', async ({ page }, testInfo) => {
  await page.goto('/')
  await page.getByLabel('Preview portal').selectOption('reviewer')
  await page.getByRole('link', { name: 'Start review' }).click()
  await page.getByRole('button', { name: 'Open prototype', exact: true }).click()
  await page.getByRole('button', { name: 'Save Orbit Labs', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Unsave Orbit Labs', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Opportunities', exact: true }).click()
  await page.getByLabel('Search opportunities').fill('Python')
  await expect(page.locator('.job-card')).toHaveCount(1)
  await page.getByRole('button', { name: 'Resume', exact: true }).click()
  await page.getByLabel('Add contact details and portfolio', { exact: true }).check()
  await page.getByRole('button', { name: 'Roadmap', exact: true }).click()
  await page.getByLabel('Review your target role', { exact: true }).check()
  await expect(page.getByRole('progressbar', { name: 'Roadmap completion' })).toHaveAttribute('value', '1')
  await page.screenshot({ path: testInfo.outputPath('reviewer-prototype.png'), fullPage: true })
  await page.getByText('Detailed rating review (optional)', { exact: true }).click()
  for (const task of ['Explore an opportunity', 'Try the resume checklist', 'Inspect the preparation roadmap']) await page.getByLabel(task, { exact: true }).check()
  for (const dimension of ['usability', 'usefulness', 'feasibility', 'completeness', 'rating']) await page.getByRole('radio', { name: `${dimension} 4 stars`, exact: true }).check()
  await page.getByRole('radio', { name: 'Yes', exact: true }).check()
  await page.getByLabel('What worked well?').fill('Saving an opportunity worked and the resume checklist was clear.')
  await page.getByLabel('Where did you get stuck?').fill('I wanted more information about the opportunity matching criteria.')
  await page.getByLabel('What should improve next?').fill('Show the matching criteria beside each opportunity.')
  await page.getByLabel('Your testing context').fill('Desktop Chrome; searched Python roles, saved a job, and tested checklists.')
  await page.getByRole('button', { name: 'Submit review', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Your perspective is recorded.' })).toBeVisible()
  await page.getByLabel('Preview portal').selectOption('owner')
  await page.goto('/#/feedback')
  await page.getByLabel('Feedback source').selectOption('Local reviews')
  await expect(page.locator('.feedback-detail')).toHaveCount(1)
  await expect(page.getByText('Show the matching criteria beside each opportunity.', { exact: true })).toBeVisible()
  await page.reload()
  await expect(page.locator('.feedback-detail')).toHaveCount(4)
})

test('evolution preserves V1 and exports an evidence-linked report', async ({ page }) => {
  await page.goto('/#/evolution')
  await expect(page.getByRole('button', { name: 'Create change proposal' })).toBeDisabled()
  await page.getByLabel('Impact for review-1', { exact: true }).selectOption('3')
  await page.getByLabel('Effort for review-1', { exact: true }).selectOption('small')
  await page.locator('.priority-list input').first().check()
  await page.getByRole('button', { name: 'Create change proposal' }).click()
  await expect(page.getByText('V1 / Preserved', { exact: true })).toBeVisible()
  await expect(page.getByText('V2 / Proposal', { exact: true })).toBeVisible()
  await expect(page.getByText('V2 build pending Python workflow', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'View decision report', exact: true }).click()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export report', exact: true }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('placement-preview-report.md')
  const records = await page.evaluate(() => JSON.parse(localStorage.getItem('veridica.frontend-preview.v1')!).state)
  expect(records.ideas[0].version).toBe(1)
  expect(records.evolutions[0].evidence).toEqual(['review-1'])
})

test('admin assignments, duplicate prevention, and reset confirmation', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Save Campus Compass', exact: true }).click()
  await page.getByLabel('Preview portal').selectOption('admin')
  await page.getByRole('button', { name: 'Assign reviewer', exact: true }).click()
  await page.getByLabel('Reviewer', { exact: true }).selectOption('Arjun Patel')
  await page.getByRole('dialog').getByRole('button', { name: 'Assign reviewer', exact: true }).click()
  await expect(page.getByRole('cell', { name: 'Arjun Patel', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Assign reviewer', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Assign reviewer', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('already assigned')
  await page.getByRole('button', { name: 'Close dialog' }).click()
  await page.getByRole('link', { name: 'Settings', exact: true }).click()
  await page.getByRole('button', { name: 'Reset preview', exact: true }).click()
  await page.getByRole('button', { name: 'Cancel', exact: true }).click()
  await page.getByRole('button', { name: 'Reset preview', exact: true }).click()
  await page.getByRole('button', { name: 'Reset local data', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('restored')
  expect(await page.evaluate(() => localStorage.getItem('veridica.saved-ideas.v1'))).toBeNull()
})

test('mobile navigation and prototype stay within the viewport', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.screenshot({ path: testInfo.outputPath('dashboard-mobile.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await page.getByRole('link', { name: 'My ideas', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Your ideas', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Open Campus Compass', exact: true }).click()
  await page.getByRole('link', { name: 'Launch prototype', exact: true }).click()
  await page.getByRole('button', { name: 'Mobile preview', exact: true }).click()
  await page.getByRole('button', { name: 'Opportunities', exact: true }).click()
  await page.getByLabel('Opportunity category').selectOption('Design')
  await expect(page.locator('.job-card')).toHaveCount(1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path: testInfo.outputPath('prototype-mobile.png'), fullPage: true })
})

test('second prototype records requests and can be published for review', async ({ page }) => {
  await page.goto('/#/ideas/circular/prototype')
  await page.getByLabel('Location and details').fill('The recycling bin near the library has not been collected this week.')
  await page.getByRole('button', { name: 'Submit sample request' }).click()
  await expect(page.getByText('Recorded locally', { exact: true })).toBeVisible()
  await expect(page.locator('.request-row')).toHaveCount(1)
  await page.getByRole('combobox', { name: 'Preferred day' }).selectOption('Friday')
  await expect(page.getByText('Friday · 8:00 AM to 12:00 PM')).toBeVisible()
  await page.getByRole('link', { name: 'Idea details', exact: true }).click()
  await page.getByRole('button', { name: 'Publish for review', exact: true }).click()
  await expect(page.locator('.detail-meta').getByText('Review open', { exact: true })).toBeVisible()
  await page.getByRole('tab', { name: 'Requirements', exact: true }).click()
  await expect(page.getByText('Offline preview brief', { exact: true })).toBeVisible()
  await expect(page.getByText('This is owner-provided preview content. No AI workflow has run in offline preview mode.', { exact: true })).toBeVisible()
})

test('authenticated owner sees safe interactive preview without executing generated source', async ({ page }) => {
  const timestamp = '2026-10-23T00:00:00Z'
  const version = {
    id: 'idea-version-1',
    owner_id: 'owner-1',
    version_id: 'idea-version-1',
    source_version_id: null,
    created_by_id: 'owner-1',
    change_summary: 'Initial idea submission',
    title: 'Campus Compass',
    category: 'Education',
    problem: 'Students need a better placement preparation process.',
    solution: 'A guided workspace for career preparation.',
    audience: 'College students',
    features: ['Preparation roadmap'],
    constraints: 'No live integrations.',
    version: 1,
    status: 'Draft',
    created_at: timestamp,
    updated_at: timestamp,
    version_created_at: timestamp,
    assets: [],
  }
  const requirement = {
    id: 'requirement-run-1',
    idea_id: 'idea-1',
    idea_version_id: version.id,
    source_version: 1,
    workflow_run_id: 'requirements-workflow-1',
    provider: 'ollama',
    model_version: 'deterministic-test-double',
    prompt_version: 'requirement-spec-v1',
    status: 'completed',
    validation_status: 'valid',
    result: {
      problem: [{ text: 'A clearer placement preparation process.', basis: 'explicit', source_fields: ['problem'] }],
      target_users: [{ text: 'College students.', basis: 'explicit', source_fields: ['audience'] }],
      user_journeys: [],
      core_features: [{ text: 'Preparation roadmap.', basis: 'explicit', source_fields: ['features'] }],
      constraints: [],
      assumptions: [],
      acceptance_criteria: [],
      open_questions: ['Which opportunity data source is intended?'],
    },
    error_message: null,
    attempt_count: 1,
    created_at: timestamp,
    started_at: timestamp,
    completed_at: timestamp,
    updated_at: timestamp,
  }
  const prototype = {
    id: 'prototype-build-1',
    idea_id: 'idea-1',
    idea_version_id: version.id,
    source_version: 1,
    requirement_analysis_run_id: requirement.id,
    workflow_run_id: 'prototype-workflow-1',
    template_id: 'education-placement-preparation',
    template_version: '1.0',
    status: 'source_generated',
    validation_status: 'passed',
    build_status: 'blocked_isolation',
    publish_status: 'unpublished',
    plan: {
      preview_spec: {
        schema_version: '1',
        source_version: 1,
        requirement_analysis_id: requirement.id,
        title: 'Campus Compass',
        screens: [
          {
            key: 'overview',
            title: 'Overview',
            components: [
              { type: 'heading', text: 'Campus Compass' },
              { type: 'text', text: '<img src=x onerror=window.__previewInjected=true>' },
              { type: 'button', label: 'Mark explored', action: 'mark-complete' },
            ],
          },
          {
            key: 'features',
            title: 'Features',
            components: [{ type: 'search', label: 'Search validated features', items: ['Preparation roadmap'] }],
          },
          {
            key: 'journeys',
            title: 'Journeys',
            components: [{ type: 'checklist', title: 'Validated journey steps', items: ['Review roadmap'] }],
          },
          {
            key: 'questions',
            title: 'Questions',
            components: [{ type: 'form', label: 'Try a local prototype note', placeholder: 'Write a note', submit_label: 'Save note locally' }],
          },
        ],
      },
    },
    manifest: null,
    validation_results: {
      scope: 'Static checks only.',
      checks: [{ name: 'allowlisted_paths', status: 'passed' }],
      build_boundary_available: false,
      built_artifact_available: false,
    },
    source_files: [{ path: 'src/Prototype.tsx', sha256: 'a'.repeat(64), size_bytes: 45 }],
    artifact_metadata: {
      artifact_type: 'generated_source',
      file_count: 1,
      total_size_bytes: 45,
      source_sha256: 'b'.repeat(64),
      built_artifact_available: false,
    },
    preview_url: null,
    error_message: null,
    created_at: timestamp,
    completed_at: timestamp,
  }
  let analysisStarted = false
  const persistedReview = {
    id: 'feedback-1',
    assignment_id: 'assignment-1',
    idea_id: 'idea-1',
    idea_version_id: version.id,
    reviewer_id: 'reviewer-1',
    review_session_id: 'session-1',
    idempotency_key: 'feedback-key',
    rating: 4,
    usability_score: 4,
    usefulness_score: 4,
    completeness_score: 3,
    feasibility_score: 4,
    would_use: true,
    feedback_text: 'A clearer placement roadmap would help students prepare.',
    strengths: 'The preparation flow is understandable.',
    concerns: 'The next steps are not explicit enough.',
    suggested_improvements: 'Add a staged preparation roadmap.',
    usage_context: 'Reviewed the assigned version on a laptop.',
    created_at: timestamp,
    analysis_status: 'received',
    analysis_error: null,
  }
  const feedbackAnalysis = {
    id: 'feedback-analysis-1',
    idea_id: 'idea-1',
    idea_version_id: version.id,
    source_version: 1,
    workflow_run_id: 'feedback-workflow-1',
    input_digest: 'c'.repeat(64),
    source_feedback_ids: [persistedReview.id],
    provider: 'ollama',
    model_version: 'test-model',
    embedding_model_version: 'nomic-embed-text',
    prompt_version: 'feedback-intelligence-v1',
    status: 'completed',
    validation_status: 'valid',
    result: {
      source_feedback_ids: [persistedReview.id],
      quality: [{
        feedback_id: persistedReview.id,
        relevance: 0.8,
        constructiveness: 0.7,
        originality: 0.8,
        internal_consistency: 0.9,
        spam_risk: 0.1,
        authenticity_indicator: 0.9,
        self_reported_confidence: 0.8,
        uncertainty: 'Only this persisted review was available.',
        explanations: { relevance: 'Addresses the idea.' },
      }],
      deterministic_signals: [{
        feedback_id: persistedReview.id,
        text_characters: 60,
        structured_ratings_complete: true,
        exact_duplicate_of: null,
      }],
      themes: [{
        label: 'Preparation roadmap',
        kind: 'feature_request',
        summary: 'The review requests clearer preparation steps.',
        feedback_ids: [persistedReview.id],
      }],
      contradictions: [],
      duplicate_pairs: [],
      trust: [{
        feedback_id: persistedReview.id,
        score: 0.82,
        factor_json: {
          review_quality: 0.82,
          historical_accuracy: null,
          peer_alignment: null,
          consistency: null,
          verified_expertise: null,
          community_validation: null,
        },
        factor_weights: {
          review_quality: 0.3,
          historical_accuracy: 0.2,
          peer_alignment: 0.15,
          consistency: 0.15,
          verified_expertise: 0.1,
          community_validation: 0.1,
        },
        formula_version: 'trust-baseline-partial-v1',
        evidence_coverage: 0.3,
        missing_factors: ['historical_accuracy', 'peer_alignment', 'consistency', 'verified_expertise', 'community_validation'],
        interpretation: 'Partial feedback-level estimate, not a reputation score.',
      }],
      consensus: {
        sample_size: 1,
        evidence_coverage: 1,
        raw_support_count: 1,
        raw_support: 1,
        normalized_weight_denominator: 0.5904,
        raw_feedback_weights: { 'feedback-1': 0.5904 },
        normalized_feedback_weights: { 'feedback-1': 1 },
        weighted_support: 1,
        confidence_indicator: 0.1333333333,
        confidence_method: 'Uncalibrated indicator using sample size and model confidence.',
        uncertainty: 'Small samples are not definitive.',
        evidence_ids: [persistedReview.id],
      },
      priorities: [{
        rank: 1,
        priority: 'P1',
        title: 'Preparation roadmap',
        rationale: 'The review asks for clearer preparation steps.',
        feedback_ids: [persistedReview.id],
        theme_labels: ['Preparation roadmap'],
        evidence_count: 1,
        weighted_support: 1,
        impact: 'medium',
        impact_rationale: 'It addresses the stated preparation problem.',
        feasibility: 'unknown',
        feasibility_rationale: 'Implementation effort is not recorded.',
        assumptions: [],
        missing_inputs: ['Implementation effort'],
      }],
    },
    error_message: null,
    attempt_count: 1,
    created_at: timestamp,
    started_at: timestamp,
    completed_at: timestamp,
  }
  let evolutionProposal: Record<string, unknown> | null = null
  let decisionReport: Record<string, unknown> | null = null

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path === '/api/v1/auth/login') {
      await route.fulfill({
        json: {
          access_token: 'test-owner-token',
          token_type: 'bearer',
          user: { id: 'owner-1', email: 'owner@example.test', role: 'owner' },
        },
      })
    } else if (path === '/api/v1/ideas' && request.method() === 'GET') {
      await route.fulfill({ json: { items: [{ ...version, id: 'idea-1' }], total: 1, limit: 20, offset: 0 } })
    } else if (path === '/api/v1/ideas/idea-1') {
      await route.fulfill({ json: { ...version, id: 'idea-1', versions: [version], status_history: [] } })
    } else if (path.endsWith('/versions/1/feedback')) {
      await route.fulfill({ json: [persistedReview] })
    } else if (path.endsWith('/versions/1/feedback-analysis') && request.method() === 'POST') {
      analysisStarted = true
      await route.fulfill({ json: feedbackAnalysis })
    } else if (path.endsWith('/versions/1/feedback-analysis')) {
      await route.fulfill({ json: analysisStarted ? feedbackAnalysis : null })
    } else if (path.endsWith('/versions/1/feedback-analysis/feedback-analysis-1')) {
      await route.fulfill({ json: feedbackAnalysis })
    } else if (path.endsWith('/requirements')) {
      await route.fulfill({ json: requirement })
    } else if (path.endsWith('/prototypes') && request.method() === 'GET') {
      await route.fulfill({ json: null })
    } else if (path.endsWith('/prototypes') && request.method() === 'POST') {
      await route.fulfill({ json: prototype })
    } else if (path.endsWith('/prototypes/prototype-build-1/source')) {
      await route.fulfill({
        json: {
          prototype_build_id: prototype.id,
          files: { 'src/Prototype.tsx': "export default function Safe() { return <div>source-only</div> }" },
        },
      })
    } else if (path.endsWith('/evolution') && request.method() === 'POST') {
      evolutionProposal = {
        id: 'evolution-1',
        idea_id: 'idea-1',
        idea_version_id: version.id,
        source_version: 1,
        requirement_analysis_run_id: requirement.id,
        feedback_analysis_run_id: feedbackAnalysis.id,
        source_feedback_ids: [persistedReview.id],
        suggestions: [{
          rank: 1,
          priority: 'P1',
          title: 'Preparation roadmap',
          rationale: 'The persisted review requests clearer steps.',
          source_feedback_ids: [persistedReview.id],
          expected_benefit: { interpretation: 'Addresses the cited concern.', qualitative_impact: 'medium', weighted_support: 1 },
          assumptions: [],
          risks: [{ feedback_id: persistedReview.id, concern: persistedReview.concerns }],
          validation_criteria: [],
          validation_note: 'Owner and reviewers must validate this change.',
          feasibility: 'unknown',
          feasibility_rationale: 'No effort estimate is recorded.',
          missing_inputs: ['Implementation effort'],
          builder_supported: true,
        }],
        status: 'proposed',
        target_version_id: null,
        prototype_build_id: null,
        provider: 'ollama',
        model_version: 'test-model',
        prompt_version: 'evolution-evidence-proposals-v1',
        validation_results: {},
        created_at: timestamp,
        approved_at: null,
      }
      await route.fulfill({ json: evolutionProposal })
    } else if (path.endsWith('/evolution') && request.method() === 'GET') {
      await route.fulfill({ json: evolutionProposal })
    } else if (path.endsWith('/evolution/evolution-1/approve')) {
      evolutionProposal = {
        ...evolutionProposal,
        status: 'approved',
        target_version_id: 'idea-version-2',
        prototype_build_id: 'prototype-build-2',
        validation_results: {
          target_version: 2,
          prototype_source_status: 'source_generated',
          prototype_build_status: 'blocked_isolation',
          prototype_publish_status: 'unpublished',
        },
      }
      await route.fulfill({ json: evolutionProposal })
    } else if (path.endsWith('/decision-reports') && request.method() === 'POST') {
      decisionReport = {
        id: 'decision-report-1',
        idea_id: 'idea-1',
        idea_version_id: version.id,
        source_version: 1,
        requirement_analysis_run_id: requirement.id,
        feedback_analysis_run_id: feedbackAnalysis.id,
        evolution_proposal_id: 'evolution-1',
        source_feedback_ids: [persistedReview.id],
        report_version: 'decision-report-v1',
        report: { problem: { value: version.problem, classification: 'observed_owner_input' } },
        created_at: timestamp,
      }
      await route.fulfill({ json: decisionReport })
    } else if (path.endsWith('/decision-reports')) {
      await route.fulfill({ json: decisionReport })
    } else {
      await route.fulfill({ status: 404, json: { detail: 'Unexpected API request.' } })
    }
  })

  await page.goto('/#/auth')
  await page.getByLabel('Email address').fill('owner@example.test')
  await page.getByLabel('Password').fill('test-password-value')
  await page.getByRole('button', { name: 'Sign in', exact: false }).click()
  await page.goto('/#/ideas/idea-1')
  await page.getByRole('tab', { name: 'Requirements', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Safe prototype source' })).toBeVisible()
  await page.getByRole('button', { name: 'Generate prototype source' }).click()
  await expect(page.getByText('Build: blocked — an isolated disposable build environment is not available.')).toBeVisible()
  await expect(
    page.locator('.prototype-source-panel').getByText('Generated source:').locator('..'),
  ).toContainText('not executed')
  await expect(page.getByRole('region', { name: 'Schema-driven prototype preview' })).toBeVisible()
  await expect(page.getByText('<img src=x onerror=window.__previewInjected=true>', { exact: true })).toBeVisible()
  await expect(page.locator('.schema-prototype-screen img')).toHaveCount(0)
  expect(await page.evaluate(() => (window as Window & { __previewInjected?: boolean }).__previewInjected)).toBeUndefined()
  await page.getByRole('button', { name: 'Features', exact: true }).click()
  await page.getByLabel('Search validated features').fill('roadmap')
  await expect(page.getByText('Preparation roadmap', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Journeys', exact: true }).click()
  await page.getByLabel('Review roadmap').check()
  await page.getByRole('button', { name: 'Questions', exact: true }).click()
  await page.getByLabel('Try a local prototype note').fill('This remains local.')
  await page.getByRole('button', { name: 'Save note locally', exact: true }).click()
  await expect(page.getByText('Note saved in this browser session only.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'View generated source' }).click()
  await page.getByText('src/Prototype.tsx', { exact: true }).click()
  await expect(page.getByText(/export default function Safe/)).toBeVisible()
  await page.goto('/#/analytics')
  await expect(page.getByText('1 persisted review in this version snapshot.')).toBeVisible()
  await page.getByRole('button', { name: 'Analyze persisted feedback' }).click()
  await expect(page.getByText('Preparation roadmap', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('normalized weighted support 1.0000')).toBeVisible()
  await page.goto('/#/trust')
  await expect(page.getByText('feedback-1', { exact: true })).toBeVisible()
  await expect(page.getByText('historical_accuracy, peer_alignment, consistency, verified_expertise, community_validation')).toBeVisible()
  await page.goto('/#/consensus')
  await expect(page.getByText('Trust-weighted support', { exact: true })).toBeVisible()
  await expect(page.getByText('1 of 1 persisted reviews would use this version.')).toBeVisible()
  await page.goto('/#/feedback')
  await expect(page.getByText('A clearer placement roadmap would help students prepare.')).toBeVisible()
  await page.goto('/#/evolution?idea=idea-1')
  await page.getByRole('button', { name: 'Generate evidence-linked proposal' }).click()
  await expect(page.getByText('Generated suggestions — not approved')).toBeVisible()
  await page.getByRole('checkbox', { name: 'Approve Preparation roadmap' }).check()
  await page.getByRole('button', { name: 'Approve 1 selected change(s)' }).click()
  await expect(page.getByText('Candidate V2 · Draft')).toBeVisible()
  await expect(page.getByText(/build: blocked_isolation/)).toBeVisible()
  await page.goto('/#/reports?idea=idea-1')
  await page.getByRole('button', { name: 'Create report snapshot' }).click()
  await expect(page.getByText('Persisted snapshot · decision-report-v1')).toBeVisible()
  await expect(page.getByText(/decision-report-1/)).toBeVisible()
})

test('offline auth preview sends or saves no credentials and preserves the chosen portal', async ({ page }) => {
  const authRequests: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/auth/')) authRequests.push(request.url())
  })
  await page.goto('/#/auth')
  await page.getByRole('tab', { name: 'Create account', exact: true }).click()
  await page.getByLabel('Email address').fill('preview@example.com')
  await page.getByLabel('Password', { exact: true }).fill('test-only-password')
  const stored = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))
  expect(stored).not.toContain('test-only-password')
  expect(stored).not.toContain('preview@example.com')
  await expect(page.getByText('Offline mode does not send or save credentials.')).toBeVisible()
  await page.getByLabel('Preview role').selectOption('reviewer')
  await page.getByRole('button', { name: 'Continue to preview', exact: true }).click()
  expect(authRequests).toEqual([])
  await page.reload()
  await expect(page.getByLabel('Preview portal')).toHaveValue('reviewer')
  await page.goto('/#/analytics')
  await expect(page.getByRole('heading', { name: 'This view belongs to the owner portal' })).toBeVisible()
})

test('social feed saves projects, filters without changing review evidence, and shares links', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.feed-post')).toHaveCount(3)
  await page.getByRole('tab', { name: 'Saved', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Your collection starts here' })).toBeVisible()
  await page.getByRole('tab', { name: 'For you', exact: true }).click()
  await page.getByRole('button', { name: 'Save Campus Compass', exact: true }).click()
  await page.getByRole('tab', { name: 'Saved', exact: true }).click()
  await expect(page.locator('.feed-post')).toHaveCount(1)
  await page.reload()
  await page.getByRole('tab', { name: 'Saved', exact: true }).click()
  await expect(page.locator('.feed-post')).toHaveCount(1)
  await page.getByRole('button', { name: 'Share Campus Compass', exact: true }).click()
  await expect(page.getByLabel('Project URL')).toHaveValue('http://127.0.0.1:5173/#/ideas/placement')
  await page.getByRole('button', { name: 'Close dialog' }).click()
  await page.getByRole('button', { name: 'Unsave Campus Compass', exact: true }).click()
  await expect(page.locator('.feed-post')).toHaveCount(0)
  await page.getByRole('tab', { name: 'Review open', exact: true }).click()
  await expect(page.locator('.feed-post')).toHaveCount(1)
  const records = await page.evaluate(() => JSON.parse(localStorage.getItem('veridica.frontend-preview.v1')!).state)
  expect(records.reviews).toHaveLength(3)
  expect(records.ideas[0].version).toBe(1)
})

test('social feed fits small mobile screens and quick navigation works', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 360, height: 800 })
  await page.goto('/')
  await expect(page.getByRole('navigation', { name: 'Quick navigation' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path: testInfo.outputPath('social-feed-mobile.png'), fullPage: true })
  await page.getByRole('link', { name: 'Create idea', exact: true }).click()
  await expect(page.getByLabel('Idea title')).toBeVisible()
  await page.getByRole('link', { name: 'Home feed', exact: true }).click()
  await page.getByRole('link', { name: 'View Campus Compass story', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Campus Compass', exact: true })).toBeVisible()
})

test('review comments become feasible, evidence-linked priorities without invented ratings', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByLabel('Preview portal').selectOption('reviewer')
  await page.getByRole('link', { name: 'Start review' }).click()
  await expect(page.getByRole('button', { name: 'Post comment', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Open prototype', exact: true }).click()
  await page.getByRole('button', { name: 'Opportunities', exact: true }).click()
  await page.getByLabel('Your comment', { exact: true }).fill('Keep role filters visible while scrolling the opportunity list.')
  await page.getByLabel('What did you try?', { exact: true }).fill('I searched for Python roles and lost the filter controls when scrolling.')
  await page.getByRole('button', { name: 'Post comment', exact: true }).click()
  await expect(page.locator('.comment-entry')).toHaveCount(1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path: testInfo.outputPath('comment-mobile.png'), fullPage: true })
  await expect(page.getByRole('button', { name: 'Useful comment by Maya Chen', exact: true })).toBeDisabled()
  const commentId = await page.locator('.comment-entry').getAttribute('id')
  await page.getByLabel('Preview portal').selectOption('owner')
  await page.getByRole('button', { name: 'Comments on Campus Compass', exact: true }).click()
  await page.getByRole('button', { name: 'Useful comment by Maya Chen', exact: true }).click()
  await page.getByRole('link', { name: 'Prioritize improvements', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Create change proposal' })).toBeDisabled()
  await page.getByLabel(`Impact for ${commentId}`, { exact: true }).selectOption('3')
  await page.getByLabel(`Effort for ${commentId}`, { exact: true }).selectOption('small')
  await expect(page.locator(`[data-evidence-id="${commentId}"]`)).toContainText('P1')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path: testInfo.outputPath('comment-priorities.png'), fullPage: true })
  await page.locator('.priority-list input').first().check()
  await page.getByRole('button', { name: 'Create change proposal', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Selected priority order' })).toBeVisible()
  await expect(page.getByText('V1 / Preserved', { exact: true })).toBeVisible()
  const records = await page.evaluate(() => JSON.parse(localStorage.getItem('veridica.frontend-preview.v1')!).state)
  expect(records.reviews).toHaveLength(3)
  expect(records.comments).toHaveLength(1)
  expect(records.assignments[0].status).toBe('Completed')
  expect(records.evolutions[0].evidence).toEqual([commentId])
  expect(records.evolutions[0].priorities[0].priority).toBe('P1')
  expect(records.evolutions[0].priorityFormulaVersion).toBe('preview-impact-effort-v1')
  await page.getByRole('link', { name: 'Source evidence', exact: true }).click()
  await expect(page.locator(`[id="${commentId}"]`)).toBeInViewport()
})

test('interest discovery counts unique successful link copies, not share-dialog opens', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.goto('/')
  const post = page.locator('.feed-post').filter({ has: page.getByRole('heading', { name: 'Campus Compass', exact: true }) })
  await post.getByRole('button', { name: 'Like Campus Compass', exact: true }).click()
  await expect(post.getByText('1 interested', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Share Campus Compass', exact: true }).click()
  await expect(post.getByText('0 unique link copies', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Copy link', exact: true }).click()
  await expect(post.getByText('1 unique link copy', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Share Campus Compass', exact: true }).click()
  await page.getByRole('button', { name: 'Copy link', exact: true }).click()
  await expect(post.getByText('1 unique link copy', { exact: true })).toBeVisible()
  await page.getByRole('tab', { name: 'Interest', exact: true }).click()
  await expect(page.locator('.feed-post').first()).toContainText('Campus Compass')
  await page.reload()
  await expect(post.getByRole('button', { name: 'Unlike Campus Compass', exact: true })).toHaveAttribute('aria-pressed', 'true')
})

test('existing browser workspaces upgrade without losing ideas or reviews', async ({ page }) => {
  await page.goto('/')
  await page.evaluate(() => {
    const stored = JSON.parse(localStorage.getItem('veridica.frontend-preview.v1')!)
    delete stored.state.comments
    delete stored.state.signals
    delete stored.state.assessments
    localStorage.setItem('veridica.frontend-preview.v1', JSON.stringify(stored))
  })
  await page.reload()
  await expect(page.locator('.feed-post')).toHaveCount(3)
  const records = await page.evaluate(() => JSON.parse(localStorage.getItem('veridica.frontend-preview.v1')!).state)
  expect(records.reviews).toHaveLength(3)
  expect(records.comments).toEqual([])
  expect(records.signals).toEqual([])
  await page.goto('/#/evolution')
  await expect(page.locator('.assessment-item')).toHaveCount(3)
})