import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { Activity, ArrowRight, Check, Download, FileText, LockKeyhole, Plus, RefreshCw, ShieldCheck, Users } from 'lucide-react'
import { downloadFile, reviewers } from '../services/preview'
import type { Role } from '../services/preview'
import { useWorkspace } from '../services/workspace'
import { login, register } from '../services/auth'
import { Badge, dateLabel, Empty, Modal, PageHeading, SectionHeading, Status } from '../components/ui'

export function WorkflowMonitor() {
  const { state } = useWorkspace()
  const [query, setQuery] = useState('')
  const events = state.audit.filter((event) => `${event.action} ${event.entity}`.toLowerCase().includes(query.toLowerCase()))
  return <><PageHeading eyebrow="OPERATIONS" title="A clear view of the work in motion." /><div className="notice"><Activity size={21} /><div><strong>No Python workflow is connected</strong><p>The activity below contains local preview events, not Celery jobs or LangGraph executions.</p></div></div><div className="pipeline-list">{['Requirement analysis', 'Prototype build & validation', 'Feedback quality & trust', 'Consensus & prioritization', 'Evolution & decision report'].map((step, index) => <div key={step}><span>{String(index + 1).padStart(2, '0')}</span><div><h3>{step}</h3><small>Python / LangGraph</small></div><Badge>Not started</Badge></div>)}</div><div className="section-space"><SectionHeading title="Local activity log" /><div className="filter-bar"><input aria-label="Search activity" placeholder="Filter activity..." value={query} onChange={(event) => setQuery(event.target.value)} /></div>{events.length ? <div className="table-scroll"><table><thead><tr><th>Event</th><th>Entity</th><th>Date</th><th>Source</th></tr></thead><tbody>{events.map((entry) => <tr key={entry.id}><td>{entry.action}</td><td>{entry.entity}</td><td>{dateLabel(entry.created)}</td><td><Badge>Preview event</Badge></td></tr>)}</tbody></table></div> : <Empty title="No matching events" />}</div></>
}

export function AdminPanel() {
  const { state, role, update, notify } = useWorkspace()
  const [tab, setTab] = useState('Assignments')
  const [modal, setModal] = useState(false)
  const [ideaId, setIdeaId] = useState('placement')
  const [reviewer, setReviewer] = useState(reviewers[0])
  if (role !== 'admin') return <Empty title="Admin preview portal required"><p>Choose Admin portal in the workspace header to inspect this view. This is not an authentication boundary.</p></Empty>
  function assign() {
    const idea = state.ideas.find((entry) => entry.id === ideaId && entry.status === 'Review open')
    if (!idea) { notify('Select an idea with an open review cycle.'); return }
    if (state.assignments.some((entry) => entry.ideaId === ideaId && entry.reviewer === reviewer)) { notify('That reviewer is already assigned to this idea.'); return }
    update((current) => ({ ...current, assignments: [...current.assignments, { id: crypto.randomUUID(), ideaId, reviewer, status: 'Assigned' }], audit: [{ id: crypto.randomUUID(), action: 'Preview reviewer assigned', entity: `${idea.title} / ${reviewer}`, created: new Date().toISOString() }, ...current.audit] }), 'Reviewer assigned in the local preview.')
    setModal(false)
  }
  return <><PageHeading eyebrow="ADMIN PORTAL" title="Keep the review process accountable." actions={<button className="button primary" onClick={() => setModal(true)}><Plus size={16} />Assign reviewer</button>}>Assignments, reviewer records, and local audit history.</PageHeading><div className="tabs" role="tablist">{['Assignments', 'Reviewers', 'Audit log'].map((value) => <button role="tab" aria-selected={tab === value} onClick={() => setTab(value)} key={value}>{value}</button>)}</div>
    {tab === 'Assignments' && <div className="table-scroll"><table><thead><tr><th>Project</th><th>Reviewer</th><th>Version</th><th>Status</th></tr></thead><tbody>{state.assignments.map((assignment) => <tr key={assignment.id}><td><Link className="text-link" to={`/ideas/${assignment.ideaId}`}>{state.ideas.find((idea) => idea.id === assignment.ideaId)?.title}</Link></td><td>{assignment.reviewer}</td><td>V{state.ideas.find((idea) => idea.id === assignment.ideaId)?.version}</td><td><Status value={assignment.status} /></td></tr>)}</tbody></table></div>}
    {tab === 'Reviewers' && <><div className="notice"><Users size={20} /><div><strong>Sample reviewer directory</strong><p>Account management, verified expertise and role authorization will come from the Python backend.</p></div></div><div className="table-scroll"><table><thead><tr><th>Reviewer</th><th>Assignments</th><th>Trust score</th><th>Identity status</th></tr></thead><tbody>{reviewers.map((name) => <tr key={name}><td><span className="person-cell"><span className="avatar">{name.split(' ').map((part) => part[0]).join('')}</span>{name}</span></td><td>{state.assignments.filter((assignment) => assignment.reviewer === name).length}</td><td>Not calculated</td><td><Badge>Preview identity</Badge></td></tr>)}</tbody></table></div></>}
    {tab === 'Audit log' && <div className="table-scroll"><table><thead><tr><th>Action</th><th>Entity</th><th>Timestamp</th></tr></thead><tbody>{state.audit.map((entry) => <tr key={entry.id}><td>{entry.action}</td><td>{entry.entity}</td><td>{new Date(entry.created).toLocaleString()}</td></tr>)}</tbody></table></div>}
    {modal && <Modal title="Assign a reviewer" onClose={() => setModal(false)}><form className="modal-form" onSubmit={(event) => { event.preventDefault(); assign() }}><label>Open review cycle<select aria-label="Open review cycle" value={ideaId} onChange={(event) => setIdeaId(event.target.value)}>{state.ideas.filter((idea) => idea.status === 'Review open').map((idea) => <option key={idea.id} value={idea.id}>{idea.title}</option>)}</select></label><label>Reviewer<select aria-label="Reviewer" value={reviewer} onChange={(event) => setReviewer(event.target.value)}>{reviewers.map((name) => <option key={name}>{name}</option>)}</select></label><p>Assignments are local preview records. No email invitation is sent.</p><button className="button primary" type="submit">Assign reviewer<ArrowRight size={15} /></button></form></Modal>}
  </>
}

export function SettingsPage() {
  const { state, reset, role } = useWorkspace()
  const [confirm, setConfirm] = useState(false)
  return <><PageHeading eyebrow="WORKSPACE SETTINGS" title="Your workspace, clearly defined." /><div className="settings-sections"><section><div><ShieldCheck size={22} /><h2>Preview environment</h2><p>Browser-local storage. No data is sent to Python or AWS.</p></div><Badge tone="green">Frontend preview</Badge></section><section><div><LockKeyhole size={22} /><h2>Identity & access</h2><p>Current portal: {role}. Real authentication and authorization are not connected.</p></div><Link className="button" to="/auth">View sign-in screen<ArrowRight size={15} /></Link></section><section><div><FileText size={22} /><h2>Export preview records</h2><p>Ideas, reviews, version proposals, assignments, and activity.</p></div><button className="button" onClick={() => downloadFile('veridica-preview.json', JSON.stringify({ source: 'frontend-preview', exportedAt: new Date().toISOString(), ...state }, null, 2), 'application/json')}><Download size={15} />Export data</button></section><section><div><RefreshCw size={22} /><h2>Reset local workspace</h2><p>Remove browser-local changes and restore the original sample records.</p></div><button className="button danger" onClick={() => setConfirm(true)}>Reset preview</button></section></div>{confirm && <Modal title="Reset this preview workspace?" onClose={() => setConfirm(false)}><p>Your local ideas, reviews, assignments, and version proposals will be replaced with the sample workspace. Export anything you need before continuing.</p><div className="form-actions"><button className="button" onClick={() => setConfirm(false)}>Cancel</button><button className="button danger" onClick={() => { reset(); setConfirm(false) }}>Reset local data</button></div></Modal>}</>
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
  return <div className="auth-page"><div className="auth-brand"><ShieldCheck size={31} />veridica.</div><div className="auth-layout"><section className="auth-intro"><span className="eyebrow">IDEAS DESERVE MORE THAN A GUESS.</span><h1>Build something.<br />Learn something.<br />Make it better.</h1><div className="auth-steps">{['A visual prototype to explore', 'Feedback with evidence behind it', 'A clearer path to the next version'].map((text) => <p key={text}><Check size={16} />{text}</p>)}</div><Badge>Local API authentication</Badge></section><section className="auth-form-section"><div className="tabs" role="tablist">{['Sign in', 'Create account'].map((value) => <button role="tab" aria-selected={mode === value} key={value} onClick={() => { setMode(value); setError('') }}>{value}</button>)}</div><h2>{mode === 'Sign in' ? 'Welcome back.' : 'A place for your next idea.'}</h2><form className="modal-form" onSubmit={submit}><label>Email address<input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label><label>Password<input required minLength={12} type="password" autoComplete={mode === 'Sign in' ? 'current-password' : 'new-password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 12 characters" /></label>{error && <p role="alert" className="error">{error}</p>}<button className="button primary" type="submit" disabled={busy}>{busy ? 'Connecting...' : mode}<ArrowRight size={15} /></button></form><div className="auth-preview"><p>Offline mode does not send or save credentials.</p><select aria-label="Preview role" value={role} onChange={(event) => chooseRole(event.target.value as Role)}><option value="owner">Idea owner</option><option value="reviewer">Reviewer</option><option value="admin">Admin</option></select><button className="button" onClick={() => { setRole(role); navigate(role === 'reviewer' ? '/reviews' : role === 'admin' ? '/admin' : '/') }}>Continue to preview<ArrowRight size={15} /></button></div></section></div><footer>Local authentication uses the Python API · Preview mode remains browser-local</footer></div>
}