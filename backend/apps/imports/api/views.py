from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.imports.api.serializers import (
    BatchReadSerializer,
    RowReadSerializer,
    SourceAuthorizationSerializer,
    SourceReadSerializer,
    SourceWriteSerializer,
)
from backend.apps.imports.models import DataSource, ImportBatch, ImportRow
from backend.apps.imports.services import records


class SourceViewSet(GenericViewSet[DataSource]):
    serializer_class = SourceReadSerializer
    queryset = DataSource.objects.none()

    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(records.list_sources(active_request_user(request)))
        return self.get_paginated_response(SourceReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        return Response(
            SourceReadSerializer(records.get_source(active_request_user(request), pk)).data
        )

    @extend_schema(request=SourceWriteSerializer, responses={201: SourceReadSerializer})
    def create(self, request: Request) -> Response:
        serializer = SourceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = records.create_source(active_request_user(request), serializer.validated_data)
        return Response(SourceReadSerializer(source).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=SourceWriteSerializer, responses=SourceReadSerializer)
    def partial_update(self, request: Request, pk: UUID) -> Response:
        serializer = SourceWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        source = records.update_source(active_request_user(request), pk, serializer.validated_data)
        return Response(SourceReadSerializer(source).data)

    @extend_schema(request=SourceAuthorizationSerializer, responses=SourceReadSerializer)
    @action(detail=True, methods=["post"])
    def authorize(self, request: Request, pk: UUID) -> Response:
        serializer = SourceAuthorizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = records.authorize_source(
            active_request_user(request), pk, **serializer.validated_data
        )
        return Response(SourceReadSerializer(source).data)

    @extend_schema(request=None, responses=SourceReadSerializer)
    @action(detail=True, methods=["post"])
    def revoke(self, request: Request, pk: UUID) -> Response:
        return Response(
            SourceReadSerializer(records.revoke_source(active_request_user(request), pk)).data
        )


class BatchViewSet(GenericViewSet[ImportBatch]):
    serializer_class = BatchReadSerializer
    queryset = ImportBatch.objects.none()

    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(records.list_batches(active_request_user(request)))
        return self.get_paginated_response(BatchReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        return Response(
            BatchReadSerializer(records.get_batch(active_request_user(request), pk)).data
        )


class RowViewSet(GenericViewSet[ImportRow]):
    serializer_class = RowReadSerializer
    queryset = ImportRow.objects.none()

    def list(self, request: Request, batch_id: UUID) -> Response:
        page = self.paginate_queryset(records.list_rows(active_request_user(request), batch_id))
        return self.get_paginated_response(RowReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        return Response(RowReadSerializer(records.get_row(active_request_user(request), pk)).data)
