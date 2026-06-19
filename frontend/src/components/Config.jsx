import { useState } from 'react'
import { api } from '../api.js'

export default function Config({ cats, types, reload }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 12, letterSpacing: 2, marginBottom: 16 }}>
        // SYSTEM CONFIG · reference data used by the command bar &amp; filters
      </div>
      <ConfigList
        title="&#9612; CATEGORIES"
        items={cats}
        placeholder="new category name..."
        onAdd={async (n) => { await api.addCategory(n); await reload() }}
        onDel={async (n) => { await api.delCategory(n); await reload() }}
        onRename={async (oldN, newN) => { await api.renameCategory(oldN, newN); await reload() }}
      />
      <div style={{ height: 18 }} />
      <ConfigList
        title="&#9612; TYPES"
        items={types}
        placeholder="new type name..."
        onAdd={async (n) => { await api.addType(n); await reload() }}
        onDel={async (n) => { await api.delType(n); await reload() }}
        onRename={async (oldN, newN) => { await api.renameType(oldN, newN); await reload() }}
      />
    </div>
  )
}

function ConfigList({ title, items, placeholder, onAdd, onDel, onRename, note }) {
  const [draft, setDraft] = useState('')
  const [editing, setEditing] = useState(null)   // name being renamed
  const [editVal, setEditVal] = useState('')
  const submit = async () => { const v = draft.trim(); if (!v) return; await onAdd(v); setDraft('') }
  const startEdit = (name) => { setEditing(name); setEditVal(name) }
  const saveEdit = async () => { const v = editVal.trim(); if (v && v !== editing) await onRename(editing, v); setEditing(null) }
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '2px solid var(--gd)', borderBottom: '1px dotted var(--gd)', padding: '7px 0', marginBottom: 10 }}>
        <span className="silk" style={{ fontSize: 13, color: 'var(--g)', letterSpacing: 1 }} dangerouslySetInnerHTML={{ __html: title }} />
        <span className="muted" style={{ fontSize: 11 }}>{items.length} ITEMS</span>
      </div>
      {note && <div className="muted" style={{ fontSize: 11, marginBottom: 10 }} dangerouslySetInnerHTML={{ __html: note }} />}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 12 }}>
        {items.length === 0 && <span className="muted" style={{ fontSize: 13 }}>&#183; none</span>}
        {items.map((name) => (
          <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ color: 'var(--g)' }}>&#9656;</span>
            {editing === name ? (
              <>
                <input className="box" style={{ flex: '1 1 200px' }} autoFocus value={editVal}
                  onChange={(e) => setEditVal(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') setEditing(null) }} />
                <button className="action commit" onClick={saveEdit}>SAVE</button>
                <button className="action" onClick={() => setEditing(null)}>CANCEL</button>
              </>
            ) : (
              <>
                <span style={{ fontSize: 16, color: 'var(--gb)' }}>{name}</span>
                <span style={{ flex: 1, minWidth: 14, height: 0, borderTop: '1px dotted var(--gd)', margin: '0 6px' }} />
                {onRename && <button className="action" onClick={() => startEdit(name)}>EDIT</button>}
                <button className="action" onClick={() => onDel(name)}>DEL</button>
              </>
            )}
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8, maxWidth: 420 }}>
        <input className="box" style={{ flex: 1 }} placeholder={placeholder}
          value={draft} onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit() }} />
        <button className="action commit" onClick={submit}>ADD</button>
      </div>
    </div>
  )
}
