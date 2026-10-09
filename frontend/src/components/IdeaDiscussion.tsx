import { useState } from 'react'
import { Link } from 'react-router'
import { Heart, MessageCircle, Send, ThumbsUp } from 'lucide-react'
import { addComment, interestSummary, previewActor, rankPriorities, recordSignal, toggleCommentSupport } from '../services/preview'
import type { Idea, IdeaComment } from '../services/preview'
import { useWorkspace } from '../services/workspace'
import { Badge, dateLabel } from './ui'

export function InterestSignals({ idea }: { idea: Idea }) {
  const { state, update, role } = useWorkspace()
  const actor = previewActor(role)
  const summary = interestSummary(state, idea.id)
  const liked = state.signals.some((signal) => signal.ideaId === idea.id && signal.version === idea.version && signal.actor === actor && signal.kind === 'interest')
  return <div className="interest-signals"><button type="button" className={liked ? 'liked' : ''} aria-label={`${liked ? 'Unlike' : 'Like'} ${idea.title}`} aria-pressed={liked} title="Interest only, not a validation score" onClick={() => update((current) => recordSignal(current, idea.id, actor, 'interest'))}><Heart size={21} fill={liked ? 'currentColor' : 'none'} /><span>{summary.likes} interested</span></button><span>{summary.linkCopies} unique link {summary.linkCopies === 1 ? 'copy' : 'copies'}</span><small>Local interest, not trust</small></div>
}

export function IdeaDiscussion({ idea, canComment = true }: { idea: Idea; canComment?: boolean }) {
  const { state, update, role, notify } = useWorkspace()
  const [text, setText] = useState('')
  const [context, setContext] = useState('')
  const [kind, setKind] = useState<IdeaComment['kind']>('suggestion')
  const actor = previewActor(role)
  const comments = state.comments.filter((comment) => comment.ideaId === idea.id && comment.version === idea.version)
  const priorities = rankPriorities(state, idea.id)
  const open = idea.status === 'Review open'
  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canComment) { notify('Try the prototype before leaving a review comment.'); return }
    try {
      const next = addComment(state, { id: crypto.randomUUID(), ideaId: idea.id, version: idea.version, author: actor, kind, text, context, created: new Date().toISOString() })
      update(() => next, 'Comment saved. It is available for owner prioritization; no AI analysis has run.')
      setText(''); setContext('')
    } catch (error) { notify(error instanceof Error ? error.message : 'Unable to post comment.') }
  }
  return <section className="idea-discussion" aria-label="Idea comments"><div className="discussion-heading"><h2><MessageCircle size={20} />Comments <span>{comments.length}</span></h2>{role !== 'reviewer' && <Link to={`/evolution?idea=${idea.id}`} className="text-link">Prioritize improvements</Link>}</div><InterestSignals idea={idea} />
    {open ? <form className="comment-composer" onSubmit={submit}><div className="comment-author"><span className="avatar">{actor.split(' ').map((part) => part[0]).join('')}</span><strong>{actor}</strong><Badge>V{idea.version} · Local</Badge></div><label>Comment type<select aria-label="Comment type" value={kind} onChange={(event) => setKind(event.target.value as IdeaComment['kind'])}><option value="suggestion">Improvement suggestion</option><option value="problem">Problem to solve</option><option value="question">Question / discussion</option></select></label><label>Your comment<textarea required minLength={10} maxLength={2000} value={text} onChange={(event) => setText(event.target.value)} placeholder="What should change, and why would it help?" rows={3} /></label><label>What did you try?<input required minLength={10} maxLength={1000} value={context} onChange={(event) => setContext(event.target.value)} placeholder="Screen, task, device, or observed problem" /></label><div className="comment-submit"><small>{canComment ? 'Suggestions inform priorities; questions stay in discussion.' : 'Open and interact with the prototype first.'}</small><button className="button primary" disabled={!canComment} type="submit"><Send size={14} />Post comment</button></div></form> : <p className="discussion-empty">Comments open when this idea is published for review.</p>}
    <div className="comment-thread">{comments.length ? [...comments].reverse().map((comment) => <article className="comment-entry" key={comment.id} id={comment.id}><header><strong>{comment.author}</strong><Badge tone="blue">{comment.kind}</Badge><time>{dateLabel(comment.created)}</time></header><p>{comment.text}</p><small>{comment.context}</small><footer><button type="button" className={comment.supporters.includes(actor) ? 'supported' : ''} aria-label={`Useful comment by ${comment.author}`} aria-pressed={comment.supporters.includes(actor)} disabled={actor === comment.author} title={actor === comment.author ? 'Other participants can mark your comment useful' : 'This suggestion is useful'} onClick={() => update((current) => toggleCommentSupport(current, comment.id, actor))}><ThumbsUp size={15} />Useful · {comment.supporters.length}</button><Badge>{priorities.find((item) => item.id === comment.id)?.priority ?? 'Needs estimate'}</Badge></footer></article>) : <p className="discussion-empty">No comments yet. A specific suggestion can shape the next version.</p>}</div>
  </section>
}