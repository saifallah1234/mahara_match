from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from backend.apps.candidates.services.records import create_profile
from backend.apps.identity.models import (
    OnboardingRequest,
    Organization,
    OrganizationMember,
    OrganizationType,
    Role,
    RoleCode,
    User,
    UserRole,
    UserStatus,
)
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import IdentityPermissionCode
from backend.apps.identity.services.organization_members import create_member
from backend.apps.identity.services.user_roles import assign_role
from backend.apps.identity.services.users import create_account, update_status
from backend.apps.platform.services.records import append_audit, send_notification
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


@transaction.atomic
def register(data: Mapping[str, Any]) -> User:
    account_type = data["account_type"]
    if account_type not in {RoleCode.CANDIDATE, RoleCode.RECRUITER, RoleCode.TRAINING_MANAGER}:
        raise DomainValidationError(details={"account_type": ["Invalid account type."]})
    if account_type != RoleCode.CANDIDATE and (
        not data.get("organization_name") or not data.get("matricule_fiscal")
    ):
        raise DomainValidationError(
            details={"organization": ["Name and matricule fiscal are required."]}
        )
    user = create_account(
        data,
        status=UserStatus.ACTIVE if account_type == RoleCode.CANDIDATE else UserStatus.PENDING,
    )
    if account_type == RoleCode.CANDIDATE:
        try:
            role = Role.objects.get(code=RoleCode.CANDIDATE)
        except Role.DoesNotExist as exc:
            raise DomainValidationError("Identity roles have not been initialized.") from exc
        UserRole.objects.create(user=user, role=role)
        create_profile(user, {})
    else:
        OnboardingRequest.objects.create(
            user=user,
            requested_role=account_type,
            organization_name=data["organization_name"],
            matricule_fiscal=data["matricule_fiscal"],
        )
    return user


def list_requests(actor: User) -> QuerySet[OnboardingRequest]:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    return OnboardingRequest.objects.select_related("user", "organization").order_by(
        "created_at", "id"
    )


@transaction.atomic
def approve(actor: User, request_id: UUID, organization_id: UUID) -> OnboardingRequest:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    try:
        request = (
            OnboardingRequest.objects.select_for_update().select_related("user").get(id=request_id)
        )
    except OnboardingRequest.DoesNotExist as exc:
        raise DomainNotFoundError("Onboarding request not found.") from exc
    if (
        request.status != OnboardingRequest.Status.PENDING
        or request.user.status != UserStatus.PENDING
    ):
        raise DomainValidationError("Only pending requests and accounts can be approved.")
    if request.requested_role not in {RoleCode.RECRUITER, RoleCode.TRAINING_MANAGER}:
        raise DomainValidationError("Only recruiter and training requests can be approved.")
    try:
        organization = Organization.objects.get(id=organization_id, deleted_at__isnull=True)
    except Organization.DoesNotExist as exc:
        raise DomainValidationError(
            details={"organization_id": ["Organization not found."]}
        ) from exc
    expected_type = (
        {OrganizationType.COMPANY, OrganizationType.SUBSIDIARY}
        if request.requested_role == RoleCode.RECRUITER
        else {OrganizationType.TRAINING_PROVIDER}
    )
    if organization.type not in expected_type or organization.verification_status != "VERIFIED":
        raise DomainValidationError(
            details={
                "organization_id": ["A verified organization of the correct type is required."]
            }
        )
    if organization.matricule_fiscal != request.matricule_fiscal:
        raise DomainValidationError(
            details={"organization_id": ["Organization identifier does not match the request."]}
        )
    if not OrganizationMember.objects.filter(user=request.user, organization=organization).exists():
        create_member(actor, {"organization_id": organization.id, "user": request.user_id})
    try:
        role = Role.objects.get(code=request.requested_role)
    except Role.DoesNotExist as exc:
        raise DomainValidationError("Identity roles have not been initialized.") from exc
    assign_role(actor, user_id=request.user_id, role_id=role.id, organization_id=organization.id)
    request.organization = organization
    request.status = OnboardingRequest.Status.APPROVED
    request.save(update_fields=["organization", "status", "updated_at"])
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="identity.onboarding.approve",
        entity_type="onboarding_request",
        entity_id=request.id,
        before={"status": OnboardingRequest.Status.PENDING},
        after={
            "status": OnboardingRequest.Status.APPROVED,
            "organization_id": str(organization.id),
        },
    )
    update_status(actor, request.user, UserStatus.ACTIVE)
    send_notification(
        request.user,
        type="identity.onboarding.approved",
        title="Demande approuvée",
        body="Votre demande d’accès a été approuvée. Vous pouvez vous connecter à votre espace.",
        payload_json={"onboarding_request_id": str(request.id)},
    )
    return request


@transaction.atomic
def reject(actor: User, request_id: UUID) -> OnboardingRequest:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    try:
        request = OnboardingRequest.objects.select_for_update().get(id=request_id)
    except OnboardingRequest.DoesNotExist as exc:
        raise DomainNotFoundError("Onboarding request not found.") from exc
    if request.status != OnboardingRequest.Status.PENDING:
        raise DomainValidationError("Only pending requests can be rejected.")
    request.status = OnboardingRequest.Status.REJECTED
    request.save(update_fields=["status", "updated_at"])
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="identity.onboarding.reject",
        entity_type="onboarding_request",
        entity_id=request.id,
        before={"status": OnboardingRequest.Status.PENDING},
        after={"status": OnboardingRequest.Status.REJECTED},
    )
    send_notification(
        request.user,
        type="identity.onboarding.rejected",
        title="Demande refusée",
        body="Votre demande d’accès n’a pas été retenue.",
        payload_json={"onboarding_request_id": str(request.id)},
    )
    return request
