"""Actor-scoped database legs for hybrid retrieval.

Each builder returns a ``ScopedSearch`` (the protocol in ``ai.retrieval.hybrid``)
whose documents, vector neighbours and graph ranking come only from entities the
owning domain says the actor may see. Vector search pre-filters ``embeddings`` by
those IDs; nothing scope-related is stored next to the vectors.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Any
from uuid import UUID

from django.db.models import Q, QuerySet
from pgvector.django import CosineDistance

from backend.apps.candidates.services import retrieval_scope as candidate_scope
from backend.apps.identity.models import User
from backend.apps.matching.models import Embedding
from backend.apps.recruitment.services import retrieval_scope as offer_scope
from backend.apps.recruitment.services.job_offers import list_indexable_job_offers
from backend.apps.taxonomy.services.catalog import skills
from backend.apps.training.services import retrieval_scope as training_scope
from backend.common.retrieval import RetrievalDocument

Key = tuple[str, str]


@dataclass(frozen=True)
class EntitySource:
    """The visible rows of one entity type and how to turn them into documents."""

    rows: QuerySet[Any]
    to_documents: Callable[[QuerySet[Any]], list[RetrievalDocument]]
    ids_for_skills: Callable[[QuerySet[Any], Iterable[UUID]], Counter[UUID]]


class ScopedSearch:
    def __init__(
        self,
        sources: Mapping[str, EntitySource],
        *,
        model_name: str,
        mentioned_skill_ids: Sequence[UUID] = (),
        profile_skill_ids: Sequence[UUID] = (),
        documents: Sequence[RetrievalDocument] | None = None,
    ) -> None:
        """``documents`` may be passed when they were already loaded for the same sources."""
        self.sources = dict(sources)
        self.model_name = model_name
        self.mentioned_skill_ids = list(mentioned_skill_ids)
        self.profile_skill_ids = list(profile_skill_ids)
        if documents is not None:
            self.__dict__["retrieval_documents"] = list(documents)

    @cached_property
    def retrieval_documents(self) -> list[RetrievalDocument]:
        return [
            document
            for source in self.sources.values()
            for document in source.to_documents(source.rows)
        ]

    def documents(self) -> list[tuple[Key, str]]:
        return [
            ((document.entity_type, str(document.entity_id)), document.text)
            for document in self.retrieval_documents
        ]

    def nearest(self, vector: list[float], limit: int) -> list[Key]:
        return semantic_ranking(self.sources, vector, self.model_name, limit)

    def graph(self) -> list[Key]:
        return graph_ranking(self.sources, self.mentioned_skill_ids, self.profile_skill_ids)


def semantic_ranking(
    sources: Mapping[str, EntitySource], vector: list[float], model_name: str, limit: int
) -> list[Key]:
    if not sources:
        return []
    in_scope = Q()
    for entity_type, source in sources.items():
        in_scope |= Q(entity_type=entity_type, entity_id__in=source.rows.values("id"))
    rows = (
        Embedding.objects.filter(in_scope, model_name=model_name)
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance", "entity_type", "entity_id")
        .values_list("entity_type", "entity_id")[:limit]
    )
    return [(entity_type, str(entity_id)) for entity_type, entity_id in rows]


def graph_ranking(
    sources: Mapping[str, EntitySource],
    mentioned_skill_ids: Sequence[UUID],
    profile_skill_ids: Sequence[UUID] = (),
) -> list[Key]:
    """Rank in-scope entities linked to seed skills.

    Skills named in the question outrank the actor's profile skills, which only
    break ties, so an explicit request is never drowned by a long profile.
    """
    scores: dict[Key, tuple[int, int]] = {}
    for entity_type, source in sources.items():
        mentioned = source.ids_for_skills(source.rows, mentioned_skill_ids)
        profile = source.ids_for_skills(source.rows, profile_skill_ids)
        for entity_id in mentioned.keys() | profile.keys():
            scores[(entity_type, str(entity_id))] = (mentioned[entity_id], profile[entity_id])
    return [
        key
        for key, _ in sorted(scores.items(), key=lambda item: (-item[1][0], -item[1][1], item[0]))
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


def skills_mentioned(question: str) -> list[UUID]:
    return [
        skill_id
        for skill_id, name in skills().order_by("id").values_list("id", "canonical_name")
        if skill_is_mentioned(question, name)
    ]


def _offer_source(rows: QuerySet[Any]) -> EntitySource:
    return EntitySource(rows, offer_scope.offer_documents, offer_scope.offer_ids_for_skills)


def _training_source() -> EntitySource:
    return EntitySource(
        training_scope.visible_programs(),
        training_scope.program_documents,
        training_scope.program_ids_for_skills,
    )


def catalogue_search(
    question: str, model_name: str, documents: Sequence[RetrievalDocument] | None = None
) -> ScopedSearch:
    """Public catalogue (published offers + active programs), no personalisation.

    Used by the retrieval evaluation, which has no actor. Pass ``documents`` from a
    previous catalogue search to avoid reloading them for every question.
    """
    return ScopedSearch(
        {"offer": _offer_source(list_indexable_job_offers()), "training": _training_source()},
        model_name=model_name,
        mentioned_skill_ids=skills_mentioned(question),
        documents=documents,
    )


def candidate_offer_search(actor: User, question: str, model_name: str) -> ScopedSearch:
    """Offers a candidate may see, with their own skills as extra graph seeds."""
    return ScopedSearch(
        {"offer": _offer_source(offer_scope.visible_offers(actor))},
        model_name=model_name,
        mentioned_skill_ids=skills_mentioned(question),
        profile_skill_ids=candidate_scope.own_skill_ids(actor),
    )


def recruiter_offer_search(actor: User, question: str, model_name: str) -> ScopedSearch:
    """The recruiter's own organizations' offers, drafts included."""
    return ScopedSearch(
        {"offer": _offer_source(offer_scope.visible_offers(actor))},
        model_name=model_name,
        mentioned_skill_ids=skills_mentioned(question),
    )


def recruiter_profile_search(
    actor: User, question: str, model_name: str, seed_skill_ids: Sequence[UUID] = ()
) -> ScopedSearch:
    """Opted-in limited profiles; ``seed_skill_ids`` come from an in-scope offer if any."""
    source = EntitySource(
        candidate_scope.discoverable_profiles(actor),
        candidate_scope.limited_profile_documents,
        candidate_scope.profile_ids_for_skills,
    )
    mentioned = list(dict.fromkeys([*skills_mentioned(question), *seed_skill_ids]))
    return ScopedSearch(
        {"candidate_profile": source}, model_name=model_name, mentioned_skill_ids=mentioned
    )
