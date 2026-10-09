# Placement: pipelines/ingestion/offer_adapter.py
"""Adapter: ScrapedOffer -> values for the job_offers table.

This module is the ONLY place that knows job_offers column names for imports.
It is pure Python: no Django, no database, no browser.

It does not resolve organization, created_by, source, status, skills or language
(those need database lookups or undecided rules); the import service does that.
Rows that cannot become a valid offer raise OfferRejected with an error code,
which the service records in import_rows.error_code.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from pipelines.ingestion.scraped_offer import ScrapedOffer

# Limits mirrored from the job_offers model so bad rows are rejected as data,
# not as database exceptions.
TITLE_MAX = 200
EXTERNAL_ID_MAX = 255
OFFER_URL_MAX = 500
COMPANY_NAME_MAX = 255

# Tanitjobs shows "31/12/2026". Add formats here when another source needs them.
DEADLINE_FORMATS = ("%d/%m/%Y",)

# Settle-later table (Q24: contract_type vocabulary is undefined). Keys are the
# output of _key(raw label); values must be <= 30 chars. Empty on purpose:
# unmapped labels become "" and the raw label stays in import_rows.payload_json.
CONTRACT_TYPE_MAP: dict[str, str] = {}

# The 24 governorates of Tunisia. Spelling stored = this canonical form.
TUNISIAN_GOVERNORATES = (
    "Ariana",
    "Béja",
    "Ben Arous",
    "Bizerte",
    "Gabès",
    "Gafsa",
    "Jendouba",
    "Kairouan",
    "Kasserine",
    "Kébili",
    "Kef",
    "Mahdia",
    "Manouba",
    "Médenine",
    "Monastir",
    "Nabeul",
    "Sfax",
    "Sidi Bouzid",
    "Siliana",
    "Sousse",
    "Tataouine",
    "Tozeur",
    "Tunis",
    "Zaghouan",
)
_GOVERNORATE_ALIASES = {"le kef": "Kef", "la manouba": "Manouba", "mednine": "Médenine"}


class OfferRejected(Exception):
    """The scraped row cannot become a valid job offer."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class MappedJobOffer:
    # --- Columns of job_offers (exactly what to_model_fields() returns) ---
    external_id: str
    offer_url: str
    title: str
    description: str
    contract_type: str
    country_code: str
    governorate: str
    city: str
    application_deadline: date | None
    easy_apply: bool
    company_name: str  # shown for imported offers; "" when the page shows none

    # --- Signal for the import service; NOT a column ---
    is_open: bool | None  # what the source reported; the service decides status

    def to_model_fields(self) -> dict[str, Any]:
        return {
            "external_id": self.external_id,
            "offer_url": self.offer_url,
            "title": self.title,
            "description": self.description,
            "contract_type": self.contract_type,
            "country_code": self.country_code,
            "governorate": self.governorate,
            "city": self.city,
            "application_deadline": self.application_deadline,
            "easy_apply": self.easy_apply,
            "company_name": self.company_name,
        }


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    text = text.strip()
    return text or None


def _key(text: str) -> str:
    """Lowercase, accent-free, punctuation-free lookup key."""
    stripped = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]+", " ", stripped.lower()).strip()


_GOVERNORATE_BY_KEY = {_key(name): name for name in TUNISIAN_GOVERNORATES}
_GOVERNORATE_BY_KEY.update(_GOVERNORATE_ALIASES)
_LOCATION_SPLIT = re.compile(r"\s*[,;/|]\s*|\s+[-–—]\s+")
_COUNTRY_BY_KEY = {"tunisie": "TN", "tunisia": "TN"}


def parse_deadline(raw: str | None) -> date | None:
    text = _clean(raw)
    if text is None:
        return None
    for fmt in DEADLINE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_location(raw: str | None) -> tuple[str, str]:
    """Returns (country_code, governorate); either may be "" when not certain.

    Observed Tanitjobs format: "<place>, <governorate>, <country>" (the country
    and place parts may be absent). Rules:
    - a final token naming a known country gives the country code;
    - the last remaining token is the governorate, if it is a known one;
    - nothing else is guessed, and the place part (neighborhood, zone, town)
      is NOT stored in city: it mixes different kinds of place.
    """
    text = _clean(raw)
    if text is None:
        return "", ""
    tokens = [t for t in _LOCATION_SPLIT.split(text) if t.strip()]

    country_code = ""
    if tokens and _key(tokens[-1]) in _COUNTRY_BY_KEY:
        country_code = _COUNTRY_BY_KEY[_key(tokens.pop())]

    governorate = _GOVERNORATE_BY_KEY.get(_key(tokens[-1]), "") if tokens else ""
    if governorate:
        country_code = "TN"
    return country_code, governorate


def normalize_contract_type(raw: str | None) -> str:
    text = _clean(raw)
    return CONTRACT_TYPE_MAP.get(_key(text), "") if text else ""


# ---------------------------------------------------------------------------
# The adapter
# ---------------------------------------------------------------------------


def adapt_offer(offer: ScrapedOffer) -> MappedJobOffer:
    external_id = _clean(offer.external_id)
    if external_id is None:
        raise OfferRejected("MISSING_EXTERNAL_ID", "The source did not provide an offer id.")
    if len(external_id) > EXTERNAL_ID_MAX:
        raise OfferRejected("INVALID_EXTERNAL_ID", f"Offer id longer than {EXTERNAL_ID_MAX}.")

    title = _clean(offer.title)
    if title is None:
        raise OfferRejected("MISSING_TITLE", "The offer has no title.")

    description = _clean(offer.description)
    if description is None:
        raise OfferRejected("MISSING_DESCRIPTION", "The offer has no description.")

    url = offer.offer_url.strip()
    if not url.startswith("https://") or len(url) > OFFER_URL_MAX:
        raise OfferRejected("INVALID_OFFER_URL", "offer_url must be https and at most 500 chars.")

    country_code, governorate = parse_location(offer.location_raw)

    return MappedJobOffer(
        external_id=external_id,
        offer_url=url,
        title=title[:TITLE_MAX],  # full title survives in import_rows.payload_json
        description=description,
        contract_type=normalize_contract_type(offer.employment_type_raw),
        country_code=country_code,
        governorate=governorate,
        city="",
        application_deadline=parse_deadline(offer.expiration_date_raw),
        easy_apply=False,  # scraped offers always send candidates to the original site
        company_name=(_clean(offer.company_name) or "")[:COMPANY_NAME_MAX],
        is_open=offer.accepting_applications,
    )
