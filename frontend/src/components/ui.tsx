import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { AlertCircle, ArrowUpRight, Inbox, Loader2, RefreshCw, X } from 'lucide-react'
import { Link } from 'react-router'

export function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>
}

const STATUS_LABELS: Record<string, { label: string; tone: string }> = {
  'Review open': { label: 'Review open', tone: 'green' },
  Completed: { label: 'Completed', tone: 'green' },
  completed: { label: 'Completed', tone: 'green' },
  'Requirements ready': { label: 'Requirements ready', tone: 'green' },
  'Analysis ready': { label: 'Analysis ready', tone: 'green' },
  'Report ready': { label: 'Report ready', tone: 'green' },
  Active: { label: 'Active', tone: 'green' },
  Submitted: { label: 'Submitted', tone: 'green' },
  submitted: { label: 'Submitted', tone: 'green' },
  approved: { label: 'Approved', tone: 'green' },
  'Ready for review': { label: 'Ready for review', tone: 'blue' },
  'Evolution ready': { label: 'Evolution ready', tone: 'blue' },
  'Generating requirements': { label: 'Generating requirements', tone: 'blue' },
  'Analyzing feedback': { label: 'Analyzing feedback', tone: 'blue' },
  queued: { label: 'In progress', tone: 'blue' },
  running: { label: 'In progress', tone: 'blue' },
  in_progress: { label: 'In progress', tone: 'blue' },
  Assigned: { label: 'Assigned', tone: 'blue' },
  assigned: { label: 'Assigned', tone: 'blue' },
  proposed: { label: 'Awaiting approval', tone: 'blue' },
  'Awaiting analysis': { label: 'Awaiting analysis', tone: 'neutral' },
  'Awaiting report': { label: 'Awaiting report', tone: 'neutral' },
  Draft: { label: 'Draft', tone: 'neutral' },
  Pending: { label: 'Pending', tone: 'neutral' },
  Archived: { label: 'Archived', tone: 'neutral' },
  Revoked: { label: 'Revoked', tone: 'coral' },
  'Action required': { label: 'Action required', tone: 'coral' },
  failed: { label: 'Action required', tone: 'coral' },
}

export function Status({ value }: { value: string }) {
  const mapped = STATUS_LABELS[value] ?? {
    label: value.replaceAll('_', ' '),
    tone: 'blue',
  }
  return <Badge tone={mapped.tone}><span className="tiny-dot" />{mapped.label}</Badge>
}

export function PageHeading({ eyebrow, title, children, actions }: { eyebrow?: string; title: string; children?: ReactNode; actions?: ReactNode }) {
  return <div className="page-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1>{children && <p className="subtitle">{children}</p>}</div>{actions && <div className="heading-actions">{actions}</div>}</div>
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="empty"><Inbox size={32} strokeWidth={1.3} /><h3>{title}</h3>{children}</div>
}

export function LoadingState({
  title = 'Loading workspace...',
  description,
  detail,
}: {
  title?: string
  description?: string
  detail?: string
}) {
  const copy = description ?? detail
  return <div role="status" aria-live="polite" className="empty loading-state">
    <Loader2 size={28} className="spinning" />
    <h3>{title}</h3>
    {copy && <p>{copy}</p>}
  </div>
}

export function sanitizeUserMessage(raw: unknown, fallback = "We couldn't complete this action. Please try again."): string {
  if (!raw) return fallback
  const message = raw instanceof Error ? raw.message : String(raw)
  const trimmed = message.trim()
  if (!trimmed) return fallback
  if (
    /traceback|sqlalchemy|psycopg|httpx|ollama|gemini|celery|redis|langgraph|pgvector|exception|stack|http:\/\/|https:\/\/|\/api\/v1\//i.test(trimmed)
    || trimmed.length > 220
  ) {
    return fallback
  }
  return trimmed
}

export function ErrorBanner({
  message,
  onRetry,
  retryLabel = 'Try again',
}: {
  message: unknown
  onRetry?: () => void
  retryLabel?: string
}) {
  const safeMessage = sanitizeUserMessage(message)
  return <div role="alert" className="error-banner">
    <AlertCircle size={18} />
    <span>{safeMessage}</span>
    {onRetry && <button type="button" className="button compact" onClick={onRetry}><RefreshCw size={13} />{retryLabel}</button>}
  </div>
}

export function SectionHeading({ title, link, to }: { title: string; link?: string; to?: string }) {
  return <div className="section-heading"><h2>{title}</h2>{link && to && <Link className="text-link" to={to}>{link}<ArrowUpRight size={15} /></Link>}</div>
}

export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const reference = useRef<HTMLDialogElement>(null)
  useEffect(() => { const dialog = reference.current; dialog?.showModal(); return () => dialog?.close() }, [])
  return <dialog ref={reference} aria-label={title} className="modal" onCancel={onClose} onClick={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <div className="modal-heading"><h2>{title}</h2><button className="icon-button" aria-label="Close dialog" title="Close dialog" onClick={onClose}><X size={20} /></button></div>{children}
  </dialog>
}

export function ConfirmModal({
  title,
  description,
  confirmLabel = 'Confirm',
  danger = false,
  busy = false,
  onConfirm,
  onClose,
  onCancel,
}: {
  title: string
  description: string
  confirmLabel?: string
  danger?: boolean
  busy?: boolean
  onConfirm: () => void
  onClose?: () => void
  onCancel?: () => void
}) {
  const handleClose = onClose ?? onCancel ?? (() => undefined)
  return <Modal title={title} onClose={handleClose}>
    <p>{description}</p>
    <div className="form-actions">
      <button type="button" className="button" disabled={busy} onClick={handleClose}>Cancel</button>
      <button type="button" className={`button ${danger ? 'danger' : 'primary'}`} disabled={busy} onClick={onConfirm}>
        {busy ? 'Working...' : confirmLabel}
      </button>
    </div>
  </Modal>
}

export function dateLabel(value: string) {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return 'Recently'
  return parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function formatFactorLabel(factor: string): string {
  return factor
    .replaceAll('_', ' ')
    .replace(/^\w/, (letter) => letter.toUpperCase())
}
