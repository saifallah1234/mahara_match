from rest_framework import serializers
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


class DocumentViewSet(GenericViewSet[Document]):
    serializer_class = DocumentReadSerializer
    queryset = Document.objects.none()

    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(documents.list_owned_documents(active_request_user(request)))
        return self.get_paginated_response(DocumentReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        document = documents.get_owned_document(active_request_user(request), str(pk))
        return Response(DocumentReadSerializer(document).data)
