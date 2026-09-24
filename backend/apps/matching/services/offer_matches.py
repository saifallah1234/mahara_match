from uuid import UUID

from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import has_permission
from backend.apps.matching.models import OfferMatch
from backend.apps.matching.services.contracts import MatchingPermissionCode
from backend.apps.recruitment.services.scope import restrict_to_organizations
from backend.common.exceptions import DomainNotFoundError

# Read-only: scores, explanations and model versions are computed internally (P04-3).
# TODO(G03): candidates reading their own matches needs the user -> candidate link.


def list_offer_matches(actor: User) -> QuerySet[OfferMatch]:
    queryset = restrict_to_organizations(
        actor,
        OfferMatch.objects.all(),
        MatchingPermissionCode.READ_OFFER_MATCHES,
        "offer__organization_id",
    )
    return queryset.order_by("-calculated_at", "id")


def get_offer_match(actor: User, match_id: UUID | str) -> OfferMatch:
    try:
        match = OfferMatch.objects.select_related("offer").get(id=match_id)
    except OfferMatch.DoesNotExist as exc:
        raise DomainNotFoundError("Offer match not found.") from exc
    if not has_permission(
        actor, MatchingPermissionCode.READ_OFFER_MATCHES, match.offer.organization_id
    ):
        raise DomainNotFoundError("Offer match not found.")
    return match
