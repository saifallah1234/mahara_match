from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import NAMESPACE_URL, UUID, uuid5

from django.db import transaction
from django.utils import timezone

from backend.apps.identity.models import Organization, User
from backend.apps.imports.models import DataSource
from backend.apps.matching.models import Embedding
from backend.apps.matching.services.evaluation_schema import EVALUATION_SCHEMA, use_schema
from backend.apps.recruitment.models import JobOffer, OfferSkill
from backend.apps.taxonomy.models import Skill
from backend.apps.training.models import TrainingProgram, TrainingSession, TrainingSkill

MIN_SKILL_COUNT = 12
MAX_SKILL_COUNT = 15
EXPECTED_OFFER_COUNT = 23
EXPECTED_DRAFT_COUNT = 22
PROGRAM_COUNT = 6
SKILLS_PER_PROGRAM = 2
SESSION_COUNT = 6


def _normalize_alias(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", unaccented).strip()


def _alias_pattern(alias: str) -> re.Pattern[str]:
    normalized = re.escape(_normalize_alias(alias)).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){normalized}(?!\w)", re.UNICODE)


_SKILL_ALIASES = {
    "Python": ("python",),
    "SQL": ("sql", "structured query language"),
    "Docker": ("docker", "conteneurisation", "containerization"),
    "Cloud Computing": ("cloud", "informatique en nuage"),
    "Machine Learning": ("machine learning", "apprentissage automatique", "ml"),
    "Data Engineering": ("data engineering", "data engineer", "ingenierie des donnees"),
    "Data Analytics": (
        "data analytics",
        "data analysis",
        "analyse de donnees",
        "analytique des donnees",
    ),
    "Deep Learning": ("deep learning", "apprentissage profond"),
    "Natural Language Processing": (
        "natural language processing",
        "traitement du langage naturel",
        "nlp",
    ),
    "Artificial Intelligence": (
        "artificial intelligence",
        "intelligence artificielle",
        "ai",
        "ia",
    ),
    "PostgreSQL": ("postgresql", "postgres"),
    "JavaScript": ("javascript", "js"),
    "TypeScript": ("typescript",),
    "React": ("react", "react.js"),
    "Django": ("django",),
    "REST APIs": ("rest api", "api rest", "restful api"),
    "Git": ("git", "github", "gitlab"),
    "Linux": ("linux",),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "Kubernetes": ("kubernetes", "k8s"),
    "CI/CD": ("ci/cd", "continuous integration", "integration continue"),
    "TensorFlow": ("tensorflow",),
    "PyTorch": ("pytorch",),
    "Java": ("java",),
    "Jupyter": ("jupyter",),
    "ETL": ("etl", "extract transform load"),
    "Apache Spark": ("apache spark", "pyspark", "spark"),
    "Excel": ("excel", "microsoft excel"),
    "Power BI": ("power bi",),
    "NumPy": ("numpy",),
    "Pandas": ("pandas",),
    "C#": ("c#", "c sharp"),
    "C++": ("c++",),
}
_NORMALIZED_SKILLS = {
    canonical: tuple(_alias_pattern(alias) for alias in aliases)
    for canonical, aliases in _SKILL_ALIASES.items()
}


@dataclass(frozen=True)
class EvaluationPlan:
    offers: tuple[SourceOffer, ...]
    skill_names: tuple[str, ...]
    offer_skills: dict[UUID, tuple[str, ...]]
    skill_offer_counts: dict[str, int]
    program_skills: dict[int, tuple[str, ...]]


class SourceOffer(TypedDict):
    id: UUID
    title: str
    description: str
    company_name: str
    contract_type: str
    work_mode: str
    experience_level: str
    country_code: str
    governorate: str
    city: str
    min_salary: Decimal | None
    max_salary: Decimal | None
    application_deadline: date | None
    easy_apply: bool
    offer_url: str
    status: str
    published_at: datetime | None
    deleted_at: datetime | None


def evaluation_uuid(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"mahara-match:{EVALUATION_SCHEMA}:{name}")


def plan_from_public_offers() -> EvaluationPlan:
    with use_schema("public"):
        offers = tuple(
            JobOffer.objects.order_by("id").values(
                "id",
                "title",
                "description",
                "company_name",
                "contract_type",
                "work_mode",
                "experience_level",
                "country_code",
                "governorate",
                "city",
                "min_salary",
                "max_salary",
                "application_deadline",
                "easy_apply",
                "offer_url",
                "status",
                "published_at",
                "deleted_at",
            )
        )

    statuses = Counter(str(offer["status"]) for offer in offers)
    if len(offers) != EXPECTED_OFFER_COUNT or statuses != {
        "DRAFT": EXPECTED_DRAFT_COUNT,
        "PUBLISHED": 1,
    }:
        raise ValueError(
            "Expected exactly 23 public offers (22 DRAFT, 1 PUBLISHED); "
            f"found {len(offers)} with statuses {dict(statuses)}. No data was written."
        )

    offer_mentions: dict[UUID, Counter[str]] = {}
    offer_counts: Counter[str] = Counter()
    for offer in offers:
        mentions = _skill_mentions(str(offer["description"] or ""))
        offer_mentions[offer["id"]] = mentions
        offer_counts.update(mentions.keys())
    eligible_skills = sorted(
        ((name, count) for name, count in offer_counts.items() if count >= 2),
        key=lambda item: (-item[1], item[0]),
    )
    if len(eligible_skills) < MIN_SKILL_COUNT:
        raise ValueError(
            f"Need at least {MIN_SKILL_COUNT} distinct canonical skills mentioned in at least "
            f"two offers; found {len(eligible_skills)}. Counts: {dict(eligible_skills)}. "
            "No evaluation data was written."
        )
    selected_skills = eligible_skills[:MAX_SKILL_COUNT]
    skill_names = tuple(name for name, _ in selected_skills)
    skill_offer_counts = dict(selected_skills)

    offer_skills = link_mentioned_skills(offer_mentions, skill_names)
    program_skills = build_program_skills(skill_names)
    return EvaluationPlan(offers, skill_names, offer_skills, skill_offer_counts, program_skills)


def link_mentioned_skills(
    offer_mentions: dict[UUID, Counter[str]], skill_names: tuple[str, ...]
) -> dict[UUID, tuple[str, ...]]:
    """Link every selected skill actually mentioned by each offer; never truncate."""
    offer_skills: dict[UUID, tuple[str, ...]] = {}
    for offer_id, mentions in offer_mentions.items():
        selected = tuple(name for name in skill_names if name in mentions)
        offer_skills[offer_id] = selected
    return offer_skills


def clear_evaluation_data() -> dict[str, int]:
    with transaction.atomic():
        source = DataSource.objects.filter(name="EVAL_TEST_ONLY GraphRAG Dataset").first()
        offer_ids = (
            list(JobOffer.objects.filter(source=source).values_list("id", flat=True))
            if source
            else []
        )
        program_ids = [evaluation_uuid(f"program:{index}") for index in range(PROGRAM_COUNT)]
        session_ids = [evaluation_uuid(f"session:{index}") for index in range(SESSION_COUNT)]
        skill_ids = list(
            Skill.objects.filter(category="TEST_ONLY_EVALUATION").values_list("id", flat=True)
        )

        counts = {
            "sessions": TrainingSession.objects.filter(id__in=session_ids).count(),
            "training_skills": TrainingSkill.objects.filter(program_id__in=program_ids).count(),
            "programs": TrainingProgram.objects.filter(id__in=program_ids).count(),
            "offer_skills": OfferSkill.objects.filter(offer_id__in=offer_ids).count(),
            "offers": len(offer_ids),
            "skills": len(skill_ids),
            "embeddings": Embedding.objects.filter(
                entity_type__in=("offer", "skill", "training"),
                entity_id__in=[*offer_ids, *skill_ids, *program_ids],
            ).count(),
        }
        Embedding.objects.filter(
            entity_type__in=("offer", "skill", "training"),
            entity_id__in=[*offer_ids, *skill_ids, *program_ids],
        ).delete()
        TrainingSession.objects.filter(id__in=session_ids).delete()
        TrainingSkill.objects.filter(program_id__in=program_ids).delete()
        TrainingProgram.objects.filter(id__in=program_ids).delete()
        OfferSkill.objects.filter(offer_id__in=offer_ids).delete()
        JobOffer.objects.filter(id__in=offer_ids).delete()
        Skill.objects.filter(category="TEST_ONLY_EVALUATION").delete()
        Organization.objects.filter(
            matricule_fiscal__in=("9999999A00000", "9999998A00000")
        ).delete()
        User.objects.filter(email="eval-graphrag@test.invalid").delete()
        if source:
            source.delete()
    return counts


def populate_evaluation_schema(plan: EvaluationPlan) -> dict[str, int]:
    now = timezone.now()
    with use_schema(EVALUATION_SCHEMA):
        with transaction.atomic():
            source, _ = DataSource.objects.update_or_create(
                name="EVAL_TEST_ONLY GraphRAG Dataset",
                defaults={"type": "CSV", "is_authorized": False},
            )
            employer = _test_organization(
                "employer", "TEST ONLY - GraphRAG Evaluation Employer", "COMPANY"
            )
            provider = _test_organization(
                "provider", "TEST ONLY - GraphRAG Evaluation Provider", "TRAINING_PROVIDER"
            )
            creator, _ = User.objects.update_or_create(
                email="eval-graphrag@test.invalid",
                defaults={
                    "first_name": "TEST",
                    "last_name": "GraphRAG Evaluation",
                    "status": "ACTIVE",
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            creator.set_unusable_password()
            creator.save(update_fields=["password", "updated_at"])

            skills_by_name = {
                name: Skill.objects.update_or_create(
                    canonical_name=name,
                    defaults={
                        "category": "TEST_ONLY_EVALUATION",
                        "description": "TEST DATA ONLY: extracted from source offer descriptions.",
                    },
                )[0]
                for name in plan.skill_names
            }
            for source_offer in plan.offers:
                offer_id = source_offer["id"]
                defaults = {
                    key: value
                    for key, value in source_offer.items()
                    if key not in {"id", "status", "published_at", "deleted_at"}
                }
                is_draft = source_offer["status"] == "DRAFT"
                defaults.update(
                    {
                        "organization": employer,
                        "company_name": "TEST ONLY - GraphRAG Evaluation Employer",
                        "created_by": creator,
                        "source": source,
                        "external_id": f"EVAL-{offer_id}",
                        "title": f"TEST ONLY - {source_offer['title']}",
                        "status": "PUBLISHED" if is_draft else source_offer["status"],
                        "published_at": now if is_draft else source_offer["published_at"],
                        "closed_at": None,
                        "deleted_at": source_offer["deleted_at"],
                        "easy_apply": True,
                        "description": f"TEST DATA ONLY. {source_offer['description']}",
                    }
                )
                offer, _ = JobOffer.objects.update_or_create(id=offer_id, defaults=defaults)
                for skill_name in plan.offer_skills[offer_id]:
                    OfferSkill.objects.update_or_create(
                        offer=offer,
                        skill=skills_by_name[skill_name],
                        defaults={"importance": "TEST_ONLY_EVALUATION", "is_mandatory": True},
                    )

            for program_number in range(PROGRAM_COUNT):
                program_id = evaluation_uuid(f"program:{program_number}")
                program_skill_names = plan.program_skills[program_number]
                first_skill = program_skill_names[0]
                program, _ = TrainingProgram.objects.update_or_create(
                    id=program_id,
                    defaults={
                        "organization": provider,
                        "title": f"TEST ONLY - Practical {first_skill.title()} Program",
                        "description": (
                            f"TEST DATA ONLY. Synthetic course using {first_skill} and related skills."
                        ),
                        "level": "INTERMEDIATE",
                        "delivery_mode": "ONLINE",
                        "status": "ACTIVE",
                        "is_free": True,
                        "price": 0,
                    },
                )
                for skill_name in plan.program_skills[program_number]:
                    TrainingSkill.objects.update_or_create(
                        program=program,
                        skill=skills_by_name[skill_name],
                        purpose="TAUGHT",
                        defaults={"target_level": "INTERMEDIATE"},
                    )
                start_date = now + timedelta(days=30 + 7 * program_number)
                TrainingSession.objects.update_or_create(
                    id=evaluation_uuid(f"session:{program_number}"),
                    defaults={
                        "program": program,
                        "start_date": start_date,
                        "end_date": start_date + timedelta(days=2),
                        "registration_deadline": start_date - timedelta(days=1),
                        "capacity": 25,
                        "location_or_url": "TEST DATA ONLY - https://example.invalid/eval-graphrag",
                        "status": "PLANNED",
                    },
                )

    return {
        "offers": len(plan.offers),
        "skills": len(plan.skill_names),
        "offer_skills": sum(map(len, plan.offer_skills.values())),
        "programs": PROGRAM_COUNT,
        "training_skills": sum(map(len, plan.program_skills.values())),
        "skills_without_training": len(plan.skill_names)
        - len({name for names in plan.program_skills.values() for name in names}),
        "sessions": SESSION_COUNT,
    }


def _skill_mentions(text: str) -> Counter[str]:
    normalized_text = _normalize_alias(text)
    return Counter(
        {
            canonical: 1
            for canonical, patterns in _NORMALIZED_SKILLS.items()
            if any(pattern.search(normalized_text) for pattern in patterns)
        }
    )


def build_program_skills(skill_names: tuple[str, ...]) -> dict[int, tuple[str, ...]]:
    if not MIN_SKILL_COUNT <= len(skill_names) <= MAX_SKILL_COUNT:
        raise ValueError(f"Expected {MIN_SKILL_COUNT}-{MAX_SKILL_COUNT} canonical skills.")
    untrained_count = 3 if len(skill_names) == MAX_SKILL_COUNT else 2
    trained = skill_names[:-untrained_count]
    if len(trained) < SKILLS_PER_PROGRAM:
        raise ValueError("Not enough trained skills to populate all programs.")
    return {
        index: tuple(
            trained[(index * SKILLS_PER_PROGRAM + offset) % len(trained)]
            for offset in range(SKILLS_PER_PROGRAM)
        )
        for index in range(PROGRAM_COUNT)
    }


def _test_organization(key: str, legal_name: str, organization_type: str) -> Organization:
    return Organization.objects.update_or_create(
        matricule_fiscal="9999999A00000" if key == "employer" else "9999998A00000",
        defaults={
            "legal_name": legal_name,
            "type": organization_type,
            "verification_status": "VERIFIED",
            "deleted_at": None,
        },
    )[0]
