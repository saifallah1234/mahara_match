from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from backend.apps.documents.models import Document
from backend.apps.identity.models import User
from backend.common.exceptions import DomainNotFoundError


def list_owned_documents(actor: User) -> QuerySet[Document]:
    return Document.objects.filter(owner_user=actor)


def get_owned_document(actor: User, document_id: UUID | str) -> Document:
    try:
        return list_owned_documents(actor).get(id=document_id)
    except Document.DoesNotExist as exc:
        raise DomainNotFoundError("Document not found.") from exc


def create_document(owner: User, data: Mapping[str, Any]) -> Document:
    """Trusted storage service entrypoint; no public metadata creation route."""
    return Document.objects.create(owner_user=owner, **data)
