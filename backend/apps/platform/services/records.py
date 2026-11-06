from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from django.utils import timezone

from backend.apps.identity.models import User, UserStatus
from backend.apps.identity.services.access import require_permission
from backend.apps.platform.models import AuditLog, Notification
from backend.apps.platform.services.contracts import PlatformPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def list_notifications(actor: User) -> QuerySet[Notification]:
    return Notification.objects.filter(user=actor)


def get_notification(actor: User, notification_id: UUID | str) -> Notification:
    try:
        return list_notifications(actor).get(pk=notification_id)
    except Notification.DoesNotExist as exc:
        raise DomainNotFoundError("Notification not found.") from exc


def mark_read(actor: User, notification_id: UUID | str) -> Notification:
    notification = get_notification(actor, notification_id)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at", "updated_at"])
    return notification


def send_notification(user: User, **data: Any) -> Notification:
    """Trusted application-service entrypoint; delivery channels are a later phase."""
    return Notification.objects.create(user=user, **data)


def notify_role_holders(actor: User, organization_id: UUID, role_code: str, **data: Any) -> None:
    """Notify active holders of an organization role, except the user who made the change."""
    holders = (
        User.objects.filter(
            status=UserStatus.ACTIVE,
            deleted_at__isnull=True,
            role_assignments__organization_id=organization_id,
            role_assignments__role__code=role_code,
        )
        .exclude(pk=actor.pk)
        .distinct()
    )
    for holder in holders:
        send_notification(holder, **data)


def append_audit(
    *,
    actor_type: str,
    action: str,
    entity_type: str,
    entity_id: UUID,
    actor_user: User | None = None,
    agent_execution_id: UUID | None = None,
    before: Any = None,
    after: Any = None,
    ip_address: str | None = None,
) -> AuditLog:
    if (
        (actor_type == "USER" and (actor_user is None or agent_execution_id is not None))
        or (actor_type == "AGENT" and (agent_execution_id is None or actor_user is not None))
        or (actor_type == "SYSTEM" and (actor_user is not None or agent_execution_id is not None))
        or actor_type not in {"USER", "AGENT", "SYSTEM"}
    ):
        raise DomainValidationError(details={"actor_type": ["Actor attribution is required."]})
    return AuditLog.objects.create(
        actor_type=actor_type,
        actor_user=actor_user,
        agent_execution_id=agent_execution_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=before,
        after_json=after,
        ip_address=ip_address,
    )


def list_audit_logs(actor: User) -> QuerySet[AuditLog]:
    require_permission(actor, PlatformPermissionCode.READ_AUDIT)
    return AuditLog.objects.all()


def get_audit_log(actor: User, log_id: UUID | str) -> AuditLog:
    try:
        return list_audit_logs(actor).get(pk=log_id)
    except AuditLog.DoesNotExist as exc:
        raise DomainNotFoundError("Audit log not found.") from exc
