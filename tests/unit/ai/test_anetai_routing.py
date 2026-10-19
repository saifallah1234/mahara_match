from typing import Any

import pytest

from ai.agents.anetai import BASELINE_ROUTE, resolve_route
from ai.agents.intents import (
    CANDIDATE_JOB_SEARCH,
    RECRUITER_CANDIDATE_SEARCH,
    RECRUITER_OFFER_SEARCH,
    UNSUPPORTED,
    detect_language,
    mentions_offer,
    route_request,
)
from ai.agents.templates import (
    candidate_search_reply,
    job_search_reply,
    own_offer_search_reply,
    unsupported_reply,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("prompt", "language"),
    [
        ("What jobs match my profile?", "en"),
        ("Find jobs for me", "en"),
        ("Can you show me offers in Python?", "en"),
        ("Trouve-moi un emploi", "fr"),
        ("Est-ce que des offres me correspondent ?", "fr"),
        ("Quels emplois correspondent à mon profil ?", "fr"),
        ("Trouve-moi des offres pour développeur Python", "fr"),
        ("ما هي الوظائف المناسبة لملفي؟", "ar"),
        ("أريد عروض عمل في Python و SQL", "ar"),
    ],
)
def test_language_is_detected(prompt: str, language: str) -> None:
    assert detect_language(prompt) == language


@pytest.mark.parametrize(
    "prompt",
    [
        "What jobs match my profile?",
        "Find jobs for me",
        "Recommend job opportunities",
        "Show matching jobs",
        "Find me a job in data with training for missing skills",
        "Quels emplois correspondent à mon profil ?",
        "Trouve-moi des offres d'emploi en Python",
        "Je cherche un poste de développeur",
        "ما هي الوظائف المناسبة لملفي؟",
        "أريد عروض عمل في Python",
        "ابحث لي عن فرص عمل",
    ],
)
def test_candidate_job_intents_in_three_languages(prompt: str) -> None:
    assert route_request("candidate", prompt) == CANDIDATE_JOB_SEARCH


@pytest.mark.parametrize(
    "prompt",
    [
        "Can you improve my CV?",
        "Help me apply for a job",
        "Recommend training for me",
        "Améliore ma lettre de motivation pour cet emploi",
        "ساعدني في كتابة السيرة الذاتية",
        "Hello",
    ],
)
def test_candidate_unsupported_requests(prompt: str) -> None:
    assert route_request("candidate", prompt) == UNSUPPORTED


def test_baseline_tool_can_be_selected_for_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    assert resolve_route("candidate", "Find jobs for me") == CANDIDATE_JOB_SEARCH
    monkeypatch.setenv("ANETAI_CANDIDATE_TOOL", "baseline")
    assert resolve_route("candidate", "Find jobs for me") == BASELINE_ROUTE
    assert resolve_route("candidate", "Hello") == UNSUPPORTED


def _evidence(**overrides: Any) -> dict[str, Any]:
    match = {
        "offer_id": "o1",
        "rank": 1,
        "title": "Data Analyst",
        "organization": "Org",
        "offer_url": "https://jobs.example.test/1",
        "matched_skills": ["SQL"],
        "missing_skills": ["Python"],
        "offer_skills": ["Python", "SQL"],
        "training": [
            {
                "program_id": "p1",
                "title": "Python 101",
                "organization": "Academy",
                "skill": "Python",
            }
        ],
    }
    return {
        "reason": "matches_found",
        "profile_has_skills": True,
        "matches": [match],
        **overrides,
    }


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (
            "en",
            "1. Data Analyst at Org. Matched skills: SQL. Missing skills: Python. "
            "Training for missing skills: Python 101 (Academy) for Python. "
            "Offer link: https://jobs.example.test/1",
        ),
        (
            "fr",
            "1. Data Analyst chez Org. Compétences correspondantes : SQL. "
            "Compétences manquantes : Python. Formations pour les compétences manquantes : "
            "Python 101 (Academy) pour Python. Lien de l'offre : https://jobs.example.test/1",
        ),
        (
            "ar",
            "1. Data Analyst لدى Org. المهارات المتوفرة: SQL. المهارات الناقصة: Python. "
            "تكوينات للمهارات الناقصة: Python 101 (Academy) لمهارة Python. "
            "رابط العرض: https://jobs.example.test/1",
        ),
    ],
)
def test_job_search_template_per_language(language: str, expected: str) -> None:
    assert job_search_reply(_evidence(), language) == expected


def test_templates_for_empty_results_and_missing_profile_skills() -> None:
    assert job_search_reply(_evidence(matches=[], reason="no_matching_offers"), "fr") == (
        "Aucune offre publiée ne correspond à votre demande."
    )
    assert "أضف مهارات" in job_search_reply(
        _evidence(matches=[], reason="candidate_has_no_skills"), "ar"
    )
    assert job_search_reply(_evidence(profile_has_skills=False), "en").endswith(
        "Add skills to your profile for personalised results."
    )
    assert "pas encore prises en charge" in unsupported_reply("fr")


@pytest.mark.parametrize(
    ("prompt", "route"),
    [
        ("Find candidates with Python and SQL", RECRUITER_CANDIDATE_SEARCH),
        (
            "Which profiles fit offer 3f1c2d9a-0000-4000-8000-000000000001?",
            RECRUITER_CANDIDATE_SEARCH,
        ),
        ("Trouve des candidats pour mon offre Data Analyst", RECRUITER_CANDIDATE_SEARCH),
        ("ابحث عن مرشحين يعرفون Python", RECRUITER_CANDIDATE_SEARCH),
        ("Show my offers about data", RECRUITER_OFFER_SEARCH),
        ("Quelles sont mes offres en brouillon ?", RECRUITER_OFFER_SEARCH),
        ("ما هي عروضي المنشورة؟", RECRUITER_OFFER_SEARCH),
        ("Show me the CVs of applicants", UNSUPPORTED),
        ("Liste les candidatures reçues", UNSUPPORTED),
        ("What jobs match my profile?", UNSUPPORTED),
    ],
)
def test_recruiter_routes_in_three_languages(prompt: str, route: str) -> None:
    assert route_request("recruiter", prompt) == route


@pytest.mark.parametrize("prompt", ["Find candidates with Python", "Show my offers"])
def test_recruiter_intents_are_refused_for_candidates(prompt: str) -> None:
    assert route_request("candidate", prompt) == UNSUPPORTED


def test_offer_reference_detection() -> None:
    assert mentions_offer("Candidates for offer Data Analyst")
    assert mentions_offer("candidats pour l'offre X")
    assert mentions_offer("مرشحين لهذا العرض")
    assert not mentions_offer("Find candidates with Python")


def test_recruiter_templates_hold_ids_and_skills_only() -> None:
    evidence = {
        "reason": "profiles_found",
        "matches": [{"profile_id": "p-1", "rank": 1, "matched_skills": ["Python"]}],
    }
    assert candidate_search_reply(evidence, "en") == (
        "1. Profile p-1. Matched skills: Python.\n"
        "Open a profile in candidate discovery to see its details."
    )
    assert candidate_search_reply({"reason": "offer_not_accessible", "matches": []}, "fr") == (
        "Cette offre n'est pas accessible depuis votre compte."
    )
    offers = {
        "reason": "offers_found",
        "matches": [{"title": "Data Analyst", "status": "DRAFT", "skills": ["SQL"]}],
    }
    assert own_offer_search_reply(offers, "fr") == "1. Data Analyst (brouillon). Compétences : SQL."
    assert own_offer_search_reply({"reason": "no_matching_offers", "matches": []}, "en") == (
        "None of your offers matched your request."
    )
    assert "عروضك" in unsupported_reply("ar", "recruiter")
