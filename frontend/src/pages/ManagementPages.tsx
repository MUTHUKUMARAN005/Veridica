import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { Activity, ArrowRight, Check, Download, FileText, LockKeyhole, Plus, RefreshCw, ShieldCheck, Users } from 'lucide-react'
import { downloadFile, reviewers } from '../services/preview'
import type { Role } from '../services/preview'
import { useWorkspace } from '../services/workspace'
import { getAccessToken, getCurrentUser, login, register } from '../services/auth'
import type { AuthUser } from '../services/auth'
import { createAdminAssignment, listAdminAssignments, revokeAdminAssignment } from '../services/authorization'
import type { AdminAssignment } from '../services/authorization'
import {
  getEvolutionProposal,
  getIdea,
  getLatestDecisionReport,
  getLatestFeedbackAnalysis,
  getLatestPrototypeSource,
  getLatestRequirementAnalysis,
  listIdeas,
  listPersistedFeedback,
} from '../services/ideas'
import { Badge, ConfirmModal, dateLabel, Empty, ErrorBanner, LoadingState, Modal, PageHeading, SectionHeading, Status } from '../components/ui'

export function WorkflowMonitor() {
  const { state } = useWorkspace()
  const [query, setQuery] = useState('')
  const [liveStatus, setLiveStatus] = useState<Record<string, boolean>>({})
  const [activeIdea, setActiveIdea] = useState<{ id: string; title: string; version: number } | null>(null)
  const isAuthenticated = Boolean(getAccessToken())

  useEffect(() => {
    if (!isAuthenticated) return
    let active = true
    listIdeas({ limit: 5, offset: 0 })
      .then(async (page) => {
        if (!active || !page.items.length) return
        const first = page.items[0]
        const detail = await getIdea(first.id)
        if (!active) return
        setActiveIdea({ id: detail.id, title: detail.title, version: detail.version })
        const [req, proto, revs, fa, evo, rep] = await Promise.all([
          getLatestRequirementAnalysis(detail.id, 1).catch(() => null),
          getLatestPrototypeSource(detail.id, 1).catch(() => null),
          listPersistedFeedback(detail.id, 1).catch(() => []),
          getLatestFeedbackAnalysis(detail.id, 1).catch(() => null),
          getEvolutionProposal(detail.id, 1).catch(() => null),
          getLatestDecisionReport(detail.id, 1).catch(() => null),
        ])
        if (!active) return
        const faDone = Boolean(fa && fa.status === 'completed' && fa.result)
        const evoApproved = Boolean(evo && evo.status === 'approved')
        setLiveStatus({
          submission: true,
          requirements: Boolean(req && req.status === 'completed' && req.validation_status === 'valid'),
          builder: Boolean(proto && proto.validation_status === 'passed'),
          reviewer: revs.length > 0,
          quality: faDone,
          nlp: faDone,
          trustConsensus: faDone,
          evolution: Boolean(evo),
          approval: evoApproved,
          immutableVersion: detail.versions.length > 1 || evoApproved,
          decisionReport: Boolean(rep),
        })
      })
      .catch(() => {})
    return () => { active = false }
  }, [isAuthenticated])

  const events = state.audit.filter((event) => `${event.action} ${event.entity}`.toLowerCase().includes(query.toLowerCase()))
  const ideaPath = activeIdea ? `/ideas/${activeIdea.id}` : '/ideas'
  const stages: { key: string; step: string; detail: string; to: string }[] = [
    { key: 'submission', step: 'Idea Submission', detail: 'Owner submits idea brief, problem statement, target audience, core features, constraints, and reference files.', to: ideaPath },
    { key: 'requirements', step: '1. Requirement Analysis', detail: 'Generates structured problem understanding, user journeys, functional criteria, assumptions, and open questions.', to: ideaPath },
    { key: 'builder', step: '2. AI Builder', detail: 'Produces validated prototype source and interactive schema-driven browser preview for the exact version.', to: activeIdea ? `/ideas/${activeIdea.id}/prototype` : '/prototypes' },
    { key: 'reviewer', step: 'Reviewer Portal', detail: 'Version is published, reviewers are assigned, and verified version-locked feedback is persisted.', to: '/feedback' },
    { key: 'quality', step: '3. Feedback Quality', detail: 'Evaluates relevance, constructiveness, originality, internal consistency, and spam risk indicators.', to: '/trust' },
    { key: 'nlp', step: '4. NLP and Semantic Analysis', detail: 'Extracts evidence-linked themes, contradictions, and semantic similarity across submitted reviews.', to: '/analytics' },
    { key: 'trustConsensus', step: '5. Trust, Consensus and Prioritization', detail: 'Computes deterministic partial trust weights, raw vs. weighted consensus, and P1–P3 ranked improvements (branches to Idea Evolution or directly to Decision Intelligence).', to: '/consensus' },
    { key: 'evolution', step: '6. Idea Evolution', detail: 'Synthesizes an evidence-backed V2 change proposal linked to verified reviewer citations.', to: activeIdea ? `/evolution?idea=${activeIdea.id}` : '/evolution' },
    { key: 'approval', step: 'Owner Approval', detail: 'Idea owner selects and approves supported improvement ranks before any new version is created.', to: activeIdea ? `/evolution?idea=${activeIdea.id}` : '/evolution' },
    { key: 'immutableVersion', step: 'New Immutable Version', detail: 'Creates immutable candidate V2 (preserving V1) and generates its updated prototype specification.', to: ideaPath },
    { key: 'decisionReport', step: '7. Decision Intelligence → Decision Report', detail: 'Generates a traceable Decision Report snapshot from Step 5 (Consensus & Priorities) and/or Step 6 (New Immutable Version).', to: activeIdea ? `/reports?idea=${activeIdea.id}` : '/reports' },
  ]
  return <>
    <PageHeading eyebrow="OPERATIONS" title="A clear view of the validation pipeline." />
    <div className="notice"><Activity size={21} /><div><strong>Validation workflow stages{activeIdea ? ` · ${activeIdea.title}` : ''}</strong><p>Each stage processes version-specific evidence so your original idea and reviewer records stay auditable. Step 5 (Trust, Consensus and Prioritization) feeds both Step 6 (Idea Evolution → Owner Approval → New Immutable Version) and Step 7 (Decision Intelligence → Decision Report).</p></div></div>
    <div className="pipeline-list">
      {stages.map(({ key, step, detail, to }, index) => {
        const completed = isAuthenticated ? Boolean(liveStatus[key]) : true
        return <div key={step}>
          <span>{String(index + 1).padStart(2, '0')}</span>
          <div>
            <h3>{step}</h3>
            <small>{detail}</small>
          </div>
          <div className="requirement-status-group">
            <Status value={isAuthenticated ? (completed ? 'Completed' : 'Pending') : 'Available'} />
            <Link className="button" to={to}>Open<ArrowRight size={14} /></Link>
          </div>
        </div>
      })}
    </div>
    {!isAuthenticated && <div className="section-space">
      <SectionHeading title="Workspace activity log" />
      <div className="filter-bar"><input aria-label="Search activity" placeholder="Filter activity..." value={query} onChange={(event) => setQuery(event.target.value)} /></div>
      {events.length ? <div className="table-scroll"><table><thead><tr><th>Event</th><th>Project</th><th>Date</th><th>Status</th></tr></thead><tbody>{events.map((entry) => <tr key={entry.id}><td>{entry.action}</td><td>{entry.entity}</td><td>{dateLabel(entry.created)}</td><td><Badge>Recorded</Badge></td></tr>)}</tbody></table></div> : <Empty title="No matching events" />}
    </div>}
  </>
}

export function AdminPanel() {
  return getAccessToken() ? <ApiAdminPanel /> : <PreviewAdminPanel />
}

function ApiAdminPanel() {
  const [assignments, setAssignments] = useState<AdminAssignment[]>([])
  const [ideaId, setIdeaId] = useState('')
  const [version, setVersion] = useState('1')
  const [reviewerEmail, setReviewerEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [refresh, setRefresh] = useState(0)
  const [revokeTarget, setRevokeTarget] = useState<AdminAssignment | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    listAdminAssignments()
      .then((records) => { if (active) setAssignments(records) })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Assignments could not be loaded.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [refresh])

  async function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await createAdminAssignment(ideaId.trim(), Number(version), reviewerEmail.trim())
      setIdeaId('')
      setReviewerEmail('')
      setRefresh((value) => value + 1)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The reviewer could not be assigned.')
    } finally {
      setBusy(false)
    }
  }

  async function revoke(assignmentId: string) {
    setBusy(true)
    setError('')
    try {
      await revokeAdminAssignment(assignmentId)
      setRevokeTarget(null)
      setRefresh((value) => value + 1)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The assignment could not be revoked.')
    } finally {
      setBusy(false)
    }
  }

  return <>
    <PageHeading eyebrow="AUTHORIZED ADMINISTRATION" title="Manage version-specific reviewer access.">Administrators can assign or revoke a reviewer for an exact idea version.</PageHeading>
    <form className="review-form" onSubmit={assign}>
      <h2>Assign a reviewer</h2>
      <label>Project reference ID<input required minLength={36} maxLength={36} value={ideaId} onChange={(event) => setIdeaId(event.target.value)} placeholder="Project reference ID shared by the owner" /></label>
      <div className="form-two">
        <label>Version<input required type="number" min={1} value={version} onChange={(event) => setVersion(event.target.value)} /></label>
        <label>Reviewer account email<input required type="email" value={reviewerEmail} onChange={(event) => setReviewerEmail(event.target.value)} placeholder="reviewer@example.com" /></label>
      </div>
      {error && <ErrorBanner message={error} />}
      <button className="button primary" disabled={busy}>{busy ? 'Assigning…' : 'Assign reviewer'}<ArrowRight size={15} /></button>
    </form>
    <div className="section-space">
      <SectionHeading title="Reviewer assignments" />
      {loading ? <LoadingState title="Loading assignments…" /> : assignments.length ? <div className="table-scroll"><table><thead><tr><th>Idea</th><th>Version</th><th>Reviewer</th><th>Status</th><th>Review</th><th>Action</th></tr></thead><tbody>{assignments.map((assignment) => <tr key={assignment.id}><td><strong>{assignment.idea_title}</strong></td><td>V{assignment.version}</td><td>{assignment.reviewer_email}</td><td><Status value={assignment.active ? 'Active' : 'Revoked'} /></td><td><Status value={assignment.review_submitted ? 'Submitted' : 'Assigned'} /></td><td>{assignment.active && <button className="button danger compact" disabled={busy} onClick={() => setRevokeTarget(assignment)}>Revoke</button>}</td></tr>)}</tbody></table></div> : <Empty title="No reviewer assignments yet" />}
    </div>
    {revokeTarget && <ConfirmModal
      title="Revoke reviewer access?"
      description={`Remove ${revokeTarget.reviewer_email}'s access to ${revokeTarget.idea_title} (V${revokeTarget.version})?`}
      confirmLabel="Revoke access"
      busy={busy}
      onCancel={() => setRevokeTarget(null)}
      onConfirm={() => void revoke(revokeTarget.id)}
    />}
  </>
}

function PreviewAdminPanel() {
  const { state, role, update, notify } = useWorkspace()
  const [tab, setTab] = useState('Assignments')
  const [modal, setModal] = useState(false)
  const [ideaId, setIdeaId] = useState('placement')
  const [reviewer, setReviewer] = useState(reviewers[0])
  if (role !== 'admin') return <Empty title="Admin preview portal required"><p>Choose Admin portal in the workspace header to inspect this view.</p></Empty>
  function assign() {
    const idea = state.ideas.find((entry) => entry.id === ideaId && entry.status === 'Review open')
    if (!idea) { notify('Select an idea with an open review cycle.'); return }
    if (state.assignments.some((entry) => entry.ideaId === ideaId && entry.reviewer === reviewer)) { notify('That reviewer is already assigned to this idea.'); return }
    update((current) => ({ ...current, assignments: [...current.assignments, { id: crypto.randomUUID(), ideaId, reviewer, status: 'Assigned' }], audit: [{ id: crypto.randomUUID(), action: 'Preview reviewer assigned', entity: `${idea.title} / ${reviewer}`, created: new Date().toISOString() }, ...current.audit] }), 'Reviewer assigned in the local preview.')
    setModal(false)
  }
  return <><PageHeading eyebrow="ADMIN PORTAL" title="Keep the review process accountable." actions={<button className="button primary" onClick={() => setModal(true)}><Plus size={16} />Assign reviewer</button>}>Assignments, reviewer records, and audit history.</PageHeading><div className="tabs" role="tablist">{['Assignments', 'Reviewers', 'Audit log'].map((value) => <button role="tab" aria-selected={tab === value} onClick={() => setTab(value)} key={value}>{value}</button>)}</div>
    {tab === 'Assignments' && <div className="table-scroll"><table><thead><tr><th>Project</th><th>Reviewer</th><th>Version</th><th>Status</th></tr></thead><tbody>{state.assignments.map((assignment) => <tr key={assignment.id}><td><Link className="text-link" to={`/ideas/${assignment.ideaId}`}>{state.ideas.find((idea) => idea.id === assignment.ideaId)?.title}</Link></td><td>{assignment.reviewer}</td><td>V{state.ideas.find((idea) => idea.id === assignment.ideaId)?.version}</td><td><Status value={assignment.status} /></td></tr>)}</tbody></table></div>}
    {tab === 'Reviewers' && <><div className="notice"><Users size={20} /><div><strong>Reviewer directory</strong><p>Assign verified reviewers to specific idea versions to gather independent product feedback.</p></div></div><div className="table-scroll"><table><thead><tr><th>Reviewer</th><th>Assignments</th><th>Trust score</th><th>Identity status</th></tr></thead><tbody>{reviewers.map((name) => <tr key={name}><td><span className="person-cell"><span className="avatar">{name.split(' ').map((part) => part[0]).join('')}</span>{name}</span></td><td>{state.assignments.filter((assignment) => assignment.reviewer === name).length}</td><td>Not calculated</td><td><Badge>Verified reviewer</Badge></td></tr>)}</tbody></table></div></>}
    {tab === 'Audit log' && <div className="table-scroll"><table><thead><tr><th>Action</th><th>Entity</th><th>Timestamp</th></tr></thead><tbody>{state.audit.map((entry) => <tr key={entry.id}><td>{entry.action}</td><td>{entry.entity}</td><td>{new Date(entry.created).toLocaleString()}</td></tr>)}</tbody></table></div>}
    {modal && <Modal title="Assign a reviewer" onClose={() => setModal(false)}><form className="modal-form" onSubmit={(event) => { event.preventDefault(); assign() }}><label>Open review cycle<select aria-label="Open review cycle" value={ideaId} onChange={(event) => setIdeaId(event.target.value)}>{state.ideas.filter((idea) => idea.status === 'Review open').map((idea) => <option key={idea.id} value={idea.id}>{idea.title}</option>)}</select></label><label>Reviewer<select aria-label="Reviewer" value={reviewer} onChange={(event) => setReviewer(event.target.value)}>{reviewers.map((name) => <option key={name}>{name}</option>)}</select></label><p>Assign this reviewer to test the current prototype version.</p><button className="button primary" type="submit">Assign reviewer<ArrowRight size={15} /></button></form></Modal>}
  </>
}

export function SettingsPage() {
  const { state, reset, role } = useWorkspace()
  const [confirm, setConfirm] = useState(false)
  const [sessionUser, setSessionUser] = useState<AuthUser | null>(null)

  useEffect(() => {
    setSessionUser(getCurrentUser())
  }, [])

  return <>
    <PageHeading eyebrow="WORKSPACE SETTINGS" title="Your workspace, clearly defined." />
    <div className="settings-sections">
      <section>
        <div>
          <ShieldCheck size={22} />
          <h2>Workspace environment</h2>
          <p>{sessionUser ? 'Your ideas, prototypes, and reviews are saved to your account.' : 'You are exploring the interactive preview workspace in your browser.'}</p>
        </div>
        <Badge tone="green">{sessionUser ? 'Connected' : 'Preview mode'}</Badge>
      </section>
      <section>
        <div>
          <LockKeyhole size={22} />
          <h2>Identity & access</h2>
          <p>{sessionUser ? `Signed in as ${sessionUser.email} (${sessionUser.role}).` : `Current portal view: ${role}. Sign in to access your saved account records.`}</p>
        </div>
        <Link className="button" to="/auth">{sessionUser ? 'Switch account' : 'Sign in'}<ArrowRight size={15} /></Link>
      </section>
      <section>
        <div>
          <FileText size={22} />
          <h2>Export workspace records</h2>
          <p>Download a copy of your workspace ideas, reviews, version proposals, and activity.</p>
        </div>
        <button className="button" onClick={() => downloadFile('veridica-workspace.json', JSON.stringify({ exportedAt: new Date().toISOString(), ...state }, null, 2), 'application/json')}><Download size={15} />Export data</button>
      </section>
      <section>
        <div>
          <RefreshCw size={22} />
          <h2>Reset sample records</h2>
          <p>Remove browser-local sample changes and restore the default demonstration projects.</p>
        </div>
        <button className="button danger" onClick={() => setConfirm(true)}>Reset sample data</button>
      </section>
    </div>
    {confirm && <ConfirmModal
      title="Reset sample workspace?"
      description="Your browser-local sample ideas, reviews, assignments, and proposals will be restored to their defaults."
      confirmLabel="Reset sample data"
      onCancel={() => setConfirm(false)}
      onConfirm={() => { reset(); setConfirm(false) }}
    />}
  </>
}

export function AuthPage() {
  const { setRole } = useWorkspace()
  const navigate = useNavigate()
  const [mode, setMode] = useState('Sign in')
  const [role, chooseRole] = useState<Role>('owner')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = mode === 'Sign in' ? await login(email, password) : await register(email, password)
      setRole(result.user.role)
      navigate('/')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Authentication failed.')
    } finally {
      setBusy(false)
    }
  }
  return <div className="auth-page"><div className="auth-brand"><ShieldCheck size={31} />veridica.</div><div className="auth-layout"><section className="auth-intro"><span className="eyebrow">IDEAS DESERVE MORE THAN A GUESS.</span><h1>Build something.<br />Learn something.<br />Make it better.</h1><div className="auth-steps">{['A visual prototype to explore', 'Feedback with evidence behind it', 'A clearer path to the next version'].map((text) => <p key={text}><Check size={16} />{text}</p>)}</div><Badge tone="green">Trust-based product validation</Badge></section><section className="auth-form-section"><div className="tabs" role="tablist">{['Sign in', 'Create account'].map((value) => <button role="tab" aria-selected={mode === value} key={value} onClick={() => { setMode(value); setError('') }}>{value}</button>)}</div><h2>{mode === 'Sign in' ? 'Welcome back.' : 'A place for your next idea.'}</h2><form className="modal-form" onSubmit={submit}><label>Email address<input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label><label>Password<input required minLength={12} type="password" autoComplete={mode === 'Sign in' ? 'current-password' : 'new-password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 12 characters" /></label>{error && <ErrorBanner message={error} />}<button className="button primary" type="submit" disabled={busy}>{busy ? 'Signing in…' : mode}<ArrowRight size={15} /></button></form><div className="auth-preview"><p>Or explore the interactive sample workspace without signing in.</p><select aria-label="Preview role" value={role} onChange={(event) => chooseRole(event.target.value as Role)}><option value="owner">Idea owner</option><option value="reviewer">Reviewer</option><option value="admin">Admin</option></select><button className="button" onClick={() => { setRole(role); navigate(role === 'reviewer' ? '/reviews' : role === 'admin' ? '/admin' : '/') }}>Explore sample workspace<ArrowRight size={15} /></button></div></section></div><footer>Veridica · Trust-based crowd product validation & idea evolution</footer></div>
}
