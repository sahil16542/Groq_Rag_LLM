"""Tests for ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from groqdoc.utils import (
    chunk_text,
    parse_markdown,
    parse_file,
    CHUNK_SIZE,
    TOKENIZER,
)


def _token_count(text: str) -> int:
    return len(TOKENIZER.encode(text))


class TestChunkText:
    def test_short_text_produces_one_chunk(self) -> None:
        text = "This is a short paragraph."
        chunks = chunk_text(text, "test.md", page_num=1)
        assert len(chunks) == 1
        assert chunks[0].text.strip() == text.strip()

    def test_chunk_fields_populated(self) -> None:
        chunks = chunk_text("Hello world.", "myfile.pdf", page_num=3)
        c = chunks[0]
        assert c.source_file == "myfile.pdf"
        assert c.page_num == 3
        assert c.chunk_index == 0
        assert isinstance(c.char_start, int)

    def test_long_text_splits_into_multiple_chunks(self) -> None:
        word = "token " * 600
        chunks = chunk_text(word, "big.txt", page_num=1)
        assert len(chunks) >= 2

    def test_chunk_does_not_exceed_size(self) -> None:
        long_text = "word " * 1000
        chunks = chunk_text(long_text, "big.txt", page_num=1)
        for chunk in chunks:
            assert _token_count(chunk.text) <= CHUNK_SIZE + 10

    def test_chunk_index_increments(self) -> None:
        long_text = "word " * 1000
        chunks = chunk_text(long_text, "big.txt", page_num=1)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_start_chunk_index_offset(self) -> None:
        chunks = chunk_text("Hello.", "f.md", page_num=1, start_chunk_index=5)
        assert chunks[0].chunk_index == 5

    def test_paragraph_boundary_respected(self) -> None:
        text = "First paragraph.\n\nSecond paragraph."
        chunks = chunk_text(text, "f.md", page_num=1)
        assert len(chunks) == 1
        assert "First paragraph" in chunks[0].text
        assert "Second paragraph" in chunks[0].text

    def test_empty_text_returns_no_chunks(self) -> None:
        chunks = chunk_text("   \n\n  ", "empty.md", page_num=1)
        assert chunks == []


class TestParseMarkdown:
    def test_reads_text(self, tmp_path: Path) -> None:
        md = tmp_path / "sample.md"
        md.write_text("# Title\n\nSome content here.")
        pages = parse_markdown(md)
        assert len(pages) == 1
        assert pages[0][0] == 1
        assert "Title" in pages[0][1]

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        md = tmp_path / "empty.md"
        md.write_text("   ")
        pages = parse_markdown(md)
        assert pages == []


class TestParseFile:
    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "data.csv"
        f.write_text("a,b,c")
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_file(f)

    def test_markdown_dispatched(self, tmp_path: Path) -> None:
        md = tmp_path / "doc.md"
        md.write_text("Hello markdown.")
        pages = parse_file(md)
        assert pages and "Hello markdown" in pages[0][1]
