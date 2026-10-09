from typing import Any

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
    TokenVerifySerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

from backend.apps.identity.models import User, UserStatus


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    @transaction.atomic
    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:
        email = User.objects.normalize_identity_email(str(attrs.get(self.username_field, "")))
        User.objects.select_for_update().filter(email__iexact=email).first()
        return super().validate(attrs)


class ActiveTokenRefreshSerializer(TokenRefreshSerializer):
    @transaction.atomic
    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:
        refresh = RefreshToken(attrs["refresh"])
        user_id = refresh.get(api_settings.USER_ID_CLAIM)
        user = User.objects.select_for_update().filter(id=user_id).first()
        if user is None or not user.is_active:
            raise AuthenticationFailed("The account is not active.", code="account_inactive")
        return super().validate(attrs)


class ActiveTokenVerifySerializer(TokenVerifySerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[Any, Any]:
        data = super().validate(attrs)
        token = UntypedToken(attrs["token"])
        if not User.objects.filter(
            id=token.get(api_settings.USER_ID_CLAIM),
            status=UserStatus.ACTIVE,
            deleted_at__isnull=True,
        ).exists():
            raise AuthenticationFailed("The account is not active.", code="account_inactive")
        return data


class AccessTokenSerializer(serializers.Serializer[dict[str, Any]]):
    access = serializers.CharField(read_only=True)
