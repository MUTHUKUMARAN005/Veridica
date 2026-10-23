import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useForm } from 'react-hook-form'
import { ArrowLeft, ArrowRight, ArrowUpRight, Clock3, FileText, Lightbulb, MessageSquare, Play, Plus, Search, Upload, Users } from 'lucide-react'
import { addIdea, ideaReviews, publishIdea } from '@/services/preview'
import type { Idea } from '@/services/preview'
import { useWorkspace } from '@/services/workspace'
import { Badge, dateLabel, Empty, Modal, PageHeading, SectionHeading, Status } from '@/components/ui'
import { ProjectVisual } from '@/components/ProjectVisual'
import { IdeaFeed } from '@/components/IdeaFeed'
import { SchemaPrototypePreview } from '@/components/SchemaPrototypePreview'
import {
  createIdea,
  createIdeaVersion,
  downloadIdeaAsset,
  getLatestRequirementAnalysis,
  getLatestPrototypeSource,
  getIdea,
  listIdeas,
  publishIdeaVersion,
  startRequirementAnalysis,
  generatePrototypeSource,
  getPrototypeSourceFiles,
  toPreviewIdea,
  updateIdeaStatus,
  uploadIdeaAsset,
} from '@/services/ideas'
import type {
  ApiIdeaDetail,
  PrototypeBuild,
  PrototypeSource,
  RequirementAnalysis,
  RequirementFact,
} from '../services/ideas'
import { getAccessToken } from '../services/auth'
import { listReviewerAssignments } from '../services/authorization'
import type { ReviewerAssignment } from '../services/authorization'

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
  return getAccessToken() ? <Ideas /> : <IdeaFeed />
}

export function Ideas({ prototypes = false }: { prototypes?: boolean }) {
  const { state, role } = useWorkspace()
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState('')
  const [apiIdeas, setApiIdeas] = useState<Idea[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('All statuses')
  const [category, setCategory] = useState('All categories')
  useEffect(() => {
    if (!getAccessToken()) return
    let active = true
    setLoading(true)
    setApiError('')
    setApiIdeas([])
    setTotal(0)
    listIdeas({
      limit: 20,
      offset,
      status: status === 'All statuses' ? undefined : status,
      category: category === 'All categories' ? undefined : category,
      q: query,
    })
      .then((page) => {
        if (!active) return
        setApiIdeas(page.items.map((idea) => toPreviewIdea(idea)))
        setTotal(page.total)
      })
      .catch((error: unknown) => {
        if (active) setApiError(error instanceof Error ? error.message : 'The ideas could not be loaded.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [offset, status, category, query])
  const sourceIdeas = getAccessToken() ? apiIdeas : state.ideas
  const ideas = sourceIdeas.filter((idea) => {
    if (prototypes && idea.status === 'Draft') return false
    if (getAccessToken()) return true
    return `${idea.title} ${idea.category}`.toLowerCase().includes(query.toLowerCase())
      && (status === 'All statuses' || idea.status === status)
      && (category === 'All categories' || idea.category === category)
  })
  if (loading) return <div role="status" className="empty">Loading your API ideas...</div>
  return <><PageHeading eyebrow="WORKSPACE" title={prototypes ? 'Prototype library' : 'Your ideas'} actions={role !== 'reviewer' && <Link className="button primary" to="/ideas/new"><Plus size={17} />New idea</Link>}>{prototypes ? 'Reviewable spaces, connected to the ideas behind them.' : 'From the first question to the next version.'}</PageHeading>
    <div className="filter-bar"><label className="search-field"><Search size={17} /><input aria-label="Search ideas" placeholder="Search ideas" value={query} onChange={(event) => { setQuery(event.target.value); setOffset(0) }} /></label><select aria-label="Idea status" value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0) }}>{['All statuses', 'Draft', 'Ready for review', 'Review open', 'Evolution ready', 'Archived'].map((value) => <option key={value}>{value}</option>)}</select><select aria-label="Idea category" value={category} onChange={(event) => { setCategory(event.target.value); setOffset(0) }}>{['All categories', 'Education', 'Sustainability', 'Community', 'Healthcare', 'Productivity', 'Other'].map((value) => <option key={value}>{value}</option>)}</select><span className="filter-count">{getAccessToken() ? total : ideas.length} {total === 1 ? 'idea' : 'ideas'}</span></div>
    {apiError && <p role="alert" className="error">{apiError}</p>}
    {ideas.length ? <div className="project-grid library">{ideas.map((idea) => <ProjectCard idea={idea} key={idea.id} />)}</div> : !apiError && <Empty title="No matching ideas"><p>Try another search or status.</p></Empty>}
    {getAccessToken() && total > 20 && <nav className="pagination" aria-label="Idea pages"><button className="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous</button><span>{offset + 1}–{Math.min(offset + apiIdeas.length, total)} of {total}</span><button className="button" disabled={offset + 20 >= total} onClick={() => setOffset(offset + 20)}>Next</button></nav>}
  </>
}

type IdeaForm = { title: string; category: string; problem: string; solution: string; audience: string; features: string; constraints: string }
export function IdeaSubmission() {
  const { update, role, notify } = useWorkspace()
  const navigate = useNavigate()
  const [assets, setAssets] = useState<string[]>([])
  const [assetFiles, setAssetFiles] = useState<File[]>([])
  const [saveError, setSaveError] = useState('')
  const [partialSavedIdeaId, setPartialSavedIdeaId] = useState('')
  const { register, handleSubmit, formState: { errors } } = useForm<IdeaForm>({ defaultValues: { category: 'Education' } })
  if (role === 'reviewer') return <Empty title="Owner portal required"><Link className="button" to="/reviews">Back to review queue</Link></Empty>
  async function submit(values: IdeaForm) {
    setSaveError('')
    setPartialSavedIdeaId('')
    const features = values.features.split('\n').map((feature) => feature.trim()).filter(Boolean)
    const input = { ...values, features, assets }
    if (getAccessToken()) {
      let savedIdeaId = ''
      try {
        const saved = await createIdea({ ...values, features })
        savedIdeaId = saved.id
        for (const file of assetFiles) {
          await uploadIdeaAsset(saved.id, saved.version, file)
        }
        navigate(`/ideas/${saved.id}`)
      } catch (error) {
        const message = error instanceof Error ? error.message : 'The idea could not be saved.'
        if (savedIdeaId) {
          setPartialSavedIdeaId(savedIdeaId)
          setSaveError(`The idea was saved, but an attachment could not be uploaded: ${message}`)
        } else {
          setSaveError(message)
        }
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
        setAssetFiles(files)
      }} /><small>{getAccessToken() ? 'Files upload privately to your authenticated idea.' : 'Filenames only in offline preview. No files are uploaded.'}</small></label>{assets.map((asset) => <p className="file-name" key={asset}><FileText size={14} />{asset}</p>)}
    </section>{saveError && <p role="alert" className="error">{saveError}{partialSavedIdeaId && <> <Link to={`/ideas/${partialSavedIdeaId}`}>Open the saved idea</Link></>}</p>}<div className="form-actions"><Link className="button" to="/ideas">Cancel</Link><button className="button primary" type="submit">Save idea<ArrowRight size={16} /></button></div></form>
    <aside className="form-aside"><Lightbulb size={27} /><h3>Start with something specific.</h3><p>A clear problem and a focused first version make room for more useful feedback.</p><hr /><span className="eyebrow">WHAT COMES NEXT</span><ol><li>Requirements</li><li>Visual prototype</li><li>Reviewer feedback</li><li>Evidence-led evolution</li></ol><Badge>Python agents pending</Badge></aside></div>
  </>
}

export function IdeaDetails() {
  const { id } = useParams()
  const { state, update, role, notify } = useWorkspace()
  const [apiDetail, setApiDetail] = useState<ApiIdeaDetail | null>(null)
  const [apiIdea, setApiIdea] = useState<ReturnType<typeof toPreviewIdea> | null>(null)
  const [apiVersions, setApiVersions] = useState<ReturnType<typeof toPreviewIdea>[]>([])
  const [apiLoading, setApiLoading] = useState(false)
  const [apiError, setApiError] = useState('')
  const [versionDialog, setVersionDialog] = useState(false)
  const [versionBusy, setVersionBusy] = useState(false)
  const [versionError, setVersionError] = useState('')
  const [assetBusy, setAssetBusy] = useState(false)
  const [assetError, setAssetError] = useState('')
  const [publishingVersion, setPublishingVersion] = useState<number | null>(null)
  const [publishError, setPublishError] = useState('')
  const [versionInput, setVersionInput] = useState({
    title: '', category: '', problem: '', solution: '', audience: '', features: '', constraints: '',
  })
  const [changeSummary, setChangeSummary] = useState('')
  useEffect(() => {
    if (!id || !getAccessToken()) return
    let active = true
    setApiError('')
    setApiLoading(true)
    getIdea(id)
      .then((result) => {
        if (!active) return
        setApiDetail(result)
        setApiIdea(toPreviewIdea(result))
        setApiVersions(result.versions.map((version) => toPreviewIdea(version)))
      })
      .catch((reason: unknown) => {
        if (active) setApiError(reason instanceof Error ? reason.message : 'The idea could not be loaded.')
      })
      .finally(() => { if (active) setApiLoading(false) })
    return () => { active = false }
  }, [id])
  const idea = getAccessToken()
    ? apiIdea?.id === id ? apiIdea : undefined
    : state.ideas.find((candidate) => candidate.id === id)
  const [tab, setTab] = useState('Overview')
  if (!idea) {
    if (apiLoading) return <div role="status" className="empty">Loading your authorized idea...</div>
    return <Empty title={apiError ? 'Idea unavailable' : 'Idea not found'}>{apiError && <p role="alert">{apiError}</p>}<Link to="/ideas">Back to ideas</Link></Empty>
  }
  const currentIdea = idea
  const reviews = ideaReviews(state, currentIdea.id)
  function openVersionDialog() {
    setVersionError('')
    setChangeSummary('')
    setVersionInput({
      title: currentIdea.title,
      category: currentIdea.category,
      problem: currentIdea.problem,
      solution: currentIdea.solution,
      audience: currentIdea.audience,
      features: currentIdea.features.join('\n'),
      constraints: currentIdea.constraints,
    })
    setVersionDialog(true)
  }
  async function saveVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setVersionBusy(true)
    setVersionError('')
    try {
      const saved = await createIdeaVersion(currentIdea.id, {
        ...versionInput,
        features: versionInput.features.split('\n').map((feature) => feature.trim()).filter(Boolean),
        expected_version: currentIdea.version,
        change_summary: changeSummary,
      })
      const nextVersion = toPreviewIdea(saved)
      setApiIdea(nextVersion)
      setApiVersions((current) => [...current, nextVersion])
      setApiDetail((current) => current
        ? { ...saved, versions: [...current.versions, saved] }
        : current)
      setVersionDialog(false)
      notify(`Version ${saved.version} was saved without changing earlier versions.`)
    } catch (reason) {
      setVersionError(reason instanceof Error ? reason.message : 'The new version could not be saved.')
    } finally {
      setVersionBusy(false)
    }
  }
  async function changeApiStatus(status: 'Draft' | 'Archived') {
    try {
      const saved = await updateIdeaStatus(currentIdea.id, status)
      setApiDetail((current) => current ? { ...current, ...saved } : current)
      setApiIdea(toPreviewIdea(saved))
      notify(status === 'Archived' ? 'Idea archived.' : 'Idea restored.')
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : 'The idea status could not be changed.')
    }
  }
  async function publishApiVersion(version: number) {
    setPublishingVersion(version)
    setPublishError('')
    try {
      await publishIdeaVersion(currentIdea.id, version)
      setApiIdea((current) => current ? { ...current, status: 'Review open' } : current)
      setApiDetail((current) => current ? { ...current, status: 'Review open' } : current)
      notify(`Version ${version} is published for review.`)
    } catch (reason) {
      setPublishError(reason instanceof Error ? reason.message : 'The version could not be published.')
    } finally {
      setPublishingVersion(null)
    }
  }
  async function uploadAssets(files: FileList | null) {
    if (!files?.length || !apiDetail) return
    setAssetBusy(true)
    setAssetError('')
    try {
      let latest = apiDetail
      for (const file of Array.from(files)) {
        latest = {
          ...latest,
          ...(await uploadIdeaAsset(currentIdea.id, currentIdea.version, file)),
          versions: latest.versions,
        }
      }
      setApiDetail(latest)
      setApiIdea(toPreviewIdea(latest))
      notify('Reference file uploaded privately.')
    } catch (reason) {
      setAssetError(reason instanceof Error ? reason.message : 'The reference file could not be uploaded.')
    } finally {
      setAssetBusy(false)
    }
  }
  async function downloadAsset(asset: NonNullable<ApiIdeaDetail['assets']>[number]) {
    try {
      await downloadIdeaAsset(currentIdea.id, currentIdea.version, asset.id, asset.filename)
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : 'The reference file could not be downloaded.')
    }
  }
  return <><Link className="back-link" to="/ideas"><ArrowLeft size={15} />Your ideas</Link><PageHeading eyebrow={`${idea.category.toUpperCase()} / V${idea.version}`} title={idea.title} actions={<>{getAccessToken() && role === 'owner' && idea.status === 'Archived' && <button className="button" onClick={() => void changeApiStatus('Draft')}>Restore idea</button>}{getAccessToken() && role === 'owner' && idea.status === 'Draft' && <button className="button" onClick={() => void changeApiStatus('Archived')}>Archive idea</button>}{idea.status === 'Ready for review' && role !== 'reviewer' && <button className="button" onClick={() => update((current) => publishIdea(current, idea.id), 'Preview review cycle opened.')}>Publish for review</button>}<Link className="button primary" to={`/ideas/${idea.id}/prototype`}><Play size={16} />{idea.status === 'Draft' ? 'Prototype workspace' : 'Launch prototype'}</Link></>}>{idea.audience}</PageHeading>
    <div className="detail-meta"><Status value={idea.status} /><span><Clock3 size={14} />Updated {dateLabel(idea.updated)}</span><Badge>{getAccessToken() ? 'Authenticated API' : 'Offline preview'}</Badge></div>
    <div className="tabs" role="tablist">{['Overview', 'Requirements', 'Feedback', 'Versions'].map((value) => <button key={value} role="tab" aria-selected={tab === value} onClick={() => setTab(value)}>{value}{value === 'Feedback' && <span>{reviews.length}</span>}</button>)}</div>
    {tab === 'Overview' && <div className="detail-layout"><div><div className="detail-visual"><ProjectVisual idea={idea} /></div><section className="prose-section"><h2>The problem</h2><p>{idea.problem}</p><h2>The solution</h2><p>{idea.solution}</p></section><SectionHeading title="Core features" /><div className="feature-grid">{idea.features.map((feature, index) => <div key={feature}><span>{String(index + 1).padStart(2, '0')}</span><h3>{feature}</h3></div>)}</div></div><aside className="detail-aside"><h3>Review cycle</h3><strong className="big-number">{reviews.length}<small>feedback records</small></strong><Link className="button" to={`/feedback?idea=${idea.id}`}>Explore feedback<ArrowRight size={15} /></Link><hr /><h3>Constraints</h3><p>{idea.constraints || 'No constraints added.'}</p><hr /><h3>Reference files</h3>{getAccessToken() ? apiDetail?.assets.map((asset) => <button className="file-name" key={asset.id} onClick={() => void downloadAsset(asset)}><FileText size={14} />{asset.filename} · Download</button>) : idea.assets.map((asset) => <p className="file-name" key={asset}><FileText size={14} />{asset}</p>)}{!idea.assets.length && <p>No reference files.</p>}{getAccessToken() && idea.status === 'Draft' && <label className="upload-zone"><Upload size={18} /><strong>{assetBusy ? 'Uploading...' : 'Add reference files'}</strong><span>PDF, PNG, or JPG · up to 10 MB each</span><input aria-label="Add reference files" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" disabled={assetBusy} onChange={(event) => { void uploadAssets(event.target.files); event.target.value = '' }} /></label>}{assetError && <p role="alert" className="error">{assetError}</p>}<hr /><Link className="text-link" to={`/evolution?idea=${idea.id}`}>View evolution<ArrowUpRight size={15} /></Link></aside></div>}
    {tab === 'Requirements' && (getAccessToken()
      ? <RequirementAnalysisPanel ideaId={currentIdea.id} version={currentIdea.version} />
      : <section className="requirements"><div className="notice"><FileText size={19} /><div><strong>Offline preview brief</strong><p>This is owner-provided preview content. No AI workflow has run in offline preview mode.</p></div></div><dl><dt>Problem</dt><dd>{idea.problem}</dd><dt>Target users</dt><dd>{idea.audience}</dd><dt>Proposed solution</dt><dd>{idea.solution}</dd><dt>Features</dt><dd><ul>{idea.features.map((feature) => <li key={feature}>{feature}</li>)}</ul></dd><dt>Constraints</dt><dd>{idea.constraints || 'None specified'}</dd></dl></section>)}
    {tab === 'Feedback' && (reviews.length ? <div className="evidence-list">{reviews.map((review) => <article key={review.id}><div><strong>{review.reviewer}</strong><Badge>{review.sample ? 'Sample' : 'Local review'}</Badge><span>{review.rating}/5</span></div><p>{review.improvements}</p><small>{review.context}</small><Link className="text-link" to={`/feedback?idea=${idea.id}#${review.id}`}>View evidence<ArrowUpRight size={14} /></Link></article>)}</div> : <Empty title="No feedback for this idea yet" />)}
    {tab === 'Versions' && <><SectionHeading title="Saved immutable versions" />{getAccessToken() && role === 'owner' && idea.status !== 'Archived' && <button className="button primary" onClick={openVersionDialog}><Plus size={15} />Create version</button>}<div className="version-list">{(getAccessToken() ? apiVersions : [idea]).map((version) => {
      const provenance = apiDetail?.versions.find((item) => item.version === version.version)
      return <div key={`${version.id}-${version.version}`}><Badge tone="green">V{version.version}</Badge><h3>{version.version === 1 ? 'Original idea version' : `Saved version ${version.version}`}</h3><p>{version.solution}</p><small>{provenance?.change_summary ?? 'Immutable owner-authored snapshot'}{provenance?.source_version_id ? ` · Derived from V${version.version - 1}` : ''}</small><p>{provenance?.version_created_at ? dateLabel(provenance.version_created_at) : ''}</p>{getAccessToken() && role === 'owner' && currentIdea.status !== 'Archived' && <button className="button" disabled={publishingVersion !== null} onClick={() => void publishApiVersion(version.version)}>{publishingVersion === version.version ? 'Publishing...' : `Publish V${version.version} for review`}</button>}</div>
    })}{!getAccessToken() && state.evolutions.filter((evolution) => evolution.ideaId === idea.id).map((evolution) => <div key={evolution.id}><Badge tone="blue">V{evolution.target} proposal</Badge><h3>Evidence-linked change set</h3><ul>{evolution.changes.map((change) => <li key={change}>{change}</li>)}</ul><Link className="text-link" to={`/evolution?idea=${idea.id}`}>Compare versions<ArrowRight size={14} /></Link></div>)}</div>{versionDialog && <Modal title="Create an immutable idea version" onClose={() => setVersionDialog(false)}><form className="modal-form" onSubmit={saveVersion}>{(['title', 'category', 'audience', 'problem', 'solution', 'features', 'constraints'] as const).map((field) => <label key={field}>{field === 'features' ? 'Core features (one per line)' : field[0].toUpperCase() + field.slice(1)}{field === 'problem' || field === 'solution' || field === 'features' || field === 'constraints' ? <textarea required={field !== 'constraints'} rows={field === 'features' ? 4 : 3} value={versionInput[field]} onChange={(event) => setVersionInput((current) => ({ ...current, [field]: event.target.value }))} /> : <input required value={versionInput[field]} onChange={(event) => setVersionInput((current) => ({ ...current, [field]: event.target.value }))} />}</label>)}<label>Change summary<input required value={changeSummary} onChange={(event) => setChangeSummary(event.target.value)} /></label>{versionError && <p role="alert" className="error">{versionError}</p>}<button className="button primary" disabled={versionBusy || !changeSummary.trim()}>{versionBusy ? 'Saving...' : 'Save new version'}</button></form></Modal>}</>}
    {publishError && <p role="alert" className="error">{publishError}</p>}
  </>
}

function RequirementAnalysisPanel({ ideaId, version }: { ideaId: string; version: number }) {
  const [analysis, setAnalysis] = useState<RequirementAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let active = true
    let timer: number | undefined
    async function refresh() {
      try {
        const result = await getLatestRequirementAnalysis(ideaId, version)
        if (!active) return
        setAnalysis(result)
        setError('')
        if (result && (result.status === 'queued' || result.status === 'running')) {
          timer = window.setTimeout(() => void refresh(), 1800)
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : 'Requirement status could not be loaded.')
      } finally {
        if (active) setLoading(false)
      }
    }
    void refresh()
    return () => {
      active = false
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [ideaId, version, refreshKey])

  async function start() {
    setStarting(true)
    setError('')
    try {
      const run = await startRequirementAnalysis(ideaId, version)
      setAnalysis(run)
      setRefreshKey((current) => current + 1)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The Requirement Agent could not be started.')
    } finally {
      setStarting(false)
    }
  }

  function renderFacts(title: string, facts: RequirementFact[]) {
    return <section key={title}><h3>{title}</h3>{facts.length
      ? <ul>{facts.map((fact, index) => <li key={`${fact.text}-${index}`}><span>{fact.text}</span> <Badge tone={fact.basis === 'assumption' ? 'blue' : 'green'}>{fact.basis}</Badge><small>Source: {fact.source_fields.join(', ')}</small></li>)}</ul>
      : <p className="muted">No supported items identified from this version.</p>}</section>
  }

  const result = analysis?.result
  return <section className="requirements">
    <div className="notice"><FileText size={19} /><div><strong>Requirement Agent · immutable source V{version}</strong><p>Analysis runs in the backend worker. Inferred details are labeled as assumptions; missing information remains an open question.</p></div></div>
    <div className="form-actions"><button className="button primary" onClick={() => void start()} disabled={starting || loading || analysis?.status === 'queued' || analysis?.status === 'running'}>{starting ? 'Starting analysis...' : analysis?.status === 'completed' ? 'Run again' : 'Analyze requirements'}</button>{analysis && <Status value={analysis.status} />}</div>
    {loading && <p role="status">Loading saved requirement analysis...</p>}
    {error && <p role="alert" className="error">{error} <button className="text-link" onClick={() => setRefreshKey((current) => current + 1)}>Retry status check</button></p>}
    {analysis && <div aria-live="polite">
      <p><strong>Workflow:</strong> {analysis.workflow_run_id} · {analysis.provider} / {analysis.model_version} · prompt {analysis.prompt_version}</p>
      {(analysis.status === 'queued' || analysis.status === 'running') && <p role="status">{analysis.status === 'queued' ? 'Waiting for a worker...' : 'Analyzing the immutable source version...'}</p>}
      {analysis.error_message && <p role="alert" className="error">{analysis.error_message}</p>}
      {result && <>
        <p><Badge tone="green">Schema validated</Badge> Source V{analysis.source_version} · {analysis.completed_at ? dateLabel(analysis.completed_at) : ''}</p>
        {renderFacts('Problem understanding', result.problem)}
        {renderFacts('Target users', result.target_users)}
        <section><h3>User journeys</h3>{result.user_journeys.length ? result.user_journeys.map((journey, index) => <article key={`${journey.actor.text}-${index}`}><h4>{journey.actor.text}</h4><p>Need: {journey.need.text}</p><ol>{journey.steps.map((step, stepIndex) => <li key={`${step}-${stepIndex}`}>{step}</li>)}</ol><p>Outcome: {journey.outcome.text}</p></article>) : <p className="muted">No journeys could be grounded from the supplied brief.</p>}</section>
        {renderFacts('Core features', result.core_features)}
        {renderFacts('Constraints', result.constraints)}
        {renderFacts('Acceptance criteria', result.acceptance_criteria)}
        <section><h3>Assumptions</h3>{result.assumptions.length ? <ul>{result.assumptions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <p className="muted">No assumptions recorded.</p>}</section>
        <section><h3>Open questions</h3>{result.open_questions.length ? <ul>{result.open_questions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <p className="muted">No open questions recorded.</p>}</section>
        {analysis.status === 'completed' && analysis.validation_status === 'valid' &&
          <PrototypeSourcePanel
            ideaId={ideaId}
            version={version}
            requirementAnalysisId={analysis.id}
          />}
      </>}
    </div>}
  </section>
}

function PrototypeSourcePanel({
  ideaId,
  version,
  requirementAnalysisId,
}: {
  ideaId: string
  version: number
  requirementAnalysisId: string
}) {
  const [build, setBuild] = useState<PrototypeBuild | null>(null)
  const [source, setSource] = useState<PrototypeSource | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [sourceLoading, setSourceLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getLatestPrototypeSource(ideaId, version)
      .then((result) => { if (active) setBuild(result) })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Prototype status could not be loaded.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [ideaId, version])

  async function generate() {
    setGenerating(true)
    setError('')
    try {
      setBuild(await generatePrototypeSource(ideaId, version, requirementAnalysisId))
      setSource(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Prototype source could not be generated.')
    } finally {
      setGenerating(false)
    }
  }

  async function loadSource() {
    if (!build) return
    setSourceLoading(true)
    setError('')
    try {
      setSource(await getPrototypeSourceFiles(ideaId, version, build.id))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Generated source could not be retrieved.')
    } finally {
      setSourceLoading(false)
    }
  }

  return <section className="prototype-source-panel">
    <h3>Safe prototype source</h3>
    <p>
      This limited template supports education placement preparation. Generated source
      is stored separately and statically checked; it is never run by the API or worker.
    </p>
    {loading && <p role="status">Loading prototype source status...</p>}
    {!loading && !build && <button
      className="button primary"
      disabled={generating}
      onClick={() => void generate()}
    >{generating ? 'Generating source...' : 'Generate prototype source'}</button>}
    {error && <p role="alert" className="error">{error}</p>}
    {build && <div aria-live="polite">
      <p><strong>Source:</strong> {build.status.replaceAll('_', ' ')} · V{build.source_version}</p>
      <p><strong>Static validation:</strong> {build.validation_status}</p>
      <p role="status"><strong>Build:</strong> blocked — an isolated disposable build environment is not available.</p>
      <p><strong>Generated source:</strong> unpublished and not executed. The browser preview below renders only the supported saved specification.</p>
      {build.error_message && <p role="alert" className="error">{build.error_message}</p>}
      {build.plan?.preview_spec && <SchemaPrototypePreview spec={build.plan.preview_spec} />}
      {build.source_files.length > 0 && <>
        <ul>{build.source_files.map((file) => <li key={file.path}>{file.path} · {file.size_bytes} bytes</li>)}</ul>
        <button
          className="button"
          disabled={sourceLoading}
          onClick={() => source ? setSource(null) : void loadSource()}
        >{sourceLoading ? 'Loading source...' : source ? 'Hide generated source' : 'View generated source'}</button>
      </>}
      {source && <div className="generated-source">
        {Object.entries(source.files).map(([path, contents]) => <details key={path}>
          <summary>{path}</summary>
          <pre><code>{contents}</code></pre>
        </details>)}
      </div>}
      <p className="muted">Static checks are not a build, runtime test, or security review.</p>
    </div>}
  </section>
}

export function ReviewQueue() {
  const { state } = useWorkspace()
  const [apiAssignments, setApiAssignments] = useState<ReviewerAssignment[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!getAccessToken()) return
    let active = true
    setLoading(true)
    listReviewerAssignments()
      .then((assignments) => { if (active) setApiAssignments(assignments) })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Assignments could not be loaded.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  if (getAccessToken()) {
    if (loading) return <div role="status" className="empty">Loading assigned idea versions...</div>
    return <><PageHeading eyebrow="AUTHENTICATED REVIEWER" title="Your assigned idea versions.">Only active assignments for your signed-in account are shown.</PageHeading>
      {error && <p role="alert" className="error">{error}</p>}
      {apiAssignments.length ? <div className="assignment-list">{apiAssignments.map((assignment) => <article className="assignment" key={assignment.id}><div className="assignment-brief"><Badge>Version {assignment.version}</Badge><h2>{assignment.idea_title}</h2><p>{assignment.solution}</p><small>Assigned {new Date(assignment.assigned_at).toLocaleDateString()}</small></div><Link className="button primary" to={`/reviews/${assignment.id}`}>{assignment.review_submitted ? 'View assignment' : 'Review assigned version'}<ArrowRight size={16} /></Link><p className="muted">{assignment.review_submitted ? 'Review submitted' : 'Review not submitted'}</p></article>)}</div> : !error && <Empty title="No active assignments"><p>Version-specific assignments will appear here when an administrator assigns them.</p></Empty>}
    </>
  }
  const assignments = state.assignments.filter((assignment) => assignment.reviewer === 'Maya Chen')
  return <><PageHeading eyebrow="REVIEWER PORTAL / MAYA CHEN" title="A fresh perspective starts here.">Your assigned prototypes and review sessions.</PageHeading><div className="notice"><Users size={19} /><div><strong>Preview reviewer identity</strong><p>Maya Chen · Assigned projects only · Real authentication pending</p></div></div><SectionHeading title="Your assignments" />
    {assignments.length ? <div className="assignment-list">{assignments.map((assignment) => {
      const idea = state.ideas.find((candidate) => candidate.id === assignment.ideaId)
      if (!idea) return null
      return <article className="assignment" key={assignment.id}><ProjectVisual idea={idea} /><div><div className="card-meta"><Badge>{idea.category}</Badge><Status value={assignment.status} /></div><h2>{idea.title}</h2><p>{idea.solution}</p><span className="muted">Prototype V{idea.version}</span></div><Link className="button primary" to={`/reviews/${idea.id}`}>{assignment.status === 'Completed' ? 'View review' : 'Start review'}<ArrowRight size={16} /></Link></article>
    })}</div> : <Empty title="No assignments yet"><p>Assigned review cycles will appear here.</p></Empty>}
  </>
}