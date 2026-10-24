import { useState } from 'react'
import type { FormEvent } from 'react'
import type { PrototypePreviewSpec } from '../services/ideas'

export function SchemaPrototypePreview({ spec }: { spec: PrototypePreviewSpec }) {
  const screens = Array.isArray(spec?.screens) ? spec.screens : []
  const [screenKey, setScreenKey] = useState(screens[0]?.key ?? 'overview')
  const [query, setQuery] = useState('')
  const [checked, setChecked] = useState<string[]>([])
  const [note, setNote] = useState('')
  const [savedNote, setSavedNote] = useState(false)
  const [complete, setComplete] = useState(false)
  const screen = screens.find((item) => item.key === screenKey) ?? screens[0]
  const components = Array.isArray(screen?.components) ? screen.components : []
  if (!screen) return <p className="muted">This prototype has no supported screens.</p>

  function submitNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSavedNote(true)
    setNote('')
  }

  return <section className="schema-prototype" aria-label="Schema-driven prototype preview">
    <div className="notice">
      <strong>Interactive prototype preview · Version {spec.source_version}</strong>
      <p>Explore the screens and user flows below to evaluate this version.</p>
    </div>
    <nav className="schema-prototype-nav" aria-label="Prototype screens">
      {screens.map((item) => <button
        type="button"
        className="button"
        aria-current={screen.key === item.key ? 'page' : undefined}
        key={item.key}
        onClick={() => setScreenKey(item.key)}
      >{item.title}</button>)}
    </nav>
    <div className="schema-prototype-screen">
      <h3>{screen.title}</h3>
      {components.map((component, index) => {
        const key = `${screen.key}-${component.type}-${index}`
        switch (component.type) {
          case 'heading':
            return <h2 key={key}>{component.text}</h2>
          case 'text':
            return <p key={key}>{component.text}</p>
          case 'card':
            return <article className="schema-prototype-card" key={key}><h4>{component.title}</h4><p>{component.body}</p></article>
          case 'search': {
            const items = component.items.filter((item) => item.toLowerCase().includes(query.toLowerCase()))
            return <section key={key}><label>{component.label}<input value={query} onChange={(event) => setQuery(event.target.value)} /></label>{items.length
              ? <ul>{items.map((item, itemIndex) => <li key={`${item}-${itemIndex}`}>{item}</li>)}</ul>
              : <p className="muted">No matching validated features.</p>}</section>
          }
          case 'checklist':
            return <section key={key}><h4>{component.title}</h4>{component.items.length
              ? component.items.map((item, itemIndex) => <label className="schema-prototype-check" key={`${item}-${itemIndex}`}><input
                type="checkbox"
                checked={checked.includes(`${key}-${itemIndex}`)}
                onChange={() => setChecked((current) => current.includes(`${key}-${itemIndex}`)
                  ? current.filter((entry) => entry !== `${key}-${itemIndex}`)
                  : [...current, `${key}-${itemIndex}`])}
              />{item}</label>)
              : <p className="muted">No validated journey steps are available yet.</p>}</section>
          case 'form':
            return <form key={key} onSubmit={submitNote}><label>{component.label}<textarea required value={note} placeholder={component.placeholder} onChange={(event) => { setNote(event.target.value); setSavedNote(false) }} /></label><button className="button primary">{component.submit_label}</button>{savedNote && <p role="status">Note saved in this browser session only.</p>}</form>
          case 'button':
            return <button className="button" key={key} onClick={() => setComplete(true)}>{complete ? 'Completed' : component.label}</button>
        }
      })}
    </div>
  </section>
}
