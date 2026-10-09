import { test } from 'node:test'
import assert from 'node:assert/strict'
import { addComment, addIdea, addReview, assessPriority, freshState, interestSummary, proposeEvolution, publishIdea, rankPriorities, recordSignal, reviewSummary, toggleCommentSupport } from './preview.ts'

test('metrics are derived from feedback and remain empty without evidence', () => {
  assert.deepEqual(reviewSummary([]), { count: 0, rating: null, support: null })
  assert.equal(reviewSummary(freshState().reviews).support, 2 / 3)
})

test('review submission is immutable, validated and idempotent', () => {
  const state = freshState()
  const review = { ...state.reviews[0], id: 'new-review', sample: false }
  const next = addReview(state, review)
  assert.equal(state.reviews.length, 3)
  assert.equal(next.reviews.length, 4)
  assert.equal(addReview(next, review), next)
  assert.throws(() => addReview(state, { ...review, rating: 6 }))
  assert.throws(() => addReview(state, { ...review, context: '' }))
  assert.throws(() => addReview(state, { ...review, version: 2 }))
})

test('evolution requires same-version evidence and never overwrites V1', () => {
  const state = assessPriority(freshState(), { evidenceId: 'review-1', impact: 3, effort: 'small', blocked: false }, 'owner')
  const original = structuredClone(state.ideas[0])
  const next = proposeEvolution(state, 'placement', ['review-1'])
  assert.deepEqual(next.ideas[0], original)
  assert.equal(next.evolutions[0].target, 2)
  assert.deepEqual(next.evolutions[0].evidence, ['review-1'])
  assert.throws(() => proposeEvolution(state, 'placement', []))
  assert.throws(() => proposeEvolution(next, 'placement', ['review-2']))
})

const comment = { id: 'comment-1', ideaId: 'placement', version: 1, author: 'Maya Chen', kind: 'suggestion' as const, text: 'Keep job filters visible on small screens.', context: 'Tested opportunity search on a mobile screen.', created: '2026-09-30T10:00:00Z' }

test('comments are validated, idempotent and do not invent structured ratings', () => {
  const state = addComment(freshState(), comment)
  assert.equal(state.comments.length, 1)
  assert.equal(state.reviews.length, 3)
  assert.equal(state.assignments[0].status, 'Completed')
  assert.equal(addComment(state, comment), state)
  assert.throws(() => addComment(freshState(), { ...comment, text: 'Nice' }))
  assert.throws(() => addComment(freshState(), { ...comment, ideaId: 'found' }))
  assert.throws(() => addComment(freshState(), { ...comment, version: 2 }))
})

test('likes toggle and link copies deduplicate without changing trust or evidence', () => {
  let state = recordSignal(freshState(), 'placement', 'Maya Chen', 'interest')
  state = recordSignal(state, 'placement', 'Maya Chen', 'link_copy')
  assert.equal(recordSignal(state, 'placement', 'Maya Chen', 'link_copy'), state)
  assert.deepEqual(interestSummary(state, 'placement'), { likes: 1, linkCopies: 1, discoveryScore: 3 })
  assert.equal(state.reviews.length, 3)
  assert.equal(interestSummary(recordSignal(state, 'placement', 'Maya Chen', 'interest'), 'placement').likes, 0)
})

test('prioritization requires owner estimates and favors impact with smaller effort', () => {
  let state = addComment(freshState(), comment)
  assert.equal(rankPriorities(state, 'placement').find((item) => item.id === comment.id)?.priority, 'Needs estimate')
  assert.throws(() => proposeEvolution(state, 'placement', [comment.id]))
  assert.throws(() => assessPriority(state, { evidenceId: comment.id, impact: 3, effort: 'small', blocked: false }, 'reviewer'))
  state = assessPriority(state, { evidenceId: comment.id, impact: 3, effort: 'small', blocked: false }, 'owner')
  state = assessPriority(state, { evidenceId: 'review-1', impact: 3, effort: 'large', blocked: false }, 'owner')
  assert.equal(rankPriorities(state, 'placement')[0].id, comment.id)
  const next = proposeEvolution(state, 'placement', ['review-1', comment.id])
  assert.equal(next.evolutions[0].evidence[0], comment.id)
  assert.equal(next.evolutions[0].priorities?.[0].priority, 'P1')
  assert.equal(next.ideas[0].version, 1)
  assert.throws(() => proposeEvolution(state, 'placement', [comment.id, 'unknown-evidence']))
})

test('useful votes exclude self votes, toggle, cap ranking influence, and respect blockers', () => {
  let state = addComment(freshState(), comment)
  assert.throws(() => toggleCommentSupport(state, comment.id, comment.author))
  for (const actor of ['Owner', 'Reviewer two', 'Reviewer three', 'Reviewer four']) state = toggleCommentSupport(state, comment.id, actor)
  state = assessPriority(state, { evidenceId: comment.id, impact: 3, effort: 'small', blocked: false }, 'owner')
  assert.equal(rankPriorities(state, 'placement')[0].score, 11)
  const proposal = proposeEvolution(state, 'placement', [comment.id]).evolutions[0]
  state = assessPriority(state, { evidenceId: comment.id, impact: 1, effort: 'small', blocked: true }, 'owner')
  assert.throws(() => proposeEvolution(state, 'placement', [comment.id]))
  assert.equal(proposal.priorities?.[0].impact, 3)
  state = toggleCommentSupport(state, comment.id, 'Owner')
  assert.equal(state.comments[0].supporters.length, 3)
})

test('questions and old-version evidence cannot become implementation priorities', () => {
  let state = addComment(freshState(), { ...comment, kind: 'question' })
  assert.equal(state.assignments[0].status, 'Assigned')
  state = assessPriority(state, { evidenceId: comment.id, impact: 3, effort: 'small', blocked: false }, 'admin')
  assert.equal(rankPriorities(state, 'placement').find((entry) => entry.id === comment.id)?.priority, 'Discuss')
  assert.throws(() => proposeEvolution(state, 'placement', [comment.id]))
  state = { ...state, comments: [{ ...state.comments[0], version: 2 }] }
  assert.ok(!rankPriorities(state, 'placement').some((entry) => entry.id === comment.id))
})

test('ideas start as drafts and only ready prototypes can be published', () => {
  const state = freshState()
  const next = addIdea(state, { title: 'Test idea', problem: 'A problem', solution: 'A solution', audience: 'Students', features: ['Search'], category: 'Education', constraints: '', assets: [] })
  assert.equal(next.ideas[0].version, 1)
  assert.equal(next.ideas[0].status, 'Draft')
  assert.throws(() => publishIdea(next, next.ideas[0].id))
  assert.equal(publishIdea(state, 'circular').ideas[1].status, 'Review open')
})