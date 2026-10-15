from __future__ import annotations

import re
from collections import Counter
from math import log2
from typing import TypedDict
from uuid import UUID

from django.db.models import QuerySet
from pgvector.django import CosineDistance

from backend.apps.matching.models import Embedding
from backend.apps.matching.services.embedding_index import EmbeddingDocument
from backend.apps.recruitment.models import OfferSkill
from backend.apps.taxonomy.models import Skill
from backend.apps.training.models import TrainingSkill

_WORD = re.compile(r"[^\W_][\w+#.-]{2,}", re.UNICODE)


class RetrievalCase(TypedDict, total=False):
    id: str
    language: str
    category: str
    question: str
    relevant: list[str]


def lexical_ranking(question: str, documents: list[EmbeddingDocument]) -> list[tuple[str, str]]:
    query_terms = set(_tokens(question))
    scored = []
    for document in documents:
        if document.entity_type not in {"offer", "training"}:
            continue
        overlap = len(query_terms & set(_tokens(document.text)))
        key = _candidate_key(document.entity_type, document.entity_id)
        scored.append((overlap, key))
    return [key for _, key in sorted(scored, key=lambda item: (-item[0], item[1]))]


def semantic_ranking(
    question_vector: list[float], model_name: str, limit: int
) -> list[tuple[str, str]]:
    queryset: QuerySet[Embedding] = Embedding.objects.filter(
        model_name=model_name,
        entity_type__in=("offer", "training"),
    )
    return [
        (entity_type, str(entity_id))
        for entity_type, entity_id in queryset.annotate(
            distance=CosineDistance("embedding", question_vector)
        )
        .order_by("distance", "entity_type", "entity_id")
        .values_list("entity_type", "entity_id")[:limit]
    ]


def skill_is_mentioned(question: str, skill_name: str) -> bool:
    """True if the skill name appears as a whole term in the question.

    Case-insensitive. Boundaries only consider Latin letters and digits,
    so attached Arabic prefixes (e.g. "وSQL") still match, while "Java"
    does not match inside "JavaScript".
    """
    name = re.escape(skill_name.lower())
    pattern = r"(?<![a-z0-9])" + name + r"(?![a-z0-9])"
    return re.search(pattern, question.lower()) is not None


def graph_skill_ranking(question: str) -> list[tuple[str, str]]:
    skill_ids = [
        skill_id
        for skill_id, name in Skill.objects.values_list("id", "canonical_name")
        if skill_is_mentioned(question, name)
    ]
    scores: Counter[tuple[str, str]] = Counter()
    offer_links = OfferSkill.objects.filter(skill_id__in=skill_ids)
    for (offer_id,) in offer_links.values_list("offer_id"):
        scores[("offer", str(offer_id))] += 1
    training_links = TrainingSkill.objects.filter(skill_id__in=skill_ids)
    for (program_id,) in training_links.values_list("program_id"):
        scores[("training", str(program_id))] += 1
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [key for key, _ in ranked]


def reciprocal_rank_fusion(*rankings: list[tuple[str, str]]) -> list[tuple[str, str]]:
    scores: dict[tuple[str, str], float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            scores[key] = scores.get(key, 0.0) + 1 / (60 + rank)
    return [key for key, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


def candidate_details(
    ranked: list[tuple[str, str]], documents: list[EmbeddingDocument], limit: int
) -> list[dict[str, str]]:
    text_by_key = {
        _candidate_key(document.entity_type, document.entity_id): document.text
        for document in documents
    }
    results = []
    for entity_type, entity_id in ranked[:limit]:
        text = text_by_key.get((entity_type, entity_id), "")
        title = text.splitlines()[0] if text else ""
        results.append({"type": entity_type, "id": entity_id, "title": title})
    return results


def relevance_metrics(
    ranked: list[tuple[str, str]], relevant: list[tuple[str, str]], limit: int
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


def _tokens(text: str) -> list[str]:
    return [token.casefold().strip(".-") for token in _WORD.findall(text)]


def _candidate_key(entity_type: str, entity_id: UUID) -> tuple[str, str]:
    return entity_type, str(entity_id)
