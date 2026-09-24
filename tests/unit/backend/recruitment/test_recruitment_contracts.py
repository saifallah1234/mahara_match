import pytest

from backend.apps.identity.models import RoleCode
from backend.apps.recruitment.services.contracts import (
    RECRUITMENT_GRANTS,
    RECRUITMENT_PERMISSIONS,
    RecruitmentPermissionCode,
)

pytestmark = pytest.mark.unit


def test_permission_codes_are_unique_and_namespaced() -> None:
    codes = [definition.code for definition in RECRUITMENT_PERMISSIONS]
    assert len(codes) == len(set(codes))
    assert all(code.startswith("recruitment.") for code in codes)


def test_every_grant_targets_a_defined_permission_and_known_role() -> None:
    defined = {definition.code for definition in RECRUITMENT_PERMISSIONS}
    known_roles = {RoleCode.RECRUITER, RoleCode.ADMIN}
    for role_code, permission_code in RECRUITMENT_GRANTS:
        assert permission_code in defined
        assert role_code in known_roles


def test_candidates_cannot_manage_or_read_recruiter_data() -> None:
    for code in (
        RecruitmentPermissionCode.MANAGE_OFFERS,
        RecruitmentPermissionCode.READ_APPLICATIONS,
        RecruitmentPermissionCode.READ_INTERVIEWS,
    ):
        assert (RoleCode.CANDIDATE, code) not in RECRUITMENT_GRANTS


def test_admin_has_no_access_to_personal_application_data_by_default() -> None:
    assert (RoleCode.ADMIN, RecruitmentPermissionCode.READ_APPLICATIONS) not in RECRUITMENT_GRANTS
    assert (RoleCode.ADMIN, RecruitmentPermissionCode.READ_INTERVIEWS) not in RECRUITMENT_GRANTS
