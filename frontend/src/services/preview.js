export const reviewers = ['Maya Chen', 'Arjun Patel', 'Sofia Rivera'];
export const initialState = {
    ideas: [
        { id: 'placement', title: 'Campus Compass', category: 'Education', problem: 'Students struggle to find relevant placement opportunities and prepare for company-specific recruitment.', solution: 'A placement workspace that brings opportunities, resume preparation and a personal learning roadmap together.', audience: 'College students and placement teams', features: ['Job matching', 'Resume checklist', 'Preparation roadmap', 'Progress dashboard'], constraints: 'Prototype integrations only; no external recruitment data.', status: 'Review open', version: 1, color: 'mint', updated: '2026-09-28', assets: [] },
        { id: 'circular', title: 'Circular City', category: 'Sustainability', problem: 'Residents have no consistent way to report missed waste collections or track requests.', solution: 'A neighborhood reporting and collection scheduling workspace.', audience: 'Residents and municipal teams', features: ['Report an issue', 'Collection schedule', 'Request tracking'], constraints: 'No live municipal integrations.', status: 'Ready for review', version: 1, color: 'blue', updated: '2026-09-27', assets: [] },
        { id: 'found', title: 'Found Together', category: 'Community', problem: 'Lost items are scattered across disconnected campus groups.', solution: 'A searchable campus lost-and-found with structured reports.', audience: 'Students and campus staff', features: ['Item reporting', 'Search and filter', 'Claim requests'], constraints: 'Identity verification is outside the preview.', status: 'Draft', version: 1, color: 'coral', updated: '2026-09-26', assets: [] },
    ],
    reviews: [
        { id: 'review-1', ideaId: 'placement', version: 1, reviewer: 'Maya Chen', rating: 4, usability: 4, usefulness: 5, feasibility: 4, completeness: 3, wouldUse: true, strengths: 'The opportunity list makes the next step feel clear.', concerns: 'The preparation roadmap needs an explicit progress indicator.', improvements: 'Add completion controls to every roadmap step.', context: 'Tested the job list and roadmap on a laptop.', created: '2026-09-28T10:00:00Z', sample: true },
        { id: 'review-2', ideaId: 'placement', version: 1, reviewer: 'Arjun Patel', rating: 3, usability: 3, usefulness: 4, feasibility: 4, completeness: 3, wouldUse: true, strengths: 'Saved opportunities are useful for comparing roles.', concerns: 'Filters could be easier to discover on a smaller screen.', improvements: 'Keep opportunity filters visible on mobile.', context: 'Compared roles and saved an opportunity on mobile.', created: '2026-09-28T12:00:00Z', sample: true },
        { id: 'review-3', ideaId: 'placement', version: 1, reviewer: 'Sofia Rivera', rating: 4, usability: 4, usefulness: 4, feasibility: 3, completeness: 4, wouldUse: false, strengths: 'The resume checklist is easy to scan.', concerns: 'There is no explanation of how matching would work.', improvements: 'Explain the criteria behind each opportunity match.', context: 'Completed the resume checklist and inspected job details.', created: '2026-09-28T14:00:00Z', sample: true },
    ],
    evolutions: [],
    comments: [],
    signals: [],
    assessments: [],
    assignments: [{ id: 'assignment-1', ideaId: 'placement', reviewer: 'Maya Chen', status: 'Assigned' }],
    audit: [{ id: 'event-1', action: 'Sample review cycle opened', entity: 'Campus Compass', created: '2026-09-28T09:00:00Z' }],
};
export function freshState() { return structuredClone(initialState); }
export function ideaReviews(state, ideaId) { return state.reviews.filter((review) => review.ideaId === ideaId); }
export function reviewSummary(reviews) {
    return {
        count: reviews.length,
        rating: reviews.length ? reviews.reduce((total, review) => total + review.rating, 0) / reviews.length : null,
        support: reviews.length ? reviews.filter((review) => review.wouldUse).length / reviews.length : null,
    };
}
export function addReview(state, review) {
    if (!state.ideas.some((idea) => idea.id === review.ideaId && idea.status === 'Review open' && idea.version === review.version))
        throw new Error('This review cycle is not open.');
    if (state.reviews.some((existing) => existing.id === review.id))
        return state;
    if ([review.rating, review.usability, review.usefulness, review.feasibility, review.completeness].some((score) => !Number.isInteger(score) || score < 1 || score > 5))
        throw new Error('Ratings must be between 1 and 5.');
    if ([review.strengths, review.concerns, review.improvements, review.context].some((value) => value.trim().length < 10))
        throw new Error('Add at least 10 characters of evidence in each feedback field.');
    return { ...state, reviews: [...state.reviews, review], assignments: state.assignments.map((assignment) => assignment.ideaId === review.ideaId && assignment.reviewer === review.reviewer ? { ...assignment, status: 'Completed' } : assignment) };
}
export function proposeEvolution(state, ideaId, evidence) {
    const idea = state.ideas.find((candidate) => candidate.id === ideaId);
    const priorities = rankPriorities(state, ideaId).filter((item) => evidence.includes(item.id));
    if (!idea || !priorities.length || new Set(evidence).size !== priorities.length)
        throw new Error('Select current-version feedback evidence first.');
    if (priorities.some((item) => item.score === null))
        throw new Error('Assess impact and effort, and resolve blocked items or questions before proposing changes.');
    if (state.evolutions.some((evolution) => evolution.ideaId === ideaId && evolution.source === idea.version))
        throw new Error('A proposal already exists for this version.');
    const created = new Date().toISOString();
    return { ...state, evolutions: [...state.evolutions, { id: crypto.randomUUID(), ideaId, source: idea.version, target: idea.version + 1, priorityFormulaVersion: 'preview-impact-effort-v1', changes: priorities.map((item) => item.text), evidence: priorities.map((item) => item.id), priorities: priorities.map((item) => ({ evidenceId: item.id, priority: item.priority, impact: item.impact, effort: item.effort, score: item.score, rationale: item.rationale })), created }], audit: [{ id: crypto.randomUUID(), action: 'Priority-based preview proposal created', entity: idea.title, created }, ...state.audit] };
}
export function previewActor(role) { return role === 'reviewer' ? 'Maya Chen' : role === 'admin' ? 'Preview admin' : 'Idea owner'; }
export function addComment(state, input) {
    const idea = state.ideas.find((entry) => entry.id === input.ideaId && entry.version === input.version);
    if (!idea || idea.status !== 'Review open')
        throw new Error('Comments open when the review cycle is published.');
    if (state.comments.some((entry) => entry.id === input.id))
        return state;
    if (!['suggestion', 'problem', 'question'].includes(input.kind))
        throw new Error('Choose a valid comment type.');
    if (input.text.trim().length < 10 || input.text.length > 2000 || input.context.trim().length < 10 || input.context.length > 1000 || !input.author.trim())
        throw new Error('Add a comment and testing context of at least 10 characters, within the field limits.');
    return { ...state, comments: [...state.comments, { ...input, text: input.text.trim(), context: input.context.trim(), supporters: [] }], assignments: state.assignments.map((assignment) => assignment.ideaId === idea.id && assignment.reviewer === input.author && input.kind !== 'question' ? { ...assignment, status: 'Completed' } : assignment), audit: [{ id: crypto.randomUUID(), action: 'Preview comment submitted', entity: idea.title, created: input.created }, ...state.audit] };
}
export function toggleCommentSupport(state, commentId, actor) {
    const comment = state.comments.find((entry) => entry.id === commentId);
    if (!comment || !actor.trim() || comment.author === actor)
        throw new Error('Useful votes must come from another participant.');
    return { ...state, comments: state.comments.map((entry) => entry.id === commentId ? { ...entry, supporters: entry.supporters.includes(actor) ? entry.supporters.filter((person) => person !== actor) : [...entry.supporters, actor] } : entry) };
}
export function recordSignal(state, ideaId, actor, kind) {
    const idea = state.ideas.find((entry) => entry.id === ideaId);
    if (!idea || !actor.trim() || !['interest', 'link_copy'].includes(kind))
        throw new Error('Invalid interest signal.');
    const exists = state.signals.some((entry) => entry.ideaId === ideaId && entry.version === idea.version && entry.actor === actor && entry.kind === kind);
    if (exists && kind === 'link_copy')
        return state;
    return { ...state, signals: exists ? state.signals.filter((entry) => !(entry.ideaId === ideaId && entry.version === idea.version && entry.actor === actor && entry.kind === kind)) : [...state.signals, { ideaId, version: idea.version, actor, kind }] };
}
export function interestSummary(state, ideaId) {
    const version = state.ideas.find((idea) => idea.id === ideaId)?.version;
    const signals = state.signals.filter((entry) => entry.ideaId === ideaId && entry.version === version);
    const likes = new Set(signals.filter((entry) => entry.kind === 'interest').map((entry) => entry.actor)).size;
    const linkCopies = new Set(signals.filter((entry) => entry.kind === 'link_copy').map((entry) => entry.actor)).size;
    return { likes, linkCopies, discoveryScore: likes * 2 + Math.min(linkCopies, 3) };
}
export function assessPriority(state, assessment, role) {
    if (role === 'reviewer')
        throw new Error('Only an owner or admin can assess implementation effort.');
    if (![1, 2, 3].includes(assessment.impact) || !['unknown', 'small', 'medium', 'large'].includes(assessment.effort) || typeof assessment.blocked !== 'boolean')
        throw new Error('Invalid priority assessment.');
    if (!state.comments.some((entry) => entry.id === assessment.evidenceId) && !state.reviews.some((entry) => entry.id === assessment.evidenceId))
        throw new Error('Feedback evidence not found.');
    return { ...state, assessments: [...state.assessments.filter((entry) => entry.evidenceId !== assessment.evidenceId), assessment], audit: [{ id: crypto.randomUUID(), action: `Preview priority assessed by ${role}`, entity: assessment.evidenceId, created: new Date().toISOString() }, ...state.audit] };
}
export function rankPriorities(state, ideaId) {
    const idea = state.ideas.find((entry) => entry.id === ideaId);
    if (!idea)
        return [];
    const evidence = [
        ...state.reviews.filter((review) => review.ideaId === ideaId && review.version === idea.version).map((review) => ({ id: review.id, text: review.improvements, author: review.reviewer, context: review.context, source: 'review', supports: 0, question: false })),
        ...state.comments.filter((comment) => comment.ideaId === ideaId && comment.version === idea.version).map((comment) => ({ id: comment.id, text: comment.text, author: comment.author, context: comment.context, source: 'comment', supports: new Set(comment.supporters.filter((actor) => actor !== comment.author)).size, question: comment.kind === 'question' })),
    ];
    return evidence.map((entry) => {
        const assessment = state.assessments.find((item) => item.evidenceId === entry.id);
        const impact = assessment?.impact ?? 2;
        const effort = assessment?.effort ?? 'unknown';
        const score = effort === 'unknown' || assessment?.blocked || entry.question ? null : impact * 3 + Math.min(entry.supports, 3) - { small: 1, medium: 3, large: 5 }[effort];
        const priority = entry.question ? 'Discuss' : assessment?.blocked ? 'Blocked' : score === null ? 'Needs estimate' : score >= 7 ? 'P1' : score >= 4 ? 'P2' : 'P3';
        return { ...entry, ideaId, version: idea.version, impact, effort, score, priority, rationale: score === null ? 'An actionable change, owner estimate and no unresolved blocker are required.' : `Impact ${impact} x 3 + useful votes ${Math.min(entry.supports, 3)} (capped) - effort ${{ small: 1, medium: 3, large: 5 }[effort]}. Owner estimates, not AI feasibility or trust.` };
    }).sort((left, right) => (right.score ?? -Infinity) - (left.score ?? -Infinity) || left.id.localeCompare(right.id));
}
export function downloadFile(filename, content, type = 'text/plain') {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}
export function addIdea(state, input) {
    if (!input.title.trim() || !input.problem.trim() || !input.solution.trim() || !input.audience.trim() || !input.features.length)
        throw new Error('Complete all required idea fields.');
    const idea = { ...input, id: crypto.randomUUID(), title: input.title.trim(), version: 1, status: 'Draft', color: 'mint', updated: new Date().toISOString() };
    return { ...state, ideas: [idea, ...state.ideas], audit: [{ id: crypto.randomUUID(), action: 'Preview idea created', entity: idea.title, created: idea.updated }, ...state.audit] };
}
export function publishIdea(state, ideaId) {
    const idea = state.ideas.find((candidate) => candidate.id === ideaId);
    if (!idea || idea.status !== 'Ready for review')
        throw new Error('A validated prototype is required before publishing.');
    return { ...state, ideas: state.ideas.map((candidate) => candidate.id === ideaId ? { ...candidate, status: 'Review open' } : candidate), audit: [{ id: crypto.randomUUID(), action: 'Preview review cycle opened', entity: idea.title, created: new Date().toISOString() }, ...state.audit] };
}
