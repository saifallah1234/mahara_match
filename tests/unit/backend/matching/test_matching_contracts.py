import pytest

from backend.apps.identity.models import RoleCode
from backend.apps.matching.services.contracts import (
    MATCHING_GRANTS,
    MATCHING_PERMISSIONS,
    MatchingPermissionCode,
)

pytestmark = pytest.mark.unit


def test_permission_codes_are_unique_and_namespaced() -> None:
    codes = [definition.code for definition in MATCHING_PERMISSIONS]
    assert len(codes) == len(set(codes))
    assert all(code.startswith("matching.") for code in codes)


def test_grants_reference_the_defined_permission() -> None:
    assert {code for _, code in MATCHING_GRANTS} == {MatchingPermissionCode.READ_OFFER_MATCHES}


def test_candidates_are_not_granted_match_reads_until_g03_is_decided() -> None:
    assert (RoleCode.CANDIDATE, MatchingPermissionCode.READ_OFFER_MATCHES) not in MATCHING_GRANTS
