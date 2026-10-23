import { afterEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { login, logout } from './auth.ts'
import { createIdeaVersion } from './ideas.ts'
import {
  createAdminAssignment,
  getReviewerAssignment,
  listAdminAssignments,
  listReviewerAssignments,
  revokeAdminAssignment,
  startReviewerSession,
  submitReviewerReview,
} from './authorization.ts'

const originalFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = originalFetch
  logout()
})

test('authenticated assignment clients use server-scoped routes and send the bearer token', async () => {
  const requests: {
    path: string
    method: string
    body: string | undefined
    idempotencyKey: string | null
  }[] = []
  globalThis.fetch = async (input, init) => {
    const path = String(input)
    const method = init?.method ?? 'GET'
    if (path === '/api/v1/auth/login') {
      return new Response(JSON.stringify({
        access_token: 'test-token',
        token_type: 'bearer',
        user: { id: 'reviewer-id', email: 'reviewer@example.com', role: 'reviewer' },
      }), { status: 200 })
    }
    assert.equal(new Headers(init?.headers).get('authorization'), 'Bearer test-token')
    requests.push({
      path,
      method,
      body: init?.body?.toString(),
      idempotencyKey: new Headers(init?.headers).get('idempotency-key'),
    })
    return new Response(JSON.stringify({ ok: true }), { status: 200 })
  }
  await login('reviewer@example.com', 'test-password')

  await createIdeaVersion('idea-one', {
    title: 'New version',
    category: 'Education',
    problem: 'Students need an easier way to prepare.',
    solution: 'A clearer preparation workspace.',
    audience: 'College students',
    features: ['Planning'],
    constraints: '',
    expected_version: 1,
    change_summary: 'Clarify the initial scope.',
  })
  await listReviewerAssignments()
  await getReviewerAssignment('assignment/one')
  await startReviewerSession('assignment-one')
  const feedback = {
    session_id: '00000000-0000-4000-8000-000000000001',
    rating: 5,
    usability_score: 4,
    usefulness_score: 5,
    completeness_score: 4,
    feasibility_score: 4,
    would_use: true,
    feedback_text: 'Evidence from this assigned version.',
    strengths: 'The main workflow is clear.',
    concerns: 'Some navigation is difficult.',
    suggested_improvements: 'Make the navigation clearer.',
    usage_context: 'I reviewed the version as a student.',
  }
  await submitReviewerReview('assignment-one', feedback, 'test-idempotency-key-0001')
  await listAdminAssignments()
  await createAdminAssignment('idea-one', 2, 'reviewer@example.com')
  await revokeAdminAssignment('assignment-one')

  assert.deepEqual(requests.map(({ path, method }) => [path, method]), [
    ['/api/v1/ideas/idea-one/versions', 'POST'],
    ['/api/v1/reviewer/assignments', 'GET'],
    ['/api/v1/reviewer/assignments/assignment%2Fone', 'GET'],
    ['/api/v1/reviewer/assignments/assignment-one/sessions', 'POST'],
    ['/api/v1/reviewer/assignments/assignment-one/reviews', 'POST'],
    ['/api/v1/admin/assignments', 'GET'],
    ['/api/v1/admin/assignments', 'POST'],
    ['/api/v1/admin/assignments/assignment-one', 'DELETE'],
  ])
  assert.deepEqual(JSON.parse(requests[0].body ?? '{}'), {
    title: 'New version',
    category: 'Education',
    problem: 'Students need an easier way to prepare.',
    solution: 'A clearer preparation workspace.',
    audience: 'College students',
    features: ['Planning'],
    constraints: '',
    expected_version: 1,
    change_summary: 'Clarify the initial scope.',
  })
  assert.equal(requests[4].body, JSON.stringify(feedback))
  assert.equal(requests[4].idempotencyKey, 'test-idempotency-key-0001')
  assert.equal(
    requests[6].body,
    JSON.stringify({ idea_id: 'idea-one', version: 2, reviewer_email: 'reviewer@example.com' }),
  )
})
