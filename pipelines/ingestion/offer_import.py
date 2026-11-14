# Placement: pipelines/ingestion/offer_import.py
"""Entry point: scrape -> adapt -> hand each offer to the import services.

Run from the repository root:

    uv run python -m pipelines.ingestion.offer_import tanitjobs "python" --max-pages 1
    uv run python -m pipelines.ingestion.offer_import tanitjobs      # configured keywords
    uv run python -m pipelines.ingestion.offer_import --batch-id <id> --headless  # admin launch

Django models are never imported here. The services are imported lazily, after
Django is configured, so this module also loads without a Django environment.
"""

import argparse
import logging
import os
import sys
from collections.abc import Callable, Mapping, Sequence
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
    # Used when no keyword is given (admin button, scheduler). "" is an empty search,
    # which on Tanitjobs lists offers of every field (decision 2026-11-14).
    default_keywords: tuple[str, ...] = ("",)
    default_max_pages: int = 2


SOURCES: dict[str, SourceConfig] = {
    "tanitjobs": SourceConfig(
        name="Tanitjobs",
        source_type="WEB_SCRAPING",
        base_url="https://www.tanitjobs.com/",
        acquisition_method="browser automation (Playwright via SeleniumBase)",
        scraper_factory=lambda headless: TanitJobsScraper(headless=headless),
    ),
}


def automatic_plan(config: SourceConfig, configuration: Any) -> tuple[list[str], int]:
    """Keywords and page limit for a run without an explicit keyword.

    The source's configuration_json may override the defaults:
    {"keywords": ["", "informatique"], "max_pages": 2}. Invalid values fall back to
    the defaults instead of failing the run.
    """
    settings = configuration if isinstance(configuration, Mapping) else {}
    keywords = settings.get("keywords")
    if not (isinstance(keywords, list) and keywords and all(isinstance(k, str) for k in keywords)):
        keywords = list(config.default_keywords)
    max_pages = settings.get("max_pages")
    if not (isinstance(max_pages, int) and not isinstance(max_pages, bool) and max_pages > 0):
        max_pages = config.default_max_pages
    return list(dict.fromkeys(keyword.strip() for keyword in keywords)), max_pages


def run_import(
    source_key: str,
    keywords: Sequence[str] | None,
    *,
    max_pages: int | None = None,
    cards_per_page_limit: int | None = None,
    refresh: bool = False,
    headless: bool = False,
    scraper: Any = None,
    batch_id: str | None = None,
) -> dict[str, int]:
    """Returns row counts by status. One batch covers every keyword of the run.

    keywords=None uses automatic_plan() (source configuration, else the defaults).
    batch_id continues a batch prepared by the admin launcher instead of opening one.
    `scraper` can be injected (used by tests).
    """
    from django.db import close_old_connections

    from backend.apps.imports.services import batch_processing as imports
    from backend.apps.recruitment.services import import_reconciliation as reconciliation

    config = SOURCES[source_key]
    if batch_id is None:
        source = imports.get_or_create_source(
            name=config.name,
            source_type=config.source_type,
            base_url=config.base_url,
            acquisition_method=config.acquisition_method,
        )
        run = imports.start_import(source)  # refuses an unauthorized source before any browser
    else:
        run = imports.resume_import(batch_id)
        source = run.batch.source

    failed = False
    scrape_error: BaseException | None = None
    try:
        if keywords is None:
            keywords, planned_pages = automatic_plan(config, source.configuration_json)
            max_pages = max_pages if max_pages is not None else planned_pages
        logger.info("Keywords %s, max pages per keyword %s", list(keywords), max_pages)

        # Known offers are not revisited unless --refresh (saves ~6 s per skipped page).
        skip_ids = set() if refresh else reconciliation.known_external_ids(source)
        scraper = scraper or config.scraper_factory(headless)

        # Phase 1: browser. The sync Playwright API keeps an asyncio loop running in this
        # thread, and Django refuses ORM calls while one is running. So nothing touches
        # the database inside this block: offers are only collected.
        collected: list[ScrapedOffer] = []
        seen: set[str] = set()
        try:
            with scraper:
                for keyword in keywords:
                    for scraped in scraper.scrape(
                        keyword,
                        max_pages=max_pages,
                        cards_per_page_limit=cards_per_page_limit,
                        skip_external_ids=skip_ids,
                    ):
                        if scraped.external_id is not None:
                            if scraped.external_id in seen:
                                continue  # already found under an earlier keyword
                            seen.add(scraped.external_id)
                            skip_ids.add(scraped.external_id)
                        collected.append(scraped)
        except BaseException as exc:  # keep what was collected, even on Ctrl+C
            scrape_error = exc
            logger.error("Scraping stopped early after %d offers: %r", len(collected), exc)

        # Phase 2: database. The browser is closed, so the ORM is allowed again.
        close_old_connections()  # the connection may have idled out during a long scrape
        failed = scrape_error is not None
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
    parser.add_argument("source", nargs="?", choices=sorted(SOURCES))
    parser.add_argument(
        "keyword",
        nargs="?",
        default=None,
        help="omit to use the source's configured keywords (default: empty search, every field)",
    )
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--cards-per-page", type=int, default=None)
    parser.add_argument("--refresh", action="store_true", help="revisit offers already stored")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--batch-id", help="run a batch prepared by the admin launcher")
    args = parser.parse_args(argv)
    if args.source is None and args.batch_id is None:
        parser.error("give a source (e.g. tanitjobs) or --batch-id")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings.development")
    import django

    django.setup()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    from backend.apps.imports.services import batch_processing as imports

    source_key = args.source
    if source_key is None:
        name = imports.batch_source_name(args.batch_id)
        source_key = next((key for key, cfg in SOURCES.items() if cfg.name == name), None)
        if source_key is None:
            imports.mark_batch_failed(args.batch_id)
            print(f"No scraper for the source of batch {args.batch_id} ({name}).", file=sys.stderr)
            return 1

    try:
        counts = run_import(
            source_key,
            [args.keyword] if args.keyword is not None else None,
            max_pages=args.max_pages,
            cards_per_page_limit=args.cards_per_page,
            refresh=args.refresh,
            headless=args.headless,
            batch_id=args.batch_id,
        )
    except imports.SourceNotAuthorized as exc:
        if args.batch_id:
            imports.mark_batch_failed(args.batch_id)
        print(
            f"Refused: {exc}\nApprove the source first (see the data_sources row).", file=sys.stderr
        )
        return 1
    except BaseException:
        if args.batch_id:
            imports.mark_batch_failed(args.batch_id)  # no-op when the batch was finished
        raise
    print("Import finished:", counts or "no rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
