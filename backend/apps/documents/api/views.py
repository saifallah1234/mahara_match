from io import BytesIO

from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.documents.models import Document
from backend.apps.documents.services import documents
from backend.apps.identity.api.common_permissions import active_request_user


class DocumentReadSerializer(serializers.ModelSerializer[Document]):
    class Meta:
        model = Document
        fields = (
            "id",
            "type",
            "file_name",
            "mime_type",
            "size_bytes",
            "checksum",
            "scan_status",
            "uploaded_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer[dict[str, object]]):
    file = serializers.FileField(
        write_only=True, help_text="A PDF, JPEG or PNG file no larger than 10 MiB."
    )
    type = serializers.CharField(
        max_length=30,
        write_only=True,
        help_text="Uppercase document type using letters, numbers and underscores.",
    )


class DocumentViewSet(GenericViewSet[Document]):
    serializer_class = DocumentReadSerializer
    queryset = Document.objects.none()
    parser_classes = (MultiPartParser,)

    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(documents.list_owned_documents(active_request_user(request)))
        return self.get_paginated_response(DocumentReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        document = documents.get_owned_document(active_request_user(request), str(pk))
        return Response(DocumentReadSerializer(document).data)

    @extend_schema(
        description="Upload an owner-scoped document to private object storage.",
        request=DocumentUploadSerializer,
        responses={201: DocumentReadSerializer},
    )
    def create(self, request: Request) -> Response:
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = documents.upload_document(
            active_request_user(request),
            serializer.validated_data["file"],
            serializer.validated_data["type"],
        )
        return Response(DocumentReadSerializer(document).data, status=201)

    @extend_schema(
        description="Download an owned document through the authenticated backend.",
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
    )
    @action(detail=True, methods=("get",), url_path="download")
    def download(self, request: Request, pk: str | None = None) -> FileResponse:
        document, content = documents.download_owned_document(active_request_user(request), str(pk))
        response = FileResponse(
            BytesIO(content),
            as_attachment=True,
            filename=document.file_name,
            content_type=document.mime_type,
        )
        response["Content-Length"] = str(document.size_bytes)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
