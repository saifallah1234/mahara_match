# Placement: pipelines/document_processing/cv_adapter.py
"""Raw CV extraction -> a profile proposal shaped like the candidate's records.

Pure Python (no Django, no LLM), like pipelines/ingestion/offer_adapter.py. It only
reshapes and normalizes what the CV said: dates to ISO, a governorate from the
location, language codes and CEFR levels, a skill list. References (skills,
languages, education levels) are resolved to ids by the backend when the proposal
is shown, and nothing is written to the profile until the candidate confirms.
Anything that cannot be read stays None; the candidate fills it in.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from pipelines.ingestion.offer_vocabulary import (
    COUNTRY_CODE_BY_KEY,
    GOVERNORATE_BY_KEY,
    normalize_key,
)

PROPOSAL_VERSION = 1

_MONTHS = {
    "jan": 1, "janv": 1, "january": 1, "janvier": 1,
    "feb": 2, "fev": 2, "fevr": 2, "february": 2, "fevrier": 2,
    "mar": 3, "march": 3, "mars": 3,
    "apr": 4, "avr": 4, "april": 4, "avril": 4,
    "may": 5, "mai": 5,
    "jun": 6, "june": 6, "juin": 6,
    "jul": 7, "juil": 7, "july": 7, "juillet": 7,
    "aug": 8, "aou": 8, "august": 8, "aout": 8,
    "sep": 9, "sept": 9, "september": 9, "septembre": 9,
    "oct": 10, "october": 10, "octobre": 10,
    "nov": 11, "november": 11, "novembre": 11,
    "dec": 12, "december": 12, "decembre": 12,
}  # fmt: skip
_ONGOING = ("present", "aujourd", "en cours", "actuel", "current", "now", "ce jour")

_LANGUAGE_CODES = {
    "francais": "fr", "french": "fr", "fr": "fr",
    "anglais": "en", "english": "en", "en": "en",
    "arabe": "ar", "arabic": "ar", "ar": "ar", "العربية": "ar",
    "espagnol": "es", "spanish": "es",
    "allemand": "de", "german": "de", "deutsch": "de",
    "italien": "it", "italian": "it",
    "turc": "tr", "turkish": "tr",
    "chinois": "zh", "chinese": "zh",
}  # fmt: skip
_LEVEL_WORDS = (
    (("natif", "native", "maternelle", "mother tongue", "bilingue", "bilingual"), "C2"),
    (("courant", "fluent", "avance", "advanced", "excellent", "professionnel"), "C1"),
    (("intermediaire", "intermediate", "bon niveau", "good"), "B1"),
    (("notions", "debutant", "beginner", "basic", "elementaire", "elementary", "scolaire"), "A2"),
)


def build_proposal(extraction: dict[str, Any]) -> dict[str, Any]:
    """`extraction` is CVExtraction.model_dump(mode="json")."""
    personal = extraction.get("personal_information") or {}
    return {
        "version": PROPOSAL_VERSION,
        "identity": _identity(personal, extraction),
        "experiences": [_experience(item) for item in extraction.get("experience") or []],
        "educations": [_education(item) for item in extraction.get("education") or []],
        "skills": _skills(extraction.get("skills") or []),
        "languages": [_language(item) for item in extraction.get("spoken_languages") or []],
        "certifications": [_certification(item) for item in extraction.get("certifications") or []],
        "projects": [_project(item) for item in extraction.get("projects") or []],
    }


# -- identity ------------------------------------------------------------------


def split_full_name(full_name: str | None) -> tuple[str, str]:
    """'Yasmine Chakroun' -> ('Yasmine', 'Chakroun'); 'CHAKROUN Yasmine' -> ('Yasmine', 'CHAKROUN')."""
    words = (full_name or "").split()
    if not words:
        return "", ""
    upper = [w for w in words if len(w) > 1 and w.isupper()]
    if upper and len(upper) < len(words):
        return " ".join(w for w in words if w not in upper), " ".join(upper)
    return words[0], " ".join(words[1:])


def _identity(personal: dict[str, Any], extraction: dict[str, Any]) -> dict[str, Any]:
    first_name, last_name = split_full_name(personal.get("full_name"))
    governorate, city, country = _place(personal.get("location"))
    phone = (personal.get("phone") or "").strip()
    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": (personal.get("email") or "").strip(),
        "phone": phone[:30],
        "country_code": country or _country_from_phone(phone) or "",
        "governorate": governorate or "",
        "city": city or "",
        "headline": clean_text(extraction.get("headline"))[:200],
        "summary": clean_text(extraction.get("professional_summary")),
        "linkedin": personal.get("linkedin") or "",
        "github": personal.get("github") or "",
    }


def clean_text(text: str | None) -> str:
    """Drop markdown left by the PDF conversion: '**x**', '_|_' separators, backticks."""
    cleaned = re.sub(r"\s*_?\|_?\s*", " · ", text or "")
    cleaned = re.sub(r"\*\*|`|(?<!\w)_|_(?!\w)", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" ·")


def _place(location: str | None) -> tuple[str | None, str | None, str | None]:
    """'Ariana, Tunis' -> governorate 'Ariana', city 'Ariana'; country from a known name."""
    parts = [p.strip() for p in re.split(r"[,\-–/|]", location or "") if p.strip()]
    governorate = city = country = None
    for part in parts:
        key = normalize_key(part)
        if governorate is None and key in GOVERNORATE_BY_KEY:
            governorate = GOVERNORATE_BY_KEY[key]
        if country is None and key in COUNTRY_CODE_BY_KEY:
            country = COUNTRY_CODE_BY_KEY[key]
    if parts and normalize_key(parts[0]) not in COUNTRY_CODE_BY_KEY:
        city = parts[0][:100]
    if governorate and not country:
        country = "TN"
    return governorate, city, country


def _country_from_phone(phone: str) -> str | None:
    digits = re.sub(r"[^\d+]", "", phone)
    if digits.startswith(("+216", "00216")):
        return "TN"
    return None


# -- records ---------------------------------------------------------------------


def parse_cv_date(text: str | None, *, end: bool = False) -> str | None:
    """'Sept. 2024' -> '2024-09-01'; '03/2023' -> '2023-03-01'; '2021' -> '2021-01-01'
    (or '2021-12-31' when end=True); 'Present' -> None. ISO date or None."""
    if not text:
        return None
    cleaned = normalize_key(text)
    if any(word in cleaned for word in _ONGOING):
        return None
    numeric = re.search(r"\b(\d{1,2})[/.\-](\d{4})\b", text)  # before punctuation is removed
    if numeric and 1 <= int(numeric.group(1)) <= 12:
        return date(int(numeric.group(2)), int(numeric.group(1)), 1).isoformat()
    year_match = re.search(r"\b(19[5-9]\d|20\d{2})\b", cleaned)
    if not year_match:
        return None
    year = int(year_match.group(1))
    for word in re.findall(r"[a-z]+", cleaned):
        month = _MONTHS.get(word) or _MONTHS.get(word[:4]) or _MONTHS.get(word[:3])
        if month:
            return date(year, month, 1).isoformat()
    return date(year, 12, 31).isoformat() if end else date(year, 1, 1).isoformat()


def _year(text: str | None) -> int | None:
    match = re.search(r"\b(19[5-9]\d|20\d{2})\b", text or "")
    return int(match.group(1)) if match else None


def _experience(item: dict[str, Any]) -> dict[str, Any]:
    lines = [item.get("description") or ""]
    lines += [f"- {r}" for r in item.get("responsibilities") or [] if r]
    if item.get("technologies"):
        lines.append("Technologies : " + ", ".join(item["technologies"]))
    ongoing = bool(item.get("is_current"))
    return {
        "job_title": (item.get("job_title") or "")[:150],
        "organization_name": (item.get("company") or "")[:200],
        "start_date": parse_cv_date(item.get("start_date")),
        "end_date": None if ongoing else parse_cv_date(item.get("end_date"), end=True),
        "description": "\n".join(line for line in lines if line).strip(),
    }


def _education(item: dict[str, Any]) -> dict[str, Any]:
    ongoing = bool(item.get("is_current"))
    description = " - ".join(p for p in (item.get("degree"), item.get("description")) if p)
    return {
        "degree_level": item.get("degree_level") or None,
        "degree": item.get("degree") or "",
        "institution": (item.get("institution") or "")[:200],
        "field_of_study": (item.get("field_of_study") or "")[:150],
        "start_year": _year(item.get("start_date")),
        "end_year": None if ongoing else _year(item.get("end_date")),
        "description": description,
    }


def _skills(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"name": item["name"].strip()[:150], "category": item.get("category") or ""}
        for item in items
        if (item.get("name") or "").strip()
    ]


def cefr_level(proficiency: str | None) -> str | None:
    text = normalize_key(proficiency or "")
    explicit = re.search(r"\b([abc][12])\b", text)
    if explicit:
        return explicit.group(1).upper()
    for words, level in _LEVEL_WORDS:
        if any(word in text for word in words):
            return level
    return None


def _language(item: dict[str, Any]) -> dict[str, Any]:
    name = (item.get("name") or "").strip()
    return {
        "name": name,
        "code": _LANGUAGE_CODES.get(normalize_key(name)),
        "proficiency": item.get("proficiency") or "",
        "level": cefr_level(item.get("proficiency")),
    }


def _certification(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": (item.get("name") or "")[:200],
        "certification_organization": (item.get("issuer") or "")[:200],
        "issue_date": parse_cv_date(item.get("date")),
        "description": "",
    }


def _project(item: dict[str, Any]) -> dict[str, Any]:
    lines = [item.get("summary") or ""] + [f"- {h}" for h in item.get("highlights") or [] if h]
    github = item.get("github") or ""
    return {
        "name": (item.get("title") or "")[:200],
        "description": "\n".join(line for line in lines if line).strip(),
        "repository_url": github if github.startswith("http") else "",
        "technologies": [t.strip()[:150] for t in item.get("technologies") or [] if t.strip()],
    }
