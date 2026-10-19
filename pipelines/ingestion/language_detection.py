# Placement: pipelines/ingestion/language_detection.py
"""Language of an offer description, limited to the languages we store.

Pure Python + the `lingua-language-detector` package; no Django. Kept in its own
module so the library can be swapped without touching the adapter.

Returns an ISO 639-1 code ("fr", "en", "ar") or None when unsure. The service
maps the code to a taxonomy.Language row; a code with no row stays empty.

Detection only among fr/en/ar would force a Spanish text into one of them. A few
extra "decoy" languages are therefore included: if one of them wins, the answer
is None instead of a wrong code.
"""

from functools import lru_cache

from lingua import Language, LanguageDetector, LanguageDetectorBuilder

MIN_TEXT_LENGTH = 40  # shorter texts give unreliable results
MIN_CONFIDENCE = 0.8

_STORED = {Language.FRENCH: "fr", Language.ENGLISH: "en", Language.ARABIC: "ar"}
_DECOYS = (
    Language.GERMAN,
    Language.SPANISH,
    Language.ITALIAN,
    Language.PORTUGUESE,
    Language.DUTCH,
    Language.TURKISH,
)


@lru_cache(maxsize=1)
def _detector() -> LanguageDetector:
    return LanguageDetectorBuilder.from_languages(*_STORED, *_DECOYS).build()


def detect_language_code(text: str | None) -> str | None:
    cleaned = " ".join(text.split()) if text else ""
    if len(cleaned) < MIN_TEXT_LENGTH:
        return None
    best = _detector().compute_language_confidence_values(cleaned)[0]
    if best.value < MIN_CONFIDENCE:
        return None
    return _STORED.get(best.language)
