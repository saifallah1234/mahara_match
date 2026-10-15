"""Token-overlap ranking over already-scoped documents (FR/AR/EN).

Normalisation: casefold, NFKD accent stripping (``données`` -> ``donnees``), Arabic
tashkeel removal and alef unification (``أ إ آ ٱ`` -> ``ا``), tatweel removal.
Latin and Arabic runs are split apart, so an attached prefix such as ``وSQL``
yields ``sql``. A slash compound keeps its whole form and its parts:
``CI/CD`` -> ``ci/cd``, ``ci``, ``cd``. Tokens shorter than two characters and
stop words are dropped. Documents sharing no term with the query are excluded.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

Key = tuple[str, str]

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#./-]*|[^\W\da-z_]+", re.UNICODE)
_ALEF_WASLA = "\u0671"
_TATWEEL = "\u0640"
_LIGATURES = str.maketrans({"œ": "oe", "æ": "ae"})

_ENGLISH = """
a an and are as at be by can for from have how in is it me my of on or show that the
their there this to what which who with you your
"""
_FRENCH = """
au aux avec ce ces dans de des du elle en est et il je la le les leur ma mes mon ne nous
ou par pas pour qu que quel quelle quelles quels qui sa se ses son sont sur un une vous
"""
_ARABIC = """
الى التي الذي الذين ان او على عن في قد كل لا لم ما ماذا مع من هل هذا هذه هو هي و
"""
# Stored already normalised: French without accents, Arabic with unified alef forms.
STOP_WORDS = frozenset((_ENGLISH + _FRENCH + _ARABIC).split())


def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    stripped = "".join(char for char in folded if not unicodedata.combining(char))
    return stripped.translate(_LIGATURES).replace(_ALEF_WASLA, "ا").replace(_TATWEEL, "")


def terms(text: str) -> set[str]:
    found: set[str] = set()
    for raw in _TOKEN.findall(normalize(text)):
        token = raw.rstrip("./-")
        candidates = [token, *token.split("/")] if "/" in token else [token]
        found.update(
            candidate
            for candidate in candidates
            if len(candidate) >= 2 and candidate not in STOP_WORDS
        )
    return found


def lexical_ranking(query: str, documents: Iterable[tuple[Key, str]]) -> list[Key]:
    """Rank documents by the number of distinct query terms they contain.

    Ties keep the documents' sort order by key so results are deterministic.
    """
    query_terms = terms(query)
    if not query_terms:
        return []
    scored = []
    for key, text in documents:
        overlap = len(query_terms & terms(text))
        if overlap:
            scored.append((overlap, key))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [key for _, key in scored]
