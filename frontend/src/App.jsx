import { useEffect, useMemo, useState } from 'react'
import { api } from './api.js'
import TaskRow from './components/TaskRow.jsx'
import Calendar from './components/Calendar.jsx'
import Config from './components/Config.jsx'

const MONTHS = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
const todayISO = () => {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
export const prettyDate = (s) => {
  if (!s) return ''
  const [y, m, d] = s.split('-').map(Number)
  return `${MONTHS[m - 1]} ${String(d).padStart(2, '0')} ${y}`
}

export default function App() {
  const [tab, setTab] = useState('directives')
  const [tasks, setTasks] = useState([])
  const [events, setEvents] = useState([])
  const [cats, setCats] = useState([])
  const [types, setTypes] = useState([])
  const [loaded, setLoaded] = useState(false)

  // display prefs (persisted)
  const [scan, setScan] = useState(() => localStorage.getItem('pref_scan') !== 'off')
  const [glow, setGlow] = useState(() => localStorage.getItem('pref_glow') !== 'off')
  const [scale, setScale] = useState(() => parseFloat(localStorage.getItem('pref_scale')) || 1.1)
  useEffect(() => { localStorage.setItem('pref_scan', scan ? 'on' : 'off') }, [scan])
  useEffect(() => {
    localStorage.setItem('pref_glow', glow ? 'on' : 'off')
    document.documentElement.setAttribute('data-glow', glow ? 'on' : 'off')
  }, [glow])
  useEffect(() => { localStorage.setItem('pref_scale', String(scale)) }, [scale])
  const bumpScale = (d) => setScale((s) => Math.min(1.8, Math.max(0.8, Math.round((s + d) * 10) / 10)))

  const [filterType, setFilterType] = useState('all')
  const [filterCat, setFilterCat] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')

  const [draft, setDraft] = useState({ title: '', type: 'd2d', category: '', dateKind: 'open', date: todayISO() })

  const today = todayISO()

  async function reload() {
    const [t, e] = await Promise.all([api.tasks(), api.events()])
    setTasks(t); setEvents(e)
  }
  async function reloadConfig() {
    const [c, ty] = await Promise.all([api.categories(), api.types()])
    setCats(c); setTypes(ty)
    setDraft((d) => ({ ...d, category: c.includes(d.category) ? d.category : (c[0] || '') }))
  }
  useEffect(() => {
    (async () => {
      await reloadConfig()
      await reload()
      setLoaded(true)
    })()
  }, [])

  const catIdx = (c) => { const i = cats.indexOf(c); return i < 0 ? 99 : i }

  // visible = open tasks always; begin tasks from beginDate forward
  const visible = useMemo(
    () => tasks.filter((t) => t.dateKind === 'open' || (t.beginDate && t.beginDate <= today)),
    [tasks, today],
  )
  const filtered = visible.filter((t) => {
    if (filterType !== 'all' && t.type !== filterType) return false
    if (filterCat !== 'all' && t.category !== filterCat) return false
    if (filterStatus === 'active' && t.done) return false
    if (filterStatus === 'done' && !t.done) return false
    if (filterStatus === 'blocked' && !t.blocked) return false
    return true
  })
  const sortFn = (a, b) => (a.done - b.done) || (catIdx(a.category) - catIdx(b.category))
  const major = filtered.filter((t) => t.type === 'major').sort(sortFn)
  const d2d = filtered.filter((t) => t.type === 'd2d').sort(sortFn)
  const totalActive = major.length + d2d.length

  const todayEvents = events.filter((e) => e.start <= today && today <= e.end)

  // ---- mutations (call API, then reload) ----
  const wrap = (fn) => async (...a) => { await fn(...a); await reload() }
  const handlers = {
    onToggle: wrap((t) => api.setDone(t.id, !t.done)),
    onDel: wrap((id) => api.delTask(id)),
    onEdit: wrap((id, patch) => api.editTask(id, patch)),
    onAddSub: wrap((id, title) => api.addSub(id, title)),
    onToggleSub: wrap((s) => api.setSubDone(s.id, !s.done)),
    onDelSub: wrap((id) => api.delSub(id)),
    onLogTask: wrap((id, text) => api.logTask(id, text)),
    onLogSub: wrap((id, text) => api.logSub(id, text)),
    onSetBlockers: wrap((id, ids) => api.editTask(id, { blocked_by: ids.join(',') })),
  }

  async function addTask() {
    const title = draft.title.trim()
    if (!title) return
    await api.addTask({
      title, type: draft.type, category: draft.category,
      date: draft.dateKind === 'begin' ? draft.date : '',
    })
    setDraft((d) => ({ ...d, title: '' }))
    await reload()
  }

  const cycle = (arr, cur) => arr[(arr.indexOf(cur) + 1) % arr.length]
  const majorName = (types.find((t) => t.kind === 'major') || {}).name || 'MAJOR'
  const d2dName = (types.find((t) => t.kind === 'd2d') || {}).name || 'DAY-TO-DAY'
  const typeLabels = { major: majorName, d2d: d2dName }
  const draftHint = `> new ${draft.type === 'major' ? majorName : d2dName} task · [${draft.category}] · ` +
    (draft.dateKind === 'open' ? 'OPEN (carries over daily)' : `BEGINS ${draft.date}`)

  return (
    <>
      {scan && <div className="crt-scan" />}
      <div className="crt-vignette" />
      <div className="shell" style={{ textShadow: 'var(--glow)', zoom: scale }}>

        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 13, marginBottom: 20, flexWrap: 'wrap' }}>
          <span className="silk" style={{ fontSize: 15, color: 'var(--gd)', letterSpacing: 1, paddingBottom: 7 }}>ROOT@SYS:~#</span>
          <span className="silk" style={{ fontSize: 34, color: 'var(--g)', letterSpacing: 2, textShadow: glow ? '0 0 7px currentColor, 0 0 18px currentColor, 0 0 34px var(--g)' : 'none' }}>DIRECTIVES</span>
          <span className="silk cursor" style={{ fontSize: 28, color: 'var(--g)', paddingBottom: 2 }}>&#9646;</span>
          <span style={{ flex: 1, minWidth: 20 }} />
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', paddingBottom: 4 }}>
            <button className="action" title="text/button glow" onClick={() => setGlow((v) => !v)}>GLARE:{glow ? 'ON' : 'OFF'}</button>
            <button className="action" title="scanlines" onClick={() => setScan((v) => !v)}>SCAN:{scan ? 'ON' : 'OFF'}</button>
            <button className="action" title="smaller" onClick={() => bumpScale(-0.1)} style={{ fontSize: 11 }}>A&#8722;</button>
            <button className="action" title="larger" onClick={() => bumpScale(0.1)} style={{ fontSize: 16 }}>A+</button>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, marginBottom: 18, flexWrap: 'wrap' }}>
          <button className={'tab' + (tab === 'directives' ? ' active' : '')} onClick={() => setTab('directives')}>[ DIRECTIVES ]</button>
          <button className={'tab' + (tab === 'calendar' ? ' active' : '')} onClick={() => setTab('calendar')}>[ CALENDAR ]</button>
          <button className={'tab' + (tab === 'config' ? ' active' : '')} onClick={() => setTab('config')}>[ CONFIG ]</button>
        </div>

        {!loaded && <div className="muted" style={{ fontSize: 14 }}>&gt; loading directives_</div>}

        {loaded && tab === 'directives' && (
          <div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
              <input className="cmd" style={{ flex: '1 1 260px', minWidth: 220 }} placeholder="Enter command/task..."
                value={draft.title}
                onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                onKeyDown={(e) => { if (e.key === 'Enter') addTask() }} />
              <button className="cycle" onClick={() => setDraft({ ...draft, type: draft.type === 'major' ? 'd2d' : 'major' })}>TYPE: {(draft.type === 'major' ? majorName : d2dName).toUpperCase()}</button>
              <button className="cycle" onClick={() => setDraft({ ...draft, category: cycle(cats, draft.category) })}>CAT:{draft.category}</button>
              <button className="cycle" onClick={() => setDraft({ ...draft, dateKind: draft.dateKind === 'open' ? 'begin' : 'open' })}>{draft.dateKind === 'open' ? 'OPEN' : 'BEGIN'}</button>
              {draft.dateKind === 'begin' && (
                <input type="date" className="datein" value={draft.date} onChange={(e) => setDraft({ ...draft, date: e.target.value })} />
              )}
              <button className="solid commit" style={{ fontSize: 18, padding: '0 24px' }} onClick={addTask}>[ EXEC ]</button>
            </div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 12, letterSpacing: 1 }}>{draftHint}</div>

            <div style={{ height: 0, borderTop: '2px solid var(--g)', marginBottom: 16 }} />

            <div style={{ marginBottom: 14 }}>
              <div className="muted" style={{ fontSize: 13, letterSpacing: 2, marginBottom: 7 }}>// TODAY &#183; {prettyDate(today)}</div>
              {todayEvents.length > 0 ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {todayEvents.map((e) => (
                    <span key={e.id} style={{ border: '1px solid var(--gd)', padding: '4px 11px', fontSize: 13, color: 'var(--gb)' }}>
                      &#9670; {e.title}{e.single ? '' : ` · thru ${e.end}`}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="muted" style={{ fontSize: 13 }}>&#183; no scheduled events</div>
              )}
            </div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap', alignItems: 'center' }}>
              <span className="muted" style={{ fontSize: 12, letterSpacing: 1 }}>FILTER:</span>
              <button className="action" onClick={() => setFilterType(cycle(['all', 'major', 'd2d'], filterType))}>TYPE:{filterType === 'all' ? 'ALL' : (filterType === 'major' ? majorName : d2dName).toUpperCase()}</button>
              <button className="action" onClick={() => setFilterCat(cycle(['all', ...cats], filterCat))}>CAT:{filterCat === 'all' ? 'ALL' : filterCat}</button>
              <button className="action" onClick={() => setFilterStatus(cycle(['all', 'active', 'done', 'blocked'], filterStatus))}>STATUS:{filterStatus.toUpperCase()}</button>
              <span style={{ flex: 1 }} />
              <span className="muted" style={{ fontSize: 12 }}>{totalActive} ACTIVE</span>
            </div>

            {major.length > 0 && (
              <Section label={`&#9612; ${majorName.toUpperCase()}`} tag="// HIGH PRIORITY">
                {major.map((t) => <TaskRow key={t.id} task={t} allTasks={tasks} cats={cats} typeLabels={typeLabels} h={handlers} />)}
              </Section>
            )}
            {d2d.length > 0 && (
              <Section label={`&#9612; ${d2dName.toUpperCase()}`} tag="// ROUTINE">
                {d2d.map((t) => <TaskRow key={t.id} task={t} allTasks={tasks} cats={cats} typeLabels={typeLabels} h={handlers} />)}
              </Section>
            )}
            {totalActive === 0 && (
              <div className="muted" style={{ border: '1px dashed var(--gd)', padding: 40, textAlign: 'center', fontSize: 15, letterSpacing: 1 }}>&gt; NO ACTIVE DIRECTIVES &#183; awaiting input_</div>
            )}
          </div>
        )}

        {loaded && tab === 'calendar' && (
          <Calendar tasks={tasks} events={events} reload={reload} today={today} handlers={handlers} />
        )}

        {loaded && tab === 'config' && (
          <Config cats={cats} types={types.map((t) => t.name)} reload={reloadConfig} />
        )}
      </div>
    </>
  )
}

function Section({ label, tag, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '2px solid var(--gd)', borderBottom: '1px dotted var(--gd)', padding: '7px 0', marginBottom: 3 }}>
        <span className="silk" style={{ fontSize: 13, color: 'var(--g)', letterSpacing: 1 }} dangerouslySetInnerHTML={{ __html: label }} />
        <span className="muted" style={{ fontSize: 11, letterSpacing: 2 }}>{tag}</span>
      </div>
      {children}
    </div>
  )
}
