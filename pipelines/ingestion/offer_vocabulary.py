# Placement: pipelines/ingestion/offer_vocabulary.py
"""Lookup tables used by offer_adapter.py. DATA ONLY: edit these when the team
settles a vocabulary (Q24); no logic here except key normalization.

Every table is keyed by normalize_key(label): lowercase, accent-free, with
punctuation collapsed to single spaces, so "Contrat al Karama", "contrat  al-karama"
and "CONTRAT AL KARAMA" are the same key.
"""

import re
import unicodedata


def normalize_key(text: str) -> str:
    """Lowercase, accent-free, punctuation-free lookup key."""
    stripped = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]+", " ", stripped.lower()).strip()


# ---------------------------------------------------------------------------
# Info-box labels on the Tanitjobs detail page (already normalized).
# ---------------------------------------------------------------------------
INFO_CONTRACT = normalize_key("Type d'emploi désiré")
INFO_WORK_MODE = normalize_key("Mode de travail")
INFO_EXPERIENCE = normalize_key("Experience")
INFO_SALARY = normalize_key("Rémunération proposée")

# ---------------------------------------------------------------------------
# Work mode. Values must be WorkMode values (REMOTE / HYBRID / ONSITE).
# Tanitjobs only shows a tag for hybrid and remote offers, so ONSITE is the
# agreed default when nothing is shown. The default is applied by the adapter;
# the raw payload keeps the original "nothing shown".
# ---------------------------------------------------------------------------
WORK_MODE_BY_KEY: dict[str, str] = {
    "teletravail": "REMOTE",
    "remote": "REMOTE",
    "a distance": "REMOTE",
    "hybride": "HYBRID",
    "hybrid": "HYBRID",
    "presentiel": "ONSITE",
    "onsite": "ONSITE",
    "on site": "ONSITE",
}
DEFAULT_WORK_MODE = "ONSITE"

# ---------------------------------------------------------------------------
# Contract type (Q24: vocabulary still to be confirmed by the team). Max 30 chars.
# Real contract kinds win; working-time labels are only a fallback when the page
# lists no contract kind at all.
# ---------------------------------------------------------------------------
CONTRACT_KIND_BY_KEY: dict[str, str] = {
    "cdi": "CDI",
    "sivp": "SIVP",
    "contrat al karama": "KARAMA",
    "freelance independant": "FREELANCE",  # the site's label is "Freelance / Indépendant"
    "freelance": "FREELANCE",
    "saisonnier": "SEASONAL",
    "stage": "INTERNSHIP",
}
WORKING_TIME_BY_KEY: dict[str, str] = {
    "temps plein": "FULL_TIME",
    "temps partiel": "PART_TIME",
}

# ---------------------------------------------------------------------------
# Experience: the site's closed list, stored as the site's own label.
# "o a 1 an" is the letter-O variant produced by OCR; the real label uses a zero.
# ---------------------------------------------------------------------------
EXPERIENCE_BY_KEY: dict[str, str] = {
    "5 a 10 ans": "5 à 10 ans",
    "3 a 5 ans": "3 à 5 ans",
    "1 a 3 ans": "1 à 3 ans",
    "0 a 1 an": "0 à 1 an",
    "o a 1 an": "0 à 1 an",
    "debutant": "Débutant",
}

# ---------------------------------------------------------------------------
# Tunisia: the 24 governorates (stored spelling = this canonical form).
# ---------------------------------------------------------------------------
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
GOVERNORATE_BY_KEY: dict[str, str] = {normalize_key(name): name for name in TUNISIAN_GOVERNORATES}
GOVERNORATE_BY_KEY.update(_GOVERNORATE_ALIASES)

# ---------------------------------------------------------------------------
# Countries (ISO 3166-1 alpha-2) with French and English names. Only countries
# employers are likely to post for; a name not listed here leaves country_code
# blank (unknown) instead of guessing. Extend freely.
# ---------------------------------------------------------------------------
_COUNTRY_NAMES: dict[str, tuple[str, ...]] = {
    "TN": ("Tunisie", "Tunisia"),
    "FR": ("France",),
    "US": (
        "USA",
        "États-Unis",
        "Etats-Unis",
        "États-Unis d'Amérique",
        "United States",
        "United States of America",
    ),
    "CA": ("Canada",),
    "DE": ("Allemagne", "Germany"),
    "IT": ("Italie", "Italy"),
    "ES": ("Espagne", "Spain"),
    "BE": ("Belgique", "Belgium"),
    "CH": ("Suisse", "Switzerland"),
    "NL": ("Pays-Bas", "Netherlands", "Hollande"),
    "GB": ("Royaume-Uni", "United Kingdom", "UK", "Angleterre"),
    "LU": ("Luxembourg",),
    "IE": ("Irlande", "Ireland"),
    "PT": ("Portugal",),
    "AT": ("Autriche", "Austria"),
    "SE": ("Suède", "Sweden"),
    "NO": ("Norvège", "Norway"),
    "DK": ("Danemark", "Denmark"),
    "PL": ("Pologne", "Poland"),
    "RO": ("Roumanie", "Romania"),
    "TR": ("Turquie", "Turkey"),
    "LY": ("Libye", "Libya"),
    "DZ": ("Algérie", "Algeria"),
    "MA": ("Maroc", "Morocco"),
    "EG": ("Égypte", "Egypt"),
    "MR": ("Mauritanie", "Mauritania"),
    "SN": ("Sénégal", "Senegal"),
    "CI": ("Côte d'Ivoire", "Ivory Coast"),
    "CM": ("Cameroun", "Cameroon"),
    "GA": ("Gabon",),
    "ML": ("Mali",),
    "SA": ("Arabie Saoudite", "Saudi Arabia"),
    "AE": ("Émirats arabes unis", "United Arab Emirates", "UAE"),
    "QA": ("Qatar",),
    "KW": ("Koweït", "Kuwait"),
    "BH": ("Bahreïn", "Bahrain"),
    "OM": ("Oman",),
    "JO": ("Jordanie", "Jordan"),
    "LB": ("Liban", "Lebanon"),
}
COUNTRY_CODE_BY_KEY: dict[str, str] = {
    normalize_key(name): code for code, names in _COUNTRY_NAMES.items() for name in names
}
