from typing import Any

from django.conf import settings
from django.middleware.csrf import get_token
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from backend.apps.identity.api.authentication_serializers import (
    AccessTokenSerializer,
    EmailTokenObtainPairSerializer,
)

CSRF_PARAMETERS = [
    OpenApiParameter(
        name="X-CSRFToken",
        type=str,
        location=OpenApiParameter.HEADER,
        required=True,
        description="Value from Django's csrftoken cookie.",
    ),
    OpenApiParameter(
        name="csrftoken",
        type=str,
        location=OpenApiParameter.COOKIE,
        required=True,
        description="CSRF cookie issued by GET /api/v1/auth/csrf/.",
    ),
]
REFRESH_COOKIE_PARAMETER = OpenApiParameter(
    name="mahara_refresh",
    type=str,
    location=OpenApiParameter.COOKIE,
    required=True,
    description="HttpOnly refresh credential.",
)


def _enforce_csrf(request: Request) -> None:
    SessionAuthentication().enforce_csrf(request)


def _set_refresh_cookie(response: Response, refresh: str) -> None:
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh,
        max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


class CsrfCookieView(APIView):
    authentication_classes: tuple[type, ...] = ()
    permission_classes: tuple[type, ...] = ()

    @extend_schema(
        description="Issue Django's readable CSRF cookie for browser authentication requests.",
        responses={204: None},
    )
    def get(self, request: Request) -> Response:
        get_token(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CookieTokenObtainPairView(TokenObtainPairView):
    @extend_schema(
        description="Return an access token and set the rotating refresh token as an HttpOnly cookie.",
        parameters=CSRF_PARAMETERS,
        request=EmailTokenObtainPairSerializer,
        responses=AccessTokenSerializer,
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        _enforce_csrf(request)
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc

        data = dict(serializer.validated_data)
        refresh = data.pop("refresh")
        response = Response(data, status=status.HTTP_200_OK)
        _set_refresh_cookie(response, refresh)
        return response


class CookieTokenRefreshView(TokenRefreshView):
    @extend_schema(
        description="Rotate the refresh cookie and return a new access token.",
        parameters=[*CSRF_PARAMETERS, REFRESH_COOKIE_PARAMETER],
        request=None,
        responses=AccessTokenSerializer,
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        _enforce_csrf(request)
        refresh = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if not refresh:
            raise AuthenticationFailed("Refresh cookie is required.", code="refresh_cookie_missing")

        serializer = self.get_serializer(data={"refresh": refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc

        data = dict(serializer.validated_data)
        rotated_refresh = data.pop("refresh", refresh)
        response = Response(data, status=status.HTTP_200_OK)
        _set_refresh_cookie(response, rotated_refresh)
        return response


class ActiveTokenVerifyView(TokenVerifyView):
    @extend_schema(description="Verify a JWT and require its user account to remain active.")
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        description="Blacklist the refresh cookie when present, then clear it.",
        parameters=CSRF_PARAMETERS,
        request=None,
        responses={204: None},
    )
    def post(self, request: Request) -> Response:
        _enforce_csrf(request)
        refresh = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if refresh:
            try:
                token = RefreshToken(refresh)  # type: ignore[arg-type]
                if str(token.get(api_settings.USER_ID_CLAIM)) == str(request.user.id):
                    token.blacklist()
            except TokenError:
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response
