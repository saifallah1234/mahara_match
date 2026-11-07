# Placement: backend/apps/reporting/api/views.py
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.identity.api.common_permissions import IsActiveAuthenticated, active_request_user
from backend.apps.reporting.services.indicators import ministry_indicators


class IndicatorsView(APIView):
    permission_classes = (IsActiveAuthenticated,)

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request: Request) -> Response:
        return Response(ministry_indicators(active_request_user(request)))
