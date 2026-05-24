# GroqDoc

A local document Q&A system powered by RAG (Retrieval-Augmented Generation). Upload PDFs, DOCX, or Markdown files, index them locally, and ask natural language questions — answers are cited back to your documents.

Built with a FastAPI backend, React + Tailwind frontend, ChromaDB vector store, and Groq's `llama-3.3-70b-versatile` for inference.

---

## Features

- **Ask questions** over your documents with cited, grounded answers
- **Summarize** any document in one click
- **Upload & delete** documents directly from the UI
- **Local embeddings** — no document content leaves your machine during indexing
- **Cross-encoder reranking** for higher quality retrieval
- **Citation warnings** when the LLM answer isn't grounded in your documents

---

## How it works

```
Upload docs → Chunk + Embed (local) → Store in ChromaDB
                                              ↓
Ask question → Embed query → Top-8 cosine search → Rerank to top-5
                                              ↓
                              Build prompt with chunks → Groq LLM → Cited answer
```

1. **Ingest** — documents are split into 512-token chunks (50-token overlap), embedded with `all-MiniLM-L6-v2`, and stored in a local ChromaDB vector store alongside a SQLite metadata index.
2. **Retrieve** — at query time, the top-8 chunks are fetched by cosine similarity, then reranked to top-5 with `cross-encoder/ms-marco-MiniLM-L-6-v2`.
3. **Answer** — retrieved chunks are passed to `llama-3.3-70b-versatile` via Groq. The model answers only from the provided context and cites every claim as `[filename, chunk N]`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM inference | Groq API (`llama-3.3-70b-versatile`) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local) |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` (local) |
| Vector store | ChromaDB (persistent, no server needed) |
| Metadata store | SQLite (stdlib) |
| Backend API | FastAPI + Uvicorn |
| Frontend | React 18 + Vite + Tailwind CSS |
| Document parsing | pypdf, python-docx |
| Tokenisation | tiktoken (cl100k_base) |

---

## Project Structure

```
RAG v2/
├── groqdoc/
│   ├── api.py          # FastAPI backend (REST API)
│   ├── ingest.py       # Chunking + embedding pipeline
│   ├── retriever.py    # Cosine search + cross-encoder rerank
│   ├── prompt.py       # System prompt builder + citation logic
│   ├── query.py        # CLI entrypoint
│   └── utils.py        # File parsing + token-aware chunking
├── ui/
│   ├── src/
│   │   ├── App.jsx             # Root component + state
│   │   ├── components/
│   │   │   ├── Sidebar.jsx     # Document list, upload, index, delete
│   │   │   ├── ChatMessage.jsx # Message bubbles + expandable sources
│   │   │   └── ChatInput.jsx   # Auto-resizing textarea
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
├── docs/               # Drop your documents here
├── data/               # Auto-created — ChromaDB + SQLite (gitignored)
├── tests/
│   ├── test_ingest.py
│   └── test_retriever.py
├── requirements.txt
└── .env.example
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A free [Groq API key](https://console.groq.com)

### 1. Clone and install Python dependencies

```bash
cd "RAG v2"

# Create a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 2. Configure your Groq API key

```bash
cp .env.example .env
```

Open `.env` and set:

```
GROQ_API_KEY=gsk_your_key_here
```

### 3. Install frontend dependencies

```bash
cd ui
npm install
cd ..
```

---

## Running the App

Open **two terminals** from the project root:

**Terminal 1 — Backend API:**
```bash
.venv/bin/uvicorn groqdoc.api:app --port 8001
```

**Terminal 2 — Frontend:**
```bash
cd ui
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Using the Web UI

1. **Upload a document** — click *Upload Document* in the sidebar and pick a PDF, DOCX, or Markdown file.
2. **Index documents** — click *Index Documents* to embed and store all files in the sidebar. Wait for the confirmation message in the chat.
3. **Ask a question** — type in the chat input and press Enter. The answer appears with expandable source citations.
4. **Summarize a document** — hover over a document name in the sidebar and click the lines icon (≡) that appears.
5. **Delete a document** — hover over a document name and click the red trash icon. This removes the file and purges its chunks from the index.

---

## CLI Usage (optional)

You can also use the tool from the terminal without the web UI:

```bash
# Ingest a folder of documents
python -m groqdoc.ingest ./docs

# Re-ingest from scratch (clears existing data)
python -m groqdoc.ingest ./docs --reset

# Ask a question
python -m groqdoc.query "What is supervised learning?"
python -m groqdoc.query "Summarise the key findings"
```

---

## API Reference

The backend runs on `http://localhost:8001`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/status` | Index readiness and chunk count |
| `GET` | `/documents` | List documents in `docs/` |
| `POST` | `/upload` | Upload a document file |
| `DELETE` | `/documents/{filename}` | Delete a document and its index chunks |
| `POST` | `/ingest?reset=false` | Trigger indexing of all documents |
| `POST` | `/query` | Ask a question (`{"question": "..."}`) |
| `POST` | `/summarize` | Summarize a document (`{"source_file": "..."}`) |

---

## Running Tests

```bash
source .venv/bin/activate
pip install pytest
pytest tests/ -v
```

---

## Supported File Types

| Format | Extension |
|---|---|
| PDF | `.pdf` |
| Word Document | `.docx` |
| Markdown | `.md`, `.markdown` |

---

## Notes

- All embeddings are computed locally — document content is never sent to any external service during indexing.
- Only the top-5 retrieved chunks (not full documents) are sent to Groq at query time.
- If the LLM answer contains no citation tags, a warning is shown in the UI alongside the raw source chunks.
- The `data/` directory (ChromaDB + SQLite) is auto-created and should be added to `.gitignore`.
