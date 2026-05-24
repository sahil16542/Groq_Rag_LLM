"""FastAPI backend for the GroqDoc web UI."""

from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

import chromadb
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, CrossEncoder

from groqdoc.ingest import ingest_folder, CHROMA_COLLECTION, DB_PATH, SQLITE_DB, SUPPORTED_EXTENSIONS
from groqdoc.retriever import retrieve, load_models
from groqdoc.prompt import build_system_prompt, has_citations

DOCS_FOLDER = Path(__file__).parent.parent / "docs"
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024

app = FastAPI(title="GroqDoc API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_embed_model: Optional[SentenceTransformer] = None
_rerank_model: Optional[CrossEncoder] = None


def _get_models() -> tuple[SentenceTransformer, CrossEncoder]:
    global _embed_model, _rerank_model
    if _embed_model is None or _rerank_model is None:
        _embed_model, _rerank_model = load_models()
    return _embed_model, _rerank_model


class QueryRequest(BaseModel):
    question: str


class ChunkInfo(BaseModel):
    text: str
    source_file: str
    page_num: int
    chunk_index: int
    score: float


class QueryResponse(BaseModel):
    answer: str
    chunks: list[ChunkInfo]
    has_citations: bool
    warning: Optional[str] = None


@app.get("/status")
def status() -> dict:
    """Return whether the vector store is ready and how many chunks are indexed."""
    try:
        client = chromadb.PersistentClient(path=str(DB_PATH / "chroma"))
        col = client.get_collection(CHROMA_COLLECTION)
        return {"ready": True, "chunk_count": col.count()}
    except Exception:
        return {"ready": False, "chunk_count": 0}


@app.get("/documents")
def list_documents() -> dict:
    """List documents currently in the docs folder."""
    if not DOCS_FOLDER.exists():
        return {"documents": []}
    docs = sorted(
        f.name for f in DOCS_FOLDER.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    return {"documents": docs}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict:
    """Save an uploaded file to the docs folder."""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )
    DOCS_FOLDER.mkdir(parents=True, exist_ok=True)
    dest = DOCS_FOLDER / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"filename": file.filename}


@app.delete("/documents/{filename}")
def delete_document(filename: str) -> dict:
    """Delete a document file and remove its chunks from the index."""
    file_path = DOCS_FOLDER / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")

    # Remove file from disk
    file_path.unlink()

    # Remove chunks from ChromaDB
    try:
        chroma_client = chromadb.PersistentClient(path=str(DB_PATH / "chroma"))
        col = chroma_client.get_collection(CHROMA_COLLECTION)
        all_items = col.get(where={"source_file": filename}, include=[])
        if all_items["ids"]:
            col.delete(ids=all_items["ids"])
    except Exception:
        pass

    # Remove from SQLite
    try:
        conn = sqlite3.connect(str(SQLITE_DB))
        conn.execute("DELETE FROM chunks WHERE source_file = ?", (filename,))
        conn.commit()
        conn.close()
    except Exception:
        pass

    return {"ok": True, "deleted": filename}


@app.post("/ingest")
def ingest(reset: bool = False) -> dict:
    """Trigger ingestion of all documents in the docs folder."""
    if not DOCS_FOLDER.exists() or not any(
        f for f in DOCS_FOLDER.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ):
        raise HTTPException(status_code=400, detail="No supported documents found in docs/ folder.")
    ingest_folder(DOCS_FOLDER, reset=reset)
    return {"ok": True}


class SummarizeRequest(BaseModel):
    source_file: str


@app.post("/summarize")
def summarize(req: SummarizeRequest) -> QueryResponse:
    """Summarize all indexed chunks for a specific document."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set. Check your .env file.")

    try:
        client_chroma = chromadb.PersistentClient(path=str(DB_PATH / "chroma"))
        col = client_chroma.get_collection(CHROMA_COLLECTION)
    except Exception:
        raise HTTPException(status_code=400, detail="Documents not indexed yet. Click 'Index Documents' first.")

    all_items = col.get(
        where={"source_file": req.source_file},
        include=["documents", "metadatas"],
    )

    if not all_items["ids"]:
        raise HTTPException(status_code=404, detail=f"No indexed chunks found for '{req.source_file}'.")

    # Sort by chunk_index, sample evenly to stay within token budget (~15 chunks)
    paired = sorted(
        zip(all_items["metadatas"], all_items["documents"]),
        key=lambda x: x[0]["chunk_index"],
    )
    total = len(paired)
    step = max(1, total // 15)
    sampled = paired[::step][:15]

    context = "\n\n---\n\n".join(
        f"[{req.source_file}, chunk {m['chunk_index']}]\n{doc}"
        for m, doc in sampled
    )

    system_prompt = (
        "You are a document summarisation assistant. "
        "Summarise the document below in clear, concise prose. "
        "Cover the main topics, key findings, and important details. "
        "Cite sections as [filename, chunk N] where relevant.\n\n"
        f"Document excerpts:\n{context}"
    )

    groq_client = Groq(api_key=api_key)
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please provide a comprehensive summary of '{req.source_file}'."},
        ],
    )
    answer = response.choices[0].message.content or ""

    return QueryResponse(
        answer=answer,
        chunks=[
            ChunkInfo(
                text=doc,
                source_file=m["source_file"],
                page_num=m["page_num"],
                chunk_index=m["chunk_index"],
                score=1.0,
            )
            for m, doc in sampled
        ],
        has_citations=has_citations(answer),
        warning=None,
    )


@app.post("/query")
def query(req: QueryRequest) -> QueryResponse:
    """Answer a question using retrieved document chunks."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set. Check your .env file.")

    try:
        embed_model, rerank_model = _get_models()
        chunks = retrieve(req.question, embed_model, rerank_model)
    except Exception as e:
        if "does not exist" in str(e) or "Collection" in str(e):
            raise HTTPException(status_code=400, detail="Documents not indexed yet. Click 'Index Documents' first.")
        raise HTTPException(status_code=500, detail=str(e))

    if not chunks:
        return QueryResponse(answer="No relevant documents found.", chunks=[], has_citations=False)

    system_prompt = build_system_prompt(chunks)
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.question},
        ],
    )
    answer = response.choices[0].message.content or ""
    cited = has_citations(answer)

    return QueryResponse(
        answer=answer,
        chunks=[
            ChunkInfo(
                text=c.text,
                source_file=c.source_file,
                page_num=c.page_num,
                chunk_index=c.chunk_index,
                score=c.score,
            )
            for c in chunks
        ],
        has_citations=cited,
        warning=(
            "Answer may not be grounded in your documents. Here are the closest chunks found."
            if not cited else None
        ),
    )
