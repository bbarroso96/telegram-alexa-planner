// Thin wrapper over the planner REST API. Same-origin relative URLs; in dev
// Vite proxies /api to the FastAPI server on :8000.

async function req(method, url, body) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(url, opts)
  if (!res.ok) throw new Error(`${method} ${url} -> ${res.status}`)
  const ct = res.headers.get('content-type') || ''
  return ct.includes('application/json') ? res.json() : null
}

export const api = {
  // reads
  tasks: () => req('GET', '/api/tasks?include_done=true'),
  events: () => req('GET', '/api/events'),
  categories: () => req('GET', '/api/categories'),
  types: () => req('GET', '/api/types'),

  // tasks
  addTask: (t) => req('POST', '/api/tasks', t),
  editTask: (id, patch) => req('PATCH', `/api/tasks/${id}`, patch),
  setDone: (id, done) => req('POST', `/api/tasks/${id}/${done ? 'done' : 'reopen'}`),
  delTask: (id) => req('DELETE', `/api/tasks/${id}`),
  logTask: (id, text) => req('POST', `/api/tasks/${id}/updates`, { text }),

  // subtasks
  addSub: (taskId, title) => req('POST', `/api/tasks/${taskId}/subtasks`, { title }),
  setSubDone: (id, done) => req('POST', `/api/subtasks/${id}/${done ? 'done' : 'reopen'}`),
  delSub: (id) => req('DELETE', `/api/subtasks/${id}`),
  logSub: (id, text) => req('POST', `/api/subtasks/${id}/updates`, { text }),

  // events
  addEvent: (e) => req('POST', '/api/events', e),
  editEvent: (id, patch) => req('PATCH', `/api/events/${id}`, patch),
  delEvent: (id) => req('DELETE', `/api/events/${id}`),
  commentEvent: (id, text) => req('POST', `/api/events/${id}/comments`, { text }),

  // config — categories & types
  addCategory: (name) => req('POST', '/api/categories', { name }),
  renameCategory: (oldName, newName) => req('PUT', '/api/categories', { old: oldName, new: newName }),
  delCategory: (name) => req('DELETE', `/api/categories?name=${encodeURIComponent(name)}`),
  addType: (name) => req('POST', '/api/types', { name }),
  renameType: (oldName, newName) => req('PUT', '/api/types', { old: oldName, new: newName }),
  delType: (name) => req('DELETE', `/api/types?name=${encodeURIComponent(name)}`),
}
