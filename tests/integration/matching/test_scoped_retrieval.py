"""Scope leak tests: no retrieval leg may return an entity outside the caller's scope.

Every seeded entity shares the same skill, the same words and the same vector, so
anything a leg returns is decided by the scope filter alone.
"""

from typing import Any

import pytest
from django.utils import timezone

from ai.retrieval.hybrid.retriever import retrieve
from backend.apps.candidates.models import CandidateSkill, ProfileVisibility, SkillLevel
from backend.apps.identity.models import Organization
from backend.apps.matching.models import Embedding
from backend.apps.matching.services.embedding_index import (
    delete_stale_embeddings,
    indexable_documents,
    stale_embeddings,
)
from backend.apps.matching.services.retrieval import (
    ScopedSearch,
    candidate_offer_search,
    recruiter_offer_search,
    recruiter_profile_search,
)
from backend.apps.recruitment.models import JobOffer, OfferSkill
from backend.apps.recruitment.services.retrieval_scope import get_offer_summary, visible_offers
from backend.apps.taxonomy.models import Skill
from backend.apps.training.models import TrainingProgram, TrainingSkill
from backend.apps.training.services.retrieval_scope import programs_teaching
from backend.common.exceptions import DomainNotFoundError, DomainPermissionError

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

MODEL = "test-embedder"
VECTOR = [1.0, 0.0, 0.0]
QUESTION = "Kotlin developer"


def _vector(entity_type: str, entity_id: Any) -> None:
    now = timezone.now()
    Embedding.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        model_name=MODEL,
        embedding=VECTOR,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def world(phase3: dict[str, Any]) -> dict[str, Any]:
    kotlin = Skill.objects.create(canonical_name="Kotlin")
    unverified = Organization.objects.create(
        type="COMPANY",
        legal_name="Unverified",
        matricule_fiscal="9999999A00000",
        verification_status="PENDING",
    )

    def offer(name: str, organization: Organization, status: str, **extra: Any) -> JobOffer:
        created = JobOffer.objects.create(
            organization=organization,
            created_by=phase3["recruiter"],
            title=f"Kotlin developer {name}",
            description="Kotlin developer for mobile apps",
            easy_apply=True,
            status=status,
            **extra,
        )
        OfferSkill.objects.create(offer=created, skill=kotlin)
        _vector("offer", created.id)
        return created

    own = phase3["recruiter_org"]
    offers = {
        "published": offer("published", own, "PUBLISHED"),
        "draft": offer("draft", own, "DRAFT"),
        "closed": offer("closed", own, "CLOSED"),
        "deleted": offer("deleted", own, "PUBLISHED", deleted_at=timezone.now()),
        "unverified": offer("unverified", unverified, "PUBLISHED"),
        "foreign": offer("foreign", phase3["other_recruiter_org"], "PUBLISHED"),
    }

    opted_in = phase3["candidate_profile"]
    opted_in.profile_visibility = ProfileVisibility.RECRUITERS
    opted_in.headline = "Kotlin developer"
    opted_in.save()
    private = phase3["other_candidate_profile"]
    private.profile_visibility = ProfileVisibility.PRIVATE
    private.headline = "Kotlin developer"
    private.save()
    for profile in (opted_in, private):
        CandidateSkill.objects.create(candidate=profile, skill=kotlin, level=SkillLevel.EXPERT)
        _vector("candidate_profile", profile.id)

    return {**phase3, "kotlin": kotlin, "offers": offers, "unverified_org": unverified}


def _all_legs(search: ScopedSearch) -> set[tuple[str, str]]:
    keys = {key for key, _ in search.documents()}
    keys |= set(search.nearest(VECTOR, 50))
    keys |= set(search.graph())
    keys |= set(retrieve(QUESTION, search, embedder=lambda _: VECTOR).ranked)
    return keys


def _offer_keys(world: dict[str, Any], *names: str) -> set[tuple[str, str]]:
    return {("offer", str(world["offers"][name].id)) for name in names}


def test_candidate_sees_only_published_offers_of_verified_live_organizations(
    world: dict[str, Any],
) -> None:
    search = candidate_offer_search(world["candidate"], QUESTION, MODEL)

    visible = _offer_keys(world, "published", "foreign")
    assert {key for key, _ in search.documents()} == visible
    assert set(search.nearest(VECTOR, 50)) == visible
    assert set(search.graph()) == visible
    assert _all_legs(search) == visible


def test_candidate_profile_skills_seed_the_graph_leg(world: dict[str, Any]) -> None:
    search = candidate_offer_search(world["candidate"], "anything", MODEL)
    assert set(search.graph()) == _offer_keys(world, "published", "foreign")


def test_recruiter_sees_own_drafts_and_closed_but_not_other_organizations(
    world: dict[str, Any],
) -> None:
    search = recruiter_offer_search(world["recruiter"], QUESTION, MODEL)
    assert _all_legs(search) == _offer_keys(world, "published", "draft", "closed")


def test_recruiter_sees_only_opted_in_profiles_without_identity(world: dict[str, Any]) -> None:
    search = recruiter_profile_search(world["recruiter"], QUESTION, MODEL)

    assert _all_legs(search) == {("candidate_profile", str(world["candidate_profile"].id))}
    text = "\n".join(text for _, text in search.documents())
    assert "Kotlin developer" in text
    for private_value in ("Private", "Identity", "candidate@example.test"):
        assert private_value not in text


def test_unverified_recruiter_is_refused(world: dict[str, Any]) -> None:
    organization = world["recruiter_org"]
    organization.verification_status = "PENDING"
    organization.save()
    with pytest.raises(DomainPermissionError):
        recruiter_profile_search(world["recruiter"], QUESTION, MODEL)
    with pytest.raises(DomainPermissionError):
        visible_offers(world["recruiter"])


@pytest.mark.parametrize("role", ["admin", "provider"])
def test_roles_outside_this_iteration_are_refused(world: dict[str, Any], role: str) -> None:
    with pytest.raises(DomainPermissionError):
        visible_offers(world[role])


def test_offer_outside_recruiter_scope_is_not_found(world: dict[str, Any]) -> None:
    own = get_offer_summary(world["recruiter"], world["offers"]["draft"].id)
    assert own.skills == {world["kotlin"].id: "Kotlin"}
    with pytest.raises(DomainNotFoundError):
        get_offer_summary(world["recruiter"], world["offers"]["foreign"].id)
    with pytest.raises(DomainNotFoundError):
        get_offer_summary(world["recruiter"], "not-a-uuid")


def test_missing_skill_hop_returns_only_active_programs_of_verified_providers(
    world: dict[str, Any],
) -> None:
    kotlin = world["kotlin"]
    active = world["program"]
    TrainingSkill.objects.create(program=active, skill=kotlin, target_level=SkillLevel.ADVANCED)
    draft = TrainingProgram.objects.create(
        organization=world["provider_org"],
        title="Kotlin draft",
        status="DRAFT",
        delivery_mode="ONLINE",
    )
    pending_provider = world["other_provider_org"]
    pending_provider.verification_status = "PENDING"
    pending_provider.save()
    unverified = TrainingProgram.objects.create(
        organization=pending_provider,
        title="Kotlin elsewhere",
        status="ACTIVE",
        delivery_mode="ONLINE",
    )
    for program in (draft, unverified):
        TrainingSkill.objects.create(
            program=program, skill=kotlin, target_level=SkillLevel.ADVANCED
        )

    suggestions = programs_teaching([kotlin.id], limit=5)

    assert [suggestion.program_id for suggestion in suggestions] == [active.id]
    assert suggestions[0].skill_name == "Kotlin"


def test_prune_removes_only_vectors_of_entities_no_longer_indexable(
    world: dict[str, Any],
) -> None:
    other_model = Embedding.objects.create(
        entity_type="offer",
        entity_id=world["offers"]["deleted"].id,
        model_name="another-model",
        embedding=VECTOR,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    keep = {
        entity_type: {document.entity_id for document in documents}
        for entity_type, documents in indexable_documents().items()
    }

    stale = set(stale_embeddings(MODEL, keep).values_list("entity_type", "entity_id"))
    deleted = delete_stale_embeddings(MODEL, keep)

    assert stale == {
        ("offer", world["offers"]["deleted"].id),
        ("offer", world["offers"]["unverified"].id),
        ("candidate_profile", world["other_candidate_profile"].id),
    }
    assert deleted == 3
    remaining = set(
        Embedding.objects.filter(model_name=MODEL).values_list("entity_type", "entity_id")
    )
    assert ("offer", world["offers"]["draft"].id) in remaining
    assert ("candidate_profile", world["candidate_profile"].id) in remaining
    assert Embedding.objects.filter(id=other_model.id).exists()
