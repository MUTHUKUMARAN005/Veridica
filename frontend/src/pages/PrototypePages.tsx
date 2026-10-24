import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { useForm } from 'react-hook-form'
import { ArrowLeft, ArrowRight, Bookmark, Check, CheckCheck, CheckCircle2, ChevronRight, Code2, FileText, GraduationCap, LayoutDashboard, Leaf, ListChecks, MapPin, Monitor, Play, Search, Send, ShieldCheck, Smartphone, Star, Target } from 'lucide-react'
import { SchemaPrototypePreview } from '@/components/SchemaPrototypePreview'
import { addReview } from '@/services/preview'
import type { Idea, Review } from '@/services/preview'
import { useWorkspace } from '@/services/workspace'
import { Badge, Empty, ErrorBanner, LoadingState, Modal, PageHeading, Status } from '@/components/ui'
import { IdeaDiscussion } from '@/components/IdeaDiscussion'
import { getAccessToken } from '@/services/auth'
import { getIdea, getLatestPrototypeSource } from '@/services/ideas'
import type { ApiIdeaDetail, PrototypeBuild } from '@/services/ideas'
import { getReviewerAssignment, getReviewerPrototypePreview, startReviewerSession, submitReviewerReview } from '@/services/authorization'
import type { ApiReview, ReviewerAssignment, ReviewerPrototypePreview, ReviewSubmission } from '@/services/authorization'

const jobs = [
  { id: 'orbit', company: 'Orbit Labs', title: 'Frontend engineering intern', field: 'Engineering', location: 'Bengaluru · Hybrid', color: 'green', skills: 'React · TypeScript · Accessible UI', description: 'Build and test accessible interfaces alongside a product team. This is a fictional opportunity for prototype testing.' },
  { id: 'forma', company: 'Forma Studio', title: 'Product design intern', field: 'Design', location: 'Remote', color: 'coral', skills: 'Figma · Research · Interaction design', description: 'Explore user needs and translate research into thoughtful product experiences. This is a fictional opportunity.' },
  { id: 'nova', company: 'Nova Systems', title: 'Software engineering intern', field: 'Engineering', location: 'Hyderabad · On-site', color: 'blue', skills: 'Python · SQL · Problem solving', description: 'Work on data-backed product features and learn engineering practices. No external application is submitted in this preview.' },
]
const resumeTasks = ['Add contact details and portfolio', 'Describe two projects with outcomes', 'List relevant technical skills', 'Check formatting and spelling']
const roadmapTasks = ['Review your target role', 'Practice core problem solving', 'Prepare a project walkthrough', 'Complete a mock interview']

export function PrototypeDemo({ idea, onInteraction = () => undefined, proposed = false }: { idea: Idea; onInteraction?: () => void; proposed?: boolean }) {
  const [screen, setScreen] = useState('Dashboard')
  const [query, setQuery] = useState('')
  const [field, setField] = useState('All roles')
  const [saved, setSaved] = useState<string[]>([])
  const [resume, setResume] = useState<string[]>([])
  const [roadmap, setRoadmap] = useState<string[]>([])
  const [selected, setSelected] = useState<(typeof jobs)[number] | null>(null)
  const [requests, setRequests] = useState<{ text: string; type: string }[]>([])
  const [request, setRequest] = useState('')
  const [requestType, setRequestType] = useState('Missed collection')
  const [day, setDay] = useState('Wednesday')
  function toggle(value: string, collection: string[], setter: (values: string[]) => void) { setter(collection.includes(value) ? collection.filter((entry) => entry !== value) : [...collection, value]); onInteraction() }
  if (idea.id === 'circular') return <div className="demo city-demo"><header className="demo-header"><div><Leaf size={22} /><strong>Circular City</strong></div><Badge tone="blue">Sample prototype</Badge></header><div className="city-content"><div className="demo-welcome"><span className="eyebrow">YOUR NEIGHBORHOOD</span><h2>A cleaner block starts here.</h2><p>Riverside neighborhood · Sample location</p></div><div className="city-columns"><form className="demo-request" onSubmit={(event) => { event.preventDefault(); setRequests([...requests, { text: request, type: requestType }]); setRequest(''); onInteraction() }}><h3>Report a collection issue</h3><label>Issue type<select value={requestType} onChange={(event) => setRequestType(event.target.value)}><option>Missed collection</option><option>Overflowing bin</option><option>Recycling question</option></select></label><label>Location and details<textarea required minLength={10} value={request} onChange={(event) => setRequest(event.target.value)} placeholder="Street, landmark, and what happened" /></label><button className="button primary">Submit sample request<ArrowRight size={14} /></button></form><div className="collection"><Leaf size={32} /><h3>Collection preference</h3><label>Preferred day<select value={day} onChange={(event) => { setDay(event.target.value); onInteraction() }}>{['Monday', 'Wednesday', 'Friday'].map((value) => <option key={value}>{value}</option>)}</select></label><p>{day} · 8:00 AM to 12:00 PM</p><small>Prototype only. No collection is scheduled.</small></div></div><h3 className="demo-section-title">Your sample requests</h3>{requests.length ? requests.map((entry, index) => <div className="request-row" key={`${entry.text}-${index}`}><CheckCircle2 size={18} /><div><strong>{entry.type}</strong><p>{entry.text}</p></div><Badge tone="green">Recorded locally</Badge></div>) : <p className="muted">No requests in this session.</p>}</div></div>
  const visibleJobs = jobs.filter((job) => (field === 'All roles' || job.field === field) && `${job.title} ${job.company} ${job.skills}`.toLowerCase().includes(query.toLowerCase()))
  const choices = [{ name: 'Dashboard', icon: LayoutDashboard }, { name: 'Opportunities', icon: Search }, { name: 'Resume', icon: FileText }, { name: 'Roadmap', icon: Target }]
  const jobCards = (collection: typeof jobs) => collection.map((job) => <article className="job-card" key={job.id}><div className="job-top"><span className={`company-logo ${job.color}`}>{job.company[0]}</span><button className="icon-button" title={saved.includes(job.id) ? `Unsave ${job.company}` : `Save ${job.company}`} aria-label={saved.includes(job.id) ? `Unsave ${job.company}` : `Save ${job.company}`} aria-pressed={saved.includes(job.id)} onClick={() => toggle(job.id, saved, setSaved)}><Bookmark size={17} fill={saved.includes(job.id) ? 'currentColor' : 'none'} /></button></div><small>{job.company}</small><h3>{job.title}</h3><p><MapPin size={12} />{job.location}</p><div className="job-skills">{job.skills}</div><button className="text-link" onClick={() => { setSelected(job); onInteraction() }}>View opportunity<ArrowRight size={13} /></button></article>)
  return <div className="demo campus-demo"><header className="demo-header"><div><GraduationCap size={23} /><strong>Campus Compass</strong></div><Badge tone="green">{proposed ? 'Proposed UI preview' : 'Sample prototype'}</Badge><span className="avatar small">AS</span></header><nav className="demo-tabs" aria-label="Prototype screens">{choices.map(({ name, icon: Icon }) => <button className={screen === name ? 'selected' : ''} key={name} onClick={() => { setScreen(name); onInteraction() }}><Icon size={15} />{name}</button>)}</nav><div className="demo-content">
    <div className="demo-welcome"><span className="eyebrow">{screen === 'Dashboard' ? 'YOUR NEXT CHAPTER' : 'YOUR PLACEMENT WORKSPACE'}</span><h2>{screen === 'Dashboard' ? 'Good things are ahead, Alex.' : screen === 'Opportunities' ? 'Find a role worth getting ready for.' : screen === 'Resume' ? 'Make your experience count.' : 'One step closer to ready.'}</h2><p>{screen === 'Dashboard' ? 'A little preparation today. A world of possibilities tomorrow.' : 'Sample experience · No external integrations'}</p></div>
    {screen === 'Dashboard' && <><div className="demo-stats"><div><Bookmark size={19} /><strong>{saved.length}</strong><span>Saved opportunities</span></div><div><FileText size={19} /><strong>{resume.length}/{resumeTasks.length}</strong><span>Resume checks complete</span></div><div><Target size={19} /><strong>{roadmap.length}/{roadmapTasks.length}</strong><span>Roadmap steps complete</span></div></div><div className="demo-section-heading"><h3>Explore opportunities</h3><button className="text-link" onClick={() => { setScreen('Opportunities'); onInteraction() }}>View all<ArrowRight size={13} /></button></div><div className="job-grid">{jobCards(jobs.slice(0, 2))}</div></>}
    {screen === 'Opportunities' && <><div className="demo-filters"><label className="search-field"><Search size={15} /><input aria-label="Search opportunities" value={query} onChange={(event) => { setQuery(event.target.value); onInteraction() }} placeholder="Role, company, or skill" /></label><select aria-label="Opportunity category" value={field} onChange={(event) => { setField(event.target.value); onInteraction() }}><option>All roles</option><option>Engineering</option><option>Design</option></select></div><div className="job-grid">{jobCards(visibleJobs)}</div>{!visibleJobs.length && <Empty title="No matching opportunities" />}</>}
    {(screen === 'Resume' || screen === 'Roadmap') && <div className="demo-checklist"><div className="checklist-intro">{screen === 'Resume' ? <FileText size={24} /> : <Target size={24} />}<div><h3>{screen === 'Resume' ? 'Resume readiness checklist' : 'Your preparation roadmap'}</h3><p>{screen === 'Resume' ? 'Self-check only. No resume is uploaded or analyzed.' : `${roadmap.length} of ${roadmapTasks.length} steps completed`}</p></div></div>{screen === 'Roadmap' && <progress aria-label="Roadmap completion" value={roadmap.length} max={roadmapTasks.length} />}{(screen === 'Resume' ? resumeTasks : roadmapTasks).map((task) => <label key={task}><input type="checkbox" checked={(screen === 'Resume' ? resume : roadmap).includes(task)} onChange={() => toggle(task, screen === 'Resume' ? resume : roadmap, screen === 'Resume' ? setResume : setRoadmap)} /><span>{task}</span><ChevronRight size={14} /></label>)}</div>}
  </div>{selected && <Modal title={selected.title} onClose={() => setSelected(null)}><Badge tone="green">{selected.company}</Badge><p>{selected.location}</p><p>{selected.description}</p><h3>Relevant skills</h3><p>{selected.skills}</p><button className="button primary" onClick={() => toggle(selected.id, saved, setSaved)}><Bookmark size={15} />{saved.includes(selected.id) ? 'Remove from saved' : 'Save opportunity'}</button></Modal>}</div>
}

export function PrototypeWorkspace() {
  const { id } = useParams()
  const { state } = useWorkspace()
  const [size, setSize] = useState('desktop')
  const [tab, setTab] = useState('Prototype')
  const [apiIdea, setApiIdea] = useState<ApiIdeaDetail | null>(null)
  const [apiBuild, setApiBuild] = useState<PrototypeBuild | null>(null)
  const [loading, setLoading] = useState(Boolean(getAccessToken()))
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id || !getAccessToken()) return
    let active = true
    setLoading(true)
    getIdea(id)
      .then(async (ideaDetail) => {
        if (!active) return
        setApiIdea(ideaDetail)
        const latestBuild = await getLatestPrototypeSource(ideaDetail.id, ideaDetail.version).catch(() => null)
        if (active) setApiBuild(latestBuild)
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Prototype workspace could not be loaded.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [id])

  if (getAccessToken()) {
    if (loading) return <LoadingState title="Loading prototype workspace…" detail="Preparing your interactive prototype preview." />
    if (error || !apiIdea) return <Empty title="Prototype unavailable">{error && <ErrorBanner message={error} />}<Link className="button" to="/ideas">Back to ideas</Link></Empty>
    return <>
      <Link className="back-link" to={`/ideas/${apiIdea.id}`}><ArrowLeft size={15} />{apiIdea.title}</Link>
      <PageHeading eyebrow="PROTOTYPE WORKSPACE" title={apiIdea.title} actions={<Link className="button" to={`/ideas/${apiIdea.id}`}>Idea details<ArrowRight size={15} /></Link>}>
        <span>Version {apiIdea.version} · {apiBuild?.plan ? 'Interactive prototype ready' : 'Awaiting prototype generation'}</span>
      </PageHeading>
      <div className="prototype-toolbar">
        <div className="tabs" role="tablist">
          {['Prototype', 'Feature brief'].map((value) => <button role="tab" aria-selected={tab === value} key={value} onClick={() => setTab(value)}>{value}</button>)}
        </div>
        <div className="segmented" aria-label="Preview size">
          <button aria-label="Desktop preview" title="Desktop preview" aria-pressed={size === 'desktop'} onClick={() => setSize('desktop')}><Monitor size={16} /></button>
          <button aria-label="Mobile preview" title="Mobile preview" aria-pressed={size === 'mobile'} onClick={() => setSize('mobile')}><Smartphone size={16} /></button>
        </div>
      </div>
      {tab === 'Prototype' && (apiBuild?.plan?.preview_spec
        ? <div className={`prototype-stage ${size}`}><SchemaPrototypePreview spec={apiBuild.plan.preview_spec} /></div>
        : <Empty title="Prototype not generated yet"><p>Generate requirements and prepare the interactive prototype from the Requirements tab on your idea details page.</p><Link className="button primary" to={`/ideas/${apiIdea.id}`}>Go to idea details</Link></Empty>)}
      {tab === 'Feature brief' && <div className="prose-section">
        <h2>Prototype scope</h2>
        <p>{apiIdea.solution}</p>
        <div className="feature-grid">{apiIdea.features.map((feature) => <div key={feature}><Check size={15} /><h3>{feature}</h3></div>)}</div>
        <h2>Known constraints</h2>
        <p>{apiIdea.constraints || 'No additional constraints specified.'}</p>
      </div>}
    </>
  }

  const idea = state.ideas.find((candidate) => candidate.id === id)
  if (!idea) return <Empty title="Prototype not found" />
  const available = ['placement', 'circular'].includes(idea.id)
  return <><Link className="back-link" to={`/ideas/${idea.id}`}><ArrowLeft size={15} />{idea.title}</Link><PageHeading eyebrow="PROTOTYPE WORKSPACE" title={idea.title} actions={<Link className="button" to={`/ideas/${idea.id}`}>Idea details<ArrowRight size={15} /></Link>}><span>V{idea.version} · {available ? 'Interactive sample prototype' : 'Awaiting prototype preparation'}</span></PageHeading><div className="prototype-toolbar"><div className="tabs" role="tablist">{['Prototype', 'Feature brief', 'Prototype info'].map((value) => <button role="tab" aria-selected={tab === value} key={value} onClick={() => setTab(value)}>{value}</button>)}</div><div className="segmented" aria-label="Preview size"><button aria-label="Desktop preview" title="Desktop preview" aria-pressed={size === 'desktop'} onClick={() => setSize('desktop')}><Monitor size={16} /></button><button aria-label="Mobile preview" title="Mobile preview" aria-pressed={size === 'mobile'} onClick={() => setSize('mobile')}><Smartphone size={16} /></button></div></div>
    {tab === 'Prototype' && (available ? <div className={`prototype-stage ${size}`}><PrototypeDemo idea={idea} /></div> : <Empty title="No generated prototype yet"><p>Your idea is saved. Generate requirements and prepare a prototype to preview it here.</p><Badge>Prototype pending</Badge></Empty>)}
    {tab === 'Feature brief' && <div className="prose-section"><h2>Prototype scope</h2><p>{idea.solution}</p><div className="feature-grid">{idea.features.map((feature) => <div key={feature}><Check size={15} /><h3>{feature}</h3></div>)}</div><h2>Known limitations</h2><p>{idea.constraints}</p><p>Sample preview interactions reset when the prototype is closed.</p></div>}
    {tab === 'Prototype info' && <><div className="notice"><Code2 size={20} /><div><strong>Controlled interactive preview</strong><p>Reviewers test this version-locked interface so all feedback applies to the same experience.</p></div></div><div className="metadata-grid">{[['Template', available ? idea.id === 'placement' ? 'Education workspace' : 'Neighborhood reporting' : 'Not selected'], ['Source', available ? 'Interactive sample' : 'Owner idea draft'], ['Version', `V${idea.version}`], ['Status', available ? 'Ready for review' : 'Awaiting preparation']].map(([label, value]) => <div key={label}><small>{label}</small><strong>{value}</strong></div>)}</div></>}
  </>
}

type ReviewForm = { rating: string; usability: string; usefulness: string; feasibility: string; completeness: string; wouldUse: string; strengths: string; concerns: string; improvements: string; context: string }
export function ReviewWorkspace() {
  const { id } = useParams()
  return getAccessToken()
    ? <ApiReviewWorkspace assignmentId={id ?? ''} />
    : <PreviewReviewWorkspace />
}

function ApiReviewWorkspace({ assignmentId }: { assignmentId: string }) {
  const [assignment, setAssignment] = useState<ReviewerAssignment | null>(null)
  const [prototypePreview, setPrototypePreview] = useState<ReviewerPrototypePreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [retryingHandoff, setRetryingHandoff] = useState(false)
  const [handoffError, setHandoffError] = useState('')
  const idempotencyKey = useRef<string | null>(null)
  const [form, setForm] = useState({
    rating: 0,
    usability_score: 0,
    usefulness_score: 0,
    completeness_score: 0,
    feasibility_score: 0,
    would_use: null as boolean | null,
    feedback_text: '',
    strengths: '',
    concerns: '',
    suggested_improvements: '',
    usage_context: '',
  })

  useEffect(() => {
    let active = true
    async function loadAssignment() {
      const result = await getReviewerAssignment(assignmentId)
      if (!active) return
      setAssignment(result)
      const savedPrototype = await getReviewerPrototypePreview(assignmentId)
      if (!active) return
      setPrototypePreview(savedPrototype)
      if (!result.review_submitted) {
        const reviewSession = result.review_session ?? await startReviewerSession(assignmentId)
        if (active) {
          setAssignment((current) => current
            ? { ...current, review_session: reviewSession, status: 'in_progress' }
            : current)
        }
      }
    }
    loadAssignment()
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'This assignment could not be loaded.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [assignmentId])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (
      !assignment?.review_session
      || !form.rating
      || !form.usability_score
      || !form.usefulness_score
      || !form.completeness_score
      || !form.feasibility_score
      || form.would_use === null
    ) return
    const wouldUse = form.would_use
    setSubmitting(true)
    setError('')
    idempotencyKey.current ??= crypto.randomUUID()
    try {
      const payload: ReviewSubmission = {
        ...form,
        session_id: assignment.review_session.id,
        would_use: wouldUse,
        feedback_text: form.feedback_text.trim(),
        strengths: form.strengths.trim(),
        concerns: form.concerns.trim(),
        suggested_improvements: form.suggested_improvements.trim(),
        usage_context: form.usage_context.trim(),
      }
      const review = await submitReviewerReview(assignmentId, payload, idempotencyKey.current)
      setAssignment((current) => current
        ? { ...current, review_submitted: true, status: 'submitted', feedback: review }
        : current)
      idempotencyKey.current = null
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Your review could not be submitted.')
    } finally {
      setSubmitting(false)
    }
  }
  async function retrySessionStart() {
    setError('')
    try {
      const reviewSession = await startReviewerSession(assignmentId)
      setAssignment((current) => current
        ? { ...current, review_session: reviewSession, status: 'in_progress' }
        : current)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The review session could not be started.')
    }
  }

  if (loading) return <LoadingState title="Loading assigned version…" detail="Preparing the prototype and review form for your session." />
  if (error && !assignment) return <Empty title="Assignment unavailable"><ErrorBanner message={error} /><Link className="button" to="/reviews">Back to your queue</Link></Empty>
  if (!assignment) return <Empty title="Assignment unavailable"><Link className="button" to="/reviews">Back to your queue</Link></Empty>
  function updateForm<K extends keyof typeof form>(field: K, value: (typeof form)[K]) {
    if (!submitting) idempotencyKey.current = null
    setForm((current) => ({ ...current, [field]: value }))
  }
  async function retryBackgroundHandoff() {
    if (!assignment) return
    const review = assignment.feedback
    if (
      !review?.idempotency_key
      || !assignment.review_session
      || review.usability_score === null
      || review.usefulness_score === null
      || review.completeness_score === null
      || review.feasibility_score === null
      || review.would_use === null
      || !review.strengths
      || !review.concerns
      || !review.suggested_improvements
      || !review.usage_context
    ) return
    setRetryingHandoff(true)
    setHandoffError('')
    try {
      const retried = await submitReviewerReview(assignmentId, {
        session_id: assignment.review_session.id,
        rating: review.rating,
        usability_score: review.usability_score,
        usefulness_score: review.usefulness_score,
        completeness_score: review.completeness_score,
        feasibility_score: review.feasibility_score,
        would_use: review.would_use,
        feedback_text: review.feedback_text,
        strengths: review.strengths,
        concerns: review.concerns,
        suggested_improvements: review.suggested_improvements,
        usage_context: review.usage_context,
      }, review.idempotency_key)
      setAssignment((current) => current ? { ...current, feedback: retried } : current)
    } catch (reason) {
      setHandoffError(reason instanceof Error ? reason.message : 'The background sync could not be retried.')
    } finally {
      setRetryingHandoff(false)
    }
  }
  function reviewReceipt(review: ApiReview) {
    return <div className="review-success">
      <CheckCheck size={36} />
      <h2>Your review is recorded.</h2>
      <p>Thank you for reviewing {assignment?.idea_title} (Version {assignment?.version}). Your structured feedback has been saved.</p>
      <Badge tone="green">Review submitted</Badge>
      <p><strong>Overall rating:</strong> {review.rating}/5</p>
      <p>{review.feedback_text}</p>
      {review.analysis_error && <>
        <ErrorBanner message={handoffError || review.analysis_error} onRetry={retryBackgroundHandoff} />
        <button className="button" disabled={retryingHandoff} onClick={() => void retryBackgroundHandoff()}>{retryingHandoff ? 'Retrying…' : 'Retry background sync'}</button>
      </>}
      <Link className="button primary" to="/reviews">Back to your queue<ArrowRight size={15} /></Link>
    </div>
  }
  return <><Link className="back-link" to="/reviews"><ArrowLeft size={15} />Your review queue</Link>
    <PageHeading eyebrow="REVIEW WORKSPACE" title={assignment.idea_title} actions={<Status value={assignment.status} />}>Version {assignment.version} · Assigned to your account.</PageHeading>
    <div className="notice"><ShieldCheck size={20} /><div><strong>Review this specific version</strong><p>Explore the interactive prototype below and share your structured feedback on Version {assignment.version}.</p></div></div>
    {error && <ErrorBanner message={error} />}
    <section className="prose-section"><h2>Problem</h2><p>{assignment.problem}</p><h2>Proposed solution</h2><p>{assignment.solution}</p><h2>Intended audience</h2><p>{assignment.audience}</p><h2>Features</h2><ul>{assignment.features.map((feature) => <li key={feature}>{feature}</li>)}</ul><h2>Constraints</h2><p>{assignment.constraints || 'No constraints provided.'}</p></section>
    {prototypePreview
      ? <SchemaPrototypePreview spec={prototypePreview.preview_spec} />
      : <p className="muted">No interactive prototype preview is attached to this version yet.</p>}
    {assignment.review_submitted && assignment.feedback
      ? reviewReceipt(assignment.feedback)
      : <form className="review-form" onSubmit={submit}><h2>Your review</h2>
        {error && <ErrorBanner message={error} />}
        {!assignment.review_session && <><p role="status">A review session is required before feedback can be submitted.</p><button type="button" className="button" onClick={() => void retrySessionStart()}>Retry session startup</button></>}
        {(['rating', 'usability_score', 'usefulness_score', 'completeness_score', 'feasibility_score'] as const).map((field) => <label key={field}>{field === 'rating' ? 'Overall rating' : field.replace('_score', '').replaceAll('_', ' ').replace(/^\w/, (letter) => letter.toUpperCase())}<select required disabled={submitting || !assignment.review_session} value={form[field] || ''} onChange={(event) => updateForm(field, Number(event.target.value))}><option value="">Select a rating</option>{[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value} / 5</option>)}</select></label>)}
        <label>Would you use this product?<select required disabled={submitting || !assignment.review_session} value={form.would_use === null ? '' : String(form.would_use)} onChange={(event) => updateForm('would_use', event.target.value === '' ? null : event.target.value === 'true')}><option value="">Choose an answer</option><option value="true">Yes</option><option value="false">No</option></select></label>
        {([
          ['feedback_text', 'Evidence and feedback'],
          ['strengths', 'Strengths'],
          ['concerns', 'Concerns'],
          ['suggested_improvements', 'Suggested improvements'],
          ['usage_context', 'Usage context'],
        ] as const).map(([field, label]) => <label key={field}>{label}<textarea disabled={submitting || !assignment.review_session} required minLength={10} maxLength={5000} rows={field === 'feedback_text' ? 5 : 3} value={form[field]} onChange={(event) => updateForm(field, event.target.value)} /></label>)}
        <button className="button primary" disabled={submitting || !assignment.review_session}>{submitting ? 'Submitting…' : error ? 'Retry review submission' : 'Submit review'}<Send size={15} /></button>
      </form>}
  </>
}

function PreviewReviewWorkspace() {
  const { id } = useParams()
  const { state, update, notify } = useWorkspace()
  const idea = state.ideas.find((candidate) => candidate.id === id)
  const [opened, setOpened] = useState(false)
  const [interacted, setInteracted] = useState(false)
  const [journey, setJourney] = useState<string[]>([])
  const { register, handleSubmit, watch, formState: { errors } } = useForm<ReviewForm>()
  const existing = state.reviews.find((review) => review.ideaId === id && review.reviewer === 'Maya Chen' && !review.sample)
  if (!idea || !state.assignments.some((assignment) => assignment.ideaId === id && assignment.reviewer === 'Maya Chen')) return <Empty title="This project is not assigned to the preview reviewer"><Link className="button" to="/reviews">Review queue</Link></Empty>
  if (existing) return <><PageHeading eyebrow="REVIEWER PORTAL" title="Your perspective is recorded." /><div className="review-success"><CheckCheck size={40} /><h2>Thank you for testing {idea.title}.</h2><p>Your feedback is saved in this workspace.</p><Badge tone="green">V{existing.version} · Local review</Badge><blockquote>{existing.improvements}</blockquote><Link className="button primary" to="/reviews">Back to your queue<ArrowRight size={15} /></Link></div><IdeaDiscussion key={idea.id} idea={idea} /></>
  const tasks = idea.id === 'placement' ? ['Explore an opportunity', 'Try the resume checklist', 'Inspect the preparation roadmap'] : ['Open the collection schedule', 'Submit a sample issue', 'Inspect the recorded request']
  function submit(values: ReviewForm) {
    if (!idea || !interacted || journey.length !== tasks.length) { notify('Use the prototype and complete the test journey before submitting.'); return }
    const review: Review = { id: crypto.randomUUID(), ideaId: idea.id, version: idea.version, reviewer: 'Maya Chen', rating: Number(values.rating), usability: Number(values.usability), usefulness: Number(values.usefulness), feasibility: Number(values.feasibility), completeness: Number(values.completeness), wouldUse: values.wouldUse === 'yes', strengths: values.strengths, concerns: values.concerns, improvements: values.improvements, context: values.context, created: new Date().toISOString(), sample: false }
    try {
      const next = addReview(state, review)
      update(() => ({ ...next, audit: [{ id: crypto.randomUUID(), action: 'Local review submitted', entity: idea.title, created: review.created }, ...next.audit] }), 'Feedback saved to your workspace.')
    } catch (error) { notify(error instanceof Error ? error.message : 'Review could not be saved.') }
  }
  return <><Link className="back-link" to="/reviews"><ArrowLeft size={15} />Your review queue</Link><PageHeading eyebrow="REVIEW WORKSPACE" title={idea.title} actions={<Status value={idea.status} />}>Prototype V{idea.version} · Assigned to Maya Chen</PageHeading>
    <section className="review-launch"><div><Monitor size={26} /><div><h2>First, spend a little time with the idea.</h2><p>{idea.solution}</p></div></div><button className="button primary" onClick={() => setOpened(!opened)}><Play size={15} />{opened ? 'Hide prototype' : 'Open prototype'}</button></section>
    {opened && <div className="review-demo"><PrototypeDemo idea={idea} onInteraction={() => setInteracted(true)} /></div>}
    <IdeaDiscussion key={idea.id} idea={idea} canComment={interacted} />
    <details className="detailed-review"><summary>Detailed rating review (optional)</summary><div className="review-layout"><form className="review-form" onSubmit={handleSubmit(submit)}><h2>Your experience</h2><p className="section-description">Ratings reflect this version, not the future potential of the idea.</p>
      {(['usability', 'usefulness', 'feasibility', 'completeness', 'rating'] as const).map((dimension) => <fieldset className="rating-field" key={dimension}><legend>{dimension === 'rating' ? 'Overall rating' : dimension[0].toUpperCase() + dimension.slice(1)}</legend><div>{[1, 2, 3, 4, 5].map((score) => <label title={`${score} of 5`} key={score}><input type="radio" value={score} aria-label={`${dimension} ${score} stars`} {...register(dimension, { required: true })} /><Star size={23} fill={Number(watch(dimension)) >= score ? '#d4b46c' : 'none'} color={Number(watch(dimension)) >= score ? '#d4b46c' : '#cdd8cf'} /></label>)}</div>{errors[dimension] && <small className="error">Select a rating.</small>}</fieldset>)}
      <fieldset className="would-use"><legend>Would you use this product?</legend><label><input type="radio" value="yes" {...register('wouldUse', { required: true })} />Yes</label><label><input type="radio" value="no" {...register('wouldUse', { required: true })} />Not yet</label>{errors.wouldUse && <small className="error">Select an answer.</small>}</fieldset>
      {([{ key: 'strengths', title: 'What worked well?', placeholder: 'Point to a screen, interaction, or result that helped.' }, { key: 'concerns', title: 'Where did you get stuck?', placeholder: 'Describe what happened and what you expected.' }, { key: 'improvements', title: 'What should improve next?', placeholder: 'Suggest a specific change based on your experience.' }, { key: 'context', title: 'Your testing context', placeholder: 'Which device, screens, and tasks did you test?' }] as const).map(({ key, title, placeholder }) => <label key={key}>{title}<textarea rows={3} placeholder={placeholder} {...register(key, { required: 'Add your evidence.', minLength: { value: 10, message: 'Add at least 10 characters.' }, maxLength: { value: 3000, message: 'Use 3000 characters or fewer.' } })} />{errors[key] && <small className="error">{errors[key]?.message}</small>}</label>)}
      <div className="form-actions"><button className="button primary" type="submit" disabled={idea.status !== 'Review open'}><Send size={15} />Submit review</button></div>
    </form><aside className="review-journey"><ListChecks size={24} /><h3>Your test journey</h3><p>V{idea.version} · {journey.length} of {tasks.length} complete</p>{tasks.map((task) => <label key={task}><input type="checkbox" checked={journey.includes(task)} onChange={() => setJourney(journey.includes(task) ? journey.filter((entry) => entry !== task) : [...journey, task])} />{task}</label>)}<div className="interaction-state"><ShieldCheck size={16} />{interacted ? 'Prototype interaction recorded' : 'Awaiting prototype interaction'}</div><hr /><p>Local feedback only. No trust or authenticity result is generated by this preview.</p></aside></div></details>
  </>
}
