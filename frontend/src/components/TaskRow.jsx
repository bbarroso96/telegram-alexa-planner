import { useState } from 'react'

const today = (() => { const d = new Date(); const p = n => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}` })()

export default function TaskRow({ task, allTasks, cats, h, typeLabels = { major: 'MAJOR', d2d: 'DAY2DAY' } }) {
  const [showLog, setShowLog] = useState(false)
  const [logText, setLogText] = useState('')
  const [showBlk, setShowBlk] = useState(false)
  const [blkSel, setBlkSel] = useState(task.blocked_by || [])
  const [subText, setSubText] = useState('')
  const [updOpen, setUpdOpen] = useState(false)
  const [subUpd, setSubUpd] = useState({})      // subId -> bool (thread open)
  const [subLog, setSubLog] = useState({})      // subId -> draft text (null = closed)
  const [edit, setEdit] = useState(null)        // null or {title,type,category,dateKind,date}

  const dateLabel = task.dateKind === 'open'
    ? '↻ DAILY'
    : (task.beginDate <= today ? 'ACTIVE ▸ ' : 'BEGINS ▸ ') + task.beginDate

  const submitLog = () => { const v = logText.trim(); if (!v) return; h.onLogTask(task.id, v); setLogText(''); setShowLog(false); setUpdOpen(true) }
  const submitSub = () => { const v = subText.trim(); if (!v) return; h.onAddSub(task.id, v); setSubText('') }
  const submitSubLog = (sid) => { const v = (subLog[sid] || '').trim(); if (!v) return; h.onLogSub(sid, v); setSubLog({ ...subLog, [sid]: undefined }); setSubUpd({ ...subUpd, [sid]: true }) }
  const saveBlockers = () => { h.onSetBlockers(task.id, blkSel); setShowBlk(false) }

  const startEdit = () => setEdit({ title: task.title, type: task.type, category: task.category, dateKind: task.dateKind, date: task.beginDate || today })
  const saveEdit = () => {
    h.onEdit(task.id, { title: edit.title.trim() || task.title, type: edit.type, category: edit.category, date: edit.dateKind === 'begin' ? edit.date : '' })
    setEdit(null)
  }
  const cycle = (arr, cur) => arr[(arr.indexOf(cur) + 1) % arr.length]

  const candidates = allTasks.filter((t) => t.id !== task.id)

  return (
    <div style={{ borderBottom: '1px dotted var(--gd)', padding: '13px 0' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <button onClick={() => h.onToggle(task)} style={iconBtn(19)}>{task.done ? '[X]' : '[ ]'}</button>
        <span style={{ fontSize: 19, color: 'var(--gb)', ...(task.done ? struck : {}) }}>{task.title}</span>
        <span style={tag}>{task.category}</span>
        <span style={{ flex: 1, minWidth: 20 }} />
        <span className="muted" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{dateLabel}</span>
        <button className="action" onClick={() => setShowBlk((v) => !v)}>!BLK</button>
        <button className="action" onClick={() => setShowLog((v) => !v)}>+LOG</button>
        <button className="action" onClick={startEdit}>EDIT</button>
        <button className="action" onClick={() => h.onDel(task.id)}>DEL</button>
      </div>

      {task.blocked && (
        <div style={{ margin: '9px 0 2px 30px', display: 'flex', alignItems: 'center', gap: 9, flexWrap: 'wrap' }}>
          <span style={invChip}>!! BLOCKED</span>
          <span style={{ fontSize: 14, color: 'var(--gb)' }}>waiting on: {task.waiting_on.join(', ')}</span>
          <button className="action" onClick={() => h.onSetBlockers(task.id, [])}>CLEAR</button>
        </div>
      )}

      {showBlk && (
        <div style={{ margin: '9px 0 2px 30px' }}>
          <div className="muted" style={{ fontSize: 12, letterSpacing: 1, marginBottom: 4 }}>blocked by which directive(s)?</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 6 }}>
            {candidates.length === 0 && <span className="muted" style={{ fontSize: 13 }}>· no other directives</span>}
            {candidates.map((c) => {
              const on = blkSel.includes(c.id)
              return (
                <button key={c.id} className="action" style={on ? { background: 'var(--g)', color: 'var(--bg)', textShadow: 'none' } : {}}
                  onClick={() => setBlkSel(on ? blkSel.filter((x) => x !== c.id) : [...blkSel, c.id])}>
                  {on ? '[x] ' : '[ ] '}{c.title}
                </button>
              )
            })}
          </div>
          <button className="action commit" onClick={saveBlockers}>SET BLOCK</button>
        </div>
      )}

      {showLog && (
        <div style={{ margin: '9px 0 2px 30px', display: 'flex', gap: 8 }}>
          <input className="box" style={{ flex: 1 }} placeholder="log an update on this directive..."
            value={logText} onChange={(e) => setLogText(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') submitLog() }} />
          <button className="action commit" onClick={submitLog}>LOG</button>
        </div>
      )}

      {edit && (
        <div style={{ margin: '9px 0 2px 30px', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input className="box" style={{ flex: '1 1 200px' }} value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} />
          <button className="cycle" onClick={() => setEdit({ ...edit, type: edit.type === 'major' ? 'd2d' : 'major' })}>TYPE: {(edit.type === 'major' ? typeLabels.major : typeLabels.d2d).toUpperCase()}</button>
          <button className="cycle" onClick={() => setEdit({ ...edit, category: cycle(cats, edit.category) })}>CAT:{edit.category}</button>
          <button className="cycle" onClick={() => setEdit({ ...edit, dateKind: edit.dateKind === 'open' ? 'begin' : 'open' })}>{edit.dateKind === 'open' ? 'OPEN' : 'BEGIN'}</button>
          {edit.dateKind === 'begin' && <input type="date" className="datein" value={edit.date} onChange={(e) => setEdit({ ...edit, date: e.target.value })} />}
          <button className="action commit" onClick={saveEdit}>SAVE</button>
          <button className="action" onClick={() => setEdit(null)}>CANCEL</button>
        </div>
      )}

      {/* subtask tree */}
      <div style={{ margin: '7px 0 0 9px', borderLeft: '1px dotted var(--gm)' }}>
        {task.subs.map((s) => (
          <div key={s.id}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '3px 0' }}>
              <span style={{ flex: 'none', width: 14, height: 0, borderTop: '1px solid var(--gm)' }} />
              <button onClick={() => h.onToggleSub(s)} style={iconBtn(16)}>{s.done ? '[X]' : '[ ]'}</button>
              <span style={{ fontSize: 16, color: 'var(--gb)', ...(s.done ? struck : {}) }}>{s.title}</span>
              {s.updates.length > 0 && (
                <button className="link" onClick={() => setSubUpd({ ...subUpd, [s.id]: !subUpd[s.id] })}>[{s.updates.length}{subUpd[s.id] ? '▾' : '▸'}]</button>
              )}
              <span style={{ flex: 1, minWidth: 14, height: 0, borderTop: '2px dotted var(--gm)', margin: '0 10px' }} />
              <button className="link" onClick={() => setSubLog({ ...subLog, [s.id]: subLog[s.id] === undefined ? '' : undefined })}>+log</button>
              <button className="action" style={{ padding: '2px 8px' }} onClick={() => h.onDelSub(s.id)}>X</button>
            </div>
            {subUpd[s.id] && (
              <div style={{ margin: '1px 0 4px 30px' }}>
                {s.updates.map((u) => <ThreadLine key={u.id} u={u} />)}
              </div>
            )}
            {subLog[s.id] !== undefined && (
              <div style={{ margin: '2px 0 6px 30px', display: 'flex', gap: 8 }}>
                <input className="box" style={{ flex: 1, fontSize: 13 }} placeholder="update on subtask..."
                  value={subLog[s.id]} onChange={(e) => setSubLog({ ...subLog, [s.id]: e.target.value })}
                  onKeyDown={(e) => { if (e.key === 'Enter') submitSubLog(s.id) }} />
                <button className="action commit" onClick={() => submitSubLog(s.id)}>LOG</button>
              </div>
            )}
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '3px 0' }}>
          <span style={{ flex: 'none', width: 14, height: 0, borderTop: '1px solid var(--gm)' }} />
          <input style={{ flex: 1, background: 'none', border: 'none', borderBottom: '1px dotted var(--gd)', color: 'var(--gb)', font: "15px 'Share Tech Mono', monospace", outline: 'none', padding: '3px 2px' }}
            placeholder="Append sub-process..." value={subText} onChange={(e) => setSubText(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') submitSub() }} />
          <button className="action commit" onClick={submitSub}>ADD</button>
        </div>
      </div>

      {task.updates.length > 0 && (
        <div style={{ margin: '7px 0 0 18px' }}>
          <button className="link" style={{ fontSize: 13, letterSpacing: 1 }} onClick={() => setUpdOpen((v) => !v)}>
            &#187; {task.updates.length} LOG{task.updates.length > 1 ? 'S' : ''} {updOpen ? '▾' : '▸'}
          </button>
          {updOpen && <div style={{ margin: '4px 0 0 14px' }}>{task.updates.map((u) => <ThreadLine key={u.id} u={u} />)}</div>}
        </div>
      )}
    </div>
  )
}

function ThreadLine({ u }) {
  return (
    <div className="muted" style={{ fontSize: 13, padding: '1px 0' }}>
      &#9492; <span style={{ color: 'var(--g)' }}>{u.ts}</span> &#183; {u.text}
    </div>
  )
}

const struck = { textDecoration: 'line-through', opacity: 0.45 }
const iconBtn = (size) => ({ background: 'none', border: 'none', color: 'var(--g)', font: `${size}px 'Share Tech Mono', monospace`, padding: 0, textShadow: 'inherit' })
const tag = { fontSize: 11, border: '1px solid var(--gd)', color: 'var(--gd)', padding: '1px 7px', letterSpacing: 1 }
const invChip = { background: 'var(--g)', color: 'var(--bg)', fontWeight: 700, fontSize: 12, padding: '2px 9px', letterSpacing: 2, textShadow: 'none' }
