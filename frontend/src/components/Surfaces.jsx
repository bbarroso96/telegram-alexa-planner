// DEMO-only (demo branch): showcases the Telegram bot and Alexa skill surfaces
// with faithful, static mockups so recruiters see the full multi-surface story.
import React from 'react'

const SANS = 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif'
const MONO = "'Share Tech Mono', ui-monospace, monospace"

// ── section header in the app's CRT band style ───────────────────────────────
function Band({ label, tag }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      borderTop: '2px solid var(--gd)', borderBottom: '1px dotted var(--gd)', padding: '7px 0', marginBottom: 14 }}>
      <span className="silk" style={{ fontSize: 13, color: 'var(--g)', letterSpacing: 1 }}
        dangerouslySetInnerHTML={{ __html: label }} />
      <span className="muted" style={{ fontSize: 11, letterSpacing: 2 }}>{tag}</span>
    </div>
  )
}

// ── Telegram ─────────────────────────────────────────────────────────────────
const TG = { bg: '#0e1621', head: '#17212b', inc: '#182533', out: '#2b5278', dim: 'rgba(255,255,255,0.5)', btn: '#15212e', link: '#62a9e0' }

function Msg({ side, time, children }) {
  const out = side === 'out'
  return (
    <div style={{ display: 'flex', justifyContent: out ? 'flex-end' : 'flex-start', marginBottom: 6 }}>
      <div style={{ maxWidth: '80%', background: out ? TG.out : TG.inc, color: '#fff', borderRadius: 12,
        padding: '7px 11px', fontSize: 14, lineHeight: 1.45, whiteSpace: 'pre-wrap', fontFamily: SANS }}>
        {children}
        {time && <span style={{ display: 'block', textAlign: 'right', fontSize: 11, color: TG.dim, marginTop: 2 }}>{time}</span>}
      </div>
    </div>
  )
}

function Keys({ rows }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, margin: '0 0 8px', maxWidth: '80%' }}>
      {rows.map((row, i) => (
        <div key={i} style={{ display: 'flex', gap: 4 }}>
          {row.map((label, j) => (
            <div key={j} style={{ flex: 1, textAlign: 'center', background: TG.btn, color: TG.link,
              borderRadius: 8, padding: '9px 6px', fontSize: 13, fontFamily: SANS, border: '1px solid rgba(98,169,224,0.25)' }}>{label}</div>
          ))}
        </div>
      ))}
    </div>
  )
}

// Each chat is driven by a script: {side,time,text} bubbles or {keys:[[...]]} buttons.
const TASK_SCRIPT = [
  { side: 'out', time: '8:40', text: '/add' },
  { side: 'inc', text: "What's the task title?" },
  { side: 'out', text: 'Finish Q3 report' },
  { side: 'inc', text: 'Choose a category:' },
  { keys: [['Work', 'Personal'], ['Home', 'Finance']] },
  { side: 'inc', text: 'Choose a type:' },
  { keys: [['Major', 'Day2Day']] },
  { side: 'inc', text: 'When do you plan to start?' },
  { keys: [['Today', 'Tomorrow'], ['Enter a date'], ['No date (open task)']] },
  { side: 'inc', text: '✅ Task created!\n#9 Finish Q3 report\n🏷 Work · Major\n📅 open' },
]

const EVENT_SCRIPT = [
  { side: 'out', time: '9:01', text: '/today' },
  { side: 'inc', text: 'Today — Jun 22\n\n📅 Events\n◆ Dentist appointment · Jun 22' },
  { side: 'inc', text: '• Buy groceries   ·   Errands' },
  { keys: [['✅ Mark done']] },
  { side: 'inc', text: '• Water the plants   ·   Home' },
  { keys: [['✅ Mark done']] },
  { side: 'out', time: '9:03', text: '/addevent' },
  { side: 'inc', text: "What's the event?" },
  { side: 'out', text: 'Team lunch' },
  { side: 'inc', text: 'One day or a date range?' },
  { keys: [['1 day', 'Range']] },
  { side: 'inc', text: '✅ Event added!\n◆ Team lunch · Jun 22' },
]

function TelegramMock({ caption, script }) {
  return (
    <div style={{ width: 340, maxWidth: '100%' }}>
      <div style={{ background: TG.bg, borderRadius: 14, overflow: 'hidden', border: '1px solid #233140' }}>
        <div style={{ background: TG.head, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#2bff66', color: '#000',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontFamily: MONO }}>CR</div>
          <div style={{ fontFamily: SANS }}>
            <div style={{ color: '#fff', fontSize: 15, fontWeight: 600 }}>Captain Rocky</div>
            <div style={{ color: '#6d7f8f', fontSize: 12 }}>bot</div>
          </div>
        </div>
        <div style={{ padding: 12, height: 430, overflowY: 'auto' }}>
          {script.map((m, i) => m.keys
            ? <Keys key={i} rows={m.keys} />
            : <Msg key={i} side={m.side} time={m.time}>{m.text}</Msg>)}
        </div>
      </div>
      <div className="muted" style={{ textAlign: 'center', fontSize: 12, marginTop: 6 }}>{caption}</div>
    </div>
  )
}

// ── Alexa / Echo Show ────────────────────────────────────────────────────────
const SCREEN_ROWS = [
  { m: '▸', t: 'Launch portfolio site', c: 'Work' },
  { m: '!!', t: 'Call the bank', c: 'Finance' },
  { m: '▸', t: 'Buy groceries', c: 'Errands' },
  { m: '[x]', t: 'Reply to emails', c: 'Work', done: true },
  { m: '▸', t: 'Water the plants', c: 'Home' },
]

function EchoShow() {
  return (
    <div style={{ width: 420, maxWidth: '100%' }}>
      <div style={{ background: '#141414', border: '1px solid #2c2c2c', borderRadius: 16, padding: 14 }}>
        <div style={{ background: '#000', borderRadius: 6, padding: '14px 18px', fontFamily: MONO }}>
          <div style={{ color: '#2bff66', fontWeight: 700, fontSize: 18 }}>▌ ALL TASKS</div>
          <div style={{ height: 0, borderTop: '2px solid #2a8f44', margin: '8px 0' }} />
          {SCREEN_ROWS.map((r, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
              <span style={{ color: r.done ? '#2a8f44' : '#2bff66', width: 22 }}>{r.m}</span>
              <span style={{ flex: 1, color: r.done ? '#2a8f44' : '#7dffa0', fontSize: 17, textDecoration: r.done ? 'line-through' : 'none' }}>{r.t}</span>
              <span style={{ color: '#2a8f44', fontSize: 13 }}>{r.c}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="muted" style={{ textAlign: 'center', fontSize: 12, marginTop: 6 }}>Echo Show 5 · on-screen (APL)</div>
    </div>
  )
}

const TRANSCRIPT = [
  ['you', 'Alexa, ask Captain Rocky what\'s on my list'],
  ['rocky', 'You have 7 pending tasks: Launch portfolio site, Plan Q3 roadmap, File quarterly taxes, Buy groceries, and 3 more.'],
  ['you', 'What\'s coming up this week?'],
  ['rocky', 'Coming up this week you have 3 events: Dentist appointment, Team offsite, and Mom\'s birthday.'],
]

function VoiceTranscript() {
  return (
    <div style={{ flex: '1 1 280px', minWidth: 260, display: 'flex', flexDirection: 'column', gap: 10 }}>
      {TRANSCRIPT.map(([who, text], i) => (
        <div key={i}>
          <div className="muted" style={{ fontSize: 11, letterSpacing: 1, marginBottom: 2 }}>
            {who === 'you' ? '🎙 YOU' : '🔊 CAPTAIN ROCKY'}
          </div>
          <div style={{ background: who === 'you' ? 'rgba(255,255,255,0.04)' : 'rgba(43,255,102,0.06)',
            border: '1px solid var(--gd)', borderRadius: 10, padding: '9px 12px', color: 'var(--gb)', fontSize: 14, lineHeight: 1.4 }}>
            {text}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── page ─────────────────────────────────────────────────────────────────────
export default function Surfaces() {
  return (
    <div>
      <div className="muted" style={{ fontSize: 12, letterSpacing: 2, marginBottom: 16 }}>
        // THE SAME PLANNER, THREE WAYS — one SQLite brain, three front-ends
      </div>

      <Band label="&#9612; TELEGRAM BOT" tag="// CHAT" />
      <div className="muted" style={{ fontSize: 13, marginBottom: 12 }}>
        Add, complete, and schedule from anywhere via a conversational bot with inline buttons and a command menu.
      </div>
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 28 }}>
        <TelegramMock caption="Creating a task" script={TASK_SCRIPT} />
        <TelegramMock caption="Daily view &amp; events" script={EVENT_SCRIPT} />
      </div>

      <Band label="&#9612; ALEXA · CAPTAIN ROCKY" tag="// VOICE + SCREEN" />
      <div className="muted" style={{ fontSize: 13, marginBottom: 14 }}>
        Ask out loud on an Echo Show — it speaks the answer and renders the same directives on screen.
      </div>
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <EchoShow />
        <VoiceTranscript />
      </div>
    </div>
  )
}
