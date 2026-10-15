"""Request language and intent routing for the ANETI agent (EN/FR/AR).

Routing is keyword-based and conservative: anything not recognised for the
caller's role is ``unsupported`` and never calls a tool.
"""

from __future__ import annotations

import re
from typing import Literal

from ai.retrieval.lexical.scoring import normalize

Language = Literal["en", "fr", "ar"]
Role = Literal["candidate", "recruiter"]

CANDIDATE_JOB_SEARCH = "candidate_job_search"
RECRUITER_CANDIDATE_SEARCH = "recruiter_candidate_search"
RECRUITER_OFFER_SEARCH = "recruiter_offer_search"
UNSUPPORTED = "unsupported"

_ARABIC_LETTER = re.compile(r"[؀-ۿ]")
_LATIN_LETTER = re.compile(r"[a-z]")
# Words that are also English ("me") are left out: they cannot decide the language.
_FRENCH_MARKERS = frozenset(
    """
    je j moi mon ma mes vous votre vos quels quelles quel quelle des les une pour avec dans
    sur emploi emplois offre offres poste postes travail formation formations correspond
    correspondent trouve trouver cherche chercher recommande recommander candidat candidats
    profil profils nos notre
    """.split()
)

# Patterns run on normalised text: casefolded, accents stripped, Arabic alef unified.
_CANDIDATE_JOBS = {
    "en": (
        r"\b(?:what|which) jobs? (?:match|fit)\b",
        r"\bmatch(?:ing)? jobs?\b",
        r"\bfind (?:me )?(?:a )?jobs?\b",
        r"\brecommend (?:me )?(?:a )?jobs?\b",
        r"\brecommend job opportunities\b",
        r"\bjob (?:recommendations?|offers?|openings?|opportunities)\b",
        r"\bjobs? for me\b",
    ),
    "fr": (
        r"\boffres? d.?emploi\b",
        r"\bemplois?\b",
        r"\b(?:trouve|cherche|recommande|propose)\w* (?:moi |nous )?(?:un |une |des )?"
        r"(?:postes?|offres?|travail)\b",
        r"\b(?:quels|quel) postes?\b",
        r"\bquelles offres\b",
        r"\boffres? (?:qui )?(?:me )?correspond",
    ),
    "ar": (
        r"وظيف",
        r"وظايف",
        r"عروض (?:ال)?عمل",
        r"عرض عمل",
        r"فرص (?:ال)?عمل",
        r"فرصة عمل",
    ),
}
_CANDIDATE_UNSUPPORTED = (
    r"\b(?:cv|resume|apply|application|applications)\b",
    r"\b(?:postuler|candidature|candidatures|lettre de motivation)\b",
    r"سيرة ذاتية|السيرة الذاتية|سيرتي|تقديم طلب|الترشح",
)

# Plural "profiles" only: "my profile" is a candidate talking about themselves.
_RECRUITER_CANDIDATES = (
    r"\b(?:candidates?|profiles|talents?)\b",
    r"\b(?:candidats?|candidates?|profils|talents?)\b",
    r"مرشح|ملفات|كفاءات",
)
_RECRUITER_OWN_OFFERS = (
    r"\b(?:my|our) (?:job )?(?:offers?|postings?|openings?|jobs?)\b",
    r"\b(?:mes|nos) (?:offres?|postes?|annonces?)\b",
    r"عروضي|عروضنا|عروض شركتي|عروض الشركة",
)
# Applicants' submitted CVs are out of scope for the agent.
_RECRUITER_UNSUPPORTED = (
    r"\b(?:cv|cvs|resume|resumes|applicants?|applications?)\b",
    r"\b(?:candidatures?|postulants?)\b",
    r"سيرة ذاتية|السيرة الذاتية|السير الذاتية|طلبات التوظيف|المتقدمين",
)
_OFFER_REFERENCE = r"\b(?:offer|posting|offre|annonce|poste)\b|عرض"


def detect_language(prompt: str) -> Language:
    text = normalize(prompt)
    if len(_ARABIC_LETTER.findall(text)) > len(_LATIN_LETTER.findall(text)):
        return "ar"
    words = set(re.findall(r"[a-z]+", text))
    return "fr" if words & _FRENCH_MARKERS else "en"


def route_request(role: Role, prompt: str) -> str:
    """Return the route for this role, or ``unsupported``."""
    text = " ".join(normalize(prompt).split())
    if role == "candidate":
        if any(re.search(pattern, text) for pattern in _CANDIDATE_UNSUPPORTED):
            return UNSUPPORTED
        if any(re.search(p, text) for patterns in _CANDIDATE_JOBS.values() for p in patterns):
            return CANDIDATE_JOB_SEARCH
    elif role == "recruiter":
        if any(re.search(pattern, text) for pattern in _RECRUITER_UNSUPPORTED):
            return UNSUPPORTED
        if any(re.search(pattern, text) for pattern in _RECRUITER_CANDIDATES):
            return RECRUITER_CANDIDATE_SEARCH
        if any(re.search(pattern, text) for pattern in _RECRUITER_OWN_OFFERS):
            return RECRUITER_OFFER_SEARCH
    return UNSUPPORTED


def mentions_offer(prompt: str) -> bool:
    """True when a recruiter request may name one of their offers ("candidates for offer X")."""
    return re.search(_OFFER_REFERENCE, " ".join(normalize(prompt).split())) is not None
