import pytest

from backend.apps.identity.models import RoleCode, User, UserStatus
from backend.apps.identity.services.contracts import (
    BASE_ROLE_NAMES,
    BASELINE_GRANTS,
    GLOBAL_ROLE_CODES,
    ORGANIZATION_ROLE_TYPES,
    IdentityPermissionCode,
)

pytestmark = pytest.mark.unit


def test_identity_email_is_normalized_case_insensitively() -> None:
    assert User.objects.normalize_identity_email("  Candidate@Example.COM ") == (
        "candidate@example.com"
    )


def test_only_active_status_is_authenticatable() -> None:
    assert User(email="active@example.com", status=UserStatus.ACTIVE).is_active is True
    assert User(email="pending@example.com", status=UserStatus.PENDING).is_active is False
    assert User(email="suspended@example.com", status=UserStatus.SUSPENDED).is_active is False
    assert User(email="disabled@example.com", status=UserStatus.DISABLED).is_active is False


def test_role_vocabulary_has_no_human_aneti_role() -> None:
    assert set(BASE_ROLE_NAMES) == {
        RoleCode.CANDIDATE,
        RoleCode.RECRUITER,
        RoleCode.TRAINING_MANAGER,
        RoleCode.MINISTRY_MANAGER,
        RoleCode.ADMIN,
    }
    assert "ANETI_AGENT" not in BASE_ROLE_NAMES


def test_role_scope_policy_is_explicit() -> None:
    assert GLOBAL_ROLE_CODES == {RoleCode.CANDIDATE, RoleCode.ADMIN}
    assert ORGANIZATION_ROLE_TYPES[RoleCode.RECRUITER] == {"COMPANY", "SUBSIDIARY"}
    assert ORGANIZATION_ROLE_TYPES[RoleCode.TRAINING_MANAGER] == {"TRAINING_PROVIDER"}
    assert ORGANIZATION_ROLE_TYPES[RoleCode.MINISTRY_MANAGER] == {"MINISTRY"}


def test_baseline_grants_cover_self_service_and_admin_management() -> None:
    for role_code in BASE_ROLE_NAMES:
        assert (role_code, IdentityPermissionCode.READ_SELF) in BASELINE_GRANTS
        assert (role_code, IdentityPermissionCode.UPDATE_SELF) in BASELINE_GRANTS
    assert (RoleCode.ADMIN, IdentityPermissionCode.MANAGE_USERS) in BASELINE_GRANTS
    assert (RoleCode.ADMIN, IdentityPermissionCode.MANAGE_RBAC) in BASELINE_GRANTS
