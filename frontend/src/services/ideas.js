import { getAccessToken } from "./auth.js";
async function request(path, init = {}) {
    const token = getAccessToken();
    if (!token)
        throw new Error('Sign in before accessing API ideas.');
    const headers = new Headers(init.headers);
    headers.set('Authorization', `Bearer ${token}`);
    if (typeof init.body === 'string' && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
    }
    const response = await fetch(path, { ...init, headers });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
        const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
            ? String(payload.detail)
            : 'The idea request failed.';
        throw new Error(detail);
    }
    return payload;
}
export function getIdea(ideaId) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}`);
}
export function createIdea(input) {
    return request('/api/v1/ideas', { method: 'POST', body: JSON.stringify(input) });
}
export function createIdeaVersion(ideaId, input) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions`, {
        method: 'POST',
        body: JSON.stringify(input),
    });
}
export function updateIdeaStatus(ideaId, status) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
    });
}
export function publishIdeaVersion(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/publish`, { method: 'POST' });
}
export function startRequirementAnalysis(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/requirements`, { method: 'POST' });
}
export function getLatestRequirementAnalysis(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/requirements`);
}
export function getRequirementAnalysis(ideaId, version, analysisId) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/requirements/${encodeURIComponent(analysisId)}`);
}
export function generatePrototypeSource(ideaId, version, requirementAnalysisId) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/prototypes`, {
        method: 'POST',
        body: JSON.stringify({ requirement_analysis_id: requirementAnalysisId }),
    });
}
export function getLatestPrototypeSource(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/prototypes`);
}
export function getPrototypeSourceFiles(ideaId, version, prototypeId) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/prototypes/${encodeURIComponent(prototypeId)}/source`);
}
export function listIdeas({ limit = 20, offset = 0, status, category, q, } = {}) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (status)
        params.set('status', status);
    if (category)
        params.set('category', category);
    if (q?.trim())
        params.set('q', q.trim());
    return request(`/api/v1/ideas?${params}`);
}
export function listPersistedFeedback(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/feedback`);
}
export function startFeedbackAnalysis(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/feedback-analysis`, { method: 'POST' });
}
export function getLatestFeedbackAnalysis(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/feedback-analysis`);
}
export function getFeedbackAnalysis(ideaId, version, analysisId) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/feedback-analysis/${encodeURIComponent(analysisId)}`);
}
export function createEvolutionProposal(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/evolution`, { method: 'POST' });
}
export function getEvolutionProposal(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/evolution`);
}
export function approveEvolutionProposal(ideaId, version, proposalId, selectedRanks) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/evolution/${encodeURIComponent(proposalId)}/approve`, {
        method: 'POST',
        body: JSON.stringify({
            expected_source_version: version,
            selected_ranks: selectedRanks,
        }),
    });
}
export function createDecisionReport(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/decision-reports`, { method: 'POST' });
}
export function getLatestDecisionReport(ideaId, version) {
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/decision-reports`);
}
export function uploadIdeaAsset(ideaId, version, file) {
    const params = new URLSearchParams({ filename: file.name });
    return request(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/assets?${params}`, {
        method: 'POST',
        headers: { 'Content-Type': file.type },
        body: file,
    });
}
export async function downloadIdeaAsset(ideaId, version, assetId, filename) {
    const token = getAccessToken();
    if (!token)
        throw new Error('Sign in before downloading an API idea asset.');
    const response = await fetch(`/api/v1/ideas/${encodeURIComponent(ideaId)}/versions/${version}/assets/${encodeURIComponent(assetId)}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) {
        const payload = await response.json().catch(() => null);
        const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
            ? String(payload.detail)
            : 'The private asset could not be downloaded.';
        throw new Error(detail);
    }
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
}
export function toPreviewIdea(idea) {
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
    };
}
