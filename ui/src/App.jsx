import { useState, useEffect, useRef } from 'react'
import Sidebar from './components/Sidebar'
import ChatMessage from './components/ChatMessage'
import ChatInput from './components/ChatInput'

const API = 'http://localhost:8001'

const WELCOME = {
  role: 'assistant',
  content: "Hi! I'm **GroqDoc**. Upload your documents, index them, then ask me anything — I'll answer with citations from your files.",
  chunks: [],
  warning: null,
}

export default function App() {
  const [messages, setMessages] = useState([WELCOME])
  const [documents, setDocuments] = useState([])
  const [status, setStatus] = useState({ ready: false, chunk_count: 0 })
  const [loading, setLoading] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    fetchStatus()
    fetchDocuments()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function fetchStatus() {
    try {
      const res = await fetch(`${API}/status`)
      setStatus(await res.json())
    } catch {
      setStatus({ ready: false, chunk_count: 0 })
    }
  }

  async function fetchDocuments() {
    try {
      const res = await fetch(`${API}/documents`)
      const data = await res.json()
      setDocuments(data.documents || [])
    } catch {}
  }

  async function handleQuery(question) {
    if (!question.trim() || loading) return
    setError(null)
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)
    try {
      const res = await fetch(`${API}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Query failed')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        chunks: data.chunks || [],
        warning: data.warning || null,
      }])
    } catch (err) {
      setError(err.message)
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }

  async function handleIngest(reset = false) {
    setIngesting(true)
    setError(null)
    try {
      const res = await fetch(`${API}/ingest?reset=${reset}`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Ingest failed')
      await fetchStatus()
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Documents indexed successfully. I've processed **${documents.length}** file${documents.length !== 1 ? 's' : ''}. Ask me anything!`,
        chunks: [],
        warning: null,
      }])
    } catch (err) {
      setError(err.message)
    } finally {
      setIngesting(false)
    }
  }

  async function handleSummarize(sourceFile) {
    setError(null)
    setMessages(prev => [...prev, { role: 'user', content: `Summarize: ${sourceFile}` }])
    setLoading(true)
    try {
      const res = await fetch(`${API}/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_file: sourceFile }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Summarization failed')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        chunks: data.chunks || [],
        warning: data.warning || null,
      }])
    } catch (err) {
      setError(err.message)
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(filename) {
    if (!window.confirm(`Remove "${filename}" and its index chunks?`)) return
    setError(null)
    try {
      const res = await fetch(`${API}/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Delete failed')
      await Promise.all([fetchDocuments(), fetchStatus()])
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleUpload(file) {
    setUploading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API}/upload`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      await fetchDocuments()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      <Sidebar
        documents={documents}
        status={status}
        ingesting={ingesting}
        uploading={uploading}
        onIngest={handleIngest}
        onUpload={handleUpload}
        onSummarize={handleSummarize}
        onDelete={handleDelete}
      />

      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-3.5 border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow shadow-violet-900/40">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h1 className="font-semibold text-sm text-slate-100 leading-none">GroqDoc</h1>
              <p className="text-xs text-slate-500 mt-0.5">
                {status.ready
                  ? `${status.chunk_count.toLocaleString()} chunks indexed`
                  : 'No index — upload & index docs first'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-600">{status.ready ? 'Ready' : 'Not ready'}</span>
            <div className={`h-2 w-2 rounded-full transition-colors ${status.ready ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-slate-600'}`} />
          </div>
        </header>

        {/* Error banner */}
        {error && (
          <div className="mx-4 mt-3 flex items-start gap-2.5 px-4 py-3 rounded-xl bg-red-900/20 border border-red-700/40 text-sm text-red-400">
            <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-red-600 hover:text-red-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg, i) => (
              <ChatMessage key={i} message={msg} />
            ))}

            {/* Typing indicator */}
            {loading && (
              <div className="flex items-start gap-3 message-enter">
                <div className="w-8 h-8 rounded-full bg-violet-600/15 border border-violet-500/25 flex items-center justify-center shrink-0">
                  <span className="text-violet-400 text-xs font-semibold">G</span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3.5 flex items-center gap-1.5">
                  <span className="typing-dot w-1.5 h-1.5 rounded-full bg-violet-400" />
                  <span className="typing-dot w-1.5 h-1.5 rounded-full bg-violet-400" />
                  <span className="typing-dot w-1.5 h-1.5 rounded-full bg-violet-400" />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        <ChatInput onSubmit={handleQuery} disabled={loading || !status.ready} />
      </div>
    </div>
  )
}
