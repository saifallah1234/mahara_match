# Placement: backend/apps/reporting/services/contracts.py
from backend.apps.identity.models import RoleCode
from backend.apps.identity.services.contracts import PermissionDefinition


class ReportingPermissionCode:
    READ_INDICATORS = "reporting.indicators.read"


REPORTING_PERMISSIONS = (
    PermissionDefinition(ReportingPermissionCode.READ_INDICATORS, "reporting.indicators", "read"),
)

# MINISTRY_MANAGER can only be assigned within a MINISTRY organization, and its
# grants only take effect while that organization is verified (identity access rules).
REPORTING_GRANTS = frozenset(
    {
        (RoleCode.MINISTRY_MANAGER, ReportingPermissionCode.READ_INDICATORS),
        (RoleCode.ADMIN, ReportingPermissionCode.READ_INDICATORS),
    }
)
