import { useState } from 'react'
import { Link } from 'react-router'
import { ArrowUpRight, Bookmark, Check, ChevronRight, Compass, MessageCircle, MoreHorizontal, Plus, Send, Sparkles } from 'lucide-react'
import type { Idea } from '../services/preview'
import { ideaReviews, interestSummary, previewActor, recordSignal } from '../services/preview'
import { useWorkspace } from '../services/workspace'
import { Badge, Empty, Modal, Status, dateLabel } from './ui'
import { ProjectVisual } from './ProjectVisual'
import { IdeaDiscussion, InterestSignals } from './IdeaDiscussion'

const savedKey = 'veridica.saved-ideas.v1'
const covers: Record<string, string> = {
  placement: '/previews/campus-compass.png',
  circular: '/previews/circular-city.png',
}

function FeedPost({ idea, saved, onSave }: { idea: Idea; saved: boolean; onSave: () => void }) {
  const { state, notify, update, role } = useWorkspace()
  const [menu, setMenu] = useState(false)
  const [share, setShare] = useState(false)
  const [discussion, setDiscussion] = useState(false)
  const reviews = ideaReviews(state, idea.id)
  const latestReview = reviews.at(-1)
  const address = `${window.location.origin}${window.location.pathname}#/ideas/${idea.id}`
  async function copyLink() {
    try { await navigator.clipboard.writeText(address); update((current) => recordSignal(current, idea.id, previewActor(role), 'link_copy'), 'Project link copied. One discovery signal per participant, not a verified external share.'); setShare(false) }
    catch { notify('Clipboard unavailable. Select and copy the project URL below.') }
  }
  return <article className="feed-post">
    <header className="post-header"><Link className={`project-avatar ${idea.color}`} to={`/ideas/${idea.id}`} aria-label={`Open ${idea.title}`}><span>{idea.title.split(' ').map((word) => word[0]).join('').slice(0, 2)}</span></Link><div className="post-identity"><Link to={`/ideas/${idea.id}`}>{idea.title}<span className="project-version">V{idea.version}</span></Link><p>{idea.category}<span>·</span>{dateLabel(idea.updated)}</p></div><button className="icon-button post-menu" aria-label={`Options for ${idea.title}`} title="Project options" onClick={() => setMenu(true)}><MoreHorizontal size={23} /></button></header>
    <Link className={`post-media ${idea.color}`} to={covers[idea.id] ? `/ideas/${idea.id}/prototype` : `/ideas/${idea.id}`} aria-label={`Explore ${idea.title} preview`}>
      <div className="post-media-heading"><span>{idea.category.toUpperCase()} / CONCEPT {String(state.ideas.indexOf(idea) + 1).padStart(2, '0')}</span><ArrowUpRight size={24} /><h2>{idea.title}</h2><p>{idea.features.slice(0, 2).join(' + ')}</p></div>
      {covers[idea.id] ? <img src={covers[idea.id]} alt={`${idea.title} interactive sample prototype screenshot`} loading="lazy" width="1000" height="760" /> : <ProjectVisual idea={idea} />}
      <span className="media-caption">{covers[idea.id] ? 'INTERACTIVE SAMPLE' : 'IDEA DRAFT'}<ChevronRight size={13} /></span>
    </Link>
    <div className="post-actions"><button className="icon-button" title="Comments" aria-label={`Comments on ${idea.title}`} onClick={() => setDiscussion(true)}><MessageCircle size={25} /></button><button className="icon-button" title="Share project" aria-label={`Share ${idea.title}`} onClick={() => setShare(true)}><Send size={23} /></button><Link className="post-open" to={`/ideas/${idea.id}`}>Explore idea<ArrowUpRight size={15} /></Link><button className={`icon-button save-action ${saved ? 'is-saved' : ''}`} title={saved ? 'Unsave idea' : 'Save idea'} aria-label={`${saved ? 'Unsave' : 'Save'} ${idea.title}`} aria-pressed={saved} onClick={onSave}><Bookmark size={25} fill={saved ? 'currentColor' : 'none'} /></button></div>
    <InterestSignals idea={idea} />
    {discussion && <Modal title={`${idea.title} discussion`} onClose={() => setDiscussion(false)}><IdeaDiscussion idea={idea} /></Modal>}
    <div className="post-body"><div className="post-evidence"><strong>{reviews.length} {reviews.length === 1 ? 'review' : 'reviews'}</strong><Status value={idea.status} /></div><p className="post-caption"><strong>{idea.title}</strong> {idea.solution}</p><div className="post-tags">{idea.features.slice(0, 3).map((feature) => <span key={feature}>#{feature.replace(/\s+/g, '')}</span>)}</div><Link className="post-comments" to={`/feedback?idea=${idea.id}`}>{reviews.length ? `View all ${reviews.length} feedback records` : 'No feedback yet'}</Link>{latestReview && <p className="post-comment"><strong>{latestReview.reviewer}</strong> {latestReview.improvements}</p>}<span className="post-source">Sample project · Browser-local workspace</span></div>
    {menu && <Modal title={idea.title} onClose={() => setMenu(false)}><div className="post-menu-items"><Link to={`/ideas/${idea.id}`} onClick={() => setMenu(false)}>Project details<ArrowUpRight size={16} /></Link><Link to={`/evolution?idea=${idea.id}`} onClick={() => setMenu(false)}>Version proposals<ArrowUpRight size={16} /></Link><Link to={`/reports?idea=${idea.id}`} onClick={() => setMenu(false)}>Decision report<ArrowUpRight size={16} /></Link><button onClick={() => { onSave(); setMenu(false) }}>{saved ? 'Remove from saved' : 'Save to your collection'}<Bookmark size={16} /></button></div></Modal>}
    {share && <Modal title="Share this idea" onClose={() => setShare(false)}><p>{idea.title} · Local preview link</p><label className="share-url">Project URL<input aria-label="Project URL" readOnly value={address} onFocus={(event) => event.target.select()} /></label><button className="button primary" onClick={copyLink}>Copy link<Send size={15} /></button></Modal>}
  </article>
}

export function IdeaFeed() {
  const { state, notify } = useWorkspace()
  const [filter, setFilter] = useState('For you')
  const [saved, setSaved] = useState<string[]>(() => {
    try { const value: unknown = JSON.parse(localStorage.getItem(savedKey) ?? '[]'); return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string') : [] }
    catch { return [] }
  })
  function toggleSaved(id: string) {
    const next = saved.includes(id) ? saved.filter((entry) => entry !== id) : [...saved, id]
    setSaved(next)
    try { localStorage.setItem(savedKey, JSON.stringify(next)) }
    catch { notify('Saved ideas will only last for this session because browser storage is unavailable.') }
  }
  const ideas = state.ideas.filter((idea) => filter === 'Saved' ? saved.includes(idea.id) : filter === 'Review open' ? idea.status === 'Review open' : true)
  if (filter === 'Interest') ideas.sort((left, right) => interestSummary(state, right.id).discoveryScore - interestSummary(state, left.id).discoveryScore)
  return <div className="social-layout"><div className="feed-column">
    <div className="feed-title"><div><span className="feed-eyebrow"><Sparkles size={13} />A SPACE FOR WHAT'S NEXT</span><h1>Your daily dose of possibility.</h1></div><Link className="create-icon" aria-label="Create a new idea" title="Create a new idea" to="/ideas/new"><Plus size={22} /></Link></div>
    <div className="story-rail" aria-label="Project shortcuts"><Link className="story story-new" to="/ideas/new"><span className="story-ring"><span><Plus size={25} /></span></span><strong>Your next idea</strong></Link>{state.ideas.map((idea) => <Link className={`story ${idea.color}`} key={idea.id} to={`/ideas/${idea.id}`} aria-label={`View ${idea.title} story`}><span className="story-ring"><span>{idea.title.split(' ').map((word) => word[0]).join('').slice(0, 2)}</span></span><strong>{idea.title}</strong></Link>)}</div>
    <div className="feed-tabs" role="tablist" aria-label="Idea feed">{['For you', 'Review open', 'Interest', 'Saved'].map((tab) => <button role="tab" aria-selected={filter === tab} key={tab} onClick={() => setFilter(tab)}>{tab}{tab === 'Saved' && <Bookmark size={14} />}</button>)}<span><span className="feed-live-dot" />Preview feed</span></div>
    <div className="feed-posts">{ideas.length ? ideas.map((idea) => <FeedPost key={idea.id} idea={idea} saved={saved.includes(idea.id)} onSave={() => toggleSaved(idea.id)} />) : <Empty title={filter === 'Saved' ? 'Your collection starts here' : 'No open review cycles'}><p>{filter === 'Saved' ? 'Saved ideas will appear in this collection.' : 'Published ideas will appear here.'}</p><button className="button" onClick={() => setFilter('For you')}>Explore ideas</button></Empty>}</div>
    <div className="feed-end"><Check size={22} /><h3>You're all caught up.</h3><Link to="/ideas/new">What will you create next?</Link></div>
  </div><aside className="feed-side"><div className="feed-profile"><span className="avatar">YO</span><div><strong>Your creative space</strong><p>Idea owner · Preview</p></div><Link to="/settings" title="Workspace settings" aria-label="Workspace settings"><ArrowUpRight size={17} /></Link></div><div className="side-heading"><h2>In your orbit</h2><Link to="/ideas">See all</Link></div>{state.ideas.slice(0, 3).map((idea) => <Link className="suggested-project" key={idea.id} to={`/ideas/${idea.id}`}><span className={`project-avatar ${idea.color}`}>{idea.title.split(' ').map((word) => word[0]).join('').slice(0, 2)}</span><div><strong>{idea.title}</strong><p>{idea.category} · V{idea.version}</p></div><ArrowUpRight size={16} /></Link>)}
    <div className="side-callout"><Compass size={27} /><Badge tone="blue">A fresh perspective</Badge><h3>Good ideas get better together.</h3><p>{state.reviews.length} feedback records in your workspace.</p><Link to="/feedback">See what people think<ArrowRightIcon /></Link></div><div className="side-links"><Link to="/analytics">Analytics</Link><Link to="/trust">Trust & quality</Link><Link to="/workflows">Activity</Link><Link to="/reports">Reports</Link></div><p className="side-footnote">VERIDICA / IDEAS INTO EVIDENCE<br />Sample data. Real possibilities.</p>
  </aside></div>
}

function ArrowRightIcon() { return <ChevronRight size={15} /> }