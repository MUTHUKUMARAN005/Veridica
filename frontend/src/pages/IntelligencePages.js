import { useEffect, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router';
import { Bar, Doughnut } from 'react-chartjs-2';
import { ArcElement, BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js';
import { ArrowRight, ArrowUpRight, Check, Download, FileCheck2, FileText, GitBranch, Info, LockKeyhole, MessageSquare, Printer, Search, ShieldCheck, Sparkles } from 'lucide-react';
import { downloadFile, ideaReviews, proposeEvolution, rankPriorities, reviewSummary } from '@/services/preview';
import { useWorkspace } from '@/services/workspace';
import { Badge, dateLabel, Empty, PageHeading, SectionHeading } from '@/components/ui';
import { IdeaDiscussion } from '@/components/IdeaDiscussion';
import { PriorityBoard, PrioritySnapshot } from '@/components/PriorityBoard';
import { getAccessToken } from '@/services/auth';
import { approveEvolutionProposal, createDecisionReport, createEvolutionProposal, getFeedbackAnalysis, getEvolutionProposal, getIdea, getLatestDecisionReport, getLatestFeedbackAnalysis, listIdeas, listPersistedFeedback, startFeedbackAnalysis, } from '@/services/ideas';
ChartJS.register(ArcElement, BarElement, CategoryScale, Legend, LinearScale, Tooltip);
ChartJS.defaults.font.family = 'Aptos, Segoe UI, sans-serif';
ChartJS.defaults.color = '#90a294';
ChartJS.defaults.font.size = 10;
function useEvidence() {
    const workspace = useWorkspace();
    const [params, setParams] = useSearchParams();
    const idea = workspace.state.ideas.find((candidate) => candidate.id === params.get('idea')) ?? workspace.state.ideas[0];
    const reviews = idea ? ideaReviews(workspace.state, idea.id) : [];
    const selector = <select className="idea-selector" aria-label="Select idea" value={idea?.id ?? ''} onChange={(event) => setParams({ idea: event.target.value })}>{workspace.state.ideas.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.title}</option>)}</select>;
    return { ...workspace, idea, reviews, selector, summary: reviewSummary(reviews) };
}
function EvidenceNote() { return <p className="evidence-note"><Info size={13}/>Values are calculated from sample and browser-local feedback, not a production validation result.</p>; }
function AuthenticatedFeedbackAnalysis({ section }) {
    const [ideas, setIdeas] = useState([]);
    const [selectedIdeaId, setSelectedIdeaId] = useState('');
    const [selectedVersion, setSelectedVersion] = useState(0);
    const [versions, setVersions] = useState([]);
    const [reviews, setReviews] = useState([]);
    const [run, setRun] = useState(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');
    useEffect(() => {
        let active = true;
        listIdeas()
            .then(async (page) => {
            if (!active)
                return;
            setIdeas(page.items.map((idea) => ({ id: idea.id, title: idea.title, version: idea.version })));
            if (!page.items.length) {
                setLoading(false);
                return;
            }
            const selected = page.items[0];
            setSelectedIdeaId(selected.id);
            const detail = await getIdea(selected.id);
            if (!active)
                return;
            const ideaVersions = detail.versions.map((version) => ({ version: version.version, title: version.title }));
            setVersions(ideaVersions);
            setSelectedVersion(detail.version);
        })
            .catch((reason) => {
            if (active)
                setError(reason instanceof Error ? reason.message : 'Ideas could not be loaded.');
        })
            .finally(() => { if (active)
            setLoading(false); });
        return () => { active = false; };
    }, []);
    useEffect(() => {
        if (!selectedIdeaId)
            return;
        let active = true;
        setLoading(true);
        setRun(null);
        setReviews([]);
        getIdea(selectedIdeaId)
            .then((detail) => {
            if (!active)
                return;
            setVersions(detail.versions.map((version) => ({ version: version.version, title: version.title })));
            setSelectedVersion((current) => current || detail.version);
        })
            .catch((reason) => {
            if (active)
                setError(reason instanceof Error ? reason.message : 'Idea versions could not be loaded.');
        })
            .finally(() => { if (active)
            setLoading(false); });
        return () => { active = false; };
    }, [selectedIdeaId]);
    useEffect(() => {
        if (!selectedIdeaId || !selectedVersion)
            return;
        let active = true;
        setLoading(true);
        Promise.all([
            listPersistedFeedback(selectedIdeaId, selectedVersion),
            getLatestFeedbackAnalysis(selectedIdeaId, selectedVersion),
        ])
            .then(([persisted, latest]) => {
            if (!active)
                return;
            setReviews(persisted);
            setRun(latest);
            setError('');
        })
            .catch((reason) => {
            if (active)
                setError(reason instanceof Error ? reason.message : 'Persisted feedback could not be loaded.');
        })
            .finally(() => { if (active)
            setLoading(false); });
        return () => { active = false; };
    }, [selectedIdeaId, selectedVersion]);
    useEffect(() => {
        if (!run || !['queued', 'running'].includes(run.status))
            return;
        let active = true;
        const timer = window.setInterval(() => {
            getFeedbackAnalysis(run.idea_id, run.source_version, run.id)
                .then((latest) => { if (active)
                setRun(latest); })
                .catch((reason) => {
                if (active)
                    setError(reason instanceof Error ? reason.message : 'Analysis status could not be refreshed.');
            });
        }, 1500);
        return () => { active = false; window.clearInterval(timer); };
    }, [run]);
    const selectedIdea = ideas.find((idea) => idea.id === selectedIdeaId);
    const result = run?.status === 'completed' ? run.result : null;
    const submitAnalysis = async () => {
        if (!selectedIdeaId || !selectedVersion)
            return;
        setSubmitting(true);
        setError('');
        try {
            setRun(await startFeedbackAnalysis(selectedIdeaId, selectedVersion));
        }
        catch (reason) {
            setError(reason instanceof Error ? reason.message : 'Feedback analysis could not be started.');
        }
        finally {
            setSubmitting(false);
        }
    };
    const selector = <div className="api-analysis-selectors">
    <select aria-label="Select idea" value={selectedIdeaId} onChange={(event) => {
            setSelectedIdeaId(event.target.value);
            setSelectedVersion(0);
        }}>
      {ideas.map((idea) => <option value={idea.id} key={idea.id}>{idea.title}</option>)}
    </select>
    <select aria-label="Select version" value={selectedVersion || ''} onChange={(event) => setSelectedVersion(Number(event.target.value))}>
      {versions.map((version) => <option value={version.version} key={version.version}>V{version.version} · {version.title}</option>)}
    </select>
  </div>;
    const pageCopy = {
        feedback: { eyebrow: 'PERSISTED REVIEW EVIDENCE', title: 'Feedback from this version.', description: 'Only submitted PostgreSQL reviews are shown in authenticated mode.' },
        analytics: { eyebrow: 'EVIDENCE AT A GLANCE', title: 'What persisted feedback supports.', description: 'Analysis is version-scoped and traces each result to submitted feedback.' },
        trust: { eyebrow: 'TRUST & QUALITY', title: 'Signals, not verdicts.', description: 'Model judgments are uncertain indicators; no score proves a person or comment is fake.' },
        consensus: { eyebrow: 'COLLECTIVE PERSPECTIVE', title: 'Agreement with evidence attached.', description: 'Raw responses and deterministic trust-weighted consensus remain separate.' },
    };
    const copy = pageCopy[section];
    return <>
    <PageHeading eyebrow={copy.eyebrow} title={copy.title} actions={selector}>{copy.description}</PageHeading>
    {error && <p role="alert" className="error">{error}</p>}
    {loading && <p role="status" className="empty">Loading persisted feedback evidence…</p>}
    {!loading && !ideas.length && <Empty title="No authenticated ideas"><p>Create a persisted idea before analyzing its reviews.</p></Empty>}
    {!loading && selectedIdea && <section className="api-analysis-panel">
      <div className="api-analysis-toolbar">
        <div><Badge>Idea {selectedIdea.id.slice(0, 8)} · V{selectedVersion}</Badge><p>{reviews.length} persisted review{reviews.length === 1 ? '' : 's'} in this version snapshot.</p></div>
        <button className="button primary" disabled={submitting || reviews.length === 0} onClick={submitAnalysis}>
          {submitting ? 'Starting…' : run?.status === 'failed' ? 'Retry analysis' : run?.status === 'completed' ? 'Refresh analysis' : 'Analyze persisted feedback'}
        </button>
      </div>
      {reviews.length === 0 && <p className="muted">No submitted feedback exists for this exact version. No analysis or consensus is available.</p>}
      {run && <div className="api-analysis-status" role="status">
        <Badge tone={run.status === 'completed' ? 'green' : run.status === 'failed' ? 'coral' : 'neutral'}>{run.status}</Badge>
        <span>Workflow {run.workflow_run_id} · {run.provider}/{run.model_version} · embedding {run.embedding_model_version} · prompt {run.prompt_version}</span>
        {run.error_message && <p role="alert" className="error">{run.error_message}</p>}
      </div>}

      {section === 'feedback' && <div className="feedback-detail-list">{reviews.map((review) => {
                    const quality = result?.quality.find((item) => item.feedback_id === review.id);
                    return <article className="feedback-detail" key={review.id}>
          <header><div><strong>Persisted review</strong><small>V{selectedVersion} · {new Date(review.created_at).toLocaleString()}</small></div><Badge>Evidence {review.id.slice(0, 8)}</Badge><span className="review-score">{review.rating}<small>/5</small></span></header>
          <p>{review.feedback_text}</p>
          <div className="feedback-columns"><section><span className="eyebrow">STRENGTHS</span><p>{review.strengths}</p></section><section><span className="eyebrow">CONCERNS</span><p>{review.concerns}</p></section></div>
          <div className="improvement"><Sparkles size={16}/><div><strong>Suggested improvement</strong><p>{review.suggested_improvements}</p></div></div>
          {quality && <p className="muted">Quality indicators — relevance {quality.relevance.toFixed(2)}, constructiveness {quality.constructiveness.toFixed(2)}, originality {quality.originality.toFixed(2)}, spam risk {quality.spam_risk.toFixed(2)}. {quality.uncertainty}</p>}
          <small className="evidence-id">Source feedback ID: {review.id}</small>
        </article>;
                })}</div>}

      {section === 'analytics' && result && <div className="api-analysis-results">
        <div className="metrics-grid analytics-metrics">
          <Metric label="Evidence analyzed" value={result.consensus.sample_size} detail={`Source IDs: ${result.source_feedback_ids.length}`}/>
          <Metric label="Raw support" value={percent(result.consensus.raw_support)} detail={`${result.consensus.raw_support_count} positive responses`}/>
          <Metric label="Trust-weighted support" value={percent(result.consensus.weighted_support)} detail={`Weight denominator ${result.consensus.normalized_weight_denominator.toFixed(4)}`}/>
          <Metric label="Evidence coverage" value={percent(result.consensus.evidence_coverage)} detail="Required source feedback represented"/>
        </div>
        <SectionHeading title="Evidence-linked themes"/>
        {result.themes.length ? <ul className="analysis-evidence-list">{result.themes.map((theme, index) => <li key={`${theme.label}-${index}`}><Badge>{theme.kind.replace('_', ' ')}</Badge><strong>{theme.label}</strong><p>{theme.summary}</p><small>Source feedback: {theme.feedback_ids.join(', ')}</small></li>)}</ul> : <Empty title="No themes extracted"><p>The validated model output found no recurring theme in this evidence snapshot.</p></Empty>}
        <SectionHeading title="Prioritized improvement signals"/>
        {result.priorities.length ? <ol className="analysis-evidence-list">{result.priorities.map((priority) => <li key={`${priority.rank}-${priority.title}`}><Badge>{priority.priority}</Badge><strong>{priority.title}</strong><p>{priority.rationale}</p><small>{priority.evidence_count} source reviews · normalized weighted support {priority.weighted_support.toFixed(4)} · impact {priority.impact}: {priority.impact_rationale} · feasibility {priority.feasibility}: {priority.feasibility_rationale} · missing: {priority.missing_inputs.join(', ') || 'none reported'}</small><small>Evidence IDs: {priority.feedback_ids.join(', ')}{priority.assumptions.length ? ` · Assumptions: ${priority.assumptions.join('; ')}` : ''}</small></li>)}</ol> : <p className="muted">No explicit feature requests were found to prioritize.</p>}
        {!!result.contradictions.length && <><SectionHeading title="Contradictions to review"/><ul className="analysis-evidence-list">{result.contradictions.map((item, index) => <li key={index}><p>{item.summary}</p><small>Evidence: {item.feedback_ids.join(', ')}</small></li>)}</ul></>}
        {!!result.duplicate_pairs.length && <><SectionHeading title="Likely similar feedback"/><ul className="analysis-evidence-list">{result.duplicate_pairs.map((item) => <li key={item.feedback_ids.join(':')}><strong>Cosine similarity {item.cosine_similarity.toFixed(3)}</strong><p>{item.method === 'pgvector_cosine' ? 'Calculated by pgvector.' : 'Deterministic test calculation.'}</p><small>{item.feedback_ids.join(' ↔ ')}</small></li>)}</ul></>}
      </div>}

      {section === 'trust' && <div className="api-analysis-results">
        <div className="formula-banner"><LockKeyhole size={23}/><div><h3>Deterministic, evidence-bounded trust</h3><p>Formula {result?.trust[0]?.formula_version ?? 'trust-baseline-partial-v1'}. Missing factors are excluded and observed weights are renormalized; these are feedback-level estimates, not reviewer reputation scores.</p></div></div>
        {result ? <div className="table-scroll"><table><thead><tr><th>Feedback ID</th><th>Partial trust</th><th>Evidence coverage</th><th>Quality</th><th>Unsupported factors</th></tr></thead><tbody>{result.trust.map((trust) => {
                        const quality = result.quality.find((item) => item.feedback_id === trust.feedback_id);
                        return <tr key={trust.feedback_id}><td>{trust.feedback_id}</td><td>{trust.score?.toFixed(3) ?? 'Not available'}</td><td>{percent(trust.evidence_coverage)}</td><td>{quality ? ((quality.relevance + quality.constructiveness + quality.originality + quality.internal_consistency + 1 - quality.spam_risk) / 5).toFixed(3) : 'Not available'}</td><td>{trust.missing_factors.join(', ')}</td></tr>;
                    })}</tbody></table></div> : <AnalysisPending run={run}/>}
        {result?.quality.map((quality) => <p className="muted" key={quality.feedback_id}>Feedback {quality.feedback_id}: authenticity indicator {quality.authenticity_indicator.toFixed(2)} · self-reported confidence {quality.self_reported_confidence.toFixed(2)} · {quality.uncertainty} This is not proof of authenticity or fraud.</p>)}
      </div>}

      {section === 'consensus' && <div className="api-analysis-results">
        {result ? <><div className="consensus-columns">
          <section className="consensus-result"><Badge tone="green">Raw support</Badge><strong>{percent(result.consensus.raw_support)}</strong><p>{result.consensus.raw_support_count} of {result.consensus.sample_size} persisted reviews would use this version.</p><small>Unweighted; evidence IDs are retained.</small></section>
          <section className="consensus-result"><Badge>Trust-weighted support</Badge><strong>{percent(result.consensus.weighted_support)}</strong><p>Trust × authenticity indicator × relevance, divided by total raw feedback weight {result.consensus.normalized_weight_denominator.toFixed(5)}.</p><small>Confidence indicator {percent(result.consensus.confidence_indicator)} · uncalibrated.</small></section>
        </div><p className="notice">{result.consensus.uncertainty} Sample size: {result.consensus.sample_size}; evidence coverage: {percent(result.consensus.evidence_coverage)}. Evidence IDs: {result.consensus.evidence_ids.join(', ')}</p></> : <AnalysisPending run={run}/>}
      </div>}
    </section>}
  </>;
}
function Metric({ label, value, detail }) {
    return <div className="metric"><div className="metric-top">{label}</div><strong>{value}</strong><p>{detail}</p></div>;
}
function AnalysisPending({ run }) {
    return <Empty title={run?.status === 'failed' ? 'Analysis failed' : 'Analysis not available'}>
    <p>{run?.error_message ?? 'Start analysis to process the persisted feedback snapshot. No empty report is treated as success.'}</p>
  </Empty>;
}
function percent(value) {
    return value === null || value === undefined ? 'Not available' : `${(value * 100).toFixed(1)}%`;
}
export function Feedback() {
    return getAccessToken() ? <AuthenticatedFeedbackAnalysis section="feedback"/> : <PreviewFeedback />;
}
function PreviewFeedback() {
    const { idea, reviews, selector } = useEvidence();
    const location = useLocation();
    useEffect(() => {
        if (location.hash)
            document.getElementById(location.hash.slice(1))?.scrollIntoView({ block: 'center' });
    }, [location.hash, idea.id]);
    const [query, setQuery] = useState('');
    const [source, setSource] = useState('All sources');
    const [sort, setSort] = useState('Newest first');
    const visible = reviews.filter((review) => `${review.reviewer} ${review.strengths} ${review.concerns} ${review.improvements}`.toLowerCase().includes(query.toLowerCase()) && (source === 'All sources' || (source === 'Sample' ? review.sample : !review.sample))).sort((left, right) => sort === 'Lowest rating' ? left.rating - right.rating : new Date(right.created).getTime() - new Date(left.created).getTime());
    return <><PageHeading eyebrow="LISTEN & LEARN" title="Every perspective adds something." actions={selector}>Explore feedback in the context of the prototype people tested.</PageHeading><div className="filter-bar"><label className="search-field"><Search size={16}/><input aria-label="Search feedback" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search feedback or reviewers"/></label><select aria-label="Feedback source" value={source} onChange={(event) => setSource(event.target.value)}>{['All sources', 'Sample', 'Local reviews'].map((value) => <option key={value}>{value}</option>)}</select><select aria-label="Feedback sort" value={sort} onChange={(event) => setSort(event.target.value)}><option>Newest first</option><option>Lowest rating</option></select><span className="filter-count">{visible.length} records</span></div>
    {visible.length ? <div className="feedback-detail-list">{visible.map((review) => <article className="feedback-detail" id={review.id} key={review.id}><header><span className="avatar">{review.reviewer.split(' ').map((name) => name[0]).join('')}</span><div><strong>{review.reviewer}</strong><small>{idea.title} · V{review.version} · {dateLabel(review.created)}</small></div><Badge tone={review.sample ? 'neutral' : 'blue'}>{review.sample ? 'Sample feedback' : 'Local feedback'}</Badge><span className="review-score">{review.rating}<small>/5</small></span></header><div className="feedback-dimensions">{[['Usability', review.usability], ['Usefulness', review.usefulness], ['Feasibility', review.feasibility], ['Completeness', review.completeness]].map(([label, score]) => <span key={label}>{label}<strong>{score}/5</strong></span>)}<span>Would use<strong>{review.wouldUse ? 'Yes' : 'Not yet'}</strong></span></div><div className="feedback-columns"><section><span className="eyebrow">WHAT WORKED</span><p>{review.strengths}</p></section><section><span className="eyebrow">CONCERNS</span><p>{review.concerns}</p></section></div><div className="improvement"><Sparkles size={16}/><div><strong>Suggested improvement</strong><p>{review.improvements}</p></div></div><footer><p><MonitorLabel />{review.context}</p><Badge>Analysis pending</Badge></footer><small className="evidence-id">Evidence ID: {review.id}</small></article>)}</div> : <Empty title="No matching feedback"><p>Try another filter, or collect a review for this idea.</p></Empty>}
    <IdeaDiscussion key={idea.id} idea={idea}/>
  </>;
}
function MonitorLabel() { return <MessageSquare size={13}/>; }
export function Analytics() {
    return getAccessToken() ? <AuthenticatedFeedbackAnalysis section="analytics"/> : <PreviewAnalytics />;
}
function PreviewAnalytics() {
    const { reviews, selector, summary } = useEvidence();
    const averages = ['usability', 'usefulness', 'feasibility', 'completeness'];
    const support = Math.round((summary.support ?? 0) * 100);
    return <><PageHeading eyebrow="EVIDENCE AT A GLANCE" title="What the feedback is telling you." actions={selector}>A clearer view of this review cycle.</PageHeading><EvidenceNote /><div className="metrics-grid analytics-metrics">{[['Feedback records', summary.count, `${reviews.filter((review) => !review.sample).length} local submissions`], ['Average rating', summary.rating === null ? 'Not available' : `${summary.rating.toFixed(1)}/5`, 'Unweighted mean'], ['Would use', summary.support === null ? 'Not available' : `${support}%`, 'Raw reviewer response'], ['Analyzed feedback', 'Pending', 'Python workflow not connected']].map(([label, value, detail]) => <div className="metric" key={label}><div className="metric-top">{label}</div><strong className={typeof value === 'string' && value.length > 5 ? 'metric-text' : ''}>{value}</strong><p>{detail}</p></div>)}</div>
    {reviews.length ? <div className="chart-grid"><section><SectionHeading title="Experience ratings"/><p className="chart-description">Average score by dimension · out of 5</p><div className="chart-container"><Bar data={{ labels: ['Usability', 'Usefulness', 'Feasibility', 'Completeness'], datasets: [{ label: 'Average score', data: averages.map((key) => reviews.reduce((total, review) => total + review[key], 0) / reviews.length), backgroundColor: ['#7dac91', '#9bb8ce', '#d8bea4', '#a9bdaa'], borderRadius: 4, barThickness: 36 }] }} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 5, ticks: { stepSize: 1 }, grid: { color: '#edf2ee' }, border: { display: false } }, x: { grid: { display: false }, border: { display: false } } } }}/></div></section><section><SectionHeading title="Would reviewers use it?"/><p className="chart-description">Direct responses, without trust weighting</p><div className="donut-container"><Doughnut data={{ labels: ['Yes', 'Not yet'], datasets: [{ data: [reviews.filter((review) => review.wouldUse).length, reviews.filter((review) => !review.wouldUse).length], backgroundColor: ['#76a78a', '#eadfd2'], borderWidth: 0, hoverOffset: 4 }] }} options={{ responsive: true, maintainAspectRatio: false, cutout: '76%', plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 23 } } } }}/></div></section></div> : <Empty title="Analytics need feedback"><p>No ratings or support values are available for this idea.</p></Empty>}
    <div className="section-space"><SectionHeading title="Next analytical layers"/><div className="pending-grid">{[{ title: 'Semantic themes', detail: 'Bedrock embeddings + pgvector', icon: MessageSquare }, { title: 'Trust distribution', detail: 'Deterministic trust snapshots', icon: ShieldCheck }, { title: 'Priority matrix', detail: 'Evidence-linked feature ranking', icon: GitBranch }].map(({ title, detail, icon: Icon }) => <div key={title}><Icon size={22}/><h3>{title}</h3><p>{detail}</p><Badge>Awaiting analysis</Badge></div>)}</div></div>
  </>;
}
export function Trust() {
    return getAccessToken() ? <AuthenticatedFeedbackAnalysis section="trust"/> : <PreviewTrust />;
}
function PreviewTrust() {
    const { selector, reviews } = useEvidence();
    const [tab, setTab] = useState('Trust factors');
    const factors = [['Review quality', '30%', 'Evidence-backed quality signals'], ['Historical accuracy', '20%', 'Outcomes across previous review cycles'], ['Peer alignment', '15%', 'Independent agreement, with diversity safeguards'], ['Consistency', '15%', 'Stable evidence across review history'], ['Verified expertise', '10%', 'Verified, domain-relevant experience'], ['Community validation', '10%', 'Auditable community assessments']];
    return <><PageHeading eyebrow="TRUST & QUALITY" title="Confidence needs a clear foundation." actions={selector}>Transparent factors. Traceable evidence. No arbitrary scores.</PageHeading><div className="notice"><ShieldCheck size={22}/><div><strong>Trust analysis is not connected</strong><p>No reviewer trust scores or authenticity indicators have been calculated. Quality indicators cannot prove a person or review is fake.</p></div></div><div className="tabs" role="tablist">{['Trust factors', 'Feedback quality'].map((value) => <button role="tab" aria-selected={tab === value} key={value} onClick={() => setTab(value)}>{value}</button>)}</div>
    {tab === 'Trust factors' ? <><div className="formula-banner"><LockKeyhole size={23}/><div><h3>Deterministic by design</h3><p>Trust = the weighted sum of six evidence factors, each normalized to [0, 1].</p></div><Badge>Blueprint baseline</Badge></div><div className="table-scroll"><table><thead><tr><th>Factor</th><th>Weight</th><th>Evidence requirement</th><th>Status</th></tr></thead><tbody>{factors.map(([name, weight, description]) => <tr key={name}><td><strong>{name}</strong></td><td>{weight}</td><td>{description}</td><td><Badge>Pending</Badge></td></tr>)}</tbody></table></div></> : <><SectionHeading title="Review analysis queue"/>{reviews.length ? <div className="table-scroll"><table><thead><tr><th>Reviewer</th><th>Evidence source</th><th>Quality / authenticity</th><th>Confidence</th></tr></thead><tbody>{reviews.map((review) => <tr key={review.id}><td>{review.reviewer}</td><td>{review.sample ? 'Sample feedback' : 'Local feedback'}</td><td><Badge>Not analyzed</Badge></td><td>Not available</td></tr>)}</tbody></table></div> : <Empty title="No feedback to analyze"/>}<div className="pending-grid section-space">{['Relevance & constructiveness', 'Originality & consistency', 'Spam & bias risk indicators'].map((title) => <div key={title}><ShieldCheck size={20}/><h3>{title}</h3><p>Python Feedback Quality Agent</p><Badge>Awaiting workflow</Badge></div>)}</div></>}
  </>;
}
export function Consensus() {
    return getAccessToken() ? <AuthenticatedFeedbackAnalysis section="consensus"/> : <PreviewConsensus />;
}
function PreviewConsensus() {
    const { idea, reviews, summary, selector } = useEvidence();
    const yes = reviews.filter((review) => review.wouldUse).length;
    return <><PageHeading eyebrow="COLLECTIVE PERSPECTIVE" title="Agreement, with the evidence attached." actions={selector}>Keep raw feedback and trust-weighted conclusions separate.</PageHeading><EvidenceNote /><div className="consensus-columns"><section className="consensus-result"><Badge tone="green">Raw support</Badge><strong>{summary.support === null ? 'Not available' : `${Math.round(summary.support * 100)}%`}</strong><p>{yes} of {reviews.length} reviewers would use this prototype.</p><div className="support-track"><span style={{ width: `${(summary.support ?? 0) * 100}%` }}/></div><small>Unweighted · sample + local responses</small></section><section className="consensus-result pending"><Badge>Trust-weighted support</Badge><ShieldCheck size={29}/><h3>Awaiting trust analysis</h3><p>Reviewer trust × authenticity × relevance, normalized before aggregation.</p><small>Confidence is unavailable until evidence is analyzed.</small></section></div><SectionHeading title="Supporting evidence"/>{reviews.length ? <div className="table-scroll"><table><thead><tr><th>Reviewer</th><th>Would use</th><th>Rating</th><th>Evidence</th><th>Source</th></tr></thead><tbody>{reviews.map((review) => <tr key={review.id}><td>{review.reviewer}</td><td><Badge tone={review.wouldUse ? 'green' : 'coral'}>{review.wouldUse ? 'Yes' : 'Not yet'}</Badge></td><td>{review.rating}/5</td><td><Link className="text-link" to={`/feedback?idea=${idea.id}#${review.id}`}>Read review<ArrowUpRight size={13}/></Link></td><td>{review.sample ? 'Sample' : 'Local'}</td></tr>)}</tbody></table></div> : <Empty title="No evidence available"/>}</>;
}
export function Evolution() {
    return getAccessToken() ? <AuthenticatedEvolution /> : <PreviewEvolution />;
}
function AuthenticatedEvolution() {
    const [params, setParams] = useSearchParams();
    const [ideas, setIdeas] = useState([]);
    const [proposal, setProposal] = useState(null);
    const [selectedRanks, setSelectedRanks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [working, setWorking] = useState(false);
    const [error, setError] = useState('');
    const selectedIdeaId = params.get('idea') ?? '';
    const idea = ideas.find((item) => item.id === selectedIdeaId);
    useEffect(() => {
        let active = true;
        listIdeas()
            .then((page) => {
            if (!active)
                return;
            setIdeas(page.items.map(({ id, title, version }) => ({ id, title, version })));
            if (!selectedIdeaId && page.items[0])
                setParams({ idea: page.items[0].id });
        })
            .catch((reason) => setError(reason instanceof Error ? reason.message : 'Ideas could not be loaded.'))
            .finally(() => active && setLoading(false));
        return () => { active = false; };
    }, [selectedIdeaId, setParams]);
    useEffect(() => {
        if (!idea) {
            setProposal(null);
            return;
        }
        let active = true;
        setLoading(true);
        getEvolutionProposal(idea.id, idea.version)
            .then((result) => {
            if (!active)
                return;
            setProposal(result);
            setSelectedRanks([]);
        })
            .catch((reason) => setError(reason instanceof Error ? reason.message : 'The proposal could not be loaded.'))
            .finally(() => active && setLoading(false));
        return () => { active = false; };
    }, [idea]);
    async function createProposal() {
        if (!idea)
            return;
        setWorking(true);
        setError('');
        try {
            setProposal(await createEvolutionProposal(idea.id, idea.version));
            setSelectedRanks([]);
        }
        catch (reason) {
            setError(reason instanceof Error ? reason.message : 'A proposal could not be created.');
        }
        finally {
            setWorking(false);
        }
    }
    async function approveProposal() {
        if (!idea || !proposal || !selectedRanks.length)
            return;
        setWorking(true);
        setError('');
        try {
            const approved = await approveEvolutionProposal(idea.id, idea.version, proposal.id, selectedRanks);
            setProposal(approved);
            setIdeas((current) => current.map((entry) => entry.id === idea.id ? { ...entry, version: entry.version + 1 } : entry));
        }
        catch (reason) {
            setError(reason instanceof Error ? reason.message : 'The selected changes could not be approved.');
        }
        finally {
            setWorking(false);
        }
    }
    const selector = <select className="idea-selector" aria-label="Select idea" value={selectedIdeaId} onChange={(event) => setParams({ idea: event.target.value })}>
    {ideas.map((item) => <option key={item.id} value={item.id}>{item.title} · V{item.version}</option>)}
  </select>;
    return <>
    <PageHeading eyebrow="IDEA EVOLUTION" title="A next version with a reason behind it." actions={selector}>
      Suggestions are grounded in persisted evidence. Only owner approval creates a new immutable version.
    </PageHeading>
    {error && <div className="notice" role="alert">{error}</div>}
    {loading ? <p role="status">Loading persisted evolution data…</p> : !idea
            ? <Empty title="No authenticated ideas available."/>
            : !proposal
                ? <section className="notice">
          <GitBranch size={20}/>
          <div>
            <strong>Evidence-based proposal</strong>
            <p>Creation requires validated requirements and a completed analysis of submitted feedback for V{idea.version}.</p>
            <button className="button primary" disabled={working} onClick={() => void createProposal()}>
              {working ? 'Preparing proposal…' : 'Generate evidence-linked proposal'}
            </button>
          </div>
        </section>
                : <>
          <div className="notice">
            <Info size={18}/>
            <div>
              <strong>{proposal.status === 'approved' ? 'Owner-approved candidate' : 'Generated suggestions — not approved'}</strong>
              <p>Source V{proposal.source_version} · {proposal.source_feedback_ids.length} submitted reviews · analysis {proposal.feedback_analysis_run_id}. A source-only Builder result is not a built or working prototype.</p>
            </div>
          </div>
          <SectionHeading title="Proposed changes and evidence"/>
          <div className="priority-list">
            {proposal.suggestions.map((suggestion) => <label key={suggestion.rank}>
              <input type="checkbox" aria-label={`Approve ${suggestion.title}`} disabled={proposal.status !== 'proposed' || !suggestion.builder_supported} checked={selectedRanks.includes(suggestion.rank)} onChange={() => setSelectedRanks((current) => current.includes(suggestion.rank)
                            ? current.filter((rank) => rank !== suggestion.rank)
                            : [...current, suggestion.rank])}/>
              <div>
                <strong>{suggestion.priority}: {suggestion.title}</strong>
                <p>{suggestion.rationale}</p>
                <span>Qualitative impact: {suggestion.expected_benefit.qualitative_impact}; weighted support: {suggestion.expected_benefit.weighted_support.toFixed(3)} (analysis value, not outcome measurement).</span>
                <p>Source feedback: {suggestion.source_feedback_ids.join(', ')}</p>
                <p>Risks: {suggestion.risks.length ? suggestion.risks.map((risk) => risk.concern).join(' · ') : 'No separate reviewer concern cited.'}</p>
                <p>{suggestion.builder_supported ? 'Supported by the current source-generation template.' : 'Outside current Builder scope; cannot approve for generation.'}</p>
                {suggestion.missing_inputs.length > 0 && <p>Missing inputs: {suggestion.missing_inputs.join(', ')}</p>}
              </div>
            </label>)}
          </div>
          {proposal.status === 'proposed'
                        ? <div className="form-actions section-space">
              <button className="button primary" disabled={working || !selectedRanks.length} onClick={() => void approveProposal()}>
                {working ? 'Creating immutable candidate…' : `Approve ${selectedRanks.length} selected change(s)`}
              </button>
            </div>
                        : <div className="notice">
              <Badge tone="blue">Candidate V{String(proposal.validation_results.target_version)} · Draft</Badge>
              <p>Builder source: {String(proposal.validation_results.prototype_source_status)} · build: {String(proposal.validation_results.prototype_build_status)} · publication: {String(proposal.validation_results.prototype_publish_status)}. No isolated build or working prototype is available.</p>
            </div>}
        </>}
  </>;
}
function PreviewEvolution() {
    const { idea, selector, state, update } = useEvidence();
    const reviews = rankPriorities(state, idea.id).filter((item) => item.score !== null).map((item) => ({ id: item.id, version: item.version, improvements: item.text, reviewer: item.author, concerns: `${item.priority} · ${item.effort} effort · ${item.rationale}`, sample: state.reviews.find((review) => review.id === item.id)?.sample ?? false }));
    const [selected, setSelected] = useState([]);
    const evolution = state.evolutions.find((entry) => entry.ideaId === idea.id && entry.source === idea.version);
    const evidence = selected.filter((id) => reviews.some((review) => review.id === id && review.version === idea.version));
    return <><PageHeading eyebrow="IDEA EVOLUTION" title="A next version with a reason behind it." actions={selector}>Preserve the original. Make every proposed change traceable.</PageHeading><div className="evolution-path">{['V1 prototype', 'Comments & feedback', 'Prioritized proposal', 'Validated V2'].map((label, index) => <div className={index === 2 && evolution ? 'current' : ''} key={label}><span>{index < 2 ? <Check size={15}/> : index + 1}</span>{label}{index < 3 && <ArrowRight size={16}/>}</div>)}</div><div className="notice"><GitBranch size={20}/><div><strong>Feasibility-aware, evidence-linked proposal</strong><p>Assess effort and impact first, then choose changes below. Questions and blockers stay out of the build plan. No AI evolution or V2 build is claimed.</p></div></div>
    {evolution ? <PrioritySnapshot evolution={evolution}/> : <PriorityBoard key={idea.id} idea={idea}/>}
    {evolution ? <><div className="version-comparison"><section><Badge tone="green">V{idea.version} / Preserved</Badge><h2>{idea.title}</h2><p>{idea.solution}</p><h3>Original scope</h3><ul>{idea.features.map((feature) => <li key={feature}><Check size={14}/>{feature}</li>)}</ul><Link className="button" to={`/ideas/${idea.id}/prototype`}>Open original prototype<ArrowUpRight size={14}/></Link></section><section><Badge tone="blue">V{evolution.target} / Proposal</Badge><h2>Evidence-led changes</h2><p>{evolution.changes.length} proposed improvements · {dateLabel(evolution.created)}</p><ul>{evolution.changes.map((change, index) => <li key={`${index}-${change}`}><span className="change-marker">+</span><div>{change}<Link to={`/feedback?idea=${idea.id}#${evolution.evidence[index]}`} className="text-link">Source evidence<ArrowUpRight size={12}/></Link></div></li>)}</ul><Badge>V2 build pending Python workflow</Badge></section></div><div className="form-actions section-space"><button className="button" onClick={() => downloadFile(`${idea.id}-v${evolution.target}-proposal.json`, JSON.stringify({ ...evolution, source: 'frontend-preview', ai_generated: false }, null, 2), 'application/json')}><Download size={15}/>Export change proposal</button><Link className="button primary" to={`/reports?idea=${idea.id}`}>View decision report<ArrowRight size={15}/></Link></div></> : <><SectionHeading title="Choose feedback to carry forward"/>{reviews.length ? <div className="priority-list">{reviews.map((review) => <label key={review.id}><input type="checkbox" checked={evidence.includes(review.id)} onChange={() => setSelected(evidence.includes(review.id) ? evidence.filter((id) => id !== review.id) : [...evidence, review.id])}/><div><strong>{review.improvements}</strong><p>{review.reviewer} · V{review.version} · {review.sample ? 'Sample' : 'Local'} evidence</p><span>{review.concerns}</span></div><Link aria-label={`Read evidence from ${review.reviewer}`} title="Read source evidence" to={`/feedback?idea=${idea.id}#${review.id}`}><ArrowUpRight size={17}/></Link></label>)}</div> : <Empty title="Feedback comes first"><p>A version proposal needs evidence from this idea.</p></Empty>}<div className="form-actions section-space"><span className="muted">{evidence.length} suggestions selected</span><button disabled={!evidence.length} className="button primary" onClick={() => update((current) => proposeEvolution(current, idea.id, evidence), 'Change proposal created. The original version is preserved.')}><GitBranch size={16}/>Create change proposal</button></div></>}
  </>;
}
export function Reports() {
    return getAccessToken() ? <AuthenticatedReports /> : <PreviewReports />;
}
function AuthenticatedReports() {
    const [params, setParams] = useSearchParams();
    const [ideas, setIdeas] = useState([]);
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(true);
    const [working, setWorking] = useState(false);
    const [error, setError] = useState('');
    const ideaId = params.get('idea') ?? '';
    const idea = ideas.find((item) => item.id === ideaId);
    useEffect(() => {
        let active = true;
        listIdeas()
            .then((page) => {
            if (!active)
                return;
            setIdeas(page.items.map(({ id, title, version }) => ({ id, title, version })));
            if (!ideaId && page.items[0])
                setParams({ idea: page.items[0].id });
        })
            .catch((reason) => setError(reason instanceof Error ? reason.message : 'Ideas could not be loaded.'))
            .finally(() => active && setLoading(false));
        return () => { active = false; };
    }, [ideaId, setParams]);
    useEffect(() => {
        if (!idea) {
            setReport(null);
            return;
        }
        let active = true;
        setLoading(true);
        getLatestDecisionReport(idea.id, idea.version)
            .then((result) => active && setReport(result))
            .catch((reason) => setError(reason instanceof Error ? reason.message : 'The report could not be loaded.'))
            .finally(() => active && setLoading(false));
        return () => { active = false; };
    }, [idea]);
    async function generateReport() {
        if (!idea)
            return;
        setWorking(true);
        setError('');
        try {
            setReport(await createDecisionReport(idea.id, idea.version));
        }
        catch (reason) {
            setError(reason instanceof Error ? reason.message : 'A report snapshot could not be created.');
        }
        finally {
            setWorking(false);
        }
    }
    const selector = <select className="idea-selector" aria-label="Select idea" value={ideaId} onChange={(event) => setParams({ idea: event.target.value })}>
    {ideas.map((item) => <option key={item.id} value={item.id}>{item.title} · V{item.version}</option>)}
  </select>;
    const reportData = report?.report;
    return <>
    <PageHeading eyebrow="DECISION INTELLIGENCE" title="A traceable record of what the evidence supports." actions={selector}>
      Persisted report snapshots identify their exact source version, analysis runs, and reviewer evidence.
    </PageHeading>
    {error && <div className="notice" role="alert">{error}</div>}
    {loading ? <p role="status">Loading report snapshot…</p> : !idea
            ? <Empty title="No authenticated ideas available."/>
            : <>
        <div className="report-toolbar">
          <Badge tone="blue">{report ? `Persisted snapshot · ${report.report_version}` : 'No report snapshot yet'}</Badge>
          <button className="button primary" disabled={working} onClick={() => void generateReport()}>
            {working ? 'Saving snapshot…' : 'Create report snapshot'}
          </button>
        </div>
        {report && reportData
                    ? <section className="report-card">
            <div className="report-summary">
              <div><small>Source version</small><strong>V{report.source_version}</strong></div>
              <div><small>Persisted feedback</small><strong>{report.source_feedback_ids.length} records</strong></div>
              <div><small>Requirements analysis</small><strong>{report.requirement_analysis_run_id ?? 'Unavailable'}</strong></div>
              <div><small>Feedback analysis</small><strong>{report.feedback_analysis_run_id ?? 'Unavailable'}</strong></div>
            </div>
            <p>Report ID {report.id} · created {dateLabel(report.created_at)}. Facts, calculations, and model interpretations are labeled in the snapshot; unavailable evidence remains explicit.</p>
            <pre className="report-json">{JSON.stringify(reportData, null, 2)}</pre>
          </section>
                    : <Empty title="No persisted report snapshot for this version."/>}
      </>}
  </>;
}
function PreviewReports() {
    const { idea, reviews, summary, selector, state } = useEvidence();
    const proposal = state.evolutions.find((entry) => entry.ideaId === idea.id);
    function exportReport() {
        const report = [`# ${idea.title} - Preview decision report`, '', 'Source: sample and browser-local feedback. Not an AI validation result.', `Version: ${idea.version}`, `Detailed feedback records: ${reviews.length}`, `Raw average rating: ${summary.rating?.toFixed(2) ?? 'Unavailable'}`, `Raw support: ${summary.support === null ? 'Unavailable' : `${Math.round(summary.support * 100)}%`}`, 'Trust-weighted consensus: Pending Python analysis.', '', '## Review evidence', ...reviews.map((review) => `- ${review.id} (${review.sample ? 'Sample' : 'Local'}): ${review.improvements}`), '', '## Comment evidence', ...state.comments.filter((comment) => comment.ideaId === idea.id && comment.version === idea.version).map((comment) => `- ${comment.id} (Local ${comment.kind}): ${comment.text} Context: ${comment.context}`), '', '## Change proposal', ...(proposal?.changes.map((change, index) => `- ${proposal.priorities?.[index]?.priority ?? 'Unranked'}: ${change} [evidence: ${proposal.evidence[index]}]`) ?? ['No change proposal created.']), ...(proposal?.priorities?.map((item) => `  ${item.evidenceId}: ${item.rationale}`) ?? []), '', '## Next steps', 'Connect Python workflows and collect authenticated reviewer evidence before making a production decision.'].join('\n');
        downloadFile(`${idea.id}-preview-report.md`, report, 'text/markdown');
    }
    return <><PageHeading eyebrow="DECISION INTELLIGENCE" title="A clear record of what comes next." actions={selector}>Findings, open questions, and the feedback behind them.</PageHeading><div className="report-toolbar"><Badge tone="coral">Preview report · Not AI-generated</Badge><div><button className="button" onClick={() => window.print()}><Printer size={15}/>Print</button><button className="button primary" onClick={exportReport}><Download size={15}/>Export report</button></div></div><section className="report-cover"><div><span className="eyebrow">VALIDATION REVIEW / V{idea.version}</span><h2>{idea.title}</h2><p>{idea.solution}</p></div><FileCheck2 size={40} strokeWidth={1.1}/></section><div className="report-summary"><div><small>Evidence coverage</small><strong>{reviews.length} feedback records</strong></div><div><small>Decision status</small><strong>Further validation needed</strong></div><div><small>Trust coverage</small><strong>Not analyzed</strong></div></div><div className="report-columns"><section><SectionHeading title="Reported strengths"/>{reviews.length ? reviews.map((review) => <Link key={review.id} to={`/feedback?idea=${idea.id}#${review.id}`} className="report-evidence"><Check size={16}/><p>{review.strengths}<small>{review.reviewer} · {review.sample ? 'Sample' : 'Local'}</small></p><ArrowUpRight size={14}/></Link>) : <p className="muted">No evidence yet.</p>}</section><section><SectionHeading title="Open concerns"/>{reviews.length ? reviews.map((review) => <Link key={review.id} to={`/feedback?idea=${idea.id}#${review.id}`} className="report-evidence concern"><Info size={16}/><p>{review.concerns}<small>{review.reviewer} · {review.sample ? 'Sample' : 'Local'}</small></p><ArrowUpRight size={14}/></Link>) : <p className="muted">No evidence yet.</p>}</section></div><div className="report-next"><div><FileText size={23}/><h3>{proposal ? 'A proposal is ready for validation.' : 'Keep the next decision grounded.'}</h3><p>{proposal ? `${proposal.changes.length} evidence-linked changes proposed. V1 is preserved; a validated V2 is still pending.` : 'Collect more reviewer evidence, evaluate trust factors, and validate changes before drawing a production conclusion.'}</p></div><Link className="button" to={`/evolution?idea=${idea.id}`}>{proposal ? 'View proposal' : 'Explore improvements'}<ArrowRight size={15}/></Link></div></>;
}
