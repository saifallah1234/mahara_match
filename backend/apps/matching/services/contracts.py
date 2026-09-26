from backend.apps.identity.models import RoleCode
from backend.apps.identity.services.contracts import PermissionDefinition


class MatchingPermissionCode:
    READ_OFFER_MATCHES = "matching.offer_match.read"


MATCHING_PERMISSIONS = (
    PermissionDefinition(MatchingPermissionCode.READ_OFFER_MATCHES, "matching.offer_match", "read"),
)

MATCHING_GRANTS: frozenset[tuple[str, str]] = frozenset(
    {
        (RoleCode.RECRUITER, MatchingPermissionCode.READ_OFFER_MATCHES),
    }
)
