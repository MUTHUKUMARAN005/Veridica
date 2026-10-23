import { ArrowUpRight, Check, GraduationCap, Leaf, MapPin, Search } from 'lucide-react';
export function ProjectVisual({ idea }) {
    return <div className={`project-visual ${idea.color}`} aria-label={`${idea.title} sample prototype preview`} role="img">
    <div className="mini-browser"><span /><span /><span /><i>{idea.category.toLowerCase()}.workspace</i></div>
    <div className="mini-app">
      <div className="mini-sidebar">{idea.color === 'mint' ? <GraduationCap size={18}/> : idea.color === 'blue' ? <Leaf size={18}/> : <MapPin size={18}/>}<span /><span /><span /><span /></div>
      <div className="mini-content"><div className="mini-title">{idea.title}<ArrowUpRight size={12}/></div>
        <div className="mini-search"><Search size={9}/>{idea.features[0]}</div>
        <div className="mini-tiles"><div><span className="mini-block"/><b>{idea.color === 'mint' ? 'Opportunities' : idea.color === 'blue' ? 'Collections' : 'Recently found'}</b><small>Sample workspace</small></div><div><span className="mini-block alternate"/><b>{idea.features[1]}</b><small>Ready to explore</small></div></div>
        <div className="mini-list"><Check size={11}/><span>{idea.features[2] ?? 'Your next step'}</span><span className="mini-pill"/></div>
      </div>
    </div>
  </div>;
}
