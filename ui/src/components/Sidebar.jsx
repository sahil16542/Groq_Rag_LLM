import { useRef } from 'react'

const EXT_ICON = {
  pdf: (
    <svg className="w-3.5 h-3.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
  ),
  docx: (
    <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  md: (
    <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  ),
}

function fileIcon(name) {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return EXT_ICON[ext] || EXT_ICON.md
}

export default function Sidebar({ documents, status, ingesting, uploading, onIngest, onUpload, onSummarize, onDelete }) {
  const fileRef = useRef(null)

  function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (file) {
      onUpload(file)
      e.target.value = ''
    }
  }

  return (
    <aside className="w-64 shrink-0 bg-slate-900 border-r border-slate-800/80 flex flex-col">
      {/* Brand */}
      <div className="px-5 pt-5 pb-4 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-md shadow-violet-900/40 shrink-0">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-slate-100 text-sm leading-none">GroqDoc</p>
            <p className="text-xs text-slate-500 mt-1">Document Q&amp;A</p>
          </div>
        </div>
      </div>

      {/* Index status */}
      <div className="px-4 py-3 border-b border-slate-800/80">
        <div className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl ${status.ready ? 'bg-emerald-900/20 border border-emerald-700/30' : 'bg-slate-800/50 border border-slate-700/50'}`}>
          <div className={`h-2 w-2 rounded-full shrink-0 ${status.ready ? 'bg-emerald-400 shadow-sm shadow-emerald-400/60' : 'bg-slate-600'}`} />
          <div>
            <p className={`text-xs font-medium ${status.ready ? 'text-emerald-300' : 'text-slate-500'}`}>
              {status.ready ? 'Index ready' : 'Not indexed'}
            </p>
            {status.ready && (
              <p className="text-xs text-emerald-600">{status.chunk_count.toLocaleString()} chunks</p>
            )}
          </div>
        </div>
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        <div className="flex items-center justify-between px-2 mb-2">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Documents</p>
          <span className="text-xs text-slate-700 tabular-nums">{documents.length}</span>
        </div>

        {documents.length === 0 ? (
          <div className="px-2 py-10 text-center">
            <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto mb-3">
              <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </div>
            <p className="text-xs text-slate-600">No documents yet</p>
            <p className="text-xs text-slate-700 mt-0.5">Upload files below</p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {documents.map(doc => (
              <div
                key={doc}
                className="flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-slate-800/60 transition-colors group"
              >
                <span className="shrink-0">{fileIcon(doc)}</span>
                <p className="text-xs text-slate-400 truncate group-hover:text-slate-300 transition-colors leading-none flex-1 min-w-0">
                  {doc}
                </p>
                <div className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-0.5">
                  {status.ready && (
                    <button
                      onClick={() => onSummarize(doc)}
                      title="Summarize"
                      className="p-1 rounded-md hover:bg-violet-600/20 text-slate-600 hover:text-violet-400 transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
                      </svg>
                    </button>
                  )}
                  <button
                    onClick={() => onDelete(doc)}
                    title="Remove document"
                    className="p-1 rounded-md hover:bg-red-600/20 text-slate-600 hover:text-red-400 transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-3 py-4 border-t border-slate-800/80 space-y-2">
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.md,.markdown"
          className="hidden"
          onChange={handleFileChange}
        />

        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-xs font-medium text-slate-300 border border-slate-700 hover:border-slate-600 hover:bg-slate-800/60 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? (
            <svg className="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          )}
          {uploading ? 'Uploading...' : 'Upload Document'}
        </button>

        <button
          onClick={() => onIngest(false)}
          disabled={ingesting || documents.length === 0}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-xs font-medium text-white bg-violet-600 hover:bg-violet-500 active:bg-violet-700 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm shadow-violet-900/40"
        >
          <svg
            className={`w-3.5 h-3.5 ${ingesting ? 'animate-spin' : ''}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {ingesting ? 'Indexing...' : 'Index Documents'}
        </button>

        {status.ready && (
          <button
            onClick={() => onIngest(true)}
            disabled={ingesting}
            className="w-full text-xs text-slate-600 hover:text-slate-500 transition-colors py-1"
          >
            Re-index (clear &amp; rebuild)
          </button>
        )}
      </div>
    </aside>
  )
}
