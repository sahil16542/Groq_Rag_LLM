"""Shared helpers: file parsing and token-aware chunking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import tiktoken
from pypdf import PdfReader
from docx import Document

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
TOKENIZER = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    text: str
    source_file: str
    page_num: int
    chunk_index: int
    char_start: int


def _tokenize(text: str) -> list[int]:
    return TOKENIZER.encode(text)


def _decode(tokens: list[int]) -> str:
    return TOKENIZER.decode(tokens)


def parse_pdf(path: Path) -> list[tuple[int, str]]:
    """Return list of (page_num, text) for each page in a PDF."""
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i + 1, text))
    return pages


def parse_docx(path: Path) -> list[tuple[int, str]]:
    """Return list of (page_num=1, full_text) for a DOCX file."""
    doc = Document(str(path))
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [(1, text)] if text else []


def parse_markdown(path: Path) -> list[tuple[int, str]]:
    """Return list of (page_num=1, full_text) for a Markdown file."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [(1, text)] if text.strip() else []


def parse_file(path: Path) -> list[tuple[int, str]]:
    """Dispatch to the right parser based on file extension."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix == ".docx":
        return parse_docx(path)
    if suffix in (".md", ".markdown"):
        return parse_markdown(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _split_paragraphs(text: str) -> list[str]:
    """Split text on blank lines into paragraphs."""
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def chunk_text(
    text: str,
    source_file: str,
    page_num: int,
    start_chunk_index: int = 0,
) -> list[Chunk]:
    """
    Chunk text by paragraph boundaries first, then by token window.
    Returns a list of Chunk objects.
    """
    paragraphs = _split_paragraphs(text)
    chunks: list[Chunk] = []
    buffer_tokens: list[int] = []
    buffer_char_start = 0
    char_cursor = 0
    chunk_index = start_chunk_index

    def flush(tokens: list[int], char_start: int) -> None:
        nonlocal chunk_index
        if not tokens:
            return
        chunk_text_str = _decode(tokens)
        chunks.append(
            Chunk(
                text=chunk_text_str,
                source_file=source_file,
                page_num=page_num,
                chunk_index=chunk_index,
                char_start=char_start,
            )
        )
        chunk_index += 1

    for para in paragraphs:
        para_tokens = _tokenize(para)
        para_char_start = text.find(para, char_cursor)
        if para_char_start == -1:
            para_char_start = char_cursor
        char_cursor = para_char_start + len(para)

        # If para alone exceeds chunk size, split it by token window
        if len(para_tokens) > CHUNK_SIZE:
            # flush what we have first
            flush(buffer_tokens, buffer_char_start)
            buffer_tokens = []

            offset = 0
            while offset < len(para_tokens):
                window = para_tokens[offset : offset + CHUNK_SIZE]
                window_start = para_char_start  # approximate
                flush(window, window_start)
                offset += CHUNK_SIZE - CHUNK_OVERLAP

            # seed overlap from end of this large para
            buffer_tokens = para_tokens[-(CHUNK_OVERLAP):]
            buffer_char_start = para_char_start
            continue

        # Would adding this para exceed chunk size?
        if buffer_tokens and len(buffer_tokens) + len(para_tokens) > CHUNK_SIZE:
            flush(buffer_tokens, buffer_char_start)
            # keep overlap
            buffer_tokens = buffer_tokens[-CHUNK_OVERLAP:]
            buffer_char_start = para_char_start

        if not buffer_tokens:
            buffer_char_start = para_char_start

        buffer_tokens.extend(para_tokens)

    flush(buffer_tokens, buffer_char_start)
    return chunks


def chunk_file(path: Path) -> Generator[Chunk, None, None]:
    """Parse a file and yield all chunks from it."""
    pages = parse_file(path)
    chunk_index = 0
    for page_num, text in pages:
        new_chunks = chunk_text(
            text,
            source_file=path.name,
            page_num=page_num,
            start_chunk_index=chunk_index,
        )
        for chunk in new_chunks:
            yield chunk
        chunk_index += len(new_chunks)
