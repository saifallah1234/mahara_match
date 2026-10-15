from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from backend.apps.matching.models import Embedding
from backend.apps.recruitment.services.job_offers import list_indexable_job_offers
from backend.apps.taxonomy.services.catalog import skills
from backend.apps.training.services.programs import list_indexable_programs


@dataclass(frozen=True)
class EmbeddingDocument:
    entity_type: str
    entity_id: UUID
    text: str


def indexable_documents(limit: int | None = None) -> dict[str, list[EmbeddingDocument]]:
    offers = list_indexable_job_offers()
    programs = list_indexable_programs()
    skill_records = skills().order_by("id")
    if limit is not None:
        offers = offers[:limit]
        programs = programs[:limit]
        skill_records = skill_records[:limit]

    documents: dict[str, list[EmbeddingDocument]] = {"offer": [], "skill": [], "training": []}
    for offer in offers:
        required_skills = ", ".join(link.skill.canonical_name for link in offer.offer_skills.all())
        text = "\n".join(
            part
            for part in (
                offer.title,
                offer.description,
                offer.contract_type,
                offer.work_mode,
                offer.experience_level,
                offer.governorate,
                offer.city,
                offer.organization.legal_name,
                required_skills,
            )
            if part
        )
        documents["offer"].append(EmbeddingDocument("offer", offer.id, text))

    for skill in skill_records:
        text = "\n".join(
            part for part in (skill.canonical_name, skill.category, skill.description) if part
        )
        documents["skill"].append(EmbeddingDocument("skill", skill.id, text))

    for program in programs:
        taught_skills = ", ".join(
            link.skill.canonical_name for link in program.program_skills.all()
        )
        text = "\n".join(
            part
            for part in (
                program.title,
                program.description,
                program.level,
                program.delivery_mode,
                program.organization.legal_name,
                taught_skills,
            )
            if part
        )
        documents["training"].append(EmbeddingDocument("training", program.id, text))

    return documents


@transaction.atomic
def store_embeddings(
    documents: Sequence[EmbeddingDocument],
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
