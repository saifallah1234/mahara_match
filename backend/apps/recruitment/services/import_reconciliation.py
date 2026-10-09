# Placement: backend/apps/recruitment/services/import_reconciliation.py
"""Decides what happens to ONE imported offer: add it, update it, or leave it.

Application service: it is the only layer here that touches the ORM. It receives
plain values (the adapter's to_model_fields() output) and never imports anything
from pipelines/, so the dependency direction stays pipelines -> services.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from backend.apps.identity.models import User
from backend.apps.identity.models.organizations import Organization
from backend.apps.imports.models.records import DataSource
from backend.apps.recruitment.models.job_offers import JobOffer, JobOfferStatus


class ReconcileOutcome(StrEnum):
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"


def reconcile_offer(
    *,
    source: DataSource,
    organization: Organization,
    created_by: User,
    external_id: str,
    fields: Mapping[str, Any],
) -> tuple[JobOffer, ReconcileOutcome]:
    """Create or update the offer identified by (source, external_id).

    Raises django.core.exceptions.ValidationError when the values break the
    model's own rules; nothing is written in that case. Call inside a transaction.

    On update only the scraped content columns are touched. status, organization,
    created_by and source are never overwritten, so a manual decision (for example
    publishing an offer) survives later imports.
    """
    values = {name: value for name, value in fields.items() if name != "external_id"}
    existing = JobOffer.objects.filter(source=source, external_id=external_id).first()

    if existing is None:
        offer = JobOffer(
            source=source,
            organization=organization,
            created_by=created_by,
            external_id=external_id,
            status=JobOfferStatus.DRAFT,
            **values,
        )
        offer.full_clean()  # model validators only run here, not on save()
        offer.save()
        return offer, ReconcileOutcome.ADDED

    if existing.deleted_at is not None:
        return existing, ReconcileOutcome.UNCHANGED  # never resurrect a deleted offer

    changed = [name for name, value in values.items() if getattr(existing, name) != value]
    if not changed:
        return existing, ReconcileOutcome.UNCHANGED

    for name in changed:
        setattr(existing, name, values[name])
    existing.full_clean()
    existing.save(update_fields=[*changed, "updated_at"])  # auto_now needs the explicit name
    return existing, ReconcileOutcome.UPDATED


def known_external_ids(source: DataSource) -> set[str]:
    """External ids already stored for this source (lets a run skip known pages)."""
    return {
        external_id
        for external_id in JobOffer.objects.filter(
            source=source, external_id__isnull=False
        ).values_list("external_id", flat=True)
        if external_id is not None
    }
