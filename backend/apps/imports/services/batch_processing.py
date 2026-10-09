# Placement: backend/apps/imports/services/batch_processing.py
"""Import runs: source authorization, batch bookkeeping and per-row outcomes.

Application service. The pipeline (scraper + adapter) calls these functions and
never touches models. Each row is committed on its own, so a crash midway keeps
everything already processed, and the batch stays visible as RUNNING/FAILED.
"""

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from backend.apps.identity.models import User, UserStatus
from backend.apps.identity.models.organizations import Organization, OrganizationType
from backend.apps.imports.models.records import DataSource, ImportBatch, ImportRow
from backend.apps.recruitment.services import import_reconciliation as reconciliation

# Placeholder owner of every imported offer: job_offers.organization and
# created_by are required, and scraped companies are not registered recruiters.
# The sentinel matricule passes the model's regex but is NOT a real tax id.
PLACEHOLDER_ORG_MATRICULE = "0000000A00000"
PLACEHOLDER_ORG_NAME = "Imported offers (external sources)"
IMPORT_USER_EMAIL = "import-bot@mahara-match.invalid"  # .invalid can never be a real mailbox

EXTERNAL_ID_MAX = 255
REJECTED = "REJECTED"


class BatchStatus(StrEnum):  # provisional vocabulary (Q24)
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SourceNotAuthorized(Exception):
    """The source is not (or no longer) approved for acquisition."""


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
    organization, _ = Organization.objects.get_or_create(
        matricule_fiscal=PLACEHOLDER_ORG_MATRICULE,
        defaults={
            "type": OrganizationType.COMPANY,
            "legal_name": PLACEHOLDER_ORG_NAME,
            "description": "Placeholder owner of offers imported from external sources. Not a real company.",
        },
    )
    return organization


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
