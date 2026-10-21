from typing import Any
from uuid import UUID

from django.apps import apps
from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from backend.apps.identity.models import Role, User, UserRole
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import (
    GLOBAL_ROLE_CODES,
    ORGANIZATION_ROLE_TYPES,
    IdentityPermissionCode,
)
from backend.apps.platform.services.records import append_audit
from backend.common.exceptions import (
    DomainNotFoundError,
    DomainPermissionError,
    DomainValidationError,
)


def list_user_roles(actor: User) -> QuerySet[UserRole]:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    return UserRole.objects.select_related("user", "role", "organization").order_by(
        "created_at", "id"
    )


def get_user_role(actor: User, assignment_id: UUID | str) -> UserRole:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    try:
        return UserRole.objects.select_related("user", "role", "organization").get(id=assignment_id)
    except UserRole.DoesNotExist as exc:
        raise DomainNotFoundError("Role assignment not found.") from exc


def _get_organization(organization_id: UUID) -> Any:
    try:
        organization_model = apps.get_model("identity", "Organization")
    except LookupError as exc:
        raise DomainValidationError(
            "Organization integration is not available until the P4 identity models are merged."
        ) from exc
    try:
        return organization_model.objects.get(id=organization_id)
    except organization_model.DoesNotExist as exc:
        raise DomainValidationError(
            details={"organization_id": ["Organization not found."]}
        ) from exc


def _validate_scope(user: User, role: Role, organization_id: UUID | None) -> None:
    if role.code in GLOBAL_ROLE_CODES:
        if organization_id is not None:
            raise DomainValidationError(
                details={"organization_id": [f"{role.code} is a global role."]}
            )
        return

    allowed_types = ORGANIZATION_ROLE_TYPES.get(role.code)
    if allowed_types is None:
        raise DomainValidationError(
            details={"role_id": ["This role has no approved scope policy."]}
        )
    if organization_id is None:
        raise DomainValidationError(
            details={"organization_id": [f"{role.code} requires an organization."]}
        )

    organization = _get_organization(organization_id)
    if organization.type not in allowed_types:
        raise DomainValidationError(
            details={"organization_id": ["The organization type is incompatible with this role."]}
        )

    membership_model = apps.get_model("identity", "OrganizationMember")
    is_member = membership_model.objects.filter(
        user_id=user.id,
        organization_id=organization.id,
    ).exists()
    if not is_member:
        raise DomainValidationError(
            details={"organization_id": ["The user must belong to the organization."]}
        )


@transaction.atomic
def assign_role(
    actor: User,
    *,
    user_id: UUID,
    role_id: UUID,
    organization_id: UUID | None,
) -> UserRole:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    if actor.id == user_id:
        raise DomainPermissionError("Self-assignment of roles is not allowed.")
    try:
        user = User.objects.select_for_update().get(id=user_id)
        role = Role.objects.get(id=role_id)
    except (User.DoesNotExist, Role.DoesNotExist) as exc:
        raise DomainValidationError(details={"assignment": ["User or role not found."]}) from exc

    _validate_scope(user, role, organization_id)
    try:
        assignment = UserRole.objects.create(
            user=user,
            role=role,
            organization_id=organization_id,
        )
    except IntegrityError as exc:
        raise DomainValidationError(
            details={"assignment": ["This role is already assigned."]}
        ) from exc
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="identity.user_role.assign",
        entity_type="user_role",
        entity_id=assignment.id,
        after={
            "user_id": str(user.id),
            "role": role.code,
            "organization_id": str(organization_id) if organization_id else None,
        },
    )
    return assignment


@transaction.atomic
def remove_role(actor: User, assignment: UserRole) -> None:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    before = {"user_id": str(assignment.user_id), "role": assignment.role.code}
    assignment.delete()
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="identity.user_role.remove",
        entity_type="user_role",
        entity_id=assignment.id,
        before=before,
    )
