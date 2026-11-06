from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from backend.apps.candidates.models import CV
from backend.apps.candidates.services.records import get_record, own_profile, purge_cv_bytes
from backend.apps.documents.services.documents import DocumentStorageError
from backend.apps.identity.models import RoleCode, User
from backend.apps.identity.services.access import require_permission
from backend.apps.platform.services.records import (
    append_audit,
    notify_role_holders,
    send_notification,
)
from backend.apps.recruitment.models import (
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
    JobOffer,
    JobOfferStatus,
)
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.common.exceptions import (
    DomainNotFoundError,
    DomainPermissionError,
    DomainValidationError,
)

_PROGRESSION = (
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.PRESELECTED,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.OFFERED,
    ApplicationStatus.HIRED,
)
_TERMINAL = {ApplicationStatus.HIRED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN}


def _valid_recruiter_transition(current: str, target: str) -> bool:
    return target == ApplicationStatus.REJECTED or (
        current in _PROGRESSION
        and target in _PROGRESSION
        and _PROGRESSION.index(target) > _PROGRESSION.index(current)
    )


@transaction.atomic
def submit_application(actor: User, data: Mapping[str, Any]) -> Application:
    candidate = own_profile(actor)
    cv_id = get_record(actor, CV, data["cv_id"]).pk
    try:
        cv = CV.objects.select_for_update().get(pk=cv_id, deleted_at__isnull=True)
    except CV.DoesNotExist as exc:
        raise DomainNotFoundError("CV not found.") from exc
    try:
        offer = JobOffer.objects.select_for_update().get(
            id=data["offer_id"], deleted_at__isnull=True, status=JobOfferStatus.PUBLISHED
        )
    except JobOffer.DoesNotExist as exc:
        raise DomainNotFoundError("Published offer not found.") from exc
    if not offer.easy_apply:
        raise DomainValidationError(
            details={"offer_id": ["This offer uses external applications."]}
        )
    if offer.organization.deleted_at or offer.organization.verification_status != "VERIFIED":
        raise DomainNotFoundError("Published offer not found.")
    if offer.application_deadline and offer.application_deadline < timezone.localdate():
        raise DomainValidationError(details={"offer_id": ["Application deadline has passed."]})
    try:
        application = Application.objects.create(
            candidate=candidate,
            offer=offer,
            cv=cv,
            cover_letter=data.get("cover_letter", ""),
            status=ApplicationStatus.SUBMITTED,
            applied_at=timezone.now(),
        )
    except IntegrityError as exc:
        raise DomainValidationError(
            details={"offer_id": ["You have already applied to this offer."]}
        ) from exc
    ApplicationStatusHistory.objects.create(application=application, status=application.status)
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="recruitment.application.submit",
        entity_type="application",
        entity_id=application.id,
        after={"status": application.status, "offer_id": str(offer.id)},
    )
    notify_role_holders(
        actor,
        offer.organization_id,
        RoleCode.RECRUITER,
        type="recruitment.application.submitted",
        title="Nouvelle candidature",
        body=f"Une candidature a été déposée pour « {offer.title} ».",
        payload_json={"application_id": str(application.id), "offer_id": str(offer.id)},
    )
    return application


@transaction.atomic
def transition_application(
    actor: User, application_id: UUID, target: str, reason: str = ""
) -> Application:
    try:
        application = (
            Application.objects.select_for_update()
            .select_related("candidate__user", "offer__organization")
            .get(id=application_id)
        )
    except Application.DoesNotExist as exc:
        raise DomainNotFoundError("Application not found.") from exc
    if target == ApplicationStatus.WITHDRAWN:
        if own_profile(actor).id != application.candidate_id:
            raise DomainNotFoundError("Application not found.")
    else:
        require_permission(
            actor, RecruitmentPermissionCode.MANAGE_APPLICATIONS, application.offer.organization_id
        )
        if application.candidate.user_id == actor.id:
            raise DomainPermissionError("You cannot review your own application.")
        if (
            application.offer.organization.deleted_at
            or application.offer.organization.verification_status != "VERIFIED"
            or not application.candidate.user.is_active
        ):
            raise DomainPermissionError()
    if application.status in _TERMINAL:
        raise DomainValidationError(details={"status": ["This application is final."]})
    if target == ApplicationStatus.WITHDRAWN:
        application.withdrawn_at = timezone.now()
    else:
        if not _valid_recruiter_transition(application.status, target):
            raise DomainValidationError(details={"status": ["Invalid application transition."]})
    previous_status = application.status
    application.status = target
    application.save(update_fields=["status", "withdrawn_at", "updated_at"])
    ApplicationStatusHistory.objects.create(application=application, status=target, reason=reason)
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="recruitment.application.transition",
        entity_type="application",
        entity_id=application.id,
        before={"status": previous_status},
        after={"status": target},
    )
    payload = {"application_id": str(application.id), "status": target}
    if target == ApplicationStatus.WITHDRAWN:
        notify_role_holders(
            actor,
            application.offer.organization_id,
            RoleCode.RECRUITER,
            type="recruitment.application.withdrawn",
            title="Candidature retirée",
            body=f"Le candidat a retiré sa candidature à « {application.offer.title} ».",
            payload_json=payload,
        )
    else:
        send_notification(
            application.candidate.user,
            type="recruitment.application.status_changed",
            title="Candidature mise à jour",
            body=f"Le statut de votre candidature à « {application.offer.title} » a changé.",
            payload_json=payload,
        )
    if target == ApplicationStatus.REJECTED:
        try:
            purge_cv_bytes(application.cv_id)
        except DocumentStorageError:
            pass  # The daily purge command retries storage failures.
    return application
