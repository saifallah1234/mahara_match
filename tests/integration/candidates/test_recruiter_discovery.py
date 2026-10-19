from datetime import date
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from backend.apps.candidates.api.serializers import CandidateProfileSerializer
from backend.apps.candidates.models import (
    CV,
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    Education,
    Experience,
    ProfileVisibility,
)
from backend.apps.candidates.services.bootstrap import seed_candidates_rbac
from backend.apps.candidates.services.contracts import CandidatePermissionCode
from backend.apps.candidates.services.discovery import list_candidates
from backend.apps.documents.models import Document
from backend.apps.identity.models import (
    Organization,
    OrganizationMember,
    Role,
    RoleCode,
    RolePermission,
    User,
    UserRole,
    UserStatus,
)
from backend.apps.identity.services.bootstrap import seed_identity_rbac
from backend.apps.taxonomy.models import EducationLevel, Skill
from backend.common.exceptions import DomainPermissionError

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def account(email: str) -> User:
    return User.objects.create_user(
        email, first_name="Private", last_name="Name", phone="12345678", status=UserStatus.ACTIVE
    )


def client_for(user: User | None = None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


@pytest.fixture
def recruiter() -> User:
    seed_identity_rbac()
    seed_candidates_rbac()
    actor = account("recruiter@example.test")
    org = Organization.objects.create(
        type="COMPANY",
        legal_name="Company",
        matricule_fiscal="0000001A00000",
        verification_status="VERIFIED",
    )
    OrganizationMember.objects.create(organization=org, user=actor)
    UserRole.objects.create(
        user=actor, role=Role.objects.get(code=RoleCode.RECRUITER), organization=org
    )
    return actor


@pytest.fixture
def profile(recruiter: User) -> CandidateProfile:
    user = account("candidate@example.test")
    UserRole.objects.create(user=user, role=Role.objects.get(code=RoleCode.CANDIDATE))
    return CandidateProfile.objects.create(
        user=user,
        profile_visibility=ProfileVisibility.RECRUITERS,
        headline="Python developer",
        governorate="Tunis",
        birth_date=date(1990, 1, 1),
        city="Private city",
        summary="Private summary",
        desired_job_title="Private target",
    )


def detail(profile: CandidateProfile) -> str:
    return reverse("candidate-profile-detail", args=(profile.id,))


@pytest.mark.parametrize("endpoint", ["list", "detail"])
def test_discovery_requires_authentication_and_recruiter(
    profile: CandidateProfile,
    endpoint: str,
) -> None:
    url = reverse("candidate-profile-list") if endpoint == "list" else detail(profile)
    response = client_for().get(url)
    assert response.status_code == 401
    assert "error" in response.json()
    response = client_for(profile.user).get(url)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


@pytest.mark.parametrize(
    "restriction", ["membership", "role", "permission", "pending_org", "deleted_org", "wrong_org"]
)
def test_recruiter_requires_valid_scope_and_permission(
    recruiter: User,
    profile: CandidateProfile,
    restriction: str,
) -> None:
    assignment = UserRole.objects.get(user=recruiter)
    org = assignment.organization
    assert org is not None
    if restriction == "membership":
        OrganizationMember.objects.filter(user=recruiter).delete()
    elif restriction == "role":
        assignment.delete()
    elif restriction == "permission":
        RolePermission.objects.filter(permission__code=CandidatePermissionCode.DISCOVER).delete()
    elif restriction == "pending_org":
        org.verification_status = "PENDING"
        org.save()
    elif restriction == "deleted_org":
        org.deleted_at = timezone.now()
        org.save()
    else:
        org.type = "MINISTRY"
        org.save()
    client = client_for(recruiter)
    assert client.get(reverse("candidate-profile-list"), {"skill": "invalid"}).status_code == 403
    assert client.get(detail(profile)).status_code == 403


@pytest.mark.parametrize("role_code", [RoleCode.ADMIN, RoleCode.MINISTRY_MANAGER])
def test_other_roles_and_superuser_do_not_bypass_recruiter_role(
    recruiter: User,
    profile: CandidateProfile,
    role_code: str,
) -> None:
    assignment = UserRole.objects.get(user=recruiter)
    assignment.role = Role.objects.get(code=role_code)
    assignment.save()
    recruiter.is_superuser = True
    recruiter.save()
    assert client_for(recruiter).get(reverse("candidate-profile-list")).status_code == 403
    assert client_for(recruiter).get(detail(profile)).status_code == 403


@pytest.mark.parametrize("deleted", [False, True])
def test_inactive_recruiter_is_denied(
    recruiter: User, profile: CandidateProfile, deleted: bool
) -> None:
    if deleted:
        recruiter.deleted_at = timezone.now()
    else:
        recruiter.status = UserStatus.DISABLED
    recruiter.save()
    client = client_for(recruiter)
    assert client.get(reverse("candidate-profile-list")).status_code == 403
    assert client.get(detail(profile)).status_code == 403
    with pytest.raises(DomainPermissionError):
        list_candidates(recruiter)


def test_visibility_cannot_be_bypassed_by_uuid_or_filters(
    recruiter: User,
    profile: CandidateProfile,
) -> None:
    profile.profile_visibility = ProfileVisibility.PRIVATE
    profile.save()
    skill = Skill.objects.create(canonical_name="Python")
    CandidateSkill.objects.create(candidate=profile, skill=skill, level="EXPERT")
    CandidatePreference.objects.create(candidate=profile, work_mode="REMOTE")
    client = client_for(recruiter)
    for filters in (
        {},
        {"search": "Python"},
        {"skill": str(skill.id)},
        {"governorate": "Tunis"},
        {"work_mode": "REMOTE"},
    ):
        response = client.get(reverse("candidate-profile-list"), filters)
        assert response.status_code == 200
        assert response.json()["count"] == 0
    assert client.get(detail(profile)).status_code == 404


@pytest.mark.parametrize("status", ["PENDING", "SUSPENDED", "DISABLED", "deleted"])
def test_inactive_candidate_is_hidden(
    recruiter: User, profile: CandidateProfile, status: str
) -> None:
    user = profile.user
    if status == "deleted":
        user.deleted_at = timezone.now()
    else:
        user.status = status
    user.save()
    client = client_for(recruiter)
    assert client.get(reverse("candidate-profile-list")).json()["count"] == 0
    assert client.get(detail(profile)).status_code == 404


def test_redacted_contract_and_self_contract(recruiter: User, profile: CandidateProfile) -> None:
    skill = Skill.objects.create(canonical_name="Python")
    CandidateSkill.objects.create(
        candidate=profile,
        skill=skill,
        level="EXPERT",
        years_experience=3,
        validated=True,
        source="Private provenance",
    )
    level = EducationLevel.objects.create(name="Master", level_order=1)
    Education.objects.create(
        candidate=profile,
        education_level=level,
        institution="University",
        field_of_study="Computing",
        start_year=2010,
        description="Private description",
    )
    Experience.objects.create(
        candidate=profile,
        organization_name="Employer",
        job_title="Developer",
        start_date=date(2020, 1, 1),
        description="Private description",
    )
    CandidatePreference.objects.create(candidate=profile, work_mode="REMOTE", relocation="OPEN")
    document = Document.objects.create(
        owner_user=profile.user,
        type="CV",
        storage_uri="private/storage",
        file_name="private.pdf",
        mime_type="application/pdf",
        size_bytes=5,
        uploaded_at=timezone.now(),
    )
    cv = CV.objects.create(
        candidate=profile, document=document, title="Private CV", version_number=1
    )
    client = client_for(recruiter)
    response = client.get(detail(profile))
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "id",
        "headline",
        "skills",
        "experiences",
        "educations",
        "governorate",
        "preferences",
    }
    assert set(data["skills"][0]) == {"skill", "level", "years_experience"}
    assert set(data["experiences"][0]) == {
        "organization_name",
        "job_title",
        "start_date",
        "end_date",
    }
    assert set(data["educations"][0]) == {
        "education_level",
        "institution",
        "field_of_study",
        "start_year",
        "end_year",
    }
    assert set(data["preferences"]) == {"work_mode", "relocation", "distance"}
    assert "Private" not in response.content.decode()
    assert str(document.id) not in response.content.decode()
    assert str(cv.id) not in response.content.decode()
    assert client.get(reverse("candidate-profile-list")).json()["results"] == [data]
    cv.deleted_at = timezone.now()
    cv.save()
    assert client.get(detail(profile)).json() == data
    self_response = client_for(profile.user).get(reverse("candidate-profile-me"))
    assert self_response.status_code == 200
    assert self_response.json() == dict(CandidateProfileSerializer(profile).data)
    assert self_response.json()["birth_date"] == "1990-01-01"


def test_filters_pagination_and_missing_preferences(
    recruiter: User, profile: CandidateProfile
) -> None:
    other = CandidateProfile.objects.create(
        user=account("other@example.test"),
        profile_visibility=ProfileVisibility.RECRUITERS,
        headline="Designer",
        governorate="Sfax",
    )
    skill = Skill.objects.create(canonical_name="Python")
    CandidateSkill.objects.create(candidate=profile, skill=skill, level="EXPERT")
    level = EducationLevel.objects.create(name="Master", level_order=1)
    Education.objects.create(
        candidate=profile, education_level=level, institution="University", start_year=2010
    )
    CandidatePreference.objects.create(candidate=profile, work_mode="REMOTE", relocation="OPEN")
    for title in ("Engineer", "Senior engineer"):
        Experience.objects.create(
            candidate=profile,
            organization_name="Company",
            job_title=title,
            start_date=date(2020, 1, 1),
        )
    client = client_for(recruiter)
    for filters in (
        {"skill": str(skill.id)},
        {"education_level": str(level.id)},
        {"governorate": "tunis"},
        {"work_mode": "REMOTE"},
        {"relocation": "OPEN"},
        {"search": "engineer"},
        {"search": "Python"},
        {"skill": str(skill.id), "governorate": "Tunis"},
    ):
        response = client.get(reverse("candidate-profile-list"), filters)
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["results"][0]["id"] == str(profile.id)
    assert client.get(detail(other)).json()["preferences"] is None
    assert client.get(reverse("candidate-profile-list"), {"search": "Private"}).json()["count"] == 0
    first = client.get(reverse("candidate-profile-list"), {"page_size": 1}).json()
    second = client.get(reverse("candidate-profile-list"), {"page_size": 1, "page": 2}).json()
    assert first["count"] == second["count"] == 2
    assert first["next"] and second["previous"]
    assert first["results"][0]["id"] != second["results"][0]["id"]


@pytest.mark.parametrize(
    "filters",
    [
        {"skill": "invalid"},
        {"education_level": "invalid"},
        {"work_mode": "invalid"},
        {"relocation": "invalid"},
    ],
)
def test_invalid_filters_use_shared_error(recruiter: User, filters: dict[str, Any]) -> None:
    response = client_for(recruiter).get(reverse("candidate-profile-list"), filters)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_discovery_permission_seed_is_idempotent_and_recruiter_only(recruiter: User) -> None:
    seed_candidates_rbac()
    assert list(
        RolePermission.objects.filter(
            permission__code=CandidatePermissionCode.DISCOVER
        ).values_list("role__code", flat=True)
    ) == [RoleCode.RECRUITER]


@pytest.mark.parametrize("deleted", [False, True])
def test_existing_jwt_is_rejected_for_inactive_recruiter(
    recruiter: User, profile: CandidateProfile, deleted: bool
) -> None:
    token = str(AccessToken.for_user(recruiter))
    if deleted:
        recruiter.deleted_at = timezone.now()
    else:
        recruiter.status = UserStatus.DISABLED
    recruiter.save()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    assert client.get(reverse("candidate-profile-list")).status_code == 401
    assert client.get(detail(profile)).status_code == 401


def test_self_opt_in_and_revocation_take_effect_immediately(
    recruiter: User, profile: CandidateProfile
) -> None:
    owner = client_for(profile.user)
    reviewer = client_for(recruiter)
    for visibility in ("PRIVATE", "RECRUITERS", "PUBLIC"):
        response = owner.patch(
            reverse("candidate-profile-me"), {"profile_visibility": visibility}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["profile_visibility"] == visibility
        expected = visibility in ("RECRUITERS", "PUBLIC")  # PUBLIC includes recruiters (Q28).
        assert reviewer.get(reverse("candidate-profile-list")).json()["count"] == int(expected)
        assert reviewer.get(detail(profile)).status_code == (200 if expected else 404)


def test_invalid_candidate_uuid_uses_shared_not_found(recruiter: User) -> None:
    response = client_for(recruiter).get(reverse("candidate-profile-detail", args=("invalid",)))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
