import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

function SourceCard({ chunk }) {
  const [open, setOpen] = useState(false)
  const pct = Math.round(chunk.score * 100)

  return (
    <div className="rounded-xl border border-slate-700/60 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2.5 px-3 py-2 bg-slate-800/50 hover:bg-slate-800/80 transition-colors text-left"
      >
        <svg className="w-3.5 h-3.5 text-slate-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <span className="flex-1 text-xs text-slate-400 truncate">
          {chunk.source_file}
          <span className="text-slate-600 ml-1">· chunk {chunk.chunk_index} · p.{chunk.page_num}</span>
        </span>
        <span className={`text-xs tabular-nums shrink-0 ${pct >= 70 ? 'text-emerald-400' : pct >= 50 ? 'text-amber-400' : 'text-slate-500'}`}>
          {pct}%
        </span>
        <svg
          className={`w-3.5 h-3.5 text-slate-600 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-3 py-2.5 bg-slate-900/60 border-t border-slate-700/40">
          <p className="text-xs text-slate-400 leading-relaxed">
            {chunk.text.length > 500 ? chunk.text.slice(0, 500) + '…' : chunk.text}
          </p>
        </div>
      )}
    </div>
  )
}

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end message-enter">
        <div className="max-w-[78%] px-4 py-3 rounded-2xl rounded-tr-sm bg-violet-600 text-white text-sm leading-relaxed shadow-sm shadow-violet-900/30">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 message-enter">
      <div className="w-8 h-8 rounded-full bg-violet-600/15 border border-violet-500/25 flex items-center justify-center shrink-0 mt-0.5">
        <span className="text-violet-400 text-xs font-semibold">G</span>
      </div>

      <div className="flex-1 min-w-0 space-y-2.5">
        {/* Answer */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3.5 text-sm leading-relaxed prose max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Warning */}
        {message.warning && (
          <div className="flex items-start gap-2.5 px-3.5 py-2.5 rounded-xl bg-amber-900/20 border border-amber-700/30 text-xs text-amber-300">
            <svg className="w-3.5 h-3.5 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>{message.warning}</span>
          </div>
        )}

        {/* Sources */}
        {message.chunks?.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs text-slate-600 px-0.5">Sources used</p>
            {message.chunks.map((chunk, i) => (
              <SourceCard key={i} chunk={chunk} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
