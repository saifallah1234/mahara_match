from dataclasses import dataclass

from backend.apps.identity.models import RoleCode


class TrainingPermissionCode:
    VIEW_CATALOG = "training.catalog.view"
    MANAGE_PROGRAMS = "training.program.manage"
    MANAGE_SKILLS = "training.skill.manage"
    MANAGE_SESSIONS = "training.session.manage"
    ENROLL_SELF = "training.enrollment.enroll_self"
    VIEW_OWN_ENROLLMENTS = "training.enrollment.view_self"
    MANAGE_ENROLLMENTS = "training.enrollment.manage"
    VIEW_OWN_RECOMMENDATIONS = "training.recommendation.view_self"
    MANAGE_RECOMMENDATIONS = "training.recommendation.manage"


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    resource: str
    action: str


BASE_PERMISSIONS = (
    PermissionDefinition(TrainingPermissionCode.VIEW_CATALOG, "training.catalog", "view"),
    PermissionDefinition(TrainingPermissionCode.MANAGE_PROGRAMS, "training.program", "manage"),
    PermissionDefinition(TrainingPermissionCode.MANAGE_SKILLS, "training.skill", "manage"),
    PermissionDefinition(TrainingPermissionCode.MANAGE_SESSIONS, "training.session", "manage"),
    PermissionDefinition(TrainingPermissionCode.ENROLL_SELF, "training.enrollment", "enroll_self"),
    PermissionDefinition(
        TrainingPermissionCode.VIEW_OWN_ENROLLMENTS, "training.enrollment", "view_self"
    ),
    PermissionDefinition(
        TrainingPermissionCode.MANAGE_ENROLLMENTS, "training.enrollment", "manage"
    ),
    PermissionDefinition(
        TrainingPermissionCode.VIEW_OWN_RECOMMENDATIONS, "training.recommendation", "view_self"
    ),
    PermissionDefinition(
        TrainingPermissionCode.MANAGE_RECOMMENDATIONS, "training.recommendation", "manage"
    ),
)

# (role_code, permission_code) grants. Roles are owned/seeded by identity; this module
# only registers training permissions and grants them to roles that already exist.
BASELINE_GRANTS: frozenset[tuple[str, str]] = frozenset(
    {
        (RoleCode.CANDIDATE, TrainingPermissionCode.VIEW_CATALOG),
        (RoleCode.CANDIDATE, TrainingPermissionCode.ENROLL_SELF),
        (RoleCode.CANDIDATE, TrainingPermissionCode.VIEW_OWN_ENROLLMENTS),
        (RoleCode.CANDIDATE, TrainingPermissionCode.VIEW_OWN_RECOMMENDATIONS),
        (RoleCode.TRAINING_MANAGER, TrainingPermissionCode.VIEW_CATALOG),
        (RoleCode.TRAINING_MANAGER, TrainingPermissionCode.MANAGE_PROGRAMS),
        (RoleCode.TRAINING_MANAGER, TrainingPermissionCode.MANAGE_SKILLS),
        (RoleCode.TRAINING_MANAGER, TrainingPermissionCode.MANAGE_SESSIONS),
        (RoleCode.TRAINING_MANAGER, TrainingPermissionCode.MANAGE_ENROLLMENTS),
        (RoleCode.TRAINING_MANAGER, TrainingPermissionCode.MANAGE_RECOMMENDATIONS),
        (RoleCode.ADMIN, TrainingPermissionCode.VIEW_CATALOG),
        (RoleCode.ADMIN, TrainingPermissionCode.MANAGE_PROGRAMS),
        (RoleCode.ADMIN, TrainingPermissionCode.MANAGE_SKILLS),
        (RoleCode.ADMIN, TrainingPermissionCode.MANAGE_SESSIONS),
        (RoleCode.ADMIN, TrainingPermissionCode.MANAGE_ENROLLMENTS),
        (RoleCode.ADMIN, TrainingPermissionCode.MANAGE_RECOMMENDATIONS),
    }
)
