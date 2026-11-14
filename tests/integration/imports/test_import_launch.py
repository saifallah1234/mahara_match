# Placement: tests/integration/imports/test_import_launch.py
"""Admin-launched imports: the endpoint, the batch guard and the launched pipeline run."""

from collections.abc import Collection, Iterator
from datetime import timedelta
from typing import Any
from uuid import UUID

import django.db
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from backend.apps.imports.models.records import DataSource, ImportBatch
from backend.apps.imports.services import import_launcher
from backend.apps.recruitment.models import JobOffer
from pipelines.ingestion import offer_import
from pipelines.ingestion.scraped_offer import ScrapedOffer

pytestmark = pytest.mark.integration


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch) -> list[UUID]:
    """Record launches instead of starting a real browser process."""
    calls: list[UUID] = []
    monkeypatch.setattr(import_launcher, "_spawn", calls.append)
    return calls


@pytest.fixture
def tanitjobs(db: None) -> DataSource:
    return DataSource.objects.create(
        name="Tanitjobs",
        type="WEB_SCRAPING",
        base_url="https://www.tanitjobs.com/",
        is_authorized=True,
        permission_evidence="test",
    )


def _client(user: Any) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _launch(user: Any, source: DataSource) -> Any:
    return _client(user).post(f"/api/v1/data-sources/{source.pk}/run-import/")


def test_admin_launch_creates_a_running_batch_and_starts_the_process(
    phase3: dict[str, Any], tanitjobs: DataSource, spawned: list[UUID]
) -> None:
    response = _launch(phase3["admin"], tanitjobs)

    assert response.status_code == 202, response.content
    batch = ImportBatch.objects.get(pk=response.json()["id"])
    assert batch.status == "RUNNING"
    assert batch.source_id == tanitjobs.pk
    assert spawned == [batch.pk]


def test_a_second_launch_is_refused_while_one_runs(
    phase3: dict[str, Any], tanitjobs: DataSource, spawned: list[UUID]
) -> None:
    assert _launch(phase3["admin"], tanitjobs).status_code == 202

    response = _launch(phase3["admin"], tanitjobs)

    assert response.status_code == 409, response.content
    assert ImportBatch.objects.filter(source=tanitjobs).count() == 1
    assert len(spawned) == 1


def test_a_stale_running_batch_is_failed_and_does_not_block(
    phase3: dict[str, Any], tanitjobs: DataSource, spawned: list[UUID]
) -> None:
    stale = ImportBatch.objects.create(
        source=tanitjobs,
        checksum="",
        status="RUNNING",
        started_at=timezone.now() - timedelta(hours=4),
    )

    assert _launch(phase3["admin"], tanitjobs).status_code == 202
    stale.refresh_from_db()
    assert stale.status == "FAILED"


@pytest.mark.parametrize(
    ("changes", "expected"),
    [({"is_authorized": False}, 400), ({"type": "CSV"}, 400)],
)
def test_only_authorized_web_scraping_sources_can_be_launched(
    phase3: dict[str, Any],
    tanitjobs: DataSource,
    spawned: list[UUID],
    changes: dict[str, Any],
    expected: int,
) -> None:
    DataSource.objects.filter(pk=tanitjobs.pk).update(**changes)

    assert _launch(phase3["admin"], tanitjobs).status_code == expected
    assert not ImportBatch.objects.exists()
    assert spawned == []


def test_non_admins_cannot_launch(
    phase3: dict[str, Any], tanitjobs: DataSource, spawned: list[UUID]
) -> None:
    assert _launch(phase3["recruiter"], tanitjobs).status_code == 403
    assert _launch(phase3["candidate"], tanitjobs).status_code == 403
    assert spawned == []


def test_a_process_that_cannot_start_fails_the_batch(
    phase3: dict[str, Any], tanitjobs: DataSource, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(batch_id: UUID) -> None:
        raise OSError("no python")

    monkeypatch.setattr(import_launcher, "_spawn", broken)

    response = _launch(phase3["admin"], tanitjobs)

    assert response.status_code == 503
    assert ImportBatch.objects.get(source=tanitjobs).status == "FAILED"


# -- the launched process: offer_import --batch-id ------------------------------


class FakeScraper:
    """Yields the same two offers for every keyword, like overlapping searches."""

    def __init__(self) -> None:
        self.searches: list[tuple[str, int | None]] = []

    def __enter__(self) -> "FakeScraper":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def scrape(
        self,
        keyword: str,
        *,
        max_pages: int | None,
        cards_per_page_limit: int | None,
        skip_external_ids: Collection[str],
    ) -> Iterator[ScrapedOffer]:
        self.searches.append((keyword, max_pages))
        for external_id in ("9001", "9002"):
            if external_id in skip_external_ids:
                continue
            yield ScrapedOffer(
                source="tanitjobs",
                offer_url=f"https://www.tanitjobs.com/job/{external_id}/offre/",
                external_id=external_id,
                title=f"Offre {external_id}",
                company_name="Acme",
                location_raw="Tunis, Tunis",
                description="Une description.",
                accepting_applications=True,
            )


def test_launched_run_uses_configured_keywords_and_one_batch(
    phase3: dict[str, Any],
    tanitjobs: DataSource,
    spawned: list[UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Real runs drop the idle connection after the browser phase; the test transaction
    # must keep its connection.
    monkeypatch.setattr(django.db, "close_old_connections", lambda: None)
    DataSource.objects.filter(pk=tanitjobs.pk).update(
        configuration_json={"keywords": ["", "informatique"], "max_pages": 3}
    )
    batch_id = _launch(phase3["admin"], tanitjobs).json()["id"]
    scraper = FakeScraper()

    counts = offer_import.run_import(
        "tanitjobs", None, scraper=scraper, batch_id=batch_id, headless=True
    )

    assert scraper.searches == [("", 3), ("informatique", 3)]
    assert counts == {"ADDED": 2}  # the second keyword's duplicates are not rows
    batch = ImportBatch.objects.get(pk=batch_id)
    assert batch.status == "COMPLETED"
    assert batch.added_count == 2
    assert ImportBatch.objects.count() == 1
    assert JobOffer.objects.filter(source=tanitjobs, status="PUBLISHED").count() == 2


def test_cli_fails_a_batch_whose_source_has_no_scraper(
    phase3: dict[str, Any], tanitjobs: DataSource, spawned: list[UUID]
) -> None:
    DataSource.objects.filter(pk=tanitjobs.pk).update(name="Unknown board")
    batch_id = _launch(phase3["admin"], tanitjobs).json()["id"]

    assert offer_import.main(["--batch-id", batch_id]) == 1
    assert ImportBatch.objects.get(pk=batch_id).status == "FAILED"


def test_cli_fails_the_batch_when_the_source_was_revoked_after_the_click(
    phase3: dict[str, Any], tanitjobs: DataSource, spawned: list[UUID]
) -> None:
    batch_id = _launch(phase3["admin"], tanitjobs).json()["id"]
    DataSource.objects.filter(pk=tanitjobs.pk).update(is_authorized=False)

    assert offer_import.main(["--batch-id", batch_id]) == 1
    assert ImportBatch.objects.get(pk=batch_id).status == "FAILED"


# -- editing run settings, scheduled runs -------------------------------------


@pytest.mark.parametrize(
    ("patch", "still_authorized"),
    [
        ({"configuration_json": {"keywords": ["informatique"], "max_pages": 1}}, True),
        ({"configuration_json": {}}, True),
        ({"name": "Tanitjobs.com"}, True),
        ({"configuration_json": {"keywords": [""], "proxy": "x"}}, False),
        ({"base_url": "https://example.tn/"}, False),
        ({"type": "CSV"}, False),
        # What the admin form sends: every field, only the keywords changed.
        (
            {
                "name": "Tanitjobs",
                "type": "WEB_SCRAPING",
                "base_url": "https://www.tanitjobs.com/",
                "configuration_json": {"keywords": ["informatique"]},
            },
            True,
        ),
    ],
)
def test_only_run_settings_keep_the_authorization(
    phase3: dict[str, Any], tanitjobs: DataSource, patch: dict[str, Any], still_authorized: bool
) -> None:
    DataSource.objects.filter(pk=tanitjobs.pk).update(configuration_json={"keywords": [""]})

    response = _client(phase3["admin"]).patch(
        f"/api/v1/data-sources/{tanitjobs.pk}/", patch, format="json"
    )

    assert response.status_code == 200, response.content
    tanitjobs.refresh_from_db()
    assert tanitjobs.is_authorized is still_authorized


def test_scheduled_run_creates_a_system_batch(tanitjobs: DataSource) -> None:
    from backend.apps.imports.services import batch_processing
    from backend.apps.platform.models import AuditLog

    batch = batch_processing.prepare_scheduled_import("Tanitjobs")

    assert batch is not None and batch.status == "RUNNING"
    audit = AuditLog.objects.get(entity_id=batch.pk)
    assert (audit.actor_type, audit.action) == ("SYSTEM", "imports.batch.schedule")


def test_scheduled_run_is_skipped_while_an_admin_run_is_going(
    phase3: dict[str, Any], tanitjobs: DataSource, spawned: list[UUID]
) -> None:
    assert _launch(phase3["admin"], tanitjobs).status_code == 202

    assert offer_import.main(["tanitjobs", "--scheduled", "--headless"]) == 0
    assert ImportBatch.objects.filter(source=tanitjobs).count() == 1


def test_scheduled_run_of_an_unauthorized_source_is_refused(tanitjobs: DataSource) -> None:
    DataSource.objects.filter(pk=tanitjobs.pk).update(is_authorized=False)

    assert offer_import.main(["tanitjobs", "--scheduled", "--headless"]) == 1
    assert not ImportBatch.objects.exists()
