# Placement: tests/integration/matching/test_offer_match_calculation_api.py
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from backend.apps.candidates.models import CandidateProfile, CandidateSkill, SkillLevel
from backend.apps.identity.models import Organization, Role, RoleCode, User, UserRole, UserStatus
from backend.apps.matching.models import OfferMatch
from backend.apps.recruitment.models import JobOffer, JobOfferStatus, OfferSkill
from backend.apps.taxonomy.models import Skill

pytestmark = pytest.mark.django_db


def _user(email: str, role_code: str) -> User:
    user = User.objects.create_user(
        email, "test-password", first_name="Test", last_name="Person", status=UserStatus.ACTIVE
    )
    role = Role.objects.get_or_create(code=role_code, defaults={"name": role_code})[0]
    UserRole.objects.create(user=user, role=role)
    return user


def _published_offer(owner: User) -> Skill:
    organization = Organization.objects.create(
        type="COMPANY",
        legal_name="Acme Ltd",
        matricule_fiscal="1234567A12345",
        verification_status="VERIFIED",
    )
    offer = JobOffer.objects.create(
        organization=organization,
        created_by=owner,
        title="Backend Engineer",
        description="Build useful software.",
        easy_apply=True,
        status=JobOfferStatus.PUBLISHED,
    )
    django = Skill.objects.create(canonical_name="Django")
    OfferSkill.objects.create(offer=offer, skill=django)
    return django


def test_candidate_with_skills_gets_scores_calculated_on_request() -> None:
    candidate = _user("candidate@example.test", RoleCode.CANDIDATE)
    CandidateProfile.objects.create(user=candidate)
    recruiter = _user("recruiter@example.test", RoleCode.RECRUITER)
    django = _published_offer(recruiter)
    CandidateSkill.objects.create(
        candidate=candidate.candidate_profile, skill=django, level=SkillLevel.INTERMEDIATE
    )
    client = APIClient()
    client.force_authenticate(candidate)

    response = client.post(reverse("offer-match-calculate"))

    assert response.status_code == 200
    assert [row["overall_score"] for row in response.json()] == ["100.00"]
    assert OfferMatch.objects.filter(candidate=candidate.candidate_profile).count() == 1


def test_recruiter_cannot_calculate_candidate_scores() -> None:
    recruiter = _user("recruiter@example.test", RoleCode.RECRUITER)
    client = APIClient()
    client.force_authenticate(recruiter)

    response = client.post(reverse("offer-match-calculate"))

    assert response.status_code == 403
    assert OfferMatch.objects.count() == 0
