# GroqDoc — Local Document Q&A with RAG

## Project overview
CLI tool that lets users ask natural language questions over a folder of local documents
(PDF, DOCX, Markdown) and get cited answers. Uses RAG: embed docs locally, retrieve
relevant chunks, answer via Groq API.

## Stack
- Python 3.11+
- Groq SDK (`groq`) — LLM inference (llama-3-70b-8192)
- ChromaDB (`chromadb`) — local vector store, no server needed
- sentence-transformers (`sentence-transformers`) — local embeddings (all-MiniLM-L6-v2)
- pypdf + python-docx — document parsing
- SQLite (stdlib) — metadata store (filename, page, chunk index)
- Rich (`rich`) — CLI output formatting

## Project structure
```
groqdoc/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example           # GROQ_API_KEY=
├── groqdoc/
│   ├── __init__.py
│   ├── ingest.py          # chunk + embed + store pipeline
│   ├── retriever.py       # cosine search + cross-encoder rerank
│   ├── prompt.py          # system prompt builder + citation formatter
│   ├── query.py           # CLI entrypoint
│   └── utils.py           # shared helpers (chunking, file parsing)
├── docs/                  # drop documents here to ingest
├── data/                  # gitignored — ChromaDB + SQLite live here
└── tests/
    ├── test_ingest.py
    └── test_retriever.py
```

## Commands
```bash
# Install
pip install -r requirements.txt

# Ingest a folder of documents
python -m groqdoc.ingest ./docs

# Ask a question
python -m groqdoc.query "How does our retry logic work?"

# Re-ingest (clears and rebuilds)
python -m groqdoc.ingest ./docs --reset
```

## Architecture rules — follow these exactly

### Chunking
- Chunk size: 512 tokens, overlap: 50 tokens
- Use `tiktoken` (cl100k_base) to count tokens, not characters
- Split on paragraph boundaries first, then fall back to token window
- Each chunk stores: `{text, source_file, page_num, chunk_index, char_start}`

### Embeddings
- Model: `sentence-transformers/all-MiniLM-L6-v2` — load once, reuse
- Embed at ingest time; never re-embed at query time unless `--reset`
- Store vectors in ChromaDB collection named `groqdoc`

### Retrieval
- Retrieve top-8 by cosine similarity, then rerank to top-5 with
  `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Return chunks with their metadata for citation

### Groq LLM call
- Model: `llama-3-70b-8192`
- Max tokens: 1024
- System prompt must include the retrieved chunks and instruct the model to:
  1. Answer only from the provided context
  2. Cite sources as [filename, chunk N]
  3. If context only partially answers, say so explicitly — never hallucinate the gap
- If no chunk scores above cosine similarity 0.35, skip LLM and return
  "No relevant documents found" directly

### Partial answer handling
- After LLM responds, check if any citation tags appear in the output
- If answer contains no citations, append a warning: "⚠ Answer may not be grounded
  in your documents. Here are the closest chunks found:" and show raw chunks

### Error handling
- Missing GROQ_API_KEY → clear error message pointing to .env.example
- Unsupported file type → warn and skip, don't crash
- ChromaDB collection missing → auto-run ingest, then query

## Code style
- Type hints on all function signatures
- Docstrings on public functions (one-line is fine)
- No global state — pass dependencies explicitly
- Keep ingest.py and query.py thin; logic lives in retriever.py / utils.py
- Use `rich.console.Console` for all terminal output, not bare `print()`

## What NOT to build (keep it simple)
- No web UI, no API server, no streaming output (v1 is CLI only)
- No authentication
- No async — synchronous is fine for a CLI tool
- No Docker

## Files to create first (in this order)
1. `requirements.txt`
2. `.env.example`
3. `groqdoc/utils.py` — file parsing + chunking
4. `groqdoc/ingest.py` — ingestion pipeline
5. `groqdoc/retriever.py` — search + rerank
6. `groqdoc/prompt.py` — system prompt + citation logic
7. `groqdoc/query.py` — CLI entrypoint
8. `README.md` — setup instructions
9. `tests/test_ingest.py` + `tests/test_retriever.py`
