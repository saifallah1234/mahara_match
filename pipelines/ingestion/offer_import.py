# Placement: pipelines/ingestion/offer_import.py
"""Entry point: scrape -> adapt -> hand each offer to the import services.

Run from the repository root:

    uv run python -m pipelines.ingestion.offer_import tanitjobs "python" --max-pages 1

Django models are never imported here. The services are imported lazily, after
Django is configured, so this module also loads without a Django environment.
"""

import argparse
import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pipelines.ingestion.offer_adapter import OfferRejected, adapt_offer
from pipelines.ingestion.scraped_offer import ScrapedOffer
from pipelines.ingestion.tanitjobs import TanitJobsScraper

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceConfig:
    name: str
    source_type: str  # provisional vocabulary (Q24)
    base_url: str
    acquisition_method: str
    scraper_factory: Callable[[bool], Any]  # headless -> scraper


SOURCES: dict[str, SourceConfig] = {
    "tanitjobs": SourceConfig(
        name="Tanitjobs",
        source_type="WEB_SCRAPING",
        base_url="https://www.tanitjobs.com/",
        acquisition_method="browser automation (Playwright via SeleniumBase)",
        scraper_factory=lambda headless: TanitJobsScraper(headless=headless),
    ),
}


def run_import(
    source_key: str,
    keyword: str,
    *,
    max_pages: int | None = None,
    cards_per_page_limit: int | None = None,
    refresh: bool = False,
    headless: bool = False,
    scraper: Any = None,
) -> dict[str, int]:
    """Returns row counts by status. `scraper` can be injected (used by tests)."""
    from django.db import close_old_connections

    from backend.apps.imports.services import batch_processing as imports
    from backend.apps.recruitment.services import import_reconciliation as reconciliation

    config = SOURCES[source_key]
    source = imports.get_or_create_source(
        name=config.name,
        source_type=config.source_type,
        base_url=config.base_url,
        acquisition_method=config.acquisition_method,
    )
    run = imports.start_import(source)  # refuses an unauthorized source before any browser opens

    # Known offers are not revisited unless --refresh (saves ~6 s per skipped page).
    skip_ids = set() if refresh else reconciliation.known_external_ids(source)
    scraper = scraper or config.scraper_factory(headless)

    # Phase 1: browser. The sync Playwright API keeps an asyncio loop running in this
    # thread, and Django refuses ORM calls while one is running. So nothing touches
    # the database inside this block: offers are only collected.
    collected: list[ScrapedOffer] = []
    scrape_error: BaseException | None = None
    try:
        with scraper:
            for scraped in scraper.scrape(
                keyword,
                max_pages=max_pages,
                cards_per_page_limit=cards_per_page_limit,
                skip_external_ids=skip_ids,
            ):
                collected.append(scraped)
    except BaseException as exc:  # keep what was collected, even on Ctrl+C
        scrape_error = exc
        logger.error("Scraping stopped early after %d offers: %r", len(collected), exc)

    # Phase 2: database. The browser is closed, so the ORM is allowed again.
    close_old_connections()  # the connection may have idled out during a long scrape
    failed = scrape_error is not None
    try:
        for row_number, scraped in enumerate(collected, start=1):
            _process(imports, run, row_number, scraped)
    except BaseException:
        failed = True
        raise
    finally:
        counts = imports.finish_import(run, failed=failed)
        rejections = imports.rejection_summary(run)
        if rejections:
            logger.info("Rejected rows by reason: %s", rejections)

    if scrape_error is not None:
        raise scrape_error
    return counts


def _process(imports: Any, run: Any, row_number: int, scraped: ScrapedOffer) -> None:
    payload = scraped.to_payload()
    try:
        mapped = adapt_offer(scraped)
    except OfferRejected as exc:
        imports.reject_row(
            run,
            row_number=row_number,
            external_id=scraped.external_id,
            payload=payload,
            error_code=exc.code,
            error_message=str(exc),
        )
        return
    imports.accept_row(
        run,
        row_number=row_number,
        external_id=mapped.external_id,
        payload=payload,
        fields=mapped.to_model_fields(),
        description_language_code=mapped.description_language_code,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import job offers from an external source.")
    parser.add_argument("source", choices=sorted(SOURCES))
    parser.add_argument("keyword")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--cards-per-page", type=int, default=None)
    parser.add_argument("--refresh", action="store_true", help="revisit offers already stored")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args(argv)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings.development")
    import django

    django.setup()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    from backend.apps.imports.services.batch_processing import SourceNotAuthorized

    try:
        counts = run_import(
            args.source,
            args.keyword,
            max_pages=args.max_pages,
            cards_per_page_limit=args.cards_per_page,
            refresh=args.refresh,
            headless=args.headless,
        )
    except SourceNotAuthorized as exc:
        print(
            f"Refused: {exc}\nApprove the source first (see the data_sources row).", file=sys.stderr
        )
        return 1
    print("Import finished:", counts or "no rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
