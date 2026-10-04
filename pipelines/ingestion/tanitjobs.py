"""Tanitjobs connector: reads public listings and yields ScrapedOffer objects.

What this module does NOT do (compared with the old scraper):
- no login and no credentials (listings are read without an account),
- no auto-apply, cover letters or application logs,
- no JSON files: results are yielded, and the import service decides what to store,
- no translation or inference: labels stay raw, unknown values stay None.

It never imports Django. Browser lifecycle comes from the existing BaseScraper.
"""

import logging
from collections.abc import Collection, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin

# Adjust these two imports to wherever the team places the files.
from pipelines.ingestion.base_scraper import BaseScraper
from pipelines.ingestion.scraped_offer import ScrapedOffer

logger = logging.getLogger(__name__)

SOURCE = "tanitjobs"
BASE_URL = "https://www.tanitjobs.com/"

DESCRIPTION_HEADING = "Description de l'emploi"
REQUIREMENTS_HEADING = "Exigences de l'emploi"
EXPIRATION_HEADING = "Date d'expiration"
EXPIRATION_FORMAT = "%d/%m/%Y"

SEARCH_SETTLE_SECONDS = 5
PAGE_SETTLE_SECONDS = 3
POLITE_DELAY_SECONDS = 3
MAX_CONSECUTIVE_FAILURES = 5


# ---------------------------------------------------------------------------
# Pure helpers: no browser involved, so they are easy to unit-test.
# ---------------------------------------------------------------------------


def none_if_blank(text: str | None) -> str | None:
    """'' and whitespace-only become None: 'not shown' must not look like data."""
    if text is None:
        return None
    text = text.strip()
    return text or None


def clean_url(href: str | None, base: str = BASE_URL) -> str | None:
    """Absolute URL without tracking parameters (?backPage=..., ?searchID=...)."""
    if href is None or not href.strip():
        return None
    return urljoin(base, href.strip().split("?")[0].split("#")[0])


def still_open(expiration_raw: str | None, today: date | None = None) -> bool | None:
    """True/False when the expiration date is readable, None when unknown."""
    raw = none_if_blank(expiration_raw)
    if raw is None:
        return None
    try:
        expires = datetime.strptime(raw, EXPIRATION_FORMAT).date()
    except ValueError:
        return None
    return expires >= (today or date.today())


# ---------------------------------------------------------------------------
# Private intermediate objects: what the search-results page and the detail
# page each contribute. They are merged into one ScrapedOffer at the end.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Card:
    external_id: str | None
    offer_url: str
    title: str | None
    company_name: str | None
    location_raw: str | None
    employment_type_raw: str | None
    date_posted_raw: str | None


@dataclass(frozen=True, slots=True)
class _Details:
    description: str | None
    expiration_date_raw: str | None
    accepting_applications: bool | None


class TanitJobsScraper(BaseScraper):
    source = SOURCE

    def __init__(self, *, headless: bool = False) -> None:
        super().__init__(base_url=BASE_URL)
        self.headless = headless

    def __enter__(self) -> "TanitJobsScraper":
        self.start_browser(headless=self.headless)
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self.sb is not None:  # start_browser may have failed before sb existed
            self.close_browser()

    # -- public entry point -------------------------------------------------

    def scrape(
        self,
        keyword: str,
        *,
        max_pages: int | None = None,
        cards_per_page_limit: int | None = None,
        skip_external_ids: Collection[str] = (),
    ) -> Iterator[ScrapedOffer]:
        """Search `keyword` and yield one ScrapedOffer per posting.

        max_pages / cards_per_page_limit: explicit caps for testing (None = no cap).
        skip_external_ids: ids the caller already has; their detail pages are not
        visited and nothing is yielded for them.
        """
        self._open_search(keyword)
        cards = self._collect_cards(max_pages, cards_per_page_limit)
        logger.info("Collected %d cards for %r", len(cards), keyword)

        consecutive_failures = 0
        for card in cards:
            if card.external_id is not None and card.external_id in skip_external_ids:
                continue

            self.sb.sleep(POLITE_DELAY_SECONDS)
            try:
                details = self._extract_details(card.offer_url)
            except Exception as err:
                consecutive_failures += 1
                logger.exception("Detail page failed, skipping: %s", card.offer_url)
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    raise RuntimeError(
                        f"{consecutive_failures} detail pages failed in a row; "
                        "the site or the browser session is likely broken."
                    ) from err
                continue

            consecutive_failures = 0
            yield self._to_offer(card, details)

    # -- step 1: run the search ---------------------------------------------

    def _open_search(self, keyword: str) -> None:
        if not self.page.url.startswith(BASE_URL):
            self.page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        search_input = self.page.get_by_placeholder("Mots Clés")
        search_input.wait_for(state="visible", timeout=30000)
        search_input = self.page.get_by_placeholder("Mots Clés")
        search_input.wait_for(state="visible")
        search_input.fill(keyword)
        search_input.press("Enter")
        self.sb.sleep(SEARCH_SETTLE_SECONDS)

    # -- step 2: walk the result pages and read the cards -------------------

    def _collect_cards(
        self, max_pages: int | None, cards_per_page_limit: int | None
    ) -> list[_Card]:
        cards: dict[str, _Card] = {}  # keyed by URL: the same job can appear twice
        page_number = 1
        while True:
            if page_number > 1 and not self._go_to_next_page():
                logger.info("No next-page link after page %d, stopping.", page_number - 1)
                break

            page_cards = self._read_cards_on_page(cards_per_page_limit)
            if not page_cards:
                logger.info("Page %d has no cards, stopping.", page_number)
                break

            for card in page_cards:
                cards.setdefault(card.offer_url, card)

            if max_pages is not None and page_number >= max_pages:
                break
            page_number += 1
        return list(cards.values())

    def _go_to_next_page(self) -> bool:
        next_link = self.page.locator("a.sj-page-btn.sj-arrow").filter(has_text="→")
        if next_link.count() == 0:
            return False
        next_link.first.click()
        self.sb.sleep(SEARCH_SETTLE_SECONDS)
        return True

    def _read_cards_on_page(self, limit: int | None) -> list[_Card]:
        job_cards = self.page.locator(".sj-job-card")
        count = job_cards.count()
        if limit is not None:
            count = min(count, limit)

        cards: list[_Card] = []
        for i in range(count):
            card = job_cards.nth(i)
            href = card.locator("div.sj-card-title a").first.get_attribute("href")
            offer_url = clean_url(href)
            if offer_url is None:
                continue

            def text(selector: str, card=card) -> str | None:
                return none_if_blank(self._safe_text(lambda: card.locator(selector).first))

            cards.append(
                _Card(
                    # VERIFY: the DOM id must be stable across searches (see notes).
                    external_id=none_if_blank(card.get_attribute("id")),
                    offer_url=offer_url,
                    title=text("div.sj-card-title a"),
                    company_name=text("div.sj-card-company a"),
                    location_raw=text("span.sj-loc"),
                    employment_type_raw=text("span.sj-type"),
                    date_posted_raw=text("span.sj-card-date"),
                )
            )
        return cards

    # -- step 3: open one posting and read its sections ---------------------

    def _extract_details(self, offer_url: str) -> _Details:
        self.page.goto(offer_url, wait_until="domcontentloaded", timeout=30000)
        self.sb.sleep(PAGE_SETTLE_SECONDS)

        headings = self.page.locator("h3.details-body__title")
        contents = self.page.locator("div.details-body__content.content-text")
        heading_count, content_count = headings.count(), contents.count()
        if heading_count != content_count:
            logger.warning(
                "%s: %d headings but %d content blocks (structure mismatch)",
                offer_url,
                heading_count,
                content_count,
            )

        sections: dict[str, str] = {}
        for i in range(min(heading_count, content_count)):
            sections[headings.nth(i).inner_text().strip()] = contents.nth(i).inner_text().strip()

        parts = (sections.get(DESCRIPTION_HEADING), sections.get(REQUIREMENTS_HEADING))
        expiration_raw = none_if_blank(sections.get(EXPIRATION_HEADING))
        return _Details(
            description=none_if_blank("\n\n".join(part for part in parts if part)),
            expiration_date_raw=expiration_raw,
            accepting_applications=still_open(expiration_raw),
        )

    # -- step 4: merge card + details into the final object -----------------

    def _to_offer(self, card: _Card, details: _Details) -> ScrapedOffer:
        return ScrapedOffer(
            source=SOURCE,
            offer_url=card.offer_url,
            external_id=card.external_id,
            title=card.title,
            company_name=card.company_name,
            location_raw=card.location_raw,
            description=details.description,
            employment_type_raw=card.employment_type_raw,
            work_arrangement_raw=None,  # Tanitjobs shows no such field; never guessed here
            date_posted_raw=card.date_posted_raw,
            expiration_date_raw=details.expiration_date_raw,
            accepting_applications=details.accepting_applications,
        )
