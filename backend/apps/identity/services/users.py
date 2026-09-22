from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import IdentityPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def list_users(actor: User) -> QuerySet[User]:
    require_permission(actor, IdentityPermissionCode.MANAGE_USERS)
    return User.objects.prefetch_related("role_assignments__role").order_by("created_at", "id")


def get_user(actor: User, user_id: UUID | str) -> User:
    require_permission(actor, IdentityPermissionCode.MANAGE_USERS)
    try:
        return User.objects.prefetch_related("role_assignments__role").get(id=user_id)
    except User.DoesNotExist as exc:
        raise DomainNotFoundError("User not found.") from exc


def get_own_profile(actor: User) -> User:
    require_permission(actor, IdentityPermissionCode.READ_SELF)
    return User.objects.prefetch_related("role_assignments__role").get(id=actor.id)


def role_assignment_summaries(user: User) -> list[dict[str, Any]]:
    return [
        {
            "role_code": assignment.role.code,
            "organization_id": assignment.organization_id,
        }
        for assignment in user.role_assignments.select_related("role")
    ]


@transaction.atomic
def create_user(actor: User, data: Mapping[str, Any]) -> User:
    require_permission(actor, IdentityPermissionCode.MANAGE_USERS)
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
