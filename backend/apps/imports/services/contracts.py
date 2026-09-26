from backend.apps.identity.models import RoleCode
from backend.apps.identity.services.contracts import PermissionDefinition


class ImportsPermissionCode:
    MANAGE_SOURCES = "imports.source.manage"
    READ_RECORDS = "imports.record.read"


IMPORTS_PERMISSIONS = (
    PermissionDefinition(ImportsPermissionCode.MANAGE_SOURCES, "imports.source", "manage"),
    PermissionDefinition(ImportsPermissionCode.READ_RECORDS, "imports.record", "read"),
)

IMPORTS_GRANTS = frozenset(
    {
        (RoleCode.ADMIN, ImportsPermissionCode.MANAGE_SOURCES),
        (RoleCode.ADMIN, ImportsPermissionCode.READ_RECORDS),
    }
)
