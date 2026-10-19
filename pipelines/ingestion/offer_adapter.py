# Placement: pipelines/ingestion/offer_adapter.py
"""Adapter: ScrapedOffer -> values for the job_offers table.

This module is the ONLY place that knows job_offers column names for imports.
It has no Django, no database and no browser. It applies the priority rules
between the card and the info box, so a rule change touches this file only.

It does not resolve organization, created_by, source, status, skills,
description_language or education_level (those need database lookups or
undecided rules); the import service does that. Rows that cannot become a valid
offer raise OfferRejected with an error code, which the service records in
import_rows.error_code.

Priority between sources (first usable value wins):
- work_mode:      card tag -> info box "Mode de travail" -> ONSITE (agreed default)
- contract_type:  a real contract kind from card then info box; only if none,
                  a working-time label (FULL_TIME / PART_TIME); else ""
- experience, salary: info box only
- country/governorate/city: the card's location
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pipelines.ingestion.language_detection import detect_language_code
from pipelines.ingestion.offer_vocabulary import (
    CONTRACT_KIND_BY_KEY,
    COUNTRY_CODE_BY_KEY,
    DEFAULT_WORK_MODE,
    EXPERIENCE_BY_KEY,
    GOVERNORATE_BY_KEY,
    INFO_CONTRACT,
    INFO_EXPERIENCE,
    INFO_SALARY,
    INFO_WORK_MODE,
    WORK_MODE_BY_KEY,
    WORKING_TIME_BY_KEY,
    normalize_key,
)
from pipelines.ingestion.scraped_offer import ScrapedOffer

# Limits mirrored from the job_offers model so bad rows are rejected as data,
# not as database exceptions.
TITLE_MAX = 200
EXTERNAL_ID_MAX = 255
OFFER_URL_MAX = 500
COMPANY_NAME_MAX = 255
CITY_MAX = 100
SALARY_LIMIT = Decimal(10) ** 10  # numeric(12, 2) holds at most 10 integer digits

# Tanitjobs shows "31/12/2026". Add formats here when another source needs them.
DEADLINE_FORMATS = ("%d/%m/%Y",)

OFFER_CLOSED = "OFFER_CLOSED"


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
    work_mode: str
    experience_level: str
    country_code: str
    governorate: str
    city: str
    min_salary: Decimal | None  # monthly TND (team decision)
    max_salary: Decimal | None
    application_deadline: date | None
    easy_apply: bool
    company_name: str  # shown for imported offers; "" when the page shows none

    # --- Signals for the import service; NOT columns ---
    description_language_code: str | None  # service maps it to taxonomy.Language
    is_open: bool | None  # what the source reported; the service decides status

    def to_model_fields(self) -> dict[str, Any]:
        return {
            "external_id": self.external_id,
            "offer_url": self.offer_url,
            "title": self.title,
            "description": self.description,
            "contract_type": self.contract_type,
            "work_mode": self.work_mode,
            "experience_level": self.experience_level,
            "country_code": self.country_code,
            "governorate": self.governorate,
            "city": self.city,
            "min_salary": self.min_salary,
            "max_salary": self.max_salary,
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


def _labels(*raw_values: str | None) -> list[str]:
    """Comma-separated labels of several sources, in page order.

    Only commas split: "Freelance / Indépendant" is ONE label.
    """
    labels: list[str] = []
    for raw in raw_values:
        if raw:
            labels.extend(part for part in raw.split(",") if part.strip())
    return labels


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


# --- location ---------------------------------------------------------------

_LOCATION_SPLIT = re.compile(r"\s*[,;/|]\s*|\s+[-–—]\s+")


def parse_location(raw: str | None) -> tuple[str, str, str]:
    """Returns (country_code, governorate, city); each may be "" when unknown.

    Observed Tanitjobs format: "<place>, <governorate>, <country>" (the place and
    the country may be absent). Rules:
    - a last token naming a known country gives the country code;
    - in Tunisia (or when no country is given) the last remaining token must be a
      known governorate; the token before it is the city, and when there is none
      the governorate is copied into city ("Sfax, Tunisie" -> city "Sfax");
    - a known foreign country takes the first remaining token as city;
    - governorate is Tunisia-only; nothing else is guessed.
    The city is a loose place name (neighborhood, zone or town), by team decision.
    """
    text = _clean(raw)
    if text is None:
        return "", "", ""
    tokens = [t.strip() for t in _LOCATION_SPLIT.split(text) if t.strip()]

    country_code = ""
    if tokens:
        found = COUNTRY_CODE_BY_KEY.get(normalize_key(tokens[-1]))
        if found:
            country_code = found
            tokens.pop()

    if country_code in ("", "TN") and tokens:
        governorate = GOVERNORATE_BY_KEY.get(normalize_key(tokens[-1]))
        if governorate:
            prefix = tokens[:-1]
            city = prefix[-1] if prefix else governorate
            return "TN", governorate, city[:CITY_MAX]

    if (
        country_code and tokens
    ):  # e.g. "Paris, France", or a Tunisian town that is not a governorate
        return country_code, "", tokens[0][:CITY_MAX]
    return country_code, "", ""


# --- contract type, work mode, experience -------------------------------------


def parse_contract_type(*raw_values: str | None) -> str:
    keys = [normalize_key(label) for label in _labels(*raw_values)]
    for key in keys:
        if key in CONTRACT_KIND_BY_KEY:
            return CONTRACT_KIND_BY_KEY[key]
    for key in keys:
        if key in WORKING_TIME_BY_KEY:
            return WORKING_TIME_BY_KEY[key]
    return ""


def parse_work_mode(*raw_values: str | None) -> str:
    for label in _labels(*raw_values):
        mode = WORK_MODE_BY_KEY.get(normalize_key(label))
        if mode:
            return mode
    return DEFAULT_WORK_MODE


def parse_experience(raw: str | None) -> str:
    text = _clean(raw)
    return EXPERIENCE_BY_KEY.get(normalize_key(text), "") if text else ""


# --- salary -----------------------------------------------------------------

# Only the format seen so far: "Entre 2000 DT et 3000 DT". Anything else (for example
# "Confidentiel", other currencies, other phrasings) stays empty; the raw text is
# kept in import_rows.payload_json so unseen formats can be spotted later.
_AMOUNT = r"(\d+(?:[ ]\d{3})*(?:[.,]\d{1,2})?)"
_SALARY_RANGE = re.compile(
    rf"^entre\s+{_AMOUNT}\s*(?:dt|tnd)\s+et\s+{_AMOUNT}\s*(?:dt|tnd)$", re.IGNORECASE
)


def _to_decimal(amount: str) -> Decimal:
    return Decimal(amount.replace(" ", "").replace(",", "."))


def parse_salary(raw: str | None) -> tuple[Decimal | None, Decimal | None]:
    """(min, max) in TND per MONTH (team decision: salaries are monthly)."""
    text = _clean(raw)
    if text is None:
        return None, None
    match = _SALARY_RANGE.match(" ".join(text.split()))  # collapses tabs and non-breaking spaces
    if match is None:
        return None, None
    low, high = _to_decimal(match.group(1)), _to_decimal(match.group(2))
    if low > high or high >= SALARY_LIMIT:
        return None, None
    return low, high


# ---------------------------------------------------------------------------
# The adapter
# ---------------------------------------------------------------------------


def adapt_offer(offer: ScrapedOffer) -> MappedJobOffer:
    if offer.accepting_applications is False:
        raise OfferRejected(OFFER_CLOSED, "The source reports this offer as closed or expired.")

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

    info = {normalize_key(label): value for label, value in offer.details.items()}
    country_code, governorate, city = parse_location(offer.location_raw)
    min_salary, max_salary = parse_salary(info.get(INFO_SALARY))

    return MappedJobOffer(
        external_id=external_id,
        offer_url=url,
        title=title[:TITLE_MAX],  # full title survives in import_rows.payload_json
        description=description,
        contract_type=parse_contract_type(offer.employment_type_raw, info.get(INFO_CONTRACT)),
        work_mode=parse_work_mode(offer.work_arrangement_raw, info.get(INFO_WORK_MODE)),
        experience_level=parse_experience(info.get(INFO_EXPERIENCE)),
        country_code=country_code,
        governorate=governorate,
        city=city,
        min_salary=min_salary,
        max_salary=max_salary,
        application_deadline=parse_deadline(offer.expiration_date_raw),
        easy_apply=False,  # scraped offers always send candidates to the original site
        company_name=(_clean(offer.company_name) or "")[:COMPANY_NAME_MAX],
        description_language_code=detect_language_code(description),
        is_open=offer.accepting_applications,
    )
