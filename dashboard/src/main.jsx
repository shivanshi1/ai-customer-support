import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'
const demoCustomer = 'C001'

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || `Request failed (${response.status})`)
  return response.json()
}

function Badge({ children, tone = '' }) { return <span className={`badge ${tone}`}>{children}</span> }

function ChatView({ onDecision }) {
  const [message, setMessage] = useState('')
  const [conversationId, setConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const send = async (event) => {
    event.preventDefault(); if (!message.trim() || busy) return
    const text = message.trim(); setMessage(''); setBusy(true); setError('')
    setMessages((items) => [...items, { sender: 'customer', content: text }])
    try {
      const result = await request('/chat', { method: 'POST', body: JSON.stringify({ customer_id: demoCustomer, message: text, conversation_id: conversationId }) })
      setConversationId(result.conversation_id); setMessages((items) => [...items, { sender: 'assistant', content: result.response }]); onDecision(result)
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <section className="panel chat-panel"><div className="panel-heading"><div><p className="eyebrow">Live conversation</p><h2>Customer chat</h2></div><Badge tone="green">Demo customer · {demoCustomer}</Badge></div>
    <div className="messages">{messages.length === 0 && <div className="empty">Ask about shipping, returns, warranty, or an order.</div>}{messages.map((item, index) => <div className={`bubble ${item.sender}`} key={index}><small>{item.sender === 'customer' ? 'Customer' : 'AI support'}</small><p>{item.content}</p></div>)}</div>
    {error && <p className="error">{error}</p>}<form className="composer" onSubmit={send}><input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Type a support question…" /><button disabled={busy}>{busy ? 'Thinking…' : 'Send'}</button></form>
  </section>
}

function DecisionCard({ decision }) {
  if (!decision) return <section className="panel decision"><p className="eyebrow">Agent review</p><h2>Decision details</h2><div className="empty">Send a message to inspect classification, safety, and retrieved sources.</div></section>
  return <section className="panel decision"><div className="panel-heading"><div><p className="eyebrow">Agent review</p><h2>Decision details</h2></div><Badge tone={decision.escalated ? 'red' : 'green'}>{decision.escalated ? 'Human review' : 'Automated'}</Badge></div><div className="decision-grid"><div><span>Intent</span><strong>{decision.intent.replaceAll('_', ' ')}</strong></div><div><span>Priority</span><strong>{decision.priority}</strong></div><div><span>Sentiment</span><strong>{decision.sentiment}</strong></div><div><span>Confidence</span><strong>{Math.round(decision.confidence * 100)}%</strong></div></div>{decision.escalation_reasons?.length > 0 && <div className="callout red"><strong>Escalation reasons</strong><p>{decision.escalation_reasons.join(' · ')}</p></div>}<div className="callout"><strong>Suggested action</strong><p>{decision.suggested_action.replaceAll('_', ' ')}</p></div><div><span className="section-label">Retrieved sources</span>{decision.sources?.length ? decision.sources.map((source) => <div className="source" key={source.source}><strong>{source.title}</strong><small>{source.source}</small><p>{source.excerpt}</p></div>) : <div className="empty compact">No source evidence was retrieved.</div>}</div></section>
}

function HistoryView() {
  const [items, setItems] = useState([]); const [selected, setSelected] = useState(null)
  useEffect(() => { request(`/conversations?customer_id=${demoCustomer}`).then(setItems).catch(() => {}) }, [])
  const open = async (id) => setSelected(await request(`/conversations/${id}?customer_id=${demoCustomer}`))
  return <section className="panel history"><div className="panel-heading"><div><p className="eyebrow">Continuity</p><h2>Conversation history</h2></div><span className="muted">{items.length} threads</span></div>{items.length === 0 ? <div className="empty">Completed chats will appear here.</div> : <div className="history-layout"><div>{items.map((item) => <button className={`history-item ${selected?.id === item.id ? 'active' : ''}`} onClick={() => open(item.id)} key={item.id}><strong>{item.subject || 'Support conversation'}</strong><small>{new Date(item.updated_at).toLocaleString()}</small></button>)}</div><div className="transcript">{selected ? selected.messages.map((item) => <div className={`transcript-row ${item.sender}`} key={item.id}><small>{item.sender}</small><p>{item.content}</p></div>) : <div className="empty">Select a thread to review its transcript.</div>}</div></div>}</section>
}

function QueueView() {
  const [tickets, setTickets] = useState([])
  const [drafts, setDrafts] = useState({})
  const load = () => request('/dashboard/tickets').then(setTickets).catch(() => {})
  useEffect(load, [])
  const update = async (ticket, status) => { const draft = drafts[ticket.id] || {}; await request(`/dashboard/tickets/${ticket.id}`, { method: 'PATCH', body: JSON.stringify({ status, assignee: draft.assignee || ticket.assignee, note: draft.note || null }) }); load() }
  return <section className="panel queue"><div className="panel-heading"><div><p className="eyebrow">Human oversight</p><h2>Review queue</h2></div><Badge tone="amber">{tickets.filter((item) => item.status !== 'resolved').length} open</Badge></div>{tickets.length === 0 ? <div className="empty">No tickets need review.</div> : tickets.map((ticket) => { const draft = drafts[ticket.id] || {}; return <div className="ticket" key={ticket.id}><div><Badge tone={ticket.priority === 'urgent' ? 'red' : 'amber'}>{ticket.priority}</Badge><strong>{ticket.summary}</strong><small>{new Date(ticket.created_at).toLocaleString()} · {ticket.assignee || 'Unassigned'}</small>{ticket.status !== 'resolved' && <><input className="queue-input" placeholder="Assign to…" value={draft.assignee || ''} onChange={(event) => setDrafts({ ...drafts, [ticket.id]: { ...draft, assignee: event.target.value } })} /><textarea className="queue-input" placeholder="Add a human note or suggested response…" value={draft.note || ''} onChange={(event) => setDrafts({ ...drafts, [ticket.id]: { ...draft, note: event.target.value } })} /></>}</div>{ticket.status !== 'resolved' && <div className="ticket-actions"><button className="secondary" onClick={() => update(ticket, 'pending')}>Save note</button><button onClick={() => update(ticket, 'resolved')}>Resolve</button></div>}</div> })}</section>
}

function AnalyticsView() {
  const [metrics, setMetrics] = useState(null)
  useEffect(() => { request('/dashboard/metrics').then(setMetrics).catch(() => {}) }, [])
  if (!metrics) return <section className="panel"><div className="empty">Loading analytics…</div></section>
  return <section className="panel analytics"><div className="panel-heading"><div><p className="eyebrow">Operations</p><h2>Analytics</h2></div><span className="muted">Live from support events</span></div><div className="metric-grid">{[['Conversations', metrics.conversations], ['Messages', metrics.messages], ['Open tickets', metrics.open_tickets], ['Automation rate', `${Math.round(metrics.automation_rate * 100)}%`]].map(([label, value]) => <div className="metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div><div className="intent-list"><h3>Top intents</h3>{Object.entries(metrics.top_intents).map(([intent, count]) => <div key={intent}><span>{intent.replaceAll('_', ' ')}</span><b>{count}</b></div>)}</div></section>
}

function App() {
  const [tab, setTab] = useState('workspace'); const [decision, setDecision] = useState(null)
  return <div className="app-shell"><aside><div className="brand"><div className="brand-mark">✦</div><div><strong>Northstar</strong><span>support operations</span></div></div><nav>{[['workspace', '◌', 'Workspace'], ['queue', '⊙', 'Review queue'], ['analytics', '▥', 'Analytics']].map(([id, icon, label]) => <button className={tab === id ? 'selected' : ''} onClick={() => setTab(id)} key={id}><i>{icon}</i>{label}</button>)}</nav><div className="side-note"><span className="status-dot" /> API connected<div className="muted">Local demo environment</div></div></aside><main><header><div><p className="eyebrow">AI customer support</p><h1>{tab === 'workspace' ? 'Support workspace' : tab === 'queue' ? 'Human review queue' : 'Support analytics'}</h1></div><div className="header-meta"><span className="status-dot" /> System healthy</div></header>{tab === 'workspace' && <><div className="workspace-grid"><ChatView onDecision={setDecision} /><DecisionCard decision={decision} /></div><HistoryView /></>}{tab === 'queue' && <QueueView />}{tab === 'analytics' && <AnalyticsView />}</main></div>
}

createRoot(document.getElementById('root')).render(<App />)
