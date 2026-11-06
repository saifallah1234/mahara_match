from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from backend.apps.identity.models import OnboardingRequest, User, UserStatus
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import IdentityPermissionCode
from backend.apps.platform.services.records import append_audit
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def list_users(actor: User) -> QuerySet[User]:
    require_permission(actor, IdentityPermissionCode.MANAGE_USERS)
    return (
        User.objects.filter(deleted_at__isnull=True)
        .prefetch_related("role_assignments__role")
        .order_by("created_at", "id")
    )


def get_user(actor: User, user_id: UUID | str) -> User:
    require_permission(actor, IdentityPermissionCode.MANAGE_USERS)
    try:
        return (
            User.objects.filter(deleted_at__isnull=True)
            .prefetch_related("role_assignments__role")
            .get(id=user_id)
        )
    except User.DoesNotExist as exc:
        raise DomainNotFoundError("User not found.") from exc


def get_own_profile(actor: User) -> User:
    return User.objects.prefetch_related("role_assignments__role").get(id=actor.id)


def role_assignment_summaries(user: User) -> list[dict[str, Any]]:
    return [
        {
            "role_code": assignment.role.code,
            "organization_id": assignment.organization_id,
        }
        for assignment in user.role_assignments.select_related("role")
    ]


def workspace_summaries(user: User) -> list[dict[str, Any]]:
    if not user.is_active:
        return []
    assignments = user.role_assignments.select_related("role", "organization").order_by(
        "role__code", "organization__legal_name"
    )
    workspaces = []
    for assignment in assignments:
        organization = assignment.organization
        if organization is not None:
            if organization.deleted_at or organization.verification_status != "VERIFIED":
                continue
            if not organization.members.filter(user=user).exists():
                continue
        workspaces.append(
            {
                "role_code": assignment.role.code,
                "organization": (
                    {
                        "id": organization.id,
                        "legal_name": organization.legal_name,
                        "type": organization.type,
                        "verification_status": organization.verification_status,
                    }
                    if organization is not None
                    else None
                ),
            }
        )
    return workspaces


@transaction.atomic
def create_user(actor: User, data: Mapping[str, Any]) -> User:
    require_permission(actor, IdentityPermissionCode.MANAGE_USERS)
    user = create_account(data)
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="identity.user.create",
        entity_type="user",
        entity_id=user.id,
        after={"status": user.status},
    )
    return user


@transaction.atomic
def create_account(data: Mapping[str, Any], *, status: str = UserStatus.PENDING) -> User:
    email = User.objects.normalize_identity_email(str(data["email"]))
    password = str(data["password"])
    candidate = User(email=email, first_name=data["first_name"], last_name=data["last_name"])
    try:
        validate_password(password, user=candidate)
    except DjangoValidationError as exc:
        raise DomainValidationError(details={"password": exc.messages}) from exc

    try:
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data.get("phone", ""),
            status=status,
        )
    except IntegrityError as exc:
        raise DomainValidationError(details={"email": ["This email is already in use."]}) from exc


@transaction.atomic
def update_profile(actor: User, target: User, data: Mapping[str, Any]) -> User:
    if actor.id == target.id:
        require_permission(actor, IdentityPermissionCode.UPDATE_SELF)
    else:
        require_permission(actor, IdentityPermissionCode.MANAGE_USERS)

    for field in ("first_name", "last_name", "phone"):
        if field in data:
            setattr(target, field, data[field])
    target.save(update_fields=[*data.keys(), "updated_at"])
    return target


def _invalidate_credentials(user: User) -> None:
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


@transaction.atomic
def update_status(actor: User, target: User, status: str) -> User:
    require_permission(actor, IdentityPermissionCode.MANAGE_USERS)
    if status not in UserStatus.values:
        raise DomainValidationError(details={"status": ["Invalid account status."]})
    target = User.objects.select_for_update().get(pk=target.pk)
    if (
        status == UserStatus.ACTIVE
        and OnboardingRequest.objects.filter(user=target)
        .exclude(status=OnboardingRequest.Status.APPROVED)
        .exists()
    ):
        raise DomainValidationError(
            "Approve the organization request before activating this account."
        )
    if target.status == status:
        return target

    previous_status = target.status
    target.status = status
    target.save(update_fields=["status", "updated_at"])
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="identity.user.status_change",
        entity_type="user",
        entity_id=target.id,
        before={"status": previous_status},
        after={"status": status},
    )
    _invalidate_credentials(target)
    return target


@transaction.atomic
def delete_own_account(actor: User) -> None:
    require_permission(actor, IdentityPermissionCode.UPDATE_SELF)
    user = User.objects.select_for_update().get(pk=actor.pk)
    if user.deleted_at is None:
        user.status = UserStatus.DISABLED
        user.deleted_at = timezone.now()
        user.save(update_fields=["status", "deleted_at", "updated_at"])
        append_audit(
            actor_type="USER",
            actor_user=actor,
            action="identity.user.delete",
            entity_type="user",
            entity_id=user.id,
            after={"status": UserStatus.DISABLED},
        )
    _invalidate_credentials(user)
