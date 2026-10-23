import { useEffect, useRef } from 'react';
import { ArrowUpRight, Inbox, X } from 'lucide-react';
import { Link } from 'react-router';
export function Badge({ children, tone = '' }) {
    return <span className={`badge ${tone}`}>{children}</span>;
}
export function Status({ value }) {
    return <Badge tone={value === 'Review open' || value === 'Completed' ? 'green' : value === 'Draft' ? 'neutral' : 'blue'}><span className="tiny-dot"/>{value}</Badge>;
}
export function PageHeading({ eyebrow, title, children, actions }) {
    return <div className="page-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1>{children && <p className="subtitle">{children}</p>}</div><div className="heading-actions">{actions}</div></div>;
}
export function Empty({ title, children }) {
    return <div className="empty"><Inbox size={32} strokeWidth={1.3}/><h3>{title}</h3>{children}</div>;
}
export function SectionHeading({ title, link, to }) {
    return <div className="section-heading"><h2>{title}</h2>{link && to && <Link className="text-link" to={to}>{link}<ArrowUpRight size={15}/></Link>}</div>;
}
export function Modal({ title, children, onClose }) {
    const reference = useRef(null);
    useEffect(() => { const dialog = reference.current; dialog?.showModal(); return () => dialog?.close(); }, []);
    return <dialog ref={reference} aria-label={title} className="modal" onCancel={onClose} onClick={(event) => { if (event.target === event.currentTarget)
        onClose(); }}>
    <div className="modal-heading"><h2>{title}</h2><button className="icon-button" aria-label="Close dialog" title="Close dialog" onClick={onClose}><X size={20}/></button></div>{children}
  </dialog>;
}
export function dateLabel(value) {
    return new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
