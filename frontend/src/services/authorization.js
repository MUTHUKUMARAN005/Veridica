import { getAccessToken } from "./auth.js";
async function request(path, init = {}) {
    const token = getAccessToken();
    if (!token)
        throw new Error('Sign in to access authenticated assignments.');
    const response = await fetch(path, {
        ...init,
        headers: {
            ...(init.body ? { 'Content-Type': 'application/json' } : {}),
            Authorization: `Bearer ${token}`,
            ...init.headers,
        },
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
        const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
            ? String(payload.detail)
            : 'The authorization request failed.';
        throw new Error(detail);
    }
    return payload;
}
export function listReviewerAssignments() {
    return request('/api/v1/reviewer/assignments');
}
export function getReviewerAssignment(assignmentId) {
    return request(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}`);
}
export function getReviewerPrototypePreview(assignmentId) {
    return request(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/prototype`);
}
export function startReviewerSession(assignmentId) {
    return request(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/sessions`, { method: 'POST' });
}
export function submitReviewerReview(assignmentId, payload, idempotencyKey) {
    return request(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/reviews`, {
        method: 'POST',
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify(payload),
    });
}
export function listAdminAssignments() {
    return request('/api/v1/admin/assignments');
}
export function createAdminAssignment(ideaId, version, reviewerEmail) {
    return request('/api/v1/admin/assignments', {
        method: 'POST',
        body: JSON.stringify({ idea_id: ideaId, version, reviewer_email: reviewerEmail }),
    });
}
export function revokeAdminAssignment(assignmentId) {
    return request(`/api/v1/admin/assignments/${encodeURIComponent(assignmentId)}`, { method: 'DELETE' });
}
