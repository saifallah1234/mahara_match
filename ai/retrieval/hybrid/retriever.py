"""Hybrid retrieval: lexical + vector + graph legs fused with reciprocal rank fusion.

Every leg runs inside the caller's authorization scope. This module never queries
storage itself; it receives a ``ScopedSearch`` already bound to an actor (or to the
public catalogue for evaluation) by the backend retrieval service.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from ai.llm.providers.embeddings import EmbeddingUnavailable, embed_query
from ai.retrieval.lexical.scoring import lexical_ranking

Key = tuple[str, str]
Embedder = Callable[[str], list[float]]

RRF_K = 60
LEXICAL, VECTOR, GRAPH = "lexical", "vector", "graph"
ALL_LEGS = frozenset({LEXICAL, VECTOR, GRAPH})


class ScopedSearch(Protocol):
    def documents(self) -> Sequence[tuple[Key, str]]:
        """``((entity_type, entity_id), text)`` for every document visible in scope."""
        ...

    def nearest(self, vector: list[float], limit: int) -> list[Key]:
        """In-scope keys ordered by vector distance to ``vector``."""
        ...

    def graph(self) -> list[Key]:
        """In-scope keys ordered by the graph leg's own score."""
        ...


@dataclass(frozen=True)
class RetrievalResult:
    ranked: list[Key]
    leg_ranks: dict[str, dict[Key, int]]
    latency_ms: dict[str, float]
    vector_unavailable: bool = False
    legs: frozenset[str] = field(default=ALL_LEGS)

    def ranks_for(self, key: Key) -> dict[str, int]:
        return {leg: ranks[key] for leg, ranks in self.leg_ranks.items() if key in ranks}


def reciprocal_rank_fusion(*rankings: Sequence[Key], k: int = RRF_K) -> list[Key]:
    scores: dict[Key, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            scores[key] = scores.get(key, 0.0) + 1 / (k + rank)
    return [key for key, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


def retrieve(
    query: str,
    search: ScopedSearch,
    *,
    legs: Collection[str] = ALL_LEGS,
    vector_limit: int = 20,
    embedder: Embedder = embed_query,
) -> RetrievalResult:
    """Run the requested legs and fuse them.

    When the embedding provider is unavailable the vector leg is skipped and
    ``vector_unavailable`` is set; lexical and graph still answer.
    """
    unknown = set(legs) - ALL_LEGS
    if unknown:
        raise ValueError(f"Unknown retrieval legs: {sorted(unknown)}")
    rankings: dict[str, list[Key]] = {}
    latency: dict[str, float] = {}
    vector_unavailable = False

    if LEXICAL in legs:
        started = time.perf_counter()
        rankings[LEXICAL] = lexical_ranking(query, search.documents())
        latency[LEXICAL] = _elapsed_ms(started)
    if VECTOR in legs:
        started = time.perf_counter()
        try:
            vector = embedder(query)
        except EmbeddingUnavailable:
            vector_unavailable = True
        else:
            rankings[VECTOR] = search.nearest(vector, vector_limit)
        latency[VECTOR] = _elapsed_ms(started)
    if GRAPH in legs:
        started = time.perf_counter()
        rankings[GRAPH] = search.graph()
        latency[GRAPH] = _elapsed_ms(started)

    return RetrievalResult(
        ranked=reciprocal_rank_fusion(*rankings.values()),
        leg_ranks={
            leg: {key: rank for rank, key in enumerate(ranking, start=1)}
            for leg, ranking in rankings.items()
        },
        latency_ms=latency,
        vector_unavailable=vector_unavailable,
        legs=frozenset(legs),
    )


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
