from collections.abc import Iterable, Mapping, Sequence
from uuid import UUID

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from backend.apps.candidates.services.retrieval_scope import (
    limited_profile_documents,
    retrievable_profiles,
)
from backend.apps.matching.models import Embedding
from backend.apps.recruitment.services.retrieval_scope import offer_documents, retrievable_offers
from backend.apps.taxonomy.services.catalog import skills
from backend.apps.training.services.retrieval_scope import program_documents, visible_programs
from backend.common.retrieval import RetrievalDocument

ENTITY_TYPES = ("offer", "skill", "training", "candidate_profile")


def indexable_documents(limit: int | None = None) -> dict[str, list[RetrievalDocument]]:
    """Documents whose vectors may be stored.

    Offers include drafts and closed offers of verified, live organizations so their
    recruiters can search them; every read pre-filters by the caller's scope. Candidate
    profiles are opted-in limited views only.
    """
    offers = retrievable_offers()
    programs = visible_programs()
    profiles = retrievable_profiles()
    skill_records = skills().order_by("id")
    if limit is not None:
        offers = offers[:limit]
        programs = programs[:limit]
        profiles = profiles[:limit]
        skill_records = skill_records[:limit]

    skill_documents = [
        RetrievalDocument(
            "skill",
            skill.id,
            "\n".join(
                part for part in (skill.canonical_name, skill.category, skill.description) if part
            ),
            skill.canonical_name,
        )
        for skill in skill_records
    ]
    return {
        "offer": offer_documents(offers),
        "skill": skill_documents,
        "training": program_documents(programs),
        "candidate_profile": limited_profile_documents(profiles),
    }


@transaction.atomic
def store_embeddings(
    documents: Sequence[RetrievalDocument],
    model_name: str,
    vectors: Iterable[list[float]],
) -> int:
    now = timezone.now()
    rows = [
        Embedding(
            entity_type=document.entity_type,
            entity_id=document.entity_id,
            model_name=model_name,
            embedding=vector,
            created_at=now,
            updated_at=now,
        )
        for document, vector in zip(documents, vectors, strict=True)
    ]
    if rows:
        Embedding.objects.bulk_create(
            rows,
            update_conflicts=True,
            unique_fields=("entity_type", "entity_id", "model_name"),
            update_fields=("embedding", "updated_at"),
        )
    return len(rows)


def stale_embeddings(model_name: str, keep: Mapping[str, Iterable[UUID]]) -> QuerySet[Embedding]:
    """This model's vectors whose entity is no longer indexable.

    ``keep`` maps each entity type to the IDs that are still indexable. Rows of an entity
    type absent from ``keep`` are stale too. Vectors of other models are never included.
    """
    still_indexable = Q()
    for entity_type, entity_ids in keep.items():
        still_indexable |= Q(entity_type=entity_type, entity_id__in=list(entity_ids))
    return (
        Embedding.objects.filter(model_name=model_name)
        .exclude(still_indexable)
        .order_by("entity_type", "entity_id")
    )


@transaction.atomic
def delete_stale_embeddings(model_name: str, keep: Mapping[str, Iterable[UUID]]) -> int:
    deleted, _ = stale_embeddings(model_name, keep).delete()
    return deleted
