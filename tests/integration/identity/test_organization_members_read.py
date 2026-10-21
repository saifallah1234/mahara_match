# Placement: tests/integration/identity/test_organization_members_read.py
from typing import Any

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from backend.apps.identity.models import (
    Organization,
    OrganizationMember,
    Role,
    RoleCode,
    User,
    UserRole,
    UserStatus,
)

pytestmark = pytest.mark.django_db


def _organization(name: str, org_type: str, matricule: str) -> Organization:
    return Organization.objects.create(
        type=org_type,
        legal_name=name,
        matricule_fiscal=matricule,
        verification_status="VERIFIED",
    )


def _member(email: str, role_code: str, organization: Organization) -> User:
    user = User.objects.create_user(
        email, "test-password", first_name="Member", last_name=email, status=UserStatus.ACTIVE
    )
    UserRole.objects.create(
        user=user, role=Role.objects.get(code=role_code), organization=organization
    )
    OrganizationMember.objects.create(user=user, organization=organization)
    return user


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def companies() -> dict[str, Any]:
    call_command("seed_rbac", verbosity=0)
    acme = _organization("Acme", "COMPANY", "1234567A12345")
    other = _organization("Other", "COMPANY", "7654321B54321")
    return {
        "acme": acme,
        "other": other,
        "recruiter": _member("recruiter@acme.test", RoleCode.RECRUITER, acme),
        "colleague": _member("colleague@acme.test", RoleCode.RECRUITER, acme),
        "other_recruiter": _member("recruiter@other.test", RoleCode.RECRUITER, other),
    }


def test_recruiter_lists_members_of_own_organization(companies: dict[str, Any]) -> None:
    url = reverse("organization-member-list", args=[companies["acme"].id])

    response = _client(companies["recruiter"]).get(url)

    assert response.status_code == 200
    rows = {row["user"]: row for row in response.json()["results"]}
    assert str(companies["recruiter"].id) in rows
    assert str(companies["colleague"].id) in rows
    assert rows[str(companies["colleague"].id)]["email"] == "colleague@acme.test"
    assert rows[str(companies["colleague"].id)]["role"] == "RECRUITER"


def test_training_manager_lists_members_of_own_provider(companies: dict[str, Any]) -> None:
    provider = _organization("Provider", "TRAINING_PROVIDER", "1111111A11111")
    manager = _member("manager@provider.test", RoleCode.TRAINING_MANAGER, provider)
    url = reverse("organization-member-list", args=[provider.id])

    response = _client(manager).get(url)

    assert response.status_code == 200
    assert [row["user"] for row in response.json()["results"]] == [str(manager.id)]


def test_recruiter_cannot_list_members_of_another_organization(
    companies: dict[str, Any],
) -> None:
    url = reverse("organization-member-list", args=[companies["other"].id])

    response = _client(companies["recruiter"]).get(url)

    assert response.status_code == 403


def test_recruiter_cannot_add_members_to_own_organization(companies: dict[str, Any]) -> None:
    url = reverse("organization-member-list", args=[companies["acme"].id])
    newcomer = User.objects.create_user(
        "newcomer@acme.test",
        "test-password",
        first_name="New",
        last_name="Comer",
        status=UserStatus.ACTIVE,
    )

    response = _client(companies["recruiter"]).post(url, {"user": str(newcomer.id)}, format="json")

    assert response.status_code == 403
    assert not OrganizationMember.objects.filter(user=newcomer).exists()
