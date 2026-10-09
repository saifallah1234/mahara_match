from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.identity.api.user_roles_serializers import (
    UserRoleCreateSerializer,
    UserRoleReadSerializer,
)
from backend.apps.identity.models import UserRole
from backend.apps.identity.services import user_roles as user_role_services


class UserRoleViewSet(GenericViewSet[UserRole]):
    serializer_class = UserRoleReadSerializer
    queryset = UserRole.objects.none()

    def list(self, request: Request) -> Response:
        queryset = user_role_services.list_user_roles(active_request_user(request))
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(UserRoleReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        assignment = user_role_services.get_user_role(active_request_user(request), pk)
        return Response(UserRoleReadSerializer(assignment).data)

    @extend_schema(request=UserRoleCreateSerializer, responses={201: UserRoleReadSerializer})
    def create(self, request: Request) -> Response:
        serializer = UserRoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = user_role_services.assign_role(
            active_request_user(request), **serializer.validated_data
        )
        return Response(
            UserRoleReadSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        assignment = user_role_services.get_user_role(actor, pk)
        user_role_services.remove_role(actor, assignment)
        return Response(status=status.HTTP_204_NO_CONTENT)
