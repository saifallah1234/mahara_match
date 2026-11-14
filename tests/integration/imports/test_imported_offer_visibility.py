# Placement: tests/integration/imports/test_imported_offer_visibility.py
"""Imported offers reach the candidate catalogue (decision 2026-11-14)."""

from datetime import timedelta
from typing import Any

import pytest
from django.core.management import call_command
from django.utils import timezone

from backend.apps.identity.models import Organization
from backend.apps.imports.models.records import DataSource
from backend.apps.imports.services import batch_processing
from backend.apps.recruitment.models import JobOffer
from backend.apps.recruitment.services.job_offers import (
    list_indexable_job_offers,
    list_job_offers,
)
from backend.apps.recruitment.services.retrieval_scope import visible_offers

pytestmark = pytest.mark.integration


def _fields(external_id: str, **overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "external_id": external_id,
        "offer_url": f"https://www.tanitjobs.com/job/{external_id}/",
        "title": "Développeur Python",
        "description": "Services Django et PostgreSQL.",
        "contract_type": "CDI",
        "work_mode": "ONSITE",
        "experience_level": "0 à 1 an",
        "country_code": "TN",
        "governorate": "Tunis",
        "city": "Tunis",
        "min_salary": None,
        "max_salary": None,
        "application_deadline": None,
        "easy_apply": False,
        "company_name": "Acme Tunisie",
    }
    fields.update(overrides)
    return fields


@pytest.fixture
def source(db: None) -> DataSource:
    return DataSource.objects.create(
        name="tanitjobs",
        type="JOB_BOARD",
        base_url="https://www.tanitjobs.com",
        is_authorized=True,
        permission_evidence="test",
    )


def _import(source: DataSource, external_id: str, **overrides: Any) -> JobOffer:
    run = batch_processing.start_import(source)
    row = batch_processing.accept_row(
        run,
        row_number=1,
        external_id=external_id,
        payload={},
        fields=_fields(external_id, **overrides),
    )
    batch_processing.finish_import(run)
    assert row.job_offer is not None, row.error_message
    return JobOffer.objects.get(pk=row.job_offer.pk)


def test_new_import_is_published_and_visible_to_candidates(
    phase3: dict[str, Any], source: DataSource
) -> None:
    offer = _import(source, "1001")

    assert offer.status == "PUBLISHED"
    assert offer.published_at is not None
    assert offer.organization.verification_status == "VERIFIED"
    candidate = phase3["candidate"]
    assert list_job_offers(candidate).filter(pk=offer.pk).exists()
    assert visible_offers(candidate).filter(pk=offer.pk).exists()


def test_refresh_keeps_a_manual_status_change(source: DataSource) -> None:
    offer = _import(source, "1002")
    JobOffer.objects.filter(pk=offer.pk).update(status="CLOSED")

    refreshed = _import(source, "1002", title="Développeur Python senior")

    assert refreshed.title == "Développeur Python senior"
    assert refreshed.status == "CLOSED"


def test_pending_placeholder_is_promoted_but_rejected_is_kept(source: DataSource) -> None:
    placeholder = Organization.objects.create(
        type="COMPANY",
        legal_name=batch_processing.PLACEHOLDER_ORG_NAME,
        matricule_fiscal=batch_processing.PLACEHOLDER_ORG_MATRICULE,
    )
    assert placeholder.verification_status == "PENDING"
    _import(source, "1003")
    placeholder.refresh_from_db()
    assert placeholder.verification_status == "VERIFIED"

    Organization.objects.filter(pk=placeholder.pk).update(verification_status="REJECTED")
    _import(source, "1004")
    placeholder.refresh_from_db()
    assert placeholder.verification_status == "REJECTED"


def test_command_publishes_only_old_import_drafts(
    phase3: dict[str, Any], source: DataSource
) -> None:
    old_draft = _import(source, "2001")
    no_link = _import(source, "2002")
    JobOffer.objects.filter(pk__in=[old_draft.pk, no_link.pk]).update(
        status="DRAFT", published_at=None
    )
    JobOffer.objects.filter(pk=no_link.pk).update(offer_url="")
    Organization.objects.filter(pk=old_draft.organization_id).update(verification_status="PENDING")
    recruiter_draft = JobOffer.objects.create(
        organization=phase3["recruiter_org"],
        created_by=phase3["recruiter"],
        title="Brouillon recruteur",
        description="Pas encore prêt.",
        easy_apply=True,
    )

    assert batch_processing.count_previous_import_drafts() == 1
    call_command("publish_imported_offers", "--dry-run", verbosity=0)
    assert JobOffer.objects.get(pk=old_draft.pk).status == "DRAFT"

    call_command("publish_imported_offers", verbosity=0)

    published = JobOffer.objects.get(pk=old_draft.pk)
    assert published.status == "PUBLISHED"
    assert published.published_at is not None
    assert published.organization.verification_status == "VERIFIED"
    assert JobOffer.objects.get(pk=no_link.pk).status == "DRAFT"
    assert JobOffer.objects.get(pk=recruiter_draft.pk).status == "DRAFT"
    assert list_job_offers(phase3["candidate"]).filter(pk=published.pk).exists()


def test_api_exposes_company_name(phase3: dict[str, Any], source: DataSource) -> None:
    from rest_framework.test import APIClient

    offer = _import(source, "3001")
    client = APIClient()
    client.force_authenticate(phase3["candidate"])

    response = client.get(f"/api/v1/job-offers/{offer.pk}/")

    assert response.status_code == 200, response.content
    assert response.json()["company_name"] == "Acme Tunisie"


def test_candidates_do_not_see_offers_past_their_deadline(
    phase3: dict[str, Any], source: DataSource
) -> None:
    today = timezone.localdate()
    expired = _import(source, "4001", application_deadline=today - timedelta(days=1))
    last_day = _import(source, "4002", application_deadline=today)
    no_deadline = _import(source, "4003")
    recruiter_expired = JobOffer.objects.create(
        organization=phase3["recruiter_org"],
        created_by=phase3["recruiter"],
        title="Offre expirée",
        description="Date limite passée.",
        easy_apply=True,
        status="PUBLISHED",
        application_deadline=today - timedelta(days=3),
    )

    candidate_ids = set(list_job_offers(phase3["candidate"]).values_list("pk", flat=True))
    assert expired.pk not in candidate_ids
    assert recruiter_expired.pk not in candidate_ids
    assert {last_day.pk, no_deadline.pk} <= candidate_ids
    assert not visible_offers(phase3["candidate"]).filter(pk=expired.pk).exists()
    assert not list_indexable_job_offers().filter(pk=expired.pk).exists()
    # The owning organization still sees its own expired offer.
    assert list_job_offers(phase3["recruiter"]).filter(pk=recruiter_expired.pk).exists()
