from collections.abc import Sequence

import pytest

from ai.llm.providers.embeddings import EmbeddingUnavailable
from ai.retrieval.hybrid.retriever import (
    GRAPH,
    LEXICAL,
    VECTOR,
    Key,
    reciprocal_rank_fusion,
    retrieve,
)

pytestmark = pytest.mark.unit

A, B, C, D = ("offer", "a"), ("offer", "b"), ("offer", "c"), ("training", "d")


class FakeSearch:
    def __init__(self) -> None:
        self.nearest_calls: list[tuple[list[float], int]] = []

    def documents(self) -> Sequence[tuple[Key, str]]:
        return [(A, "python django"), (B, "python"), (C, "chef cuisine")]

    def nearest(self, vector: list[float], limit: int) -> list[Key]:
        self.nearest_calls.append((vector, limit))
        return [C, B]

    def graph(self) -> list[Key]:
        return [D, B]


def test_rrf_rewards_keys_ranked_by_several_legs() -> None:
    assert reciprocal_rank_fusion([A, B], [B, C], [B]) == [B, A, C]


def test_rrf_ties_are_broken_by_key() -> None:
    assert reciprocal_rank_fusion([B], [A]) == [A, B]


def test_all_legs_are_fused_with_per_leg_ranks() -> None:
    search = FakeSearch()
    result = retrieve("python django", search, embedder=lambda _: [0.5], vector_limit=7)

    assert result.ranked[0] == B
    assert set(result.ranked) == {A, B, C, D}
    assert result.ranks_for(B) == {LEXICAL: 2, VECTOR: 2, GRAPH: 2}
    assert result.ranks_for(D) == {GRAPH: 1}
    assert search.nearest_calls == [([0.5], 7)]
    assert set(result.latency_ms) == {LEXICAL, VECTOR, GRAPH}
    assert not result.vector_unavailable


def test_embedding_outage_degrades_to_lexical_and_graph() -> None:
    def down(_: str) -> list[float]:
        raise EmbeddingUnavailable("connection refused")

    search = FakeSearch()
    result = retrieve("python", search, embedder=down)

    assert result.vector_unavailable
    assert search.nearest_calls == []
    assert set(result.leg_ranks) == {LEXICAL, GRAPH}
    assert set(result.ranked) == {A, B, D}


def test_selected_legs_only() -> None:
    result = retrieve("python", FakeSearch(), legs={LEXICAL}, embedder=lambda _: [1.0])
    assert result.ranked == [A, B]
    assert set(result.leg_ranks) == {LEXICAL}


def test_unknown_leg_is_rejected() -> None:
    with pytest.raises(ValueError, match="bm25"):
        retrieve("python", FakeSearch(), legs={"bm25"})
