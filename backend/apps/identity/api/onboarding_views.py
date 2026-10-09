from typing import Any
from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.authentication_views import CSRF_PARAMETERS, _enforce_csrf
from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.identity.models import OnboardingRequest, RoleCode
from backend.apps.identity.services import onboarding


class RegistrationSerializer(serializers.Serializer[dict[str, Any]]):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    account_type = serializers.ChoiceField(
        choices=(RoleCode.CANDIDATE, RoleCode.RECRUITER, RoleCode.TRAINING_MANAGER)
    )
    organization_name = serializers.CharField(max_length=255, required=False)
    matricule_fiscal = serializers.RegexField(
        regex=r"^\d{7}[A-Z]\d{3}\d{2}$", max_length=13, required=False
    )


class RegistrationResultSerializer(serializers.Serializer[dict[str, Any]]):
    user_id = serializers.UUIDField()
    status = serializers.CharField()


class RegistrationView(APIView):
    authentication_classes: tuple[type, ...] = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        parameters=CSRF_PARAMETERS,
        request=RegistrationSerializer,
        responses={201: RegistrationResultSerializer},
    )
    def post(self, request: Request) -> Response:
        _enforce_csrf(request)
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = onboarding.register(serializer.validated_data)
        return Response({"user_id": user.id, "status": user.status}, status=status.HTTP_201_CREATED)


class OnboardingRequestReadSerializer(serializers.ModelSerializer[OnboardingRequest]):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = OnboardingRequest
        fields = (
            "id",
            "user",
            "email",
            "first_name",
            "last_name",
            "requested_role",
            "organization_name",
            "matricule_fiscal",
            "status",
            "organization",
            "created_at",
        )
        read_only_fields = fields


class ApprovalSerializer(serializers.Serializer[dict[str, Any]]):
    organization_id = serializers.UUIDField()


class OnboardingRequestViewSet(GenericViewSet[OnboardingRequest]):
    serializer_class = OnboardingRequestReadSerializer
    queryset = OnboardingRequest.objects.none()

    @extend_schema(responses=OnboardingRequestReadSerializer(many=True))
    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(onboarding.list_requests(active_request_user(request)))
        return self.get_paginated_response(OnboardingRequestReadSerializer(page, many=True).data)

    @extend_schema(request=ApprovalSerializer, responses=OnboardingRequestReadSerializer)
    def approve(self, request: Request, pk: UUID) -> Response:
        serializer = ApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = onboarding.approve(
            active_request_user(request), pk, serializer.validated_data["organization_id"]
        )
        return Response(OnboardingRequestReadSerializer(result).data)

    @extend_schema(request=None, responses=OnboardingRequestReadSerializer)
    def reject(self, request: Request, pk: UUID) -> Response:
        result = onboarding.reject(active_request_user(request), pk)
        return Response(OnboardingRequestReadSerializer(result).data)
