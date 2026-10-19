# Placement: pipelines/ingestion/scraped_offer.py
"""ScrapedOffer: what a scraper reports about one job posting.

This is a plain data container (a "data transfer object"). It is NOT a Django
model: it has no table, no migration, and it never imports Django. Scrapers
create it; a later adapter/import service reads it and decides what to store.

Rule for every field: record only what the page actually showed. If the page
did not show it, the value is None. No guessing, no defaults that look like data.
"""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ScrapedOffer:
    # --- Identity: lets the import service recognize "I have seen this offer" ---
    source: str  # connector key, e.g. "tanitjobs" or "linkedin"
    offer_url: str  # canonical link candidates are sent to (tracking params removed)
    external_id: str | None = None  # the board's own id; the service rejects rows without one

    # --- Content exactly as displayed on the board ---
    title: str | None = None
    company_name: str | None = None
    location_raw: str | None = None
    description: str | None = None

    # --- Raw labels: translating them into our vocabulary happens later ---
    employment_type_raw: str | None = None  # e.g. "CDI", "Temps plein", "Full-time"
    work_arrangement_raw: str | None = None  # only if the page showed one; else None
    date_posted_raw: str | None = None  # e.g. "il y a 3 jours", "3 days ago"
    expiration_date_raw: str | None = None  # e.g. "31/12/2026"

    # --- Observed state; None means "unknown", not "open" ---
    accepting_applications: bool | None = None

    # --- Labeled values from the offer page's info box, exactly as displayed ---
    # e.g. {"Experience": "3 à 5 ans", "Niveau d'étude": "Licence, Bac + 3"}.
    # Only labels the page actually showed; the adapter decides what they mean.
    details: dict[str, str] = field(default_factory=dict)

    # --- Bookkeeping ---
    scraped_at: datetime = field(default_factory=_utc_now)
    extras: dict[str, Any] = field(default_factory=dict)  # source-specific leftovers

    def __post_init__(self) -> None:
        if not self.source or not self.offer_url:
            raise ValueError("ScrapedOffer requires a source and an offer_url.")

    def to_payload(self) -> dict[str, Any]:
        """JSON-safe dict, meant for import_rows.payload_json (row traceability)."""
        data = asdict(self)
        data["scraped_at"] = self.scraped_at.isoformat()
        return data
