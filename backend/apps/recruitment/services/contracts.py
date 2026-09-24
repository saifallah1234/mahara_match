from backend.apps.identity.models import RoleCode
from backend.apps.identity.services.contracts import PermissionDefinition


class RecruitmentPermissionCode:
    READ_OFFERS = "recruitment.offer.read"
    MANAGE_OFFERS = "recruitment.offer.manage"
    READ_APPLICATIONS = "recruitment.application.read"
    READ_INTERVIEWS = "recruitment.interview.read"


RECRUITMENT_PERMISSIONS = (
    PermissionDefinition(RecruitmentPermissionCode.READ_OFFERS, "recruitment.offer", "read"),
    PermissionDefinition(RecruitmentPermissionCode.MANAGE_OFFERS, "recruitment.offer", "manage"),
    PermissionDefinition(
        RecruitmentPermissionCode.READ_APPLICATIONS, "recruitment.application", "read"
    ),
    PermissionDefinition(
        RecruitmentPermissionCode.READ_INTERVIEWS, "recruitment.interview", "read"
    ),
)

# PROPOSAL (G03 not decided): who gets which permission. P1 must merge these into the
# identity seeding (bootstrap.py) once the team agrees. Application and interview data
# is personal, so admins are not granted read access here until Q19 is decided.
RECRUITMENT_GRANTS: frozenset[tuple[str, str]] = frozenset(
    {
        (RoleCode.RECRUITER, RecruitmentPermissionCode.READ_OFFERS),
        (RoleCode.RECRUITER, RecruitmentPermissionCode.MANAGE_OFFERS),
        (RoleCode.RECRUITER, RecruitmentPermissionCode.READ_APPLICATIONS),
        (RoleCode.RECRUITER, RecruitmentPermissionCode.READ_INTERVIEWS),
        (RoleCode.ADMIN, RecruitmentPermissionCode.READ_OFFERS),
    }
)
