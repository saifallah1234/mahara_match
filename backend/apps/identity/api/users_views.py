from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.identity.api.users_serializers import (
    UserCreateSerializer,
    UserProfileUpdateSerializer,
    UserReadSerializer,
    UserStatusUpdateSerializer,
)
from backend.apps.identity.models import User
from backend.apps.identity.services import users as user_services


class UserViewSet(GenericViewSet[User]):
    serializer_class = UserReadSerializer
    queryset = User.objects.none()

    @extend_schema(responses=UserReadSerializer(many=True))
    def list(self, request: Request) -> Response:
        queryset = user_services.list_users(active_request_user(request))
        page = self.paginate_queryset(queryset)
        serializer = UserReadSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(request=UserCreateSerializer, responses={201: UserReadSerializer})
    def create(self, request: Request) -> Response:
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = user_services.create_user(active_request_user(request), serializer.validated_data)
        return Response(UserReadSerializer(user).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        user = user_services.get_user(active_request_user(request), pk)
        return Response(UserReadSerializer(user).data)

    @extend_schema(request=UserProfileUpdateSerializer, responses=UserReadSerializer)
    def update(self, request: Request, pk: UUID) -> Response:
        return self._update(request, pk, partial=False)

    @extend_schema(request=UserProfileUpdateSerializer, responses=UserReadSerializer)
    def partial_update(self, request: Request, pk: UUID) -> Response:
        return self._update(request, pk, partial=True)

    def _update(self, request: Request, pk: UUID, *, partial: bool) -> Response:
        actor = active_request_user(request)
        target = user_services.get_user(actor, pk)
        serializer = UserProfileUpdateSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = user_services.update_profile(actor, target, serializer.validated_data)
        return Response(UserReadSerializer(user).data)

    @extend_schema(
        description="Set an account status. Requires identity.user.manage.",
        request=UserStatusUpdateSerializer,
        responses=UserReadSerializer,
    )
    @action(detail=True, methods=("post",), url_path="status")
    def status(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        target = user_services.get_user(actor, pk)
        serializer = UserStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = user_services.update_status(actor, target, serializer.validated_data["status"])
        return Response(UserReadSerializer(user).data)

    @extend_schema(
        methods=("GET",),
        responses=UserReadSerializer,
    )
    @extend_schema(
        methods=("PUT", "PATCH"),
        request=UserProfileUpdateSerializer,
        responses=UserReadSerializer,
    )
    @extend_schema(
        methods=("DELETE",),
        description="Soft-delete the authenticated account and invalidate its credentials.",
        responses={204: None},
    )
    @action(detail=False, methods=("get", "put", "patch", "delete"), url_path="me")
    def me(self, request: Request) -> Response:
        actor = active_request_user(request)
        if request.method == "DELETE":
            user_services.delete_own_account(actor)
            return Response(status=status.HTTP_204_NO_CONTENT)
        user = user_services.get_own_profile(actor)
        if request.method == "GET":
            return Response(UserReadSerializer(user).data)
        serializer = UserProfileUpdateSerializer(
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        user = user_services.update_profile(actor, user, serializer.validated_data)
        return Response(UserReadSerializer(user).data)
