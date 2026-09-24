from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class EnrollmentPermissions(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        is_staff = getattr(user, "is_staff", False)
        if is_staff:
            return True

        user_candidate_id = getattr(user, "candidate_id", None)
        obj_candidate_id = getattr(obj, "candidate_id", None)

        if user_candidate_id is None or obj_candidate_id is None:
            return False

        return str(obj_candidate_id) == str(user_candidate_id)
