from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

from backend.apps.candidates.models import CV
from backend.apps.documents.models import Document
from backend.apps.imports.models import DataSource, ImportBatch, ImportRow
from backend.apps.matching.models import OfferMatch
from backend.apps.platform.models import AuditLog
from backend.apps.recruitment.models import Application, JobOffer
from backend.apps.taxonomy.models import Skill
from backend.apps.training.models import (
    TrainingEnrollment,
    TrainingProgram,
    TrainingSession,
    TrainingSkill,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def client_for(actor: Any) -> APIClient:
    client = APIClient()
    client.force_authenticate(actor)
    return client


def test_candidate_read_fields_use_visible_records(phase3: dict[str, Any]) -> None:
    offer = JobOffer.objects.create(
        organization=phase3["recruiter_org"],
        created_by=phase3["recruiter"],
        title="Visible job",
        description="Work",
        status="PUBLISHED",
        easy_apply=True,
    )
    document = Document.objects.create(
        owner_user=phase3["candidate"],
        type="CV",
        storage_uri="private/cv",
        file_name="cv.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        uploaded_at=timezone.now(),
    )
    cv = CV.objects.create(
        candidate=phase3["candidate_profile"], document=document, title="CV", version_number=1
    )
    Application.objects.create(candidate=cv.candidate, offer=offer, cv=cv, status="SUBMITTED")
    offer.status = "CLOSED"
    offer.save(update_fields=["status"])

    client = client_for(phase3["candidate"])
    assert (
        client.get(reverse("application-list")).json()["results"][0]["offer_title"] == "Visible job"
    )
    offer.status = "PUBLISHED"
    offer.save(update_fields=["status"])
    assert (
        client.get(reverse("job-offer-list")).json()["results"][0]["organization_name"]
        == phase3["recruiter_org"].legal_name
    )
    assert (
        client.get(reverse("training:program-list")).json()["results"][0]["organization_name"]
        == phase3["provider_org"].legal_name
    )


@pytest.fixture
def catalog(phase3: dict[str, Any]) -> dict[str, Any]:
    now = timezone.now()
    offers, applications, matches = [], [], []
    for index, (recruiter, candidate) in enumerate(
        (("recruiter", "candidate"), ("other_recruiter", "other_candidate"))
    ):
        offer = JobOffer.objects.create(
            organization=phase3[f"{recruiter}_org"],
            created_by=phase3[recruiter],
            title="Backend" if index == 0 else "Hidden position",
            description="Ship software",
            work_mode="REMOTE" if index == 0 else "ONSITE",
            governorate="Tunis" if index == 0 else "Sfax",
            city="City",
            status="PUBLISHED" if index == 0 else "DRAFT",
            easy_apply=True,
        )
        document = Document.objects.create(
            owner_user=phase3[candidate],
            type="CV",
            storage_uri="private/storage",
            file_name="private.pdf",
            mime_type="application/pdf",
            size_bytes=1,
            uploaded_at=now,
        )
        cv = CV.objects.create(
            candidate=phase3[f"{candidate}_profile"],
            document=document,
            title="Private CV",
            version_number=1,
        )
        application = Application.objects.create(
            candidate=cv.candidate,
            offer=offer,
            cv=cv,
            status="SUBMITTED" if index == 0 else "REJECTED",
        )
        match = OfferMatch.objects.create(
            candidate=cv.candidate,
            offer=offer,
            overall_score=50,
            model_version="v1" if index == 0 else "v2",
            calculated_at=now - timedelta(days=index),
            explanation_json={"private": "Not searchable"},
        )
        offers.append(offer)
        applications.append(application)
        matches.append(match)
    program = phase3["program"]
    foreign_program = TrainingProgram.objects.create(
        organization=phase3["other_provider_org"],
        title="Hidden program",
        status="DRAFT",
        delivery_mode="PRESENTIAL",
    )
    foreign_session = TrainingSession.objects.create(
        program=foreign_program,
        start_date=now + timedelta(days=10),
        end_date=now + timedelta(days=11),
        registration_deadline=now + timedelta(days=9),
        status="CANCELLED",
        capacity=2,
        location_or_url="Hidden location",
    )
    skill = Skill.objects.create(canonical_name="Python")
    TrainingSkill.objects.create(
        program=program, skill=skill, purpose="TAUGHT", target_level="BEGINNER"
    )
    TrainingSkill.objects.create(
        program=program, skill=skill, purpose="PREREQUISITE", target_level="BEGINNER"
    )
    enrollment = TrainingEnrollment.objects.create(
        session=phase3["session"], candidate=phase3["candidate_profile"]
    )
    foreign_enrollment = TrainingEnrollment.objects.create(
        session=foreign_session, candidate=phase3["other_candidate_profile"], status="DROPPED"
    )
    audit = AuditLog.objects.create(
        actor_user=phase3["recruiter"],
        actor_type="USER",
        action="offer.create",
        entity_type="job_offers",
        entity_id=offers[0].id,
    )
    AuditLog.objects.create(
        actor_user=phase3["other_recruiter"],
        actor_type="USER",
        action="other.action",
        entity_type="users",
        entity_id=uuid4(),
    )
    AuditLog.objects.filter(pk=audit.pk).update(created_at=now - timedelta(days=1))
    source = DataSource.objects.create(name="Source", type="CSV")
    other_source = DataSource.objects.create(name="Other source", type="API")
    batch = ImportBatch.objects.create(
        source=source, checksum="one", status="COMPLETED", started_at=now, completed_at=now
    )
    other_batch = ImportBatch.objects.create(
        source=other_source, checksum="two", status="STARTED", started_at=now - timedelta(days=2)
    )
    row = ImportRow.objects.create(batch=batch, row_number=1, status="ADDED")
    ImportRow.objects.create(batch=batch, row_number=2, status="REJECTED", error_code="INVALID")
    ImportRow.objects.create(batch=other_batch, row_number=1, status="ADDED")
    phase3.update(
        offer=offers[0],
        foreign_offer=offers[1],
        application=applications[0],
        foreign_application=applications[1],
        match=matches[0],
        foreign_match=matches[1],
        foreign_program=foreign_program,
        foreign_session=foreign_session,
        enrollment=enrollment,
        foreign_enrollment=foreign_enrollment,
        batch=batch,
        row=row,
    )
    phase3["cases"] = {
        "offers": (
            "recruiter",
            reverse("job-offer-list"),
            {},
            offers[0],
            [
                {"status": "PUBLISHED"},
                {"organization_id": str(offers[0].organization_id)},
                {"governorate": "tunis"},
                {"city": "city"},
                {"work_mode": "REMOTE"},
                {"search": "backend"},
                {"search": "ship"},
            ],
        ),
        "applications": (
            "recruiter",
            reverse("application-list"),
            {},
            applications[0],
            [
                {"offer_id": str(offers[0].id)},
                {"candidate_id": str(applications[0].candidate_id)},
                {"organization_id": str(offers[0].organization_id)},
                {"status": "SUBMITTED"},
            ],
        ),
        "matches": (
            "recruiter",
            reverse("offer-match-list"),
            {},
            matches[0],
            [
                {"offer_id": str(offers[0].id)},
                {"candidate_id": str(matches[0].candidate_id)},
                {"model_version": "v1"},
                {"calculated_after": (now - timedelta(hours=1)).isoformat()},
                {"calculated_before": (now + timedelta(hours=1)).isoformat()},
            ],
        ),
        "programs": (
            "provider",
            reverse("training:program-list"),
            {"organization_id": str(program.organization_id)},
            program,
            [
                {"skill_id": str(skill.id)},
                {"governorate": "tunis"},
                {"delivery_mode": "ONLINE"},
                {"status": "ACTIVE"},
            ],
        ),
        "sessions": (
            "provider",
            reverse("training:session-list"),
            {"program_id": str(program.id)},
            phase3["session"],
            [
                {"organization_id": str(program.organization_id)},
                {"skill_id": str(skill.id)},
                {"delivery_mode": "ONLINE"},
                {"location": "classroom"},
                {"status": "PLANNED"},
                {"starts_after": now.isoformat()},
                {"starts_before": (now + timedelta(days=4)).isoformat()},
                {"ends_after": now.isoformat()},
                {"ends_before": (now + timedelta(days=4)).isoformat()},
            ],
        ),
        "enrollments": (
            "provider",
            reverse("training:enrollment-list"),
            {"organization_id": str(program.organization_id)},
            enrollment,
            [
                {"candidate_id": str(enrollment.candidate_id)},
                {"session_id": str(enrollment.session_id)},
                {"status": "REGISTERED"},
            ],
        ),
        "audits": (
            "admin",
            reverse("audit-log-list"),
            {},
            audit,
            [
                {"actor_id": str(phase3["recruiter"].id)},
                {"action": "offer.create"},
                {"entity_type": "job_offers"},
                {"entity_id": str(offers[0].id)},
                {
                    "created_after": (now - timedelta(days=2)).isoformat(),
                    "created_before": (now - timedelta(hours=1)).isoformat(),
                },
            ],
        ),
        "batches": (
            "admin",
            reverse("import-batch-list"),
            {},
            batch,
            [
                {"source_id": str(source.id)},
                {"status": "COMPLETED"},
                {"started_after": (now - timedelta(hours=1)).isoformat()},
                {
                    "started_before": (now + timedelta(hours=1)).isoformat(),
                    "source_id": str(source.id),
                },
                {"completed_after": (now - timedelta(hours=1)).isoformat()},
                {"completed_before": (now + timedelta(hours=1)).isoformat()},
            ],
        ),
        "rows": (
            "admin",
            reverse("import-batch-row-list", args=(batch.id,)),
            {},
            row,
            [
                {"status": "ADDED"},
                {"source_id": str(source.id), "status": "ADDED"},
                {"created_after": now.isoformat(), "status": "ADDED"},
                {"created_before": (now + timedelta(hours=1)).isoformat(), "status": "ADDED"},
            ],
        ),
    }
    return phase3


@pytest.mark.parametrize(
    "kind",
    [
        "offers",
        "applications",
        "matches",
        "programs",
        "sessions",
        "enrollments",
        "audits",
        "batches",
        "rows",
    ],
)
def test_authorized_filters_and_standard_pagination(catalog: dict[str, Any], kind: str) -> None:
    actor, url, scope, expected, filters = catalog["cases"][kind]
    client = client_for(catalog[actor])
    for query in filters:
        response = client.get(url, scope | query | {"page_size": "1"})
        assert response.status_code == 200
        data = response.json()
        assert set(data) == {"count", "next", "previous", "results"}
        assert data["count"] == 1, (kind, query, data)
        assert data["results"][0]["id"] == str(expected.id)
    response = client.get(url, scope | {"page_size": "1"}).json()
    if response["count"] > 1:
        assert response["next"] is not None
        second = client.get(url, scope | {"page_size": "1", "page": "2"}).json()
        assert second["previous"] is not None
        assert second["results"][0]["id"] != response["results"][0]["id"]


@pytest.mark.parametrize(
    "kind,query",
    [
        ("offers", {"status": "INVALID"}),
        ("offers", {"work_mode": "INVALID"}),
        ("offers", {"ordering": "created_by__email"}),
        ("applications", {"offer_id": "invalid"}),
        ("applications", {"status": "INVALID"}),
        ("matches", {"calculated_after": "invalid"}),
        ("matches", {"candidate_id": "invalid"}),
        ("programs", {"delivery_mode": "INVALID"}),
        ("programs", {"skill_id": "invalid"}),
        ("sessions", {"status": "INVALID"}),
        (
            "sessions",
            {"starts_after": "2030-01-02T00:00:00Z", "starts_before": "2030-01-01T00:00:00Z"},
        ),
        ("enrollments", {"status": "INVALID"}),
        ("audits", {"actor_id": "invalid"}),
        (
            "audits",
            {"created_after": "2030-01-02T00:00:00Z", "created_before": "2030-01-01T00:00:00Z"},
        ),
        ("batches", {"source_id": "invalid"}),
        ("batches", {"status": "INVALID"}),
        ("rows", {"status": "INVALID"}),
    ],
)
def test_invalid_query_values_use_shared_errors(
    catalog: dict[str, Any], kind: str, query: dict[str, str]
) -> None:
    actor, url, scope, _, _ = catalog["cases"][kind]
    response = client_for(catalog[actor]).get(url, scope | query)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "kind",
    [
        "offers",
        "applications",
        "matches",
        "programs",
        "sessions",
        "enrollments",
        "audits",
        "batches",
        "rows",
    ],
)
def test_permissions_checked_before_invalid_filters(catalog: dict[str, Any], kind: str) -> None:
    _, url, scope, _, _ = catalog["cases"][kind]
    response = client_for(
        catalog["recruiter"]
        if kind in {"programs", "sessions", "enrollments", "audits", "batches", "rows"}
        else catalog["provider"]
    ).get(url, scope | {"status": "INVALID", "candidate_id": "invalid"})
    assert response.status_code == 403
    assert APIClient().get(url, scope).status_code == 401


def test_cross_organization_and_candidate_filters_cannot_widen_scope(
    catalog: dict[str, Any],
) -> None:
    client = client_for(catalog["recruiter"])
    for route, filters in (
        ("job-offer-list", {"organization_id": str(catalog["other_recruiter_org"].id)}),
        ("application-list", {"offer_id": str(catalog["foreign_offer"].id)}),
        ("application-list", {"candidate_id": str(catalog["other_candidate_profile"].id)}),
        ("application-list", {"organization_id": str(catalog["other_recruiter_org"].id)}),
        ("offer-match-list", {"offer_id": str(catalog["foreign_offer"].id)}),
        ("offer-match-list", {"candidate_id": str(catalog["other_candidate_profile"].id)}),
    ):
        assert client.get(reverse(route), filters).json()["count"] == 0
    candidate = client_for(catalog["candidate"])
    for route in ("application-list", "offer-match-list", "training:enrollment-list"):
        assert (
            candidate.get(
                reverse(route), {"candidate_id": str(catalog["other_candidate_profile"].id)}
            ).json()["count"]
            == 0
        )
    provider = client_for(catalog["provider"])
    assert (
        provider.get(
            reverse("training:enrollment-list"),
            {"organization_id": str(catalog["other_provider_org"].id)},
        ).status_code
        == 403
    )
    assert (
        provider.get(
            reverse("training:program-list"),
            {"organization_id": str(catalog["other_provider_org"].id), "status": "DRAFT"},
        ).status_code
        == 403
    )
    assert (
        provider.get(
            reverse("training:session-list"),
            {"program_id": str(catalog["foreign_program"].id), "status": "CANCELLED"},
        ).json()["count"]
        == 0
    )


def test_job_search_excludes_hidden_and_private_fields_and_ordering_is_stable(
    catalog: dict[str, Any],
) -> None:
    client = client_for(catalog["recruiter"])
    for search in (
        "Hidden position",
        catalog["recruiter"].email,
        "Private Identity",
        "private/storage",
    ):
        assert client.get(reverse("job-offer-list"), {"search": search}).json()["count"] == 0
    second = JobOffer.objects.create(
        organization=catalog["recruiter_org"],
        created_by=catalog["recruiter"],
        title="AAA",
        description="Public description",
        easy_apply=True,
    )
    response = client.get(reverse("job-offer-list"), {"ordering": "title", "page_size": "1"}).json()
    assert response["count"] == 2 and response["results"][0]["id"] == str(second.id)
    second.deleted_at = timezone.now()
    second.save()
    assert client.get(reverse("job-offer-list"), {"status": "DRAFT"}).json()["count"] == 0


def test_openapi_documents_all_phase3_query_parameters() -> None:
    schema = SchemaGenerator().get_schema(public=True)
    expected = {
        "/api/v1/job-offers/": {
            "status",
            "governorate",
            "city",
            "work_mode",
            "organization_id",
            "search",
            "ordering",
        },
        "/api/v1/applications/": {"offer_id", "candidate_id", "organization_id", "status"},
        "/api/v1/offer-matches/": {
            "offer_id",
            "candidate_id",
            "model_version",
            "calculated_after",
            "calculated_before",
        },
        "/api/v1/training/programs/": {
            "organization_id",
            "skill_id",
            "governorate",
            "delivery_mode",
            "status",
        },
        "/api/v1/training/sessions/": {
            "program_id",
            "organization_id",
            "skill_id",
            "delivery_mode",
            "location",
            "status",
            "starts_after",
            "starts_before",
            "ends_after",
            "ends_before",
        },
        "/api/v1/training/enrollments/": {
            "organization_id",
            "candidate_id",
            "session_id",
            "status",
        },
        "/api/v1/audit-logs/": {
            "actor_id",
            "action",
            "entity_type",
            "entity_id",
            "created_after",
            "created_before",
        },
        "/api/v1/import-batches/": {
            "source_id",
            "status",
            "started_after",
            "started_before",
            "completed_after",
            "completed_before",
        },
        "/api/v1/import-batches/{batch_id}/rows/": {
            "source_id",
            "status",
            "created_after",
            "created_before",
        },
    }
    for path, names in expected.items():
        parameters = schema["paths"][path]["get"]["parameters"]
        assert {
            parameter["name"] for parameter in parameters if parameter["in"] == "query"
        } == names | {"page", "page_size"}
