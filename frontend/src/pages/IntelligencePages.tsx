import { useEffect, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router'
import { Bar, Doughnut } from 'react-chartjs-2'
import { ArcElement, BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js'
import { ArrowRight, ArrowUpRight, Check, Download, FileCheck2, FileText, GitBranch, Info, LockKeyhole, MessageSquare, Printer, Search, ShieldCheck, Sparkles } from 'lucide-react'
import { downloadFile, ideaReviews, proposeEvolution, rankPriorities, reviewSummary } from '@/services/preview'
import { useWorkspace } from '@/services/workspace'
import { Badge, dateLabel, Empty, ErrorBanner, formatFactorLabel, LoadingState, PageHeading, SectionHeading, Status } from '@/components/ui'
import { IdeaDiscussion } from '@/components/IdeaDiscussion'
import { PriorityBoard, PrioritySnapshot } from '@/components/PriorityBoard'
import { getAccessToken } from '@/services/auth'
import type {
  DecisionReport,
  EvolutionProposal,
  FeedbackAnalysisRun,
  PersistedReview,
} from '@/services/ideas'
import {
  approveEvolutionProposal,
  createDecisionReport,
  createEvolutionProposal,
  getFeedbackAnalysis,
  getEvolutionProposal,
  getIdea,
  getLatestDecisionReport,
  getLatestFeedbackAnalysis,
  listIdeas,
  listPersistedFeedback,
  startFeedbackAnalysis,
} from '@/services/ideas'

ChartJS.register(ArcElement, BarElement, CategoryScale, Legend, LinearScale, Tooltip)
ChartJS.defaults.font.family = 'Aptos, Segoe UI, sans-serif'
ChartJS.defaults.color = '#90a294'
ChartJS.defaults.font.size = 10

function useEvidence() {
  const workspace = useWorkspace()
  const [params, setParams] = useSearchParams()
  const idea = workspace.state.ideas.find((candidate) => candidate.id === params.get('idea')) ?? workspace.state.ideas[0]
  const reviews = idea ? ideaReviews(workspace.state, idea.id) : []
  const selector = <select className="idea-selector" aria-label="Select idea" value={idea?.id ?? ''} onChange={(event) => setParams({ idea: event.target.value })}>{workspace.state.ideas.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.title}</option>)}</select>
  return { ...workspace, idea, reviews, selector, summary: reviewSummary(reviews) }
}

function EvidenceNote() { return <p className="evidence-note"><Info size={13} />Values are calculated from sample and local workspace feedback, not a production validation result.</p> }

type AnalysisSection = 'feedback' | 'analytics' | 'trust' | 'consensus'

function AuthenticatedFeedbackAnalysis({ section }: { section: AnalysisSection }) {
  const [ideas, setIdeas] = useState<{ id: string; title: string; version: number }[]>([])
  const [selectedIdeaId, setSelectedIdeaId] = useState('')
  const [selectedVersion, setSelectedVersion] = useState(0)
  const [versions, setVersions] = useState<{ version: number; title: string }[]>([])
  const [reviews, setReviews] = useState<PersistedReview[]>([])
  const [run, setRun] = useState<FeedbackAnalysisRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    listIdeas()
      .then(async (page) => {
        if (!active) return
        setIdeas(page.items.map((idea) => ({ id: idea.id, title: idea.title, version: idea.version })))
        if (!page.items.length) {
          setLoading(false)
          return
        }
        const selected = page.items[0]
        setSelectedIdeaId(selected.id)
        const detail = await getIdea(selected.id)
        if (!active) return
        const ideaVersions = detail.versions.map((version) => ({ version: version.version, title: version.title }))
        setVersions(ideaVersions)
        setSelectedVersion(detail.version)
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Ideas could not be loaded.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!selectedIdeaId) return
    let active = true
    setLoading(true)
    setRun(null)
    setReviews([])
    getIdea(selectedIdeaId)
      .then((detail) => {
        if (!active) return
        setVersions(detail.versions.map((version) => ({ version: version.version, title: version.title })))
        setSelectedVersion((current) => current || detail.version)
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Idea versions could not be loaded.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [selectedIdeaId])

  useEffect(() => {
    if (!selectedIdeaId || !selectedVersion) return
    let active = true
    setLoading(true)
    Promise.all([
      listPersistedFeedback(selectedIdeaId, selectedVersion),
      getLatestFeedbackAnalysis(selectedIdeaId, selectedVersion),
    ])
      .then(([persisted, latest]) => {
        if (!active) return
        setReviews(persisted)
        setRun(latest)
        setError('')
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Submitted feedback could not be loaded.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [selectedIdeaId, selectedVersion])

  useEffect(() => {
    if (!run || !['queued', 'running'].includes(run.status)) return
    let active = true
    const timer = window.setInterval(() => {
      getFeedbackAnalysis(run.idea_id, run.source_version, run.id)
        .then((latest) => { if (active) setRun(latest) })
        .catch((reason: unknown) => {
          if (active) setError(reason instanceof Error ? reason.message : 'Analysis status could not be refreshed.')
        })
    }, 1500)
    return () => { active = false; window.clearInterval(timer) }
  }, [run])

  const selectedIdea = ideas.find((idea) => idea.id === selectedIdeaId)
  const result = run?.status === 'completed' ? run.result : null

  const submitAnalysis = async () => {
    if (!selectedIdeaId || !selectedVersion) return
    setSubmitting(true)
    setError('')
    try {
      setRun(await startFeedbackAnalysis(selectedIdeaId, selectedVersion))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Feedback analysis could not be started.')
    } finally {
      setSubmitting(false)
    }
  }

  const selector = <div className="api-analysis-selectors">
    <select aria-label="Select idea" value={selectedIdeaId} onChange={(event) => {
      setSelectedIdeaId(event.target.value)
      setSelectedVersion(0)
    }}>
      {ideas.map((idea) => <option value={idea.id} key={idea.id}>{idea.title}</option>)}
    </select>
    <select aria-label="Select version" value={selectedVersion || ''} onChange={(event) => setSelectedVersion(Number(event.target.value))}>
      {versions.map((version) => <option value={version.version} key={version.version}>V{version.version} · {version.title}</option>)}
    </select>
  </div>

  const pageCopy: Record<AnalysisSection, { eyebrow: string; title: string; description: string }> = {
    feedback: { eyebrow: 'SUBMITTED REVIEW EVIDENCE', title: 'Feedback from this version.', description: 'Explore verified reviewer feedback submitted against this exact version.' },
    analytics: { eyebrow: 'EVIDENCE AT A GLANCE', title: 'What submitted feedback supports.', description: 'Analysis is version-scoped and traces every theme and priority to reviewer responses.' },
    trust: { eyebrow: 'TRUST & QUALITY', title: 'Signals, not verdicts.', description: 'Quality judgments are uncertain indicators; no score proves a person or comment is fake.' },
    consensus: { eyebrow: 'COLLECTIVE PERSPECTIVE', title: 'Agreement with evidence attached.', description: 'Raw responses and trust-weighted consensus remain clearly separated.' },
  }
  const copy = pageCopy[section]
  const analysisStatusLabel = !run
    ? 'Awaiting analysis'
    : run.status === 'completed'
      ? 'Analysis ready'
      : run.status === 'failed'
        ? 'Action required'
        : 'Analyzing feedback'

  return <>
    <PageHeading eyebrow={copy.eyebrow} title={copy.title} actions={selector}>{copy.description}</PageHeading>
    {error && <ErrorBanner message={error} onRetry={submitAnalysis} />}
    {loading && <LoadingState title="Loading review evidence…" detail="Retrieving submitted feedback and intelligence summaries for this version." />}
    {!loading && !ideas.length && <Empty title="No ideas yet"><p>Submit an idea and collect reviewer feedback before analyzing responses.</p></Empty>}
    {!loading && selectedIdea && <section className="api-analysis-panel">
      <div className="api-analysis-toolbar">
        <div>
          <div className="requirement-status-group">
            <Status value={analysisStatusLabel} />
            <Badge tone="blue">{selectedIdea.title} · V{selectedVersion}</Badge>
          </div>
          <p>{reviews.length} submitted review{reviews.length === 1 ? '' : 's'} in this version snapshot.</p>
        </div>
        <button className="button primary" disabled={submitting || reviews.length === 0} onClick={() => void submitAnalysis()}>
          {submitting ? 'Analyzing…' : run?.status === 'failed' ? 'Retry analysis' : run?.status === 'completed' ? 'Refresh analysis' : 'Analyze feedback'}
        </button>
      </div>
      {reviews.length === 0 && <Empty title="No feedback submitted yet"><p>Assign a reviewer to test V{selectedVersion}. Feedback analysis becomes available once at least one review is submitted.</p></Empty>}
      {run?.error_message && <ErrorBanner message={run.error_message} onRetry={submitAnalysis} />}

      {section === 'feedback' && reviews.length > 0 && <div className="feedback-detail-list">{reviews.map((review, index) => {
        const quality = result?.quality.find((item) => item.feedback_id === review.id)
        return <article className="feedback-detail" key={review.id}>
          <header>
            <span className="avatar">R{index + 1}</span>
            <div>
              <strong>Verified Reviewer #{index + 1}</strong>
              <small>Version {selectedVersion} · {dateLabel(review.created_at)}</small>
            </div>
            <Badge tone="green">Submitted</Badge>
            {review.would_use !== null && <Badge tone={review.would_use ? 'green' : 'coral'}>{review.would_use ? 'Would use' : 'Needs changes'}</Badge>}
            <span className="review-score">{review.rating}<small>/5</small></span>
          </header>
          <div className="feedback-dimensions">
            {[
              ['Usability', review.usability_score],
              ['Usefulness', review.usefulness_score],
              ['Feasibility', review.feasibility_score],
              ['Completeness', review.completeness_score],
            ].map(([label, score]) => score !== null && <span key={String(label)}>{label}<strong>{score}/5</strong></span>)}
          </div>
          <p>{review.feedback_text}</p>
          <div className="feedback-columns">
            <section><span className="eyebrow">STRENGTHS</span><p>{review.strengths}</p></section>
            <section><span className="eyebrow">CONCERNS</span><p>{review.concerns}</p></section>
          </div>
          <div className="improvement"><Sparkles size={16} /><div><strong>Suggested improvement</strong><p>{review.suggested_improvements}</p></div></div>
          {quality && <p className="muted">Quality indicators — relevance {Math.round(quality.relevance * 100)}%, constructiveness {Math.round(quality.constructiveness * 100)}%, originality {Math.round(quality.originality * 100)}%. {quality.uncertainty}</p>}
        </article>
      })}</div>}

      {section === 'analytics' && (result ? <div className="api-analysis-results">
        <div className="metrics-grid analytics-metrics">
          <Metric label="Reviews analyzed" value={result.consensus.sample_size} detail={`${result.source_feedback_ids.length} verified submission${result.source_feedback_ids.length === 1 ? '' : 's'}`} />
          <Metric label="Raw support" value={percent(result.consensus.raw_support)} detail={`${result.consensus.raw_support_count} positive response${result.consensus.raw_support_count === 1 ? '' : 's'}`} />
          <Metric label="Trust-weighted support" value={percent(result.consensus.weighted_support)} detail="Weighted by review quality & relevance" />
          <Metric label="Evidence coverage" value={percent(result.consensus.evidence_coverage)} detail="Submitted feedback represented" />
        </div>
        <SectionHeading title="Evidence-linked themes" />
        {result.themes.length ? <ul className="analysis-evidence-list">{result.themes.map((theme, index) => <li key={`${theme.label}-${index}`}>
          <div className="requirement-fact-header">
            <Badge tone={theme.kind === 'complaint' ? 'coral' : theme.kind === 'feature_request' ? 'green' : 'blue'}>{formatFactorLabel(theme.kind)}</Badge>
            <small>{theme.feedback_ids.length} supporting review{theme.feedback_ids.length === 1 ? '' : 's'}</small>
          </div>
          <strong>{theme.label}</strong>
          <p>{theme.summary}</p>
        </li>)}</ul> : <Empty title="No themes extracted"><p>No recurring themes were identified in this feedback snapshot.</p></Empty>}
        <SectionHeading title="Prioritized improvement signals" />
        {result.priorities.length ? <ol className="analysis-evidence-list">{result.priorities.map((priority) => <li key={`${priority.rank}-${priority.title}`}>
          <div className="requirement-fact-header">
            <Badge tone={priority.priority === 'P1' ? 'green' : 'blue'}>{priority.priority} · Rank #{priority.rank}</Badge>
            <small>Impact: {priority.impact} · Feasibility: {priority.feasibility}</small>
          </div>
          <strong>{priority.title}</strong>
          <p>{priority.rationale}</p>
          <small>{priority.evidence_count} supporting review{priority.evidence_count === 1 ? '' : 's'} · Weighted support {percent(priority.weighted_support)} · {priority.impact_rationale}</small>
        </li>)}</ol> : <p className="muted">No explicit feature requests were found to prioritize.</p>}
        {!!result.contradictions.length && <><SectionHeading title="Contradictions to review" /><ul className="analysis-evidence-list">{result.contradictions.map((item, index) => <li key={index}><p>{item.summary}</p><small>{item.feedback_ids.length} conflicting review responses</small></li>)}</ul></>}
        {!!result.duplicate_pairs.length && <><SectionHeading title="Related feedback clusters" /><ul className="analysis-evidence-list">{result.duplicate_pairs.map((item, idx) => <li key={idx}><strong>Similarity score {(item.cosine_similarity * 100).toFixed(1)}%</strong><p>Semantic similarity match across submitted reviews.</p></li>)}</ul></>}
      </div> : <AnalysisPending run={run} />)}

      {section === 'trust' && <div className="api-analysis-results">
        <div className="formula-banner"><LockKeyhole size={23} /><div><h3>Evidence-bounded trust assessment</h3><p>Missing historical factors are excluded and observed quality weights are renormalized; these are review-level quality estimates, not personal reputation scores.</p></div><Badge tone="green">Transparent weighting</Badge></div>
        {result ? <div className="table-scroll"><table><thead><tr><th>Review</th><th>Partial trust</th><th>Evidence coverage</th><th>Quality score</th><th>Factors awaiting history</th></tr></thead><tbody>{result.trust.map((trust, index) => {
          const quality = result.quality.find((item) => item.feedback_id === trust.feedback_id)
          return <tr key={trust.feedback_id}>
            <td><strong>Verified Review #{index + 1}</strong></td>
            <td>{trust.score !== null && trust.score !== undefined ? `${Math.round(trust.score * 100)}%` : 'Not available'}</td>
            <td>{percent(trust.evidence_coverage)}</td>
            <td>{quality ? `${Math.round(((quality.relevance + quality.constructiveness + quality.originality + quality.internal_consistency + 1 - quality.spam_risk) / 5) * 100)}%` : 'Not available'}</td>
            <td>{trust.missing_factors.map(formatFactorLabel).join(', ') || 'None'}</td>
          </tr>
        })}</tbody></table></div> : <AnalysisPending run={run} />}
        {result?.quality.map((quality, index) => <p className="muted" key={quality.feedback_id}>Verified Review #{index + 1}: authenticity indicator {Math.round(quality.authenticity_indicator * 100)}% · reviewer confidence {Math.round(quality.self_reported_confidence * 100)}%. {quality.uncertainty}</p>)}
      </div>}

      {section === 'consensus' && <div className="api-analysis-results">
        {result ? <><div className="consensus-columns">
          <section className="consensus-result"><Badge tone="green">Raw support</Badge><strong>{percent(result.consensus.raw_support)}</strong><p>{result.consensus.raw_support_count} of {result.consensus.sample_size} submitted reviews would use this version.</p><small>Unweighted direct reviewer responses</small></section>
          <section className="consensus-result"><Badge tone="blue">Trust-weighted support</Badge><strong>{percent(result.consensus.weighted_support)}</strong><p>Weighted by review quality, constructiveness, and relevance across verified submissions.</p><small>Confidence indicator: {percent(result.consensus.confidence_indicator)}</small></section>
        </div><p className="notice">{result.consensus.uncertainty} Sample size: {result.consensus.sample_size} review{result.consensus.sample_size === 1 ? '' : 's'} · Evidence coverage: {percent(result.consensus.evidence_coverage)}.</p>
        <div className="form-actions section-space">
          <Link className="button primary" to={`/evolution?idea=${selectedIdeaId}`}><GitBranch size={15} />Proceed to Idea Evolution<ArrowRight size={15} /></Link>
          <Link className="button" to={`/reports?idea=${selectedIdeaId}`}><FileText size={15} />Open Decision Intelligence<ArrowRight size={15} /></Link>
        </div></> : <AnalysisPending run={run} />}
      </div>}
    </section>}
  </>
}

function Metric({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return <div className="metric"><div className="metric-top">{label}</div><strong>{value}</strong><p>{detail}</p></div>
}

function AnalysisPending({ run }: { run: FeedbackAnalysisRun | null }) {
  return <Empty title={run?.status === 'failed' ? 'Analysis requires attention' : 'Analysis not available yet'}>
    <p>{run?.status === 'failed' ? 'We could not complete feedback analysis. Please retry.' : 'Run feedback analysis to calculate themes, trust signals, and consensus from submitted reviews.'}</p>
  </Empty>
}

function percent(value: number | null | undefined) {
  return value === null || value === undefined ? 'Not available' : `${(value * 100).toFixed(1)}%`
}

export function Feedback() {
  return getAccessToken() ? <AuthenticatedFeedbackAnalysis section="feedback" /> : <PreviewFeedback />
}

function PreviewFeedback() {
  const { idea, reviews, selector } = useEvidence()
  const location = useLocation()
  useEffect(() => {
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView({ block: 'center' })
  }, [location.hash, idea.id])
  const [query, setQuery] = useState('')
  const [source, setSource] = useState('All sources')
  const [sort, setSort] = useState('Newest first')
  const visible = reviews.filter((review) => `${review.reviewer} ${review.strengths} ${review.concerns} ${review.improvements}`.toLowerCase().includes(query.toLowerCase()) && (source === 'All sources' || (source === 'Sample' ? review.sample : !review.sample))).sort((left, right) => sort === 'Lowest rating' ? left.rating - right.rating : new Date(right.created).getTime() - new Date(left.created).getTime())
  return <><PageHeading eyebrow="LISTEN & LEARN" title="Every perspective adds something." actions={selector}>Explore feedback in the context of the prototype people tested.</PageHeading><div className="filter-bar"><label className="search-field"><Search size={16} /><input aria-label="Search feedback" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search feedback or reviewers" /></label><select aria-label="Feedback source" value={source} onChange={(event) => setSource(event.target.value)}>{['All sources', 'Sample', 'Local reviews'].map((value) => <option key={value}>{value}</option>)}</select><select aria-label="Feedback sort" value={sort} onChange={(event) => setSort(event.target.value)}><option>Newest first</option><option>Lowest rating</option></select><span className="filter-count">{visible.length} records</span></div>
    {visible.length ? <div className="feedback-detail-list">{visible.map((review) => <article className="feedback-detail" id={review.id} key={review.id}><header><span className="avatar">{review.reviewer.split(' ').map((name) => name[0]).join('')}</span><div><strong>{review.reviewer}</strong><small>{idea.title} · V{review.version} · {dateLabel(review.created)}</small></div><Badge tone={review.sample ? 'neutral' : 'blue'}>{review.sample ? 'Sample feedback' : 'Local feedback'}</Badge><span className="review-score">{review.rating}<small>/5</small></span></header><div className="feedback-dimensions">{[['Usability', review.usability], ['Usefulness', review.usefulness], ['Feasibility', review.feasibility], ['Completeness', review.completeness]].map(([label, score]) => <span key={label}>{label}<strong>{score}/5</strong></span>)}<span>Would use<strong>{review.wouldUse ? 'Yes' : 'Not yet'}</strong></span></div><div className="feedback-columns"><section><span className="eyebrow">WHAT WORKED</span><p>{review.strengths}</p></section><section><span className="eyebrow">CONCERNS</span><p>{review.concerns}</p></section></div><div className="improvement"><Sparkles size={16} /><div><strong>Suggested improvement</strong><p>{review.improvements}</p></div></div><footer><p><MonitorLabel />{review.context}</p><Badge>Reviewed</Badge></footer></article>)}</div> : <Empty title="No matching feedback"><p>Try another filter, or collect a review for this idea.</p></Empty>}
    <IdeaDiscussion key={idea.id} idea={idea} />
  </>
}
function MonitorLabel() { return <MessageSquare size={13} /> }

export function Analytics() {
  return getAccessToken() ? <AuthenticatedFeedbackAnalysis section="analytics" /> : <PreviewAnalytics />
}

function PreviewAnalytics() {
  const { reviews, selector, summary } = useEvidence()
  const averages = ['usability', 'usefulness', 'feasibility', 'completeness'] as const
  const support = Math.round((summary.support ?? 0) * 100)
  return <><PageHeading eyebrow="EVIDENCE AT A GLANCE" title="What the feedback is telling you." actions={selector}>A clearer view of this review cycle.</PageHeading><EvidenceNote /><div className="metrics-grid analytics-metrics">{[['Feedback records', summary.count, `${reviews.filter((review) => !review.sample).length} local submissions`], ['Average rating', summary.rating === null ? 'Not available' : `${summary.rating.toFixed(1)}/5`, 'Unweighted mean'], ['Would use', summary.support === null ? 'Not available' : `${support}%`, 'Raw reviewer response'], ['Analysis status', 'Preview mode', 'Sign in for full intelligence']].map(([label, value, detail]) => <div className="metric" key={label}><div className="metric-top">{label}</div><strong className={typeof value === 'string' && value.length > 5 ? 'metric-text' : ''}>{value}</strong><p>{detail}</p></div>)}</div>
    {reviews.length ? <div className="chart-grid"><section><SectionHeading title="Experience ratings" /><p className="chart-description">Average score by dimension · out of 5</p><div className="chart-container"><Bar data={{ labels: ['Usability', 'Usefulness', 'Feasibility', 'Completeness'], datasets: [{ label: 'Average score', data: averages.map((key) => reviews.reduce((total, review) => total + review[key], 0) / reviews.length), backgroundColor: ['#7dac91', '#9bb8ce', '#d8bea4', '#a9bdaa'], borderRadius: 4, barThickness: 36 }] }} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 5, ticks: { stepSize: 1 }, grid: { color: '#edf2ee' }, border: { display: false } }, x: { grid: { display: false }, border: { display: false } } } }} /></div></section><section><SectionHeading title="Would reviewers use it?" /><p className="chart-description">Direct responses, without trust weighting</p><div className="donut-container"><Doughnut data={{ labels: ['Yes', 'Not yet'], datasets: [{ data: [reviews.filter((review) => review.wouldUse).length, reviews.filter((review) => !review.wouldUse).length], backgroundColor: ['#76a78a', '#eadfd2'], borderWidth: 0, hoverOffset: 4 }] }} options={{ responsive: true, maintainAspectRatio: false, cutout: '76%', plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 23 } } } }} /></div></section></div> : <Empty title="Analytics need feedback"><p>No ratings or support values are available for this idea.</p></Empty>}
    <div className="section-space"><SectionHeading title="Next analytical layers" /><div className="pending-grid">{[{ title: 'Semantic themes', detail: 'Automated grouping of recurring strengths and concerns', icon: MessageSquare }, { title: 'Trust distribution', detail: 'Evidence-weighted review quality assessment', icon: ShieldCheck }, { title: 'Priority matrix', detail: 'Evidence-linked feature ranking', icon: GitBranch }].map(({ title, detail, icon: Icon }) => <div key={title}><Icon size={22} /><h3>{title}</h3><p>{detail}</p><Badge>Available when signed in</Badge></div>)}</div></div>
  </>
}

export function Trust() {
  return getAccessToken() ? <AuthenticatedFeedbackAnalysis section="trust" /> : <PreviewTrust />
}

function PreviewTrust() {
  const { selector, reviews } = useEvidence()
  const [tab, setTab] = useState('Trust factors')
  const factors = [['Review quality', '30%', 'Evidence-backed quality signals'], ['Historical accuracy', '20%', 'Outcomes across previous review cycles'], ['Peer alignment', '15%', 'Independent agreement, with diversity safeguards'], ['Consistency', '15%', 'Stable evidence across review history'], ['Verified expertise', '10%', 'Verified, domain-relevant experience'], ['Community validation', '10%', 'Auditable community assessments']]
  return <><PageHeading eyebrow="TRUST & QUALITY" title="Confidence needs a clear foundation." actions={selector}>Transparent factors. Traceable evidence. No arbitrary scores.</PageHeading><div className="notice"><ShieldCheck size={22} /><div><strong>Preview mode trust overview</strong><p>Sign in and run feedback analysis to compute review quality and partial trust indicators. Quality indicators never claim a person or review is fake.</p></div></div><div className="tabs" role="tablist">{['Trust factors', 'Feedback quality'].map((value) => <button role="tab" aria-selected={tab === value} key={value} onClick={() => setTab(value)}>{value}</button>)}</div>
    {tab === 'Trust factors' ? <><div className="formula-banner"><LockKeyhole size={23} /><div><h3>Deterministic by design</h3><p>Trust = the weighted sum of six evidence factors, each normalized to [0, 1].</p></div><Badge>Transparent model</Badge></div><div className="table-scroll"><table><thead><tr><th>Factor</th><th>Weight</th><th>Evidence requirement</th><th>Status</th></tr></thead><tbody>{factors.map(([name, weight, description]) => <tr key={name}><td><strong>{name}</strong></td><td>{weight}</td><td>{description}</td><td><Badge>Standard factor</Badge></td></tr>)}</tbody></table></div></> : <><SectionHeading title="Review analysis queue" />{reviews.length ? <div className="table-scroll"><table><thead><tr><th>Reviewer</th><th>Evidence source</th><th>Quality / authenticity</th><th>Confidence</th></tr></thead><tbody>{reviews.map((review) => <tr key={review.id}><td>{review.reviewer}</td><td>{review.sample ? 'Sample feedback' : 'Local feedback'}</td><td><Badge>Preview only</Badge></td><td>Not available</td></tr>)}</tbody></table></div> : <Empty title="No feedback to analyze" />}<div className="pending-grid section-space">{['Relevance & constructiveness', 'Originality & consistency', 'Spam & bias risk indicators'].map((title) => <div key={title}><ShieldCheck size={20} /><h3>{title}</h3><p>Automated review quality assessment</p><Badge>Available when signed in</Badge></div>)}</div></>}
  </>
}

export function Consensus() {
  return getAccessToken() ? <AuthenticatedFeedbackAnalysis section="consensus" /> : <PreviewConsensus />
}

function PreviewConsensus() {
  const { idea, reviews, summary, selector } = useEvidence()
  const yes = reviews.filter((review) => review.wouldUse).length
  return <><PageHeading eyebrow="COLLECTIVE PERSPECTIVE" title="Agreement, with the evidence attached." actions={selector}>Keep raw feedback and trust-weighted conclusions separate.</PageHeading><EvidenceNote /><div className="consensus-columns"><section className="consensus-result"><Badge tone="green">Raw support</Badge><strong>{summary.support === null ? 'Not available' : `${Math.round(summary.support * 100)}%`}</strong><p>{yes} of {reviews.length} reviewers would use this prototype.</p><div className="support-track"><span style={{ width: `${(summary.support ?? 0) * 100}%` }} /></div><small>Unweighted · sample + local responses</small></section><section className="consensus-result pending"><Badge>Trust-weighted support</Badge><ShieldCheck size={29} /><h3>Awaiting trust analysis</h3><p>Reviewer trust × authenticity × relevance, normalized before aggregation.</p><small>Sign in and analyze submitted reviews to view weighted support.</small></section></div><SectionHeading title="Supporting evidence" />{reviews.length ? <div className="table-scroll"><table><thead><tr><th>Reviewer</th><th>Would use</th><th>Rating</th><th>Evidence</th><th>Source</th></tr></thead><tbody>{reviews.map((review) => <tr key={review.id}><td>{review.reviewer}</td><td><Badge tone={review.wouldUse ? 'green' : 'coral'}>{review.wouldUse ? 'Yes' : 'Not yet'}</Badge></td><td>{review.rating}/5</td><td><Link className="text-link" to={`/feedback?idea=${idea.id}#${review.id}`}>Read review<ArrowUpRight size={13} /></Link></td><td>{review.sample ? 'Sample' : 'Local'}</td></tr>)}</tbody></table></div> : <Empty title="No evidence available" />}</>
}

export function Evolution() {
  return getAccessToken() ? <AuthenticatedEvolution /> : <PreviewEvolution />
}

function AuthenticatedEvolution() {
  const [params, setParams] = useSearchParams()
  const [ideas, setIdeas] = useState<{ id: string; title: string; version: number }[]>([])
  const [proposal, setProposal] = useState<EvolutionProposal | null>(null)
  const [selectedRanks, setSelectedRanks] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const selectedIdeaId = params.get('idea') ?? ''
  const idea = ideas.find((item) => item.id === selectedIdeaId)

  useEffect(() => {
    let active = true
    listIdeas()
      .then((page) => {
        if (!active) return
        setIdeas(page.items.map(({ id, title, version }) => ({ id, title, version })))
        if (!selectedIdeaId && page.items[0]) setParams({ idea: page.items[0].id })
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Ideas could not be loaded.'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [selectedIdeaId, setParams])

  useEffect(() => {
    if (!idea) {
      setProposal(null)
      return
    }
    let active = true
    setLoading(true)
    getEvolutionProposal(idea.id, idea.version)
      .then((result) => {
        if (!active) return
        setProposal(result)
        setSelectedRanks([])
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'The proposal could not be loaded.'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [idea])

  async function createProposal() {
    if (!idea) return
    setWorking(true)
    setError('')
    try {
      setProposal(await createEvolutionProposal(idea.id, idea.version))
      setSelectedRanks([])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'A proposal could not be created.')
    } finally {
      setWorking(false)
    }
  }

  async function approveProposal() {
    if (!idea || !proposal || !selectedRanks.length) return
    setWorking(true)
    setError('')
    try {
      const approved = await approveEvolutionProposal(idea.id, idea.version, proposal.id, selectedRanks)
      setProposal(approved)
      setIdeas((current) => current.map((entry) => entry.id === idea.id ? { ...entry, version: entry.version + 1 } : entry))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The selected changes could not be approved.')
    } finally {
      setWorking(false)
    }
  }

  const selector = <select
    className="idea-selector"
    aria-label="Select idea"
    value={selectedIdeaId}
    onChange={(event) => setParams({ idea: event.target.value })}
  >
    {ideas.map((item) => <option key={item.id} value={item.id}>{item.title} · V{item.version}</option>)}
  </select>

  return <>
    <PageHeading eyebrow="IDEA EVOLUTION" title="A next version with a reason behind it." actions={selector}>
      Suggestions are grounded in submitted reviewer evidence. Only owner approval creates a new immutable version.
    </PageHeading>
    {error && <ErrorBanner message={error} onRetry={createProposal} />}
    {loading ? <LoadingState title="Loading evolution proposals…" detail="Checking version history and candidate improvements." /> : !idea
      ? <Empty title="No ideas available" />
      : !proposal
        ? <section className="notice">
          <GitBranch size={20} />
          <div>
            <strong>Evidence-based evolution proposal</strong>
            <p>Generating a proposal requires completed requirements and analyzed reviewer feedback for V{idea.version}.</p>
            <button className="button primary" disabled={working} onClick={() => void createProposal()}>
              {working ? 'Preparing proposal…' : 'Generate change proposal'}
            </button>
          </div>
        </section>
        : <>
          <div className="notice">
            <Info size={18} />
            <div>
              <strong>{proposal.status === 'approved' ? 'Owner-approved candidate version' : 'Proposed improvements — awaiting owner approval'}</strong>
              <p>Derived from V{proposal.source_version} across {proposal.source_feedback_ids.length} submitted review{proposal.source_feedback_ids.length === 1 ? '' : 's'}. Original versions remain immutable.</p>
            </div>
          </div>
          <SectionHeading title="Proposed changes and supporting evidence" />
          <div className="priority-list">
            {proposal.suggestions.map((suggestion) => <label key={suggestion.rank}>
              <input
                type="checkbox"
                aria-label={`Approve ${suggestion.title}`}
                disabled={proposal.status !== 'proposed' || !suggestion.builder_supported}
                checked={selectedRanks.includes(suggestion.rank)}
                onChange={() => setSelectedRanks((current) => current.includes(suggestion.rank)
                  ? current.filter((rank) => rank !== suggestion.rank)
                  : [...current, suggestion.rank])}
              />
              <div>
                <div className="requirement-fact-header">
                  <Badge tone="green">{suggestion.priority}</Badge>
                  <Badge tone={suggestion.builder_supported ? 'blue' : 'neutral'}>{suggestion.builder_supported ? 'Prototype ready' : 'Manual scope'}</Badge>
                </div>
                <strong>{suggestion.title}</strong>
                <p>{suggestion.rationale}</p>
                <span>Expected benefit: {suggestion.expected_benefit.qualitative_impact} · Weighted support: {percent(suggestion.expected_benefit.weighted_support)}</span>
                <p>Backed by {suggestion.source_feedback_ids.length} verified review{suggestion.source_feedback_ids.length === 1 ? '' : 's'} · Risks: {suggestion.risks.length ? suggestion.risks.map((risk) => risk.concern).join(' · ') : 'No separate reviewer concern cited.'}</p>
              </div>
            </label>)}
          </div>
          {proposal.status === 'proposed'
            ? <div className="form-actions section-space">
              <button className="button primary" disabled={working || !selectedRanks.length} onClick={() => void approveProposal()}>
                {working ? 'Creating immutable candidate…' : `Approve ${selectedRanks.length} selected change${selectedRanks.length === 1 ? '' : 's'}`}
              </button>
              <Link className="button" to={`/reports?idea=${idea.id}`}>Skip to Decision Report<ArrowRight size={15} /></Link>
            </div>
            : <>
              <div className="notice">
                <Check size={18} />
                <div>
                  <strong>Candidate V{String(proposal.validation_results.target_version ?? idea.version)} saved to version history</strong>
                  <p>Approved improvements have been recorded as a new immutable version while preserving V{proposal.source_version}.</p>
                </div>
              </div>
              <div className="form-actions section-space">
                <Link className="button" to={`/ideas/${idea.id}`}><GitBranch size={15} />Inspect New Immutable Version</Link>
                <Link className="button primary" to={`/reports?idea=${idea.id}`}><FileText size={15} />Open Decision Intelligence Report<ArrowRight size={15} /></Link>
              </div>
            </>}
        </>}
  </>
}

function PreviewEvolution() {
  const { idea, selector, state, update } = useEvidence()
  const reviews = rankPriorities(state, idea.id).filter((item) => item.score !== null).map((item) => ({ id: item.id, version: item.version, improvements: item.text, reviewer: item.author, concerns: `${item.priority} · ${item.effort} effort · ${item.rationale}`, sample: state.reviews.find((review) => review.id === item.id)?.sample ?? false }))
  const [selected, setSelected] = useState<string[]>([])
  const evolution = state.evolutions.find((entry) => entry.ideaId === idea.id && entry.source === idea.version)
  const evidence = selected.filter((id) => reviews.some((review) => review.id === id && review.version === idea.version))
  return <><PageHeading eyebrow="IDEA EVOLUTION" title="A next version with a reason behind it." actions={selector}>Preserve the original. Make every proposed change traceable.</PageHeading><div className="evolution-path">{['V1 prototype', 'Comments & feedback', 'Prioritized proposal', 'Validated V2'].map((label, index) => <div className={index === 2 && evolution ? 'current' : ''} key={label}><span>{index < 2 ? <Check size={15} /> : index + 1}</span>{label}{index < 3 && <ArrowRight size={16} />}</div>)}</div><div className="notice"><GitBranch size={20} /><div><strong>Feasibility-aware, evidence-linked proposal</strong><p>Assess effort and impact first, then choose changes below. Questions and blockers stay out of the build plan.</p></div></div>
    {evolution ? <PrioritySnapshot evolution={evolution} /> : <PriorityBoard key={idea.id} idea={idea} />}
    {evolution ? <><div className="version-comparison"><section><Badge tone="green">V{idea.version} / Preserved</Badge><h2>{idea.title}</h2><p>{idea.solution}</p><h3>Original scope</h3><ul>{idea.features.map((feature) => <li key={feature}><Check size={14} />{feature}</li>)}</ul><Link className="button" to={`/ideas/${idea.id}/prototype`}>Open original prototype<ArrowUpRight size={14} /></Link></section><section><Badge tone="blue">V{evolution.target} / Proposal</Badge><h2>Evidence-led changes</h2><p>{evolution.changes.length} proposed improvements · {dateLabel(evolution.created)}</p><ul>{evolution.changes.map((change, index) => <li key={`${index}-${change}`}><span className="change-marker">+</span><div>{change}<Link to={`/feedback?idea=${idea.id}#${evolution.evidence[index]}`} className="text-link">Source evidence<ArrowUpRight size={12} /></Link></div></li>)}</ul><Badge>Candidate V2</Badge></section></div><div className="form-actions section-space"><button className="button" onClick={() => downloadFile(`${idea.id}-v${evolution.target}-proposal.json`, JSON.stringify({ ...evolution, source: 'frontend-preview', ai_generated: false }, null, 2), 'application/json')}><Download size={15} />Export change proposal</button><Link className="button primary" to={`/reports?idea=${idea.id}`}>View decision report<ArrowRight size={15} /></Link></div></> : <><SectionHeading title="Choose feedback to carry forward" />{reviews.length ? <div className="priority-list">{reviews.map((review) => <label key={review.id}><input type="checkbox" checked={evidence.includes(review.id)} onChange={() => setSelected(evidence.includes(review.id) ? evidence.filter((id) => id !== review.id) : [...evidence, review.id])} /><div><strong>{review.improvements}</strong><p>{review.reviewer} · V{review.version} · {review.sample ? 'Sample' : 'Local'} evidence</p><span>{review.concerns}</span></div><Link aria-label={`Read evidence from ${review.reviewer}`} title="Read source evidence" to={`/feedback?idea=${idea.id}#${review.id}`}><ArrowUpRight size={17} /></Link></label>)}</div> : <Empty title="Feedback comes first"><p>A version proposal needs evidence from this idea.</p></Empty>}<div className="form-actions section-space"><span className="muted">{evidence.length} suggestions selected</span><button disabled={!evidence.length} className="button primary" onClick={() => update((current) => proposeEvolution(current, idea.id, evidence), 'Change proposal created. The original version is preserved.')}><GitBranch size={16} />Create change proposal</button></div></>}
  </>
}

export function Reports() {
  return getAccessToken() ? <AuthenticatedReports /> : <PreviewReports />
}

function AuthenticatedReports() {
  const [params, setParams] = useSearchParams()
  const [ideas, setIdeas] = useState<{ id: string; title: string; version: number }[]>([])
  const [report, setReport] = useState<DecisionReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const ideaId = params.get('idea') ?? ''
  const idea = ideas.find((item) => item.id === ideaId)
  useEffect(() => {
    let active = true
    listIdeas()
      .then((page) => {
        if (!active) return
        setIdeas(page.items.map(({ id, title, version }) => ({ id, title, version })))
        if (!ideaId && page.items[0]) setParams({ idea: page.items[0].id })
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Ideas could not be loaded.'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [ideaId, setParams])
  useEffect(() => {
    if (!idea) {
      setReport(null)
      return
    }
    let active = true
    setLoading(true)
    getLatestDecisionReport(idea.id, idea.version)
      .then((result) => active && setReport(result))
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'The report could not be loaded.'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [idea])
  async function generateReport() {
    if (!idea) return
    setWorking(true)
    setError('')
    try {
      setReport(await createDecisionReport(idea.id, idea.version))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'A report snapshot could not be created.')
    } finally {
      setWorking(false)
    }
  }
  const selector = <select className="idea-selector" aria-label="Select idea" value={ideaId} onChange={(event) => setParams({ idea: event.target.value })}>
    {ideas.map((item) => <option key={item.id} value={item.id}>{item.title} · V{item.version}</option>)}
  </select>
  const reportData = report?.report as Record<string, unknown> | undefined
  const docIdea = (reportData?.idea ?? reportData?.idea_summary ?? {}) as Record<string, unknown>
  const problemSummaryObj = (docIdea.problem_summary ?? {}) as Record<string, unknown>
  const docReviews = (reportData?.reviews ?? {}) as Record<string, unknown>
  const docConsensusWrapper = (docReviews.consensus ?? {}) as Record<string, unknown>
  const docThemesWrapper = (docReviews.themes ?? {}) as Record<string, unknown>
  const docPrioritiesWrapper = (reportData?.prioritized_improvements ?? {}) as Record<string, unknown>
  const docV1ToV2 = (reportData?.v1_to_v2_changes ?? {}) as Record<string, unknown>
  const feedbackAnalysis = (reportData?.feedback_analysis ?? {}) as Record<string, unknown>
  const consensus = ((docConsensusWrapper.value ?? feedbackAnalysis?.consensus) ?? {}) as Record<string, unknown>
  const themes = Array.isArray(docThemesWrapper.items)
    ? (docThemesWrapper.items as Record<string, unknown>[])
    : Array.isArray(feedbackAnalysis?.themes)
      ? (feedbackAnalysis.themes as Record<string, unknown>[])
      : []
  const priorities = Array.isArray(docPrioritiesWrapper.items)
    ? (docPrioritiesWrapper.items as Record<string, unknown>[])
    : Array.isArray(feedbackAnalysis?.priorities)
      ? (feedbackAnalysis.priorities as Record<string, unknown>[])
      : []
  const approvedChanges = Array.isArray(docV1ToV2.changes) ? (docV1ToV2.changes as string[]) : []
  const nextSteps = Array.isArray(reportData?.recommended_next_steps) ? (reportData.recommended_next_steps as string[]) : []
  const versionHistory = Array.isArray(reportData?.version_history) ? (reportData.version_history as Record<string, unknown>[]) : []

  function exportReportJson() {
    if (!report || !idea) return
    downloadFile(`${idea.title.toLowerCase().replace(/\s+/g, '-')}-v${report.source_version}-report.json`, JSON.stringify(report.report, null, 2), 'application/json')
  }

  return <>
    <PageHeading eyebrow="DECISION INTELLIGENCE" title="A traceable record of what the evidence supports." actions={selector}>
      Decision report snapshots summarize requirements, verified reviewer feedback, consensus, and prioritized next steps.
    </PageHeading>
    {error && <ErrorBanner message={error} onRetry={generateReport} />}
    {loading ? <LoadingState title="Loading decision report…" detail="Assembling version history, consensus metrics, and improvement priorities." /> : !idea
      ? <Empty title="No ideas available" />
      : <>
        <div className="report-toolbar">
          <div className="requirement-status-group">
            <Status value={report ? 'Report ready' : 'Awaiting report'} />
            {report && <span className="muted">Created {dateLabel(report.created_at)}</span>}
          </div>
          <div>
            {report && <button className="button" onClick={() => window.print()}><Printer size={15} />Print</button>}
            {report && <button className="button" onClick={exportReportJson}><Download size={15} />Export report</button>}
            <button className="button primary" disabled={working} onClick={() => void generateReport()}>
              {working ? 'Generating report…' : report ? 'Refresh report snapshot' : 'Create report snapshot'}
            </button>
          </div>
        </div>
        {report && reportData
          ? <>
            <section className="report-cover">
              <div>
                <span className="eyebrow">DECISION INTELLIGENCE REPORT · VERSION {report.source_version}</span>
                <h2>{String(docIdea.title ?? idea.title)}</h2>
                <p>{String(docIdea.solution ?? problemSummaryObj.value ?? docIdea.problem ?? '')}</p>
              </div>
              <FileCheck2 size={40} strokeWidth={1.1} />
            </section>
            <div className="report-summary">
              <div><small>Source version</small><strong>Version {report.source_version}</strong></div>
              <div><small>Verified reviews</small><strong>{report.source_feedback_ids.length} submitted review{report.source_feedback_ids.length === 1 ? '' : 's'}</strong></div>
              <div><small>Trust-weighted support</small><strong>{typeof consensus.weighted_support === 'number' ? percent(consensus.weighted_support) : 'Available in snapshot'}</strong></div>
            </div>
            <div className="report-columns">
              <section>
                <SectionHeading title="Key themes from reviewers" />
                {themes.length ? <ul className="analysis-evidence-list">{themes.map((theme, idx) => <li key={idx}>
                  <Badge tone={theme.kind === 'positive' || theme.kind === 'praise' ? 'green' : theme.kind === 'complaint' || theme.kind === 'concern' ? 'coral' : 'blue'}>{formatFactorLabel(String(theme.kind ?? 'theme'))}</Badge>
                  <strong>{String(theme.label ?? '')}</strong>
                  <p>{String(theme.summary ?? '')}</p>
                </li>)}</ul> : <p className="muted">No recurring themes recorded in this snapshot.</p>}
              </section>
              <section>
                <SectionHeading title="Recommended priorities" />
                {priorities.length ? <ul className="analysis-evidence-list">{priorities.map((priority, idx) => <li key={idx}>
                  <Badge tone="blue">{String(priority.priority ?? 'Priority')}</Badge>
                  <strong>{String(priority.title ?? '')}</strong>
                  <p>{String(priority.rationale ?? '')}</p>
                </li>)}</ul> : <p className="muted">No prioritized improvements recorded in this snapshot.</p>}
              </section>
            </div>
            {(approvedChanges.length > 0 || nextSteps.length > 0) && <div className="report-columns section-space">
              {approvedChanges.length > 0 && <section>
                <SectionHeading title="Approved candidate changes" />
                <ul className="analysis-evidence-list">{approvedChanges.map((change, idx) => <li key={idx}>
                  <Badge tone="green">Approved for V{report.source_version + 1}</Badge>
                  <strong>{change}</strong>
                </li>)}</ul>
              </section>}
              {nextSteps.length > 0 && <section>
                <SectionHeading title="Recommended next steps" />
                <ul className="analysis-evidence-list">{nextSteps.map((step, idx) => <li key={idx}><p>{step}</p></li>)}</ul>
              </section>}
            </div>}
            {versionHistory.length > 0 && <div className="section-space">
              <SectionHeading title="Traceable version lineage" />
              <div className="version-list">
                {versionHistory.map((ver, idx) => <div key={idx}>
                  <div className="version-card-top">
                    <Badge tone={idx === 0 ? 'green' : 'blue'}>V{String(ver.version ?? idx + 1)}</Badge>
                    <Status value={String(ver.status ?? 'Draft')} />
                  </div>
                  <h3>{String(ver.title ?? idea.title)}</h3>
                  <small>Immutable version record</small>
                </div>)}
              </div>
            </div>}
          </>
          : <Empty title="No decision report snapshot for this version yet"><p>Generate a report snapshot to capture your requirements, reviewer consensus, and version lineage.</p></Empty>}
      </>}
  </>
}

function PreviewReports() {
  const { idea, reviews, summary, selector, state } = useEvidence()
  const proposal = state.evolutions.find((entry) => entry.ideaId === idea.id)
  function exportReport() {
    const report = [`# ${idea.title} - Preview decision report`, '', 'Source: sample and local feedback. Not an AI validation result.', `Version: ${idea.version}`, `Detailed feedback records: ${reviews.length}`, `Raw average rating: ${summary.rating?.toFixed(2) ?? 'Unavailable'}`, `Raw support: ${summary.support === null ? 'Unavailable' : `${Math.round(summary.support * 100)}%`}`, 'Trust-weighted consensus: Available when signed in.', '', '## Review evidence', ...reviews.map((review) => `- ${review.id} (${review.sample ? 'Sample' : 'Local'}): ${review.improvements}`), '', '## Comment evidence', ...state.comments.filter((comment) => comment.ideaId === idea.id && comment.version === idea.version).map((comment) => `- ${comment.id} (Local ${comment.kind}): ${comment.text} Context: ${comment.context}`), '', '## Change proposal', ...(proposal?.changes.map((change, index) => `- ${proposal.priorities?.[index]?.priority ?? 'Unranked'}: ${change} [evidence: ${proposal.evidence[index]}]`) ?? ['No change proposal created.']), ...(proposal?.priorities?.map((item) => `  ${item.evidenceId}: ${item.rationale}`) ?? []), '', '## Next steps', 'Collect authenticated reviewer evidence before making a production decision.'].join('\n')
    downloadFile(`${idea.id}-preview-report.md`, report, 'text/markdown')
  }
  return <><PageHeading eyebrow="DECISION INTELLIGENCE" title="A clear record of what comes next." actions={selector}>Findings, open questions, and the feedback behind them.</PageHeading><div className="report-toolbar"><Badge tone="coral">Preview report</Badge><div><button className="button" onClick={() => window.print()}><Printer size={15} />Print</button><button className="button primary" onClick={exportReport}><Download size={15} />Export report</button></div></div><section className="report-cover"><div><span className="eyebrow">VALIDATION REVIEW / V{idea.version}</span><h2>{idea.title}</h2><p>{idea.solution}</p></div><FileCheck2 size={40} strokeWidth={1.1} /></section><div className="report-summary"><div><small>Evidence coverage</small><strong>{reviews.length} feedback records</strong></div><div><small>Decision status</small><strong>Further validation needed</strong></div><div><small>Trust coverage</small><strong>Preview mode</strong></div></div><div className="report-columns"><section><SectionHeading title="Reported strengths" />{reviews.length ? reviews.map((review) => <Link key={review.id} to={`/feedback?idea=${idea.id}#${review.id}`} className="report-evidence"><Check size={16} /><p>{review.strengths}<small>{review.reviewer} · {review.sample ? 'Sample' : 'Local'}</small></p><ArrowUpRight size={14} /></Link>) : <p className="muted">No evidence yet.</p>}</section><section><SectionHeading title="Open concerns" />{reviews.length ? reviews.map((review) => <Link key={review.id} to={`/feedback?idea=${idea.id}#${review.id}`} className="report-evidence concern"><Info size={16} /><p>{review.concerns}<small>{review.reviewer} · {review.sample ? 'Sample' : 'Local'}</small></p><ArrowUpRight size={14} /></Link>) : <p className="muted">No evidence yet.</p>}</section></div><div className="report-next"><div><FileText size={23} /><h3>{proposal ? 'A proposal is ready for validation.' : 'Keep the next decision grounded.'}</h3><p>{proposal ? `${proposal.changes.length} evidence-linked changes proposed. V1 is preserved.` : 'Collect more reviewer evidence, evaluate trust factors, and validate changes before drawing a production conclusion.'}</p></div><Link className="button" to={`/evolution?idea=${idea.id}`}>{proposal ? 'View proposal' : 'Explore improvements'}<ArrowRight size={15} /></Link></div></>
}
