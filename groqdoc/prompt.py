"""System prompt builder and citation formatter."""

from __future__ import annotations

import re

from groqdoc.retriever import RetrievedChunk

CITATION_PATTERN = re.compile(r"\[([^\]]+),\s*chunk\s*(\d+)\]", re.IGNORECASE)

SYSTEM_PROMPT_TEMPLATE = """\
You are a document Q&A assistant. Answer the user's question using ONLY the context \
passages provided below. Do not use any outside knowledge.

Rules:
1. Cite every claim with [filename, chunk N] immediately after the relevant sentence.
2. If the context only partially answers the question, say so explicitly — do not \
fill gaps with assumptions.
3. If the context does not answer the question at all, reply only with: \
"No relevant documents found."

Context passages:
{context}
"""


def build_system_prompt(chunks: list[RetrievedChunk]) -> str:
    """Return a system prompt with the retrieved chunks embedded."""
    context_blocks = []
    for chunk in chunks:
        header = f"[{chunk.source_file}, chunk {chunk.chunk_index}]"
        context_blocks.append(f"{header}\n{chunk.text}")
    context = "\n\n---\n\n".join(context_blocks)
    return SYSTEM_PROMPT_TEMPLATE.format(context=context)


def has_citations(answer: str) -> bool:
    """Return True if the answer contains at least one citation tag."""
    return bool(CITATION_PATTERN.search(answer))


def format_raw_chunks(chunks: list[RetrievedChunk]) -> str:
    """Format chunks as a plain-text fallback when the answer has no citations."""
    lines = []
    for chunk in chunks:
        lines.append(
            f"  [{chunk.source_file}, chunk {chunk.chunk_index}] "
            f"(score={chunk.score:.3f})\n  {chunk.text[:300]}..."
        )
    return "\n\n".join(lines)
