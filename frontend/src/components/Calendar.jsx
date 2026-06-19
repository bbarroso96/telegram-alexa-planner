import { useState } from 'react'
import { api } from '../api.js'
import { prettyDate } from '../App.jsx'

const MONTH_NAMES = ['JANUARY','FEBRUARY','MARCH','APRIL','MAY','JUNE','JULY','AUGUST','SEPTEMBER','OCTOBER','NOVEMBER','DECEMBER']
const WEEKDAYS = ['SUN','MON','TUE','WED','THU','FRI','SAT']
const pad = (n) => String(n).padStart(2, '0')
const iso = (y, m, d) => `${y}-${pad(m)}-${pad(d)}`

export default function Calendar({ tasks, events, reload, today, handlers }) {
  const [calMonth, setCalMonth] = useState(today.slice(0, 7))
  const [selDay, setSelDay] = useState(today)
  const [showForm, setShowForm] = useState(false)
  const [ev, setEv] = useState({ title: '', mode: 'single', start: today, end: today, comment: '' })
  const [cThread, setCThread] = useState({})   // eventId -> open
  const [cDraft, setCDraft] = useState({})     // eventId -> text
  const [editEv, setEditEv] = useState(null)   // {id, title, mode, start, end}

  const [y, m] = calMonth.split('-').map(Number)

  async function addEvent() {
    const title = ev.title.trim()
    if (!title) return
    const single = ev.mode === 'single'
    await api.addEvent({ title, single, start: ev.start, end: single ? ev.start : ev.end, comment: ev.comment.trim() })
    setEv({ title: '', mode: 'single', start: today, end: today, comment: '' })
    setShowForm(false)
    await reload()
  }
  const delEvent = async (id) => { await api.delEvent(id); await reload() }
  const startEditEv = (e) => setEditEv({ id: e.id, title: e.title, mode: e.single ? 'single' : 'range', start: e.start, end: e.end })
  const saveEditEv = async () => {
    const f = editEv; const title = f.title.trim(); if (!title) return
    const single = f.mode === 'single'
    let start = f.start, end = single ? f.start : f.end
    if (!single && end < start) [start, end] = [end, start]
    await api.editEvent(f.id, { title, single, start, end })
    setEditEv(null); await reload()
  }
  const addComment = async (id) => { const v = (cDraft[id] || '').trim(); if (!v) return; await api.commentEvent(id, v); setCDraft({ ...cDraft, [id]: '' }); await reload(); setCThread({ ...cThread, [id]: true }) }

  function shiftMonth(n) {
    let yy = y, mm = m + n
    while (mm > 12) { mm -= 12; yy++ }
    while (mm < 1) { mm += 12; yy-- }
    setCalMonth(iso(yy, mm, 1).slice(0, 7))
  }

  // build grid
  const first = new Date(y, m - 1, 1).getDay()
  const dim = new Date(y, m, 0).getDate()
  const cells = []
  for (let i = 0; i < first; i++) cells.push({ pad: true, key: 'p' + i })
  for (let d = 1; d <= dim; d++) {
    const date = iso(y, m, d)
    const items = []
    events.forEach((e) => {
      if (e.start <= date && date <= e.end) {
        let lbl = e.title
        if (!e.single) { if (date === e.start) lbl = '▸ ' + e.title; else if (date === e.end) lbl = e.title + ' ◂'; else lbl = '·· ' + e.title }
        items.push({ label: lbl, kind: 'event' })
      }
    })
    tasks.forEach((t) => { if (t.dateKind === 'begin' && t.beginDate === date) items.push({ label: 'BEGINNING ' + t.title, kind: 'begin' }) })
    if (date === today) { const n = tasks.filter((t) => t.dateKind === 'open' && !t.done).length; if (n > 0) items.push({ label: `TASKS (${n})`, kind: 'tasks' }) }
    cells.push({ pad: false, key: date, date, day: d, items, isToday: date === today, isSel: date === selDay })
  }
  while (cells.length % 7 !== 0) cells.push({ pad: true, key: 'pe' + cells.length })
  const weeks = []
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7))

  const selEvents = events.filter((e) => e.start <= selDay && selDay <= e.end)
  const selBegins = tasks.filter((t) => t.dateKind === 'begin' && t.beginDate === selDay)
  const selOpen = selDay === today ? tasks.filter((t) => t.dateKind === 'open') : []
  const selEmpty = selEvents.length === 0 && selBegins.length === 0 && selOpen.length === 0

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 14, flexWrap: 'wrap' }}>
        <button className="action" onClick={() => shiftMonth(-1)}>&#9666; PREV</button>
        <span className="silk" style={{ fontSize: 18, color: 'var(--g)', letterSpacing: 1, minWidth: 200 }}>{MONTH_NAMES[m - 1]} {y}</span>
        <button className="action" onClick={() => shiftMonth(1)}>NEXT &#9656;</button>
        <span style={{ flex: 1 }} />
        <button className="action" onClick={() => { setCalMonth(today.slice(0, 7)); setSelDay(today) }}>[ TODAY ]</button>
        <button className="solid" style={{ fontFamily: "'Share Tech Mono', monospace", fontSize: 13, padding: '6px 14px' }} onClick={() => setShowForm((v) => !v)}>{showForm ? '× CLOSE' : '+ NEW EVENT'}</button>
      </div>

      {showForm && (
        <div style={{ border: '1px solid var(--gd)', padding: 13, marginBottom: 14, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', background: 'rgba(43,255,102,0.03)' }}>
          <input className="box" style={{ flex: '1 1 240px' }} placeholder="event name (e.g. Jaime visiting)..." value={ev.title} onChange={(e) => setEv({ ...ev, title: e.target.value })} />
          <button className="cycle" style={{ padding: '7px 12px' }} onClick={() => setEv({ ...ev, mode: ev.mode === 'single' ? 'range' : 'single' })}>{ev.mode === 'single' ? '1 DAY' : 'RANGE'}</button>
          <input type="date" className="box" value={ev.start} onChange={(e) => setEv({ ...ev, start: e.target.value })} />
          {ev.mode === 'range' && <><span className="muted">→</span><input type="date" className="box" value={ev.end} onChange={(e) => setEv({ ...ev, end: e.target.value })} /></>}
          <input className="box" style={{ flex: '1 1 180px' }} placeholder="comment (optional)" value={ev.comment} onChange={(e) => setEv({ ...ev, comment: e.target.value })} />
          <button className="solid commit" style={{ fontSize: 14, padding: '7px 16px' }} onClick={addEvent}>[ ADD ]</button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 6, marginBottom: 6 }}>
        {WEEKDAYS.map((wd) => <div key={wd} className="muted" style={{ textAlign: 'center', fontSize: 12, letterSpacing: 1, padding: '2px 0' }}>{wd}</div>)}
      </div>

      {weeks.map((w, wi) => (
        <div key={wi} style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 6, marginBottom: 6 }}>
          {w.map((c) => c.pad ? (
            <div key={c.key} style={{ minHeight: 94, border: '1px solid transparent' }} />
          ) : (
            <div key={c.key} onClick={() => setSelDay(c.date)} style={{
              minHeight: 94, padding: '5px 6px', cursor: 'pointer', overflow: 'hidden',
              border: '1px solid ' + (c.isSel ? 'var(--g)' : 'rgba(43,255,102,0.18)'),
              background: c.isToday ? 'rgba(43,255,102,0.10)' : (c.isSel ? 'rgba(43,255,102,0.05)' : 'transparent'),
            }}>
              <div style={{ fontSize: 13, ...(c.isToday
                ? { color: 'var(--bg)', background: 'var(--g)', display: 'inline-block', minWidth: 18, textAlign: 'center', fontWeight: 700, textShadow: 'none', padding: '0 2px' }
                : { color: 'var(--gd)' }) }}>{c.day}</div>
              {c.items.map((it, i) => <div key={i} style={chipStyle(it.kind)}>{it.label}</div>)}
            </div>
          ))}
        </div>
      ))}

      <div style={{ border: '1px solid var(--gd)', marginTop: 14, padding: 15 }}>
        <div className="silk" style={{ fontSize: 14, color: 'var(--g)', marginBottom: 12, letterSpacing: 1 }}>&#9612; {prettyDate(selDay)}{selDay === today ? '  // TODAY' : ''}</div>

        {selEvents.map((e) => (
          <div key={e.id} style={{ marginBottom: 11 }}>
            {editEv && editEv.id === e.id ? (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <input className="box" style={{ flex: '1 1 200px' }} value={editEv.title} onChange={(ev2) => setEditEv({ ...editEv, title: ev2.target.value })} />
                <button className="cycle" style={{ padding: '7px 12px' }} onClick={() => setEditEv({ ...editEv, mode: editEv.mode === 'single' ? 'range' : 'single' })}>{editEv.mode === 'single' ? '1 DAY' : 'RANGE'}</button>
                <input type="date" className="box" value={editEv.start} onChange={(ev2) => setEditEv({ ...editEv, start: ev2.target.value })} />
                {editEv.mode === 'range' && <><span className="muted">→</span><input type="date" className="box" value={editEv.end} onChange={(ev2) => setEditEv({ ...editEv, end: ev2.target.value })} /></>}
                <button className="action commit" onClick={saveEditEv}>SAVE</button>
                <button className="action" onClick={() => setEditEv(null)}>CANCEL</button>
              </div>
            ) : (
              <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
                <span style={{ color: 'var(--g)' }}>&#9670;</span>
                <span style={{ fontSize: 16, color: 'var(--gb)' }}>{e.title}</span>
                <span className="muted" style={{ fontSize: 12 }}>{e.single ? prettyDate(e.start) : `${prettyDate(e.start)} → ${prettyDate(e.end)}`}</span>
                <span style={{ flex: 1, minWidth: 10 }} />
                <button className="link" onClick={() => setCThread({ ...cThread, [e.id]: !cThread[e.id] })}>▬ {e.comments.length || ''} note{e.comments.length !== 1 ? 's' : ''} {cThread[e.id] ? '▾' : '▸'}</button>
                <button className="action" onClick={() => startEditEv(e)}>EDIT</button>
                <button className="action" onClick={() => delEvent(e.id)}>DEL</button>
              </div>
            )}
            {cThread[e.id] && (
              <div style={{ margin: '5px 0 0 18px' }}>
                {e.comments.map((c) => (
                  <div key={c.id} className="muted" style={{ fontSize: 13, padding: '1px 0' }}>&#9492; <span style={{ color: 'var(--g)' }}>{c.ts}</span> &#183; {c.text}</div>
                ))}
                <div style={{ display: 'flex', gap: 8, marginTop: 5 }}>
                  <input className="box" style={{ flex: 1, fontSize: 13 }} placeholder="add comment..." value={cDraft[e.id] || ''} onChange={(ev2) => setCDraft({ ...cDraft, [e.id]: ev2.target.value })} onKeyDown={(ev2) => { if (ev2.key === 'Enter') addComment(e.id) }} />
                  <button className="action commit" onClick={() => addComment(e.id)}>ADD</button>
                </div>
              </div>
            )}
          </div>
        ))}

        {selBegins.map((b) => (
          <div key={b.id} style={{ display: 'flex', gap: 8, alignItems: 'baseline', marginBottom: 7 }}>
            <span style={{ background: 'var(--g)', color: 'var(--bg)', fontSize: 11, fontWeight: 700, padding: '1px 7px', letterSpacing: 1, textShadow: 'none' }}>BEGINNING</span>
            <span style={{ fontSize: 16, color: 'var(--gb)' }}>{b.title}</span>
            <span style={{ fontSize: 11, border: '1px solid var(--gd)', color: 'var(--gd)', padding: '1px 6px' }}>{b.category}</span>
          </div>
        ))}

        {selOpen.length > 0 && (
          <div style={{ marginTop: 6 }}>
            <div className="muted" style={{ fontSize: 12, letterSpacing: 2, marginBottom: 5 }}>// CARRIED-OVER TASKS</div>
            {selOpen.map((o) => (
              <div key={o.id} style={{ display: 'flex', gap: 8, alignItems: 'baseline', padding: '2px 0' }}>
                <button onClick={() => handlers.onToggle(o)} style={{ background: 'none', border: 'none', color: 'var(--g)', font: "15px 'Share Tech Mono', monospace", padding: 0, textShadow: 'inherit' }}>{o.done ? '[X]' : '[ ]'}</button>
                <span style={{ fontSize: 15, color: 'var(--gb)', ...(o.done ? { textDecoration: 'line-through', opacity: 0.45 } : {}) }}>{o.title}</span>
                <span style={{ fontSize: 11, border: '1px solid var(--gd)', color: 'var(--gd)', padding: '1px 6px' }}>{o.category}</span>
              </div>
            ))}
          </div>
        )}

        {selEmpty && <div className="muted" style={{ fontSize: 14 }}>&gt; nothing scheduled_</div>}
      </div>
    </div>
  )
}

function chipStyle(kind) {
  const base = { fontSize: 11, padding: '1px 4px', marginTop: 3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }
  if (kind === 'tasks') return { ...base, background: 'var(--g)', color: 'var(--bg)', fontWeight: 700, textShadow: 'none', padding: '1px 5px' }
  if (kind === 'begin') return { ...base, color: 'var(--gb)', borderLeft: '2px solid var(--g)' }
  return { ...base, color: 'var(--gd)', borderLeft: '2px solid var(--gd)' }
}
