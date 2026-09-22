from typing import cast

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from backend.apps.identity.models import User


class IsActiveAuthenticated(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_active", False)
        )


def active_request_user(request: Request) -> User:
    """Narrow DRF's User | AnonymousUser after IsActiveAuthenticated has run."""
    return cast(User, request.user)
