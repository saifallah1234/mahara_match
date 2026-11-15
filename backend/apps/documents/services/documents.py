import re
from collections.abc import Callable, Mapping
from hashlib import sha256
from hmac import compare_digest
from pathlib import PurePath
from typing import Any
from uuid import UUID, uuid4

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db.models import QuerySet
from django.utils import timezone

from backend.apps.documents.models import Document
from backend.apps.identity.models import User
from backend.common.exceptions import DomainError, DomainNotFoundError, DomainValidationError
from backend.common.storage import object_storage

ALLOWED_FILE_TYPES: dict[str, tuple[tuple[str, ...], Callable[[bytes], bool]]] = {
    "application/pdf": ((".pdf",), lambda content: content.startswith(b"%PDF-")),
    "image/jpeg": ((".jpg", ".jpeg"), lambda content: content.startswith(b"\xff\xd8\xff")),
    "image/png": ((".png",), lambda content: content.startswith(b"\x89PNG\r\n\x1a\n")),
    # DOCX CVs for ATS analysis; .docx is a ZIP container and cannot carry macros (.docm).
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        (".docx",),
        lambda content: content.startswith(b"PK\x03\x04"),
    ),
}
DOCUMENT_TYPE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,29}$")


class DocumentStorageError(DomainError):
    code = "document_storage_error"
    status_code = 503
    default_message = "Document storage is temporarily unavailable."


def list_owned_documents(actor: User) -> QuerySet[Document]:
    return (
        Document.objects.filter(owner_user=actor)
        .exclude(cv__deleted_at__isnull=False)
        .exclude(type__startswith="INTERVIEW_")
    )


def get_owned_document(actor: User, document_id: UUID | str) -> Document:
    try:
        return list_owned_documents(actor).get(id=document_id)
    except Document.DoesNotExist as exc:
        raise DomainNotFoundError("Document not found.") from exc


def create_document(owner: User, data: Mapping[str, Any]) -> Document:
    """Trusted metadata creation entrypoint."""
    return Document.objects.create(owner_user=owner, **data)


def _validate_filename(file_name: str, mime_type: str) -> None:
    if (
        not file_name
        or len(file_name) > 255
        or PurePath(file_name).name != file_name
        or "/" in file_name
        or "\\" in file_name
        or any(ord(character) < 32 for character in file_name)
    ):
        raise DomainValidationError(details={"file": ["Use a valid filename."]})

    extensions = ALLOWED_FILE_TYPES[mime_type][0]
    if not file_name.casefold().endswith(extensions):
        raise DomainValidationError(
            details={"file": ["Filename extension does not match file type."]}
        )


def _read_upload(upload: UploadedFile) -> tuple[bytes, str, str]:
    mime_type = (upload.content_type or "").partition(";")[0].strip().casefold()
    if mime_type not in ALLOWED_FILE_TYPES:
        raise DomainValidationError(details={"file": ["Only PDF, JPEG and PNG files are allowed."]})
    file_name = upload.name or ""
    _validate_filename(file_name, mime_type)

    content = bytearray()
    for chunk in upload.chunks():
        content.extend(chunk)
        if len(content) > settings.DOCUMENT_MAX_UPLOAD_BYTES:
            raise DomainValidationError(details={"file": ["File is too large."]})
    if not content:
        raise DomainValidationError(details={"file": ["File cannot be empty."]})
    if not ALLOWED_FILE_TYPES[mime_type][1](content):
        raise DomainValidationError(details={"file": ["File content does not match its type."]})
    return bytes(content), mime_type, file_name


def upload_document(owner: User, upload: UploadedFile, document_type: str) -> Document:
    if document_type.startswith("INTERVIEW_"):
        raise DomainValidationError(
            details={"type": ["Interview media uses the protected interview API."]}
        )
    if not DOCUMENT_TYPE_PATTERN.fullmatch(document_type):
        raise DomainValidationError(
            details={"type": ["Use an uppercase type containing letters, numbers or underscores."]}
        )
    content, mime_type, file_name = _read_upload(upload)
    document_id = uuid4()
    object_key = f"documents/{owner.id}/{document_id}"

    try:
        object_storage.upload_object(object_key, content, mime_type)
    except Exception as exc:
        raise DocumentStorageError() from exc

    try:
        return create_document(
            owner,
            {
                "id": document_id,
                "type": document_type,
                "storage_uri": object_key,
                "file_name": file_name,
                "mime_type": mime_type,
                "size_bytes": len(content),
                "checksum": sha256(content).hexdigest(),
                "scan_status": "PENDING",
                "uploaded_at": timezone.now(),
            },
        )
    except Exception:
        # ponytail: cleanup is best effort; add an orphan reconciler if failures are observed.
        try:
            object_storage.delete_object(object_key)
        except Exception:
            pass
        raise


def download_document(document: Document) -> tuple[Document, bytes]:
    try:
        content = object_storage.download_object(document.storage_uri)
        if len(content) != document.size_bytes or not compare_digest(
            sha256(content).hexdigest(), document.checksum
        ):
            raise ValueError("Stored document integrity check failed.")
        return document, content
    except Exception as exc:
        raise DocumentStorageError() from exc


def download_owned_document(actor: User, document_id: UUID | str) -> tuple[Document, bytes]:
    return download_document(get_owned_document(actor, document_id))
