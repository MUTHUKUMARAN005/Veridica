import { lazy, Suspense, useEffect, useState } from 'react'
import { HashRouter, Link, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router'
import { Activity, ArrowUpRight, Bell, ChartNoAxesCombined, ChevronDown, CircleHelp, Compass, FileText, FlaskConical, GitBranch, Home, Lightbulb, Menu, MessageSquare, Monitor, Search, Settings, ShieldCheck, SquarePlus, Users, X } from 'lucide-react'
import { WorkspaceProvider, useWorkspace } from './services/workspace'
import type { Role } from './services/preview'
import { Dashboard, IdeaDetails, Ideas, IdeaSubmission, ReviewQueue } from './pages/WorkspacePages'
import { PrototypeWorkspace, ReviewWorkspace } from './pages/PrototypePages'
import { AdminPanel, AuthPage, SettingsPage, WorkflowMonitor } from './pages/ManagementPages'
import { Empty, Modal } from './components/ui'
import { getCurrentUser, logout } from './services/auth'

const Feedback = lazy(() => import('./pages/IntelligencePages').then((module) => ({ default: module.Feedback })))
const Analytics = lazy(() => import('./pages/IntelligencePages').then((module) => ({ default: module.Analytics })))
const Trust = lazy(() => import('./pages/IntelligencePages').then((module) => ({ default: module.Trust })))
const Consensus = lazy(() => import('./pages/IntelligencePages').then((module) => ({ default: module.Consensus })))
const Evolution = lazy(() => import('./pages/IntelligencePages').then((module) => ({ default: module.Evolution })))
const Reports = lazy(() => import('./pages/IntelligencePages').then((module) => ({ default: module.Reports })))

const ownerLinks = [
  { to: '/', label: 'Home', icon: Home }, { to: '/ideas', label: 'My ideas', icon: Compass },
  { to: '/prototypes', label: 'Prototypes', icon: Monitor }, { to: '/feedback', label: 'Feedback', icon: MessageSquare },
]
const intelligenceLinks = [
  { to: '/analytics', label: 'Analytics', icon: ChartNoAxesCombined }, { to: '/trust', label: 'Trust & quality', icon: ShieldCheck },
  { to: '/consensus', label: 'Consensus', icon: Users }, { to: '/evolution', label: 'Idea evolution', icon: GitBranch }, { to: '/reports', label: 'Decision reports', icon: FileText },
]

function Shell() {
  const { state, role: previewRole, setRole, toast } = useWorkspace()
  const [mobile, setMobile] = useState(false)
  const [query, setQuery] = useState('')
  const [notifications, setNotifications] = useState(false)
  const [help, setHelp] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const apiUser = getCurrentUser()
  const role = apiUser?.role ?? previewRole
  useEffect(() => { setMobile(false); setQuery(''); setNotifications(false); window.scrollTo(0, 0) }, [location.pathname])
  const allowedIdeas = apiUser
    ? []
    : role === 'reviewer'
      ? state.ideas.filter((idea) => state.assignments.some((assignment) => assignment.ideaId === idea.id && assignment.reviewer === 'Maya Chen'))
      : state.ideas
  const matches = query.trim() ? allowedIdeas.filter((idea) => idea.title.toLowerCase().includes(query.toLowerCase())) : []
  const navigation = (links: typeof ownerLinks) => links.map(({ to, label, icon: Icon }) => <NavLink end={to === '/'} to={to} key={to}><Icon size={22} strokeWidth={1.7} /><span>{label}</span>{label === 'Feedback' && <small>{state.reviews.length}</small>}</NavLink>)
  if (location.pathname === '/auth') return <AuthPage />
  const authenticatedPathAllowed = apiUser
    ? (apiUser.role === 'reviewer'
      ? location.pathname.startsWith('/reviews') || location.pathname === '/settings'
      : apiUser.role === 'admin'
        ? location.pathname === '/admin' || location.pathname === '/settings'
        : location.pathname === '/'
          || location.pathname === '/ideas'
          || location.pathname === '/ideas/new'
          || /^\/ideas\/[^/]+$/.test(location.pathname)
          || location.pathname === '/prototypes'
          || [
            '/feedback',
            '/analytics',
            '/trust',
            '/consensus',
            '/evolution',
            '/reports',
          ].includes(location.pathname)
          || location.pathname === '/settings')
    : role !== 'reviewer' || location.pathname.startsWith('/reviews') || location.pathname === '/settings'
  return <div className="app-layout">
    {mobile && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMobile(false)} />}
    <aside className={`sidebar ${mobile ? 'is-open' : ''}`}>
      <Link to="/" className="brand">veridica<span className="brand-period">.</span><span className="brand-spark">✳</span></Link>
      <div className="workspace-picker"><span className="workspace-avatar">V</span><div><strong>Innovation workspace</strong><small>Personal workspace</small></div><ChevronDown size={14} /></div>
      <div className="nav-group"><p>WORKSPACE</p><nav aria-label="Workspace">{role === 'reviewer' ? navigation([{ to: '/reviews', label: 'Review queue', icon: FlaskConical }]) : navigation(ownerLinks)}</nav></div>
      {role !== 'reviewer' && <div className="nav-group"><p>INTELLIGENCE</p><nav aria-label="Intelligence">{navigation(intelligenceLinks)}</nav></div>}
      <div className="nav-group"><p>MANAGE</p><nav aria-label="Management">{role === 'admin' && navigation([{ to: '/admin', label: 'Administration', icon: Users }])}{role !== 'reviewer' && navigation([{ to: '/workflows', label: 'Workflow monitor', icon: Activity }])}{navigation([{ to: '/settings', label: 'Settings', icon: Settings }])}</nav></div>
      <div className="sidebar-bottom"><button className="help-button" onClick={() => setHelp(true)}><CircleHelp size={18} />Help & workspace info<ArrowUpRight size={14} /></button><div className="profile"><span className="avatar">{apiUser ? apiUser.email.slice(0, 2).toUpperCase() : role === 'reviewer' ? 'MC' : role === 'admin' ? 'AD' : 'YO'}</span><div><strong>{apiUser?.email ?? (role === 'reviewer' ? 'Maya Chen' : role === 'admin' ? 'Administrator' : 'Your workspace')}</strong><small>{role === 'owner' ? 'Idea owner' : role === 'reviewer' ? 'Reviewer' : 'Admin'} · {apiUser ? 'API account' : 'Preview'}</small></div></div></div>
    </aside>
    <div className="main-shell"><header className="topbar"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobile(true)}><Menu size={21} /></button><Link className="mobile-brand" to={role === 'reviewer' ? '/reviews' : '/'}>veridica<span>.</span></Link>
      <div className="global-search"><Search size={18} /><input aria-label="Search workspace" placeholder="Search your workspace..." value={query} onChange={(event) => setQuery(event.target.value)} />{query && <button className="icon-button" aria-label="Clear search" onClick={() => setQuery('')}><X size={14} /></button>}{query.trim() && <div className="search-results">{matches.length ? matches.map((idea) => <Link key={idea.id} to={role === 'reviewer' ? `/reviews/${idea.id}` : `/ideas/${idea.id}`}><Lightbulb size={16} /><span>{idea.title}</span><ArrowUpRight size={14} /></Link>) : <p>No matching ideas</p>}</div>}</div>
      <div className="topbar-actions"><span className="preview-label"><span />{apiUser ? `API · ${apiUser.email}` : 'Frontend preview'}</span>{!apiUser && <label className="portal-select"><span className="sr-only">Preview portal</span><select aria-label="Preview portal" value={role} onChange={(event) => { const next = event.target.value as Role; setRole(next); navigate(next === 'reviewer' ? '/reviews' : next === 'admin' ? '/admin' : '/') }}><option value="owner">Owner portal</option><option value="reviewer">Reviewer portal</option><option value="admin">Admin portal</option></select></label>}<div className="notification-wrap"><button className="icon-button notification-button" aria-label="Notifications" title="Notifications" aria-expanded={notifications} onClick={() => setNotifications(!notifications)}><Bell size={19} /><span /></button>{notifications && <div className="notification-panel"><h3>Local preview activity</h3>{state.audit.slice(0, 4).map((entry) => <p key={entry.id}><strong>{entry.action}</strong><small>{entry.entity}</small></p>)}<Link to="/workflows">View preview activity</Link></div>}</div>{apiUser && <button className="button compact" onClick={() => { logout(); setRole('owner'); navigate('/auth') }}>Sign out</button>}<span className="avatar small">{apiUser ? apiUser.email.slice(0, 2).toUpperCase() : role === 'reviewer' ? 'MC' : role === 'admin' ? 'AD' : 'YO'}</span></div>
    </header><div className="preview-strip"><FlaskConical size={13} /><span>{apiUser ? 'API mode · ideas save through the Python service' : 'Sample workspace · Changes stay in this browser · Python services not connected'}</span></div>
    <main id="main-content" className="page-content"><Suspense fallback={<div role="status" className="empty">Loading workspace...</div>}>{authenticatedPathAllowed ? <Routes>
      <Route path="/" element={<Dashboard />} /><Route path="/ideas" element={<Ideas />} /><Route path="/ideas/new" element={<IdeaSubmission />} /><Route path="/ideas/:id" element={<IdeaDetails />} /><Route path="/prototypes" element={<Ideas prototypes />} /><Route path="/reviews" element={<ReviewQueue />} />
      <Route path="/ideas/:id/prototype" element={<PrototypeWorkspace />} /><Route path="/reviews/:id" element={<ReviewWorkspace />} />
      <Route path="/feedback" element={<Feedback />} /><Route path="/analytics" element={<Analytics />} /><Route path="/trust" element={<Trust />} /><Route path="/consensus" element={<Consensus />} /><Route path="/evolution" element={<Evolution />} /><Route path="/reports" element={<Reports />} /><Route path="/workflows" element={<WorkflowMonitor />} /><Route path="/admin" element={<AdminPanel />} /><Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Empty title="Page not found"><Link className="button" to="/">Return to overview</Link></Empty>} />
    </Routes> : <Empty title={!apiUser ? 'This view belongs to the owner portal' : apiUser.role === 'reviewer' ? 'This view is outside your reviewer portal' : 'This view is outside your authorized portal'}><Link className="button" to={role === 'reviewer' ? '/reviews' : role === 'admin' ? '/admin' : '/ideas'}>Return to your portal</Link></Empty>}</Suspense></main></div>
    <nav className="mobile-bottom-nav" aria-label="Quick navigation"><NavLink end to={role === 'reviewer' ? '/reviews' : '/'} aria-label="Home feed" title="Home"><Home size={24} /></NavLink>{role !== 'reviewer' && <><NavLink to="/ideas" end aria-label="Explore ideas" title="Explore"><Compass size={24} /></NavLink><NavLink to="/ideas/new" aria-label="Create idea" title="Create"><SquarePlus size={27} /></NavLink><NavLink to="/feedback" aria-label="Review feedback" title="Feedback"><MessageSquare size={24} /></NavLink></>}<NavLink to="/settings" aria-label="Profile settings" title="Profile"><span className="avatar small">{role === 'reviewer' ? 'MC' : role === 'admin' ? 'AD' : 'YO'}</span></NavLink></nav>
    {toast && <div className="toast" role="status"><ShieldCheck size={18} />{toast}</div>}
    {help && <Modal title="About this workspace" onClose={() => setHelp(false)}><p>Veridica frontend preview. Sample records and local changes are stored only in this browser, not in PostgreSQL.</p><p>Portal switching is a design preview, not authentication. Authenticated requirements and Phase 6 feedback analysis use persisted API records. The Builder currently creates statically checked source for one category; isolated builds and working previews are blocked until a restricted execution boundary is available.</p><p>Trust outputs are evidence-bounded indicators, not proof of reviewer authenticity. Historical accuracy, verified expertise, peer alignment and community validation remain unsupported when records are unavailable. AWS deployment is a separate phase.</p><button className="button primary" onClick={() => setHelp(false)}>Got it</button></Modal>}
  </div>
}

export default function App() { return <HashRouter><WorkspaceProvider><Shell /></WorkspaceProvider></HashRouter> }
