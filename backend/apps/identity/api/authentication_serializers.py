from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

from backend.apps.identity.models import User, UserStatus


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD


class ActiveTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:
        refresh = RefreshToken(attrs["refresh"])
        user_id = refresh.get("user_id")
        if not User.objects.filter(id=user_id, status=UserStatus.ACTIVE).exists():
            raise AuthenticationFailed("The account is not active.", code="account_inactive")
        return super().validate(attrs)


class LogoutSerializer(serializers.Serializer[dict[str, Any]]):
    refresh = serializers.CharField(write_only=True)
