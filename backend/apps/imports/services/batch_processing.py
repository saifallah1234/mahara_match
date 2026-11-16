# Placement: backend/apps/imports/services/batch_processing.py
"""Import runs: source authorization, batch bookkeeping and per-row outcomes.

Application service. The pipeline (scraper + adapter) calls these functions and
never touches models. Each row is committed on its own, so a crash midway keeps
everything already processed, and the batch stays visible as RUNNING/FAILED.
"""

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from backend.apps.identity.models import User, UserStatus
from backend.apps.identity.models.organizations import (
    Organization,
    OrganizationType,
    VerificationStatus,
)
from backend.apps.identity.services.access import require_permission
from backend.apps.imports.models.records import DataSource, ImportBatch, ImportRow
from backend.apps.imports.services.contracts import ImportsPermissionCode
from backend.apps.platform.services.records import append_audit
from backend.apps.recruitment.services import import_reconciliation as reconciliation
from backend.common.exceptions import DomainNotFoundError, DomainValidationError
from backend.common.exceptions.domain import DomainError

# Placeholder owner of every imported offer: job_offers.organization and
# created_by are required, and scraped companies are not registered recruiters.
# The sentinel matricule passes the model's regex but is NOT a real tax id.
PLACEHOLDER_ORG_MATRICULE = "0000000A00000"
PLACEHOLDER_ORG_NAME = "Imported offers (external sources)"
IMPORT_USER_EMAIL = "import-bot@mahara-match.invalid"  # .invalid can never be a real mailbox

EXTERNAL_ID_MAX = 255
REJECTED = "REJECTED"
WEB_SCRAPING = "WEB_SCRAPING"  # the only source type a launch can run (browser scrapers)
STALE_RUN_AFTER = timedelta(hours=3)  # a launched run never takes this long


class BatchStatus(StrEnum):  # provisional vocabulary (Q24)
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SourceNotAuthorized(Exception):
    """The source is not (or no longer) approved for acquisition."""


class ImportAlreadyRunning(DomainError):
    code = "import_already_running"
    status_code = 409
    default_message = "An import of this source is already running."


@dataclass(frozen=True)
class ImportRun:
    batch: ImportBatch
    organization: Organization
    created_by: User


# -- bootstrap rows (idempotent) -------------------------------------------


def get_or_create_source(
    *, name: str, source_type: str, base_url: str, acquisition_method: str
) -> DataSource:
    """Created with is_authorized=False: a person must approve it explicitly."""
    source, _ = DataSource.objects.get_or_create(
        name=name,
        defaults={
            "type": source_type,
            "base_url": base_url,
            "acquisition_method": acquisition_method,
        },
    )
    return source


def _get_placeholder_organization() -> Organization:
    """Created VERIFIED: candidates only see offers of verified organizations.

    A placeholder left PENDING by earlier runs is promoted. REJECTED is an
    administrator's explicit choice and is kept, which hides the imported offers again.
    """
    organization, _ = Organization.objects.get_or_create(
        matricule_fiscal=PLACEHOLDER_ORG_MATRICULE,
        defaults={
            "type": OrganizationType.COMPANY,
            "legal_name": PLACEHOLDER_ORG_NAME,
            "description": "Placeholder owner of offers imported from external sources. Not a real company.",
            "verification_status": VerificationStatus.VERIFIED,
        },
    )
    if organization.verification_status == VerificationStatus.PENDING:
        organization.verification_status = VerificationStatus.VERIFIED
        organization.save(update_fields=["verification_status", "updated_at"])
    return organization


def publish_previous_imports() -> int:
    """Publish DRAFT offers stored by imports made before 2026-11-14; returns the count."""
    with transaction.atomic():
        return reconciliation.publish_imported_drafts(
            organization=_get_placeholder_organization(), created_by=_get_import_user()
        )


def count_previous_import_drafts() -> int:
    """How many offers publish_previous_imports() would publish (read-only)."""
    organization = Organization.objects.filter(matricule_fiscal=PLACEHOLDER_ORG_MATRICULE).first()
    user = User.objects.filter(email__iexact=IMPORT_USER_EMAIL).first()
    if organization is None or user is None:
        return 0
    return reconciliation.publishable_imported_drafts(
        organization=organization, created_by=user
    ).count()


def _get_import_user() -> User:
    user = User.objects.filter(email__iexact=IMPORT_USER_EMAIL).first()
    if user is None:
        # No password => unusable password; DISABLED => nobody can ever log in as it.
        user = User.objects.create_user(
            IMPORT_USER_EMAIL,
            None,
            first_name="Import",
            last_name="Bot",
            status=UserStatus.DISABLED,
        )
    return user


# -- run lifecycle -----------------------------------------------------------


def assert_source_authorized(source: DataSource) -> None:
    if not source.is_authorized:
        raise SourceNotAuthorized(f"Source '{source.name}' is not marked as authorized.")
    if source.expires_at is not None and source.expires_at <= timezone.now():
        raise SourceNotAuthorized(f"Authorization for source '{source.name}' has expired.")


def start_import(source: DataSource) -> ImportRun:
    assert_source_authorized(source)
    with transaction.atomic():
        organization = _get_placeholder_organization()
        created_by = _get_import_user()
        batch = ImportBatch.objects.create(
            source=source,
            checksum="",  # unknown until the run ends
            status=BatchStatus.RUNNING,
            started_at=timezone.now(),
        )
    return ImportRun(batch=batch, organization=organization, created_by=created_by)


def accept_row(
    run: ImportRun,
    *,
    row_number: int,
    external_id: str,
    payload: dict[str, Any],
    fields: dict[str, Any],
    description_language_code: str | None = None,
) -> ImportRow:
    """Add/update/skip the offer and record the outcome, atomically."""
    with transaction.atomic():
        try:
            offer, outcome = reconciliation.reconcile_offer(
                source=run.batch.source,
                organization=run.organization,
                created_by=run.created_by,
                external_id=external_id,
                fields=fields,
                description_language_code=description_language_code,
            )
        except ValidationError as exc:
            return _record_row(
                run,
                row_number=row_number,
                external_id=external_id,
                payload=payload,
                status=REJECTED,
                error_code="VALIDATION_ERROR",
                error_message="; ".join(exc.messages),
            )
        return _record_row(
            run,
            row_number=row_number,
            external_id=external_id,
            payload=payload,
            status=outcome.value,
            job_offer=offer,
        )


def reject_row(
    run: ImportRun,
    *,
    row_number: int,
    external_id: str | None,
    payload: dict[str, Any],
    error_code: str,
    error_message: str,
) -> ImportRow:
    return _record_row(
        run,
        row_number=row_number,
        external_id=external_id,
        payload=payload,
        status=REJECTED,
        error_code=error_code,
        error_message=error_message,
    )


def prepare_import(actor: User, source_id: UUID | str) -> ImportBatch:
    """Create the RUNNING batch of an admin-launched run (the scrape starts afterwards)."""
    require_permission(actor, ImportsPermissionCode.MANAGE_SOURCES)
    return _prepare_batch({"pk": source_id}, actor=actor)


def prepare_scheduled_import(source_name: str) -> ImportBatch | None:
    """Create the RUNNING batch of a scheduled run, or None when a run is already going.

    Same checks as an admin launch, so a scheduled run and a click never scrape the
    same source at once. Recorded in the audit log as a SYSTEM action.
    """
    try:
        return _prepare_batch({"name": source_name}, actor=None)
    except ImportAlreadyRunning:
        return None


def _prepare_batch(lookup: dict[str, Any], *, actor: User | None) -> ImportBatch:
    """Only authorized WEB_SCRAPING sources run, one run at a time per source.

    A RUNNING batch older than STALE_RUN_AFTER is treated as a crashed run and marked
    FAILED, so a dead process cannot block the source forever.
    """
    with transaction.atomic():
        source = DataSource.objects.select_for_update().filter(**lookup).first()
        if source is None:
            raise DomainNotFoundError("Data source not found.")
        if source.type != WEB_SCRAPING:
            raise DomainValidationError(
                details={"source": ["Only web-scraping sources can be launched from here."]}
            )
        try:
            assert_source_authorized(source)
        except SourceNotAuthorized as exc:
            raise DomainValidationError(details={"source": [str(exc)]}) from exc

        now = timezone.now()
        running = ImportBatch.objects.filter(source=source, status=BatchStatus.RUNNING)
        running.filter(started_at__lt=now - STALE_RUN_AFTER).update(
            status=BatchStatus.FAILED, completed_at=now, updated_at=now
        )
        if running.exists():
            raise ImportAlreadyRunning()

        batch = ImportBatch.objects.create(
            source=source, checksum="", status=BatchStatus.RUNNING, started_at=now
        )
        append_audit(
            actor_type="USER" if actor is not None else "SYSTEM",
            actor_user=actor,
            action="imports.batch.launch" if actor is not None else "imports.batch.schedule",
            entity_type="import_batches",
            entity_id=batch.id,
            after={"source_id": str(source.id)},
        )
    return batch


def resume_import(batch_id: UUID | str) -> ImportRun:
    """The ImportRun of a batch created by prepare_import(), for the launched process."""
    batch = ImportBatch.objects.select_related("source").filter(pk=batch_id).first()
    if batch is None or batch.status != BatchStatus.RUNNING:
        raise ValueError(f"Import batch {batch_id} is not waiting to run.")
    assert_source_authorized(batch.source)  # it may have been revoked since the click
    return ImportRun(
        batch=batch,
        organization=_get_placeholder_organization(),
        created_by=_get_import_user(),
    )


def batch_source_name(batch_id: UUID | str) -> str | None:
    name: str | None = (
        ImportBatch.objects.filter(pk=batch_id).values_list("source__name", flat=True).first()
    )
    return name


def mark_batch_failed(batch_id: UUID | str) -> None:
    """Close a batch whose process died before finish_import(); a finished one is left alone."""
    now = timezone.now()
    ImportBatch.objects.filter(pk=batch_id, status=BatchStatus.RUNNING).update(
        status=BatchStatus.FAILED, completed_at=now, updated_at=now
    )


def finish_import(run: ImportRun, *, failed: bool = False) -> dict[str, int]:
    """Close the batch: counters from the stored rows, checksum, final status."""
    rows = run.batch.rows.order_by()
    counts = {row["status"]: row["n"] for row in rows.values("status").annotate(n=Count("id"))}
    external_ids = sorted(rows.exclude(external_id="").values_list("external_id", flat=True))

    batch = run.batch
    batch.added_count = counts.get(reconciliation.ReconcileOutcome.ADDED, 0)
    batch.updated_count = counts.get(reconciliation.ReconcileOutcome.UPDATED, 0)
    batch.unchanged_count = counts.get(reconciliation.ReconcileOutcome.UNCHANGED, 0)
    batch.rejected_count = counts.get(REJECTED, 0)
    batch.checksum = hashlib.sha256("\n".join(external_ids).encode()).hexdigest()
    batch.status = BatchStatus.FAILED if failed else BatchStatus.COMPLETED
    batch.completed_at = timezone.now()
    batch.save()
    return counts


def rejection_summary(run: ImportRun) -> dict[str, int]:
    """Rejected rows of this run grouped by error code (e.g. OFFER_CLOSED: 5)."""
    rows = run.batch.rows.order_by().filter(status=REJECTED)
    return {
        row["error_code"]: row["n"] for row in rows.values("error_code").annotate(n=Count("id"))
    }


def _record_row(
    run: ImportRun,
    *,
    row_number: int,
    external_id: str | None,
    payload: dict[str, Any],
    status: str,
    error_code: str = "",
    error_message: str = "",
    job_offer: Any = None,
) -> ImportRow:
    return ImportRow.objects.create(
        batch=run.batch,
        row_number=row_number,
        external_id=(external_id or "")[:EXTERNAL_ID_MAX],
        payload_json=payload,
        status=status,
        error_code=error_code,
        error_message=error_message,
        job_offer=job_offer,
    )
