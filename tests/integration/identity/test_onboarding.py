import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient

from backend.apps.candidates.models import CandidateProfile
from backend.apps.identity.models import (
    OnboardingRequest,
    Organization,
    OrganizationMember,
    Role,
    RoleCode,
    User,
    UserRole,
    UserStatus,
)
from backend.apps.identity.services.bootstrap import seed_identity_rbac

pytestmark = pytest.mark.django_db

PASSWORD = "SafeExamplePassword123!"


def browser() -> tuple[APIClient, str]:
    client = APIClient(enforce_csrf_checks=True)
    assert client.get(reverse("csrf-cookie")).status_code == 204
    return client, client.cookies[settings.CSRF_COOKIE_NAME].value


def register(client: APIClient, csrf: str, account_type: str, email: str):
    data = {
        "email": email,
        "password": PASSWORD,
        "first_name": "Test",
        "last_name": "Person",
        "account_type": account_type,
    }
    if account_type != RoleCode.CANDIDATE:
        data.update(organization_name="Example Organization", matricule_fiscal="1234567A12345")
    return client.post(reverse("register"), data, format="json", HTTP_X_CSRFTOKEN=csrf)


def admin_client() -> APIClient:
    admin = User.objects.create_user(
        "admin@example.test",
        PASSWORD,
        first_name="Admin",
        last_name="User",
        status=UserStatus.ACTIVE,
    )
    UserRole.objects.create(user=admin, role=Role.objects.get(code=RoleCode.ADMIN))
    client = APIClient()
    client.force_authenticate(admin)
    return client


def test_candidate_registration_creates_active_private_profile_and_role() -> None:
    seed_identity_rbac()
    client, csrf = browser()
    assert (
        register(
            APIClient(enforce_csrf_checks=True), "", RoleCode.CANDIDATE, "bad@example.test"
        ).status_code
        == 403
    )
    response = register(client, csrf, RoleCode.CANDIDATE, "candidate@example.test")
    assert response.status_code == 201
    user = User.objects.get(email="candidate@example.test")
    assert user.status == UserStatus.ACTIVE
    assert user.email_verified_at is None
    assert UserRole.objects.filter(
        user=user, role__code=RoleCode.CANDIDATE, organization__isnull=True
    ).exists()
    assert CandidateProfile.objects.get(user=user).profile_visibility == "PRIVATE"
    assert register(client, csrf, RoleCode.CANDIDATE, "CANDIDATE@example.test").status_code == 400
    login = client.post(
        reverse("token-obtain-pair"),
        {"email": user.email, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert login.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
    assert client.get(reverse("user-me")).json()["workspaces"] == [
        {"role_code": RoleCode.CANDIDATE, "organization": None}
    ]
    assert client.get(reverse("onboarding-request-list")).status_code == 403


def test_org_registration_waits_for_privileged_review_and_membership_controls_workspace() -> None:
    seed_identity_rbac()
    client, csrf = browser()
    assert register(client, csrf, RoleCode.RECRUITER, "recruiter@example.test").status_code == 201
    user = User.objects.get(email="recruiter@example.test")
    request = OnboardingRequest.objects.get(user=user)
    assert user.status == UserStatus.PENDING
    assert not UserRole.objects.filter(user=user).exists()
    assert (
        client.post(
            reverse("token-obtain-pair"),
            {"email": user.email, "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        ).status_code
        == 401
    )

    org = Organization.objects.create(
        type="COMPANY", legal_name="Example Organization", matricule_fiscal="1234567A12345"
    )
    admin = admin_client()
    assert (
        admin.post(
            reverse("user-status", args=(user.id,)),
            {"status": UserStatus.ACTIVE},
            format="json",
        ).status_code
        == 400
    )
    approve_url = reverse("onboarding-request-approve", args=(request.id,))
    assert (
        admin.post(approve_url, {"organization_id": str(org.id)}, format="json").status_code == 400
    )
    org.verification_status = "VERIFIED"
    org.save(update_fields=["verification_status"])
    assert (
        admin.post(approve_url, {"organization_id": str(org.id)}, format="json").status_code == 200
    )
    assert (
        admin.post(approve_url, {"organization_id": str(org.id)}, format="json").status_code == 400
    )
    user.refresh_from_db()
    assert user.status == UserStatus.ACTIVE
    assert OrganizationMember.objects.filter(user=user, organization=org).exists()
    assert UserRole.objects.filter(
        user=user, role__code=RoleCode.RECRUITER, organization=org
    ).exists()

    login = client.post(
        reverse("token-obtain-pair"),
        {"email": user.email, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
    workspaces = client.get(reverse("user-me")).json()["workspaces"]
    assert workspaces[0]["organization"]["id"] == str(org.id)
    org.verification_status = "PENDING"
    org.save(update_fields=["verification_status"])
    assert client.get(reverse("user-me")).json()["workspaces"] == []
    org.verification_status = "VERIFIED"
    org.save(update_fields=["verification_status"])
    OrganizationMember.objects.filter(user=user, organization=org).delete()
    assert client.get(reverse("user-me")).json()["workspaces"] == []


def test_active_user_without_role_can_read_no_access_session() -> None:
    user = User.objects.create_user(
        "no-role@example.test",
        PASSWORD,
        first_name="No",
        last_name="Role",
        status=UserStatus.ACTIVE,
    )
    client, csrf = browser()
    login = client.post(
        reverse("token-obtain-pair"),
        {"email": user.email, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
    assert client.get(reverse("user-me")).json()["workspaces"] == []


def test_rejected_organization_request_cannot_be_activated() -> None:
    seed_identity_rbac()
    client, csrf = browser()
    assert (
        register(client, csrf, RoleCode.TRAINING_MANAGER, "trainer@example.test").status_code == 201
    )
    user = User.objects.get(email="trainer@example.test")
    request = OnboardingRequest.objects.get(user=user)
    admin = admin_client()
    reject_url = reverse("onboarding-request-reject", args=(request.id,))
    assert admin.post(reject_url, format="json").status_code == 200
    assert admin.post(reject_url, format="json").status_code == 400
    assert (
        admin.post(
            reverse("user-status", args=(user.id,)),
            {"status": UserStatus.ACTIVE},
            format="json",
        ).status_code
        == 400
    )
    user.refresh_from_db()
    assert user.status == UserStatus.PENDING


def test_public_registration_never_grants_staff_roles() -> None:
    seed_identity_rbac()
    client, csrf = browser()
    for role in (RoleCode.ADMIN, RoleCode.MINISTRY_MANAGER):
        response = register(client, csrf, role, f"{role.lower()}@example.test")
        assert response.status_code == 400
    assert not User.objects.filter(
        email__in=["admin@example.test", "ministry_manager@example.test"]
    ).exists()
