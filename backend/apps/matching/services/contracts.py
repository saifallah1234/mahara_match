from backend.apps.identity.models import RoleCode
from backend.apps.identity.services.contracts import PermissionDefinition


class MatchingPermissionCode:
    READ_OFFER_MATCHES = "matching.offer_match.read"


MATCHING_PERMISSIONS = (
    PermissionDefinition(MatchingPermissionCode.READ_OFFER_MATCHES, "matching.offer_match", "read"),
)

# PROPOSAL (G03): recruiters read matches for their organizations' offers.
# TODO(G03): candidates reading their own matches needs the user -> candidate profile link.
MATCHING_GRANTS: frozenset[tuple[str, str]] = frozenset(
    {
        (RoleCode.RECRUITER, MatchingPermissionCode.READ_OFFER_MATCHES),
        (RoleCode.ADMIN, MatchingPermissionCode.READ_OFFER_MATCHES),
    }
)
