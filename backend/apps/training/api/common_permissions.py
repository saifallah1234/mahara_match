from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class IsTrainingAdminOrManager(BasePermission):
    """Base permission checking standard RBAC/tenant access for Training module operations."""

    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        is_staff = getattr(user, "is_staff", False)
        is_training_manager = getattr(user, "is_training_manager", False)

        return bool(is_staff or is_training_manager)
