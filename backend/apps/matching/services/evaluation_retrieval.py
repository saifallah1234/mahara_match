"""Evaluation-only helpers. Ranking itself lives in the production retrieval modules:
``ai.retrieval.hybrid.retriever`` and ``backend.apps.matching.services.retrieval``.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import log2
from typing import TypedDict

from backend.common.retrieval import RetrievalDocument


class RetrievalCase(TypedDict, total=False):
    id: str
    language: str
    category: str
    question: str
    relevant: list[str]


def candidate_details(
    ranked: Sequence[tuple[str, str]], documents: Sequence[RetrievalDocument], limit: int
) -> list[dict[str, str]]:
    title_by_key = {
        (document.entity_type, str(document.entity_id)): document.title for document in documents
    }
    return [
        {
            "type": entity_type,
            "id": entity_id,
            "title": title_by_key.get((entity_type, entity_id), ""),
        }
        for entity_type, entity_id in ranked[:limit]
    ]


def relevance_metrics(
    ranked: Sequence[tuple[str, str]], relevant: Sequence[tuple[str, str]], limit: int
) -> dict[str, float]:
    expected = set(relevant)
    top = ranked[:limit]
    relevant_ranks = [rank for rank, candidate in enumerate(top, 1) if candidate in expected]
    reciprocal_rank = 1 / relevant_ranks[0] if relevant_ranks else 0.0
    recall = len({candidate for candidate in top} & expected) / len(expected) if expected else 0.0
    dcg = sum(1 / log2(rank + 1) for rank in relevant_ranks)
    ideal_count = min(len(expected), limit)
    ideal_dcg = sum(1 / log2(rank + 1) for rank in range(1, ideal_count + 1))
    return {
        f"mrr@{limit}": reciprocal_rank,
        f"recall@{limit}": recall,
        f"ndcg@{limit}": dcg / ideal_dcg if ideal_dcg else 0.0,
    }
