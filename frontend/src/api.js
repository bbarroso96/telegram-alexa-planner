// ⚠️ DEMO MOCK — this file only exists on the `demo` branch.
// It replaces the real REST client with an in-memory store of dummy data so the
// app runs fully static (no backend, no network). Mutations update local state
// and reset on refresh. The real api.js lives on `main` and is untouched.

const pad = (n) => String(n).padStart(2, '0')
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const offset = (days) => { const d = new Date(); d.setDate(d.getDate() + days); return iso(d) }
const today = iso(new Date())
const stamp = () => { const d = new Date(); return `${iso(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}` }

// auto-increment id pools (start high so they never collide with seed data)
let _id = 1000
const nextId = () => ++_id

// ---- seed state (raw, backend-shaped) ----
let cats = ['Work', 'Personal', 'Home', 'Errands', 'Finance']
let types = [{ name: 'Major', kind: 'major' }, { name: 'Day2Day', kind: 'd2d' }]

let tasks = [
  { id: 1, title: 'Launch portfolio site', type: 'major', category: 'Work', done: false,
    date: '', blocked_by: [2], created_at: today,
    subs: [
      { id: 11, title: 'Finalize design', done: true, updates: [] },
      { id: 12, title: 'Build the pages', done: false,
        updates: [{ id: 121, ts: `${today} 09:14`, text: 'hero section done, working on the about page' }] },
      { id: 13, title: 'Deploy to hosting', done: false, updates: [] },
    ],
    updates: [{ id: 101, ts: `${today} 11:02`, text: 'waiting on the final logo from the designer' }] },
  { id: 2, title: 'Plan Q3 roadmap', type: 'major', category: 'Work', done: false,
    date: offset(5), blocked_by: [], created_at: today, subs: [],
    updates: [{ id: 102, ts: `${today} 08:30`, text: 'draft shared with the team for feedback' }] },
  { id: 3, title: 'File quarterly taxes', type: 'major', category: 'Finance', done: false,
    date: offset(10), blocked_by: [], created_at: today, subs: [], updates: [] },
  { id: 4, title: 'Buy groceries', type: 'd2d', category: 'Errands', done: false,
    date: '', blocked_by: [], created_at: today,
    subs: [
      { id: 41, title: 'Milk', done: false, updates: [] },
      { id: 42, title: 'Eggs', done: false, updates: [] },
      { id: 43, title: 'Coffee beans', done: true, updates: [] },
    ], updates: [] },
  { id: 5, title: 'Reply to emails', type: 'd2d', category: 'Work', done: true,
    date: '', blocked_by: [], created_at: today, subs: [], updates: [] },
  { id: 6, title: 'Water the plants', type: 'd2d', category: 'Home', done: false,
    date: '', blocked_by: [], created_at: today, subs: [], updates: [] },
  { id: 7, title: 'Call the bank', type: 'd2d', category: 'Finance', done: false,
    date: '', blocked_by: [3], created_at: today, subs: [], updates: [] },
  { id: 8, title: 'Renew gym membership', type: 'd2d', category: 'Personal', done: false,
    date: '', blocked_by: [], created_at: today, subs: [], updates: [] },
]

let events = [
  { id: 51, title: 'Team offsite', single: false, start: offset(3), end: offset(5),
    comments: [{ id: 511, ts: `${today} 10:00`, text: 'book train tickets and hotel' }] },
  { id: 52, title: 'Dentist appointment', single: true, start: offset(2), end: offset(2), comments: [] },
  { id: 53, title: "Mom's birthday", single: true, start: offset(8), end: offset(8),
    comments: [{ id: 531, ts: `${today} 09:00`, text: 'order flowers' }] },
]

// ---- helpers ----
const resolve = (v) => Promise.resolve(v)
const findTask = (id) => tasks.find((t) => t.id === Number(id))
const findSub = (id) => { for (const t of tasks) { const s = t.subs.find((x) => x.id === Number(id)); if (s) return [t, s] } return [null, null] }

function serializeTask(t) {
  const doneIds = new Set(tasks.filter((x) => x.done).map((x) => x.id))
  const active = (t.blocked_by || []).filter((b) => !doneIds.has(b))
  const titleOf = (id) => (tasks.find((x) => x.id === id) || {}).title || `#${id}`
  return {
    id: t.id, title: t.title, type: t.type, category: t.category, done: t.done,
    dateKind: t.date ? 'begin' : 'open', beginDate: t.date || null, openDate: t.created_at,
    blocked: active.length > 0, blocked_by: t.blocked_by || [], waiting_on: active.map(titleOf),
    updates: t.updates.map((u) => ({ ...u })),
    subs: t.subs.map((s) => ({ id: s.id, title: s.title, done: s.done, updates: s.updates.map((u) => ({ ...u })) })),
  }
}

const parseIds = (raw) => String(raw || '').split(',').map((x) => x.trim()).filter(Boolean).map(Number)

export const api = {
  // reads
  tasks: () => resolve(tasks.map(serializeTask)),
  events: () => resolve(events.map((e) => ({ ...e, comments: e.comments.map((c) => ({ ...c })) }))),
  categories: () => resolve([...cats]),
  types: () => resolve(types.map((t) => ({ ...t }))),

  // tasks
  addTask: (t) => { tasks.push({ id: nextId(), title: t.title, type: t.type || 'd2d', category: t.category || '', done: false, date: t.date || '', blocked_by: [], created_at: today, subs: [], updates: [] }); return resolve({ id: _id }) },
  editTask: (id, patch) => { const t = findTask(id); if (t) { if (patch.title != null) t.title = patch.title; if (patch.category != null) t.category = patch.category; if (patch.type != null) t.type = patch.type; if (patch.date != null) t.date = patch.date; if (patch.blocked_by != null) t.blocked_by = parseIds(patch.blocked_by) } return resolve({ ok: true }) },
  setDone: (id, done) => { const t = findTask(id); if (t) t.done = done; return resolve({ ok: true }) },
  delTask: (id) => { tasks = tasks.filter((t) => t.id !== Number(id)); return resolve({ ok: true }) },
  logTask: (id, text) => { const t = findTask(id); if (t) t.updates.push({ id: nextId(), ts: stamp(), text }); return resolve({ ok: true }) },

  // subtasks
  addSub: (taskId, title) => { const t = findTask(taskId); if (t) t.subs.push({ id: nextId(), title, done: false, updates: [] }); return resolve({ ok: true }) },
  setSubDone: (id, done) => { const [, s] = findSub(id); if (s) s.done = done; return resolve({ ok: true }) },
  delSub: (id) => { const [t, s] = findSub(id); if (t) t.subs = t.subs.filter((x) => x !== s); return resolve({ ok: true }) },
  logSub: (id, text) => { const [, s] = findSub(id); if (s) s.updates.push({ id: nextId(), ts: stamp(), text }); return resolve({ ok: true }) },

  // events
  addEvent: (e) => { const single = !!e.single; let start = e.start, end = single ? e.start : (e.end || e.start); if (!single && end < start) { [start, end] = [end, start] } const ev = { id: nextId(), title: e.title, single, start, end, comments: [] }; if (e.comment && e.comment.trim()) ev.comments.push({ id: nextId(), ts: stamp(), text: e.comment.trim() }); events.push(ev); return resolve({ id: ev.id }) },
  editEvent: (id, patch) => { const ev = events.find((x) => x.id === Number(id)); if (ev) { if (patch.title != null) ev.title = patch.title; if (patch.single != null) ev.single = patch.single; if (patch.start != null) ev.start = patch.start; if (patch.end != null) ev.end = patch.end; if (ev.single) ev.end = ev.start; else if (ev.end < ev.start) { const s = ev.start; ev.start = ev.end; ev.end = s } } return resolve({ ok: true }) },
  delEvent: (id) => { events = events.filter((e) => e.id !== Number(id)); return resolve({ ok: true }) },
  commentEvent: (id, text) => { const ev = events.find((x) => x.id === Number(id)); if (ev) ev.comments.push({ id: nextId(), ts: stamp(), text }); return resolve({ ok: true }) },

  // config — categories & types
  addCategory: (name) => { if (name && !cats.includes(name)) cats.push(name); return resolve({ ok: true }) },
  renameCategory: (oldName, newName) => { const i = cats.indexOf(oldName); if (i >= 0 && newName) { cats[i] = newName; tasks.forEach((t) => { if (t.category === oldName) t.category = newName }) } return resolve({ ok: true }) },
  delCategory: (name) => { cats = cats.filter((c) => c !== name); return resolve({ ok: true }) },
  addType: (name) => { if (name && !types.some((t) => t.name === name)) types.push({ name, kind: 'd2d' }); return resolve({ ok: true }) },
  renameType: (oldName, newName) => { const t = types.find((x) => x.name === oldName); if (t && newName) t.name = newName; return resolve({ ok: true }) },
  delType: (name) => { types = types.filter((t) => t.name !== name); return resolve({ ok: true }) },
}
