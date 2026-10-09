import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useForm } from 'react-hook-form'
import { ArrowLeft, ArrowRight, ArrowUpRight, Clock3, FileText, Lightbulb, MessageSquare, Play, Plus, Search, Upload, Users } from 'lucide-react'
import { addIdea, ideaReviews, publishIdea } from '../services/preview'
import type { Idea } from '../services/preview'
import { useWorkspace } from '../services/workspace'
import { Badge, dateLabel, Empty, PageHeading, SectionHeading, Status } from '../components/ui'
import { ProjectVisual } from '../components/ProjectVisual'
import { IdeaFeed } from '../components/IdeaFeed'
import { createIdea, listIdeas, toPreviewIdea } from '../services/ideas'
import { getAccessToken } from '../services/auth'

export function ProjectCard({ idea }: { idea: Idea }) {
  const { state } = useWorkspace()
  const count = ideaReviews(state, idea.id).length
  return <article className="project-card">
    <Link to={`/ideas/${idea.id}`}><ProjectVisual idea={idea} /></Link>
    <div className="project-info"><div className="card-meta"><span>{idea.category}</span><Status value={idea.status} /></div>
      <h3><Link to={`/ideas/${idea.id}`}>{idea.title}</Link></h3><p>{idea.solution}</p>
      <div className="card-footer"><span><MessageSquare size={14} />{count} reviews</span><span>V{idea.version}</span><Link aria-label={`Open ${idea.title}`} title={`Open ${idea.title}`} to={`/ideas/${idea.id}`}><ArrowUpRight size={19} /></Link></div>
    </div>
  </article>
}

export function Dashboard() {
  return <IdeaFeed />
}

export function Ideas({ prototypes = false }: { prototypes?: boolean }) {
  const { state, role, update, notify } = useWorkspace()
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    if (!getAccessToken()) return
    let active = true
    setLoading(true)
    listIdeas()
      .then((ideas) => {
        if (active) update((current) => ({ ...current, ideas: ideas.map((idea) => toPreviewIdea(idea)) }))
      })
      .catch((error: unknown) => { if (active) notify(error instanceof Error ? error.message : 'The ideas could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [notify, update])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('All statuses')
  const ideas = state.ideas.filter((idea) => (!prototypes || idea.status !== 'Draft') && `${idea.title} ${idea.category}`.toLowerCase().includes(query.toLowerCase()) && (status === 'All statuses' || idea.status === status))
  if (loading) return <div role="status" className="empty">Loading your API ideas...</div>
  return <><PageHeading eyebrow="WORKSPACE" title={prototypes ? 'Prototype library' : 'Your ideas'} actions={role !== 'reviewer' && <Link className="button primary" to="/ideas/new"><Plus size={17} />New idea</Link>}>{prototypes ? 'Reviewable spaces, connected to the ideas behind them.' : 'From the first question to the next version.'}</PageHeading>
    <div className="filter-bar"><label className="search-field"><Search size={17} /><input aria-label="Search ideas" placeholder="Search ideas or categories" value={query} onChange={(event) => setQuery(event.target.value)} /></label><select aria-label="Idea status" value={status} onChange={(event) => setStatus(event.target.value)}>{['All statuses', 'Draft', 'Ready for review', 'Review open', 'Evolution ready'].map((value) => <option key={value}>{value}</option>)}</select><span className="filter-count">{ideas.length} {ideas.length === 1 ? 'idea' : 'ideas'}</span></div>
    {ideas.length ? <div className="project-grid library">{ideas.map((idea) => <ProjectCard idea={idea} key={idea.id} />)}</div> : <Empty title="No matching ideas"><p>Try another search or status.</p></Empty>}
  </>
}

type IdeaForm = { title: string; category: string; problem: string; solution: string; audience: string; features: string; constraints: string }
export function IdeaSubmission() {
  const { update, role, notify } = useWorkspace()
  const navigate = useNavigate()
  const [assets, setAssets] = useState<string[]>([])
  const { register, handleSubmit, formState: { errors } } = useForm<IdeaForm>({ defaultValues: { category: 'Education' } })
  if (role === 'reviewer') return <Empty title="Owner portal required"><Link className="button" to="/reviews">Back to review queue</Link></Empty>
  async function submit(values: IdeaForm) {
    const input = { ...values, features: values.features.split('\n').map((feature) => feature.trim()).filter(Boolean), assets }
    if (getAccessToken()) {
      try {
        const saved = await createIdea(input)
        update((state) => ({ ...state, ideas: [toPreviewIdea(saved, assets), ...state.ideas] }), 'Idea saved to the local API.')
        navigate(`/ideas/${saved.id}`)
      } catch (error) {
        notify(error instanceof Error ? error.message : 'The idea could not be saved.')
      }
      return
    }
    update((state) => {
      const next = addIdea(state, input)
      navigate(`/ideas/${next.ideas[0].id}`)
      return next
    }, 'Idea saved locally in offline preview mode.')
  }
  return <><Link className="back-link" to="/ideas"><ArrowLeft size={15} />Your ideas</Link><PageHeading eyebrow="A NEW START" title="Give your idea a place to grow." />
    <div className="form-layout"><form className="idea-form" onSubmit={handleSubmit(submit)}><section><h2>The essentials</h2><p className="section-description">The problem, the people, and your proposed solution.</p>
      <label>Idea title <span>*</span><input placeholder="e.g. A smarter way to prepare for campus placements" {...register('title', { required: 'Add a title.', maxLength: { value: 120, message: 'Use 120 characters or fewer.' } })} />{errors.title && <small className="error">{errors.title.message}</small>}</label>
      <div className="form-two"><label>Category<select {...register('category')}>{['Education', 'Sustainability', 'Community', 'Healthcare', 'Productivity', 'Other'].map((category) => <option key={category}>{category}</option>)}</select></label><label>Target users <span>*</span><input placeholder="Who is this for?" {...register('audience', { required: 'Add your target users.' })} />{errors.audience && <small className="error">{errors.audience.message}</small>}</label></div>
      <label>Problem statement <span>*</span><textarea rows={3} placeholder="What is difficult today, and why does it matter?" {...register('problem', { required: 'Describe the problem.', minLength: { value: 20, message: 'Add at least 20 characters.' } })} />{errors.problem && <small className="error">{errors.problem.message}</small>}</label>
      <label>Proposed solution <span>*</span><textarea rows={3} placeholder="What would a better experience look like?" {...register('solution', { required: 'Describe the solution.', minLength: { value: 20, message: 'Add at least 20 characters.' } })} />{errors.solution && <small className="error">{errors.solution.message}</small>}</label>
    </section><section><h2>Shape the first version</h2><label>Core features <span>*</span><textarea rows={4} placeholder={'One feature per line\nJob matching\nResume checklist\nPreparation roadmap'} {...register('features', { required: 'Add at least one feature.', validate: (value) => value.trim().length > 0 || 'Add at least one feature.' })} />{errors.features && <small className="error">{errors.features.message}</small>}</label><label>Constraints and considerations<textarea rows={2} placeholder="Technical, accessibility, privacy, or scope constraints" {...register('constraints')} /></label>
      <label className="upload-zone"><Upload size={22} /><strong>Reference files</strong><span>PDF, PNG, or JPG · up to 10 MB each</span><input aria-label="Reference files" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" onChange={(event) => {
        const files = Array.from(event.target.files ?? [])
        if (files.some((file) => file.size > 10 * 1024 * 1024 || !['application/pdf', 'image/png', 'image/jpeg'].includes(file.type))) { notify('Select PDF, PNG, or JPG files no larger than 10 MB.'); event.target.value = ''; return }
        setAssets(files.map((file) => file.name))
      }} /><small>Filenames only in this preview. No files are uploaded.</small></label>{assets.map((asset) => <p className="file-name" key={asset}><FileText size={14} />{asset}</p>)}
    </section><div className="form-actions"><Link className="button" to="/ideas">Cancel</Link><button className="button primary" type="submit">Save idea<ArrowRight size={16} /></button></div></form>
    <aside className="form-aside"><Lightbulb size={27} /><h3>Start with something specific.</h3><p>A clear problem and a focused first version make room for more useful feedback.</p><hr /><span className="eyebrow">WHAT COMES NEXT</span><ol><li>Requirements</li><li>Visual prototype</li><li>Reviewer feedback</li><li>Evidence-led evolution</li></ol><Badge>Python agents pending</Badge></aside></div>
  </>
}

export function IdeaDetails() {
  const { id } = useParams()
  const { state, update, role } = useWorkspace()
  const idea = state.ideas.find((candidate) => candidate.id === id)
  const [tab, setTab] = useState('Overview')
  if (!idea) return <Empty title="Idea not found"><Link to="/ideas">Back to ideas</Link></Empty>
  const reviews = ideaReviews(state, idea.id)
  return <><Link className="back-link" to="/ideas"><ArrowLeft size={15} />Your ideas</Link><PageHeading eyebrow={`${idea.category.toUpperCase()} / V${idea.version}`} title={idea.title} actions={<>{idea.status === 'Ready for review' && role !== 'reviewer' && <button className="button" onClick={() => update((current) => publishIdea(current, idea.id), 'Preview review cycle opened.')}>Publish for review</button>}<Link className="button primary" to={`/ideas/${idea.id}/prototype`}><Play size={16} />{idea.status === 'Draft' ? 'Prototype workspace' : 'Launch prototype'}</Link></>}>{idea.audience}</PageHeading>
    <div className="detail-meta"><Status value={idea.status} /><span><Clock3 size={14} />Updated {dateLabel(idea.updated)}</span><Badge>Local preview</Badge></div>
    <div className="tabs" role="tablist">{['Overview', 'Requirements', 'Feedback', 'Versions'].map((value) => <button key={value} role="tab" aria-selected={tab === value} onClick={() => setTab(value)}>{value}{value === 'Feedback' && <span>{reviews.length}</span>}</button>)}</div>
    {tab === 'Overview' && <div className="detail-layout"><div><div className="detail-visual"><ProjectVisual idea={idea} /></div><section className="prose-section"><h2>The problem</h2><p>{idea.problem}</p><h2>The solution</h2><p>{idea.solution}</p></section><SectionHeading title="Core features" /><div className="feature-grid">{idea.features.map((feature, index) => <div key={feature}><span>{String(index + 1).padStart(2, '0')}</span><h3>{feature}</h3></div>)}</div></div><aside className="detail-aside"><h3>Review cycle</h3><strong className="big-number">{reviews.length}<small>feedback records</small></strong><Link className="button" to={`/feedback?idea=${idea.id}`}>Explore feedback<ArrowRight size={15} /></Link><hr /><h3>Constraints</h3><p>{idea.constraints || 'No constraints added.'}</p><hr /><h3>Reference files</h3>{idea.assets.length ? idea.assets.map((asset) => <p className="file-name" key={asset}><FileText size={14} />{asset}</p>) : <p>No reference files.</p>}<hr /><Link className="text-link" to={`/evolution?idea=${idea.id}`}>View evolution<ArrowUpRight size={15} /></Link></aside></div>}
    {tab === 'Requirements' && <section className="requirements"><div className="notice"><FileText size={19} /><div><strong>Owner-provided brief</strong><p>Structured AI requirements are awaiting the Python Requirement Agent.</p></div></div><dl><dt>Problem</dt><dd>{idea.problem}</dd><dt>Target users</dt><dd>{idea.audience}</dd><dt>Proposed solution</dt><dd>{idea.solution}</dd><dt>Features</dt><dd><ul>{idea.features.map((feature) => <li key={feature}>{feature}</li>)}</ul></dd><dt>Constraints</dt><dd>{idea.constraints || 'None specified'}</dd></dl></section>}
    {tab === 'Feedback' && (reviews.length ? <div className="evidence-list">{reviews.map((review) => <article key={review.id}><div><strong>{review.reviewer}</strong><Badge>{review.sample ? 'Sample' : 'Local review'}</Badge><span>{review.rating}/5</span></div><p>{review.improvements}</p><small>{review.context}</small><Link className="text-link" to={`/feedback?idea=${idea.id}#${review.id}`}>View evidence<ArrowUpRight size={14} /></Link></article>)}</div> : <Empty title="No feedback for this idea yet" />)}
    {tab === 'Versions' && <div className="version-list"><div><Badge tone="green">V{idea.version}</Badge><h3>Original idea</h3><p>{idea.solution}</p><small>Preserved source version</small></div>{state.evolutions.filter((evolution) => evolution.ideaId === idea.id).map((evolution) => <div key={evolution.id}><Badge tone="blue">V{evolution.target} proposal</Badge><h3>Evidence-linked change set</h3><ul>{evolution.changes.map((change) => <li key={change}>{change}</li>)}</ul><Link className="text-link" to={`/evolution?idea=${idea.id}`}>Compare versions<ArrowRight size={14} /></Link></div>)}</div>}
  </>
}

export function ReviewQueue() {
  const { state } = useWorkspace()
  const assignments = state.assignments.filter((assignment) => assignment.reviewer === 'Maya Chen')
  return <><PageHeading eyebrow="REVIEWER PORTAL / MAYA CHEN" title="A fresh perspective starts here.">Your assigned prototypes and review sessions.</PageHeading><div className="notice"><Users size={19} /><div><strong>Preview reviewer identity</strong><p>Maya Chen · Assigned projects only · Real authentication pending</p></div></div><SectionHeading title="Your assignments" />
    {assignments.length ? <div className="assignment-list">{assignments.map((assignment) => {
      const idea = state.ideas.find((candidate) => candidate.id === assignment.ideaId)
      if (!idea) return null
      return <article className="assignment" key={assignment.id}><ProjectVisual idea={idea} /><div><div className="card-meta"><Badge>{idea.category}</Badge><Status value={assignment.status} /></div><h2>{idea.title}</h2><p>{idea.solution}</p><span className="muted">Prototype V{idea.version}</span></div><Link className="button primary" to={`/reviews/${idea.id}`}>{assignment.status === 'Completed' ? 'View review' : 'Start review'}<ArrowRight size={16} /></Link></article>
    })}</div> : <Empty title="No assignments yet"><p>Assigned review cycles will appear here.</p></Empty>}
  </>
}