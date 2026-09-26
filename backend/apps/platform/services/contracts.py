from backend.apps.identity.models import RoleCode
from backend.apps.identity.services.contracts import PermissionDefinition


class PlatformPermissionCode:
    READ_AUDIT = "platform.audit.read"


PLATFORM_PERMISSIONS = (
    PermissionDefinition(PlatformPermissionCode.READ_AUDIT, "platform.audit", "read"),
)

PLATFORM_GRANTS = frozenset({(RoleCode.ADMIN, PlatformPermissionCode.READ_AUDIT)})
