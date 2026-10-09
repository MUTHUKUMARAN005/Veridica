import { getAccessToken } from './auth'
import type { Idea } from './preview'

export type IdeaInput = Omit<Idea, 'id' | 'status' | 'version' | 'updated' | 'color'> & {
  features: string[]
}

export type ApiIdea = {
  id: string
  title: string
  category: string
  problem: string
  solution: string
  audience: string
  features: string[]
  constraints: string
  version: number
  status: Idea['status']
  created_at: string
  updated_at: string
}

export async function createIdea(input: IdeaInput): Promise<ApiIdea> {
  const token = getAccessToken()
  if (!token) throw new Error('Sign in before saving an idea to the API.')
  const response = await fetch('/api/v1/ideas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      title: input.title,
      category: input.category,
      problem: input.problem,
      solution: input.solution,
      audience: input.audience,
      features: input.features,
      constraints: input.constraints,
    }),
  })
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
      ? String(payload.detail)
      : 'The idea could not be saved.'
    throw new Error(detail)
  }
  return payload as ApiIdea
}

export async function listIdeas(): Promise<ApiIdea[]> {
  const token = getAccessToken()
  if (!token) throw new Error('Sign in before loading API ideas.')
  const response = await fetch('/api/v1/ideas', {
    headers: { Authorization: `Bearer ${token}` },
  })
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
      ? String(payload.detail)
      : 'The ideas could not be loaded.'
    throw new Error(detail)
  }
  return payload as ApiIdea[]
}

export function toPreviewIdea(idea: ApiIdea, assets: string[] = []): Idea {
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
    assets,
  }
}
