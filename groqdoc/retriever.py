"""Cosine similarity search + cross-encoder reranking."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

CHROMA_COLLECTION = "groqdoc"
DB_PATH = Path(__file__).parent.parent / "data"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
TOP_K_RETRIEVE = 8
TOP_K_RERANK = 5
MIN_COSINE_SCORE = 0.05


@dataclass
class RetrievedChunk:
    text: str
    source_file: str
    page_num: int
    chunk_index: int
    score: float


def _get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(DB_PATH / "chroma"))
    return client.get_collection(CHROMA_COLLECTION)


def retrieve(
    query: str,
    embed_model: SentenceTransformer,
    rerank_model: CrossEncoder,
) -> list[RetrievedChunk]:
    """
    Embed query, fetch top-K by cosine similarity, rerank to top-5.
    Returns empty list if best score is below MIN_COSINE_SCORE.
    """
    collection = _get_collection()

    query_embedding = embed_model.encode([query], show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(TOP_K_RETRIEVE, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    # ChromaDB cosine distance: similarity = 1 - distance
    distances = results["distances"][0]
    similarities = [1.0 - d for d in distances]

    if not docs or max(similarities) < MIN_COSINE_SCORE:
        return []

    # Cross-encoder rerank
    pairs = [[query, doc] for doc in docs]
    rerank_scores = rerank_model.predict(pairs)

    ranked = sorted(
        zip(docs, metadatas, similarities, rerank_scores),
        key=lambda x: x[3],
        reverse=True,
    )[:TOP_K_RERANK]

    return [
        RetrievedChunk(
            text=doc,
            source_file=meta["source_file"],
            page_num=meta["page_num"],
            chunk_index=meta["chunk_index"],
            score=sim,
        )
        for doc, meta, sim, _ in ranked
    ]


def load_models() -> tuple[SentenceTransformer, CrossEncoder]:
    """Load and return both models. Call once and reuse."""
    return SentenceTransformer(EMBED_MODEL), CrossEncoder(RERANK_MODEL)
