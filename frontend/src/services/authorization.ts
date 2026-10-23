import { getAccessToken } from './auth.ts'
import type { PrototypePreviewSpec } from './ideas'

export type ReviewerAssignment = {
  id: string
  idea_id: string
  idea_title: string
  version: number
  problem: string
  solution: string
  audience: string
  features: string[]
  constraints: string
  assigned_at: string
  started_at: string | null
  completed_at: string | null
  status: 'assigned' | 'in_progress' | 'submitted' | 'revoked'
  review_submitted: boolean
  review_session: ReviewSession | null
  feedback: ApiReview | null
}

export type ReviewerPrototypePreview = {
  prototype_build_id: string
  idea_version_id: string
  source_version: number
  requirement_analysis_run_id: string
  preview_spec: PrototypePreviewSpec
}

export type AdminAssignment = {
  id: string
  idea_id: string
  idea_title: string
  version: number
  reviewer_email: string
  active: boolean
  status: 'assigned' | 'in_progress' | 'submitted' | 'revoked'
  assigned_at: string
  started_at: string | null
  completed_at: string | null
  revoked_at: string | null
  review_submitted: boolean
}

export type ReviewSession = {
  id: string
  assignment_id: string
  idea_id: string
  idea_version_id: string
  reviewer_id: string
  status: 'in_progress' | 'submitted'
  started_at: string
  completed_at: string | null
}

export type ApiReview = {
  id: string
  assignment_id: string
  idea_id: string
  idea_version_id: string
  reviewer_id: string
  review_session_id: string
  idempotency_key: string | null
  rating: number
  usability_score: number | null
  usefulness_score: number | null
  completeness_score: number | null
  feasibility_score: number | null
  would_use: boolean | null
  feedback_text: string
  strengths: string | null
  concerns: string | null
  suggested_improvements: string | null
  usage_context: string | null
  created_at: string
  analysis_status: 'pending' | 'queued' | 'received'
  analysis_error: string | null
}

export type ReviewSubmission = {
  session_id: string
  rating: number
  usability_score: number
  usefulness_score: number
  completeness_score: number
  feasibility_score: number
  would_use: boolean
  feedback_text: string
  strengths: string
  concerns: string
  suggested_improvements: string
  usage_context: string
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken()
  if (!token) throw new Error('Sign in to access authenticated assignments.')
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
  })
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
      ? String(payload.detail)
      : 'The authorization request failed.'
    throw new Error(detail)
  }
  return payload as T
}

export function listReviewerAssignments() {
  return request<ReviewerAssignment[]>('/api/v1/reviewer/assignments')
}

export function getReviewerAssignment(assignmentId: string) {
  return request<ReviewerAssignment>(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}`)
}

export function getReviewerPrototypePreview(assignmentId: string) {
  return request<ReviewerPrototypePreview | null>(
    `/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/prototype`,
  )
}

export function startReviewerSession(assignmentId: string) {
  return request<ReviewSession>(
    `/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/sessions`,
    { method: 'POST' },
  )
}

export function submitReviewerReview(
  assignmentId: string,
  payload: ReviewSubmission,
  idempotencyKey: string,
) {
  return request<ApiReview>(
    `/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/reviews`,
    {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify(payload),
    },
  )
}

export function listAdminAssignments() {
  return request<AdminAssignment[]>('/api/v1/admin/assignments')
}

export function createAdminAssignment(ideaId: string, version: number, reviewerEmail: string) {
  return request<AdminAssignment>('/api/v1/admin/assignments', {
    method: 'POST',
    body: JSON.stringify({ idea_id: ideaId, version, reviewer_email: reviewerEmail }),
  })
}

export function revokeAdminAssignment(assignmentId: string) {
  return request<AdminAssignment>(
    `/api/v1/admin/assignments/${encodeURIComponent(assignmentId)}`,
    { method: 'DELETE' },
  )
}
