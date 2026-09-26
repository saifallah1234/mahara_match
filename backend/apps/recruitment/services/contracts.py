from backend.apps.identity.models import RoleCode
from backend.apps.identity.services.contracts import PermissionDefinition


class RecruitmentPermissionCode:
    READ_OFFERS = "recruitment.offer.read"
    MANAGE_OFFERS = "recruitment.offer.manage"
    READ_APPLICATIONS = "recruitment.application.read"
    MANAGE_APPLICATIONS = "recruitment.application.manage"
    READ_INTERVIEWS = "recruitment.interview.read"
    MANAGE_INTERVIEWS = "recruitment.interview.manage"


RECRUITMENT_PERMISSIONS = (
    PermissionDefinition(RecruitmentPermissionCode.READ_OFFERS, "recruitment.offer", "read"),
    PermissionDefinition(RecruitmentPermissionCode.MANAGE_OFFERS, "recruitment.offer", "manage"),
    PermissionDefinition(
        RecruitmentPermissionCode.READ_APPLICATIONS, "recruitment.application", "read"
    ),
    PermissionDefinition(
        RecruitmentPermissionCode.MANAGE_APPLICATIONS, "recruitment.application", "manage"
    ),
    PermissionDefinition(
        RecruitmentPermissionCode.READ_INTERVIEWS, "recruitment.interview", "read"
    ),
    PermissionDefinition(
        RecruitmentPermissionCode.MANAGE_INTERVIEWS, "recruitment.interview", "manage"
    ),
)

# Personal application and interview reads belong to the receiving recruiter org.
RECRUITMENT_GRANTS: frozenset[tuple[str, str]] = frozenset(
    {
        (RoleCode.RECRUITER, RecruitmentPermissionCode.READ_OFFERS),
        (RoleCode.RECRUITER, RecruitmentPermissionCode.MANAGE_OFFERS),
        (RoleCode.RECRUITER, RecruitmentPermissionCode.READ_APPLICATIONS),
        (RoleCode.RECRUITER, RecruitmentPermissionCode.MANAGE_APPLICATIONS),
        (RoleCode.RECRUITER, RecruitmentPermissionCode.READ_INTERVIEWS),
        (RoleCode.RECRUITER, RecruitmentPermissionCode.MANAGE_INTERVIEWS),
        (RoleCode.ADMIN, RecruitmentPermissionCode.READ_OFFERS),
    }
)
