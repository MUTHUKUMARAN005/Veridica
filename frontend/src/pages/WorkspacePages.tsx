import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useForm } from 'react-hook-form'
import { ArrowLeft, ArrowRight, ArrowUpRight, CheckCircle2, Clock3, Compass, FileText, GitBranch, Lightbulb, MessageSquare, Play, Plus, Search, Sparkles, Upload, UserCheck, Users } from 'lucide-react'
import { addIdea, ideaReviews, publishIdea } from '@/services/preview'
import type { Idea } from '@/services/preview'
import { useWorkspace } from '@/services/workspace'
import { Badge, ConfirmModal, dateLabel, Empty, ErrorBanner, LoadingState, Modal, PageHeading, sanitizeUserMessage, SectionHeading, Status } from '@/components/ui'
import { ProjectVisual } from '@/components/ProjectVisual'
import { IdeaFeed } from '@/components/IdeaFeed'
import { SchemaPrototypePreview } from '@/components/SchemaPrototypePreview'
import {
  createIdea,
  createIdeaVersion,
  downloadIdeaAsset,
  generatePrototypeSource,
  getEvolutionProposal,
  getIdea,
  getLatestPrototypeSource,
  getLatestRequirementAnalysis,
  listIdeas,
  listPersistedFeedback,
  publishIdeaVersion,
  startRequirementAnalysis,
  toPreviewIdea,
  updateIdeaStatus,
  uploadIdeaAsset,
} from '@/services/ideas'
import type {
  ApiIdeaDetail,
  EvolutionProposal,
  PersistedReview,
  PrototypeBuild,
  RequirementAnalysis,
  RequirementFact,
} from '../services/ideas'
import { getAccessToken, getCurrentUser } from '../services/auth'
import { listReviewerAssignments } from '../services/authorization'
import type { ReviewerAssignment } from '../services/authorization'

export function ProjectCard({ idea }: { idea: Idea }) {
  const { state } = useWorkspace()
  const count = ideaReviews(state, idea.id).length
  return <article className="project-card">
    <Link to={`/ideas/${idea.id}`}><ProjectVisual idea={idea} /></Link>
    <div className="project-info"><div className="card-meta"><span>{idea.category}</span><Status value={idea.status} /></div>
      <h3><Link to={`/ideas/${idea.id}`}>{idea.title}</Link></h3><p>{idea.solution}</p>
      <div className="card-footer"><span><MessageSquare size={14} />{getAccessToken() ? 'Workspace idea' : `${count} reviews`}</span><span>V{idea.version}</span><Link aria-label={`Open ${idea.title}`} title={`Open ${idea.title}`} to={`/ideas/${idea.id}`}><ArrowUpRight size={19} /></Link></div>
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
  const [reloadKey, setReloadKey] = useState(0)

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
        if (active) setApiError(sanitizeUserMessage(error, 'We could not load your ideas right now. Please try again.'))
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [offset, status, category, query, reloadKey])

  const sourceIdeas = getAccessToken() ? apiIdeas : state.ideas
  const ideas = sourceIdeas.filter((idea) => {
    if (prototypes && idea.status === 'Draft') return false
    if (getAccessToken()) return true
    return `${idea.title} ${idea.category}`.toLowerCase().includes(query.toLowerCase())
      && (status === 'All statuses' || idea.status === status)
      && (category === 'All categories' || idea.category === category)
  })
  const displayedCount = getAccessToken() ? total : ideas.length
  if (loading) return <LoadingState title="Loading your ideas..." description="Fetching your latest project versions and statuses." />
  return <><PageHeading eyebrow="WORKSPACE" title={prototypes ? 'Prototype library' : 'Your ideas'} actions={role !== 'reviewer' && <Link className="button primary" to="/ideas/new"><Plus size={17} />New idea</Link>}>{prototypes ? 'Reviewable spaces, connected to the ideas behind them.' : 'From the first question to the next version.'}</PageHeading>
    <div className="filter-bar"><label className="search-field"><Search size={17} /><input aria-label="Search ideas" placeholder="Search ideas" value={query} onChange={(event) => { setQuery(event.target.value); setOffset(0) }} /></label><select aria-label="Idea status" value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0) }}>{['All statuses', 'Draft', 'Ready for review', 'Review open', 'Evolution ready', 'Archived'].map((value) => <option key={value}>{value}</option>)}</select><select aria-label="Idea category" value={category} onChange={(event) => { setCategory(event.target.value); setOffset(0) }}>{['All categories', 'Education', 'Sustainability', 'Community', 'Healthcare', 'Productivity', 'Other'].map((value) => <option key={value}>{value}</option>)}</select><span className="filter-count">{displayedCount} {displayedCount === 1 ? 'idea' : 'ideas'}</span></div>
    {apiError && <ErrorBanner message={apiError} onRetry={() => setReloadKey((value) => value + 1)} />}
    {ideas.length ? <div className="project-grid library">{ideas.map((idea) => <ProjectCard idea={idea} key={idea.id} />)}</div> : !apiError && <Empty title="No matching ideas"><p>Try another search filter or create a new idea to get started.</p></Empty>}
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
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<IdeaForm>({ defaultValues: { category: 'Education' } })
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
        const message = sanitizeUserMessage(error, 'We could not save your idea right now. Please try again.')
        if (savedIdeaId) {
          setPartialSavedIdeaId(savedIdeaId)
          setSaveError(`Your idea was saved, but an attachment could not be uploaded: ${message}`)
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
    }, 'Idea saved in your browser preview workspace.')
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
      }} /><small>{getAccessToken() ? 'Files upload privately to your idea workspace.' : 'Filenames only in browser preview. No files are uploaded.'}</small></label>{assets.map((asset) => <p className="file-name" key={asset}><FileText size={14} />{asset}</p>)}
    </section>{saveError && <p role="alert" className="error">{saveError}{partialSavedIdeaId && <> <Link to={`/ideas/${partialSavedIdeaId}`}>Open the saved idea</Link></>}</p>}<div className="form-actions"><Link className="button" to="/ideas">Cancel</Link><button className="button primary" disabled={isSubmitting} type="submit">{isSubmitting ? 'Saving...' : 'Save idea'}<ArrowRight size={16} /></button></div></form>
    <aside className="form-aside"><Lightbulb size={27} /><h3>Start with something specific.</h3><p>A clear problem and a focused first version make room for more useful feedback.</p><hr /><span className="eyebrow">WHAT COMES NEXT</span><ol><li>Requirements</li><li>Visual prototype</li><li>Reviewer feedback</li><li>Evidence-led evolution</li></ol><Badge tone="blue">Guided validation</Badge></aside></div>
  </>
}

export function IdeaDetails() {
  const { id } = useParams()
  const { state, update, role, notify } = useWorkspace()
  const [apiDetail, setApiDetail] = useState<ApiIdeaDetail | null>(null)
  const [apiIdea, setApiIdea] = useState<ReturnType<typeof toPreviewIdea> | null>(null)
  const [apiVersions, setApiVersions] = useState<ReturnType<typeof toPreviewIdea>[]>([])
  const [persistedReviews, setPersistedReviews] = useState<PersistedReview[]>([])
  const [latestRequirement, setLatestRequirement] = useState<RequirementAnalysis | null>(null)
  const [latestPrototype, setLatestPrototype] = useState<PrototypeBuild | null>(null)
  const [evolutionProposal, setEvolutionProposal] = useState<EvolutionProposal | null>(null)
  const [apiLoading, setApiLoading] = useState(false)
  const [apiError, setApiError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [versionDialog, setVersionDialog] = useState(false)
  const [versionBusy, setVersionBusy] = useState(false)
  const [versionError, setVersionError] = useState('')
  const [archiveConfirm, setArchiveConfirm] = useState(false)
  const [statusBusy, setStatusBusy] = useState(false)
  const [assetBusy, setAssetBusy] = useState(false)
  const [assetError, setAssetError] = useState('')
  const [publishingVersion, setPublishingVersion] = useState<number | null>(null)
  const [publishError, setPublishError] = useState('')
  const [versionInput, setVersionInput] = useState({
    title: '', category: '', problem: '', solution: '', audience: '', features: '', constraints: '',
  })
  const [changeSummary, setChangeSummary] = useState('')
  const [tab, setTab] = useState('Overview')

  useEffect(() => {
    if (!id || !getAccessToken()) return
    let active = true
    setApiError('')
    setApiLoading(true)
    getIdea(id)
      .then(async (result) => {
        if (!active) return
        setApiDetail(result)
        setApiIdea(toPreviewIdea(result))
        setApiVersions(result.versions.map((version) => toPreviewIdea(version)))
        const [reviewsResult, reqResult, protoResult, evoResult] = await Promise.all([
          listPersistedFeedback(id, result.version).catch(() => [] as PersistedReview[]),
          getLatestRequirementAnalysis(id, result.version).catch(() => null),
          getLatestPrototypeSource(id, result.version).catch(() => null),
          getEvolutionProposal(id, result.version).catch(() => null),
        ])
        if (!active) return
        setPersistedReviews(reviewsResult)
        setLatestRequirement(reqResult)
        setLatestPrototype(protoResult)
        setEvolutionProposal(evoResult)
      })
      .catch((reason: unknown) => {
        if (active) setApiError(sanitizeUserMessage(reason, 'The idea could not be loaded right now.'))
      })
      .finally(() => { if (active) setApiLoading(false) })
    return () => { active = false }
  }, [id, reloadKey])

  const isAuthenticated = Boolean(getAccessToken())
  const idea = isAuthenticated
    ? apiIdea?.id === id ? apiIdea : undefined
    : state.ideas.find((candidate) => candidate.id === id)

  if (!idea) {
    if (apiLoading) return <LoadingState title="Loading your idea..." description="Retrieving version history, requirements, and reviewer feedback." />
    return <Empty title={apiError ? 'Idea unavailable' : 'Idea not found'}>
      {apiError && <ErrorBanner message={apiError} onRetry={() => setReloadKey((value) => value + 1)} />}
      <Link className="button" to="/ideas">Back to ideas</Link>
    </Empty>
  }

  const currentIdea = idea
  const previewReviews = ideaReviews(state, currentIdea.id)
  const feedbackCount = isAuthenticated ? persistedReviews.length : previewReviews.length
  const currentUser = getCurrentUser()
  const ownerDisplay = isAuthenticated ? (currentUser?.email ?? 'Workspace owner') : 'Idea owner'
  const prototypeAvailable = isAuthenticated
    ? Boolean(latestPrototype && latestPrototype.validation_status === 'passed' && latestPrototype.plan?.preview_spec)
    : ['placement', 'circular'].includes(currentIdea.id)

  function getNextRecommendedAction(): { title: string; description: string; actionLabel: string; onAction?: () => void; to?: string } {
    if (!isAuthenticated) {
      if (currentIdea.status === 'Draft') {
        return {
          title: 'Review your structured brief',
          description: 'Inspect the Requirements tab to verify your problem statement, target audience, and core features.',
          actionLabel: 'Open requirements',
          onAction: () => setTab('Requirements'),
        }
      }
      if (currentIdea.status === 'Ready for review') {
        return {
          title: 'Open the review cycle',
          description: 'Your sample prototype is ready. Publish this version so reviewers can explore and submit feedback.',
          actionLabel: 'Publish for review',
          onAction: () => update((current) => publishIdea(current, currentIdea.id), 'Preview review cycle opened.'),
        }
      }
      return {
        title: 'Evaluate reviewer feedback',
        description: 'Prioritize reviewer suggestions and prepare an evidence-backed V2 change proposal.',
        actionLabel: 'Prioritize improvements',
        to: `/evolution?idea=${currentIdea.id}`,
      }
    }

    if (!latestRequirement || latestRequirement.status !== 'completed') {
      return {
        title: 'Generate structured requirements',
        description: 'Analyze your Version ' + currentIdea.version + ' brief to produce user journeys, functional requirements, and acceptance criteria.',
        actionLabel: 'Open requirements',
        onAction: () => setTab('Requirements'),
      }
    }
    if (!prototypeAvailable) {
      return {
        title: 'Prepare interactive prototype preview',
        description: 'Your requirements are ready. Generate the interactive prototype specification from the Requirements tab.',
        actionLabel: 'Prepare prototype',
        onAction: () => setTab('Requirements'),
      }
    }
    if (currentIdea.status === 'Draft' || currentIdea.status === 'Ready for review') {
      return {
        title: `Publish Version ${currentIdea.version} for reviewer feedback`,
        description: 'Your interactive prototype preview is ready. Publish this version so assigned reviewers can test it.',
        actionLabel: 'Manage versions',
        onAction: () => setTab('Versions'),
      }
    }
    if (persistedReviews.length > 0 && !evolutionProposal) {
      return {
        title: 'Analyze feedback & evolve to the next version',
        description: `${persistedReviews.length} review${persistedReviews.length === 1 ? ' has' : 's have'} been submitted. Run feedback intelligence and create a V${currentIdea.version + 1} proposal.`,
        actionLabel: 'Open analytics',
        to: '/analytics',
      }
    }
    return {
      title: 'Collect reviewer perspectives',
      description: 'Version ' + currentIdea.version + ' is open for review. Once reviewers submit feedback, insights will appear in Feedback and Analytics.',
      actionLabel: 'View feedback',
      onAction: () => setTab('Feedback'),
    }
  }

  const nextAction = getNextRecommendedAction()

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
      setVersionError(sanitizeUserMessage(reason, 'The new version could not be saved.'))
    } finally {
      setVersionBusy(false)
    }
  }

  async function changeApiStatus(status: 'Draft' | 'Archived') {
    setStatusBusy(true)
    try {
      const saved = await updateIdeaStatus(currentIdea.id, status)
      setApiDetail((current) => current ? { ...current, ...saved } : current)
      setApiIdea(toPreviewIdea(saved))
      setArchiveConfirm(false)
      notify(status === 'Archived' ? 'Idea archived.' : 'Idea restored.')
    } catch (reason) {
      notify(sanitizeUserMessage(reason, 'The idea status could not be changed.'))
    } finally {
      setStatusBusy(false)
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
      setPublishError(sanitizeUserMessage(reason, 'The version could not be published.'))
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
      setAssetError(sanitizeUserMessage(reason, 'The reference file could not be uploaded.'))
    } finally {
      setAssetBusy(false)
    }
  }

  async function downloadAsset(asset: NonNullable<ApiIdeaDetail['assets']>[number]) {
    try {
      await downloadIdeaAsset(currentIdea.id, currentIdea.version, asset.id, asset.filename)
    } catch (reason) {
      notify(sanitizeUserMessage(reason, 'The reference file could not be downloaded.'))
    }
  }

  return <>
    <Link className="back-link" to="/ideas"><ArrowLeft size={15} />Your ideas</Link>
    <PageHeading
      eyebrow={`${idea.category.toUpperCase()} / V${idea.version}`}
      title={idea.title}
      actions={<>
        {isAuthenticated && role === 'owner' && idea.status === 'Archived' && <button className="button" disabled={statusBusy} onClick={() => void changeApiStatus('Draft')}>Restore idea</button>}
        {isAuthenticated && role === 'owner' && idea.status === 'Draft' && <button className="button" disabled={statusBusy} onClick={() => setArchiveConfirm(true)}>Archive idea</button>}
        {!isAuthenticated && idea.status === 'Ready for review' && role !== 'reviewer' && <button className="button" onClick={() => update((current) => publishIdea(current, idea.id), 'Preview review cycle opened.')}>Publish for review</button>}
        {prototypeAvailable
          ? <Link className="button primary" to={`/ideas/${idea.id}/prototype`}><Play size={16} />Launch prototype</Link>
          : isAuthenticated
            ? <button type="button" className="button" onClick={() => setTab('Requirements')}><Compass size={16} />Prepare prototype</button>
            : <Link className="button" to={`/ideas/${idea.id}/prototype`}><Play size={16} />Prototype workspace</Link>}
      </>}
    >{idea.audience}</PageHeading>

    <div className="detail-meta">
      <Status value={idea.status} />
      <span><UserCheck size={14} />Owner: {ownerDisplay}</span>
      <span><GitBranch size={14} />Version {idea.version}</span>
      <span><Clock3 size={14} />Updated {dateLabel(idea.updated)}</span>
      {!isAuthenticated && <Badge>Offline preview</Badge>}
    </div>

    <div className="tabs" role="tablist">
      {['Overview', 'Requirements', 'Feedback', 'Versions'].map((value) => <button key={value} role="tab" aria-selected={tab === value} onClick={() => setTab(value)}>
        {value}{value === 'Feedback' && <span>{feedbackCount}</span>}
      </button>)}
    </div>

    {tab === 'Overview' && <div className="detail-layout">
      <div>
        <div className="detail-visual"><ProjectVisual idea={idea} /></div>
        <section className="next-action-card" aria-label="Recommended next step">
          <div className="next-action-copy">
            <span className="eyebrow">NEXT RECOMMENDED ACTION</span>
            <h3>{nextAction.title}</h3>
            <p>{nextAction.description}</p>
          </div>
          {nextAction.to
            ? <Link className="button primary" to={nextAction.to}>{nextAction.actionLabel}<ArrowRight size={15} /></Link>
            : <button type="button" className="button primary" onClick={nextAction.onAction}>{nextAction.actionLabel}<ArrowRight size={15} /></button>}
        </section>
        {!prototypeAvailable && <div className="notice">
          <Compass size={19} />
          <div>
            <strong>Interactive prototype preview is not ready yet</strong>
            <p>{isAuthenticated ? 'Generate requirements and build your interactive prototype specification in the Requirements tab before launching the preview.' : 'This draft idea does not have a generated prototype yet.'}</p>
          </div>
        </div>}
        <section className="prose-section">
          <h2>The problem</h2>
          <p>{idea.problem}</p>
          <h2>The solution</h2>
          <p>{idea.solution}</p>
        </section>
        <SectionHeading title="Core features" />
        <div className="feature-grid">
          {idea.features.map((feature, index) => <div key={feature}><span>{String(index + 1).padStart(2, '0')}</span><h3>{feature}</h3></div>)}
        </div>
      </div>
      <aside className="detail-aside">
        <h3>Project summary</h3>
        <dl className="summary-meta-list">
          <div><dt>Owner</dt><dd>{ownerDisplay}</dd></div>
          <div><dt>Current version</dt><dd>V{idea.version}</dd></div>
          <div><dt>Lifecycle status</dt><dd>{idea.status}</dd></div>
          <div><dt>Prototype status</dt><dd>{prototypeAvailable ? 'Interactive preview ready' : 'Awaiting generation'}</dd></div>
        </dl>
        <hr />
        <h3>Review cycle</h3>
        <strong className="big-number">{feedbackCount}<small>feedback {feedbackCount === 1 ? 'record' : 'records'}</small></strong>
        <Link className="button" to={`/feedback?idea=${idea.id}`}>Explore feedback<ArrowRight size={15} /></Link>
        <hr />
        <h3>Constraints</h3>
        <p>{idea.constraints || 'No constraints added.'}</p>
        <hr />
        <h3>Reference files</h3>
        {isAuthenticated
          ? apiDetail?.assets.map((asset) => <button className="file-name" key={asset.id} onClick={() => void downloadAsset(asset)}><FileText size={14} />{asset.filename} · Download</button>)
          : idea.assets.map((asset) => <p className="file-name" key={asset}><FileText size={14} />{asset}</p>)}
        {!idea.assets.length && <p>No reference files.</p>}
        {isAuthenticated && idea.status === 'Draft' && <label className="upload-zone"><Upload size={18} /><strong>{assetBusy ? 'Uploading...' : 'Add reference files'}</strong><span>PDF, PNG, or JPG · up to 10 MB each</span><input aria-label="Add reference files" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" disabled={assetBusy} onChange={(event) => { void uploadAssets(event.target.files); event.target.value = '' }} /></label>}
        {assetError && <ErrorBanner message={assetError} />}
        <hr />
        <Link className="text-link" to={`/evolution?idea=${idea.id}`}>View evolution<ArrowUpRight size={15} /></Link>
      </aside>
    </div>}

    {tab === 'Requirements' && (isAuthenticated
      ? <RequirementAnalysisPanel
        ideaId={currentIdea.id}
        version={currentIdea.version}
        onAnalysisUpdate={(analysis) => setLatestRequirement(analysis)}
        onPrototypeUpdate={(prototype) => setLatestPrototype(prototype)}
      />
      : <section className="requirements"><div className="notice"><FileText size={19} /><div><strong>Offline preview brief</strong><p>This is owner-provided preview content. No AI workflow has run in offline preview mode.</p></div></div><dl><dt>Problem</dt><dd>{idea.problem}</dd><dt>Target users</dt><dd>{idea.audience}</dd><dt>Proposed solution</dt><dd>{idea.solution}</dd><dt>Features</dt><dd><ul>{idea.features.map((feature) => <li key={feature}>{feature}</li>)}</ul></dd><dt>Constraints</dt><dd>{idea.constraints || 'None specified'}</dd></dl></section>)}

    {tab === 'Feedback' && (isAuthenticated
      ? (persistedReviews.length
        ? <div className="feedback-detail-list">
          {persistedReviews.map((review, index) => <article className="feedback-detail" key={review.id}>
            <header>
              <span className="avatar">RV</span>
              <div>
                <strong>Verified reviewer #{index + 1}</strong>
                <small>{currentIdea.title} · V{currentIdea.version} · {dateLabel(review.created_at)}</small>
              </div>
              <Status value="Submitted" />
              <span className="review-score">{review.rating}<small>/5</small></span>
            </header>
            <div className="feedback-dimensions">
              {([
                ['Usability', review.usability_score],
                ['Usefulness', review.usefulness_score],
                ['Feasibility', review.feasibility_score],
                ['Completeness', review.completeness_score],
              ] as const).map(([label, score]) => score !== null && <span key={label}>{label}<strong>{score}/5</strong></span>)}
              {review.would_use !== null && <span>Would use<strong>{review.would_use ? 'Yes' : 'Not yet'}</strong></span>}
            </div>
            <p>{review.feedback_text}</p>
            <div className="feedback-columns">
              <section><span className="eyebrow">STRENGTHS</span><p>{review.strengths}</p></section>
              <section><span className="eyebrow">CONCERNS</span><p>{review.concerns}</p></section>
            </div>
            {review.suggested_improvements && <div className="improvement">
              <Sparkles size={16} />
              <div><strong>Suggested improvement</strong><p>{review.suggested_improvements}</p></div>
            </div>}
            <footer>
              <p><MessageSquare size={13} />{review.usage_context || `Reviewed Version ${currentIdea.version}`}</p>
              <Link className="text-link" to="/analytics">View feedback analytics<ArrowUpRight size={14} /></Link>
            </footer>
          </article>)}
        </div>
        : <Empty title="No reviewer feedback submitted yet">
          <p>Publish Version {currentIdea.version} and assign reviewers to collect structured feedback on this version.</p>
        </Empty>)
      : (previewReviews.length
        ? <div className="evidence-list">{previewReviews.map((review) => <article key={review.id}><div><strong>{review.reviewer}</strong><Badge>{review.sample ? 'Sample' : 'Local review'}</Badge><span>{review.rating}/5</span></div><p>{review.improvements}</p><small>{review.context}</small><Link className="text-link" to={`/feedback?idea=${idea.id}#${review.id}`}>View evidence<ArrowUpRight size={14} /></Link></article>)}</div>
        : <Empty title="No feedback for this idea yet"><p>Publish this version and collect reviewer feedback to see insights here.</p></Empty>))}

    {tab === 'Versions' && <>
      <SectionHeading title="Saved immutable versions" />
      {isAuthenticated && role === 'owner' && idea.status !== 'Archived' && <button className="button primary" onClick={openVersionDialog}><Plus size={15} />Create version</button>}
      <div className="version-list">
        {(isAuthenticated ? apiVersions : [idea]).map((version) => {
          const provenance = apiDetail?.versions.find((item) => item.version === version.version)
          const versionStatus = provenance?.status ?? version.status
          return <div key={`${version.id}-${version.version}`}>
            <div className="version-card-top">
              <Badge tone="green">V{version.version} · Immutable source</Badge>
              <Status value={versionStatus} />
            </div>
            <h3>{version.version === 1 ? 'Original idea version' : `Saved version ${version.version}`}</h3>
            <p>{version.solution}</p>
            <small>{provenance?.change_summary ?? 'Immutable owner-authored snapshot'}{provenance?.source_version_id ? ` · Derived from V${version.version - 1}` : ''}</small>
            <p>{provenance?.version_created_at ? dateLabel(provenance.version_created_at) : ''}</p>
            {isAuthenticated && role === 'owner' && currentIdea.status !== 'Archived' && versionStatus !== 'Review open' && <button className="button" disabled={publishingVersion !== null} onClick={() => void publishApiVersion(version.version)}>{publishingVersion === version.version ? 'Publishing...' : `Publish V${version.version} for review`}</button>}
          </div>
        })}
        {isAuthenticated && evolutionProposal && <div key={evolutionProposal.id}>
          <div className="version-card-top">
            <Badge tone="blue">{evolutionProposal.status === 'approved' ? `V${String(evolutionProposal.validation_results.target_version ?? currentIdea.version + 1)} candidate` : `V${currentIdea.version + 1} proposal`}</Badge>
            <Status value={evolutionProposal.status === 'approved' ? 'approved' : 'proposed'} />
          </div>
          <h3>{evolutionProposal.status === 'approved' ? 'Approved evolution candidate' : 'Proposed evolution changes'}</h3>
          <ul>{evolutionProposal.suggestions.map((item) => <li key={item.rank}>{item.title}</li>)}</ul>
          <small>Derived from Version {evolutionProposal.source_version} reviewer feedback</small>
          <p><Link className="text-link" to={`/evolution?idea=${idea.id}`}>Review evolution details<ArrowRight size={14} /></Link></p>
        </div>}
        {!isAuthenticated && state.evolutions.filter((evolution) => evolution.ideaId === idea.id).map((evolution) => <div key={evolution.id}><Badge tone="blue">V{evolution.target} proposal</Badge><h3>Evidence-linked change set</h3><ul>{evolution.changes.map((change) => <li key={change}>{change}</li>)}</ul><Link className="text-link" to={`/evolution?idea=${idea.id}`}>Compare versions<ArrowRight size={14} /></Link></div>)}
      </div>
      {versionDialog && <Modal title="Create an immutable idea version" onClose={() => setVersionDialog(false)}><form className="modal-form" onSubmit={saveVersion}>{(['title', 'category', 'audience', 'problem', 'solution', 'features', 'constraints'] as const).map((field) => <label key={field}>{field === 'features' ? 'Core features (one per line)' : field[0].toUpperCase() + field.slice(1)}{field === 'problem' || field === 'solution' || field === 'features' || field === 'constraints' ? <textarea required={field !== 'constraints'} rows={field === 'features' ? 4 : 3} value={versionInput[field]} onChange={(event) => setVersionInput((current) => ({ ...current, [field]: event.target.value }))} /> : <input required value={versionInput[field]} onChange={(event) => setVersionInput((current) => ({ ...current, [field]: event.target.value }))} />}</label>)}<label>Change summary<input required value={changeSummary} onChange={(event) => setChangeSummary(event.target.value)} /></label>{versionError && <ErrorBanner message={versionError} />}<button className="button primary" disabled={versionBusy || !changeSummary.trim()}>{versionBusy ? 'Saving...' : 'Save new version'}</button></form></Modal>}
    </>}
    {publishError && <ErrorBanner message={publishError} />}
    {archiveConfirm && <ConfirmModal
      title="Archive this idea?"
      description="Archiving removes this idea from active review workflows while preserving all saved versions and feedback history. You can restore it later."
      confirmLabel="Archive idea"
      danger
      busy={statusBusy}
      onConfirm={() => void changeApiStatus('Archived')}
      onClose={() => setArchiveConfirm(false)}
    />}
  </>
}

function RequirementAnalysisPanel({
  ideaId,
  version,
  onAnalysisUpdate,
  onPrototypeUpdate,
}: {
  ideaId: string
  version: number
  onAnalysisUpdate?: (analysis: RequirementAnalysis | null) => void
  onPrototypeUpdate?: (prototype: PrototypeBuild | null) => void
}) {
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
        onAnalysisUpdate?.(result)
        setError('')
        if (result && (result.status === 'queued' || result.status === 'running')) {
          timer = window.setTimeout(() => void refresh(), 1800)
        }
      } catch (reason) {
        if (active) setError(sanitizeUserMessage(reason, 'We could not load the requirement status right now.'))
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
      onAnalysisUpdate?.(run)
      setRefreshKey((current) => current + 1)
    } catch (reason) {
      setError(sanitizeUserMessage(reason, "We couldn't complete this action. Please try again."))
    } finally {
      setStarting(false)
    }
  }

  function formatSourceField(field: string): string {
    const labels: Record<string, string> = {
      title: 'Title',
      category: 'Category',
      problem: 'Problem statement',
      solution: 'Proposed solution',
      audience: 'Target users',
      features: 'Core features',
      constraints: 'Constraints',
    }
    return labels[field] ?? field
  }

  function renderFacts(title: string, facts: RequirementFact[]) {
    return <section className="requirement-card" key={title}>
      <h3>{title}</h3>
      {facts.length
        ? <ul className="requirement-fact-list">{facts.map((fact, index) => <li key={`${fact.text}-${index}`}>
          <div className="requirement-fact-header">
            <span>{fact.text}</span>
            <Badge tone={fact.basis === 'assumption' ? 'blue' : 'green'}>
              {fact.basis === 'assumption' ? 'AI assumption' : 'Confirmed'}
            </Badge>
          </div>
          <small>Source: {fact.source_fields.map(formatSourceField).join(', ')}</small>
        </li>)}</ul>
        : <p className="muted">No items identified from this version.</p>}
    </section>
  }

  const isRunning = analysis?.status === 'queued' || analysis?.status === 'running'
  const isReady = analysis?.status === 'completed' && analysis.validation_status === 'valid'
  const statusLabel = isReady
    ? 'Requirements ready'
    : isRunning
      ? 'Generating requirements'
      : 'Action required'
  const result = analysis?.result

  return <section className="requirements">
    <div className="notice">
      <FileText size={19} />
      <div>
        <strong>Structured requirements · Version {version}</strong>
        <p>Veridica analyzes your immutable version brief in the background. Confirmed details are linked to your inputs, while inferred items are labeled as assumptions.</p>
      </div>
    </div>

    <div className="requirements-toolbar">
      <div className="requirements-status-group">
        <Status value={statusLabel} />
        {isReady && <span className="muted">Requirements generated · Version {analysis.source_version}{analysis.completed_at ? ` · ${dateLabel(analysis.completed_at)}` : ''}</span>}
      </div>
      <button
        className="button primary"
        onClick={() => void start()}
        disabled={starting || loading || isRunning}
      >
        {starting || isRunning
          ? 'Generating requirements...'
          : analysis
            ? 'Regenerate requirements'
            : 'Analyze requirements'}
      </button>
    </div>

    {loading && <LoadingState title="Loading requirements..." description="Checking the latest structured requirements for this version." />}
    {error && <ErrorBanner message={error} onRetry={() => setRefreshKey((current) => current + 1)} />}

    {analysis && <div aria-live="polite">
      {isRunning && <div className="notice"><Sparkles size={18} /><div><strong>Generating requirements</strong><p role="status">Veridica is analyzing your idea in the background.</p></div></div>}
      {analysis.error_message && <ErrorBanner message={analysis.error_message} onRetry={() => void start()} retryLabel="Regenerate requirements" />}
      {result && <>
        <div className="requirements-grid">
          {renderFacts('Problem understanding', result.problem)}
          {renderFacts('Target users', result.target_users)}
          {renderFacts('Functional requirements', result.core_features)}
          {renderFacts('Constraints', result.constraints)}
          {renderFacts('Acceptance criteria', result.acceptance_criteria)}
        </div>

        <section className="requirement-card">
          <h3>User journeys</h3>
          {result.user_journeys.length
            ? <div className="journey-cards">{result.user_journeys.map((journey, index) => <article className="journey-card" key={`${journey.actor.text}-${index}`}>
              <div className="requirement-fact-header">
                <h4>{journey.actor.text}</h4>
                <Badge tone={journey.actor.basis === 'assumption' ? 'blue' : 'green'}>
                  {journey.actor.basis === 'assumption' ? 'AI assumption' : 'Confirmed'}
                </Badge>
              </div>
              <p><strong>Need:</strong> {journey.need.text}</p>
              <ol>{journey.steps.map((step, stepIndex) => <li key={`${step}-${stepIndex}`}>{step}</li>)}</ol>
              <p><strong>Expected outcome:</strong> {journey.outcome.text}</p>
            </article>)}</div>
            : <p className="muted">No user journeys could be grounded from the supplied brief.</p>}
        </section>

        <div className="requirements-grid two-col">
          <section className="requirement-card">
            <h3>Assumptions</h3>
            {result.assumptions.length
              ? <ul>{result.assumptions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
              : <p className="muted">No additional assumptions recorded.</p>}
          </section>
          <section className="requirement-card">
            <h3>Open questions</h3>
            {result.open_questions.length
              ? <ul>{result.open_questions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
              : <p className="muted">No open questions recorded.</p>}
          </section>
        </div>

        {isReady && <PrototypeSourcePanel
          ideaId={ideaId}
          version={version}
          requirementAnalysisId={analysis.id}
          onPrototypeUpdate={onPrototypeUpdate}
        />}
      </>}
    </div>}
  </section>
}

function PrototypeSourcePanel({
  ideaId,
  version,
  requirementAnalysisId,
  onPrototypeUpdate,
}: {
  ideaId: string
  version: number
  requirementAnalysisId: string
  onPrototypeUpdate?: (prototype: PrototypeBuild | null) => void
}) {
  const [build, setBuild] = useState<PrototypeBuild | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getLatestPrototypeSource(ideaId, version)
      .then((result) => {
        if (!active) return
        setBuild(result)
        onPrototypeUpdate?.(result)
      })
      .catch((reason: unknown) => {
        if (active) setError(sanitizeUserMessage(reason, 'Prototype preview status could not be loaded.'))
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [ideaId, version])

  async function generate() {
    setGenerating(true)
    setError('')
    try {
      const created = await generatePrototypeSource(ideaId, version, requirementAnalysisId)
      setBuild(created)
      onPrototypeUpdate?.(created)
    } catch (reason) {
      setError(sanitizeUserMessage(reason, 'We could not generate the prototype preview right now. Please try again.'))
    } finally {
      setGenerating(false)
    }
  }

  return <section className="prototype-source-panel">
    <div className="requirements-toolbar">
      <div>
        <h3>Interactive prototype preview</h3>
        <p className="muted">
          Generated from your validated Version {version} requirements so reviewers can explore screens, features, and user journeys safely in the browser.
        </p>
      </div>
      {!loading && !build && <button
        className="button primary"
        disabled={generating}
        onClick={() => void generate()}
      >{generating ? 'Preparing preview...' : 'Generate prototype preview'}</button>}
      {build && <Status value="Completed" />}
    </div>
    {loading && <LoadingState title="Loading prototype preview..." />}
    {error && <ErrorBanner message={error} onRetry={() => void generate()} />}
    {build && <div aria-live="polite">
      <div className="notice">
        <CheckCircle2 size={18} />
        <div>
          <strong>Interactive preview ready · Version {build.source_version}</strong>
          <p>Reviewers assigned to Version {build.source_version} can interact with this preview directly inside Veridica. Standalone external hosting is disabled for security.</p>
        </div>
      </div>
      {build.error_message && <ErrorBanner message={build.error_message} />}
      {build.plan?.preview_spec && <SchemaPrototypePreview spec={build.plan.preview_spec} />}
    </div>}
  </section>
}

export function ReviewQueue() {
  const { state } = useWorkspace()
  const [apiAssignments, setApiAssignments] = useState<ReviewerAssignment[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  useEffect(() => {
    if (!getAccessToken()) return
    let active = true
    setLoading(true)
    listReviewerAssignments()
      .then((assignments) => { if (active) setApiAssignments(assignments) })
      .catch((reason: unknown) => {
        if (active) setError(sanitizeUserMessage(reason, 'Your review assignments could not be loaded right now.'))
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [reloadKey])
  if (getAccessToken()) {
    if (loading) return <LoadingState title="Loading assigned idea versions..." />
    return <><PageHeading eyebrow="REVIEWER WORKSPACE" title="Your assigned idea versions.">Active review assignments for your account.</PageHeading>
      {error && <ErrorBanner message={error} onRetry={() => setReloadKey((value) => value + 1)} />}
      {apiAssignments.length ? <div className="assignment-list">{apiAssignments.map((assignment) => <article className="assignment" key={assignment.id}><div className="assignment-brief"><Badge>Version {assignment.version}</Badge><h2>{assignment.idea_title}</h2><p>{assignment.solution}</p><small>Assigned {new Date(assignment.assigned_at).toLocaleDateString()}</small></div><Link className="button primary" to={`/reviews/${assignment.id}`}>{assignment.review_submitted ? 'View submitted review' : 'Review assigned version'}<ArrowRight size={16} /></Link><Status value={assignment.review_submitted ? 'Submitted' : 'Pending'} /></article>)}</div> : !error && <Empty title="No active assignments"><p>Version-specific review assignments will appear here when an administrator assigns them to your account.</p></Empty>}
    </>
  }
  const assignments = state.assignments.filter((assignment) => assignment.reviewer === 'Maya Chen')
  return <><PageHeading eyebrow="REVIEWER PORTAL / MAYA CHEN" title="A fresh perspective starts here.">Your assigned prototypes and review sessions.</PageHeading><div className="notice"><Users size={19} /><div><strong>Preview reviewer identity</strong><p>Maya Chen · Assigned projects in browser preview mode</p></div></div><SectionHeading title="Your assignments" />
    {assignments.length ? <div className="assignment-list">{assignments.map((assignment) => {
      const idea = state.ideas.find((candidate) => candidate.id === assignment.ideaId)
      if (!idea) return null
      return <article className="assignment" key={assignment.id}><ProjectVisual idea={idea} /><div><div className="card-meta"><Badge>{idea.category}</Badge><Status value={assignment.status} /></div><h2>{idea.title}</h2><p>{idea.solution}</p><span className="muted">Prototype V{idea.version}</span></div><Link className="button primary" to={`/reviews/${idea.id}`}>{assignment.status === 'Completed' ? 'View review' : 'Start review'}<ArrowRight size={16} /></Link></article>
    })}</div> : <Empty title="No assignments yet"><p>Assigned review cycles will appear here.</p></Empty>}
  </>
}
