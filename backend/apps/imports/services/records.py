from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import F, QuerySet
from django.utils import timezone

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.imports.models import DataSource, ImportBatch, ImportRow
from backend.apps.imports.services.contracts import ImportsPermissionCode
from backend.apps.platform.services.records import append_audit
from backend.apps.recruitment.models import JobOffer
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def list_sources(actor: User) -> QuerySet[DataSource]:
    require_permission(actor, ImportsPermissionCode.MANAGE_SOURCES)
    return DataSource.objects.all()


def get_source(actor: User, source_id: UUID | str) -> DataSource:
    try:
        return list_sources(actor).get(pk=source_id)
    except DataSource.DoesNotExist as exc:
        raise DomainNotFoundError("Data source not found.") from exc


@transaction.atomic
def create_source(actor: User, data: Mapping[str, Any]) -> DataSource:
    require_permission(actor, ImportsPermissionCode.MANAGE_SOURCES)
    source = DataSource.objects.create(
        name=data["name"],
        type=data["type"],
        base_url=data.get("base_url"),
        configuration_json=data.get("configuration_json", {}),
    )
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="imports.source.create",
        entity_type="data_sources",
        entity_id=source.id,
        after={"type": source.type, "is_authorized": False},
    )
    return source


@transaction.atomic
def update_source(actor: User, source_id: UUID | str, data: Mapping[str, Any]) -> DataSource:
    source = get_source(actor, source_id)
    was_authorized = source.is_authorized
    for field in ("name", "type", "base_url", "configuration_json"):
        if field in data:
            setattr(source, field, data[field])
    update_fields = [*data.keys(), "updated_at"]
    if any(field in data for field in ("type", "base_url", "configuration_json")):
        source.is_authorized = False
        update_fields.append("is_authorized")
    source.save(update_fields=update_fields)
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="imports.source.update",
        entity_type="data_sources",
        entity_id=source.id,
        before={"is_authorized": was_authorized},
        after={"is_authorized": source.is_authorized, "changed_fields": list(data)},
    )
    return source


@transaction.atomic
def authorize_source(
    actor: User,
    source_id: UUID | str,
    *,
    acquisition_method: str,
    permission_evidence: str,
    expires_at: Any,
) -> DataSource:
    source = get_source(actor, source_id)
    if (
        not acquisition_method.strip()
        or not permission_evidence.strip()
        or expires_at <= timezone.now()
    ):
        raise DomainValidationError(
            details={"authorization": ["Evidence and future expiry required."]}
        )
    source.acquisition_method = acquisition_method
    source.permission_evidence = permission_evidence
    source.reviewed_at = timezone.now()
    source.expires_at = expires_at
    source.is_authorized = True
    source.save(
        update_fields=[
            "acquisition_method",
            "permission_evidence",
            "reviewed_at",
            "expires_at",
            "is_authorized",
            "updated_at",
        ]
    )
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="imports.source.authorize",
        entity_type="data_sources",
        entity_id=source.id,
        after={"acquisition_method": acquisition_method, "expires_at": expires_at.isoformat()},
    )
    return source


@transaction.atomic
def revoke_source(actor: User, source_id: UUID | str) -> DataSource:
    source = get_source(actor, source_id)
    source.is_authorized = False
    source.save(update_fields=["is_authorized", "updated_at"])
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="imports.source.revoke",
        entity_type="data_sources",
        entity_id=source.id,
        after={"is_authorized": False},
    )
    return source


def list_batches(actor: User) -> QuerySet[ImportBatch]:
    require_permission(actor, ImportsPermissionCode.READ_RECORDS)
    return ImportBatch.objects.all()


def get_batch(actor: User, batch_id: UUID | str) -> ImportBatch:
    try:
        return list_batches(actor).get(pk=batch_id)
    except ImportBatch.DoesNotExist as exc:
        raise DomainNotFoundError("Import batch not found.") from exc


def list_rows(actor: User, batch_id: UUID | str) -> QuerySet[ImportRow]:
    batch = get_batch(actor, batch_id)
    return batch.rows.all()


def get_row(actor: User, row_id: UUID | str) -> ImportRow:
    require_permission(actor, ImportsPermissionCode.READ_RECORDS)
    try:
        return ImportRow.objects.get(pk=row_id)
    except ImportRow.DoesNotExist as exc:
        raise DomainNotFoundError("Import row not found.") from exc


def start_batch(
    source: DataSource,
    *,
    checksum: str,
    raw_document_id: UUID | None = None,
) -> ImportBatch:
    if not source.is_authorized or source.expires_at is None or source.expires_at <= timezone.now():
        raise DomainValidationError(details={"source": ["Source is not authorized."]})
    if not checksum:
        raise DomainValidationError(details={"checksum": ["Required."]})
    return ImportBatch.objects.create(
        source=source,
        raw_document_id=raw_document_id,
        checksum=checksum,
        status="STARTED",
        started_at=timezone.now(),
    )


@transaction.atomic
def record_row(
    batch: ImportBatch,
    *,
    row_number: int,
    external_id: str,
    payload: Mapping[str, Any],
    status: str,
    job_offer: JobOffer | None = None,
    error_code: str = "",
    error_message: str = "",
) -> ImportRow:
    batch = ImportBatch.objects.select_for_update().get(pk=batch.pk)
    if batch.status != "STARTED" or row_number < 1:
        raise DomainValidationError(details={"batch": ["Batch must be active and row positive."]})
    if (
        not batch.source.is_authorized
        or batch.source.expires_at is None
        or batch.source.expires_at <= timezone.now()
    ):
        raise DomainValidationError(details={"source": ["Source authorization has expired."]})
    if batch.source.type in {"API", "CSV"} and not external_id:
        status, error_code, error_message, job_offer = (
            "REJECTED",
            "MISSING_EXTERNAL_ID",
            "Automated rows require an external ID.",
            None,
        )
    if status not in {"ADDED", "UPDATED", "UNCHANGED", "REJECTED"}:
        raise DomainValidationError(details={"status": ["Invalid row outcome."]})
    if status == "REJECTED" and not error_code:
        raise DomainValidationError(details={"error_code": ["Required for rejected rows."]})
    if status != "REJECTED" and job_offer is None:
        raise DomainValidationError(details={"job_offer": ["Required for accepted rows."]})
    if job_offer is not None and job_offer.source_id != batch.source_id:
        raise DomainValidationError(details={"job_offer": ["Offer source differs from batch."]})
    row = ImportRow.objects.create(
        batch=batch,
        row_number=row_number,
        external_id=external_id,
        payload_json=dict(payload),
        status=status,
        job_offer=job_offer,
        error_code=error_code,
        error_message=error_message,
    )
    counter = {
        "ADDED": "added_count",
        "UPDATED": "updated_count",
        "UNCHANGED": "unchanged_count",
        "REJECTED": "rejected_count",
    }[status]
    ImportBatch.objects.filter(pk=batch.pk).update(**{counter: F(counter) + 1})
    return row


@transaction.atomic
def complete_batch(batch: ImportBatch, *, failed: bool = False) -> ImportBatch:
    batch = ImportBatch.objects.select_for_update().get(pk=batch.pk)
    if batch.status != "STARTED":
        raise DomainValidationError(details={"status": ["Batch already completed."]})
    batch.status = "FAILED" if failed else "COMPLETED"
    batch.completed_at = timezone.now()
    batch.save(update_fields=["status", "completed_at", "updated_at"])
    return batch
