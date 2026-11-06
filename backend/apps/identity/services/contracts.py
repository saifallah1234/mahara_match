from dataclasses import dataclass

from backend.apps.identity.models import RoleCode


class IdentityPermissionCode:
    READ_SELF = "identity.user.read_self"
    UPDATE_SELF = "identity.user.update_self"
    MANAGE_USERS = "identity.user.manage"
    MANAGE_RBAC = "identity.rbac.manage"
    MANAGE_ORGANIZATIONS = "identity.organization.manage"
    READ_ORGANIZATION_MEMBERS = "identity.organization.read_members"


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    resource: str
    action: str


BASE_PERMISSIONS = (
    PermissionDefinition(IdentityPermissionCode.READ_SELF, "identity.user", "read_self"),
    PermissionDefinition(IdentityPermissionCode.UPDATE_SELF, "identity.user", "update_self"),
    PermissionDefinition(IdentityPermissionCode.MANAGE_USERS, "identity.user", "manage"),
    PermissionDefinition(IdentityPermissionCode.MANAGE_RBAC, "identity.rbac", "manage"),
    PermissionDefinition(
        IdentityPermissionCode.MANAGE_ORGANIZATIONS, "identity.organization", "manage"
    ),
    PermissionDefinition(
        IdentityPermissionCode.READ_ORGANIZATION_MEMBERS,
        "identity.organization",
        "read_members",
    ),
)

BASE_ROLE_NAMES: dict[str, str] = {
    RoleCode.CANDIDATE: "Candidate",
    RoleCode.RECRUITER: "Recruiter",
    RoleCode.TRAINING_MANAGER: "Training manager",
    RoleCode.MINISTRY_MANAGER: "Ministry manager",
    RoleCode.ADMIN: "Administrator",
}

GLOBAL_ROLE_CODES: frozenset[str] = frozenset({RoleCode.CANDIDATE, RoleCode.ADMIN})
ORGANIZATION_ROLE_TYPES: dict[str, frozenset[str]] = {
    RoleCode.RECRUITER: frozenset({"COMPANY", "SUBSIDIARY"}),
    RoleCode.TRAINING_MANAGER: frozenset({"TRAINING_PROVIDER"}),
    RoleCode.MINISTRY_MANAGER: frozenset({"MINISTRY"}),
}

BASELINE_GRANTS: frozenset[tuple[str, str]] = frozenset(
    (role_code, permission_code)
    for role_code in BASE_ROLE_NAMES
    for permission_code in (
        IdentityPermissionCode.READ_SELF,
        IdentityPermissionCode.UPDATE_SELF,
    )
) | frozenset(
    {
        (RoleCode.ADMIN, IdentityPermissionCode.MANAGE_USERS),
        (RoleCode.ADMIN, IdentityPermissionCode.MANAGE_RBAC),
        (RoleCode.ADMIN, IdentityPermissionCode.MANAGE_ORGANIZATIONS),
        (RoleCode.RECRUITER, IdentityPermissionCode.READ_ORGANIZATION_MEMBERS),
        (RoleCode.TRAINING_MANAGER, IdentityPermissionCode.READ_ORGANIZATION_MEMBERS),
    }
)
