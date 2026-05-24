import { useState, useRef } from 'react'

export default function ChatInput({ onSubmit, disabled }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  function submit() {
    const q = value.trim()
    if (!q || disabled) return
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    onSubmit(q)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function handleChange(e) {
    setValue(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
  }

  const canSend = !disabled && value.trim().length > 0

  return (
    <div className="px-4 py-4 border-t border-slate-800/80 bg-slate-900/30 backdrop-blur-md shrink-0">
      <div className="max-w-3xl mx-auto">
        <div className={`flex items-end gap-3 bg-slate-800/70 border rounded-2xl px-4 py-3 transition-all duration-150 ${
          disabled
            ? 'border-slate-700/40 opacity-60 cursor-not-allowed'
            : 'border-slate-600/50 hover:border-slate-500/60 focus-within:border-violet-500/50 focus-within:bg-slate-800/90'
        }`}>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={1}
            placeholder={disabled ? 'Index your documents to start chatting…' : 'Ask a question about your documents…'}
            className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-600 outline-none resize-none leading-relaxed max-h-36 disabled:cursor-not-allowed"
            style={{ height: 'auto' }}
          />
          <button
            onClick={submit}
            disabled={!canSend}
            className={`shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all mb-0.5 ${
              canSend
                ? 'bg-violet-600 hover:bg-violet-500 active:bg-violet-700 shadow-sm shadow-violet-900/40 cursor-pointer'
                : 'bg-slate-700 cursor-not-allowed'
            }`}
          >
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <p className="text-center text-xs text-slate-700 mt-2 select-none">
          Enter to send &nbsp;·&nbsp; Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
