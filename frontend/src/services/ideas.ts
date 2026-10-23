import { getAccessToken } from './auth.ts'
import type { Idea, IdeaStatus } from './preview'

export type IdeaInput = Pick<
  Idea,
  'title' | 'category' | 'problem' | 'solution' | 'audience' | 'features' | 'constraints'
>

export type ApiIdeaAsset = {
  id: string
  idea_version_id: string
  filename: string
  content_type: 'application/pdf' | 'image/png' | 'image/jpeg'
  size_bytes: number
  sha256: string
  created_at: string
}

export type ApiIdea = IdeaInput & {
  id: string
  owner_id: string
  version_id: string
  source_version_id: string | null
  created_by_id: string
  change_summary: string
  version: number
  status: IdeaStatus
  created_at: string
  updated_at: string
  version_created_at: string
  assets: ApiIdeaAsset[]
}

export type ApiIdeaDetail = ApiIdea & { versions: ApiIdea[] }
export type ApiIdeaPage = { items: ApiIdea[]; total: number; limit: number; offset: number }
export type ApiIdeaVersionInput = IdeaInput & {
  expected_version: number
  change_summary: string
}
export type ApiReviewCycle = {
  id: string
  idea_id: string
  idea_version_id: string
  version: number
  status: 'open' | 'closed'
  opened_by_id: string
  opened_at: string
  closed_at: string | null
}

export type RequirementFact = {
  text: string
  basis: 'explicit' | 'assumption'
  source_fields: ('title' | 'problem' | 'solution' | 'audience' | 'features' | 'constraints')[]
}

export type RequirementSpecification = {
  problem: RequirementFact[]
  target_users: RequirementFact[]
  user_journeys: {
    actor: RequirementFact
    need: RequirementFact
    steps: string[]
    outcome: RequirementFact
  }[]
  core_features: RequirementFact[]
  constraints: RequirementFact[]
  assumptions: string[]
  acceptance_criteria: RequirementFact[]
  open_questions: string[]
}

export type RequirementAnalysis = {
  id: string
  idea_id: string
  idea_version_id: string
  source_version: number
  workflow_run_id: string
  provider: 'ollama' | 'gemini'
  model_version: string
  prompt_version: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  validation_status: 'pending' | 'valid' | 'invalid' | 'not_run'
  result: RequirementSpecification | null
  error_message: string | null
  attempt_count: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  updated_at: string
}

export type PrototypeBuild = {
  id: string
  idea_id: string
  idea_version_id: string
  source_version: number
  requirement_analysis_run_id: string
  workflow_run_id: string
  template_id: string | null
  template_version: string | null
  status: 'source_generated' | 'validation_failed' | 'unsupported_category' | 'generation_failed' | 'source_missing'
  validation_status: 'passed' | 'failed' | 'not_run'
  build_status: 'blocked_isolation'
  publish_status: 'unpublished'
  plan: {
    template_id: 'education-placement-preparation'
    template_version: string
    framework: 'react-typescript-vite'
    category: 'education-placement'
    screens: { key: 'overview' | 'features' | 'journeys' | 'questions'; title: string; components: { name: string; purpose: string }[] }[]
    limitations: string[]
  } | null
  manifest: {
    template_id: 'education-placement-preparation'
    template_version: string
    framework: 'react-typescript-vite'
    dependencies: Record<string, string>
    scripts: Record<string, string>
    files: string[]
    source_only: true
    build_boundary: 'unavailable'
  } | null
  validation_results: {
    scope: string
    checks: { name: string; status: 'passed' | 'failed' | 'not_run' }[]
    source_file_count?: number
    source_bytes?: number
    build_boundary_available: false
    built_artifact_available: false
  }
  source_files: { path: string; sha256: string; size_bytes: number }[]
  artifact_metadata: {
    artifact_type: 'generated_source'
    file_count: number
    total_size_bytes: number
    source_sha256: string
    built_artifact_available: false
  } | null
  preview_url: null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export type PrototypeSource = {
  prototype_build_id: string
  files: Record<string, string>
}

export type PersistedReview = {
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

export type FeedbackQuality = {
  feedback_id: string
  relevance: number
  constructiveness: number
  originality: number
  internal_consistency: number
  spam_risk: number
  authenticity_indicator: number
  self_reported_confidence: number
  uncertainty: string
  explanations: Record<string, string>
}

export type FeedbackAnalysisOutput = {
  source_feedback_ids: string[]
  quality: FeedbackQuality[]
  deterministic_signals: {
    feedback_id: string
    text_characters: number
    structured_ratings_complete: boolean
    exact_duplicate_of: string | null
  }[]
  themes: {
    label: string
    kind: 'feature_request' | 'complaint' | 'positive' | 'other'
    summary: string
    feedback_ids: string[]
  }[]
  contradictions: { summary: string; feedback_ids: string[] }[]
  duplicate_pairs: {
    feedback_ids: [string, string]
    cosine_similarity: number
    method: 'pgvector_cosine' | 'deterministic_test_cosine'
  }[]
  trust: {
    feedback_id: string
    score: number | null
    factor_json: Record<string, number | null>
    factor_weights: Record<string, number>
    formula_version: string
    evidence_coverage: number
    missing_factors: string[]
    interpretation: string
  }[]
  consensus: {
    sample_size: number
    evidence_coverage: number
    raw_support_count: number
    raw_support: number | null
    normalized_weight_denominator: number
    raw_feedback_weights: Record<string, number>
    normalized_feedback_weights: Record<string, number>
    weighted_support: number | null
    confidence_indicator: number | null
    confidence_method: string
    uncertainty: string
    evidence_ids: string[]
  }
  priorities: {
    rank: number
    priority: 'P1' | 'P2' | 'P3'
    title: string
    rationale: string
    feedback_ids: string[]
    theme_labels: string[]
    evidence_count: number
    weighted_support: number
    impact: 'high' | 'medium' | 'low' | 'unknown'
    impact_rationale: string
    feasibility: 'high' | 'medium' | 'low' | 'unknown'
    feasibility_rationale: string
    assumptions: string[]
    missing_inputs: string[]
  }[]
}

export type FeedbackAnalysisRun = {
  id: string
  idea_id: string
  idea_version_id: string
  source_version: number
  workflow_run_id: string
  input_digest: string
  source_feedback_ids: string[]
  provider: string
  model_version: string
  embedding_model_version: string
  prompt_version: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  validation_status: 'pending' | 'valid' | 'invalid' | 'not_run'
  result: FeedbackAnalysisOutput | null
  error_message: string | null
  attempt_count: number
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export type EvolutionSuggestion = {
  rank: number
  priority: 'P1' | 'P2' | 'P3'
  title: string
  rationale: string
  source_feedback_ids: string[]
  expected_benefit: {
    interpretation: string
    qualitative_impact: 'high' | 'medium' | 'low' | 'unknown'
    weighted_support: number
  }
  assumptions: string[]
  risks: { feedback_id: string; concern: string }[]
  validation_criteria: string[]
  validation_note: string
  feasibility: 'high' | 'medium' | 'low' | 'unknown'
  feasibility_rationale: string
  missing_inputs: string[]
  builder_supported: boolean
}

export type EvolutionProposal = {
  id: string
  idea_id: string
  idea_version_id: string
  source_version: number
  requirement_analysis_run_id: string
  feedback_analysis_run_id: string
  source_feedback_ids: string[]
  suggestions: EvolutionSuggestion[]
  status: 'proposed' | 'approved' | 'rejected'
  target_version_id: string | null
  prototype_build_id: string | null
  provider: string
  model_version: string
  prompt_version: string
  validation_results: Record<string, unknown>
  created_at: string
  approved_at: string | null
}

export type DecisionReport = {
  id: string
  idea_id: string
  idea_version_id: string
  source_version: number
  requirement_analysis_run_id: string | null
  feedback_analysis_run_id: string | null
  evolution_proposal_id: string | null
  source_feedback_ids: string[]
  report_version: string
  report: Record<string, unknown>
  created_at: string
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken()
  if (!token) throw new Error('Sign in before accessing API ideas.')
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${token}`)
  if (typeof init.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(path, { ...init, headers })
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
      ? String(payload.detail)
      : 'The idea request failed.'
    throw new Error(detail)
  }
  return payload as T
}

export function getIdea(ideaId: string): Promise<ApiIdeaDetail> {
  return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}`)
}

export function createIdea(input: IdeaInput): Promise<ApiIdea> {
  return request('/api/v1/ideas', { method: 'POST', body: JSON.stringify(input) })
}

export function createIdeaVersion(
  ideaId: string,
  input: ApiIdeaVersionInput,
): Promise<ApiIdea> {
  return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function updateIdeaStatus(
  ideaId: string,
  status: 'Draft' | 'Archived',
): Promise<ApiIdea> {
  return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

export function publishIdeaVersion(ideaId: string, version: number): Promise<ApiReviewCycle> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/publish`,
    { method: 'POST' },
  )
}

export function startRequirementAnalysis(
  ideaId: string,
  version: number,
): Promise<RequirementAnalysis> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/requirements`,
    { method: 'POST' },
  )
}

export function getLatestRequirementAnalysis(
  ideaId: string,
  version: number,
): Promise<RequirementAnalysis | null> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/requirements`,
  )
}

export function getRequirementAnalysis(
  ideaId: string,
  version: number,
  analysisId: string,
): Promise<RequirementAnalysis> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/requirements/${encodeURIComponent(analysisId)}`,
  )
}

export function generatePrototypeSource(
  ideaId: string,
  version: number,
  requirementAnalysisId: string,
): Promise<PrototypeBuild> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/prototypes`,
    {
      method: 'POST',
      body: JSON.stringify({ requirement_analysis_id: requirementAnalysisId }),
    },
  )
}

export function getLatestPrototypeSource(
  ideaId: string,
  version: number,
): Promise<PrototypeBuild | null> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/prototypes`,
  )
}

export function getPrototypeSourceFiles(
  ideaId: string,
  version: number,
  prototypeId: string,
): Promise<PrototypeSource> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/prototypes/${encodeURIComponent(prototypeId)}/source`,
  )
}

export function listIdeas({
  limit = 20,
  offset = 0,
  status,
  category,
  q,
}: {
  limit?: number
  offset?: number
  status?: string
  category?: string
  q?: string
} = {}): Promise<ApiIdeaPage> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (status) params.set('status', status)
  if (category) params.set('category', category)
  if (q?.trim()) params.set('q', q.trim())
  return request(`/api/v1/ideas?${params}`)
}

export function listPersistedFeedback(
  ideaId: string,
  version: number,
): Promise<PersistedReview[]> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/feedback`,
  )
}

export function startFeedbackAnalysis(
  ideaId: string,
  version: number,
): Promise<FeedbackAnalysisRun> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/feedback-analysis`,
    { method: 'POST' },
  )
}

export function getLatestFeedbackAnalysis(
  ideaId: string,
  version: number,
): Promise<FeedbackAnalysisRun | null> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/feedback-analysis`,
  )
}

export function getFeedbackAnalysis(
  ideaId: string,
  version: number,
  analysisId: string,
): Promise<FeedbackAnalysisRun> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/feedback-analysis/${encodeURIComponent(analysisId)}`,
  )
}

export function createEvolutionProposal(
  ideaId: string,
  version: number,
): Promise<EvolutionProposal> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/evolution`,
    { method: 'POST' },
  )
}

export function getEvolutionProposal(
  ideaId: string,
  version: number,
): Promise<EvolutionProposal | null> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/evolution`,
  )
}

export function approveEvolutionProposal(
  ideaId: string,
  version: number,
  proposalId: string,
  selectedRanks: number[],
): Promise<EvolutionProposal> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/evolution/${encodeURIComponent(proposalId)}/approve`,
    {
      method: 'POST',
      body: JSON.stringify({
        expected_source_version: version,
        selected_ranks: selectedRanks,
      }),
    },
  )
}

export function createDecisionReport(
  ideaId: string,
  version: number,
): Promise<DecisionReport> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/decision-reports`,
    { method: 'POST' },
  )
}

export function getLatestDecisionReport(
  ideaId: string,
  version: number,
): Promise<DecisionReport | null> {
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/decision-reports`,
  )
}

export function uploadIdeaAsset(ideaId: string, version: number, file: File): Promise<ApiIdea> {
  const params = new URLSearchParams({ filename: file.name })
  return request(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/assets?${params}`,
    {
      method: 'POST',
      headers: { 'Content-Type': file.type },
      body: file,
    },
  )
}

export async function downloadIdeaAsset(
  ideaId: string,
  version: number,
  assetId: string,
  filename: string,
): Promise<void> {
  const token = getAccessToken()
  if (!token) throw new Error('Sign in before downloading an API idea asset.')
  const response = await fetch(
    `/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/assets/${encodeURIComponent(assetId)}`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null)
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
      ? String(payload.detail)
      : 'The private asset could not be downloaded.'
    throw new Error(detail)
  }
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function toPreviewIdea(idea: ApiIdea): Idea {
  return {
    id: idea.id,
    title: idea.title,
    category: idea.category,
    problem: idea.problem,
    solution: idea.solution,
    audience: idea.audience,
    features: idea.features,
    constraints: idea.constraints,
    status: idea.status,
    version: idea.version,
    color: 'mint',
    updated: idea.updated_at,
    assets: idea.assets.map((asset) => asset.filename),
  }
}
