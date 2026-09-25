import pytest

from backend.apps.identity.models import RoleCode
from backend.apps.training.services.contracts import (
    BASE_PERMISSIONS,
    BASELINE_GRANTS,
    TrainingPermissionCode,
)

pytestmark = pytest.mark.unit


def test_every_permission_code_has_a_definition() -> None:
    defined_codes = {definition.code for definition in BASE_PERMISSIONS}
    assert defined_codes == {
        TrainingPermissionCode.VIEW_CATALOG,
        TrainingPermissionCode.MANAGE_PROGRAMS,
        TrainingPermissionCode.MANAGE_SKILLS,
        TrainingPermissionCode.MANAGE_SESSIONS,
        TrainingPermissionCode.ENROLL_SELF,
        TrainingPermissionCode.VIEW_OWN_ENROLLMENTS,
        TrainingPermissionCode.MANAGE_ENROLLMENTS,
        TrainingPermissionCode.VIEW_OWN_RECOMMENDATIONS,
        TrainingPermissionCode.MANAGE_RECOMMENDATIONS,
    }


def test_every_grant_targets_a_defined_permission() -> None:
    defined_codes = {definition.code for definition in BASE_PERMISSIONS}
    for _, permission_code in BASELINE_GRANTS:
        assert permission_code in defined_codes


def test_candidate_can_browse_and_self_manage_only() -> None:
    candidate_grants = {code for role, code in BASELINE_GRANTS if role == RoleCode.CANDIDATE}
    assert candidate_grants == {
        TrainingPermissionCode.VIEW_CATALOG,
        TrainingPermissionCode.ENROLL_SELF,
        TrainingPermissionCode.VIEW_OWN_ENROLLMENTS,
        TrainingPermissionCode.VIEW_OWN_RECOMMENDATIONS,
    }
    assert TrainingPermissionCode.MANAGE_PROGRAMS not in candidate_grants
    assert TrainingPermissionCode.MANAGE_ENROLLMENTS not in candidate_grants


def test_training_manager_can_manage_the_full_catalog() -> None:
    manager_grants = {code for role, code in BASELINE_GRANTS if role == RoleCode.TRAINING_MANAGER}
    assert manager_grants == {
        TrainingPermissionCode.VIEW_CATALOG,
        TrainingPermissionCode.MANAGE_PROGRAMS,
        TrainingPermissionCode.MANAGE_SKILLS,
        TrainingPermissionCode.MANAGE_SESSIONS,
        TrainingPermissionCode.MANAGE_ENROLLMENTS,
        TrainingPermissionCode.MANAGE_RECOMMENDATIONS,
    }
    assert TrainingPermissionCode.ENROLL_SELF not in manager_grants


def test_admin_has_the_same_management_reach_as_training_manager() -> None:
    admin_grants = {code for role, code in BASELINE_GRANTS if role == RoleCode.ADMIN}
    manager_grants = {code for role, code in BASELINE_GRANTS if role == RoleCode.TRAINING_MANAGER}
    assert admin_grants == manager_grants
