from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import IsActiveAuthenticated, active_request_user
from backend.apps.matching.api.filters import OfferMatchFilters
from backend.apps.matching.api.offer_matches_serializers import OfferMatchReadSerializer
from backend.apps.matching.models import OfferMatch
from backend.apps.matching.services import offer_matches as match_services


class OfferMatchViewSet(GenericViewSet[OfferMatch]):
    """Read-only: scores and explanations are computed internally, never written by callers."""

    serializer_class = OfferMatchReadSerializer
    queryset = OfferMatch.objects.none()
    permission_classes = (IsActiveAuthenticated,)

    @extend_schema(parameters=[OfferMatchFilters], responses=OfferMatchReadSerializer(many=True))
    def list(self, request: Request) -> Response:
        queryset = match_services.list_offer_matches(active_request_user(request))
        queryset = OfferMatchFilters(data=request.query_params).apply(queryset)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(OfferMatchReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        match = match_services.get_offer_match(active_request_user(request), pk)
        return Response(OfferMatchReadSerializer(match).data)
