from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.roles_serializers import RoleReadSerializer, RoleUpdateSerializer
from backend.apps.identity.models import Role
from backend.apps.identity.services import roles as role_services


class RoleViewSet(GenericViewSet[Role]):
    serializer_class = RoleReadSerializer
    queryset = Role.objects.none()

    def list(self, request: Request) -> Response:
        queryset = role_services.list_roles(request.user)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(RoleReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        return Response(RoleReadSerializer(role_services.get_role(request.user, pk)).data)

    @extend_schema(request=RoleUpdateSerializer, responses=RoleReadSerializer)
    def partial_update(self, request: Request, pk: UUID) -> Response:
        role = role_services.get_role(request.user, pk)
        serializer = RoleUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        role = role_services.update_role(request.user, role, serializer.validated_data)
        return Response(RoleReadSerializer(role).data)
