import { afterEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { login, logout } from './auth.ts'
import {
  approveEvolutionProposal,
  createDecisionReport,
  createEvolutionProposal,
  createIdeaVersion,
  generatePrototypeSource,
  getLatestPrototypeSource,
  getLatestFeedbackAnalysis,
  getLatestRequirementAnalysis,
  getRequirementAnalysis,
  getFeedbackAnalysis,
  getEvolutionProposal,
  getLatestDecisionReport,
  getPrototypeSourceFiles,
  listIdeas,
  listPersistedFeedback,
  publishIdeaVersion,
  startRequirementAnalysis,
  startFeedbackAnalysis,
  updateIdeaStatus,
} from './ideas.ts'

const originalFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = originalFetch
  logout()
})

async function authenticate() {
  globalThis.fetch = async () => new Response(JSON.stringify({
    access_token: 'test-token',
    token_type: 'bearer',
    user: { id: 'owner-id', email: 'owner@example.com', role: 'owner' },
  }), { status: 200 })
  await login('owner@example.com', 'test-password')
}

test('idea clients use paginated server filters and explicit immutable version creation', async () => {
  await authenticate()
  const requests: { path: string; method: string; body: string | undefined }[] = []
  globalThis.fetch = async (input, init) => {
    requests.push({
      path: String(input),
      method: init?.method ?? 'GET',
      body: typeof init?.body === 'string' ? init.body : undefined,
    })
    return new Response(JSON.stringify({ ok: true }), { status: 200 })
  }

  await listIdeas({
    limit: 10,
    offset: 20,
    status: 'Draft',
    category: 'Education',
    q: 'campus idea',
  })
  await createIdeaVersion('idea/one', {
    title: 'Campus Compass V2',
    category: 'Education',
    problem: 'Students need a better way to prepare for placements.',
    solution: 'A guided workspace for preparation and opportunity discovery.',
    audience: 'College students',
    features: ['Matching'],
    constraints: '',
    expected_version: 1,
    change_summary: 'Add a clearer preparation path.',
  })
  await publishIdeaVersion('idea/one', 2)
  await startRequirementAnalysis('idea/one', 2)
  await getLatestRequirementAnalysis('idea/one', 2)
  await getRequirementAnalysis('idea/one', 2, 'run/one')
  await generatePrototypeSource('idea/one', 2, 'requirements/run')
  await getLatestPrototypeSource('idea/one', 2)
  await getPrototypeSourceFiles('idea/one', 2, 'prototype/one')
  await updateIdeaStatus('idea/one', 'Archived')
  await listPersistedFeedback('idea/one', 2)
  await startFeedbackAnalysis('idea/one', 2)
  await getLatestFeedbackAnalysis('idea/one', 2)
  await getFeedbackAnalysis('idea/one', 2, 'feedback-run')
  await createEvolutionProposal('idea/one', 2)
  await getEvolutionProposal('idea/one', 2)
  await approveEvolutionProposal('idea/one', 2, 'proposal/one', [1, 3])
  await createDecisionReport('idea/one', 2)
  await getLatestDecisionReport('idea/one', 2)

  assert.deepEqual(requests.map(({ path, method }) => [path, method]), [
    ['/api/v1/ideas?limit=10&offset=20&status=Draft&category=Education&q=campus+idea', 'GET'],
    ['/api/v1/ideas/idea%2Fone/versions', 'POST'],
    ['/api/v1/ideas/idea%2Fone/versions/2/publish', 'POST'],
    ['/api/v1/ideas/idea%2Fone/versions/2/requirements', 'POST'],
    ['/api/v1/ideas/idea%2Fone/versions/2/requirements', 'GET'],
    ['/api/v1/ideas/idea%2Fone/versions/2/requirements/run%2Fone', 'GET'],
    ['/api/v1/ideas/idea%2Fone/versions/2/prototypes', 'POST'],
    ['/api/v1/ideas/idea%2Fone/versions/2/prototypes', 'GET'],
    ['/api/v1/ideas/idea%2Fone/versions/2/prototypes/prototype%2Fone/source', 'GET'],
    ['/api/v1/ideas/idea%2Fone', 'PATCH'],
    ['/api/v1/ideas/idea%2Fone/versions/2/feedback', 'GET'],
    ['/api/v1/ideas/idea%2Fone/versions/2/feedback-analysis', 'POST'],
    ['/api/v1/ideas/idea%2Fone/versions/2/feedback-analysis', 'GET'],
    ['/api/v1/ideas/idea%2Fone/versions/2/feedback-analysis/feedback-run', 'GET'],
    ['/api/v1/ideas/idea%2Fone/versions/2/evolution', 'POST'],
    ['/api/v1/ideas/idea%2Fone/versions/2/evolution', 'GET'],
    ['/api/v1/ideas/idea%2Fone/versions/2/evolution/proposal%2Fone/approve', 'POST'],
    ['/api/v1/ideas/idea%2Fone/versions/2/decision-reports', 'POST'],
    ['/api/v1/ideas/idea%2Fone/versions/2/decision-reports', 'GET'],
  ])
  assert.deepEqual(JSON.parse(requests[1].body ?? '{}'), {
    title: 'Campus Compass V2',
    category: 'Education',
    problem: 'Students need a better way to prepare for placements.',
    solution: 'A guided workspace for preparation and opportunity discovery.',
    audience: 'College students',
    features: ['Matching'],
    constraints: '',
    expected_version: 1,
    change_summary: 'Add a clearer preparation path.',
  })
  assert.deepEqual(JSON.parse(requests[6].body ?? '{}'), {
    requirement_analysis_id: 'requirements/run',
  })
  assert.deepEqual(JSON.parse(requests[9].body ?? '{}'), { status: 'Archived' })
  assert.deepEqual(JSON.parse(requests[16].body ?? '{}'), {
    expected_source_version: 2,
    selected_ranks: [1, 3],
  })
})
