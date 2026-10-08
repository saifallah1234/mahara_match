from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from backend.apps.identity.api.authentication_views import (
    ActiveTokenVerifyView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CsrfCookieView,
    LogoutView,
)
from backend.apps.identity.api.organization_members_views import (
    OrganizationMemberViewSet,
)
from backend.apps.identity.api.organizations_views import OrganizationViewSet
from backend.apps.identity.api.permissions_views import PermissionViewSet
from backend.apps.identity.api.role_permissions_views import RolePermissionViewSet
from backend.apps.identity.api.roles_views import RoleViewSet
from backend.apps.identity.api.user_roles_views import UserRoleViewSet
from backend.apps.identity.api.users_views import UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("user-roles", UserRoleViewSet, basename="user-role")
router.register("role-permissions", RolePermissionViewSet, basename="role-permission")
router.register("organizations", OrganizationViewSet, basename="organization")

urlpatterns = [
    path("auth/csrf/", CsrfCookieView.as_view(), name="csrf-cookie"),
    path("auth/token/", CookieTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", CookieTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", ActiveTokenVerifyView.as_view(), name="token-verify"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("", include(router.urls)),
    path(
        "organizations/<uuid:organization_id>/members/",
        OrganizationMemberViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="organization-member-list",
    ),
    path(
        "organizations/<uuid:organization_id>/members/<uuid:user_id>/",
        OrganizationMemberViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="organization-member-detail",
    ),
]
