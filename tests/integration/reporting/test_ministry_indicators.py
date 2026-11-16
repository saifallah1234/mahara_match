# Placement: tests/integration/reporting/test_ministry_indicators.py
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from backend.apps.candidates.models import CV, CandidateProfile
from backend.apps.documents.models import Document
from backend.apps.identity.models import Organization, OrganizationMember, Role, User, UserRole
from backend.apps.recruitment.models import Application, JobOffer, OfferSkill
from backend.apps.taxonomy.models import Skill
from backend.apps.training.models import TrainingProgram, TrainingSkill

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

URL = "/api/v1/reporting/indicators/"


def client_for(actor: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(actor)
    return client


def ministry_manager(status: str = "VERIFIED", email: str = "ministry@example.test") -> User:
    user = User.objects.create_user(email, first_name="M", last_name="M", status="ACTIVE")
    org = Organization.objects.create(
        type="MINISTRY",
        legal_name=f"Ministry {email}",
        matricule_fiscal=f"{abs(hash(email)) % 10**7:07d}M00000",
        verification_status=status,
    )
    OrganizationMember.objects.create(user=user, organization=org)
    UserRole.objects.create(
        user=user, role=Role.objects.get(code="MINISTRY_MANAGER"), organization=org
    )
    return user


def offer(
    records: dict[str, Any], title: str, governorate: str, status: str, *skills: Skill
) -> JobOffer:
    job = JobOffer.objects.create(
        organization=records["recruiter_org"],
        created_by=records["recruiter"],
        title=title,
        description="Work",
        governorate=governorate,
        status=status,
        easy_apply=True,
    )
    for skill in skills:
        OfferSkill.objects.create(offer=job, skill=skill, is_mandatory=True)
    return job


def apply(profile: CandidateProfile, job: JobOffer, status: str = "SUBMITTED") -> Application:
    document = Document.objects.create(
        owner_user=profile.user,
        type="CV",
        storage_uri=f"private/{profile.id}/{job.id}",
        file_name="cv.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        uploaded_at=timezone.now(),
    )
    version = CV.objects.filter(candidate=profile).count() + 1
    cv = CV.objects.create(candidate=profile, document=document, title="CV", version_number=version)
    return Application.objects.create(candidate=profile, offer=job, cv=cv, status=status)


def teach(program: TrainingProgram, skill: Skill, purpose: str = "TAUGHT") -> None:
    TrainingSkill.objects.create(
        program=program, skill=skill, target_level="BEGINNER", purpose=purpose
    )


@pytest.fixture
def scenario(phase3: dict[str, Any]) -> dict[str, Any]:
    python, sql, docker = (
        Skill.objects.create(canonical_name=n) for n in ("Python", "SQL", "Docker")
    )
    Skill.objects.create(canonical_name="Unused")
    tunis = offer(phase3, "Tunis job", "Tunis", "PUBLISHED", python, sql)
    offer(phase3, "Nowhere job", "  ", "PUBLISHED", python)
    draft = offer(phase3, "Draft job", "Sfax", "DRAFT", docker)
    deleted = offer(phase3, "Deleted job", "Tunis", "PUBLISHED", docker)
    deleted.deleted_at = timezone.now()
    deleted.save(update_fields=["deleted_at"])

    submitted = apply(phase3["candidate_profile"], tunis)
    apply(phase3["other_candidate_profile"], tunis, "HIRED")
    apply(phase3["candidate_profile"], draft)

    teach(phase3["program"], sql)  # active, provider_org in Tunis
    teach(phase3["program"], python, "PREREQUISITE")
    other = TrainingProgram.objects.create(
        organization=phase3["other_provider_org"], title="Containers", status="ACTIVE"
    )
    teach(other, docker)
    archived = TrainingProgram.objects.create(
        organization=phase3["provider_org"], title="Old", status="ARCHIVED"
    )
    teach(archived, python)
    return {**phase3, "draft": draft, "submitted": submitted, "ministry": ministry_manager()}


def by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {row[key]: row for row in rows}


def test_ministry_manager_sees_aggregate_counts(scenario: dict[str, Any]) -> None:
    response = client_for(scenario["ministry"]).get(URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"regions", "skill_gaps"}
    assert by_key(body["regions"], "governorate") == {
        "Tunis": {
            "governorate": "Tunis",
            "offers": 1,
            "applications": 2,
            "hires": 1,
            "trainings": 1,
        },
        "Sfax": {"governorate": "Sfax", "offers": 0, "applications": 0, "hires": 0, "trainings": 1},
        "Non précisé": {
            "governorate": "Non précisé",
            "offers": 1,
            "applications": 0,
            "hires": 0,
            "trainings": 0,
        },
    }
    assert by_key(body["skill_gaps"], "skill") == {
        "Python": {"skill": "Python", "offer_demand": 2, "training_supply": 0},
        "SQL": {"skill": "SQL", "offer_demand": 1, "training_supply": 1},
        "Docker": {"skill": "Docker", "offer_demand": 0, "training_supply": 1},
    }


def test_admin_may_read_indicators(scenario: dict[str, Any]) -> None:
    assert client_for(scenario["admin"]).get(URL).status_code == 200


@pytest.mark.parametrize("actor", ["candidate", "recruiter", "provider"])
def test_other_roles_are_refused(scenario: dict[str, Any], actor: str) -> None:
    assert client_for(scenario[actor]).get(URL).status_code == 403


def test_unverified_ministry_is_refused(phase3: dict[str, Any]) -> None:
    pending = ministry_manager("PENDING", "pending-ministry@example.test")
    assert client_for(pending).get(URL).status_code == 403


def test_publishing_and_hiring_change_the_counts(scenario: dict[str, Any]) -> None:
    ministry, recruiter = client_for(scenario["ministry"]), client_for(scenario["recruiter"])

    published = recruiter.post(
        f"/api/v1/job-offers/{scenario['draft'].id}/transition/", {"status": "PUBLISHED"}
    )
    hired = recruiter.post(
        f"/api/v1/applications/{scenario['submitted'].id}/transition/", {"status": "HIRED"}
    )

    assert (published.status_code, hired.status_code) == (200, 200)
    regions = by_key(ministry.get(URL).json()["regions"], "governorate")
    assert (regions["Sfax"]["offers"], regions["Sfax"]["applications"]) == (1, 1)
    assert regions["Tunis"]["hires"] == 2
