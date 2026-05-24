"""Tests for retrieval and reranking logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from groqdoc.retriever import retrieve, RetrievedChunk, MIN_COSINE_SCORE, TOP_K_RERANK


def _make_mock_collection(docs: list[str], distances: list[float]) -> MagicMock:
    col = MagicMock()
    col.count.return_value = len(docs)
    col.query.return_value = {
        "documents": [docs],
        "metadatas": [
            [
                {"source_file": f"doc{i}.md", "page_num": 1, "chunk_index": i}
                for i in range(len(docs))
            ]
        ],
        "distances": [distances],
    }
    return col


class TestRetrieve:
    def _embed_model(self) -> MagicMock:
        m = MagicMock()
        m.encode.return_value = [[0.1] * 384]
        return m

    def _rerank_model(self, scores: list[float]) -> MagicMock:
        m = MagicMock()
        m.predict.return_value = scores
        return m

    @patch("groqdoc.retriever._get_collection")
    def test_returns_empty_when_best_score_below_threshold(self, mock_get: MagicMock) -> None:
        # distance of 0.9 → similarity 0.1, well below MIN_COSINE_SCORE
        mock_get.return_value = _make_mock_collection(["chunk text"], [0.9])
        result = retrieve("query", self._embed_model(), self._rerank_model([0.5]))
        assert result == []

    @patch("groqdoc.retriever._get_collection")
    def test_returns_chunks_above_threshold(self, mock_get: MagicMock) -> None:
        docs = [f"chunk {i}" for i in range(3)]
        # distance 0.5 → similarity 0.5, above MIN_COSINE_SCORE (0.35)
        distances = [0.5, 0.6, 0.7]
        mock_get.return_value = _make_mock_collection(docs, distances)
        rerank_scores = [0.9, 0.8, 0.7]
        result = retrieve("query", self._embed_model(), self._rerank_model(rerank_scores))
        assert len(result) > 0
        assert all(isinstance(r, RetrievedChunk) for r in result)

    @patch("groqdoc.retriever._get_collection")
    def test_result_capped_at_top_k_rerank(self, mock_get: MagicMock) -> None:
        docs = [f"chunk {i}" for i in range(8)]
        distances = [0.3] * 8  # similarity 0.7, all above threshold
        mock_get.return_value = _make_mock_collection(docs, distances)
        rerank_scores = list(range(8, 0, -1))
        result = retrieve("query", self._embed_model(), self._rerank_model(rerank_scores))
        assert len(result) <= TOP_K_RERANK

    @patch("groqdoc.retriever._get_collection")
    def test_result_sorted_by_rerank_score_descending(self, mock_get: MagicMock) -> None:
        docs = ["a", "b", "c"]
        distances = [0.4, 0.4, 0.4]  # similarity 0.6
        mock_get.return_value = _make_mock_collection(docs, distances)
        rerank_scores = [0.1, 0.9, 0.5]
        result = retrieve("query", self._embed_model(), self._rerank_model(rerank_scores))
        assert result[0].text == "b"  # highest rerank score

    @patch("groqdoc.retriever._get_collection")
    def test_empty_collection_returns_empty(self, mock_get: MagicMock) -> None:
        col = MagicMock()
        col.count.return_value = 0
        col.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        mock_get.return_value = col
        result = retrieve("query", self._embed_model(), self._rerank_model([]))
        assert result == []
