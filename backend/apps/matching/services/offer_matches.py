from uuid import UUID

from django.db.models import F, Q, QuerySet

from backend.apps.identity.models import RoleCode, User, UserRole
from backend.apps.matching.models import OfferMatch
from backend.apps.matching.services.contracts import MatchingPermissionCode
from backend.apps.recruitment.services.scope import organization_ids_with_permission
from backend.common.exceptions import DomainNotFoundError, DomainPermissionError


def list_offer_matches(actor: User) -> QuerySet[OfferMatch]:
    scope = organization_ids_with_permission(actor, MatchingPermissionCode.READ_OFFER_MATCHES)
    candidate = (
        actor.is_active
        and UserRole.objects.filter(user=actor, role__code=RoleCode.CANDIDATE).exists()
    )
    queryset = OfferMatch.objects.filter(offer__deleted_at__isnull=True)
    if scope is None:
        return queryset.order_by("-calculated_at", "id")
    if not candidate and not scope:
        raise DomainPermissionError()
    visibility = Q(
        offer__organization_id__in=scope,
        candidate__user__status="ACTIVE",
        offer__organization__verification_status="VERIFIED",
        offer__organization__deleted_at__isnull=True,
        candidate__applications__offer_id=F("offer_id"),
    )
    if candidate:
        visibility |= Q(candidate__user=actor)
    return queryset.filter(visibility).distinct().order_by("-calculated_at", "id")


def get_offer_match(actor: User, match_id: UUID | str) -> OfferMatch:
    try:
        match = list_offer_matches(actor).select_related("offer").get(id=match_id)
    except OfferMatch.DoesNotExist as exc:
        raise DomainNotFoundError("Offer match not found.") from exc
    return match
