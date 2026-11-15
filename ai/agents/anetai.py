from __future__ import annotations

import logging
import os
import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from ai.agents.intents import (
    CANDIDATE_CV_ADVICE,
    CANDIDATE_JOB_SEARCH,
    RECRUITER_CANDIDATE_SEARCH,
    RECRUITER_OFFER_SEARCH,
    UNSUPPORTED,
    Role,
    detect_language,
    mentions_offer,
    route_request,
)
from ai.agents.templates import (
    candidate_search_reply,
    cv_advice_reply,
    job_search_reply,
    own_offer_search_reply,
    unsupported_reply,
)
from ai.llm.providers.ollama import get_chat_model
from ai.tools.candidate_search import (
    CANDIDATE_TOOL_NAME,
    OFFER_TOOL_NAME,
    search_candidates,
    search_own_offers,
)
from ai.tools.cv_advice import TOOL_NAME as CV_ADVICE_TOOL
from ai.tools.cv_advice import get_cv_advice
from ai.tools.job_matches import get_candidate_job_matches
from ai.tools.job_search import TOOL_NAME as JOB_SEARCH_TOOL
from ai.tools.job_search import search_jobs_for_candidate
from ai.workflows.job_matching import RouteSpec, build_agent_graph
from backend.apps.recruitment.services.retrieval_scope import offer_reference

if TYPE_CHECKING:
    from backend.apps.identity.models import User

logger = logging.getLogger(__name__)

AGENT_VERSION = "anetai-v2"
# Wording is optional polish: a slow or unreachable model must not delay the grounded reply.
WORDING_TIMEOUT_SECONDS = 8
# Phase 7 skill-coverage route, kept selectable (ANETAI_CANDIDATE_TOOL=baseline) until the
# retrieval route is verified live; remove it in a follow-up.
BASELINE_ROUTE = "job_match_search"
UNSUPPORTED_ROUTE = UNSUPPORTED
_UNSUPPORTED_CLAIMS = (
    "require",
    "qualif",
    "eligible",
    "eligibility",
    "perfect",
    "strong match",
    "great fit",
    "ideal fit",
    "suitable",
    "you should apply",
    "year of experience",
    "years of experience",
    "must have",
    "need to have",
    "apply",
    "learn more",
)
_SAFE_REWORDING = {
    "a",
    "an",
    "and",
    "at",
    "based",
    "coverage",
    "has",
    "in",
    "is",
    "job",
    "jobs",
    "match",
    "matches",
    "missing",
    "offer",
    "offers",
    "on",
    "profile",
    "score",
    "shows",
    "skill",
    "skills",
    "the",
    "with",
}


def resolve_route(role: Role, prompt: str) -> str:
    route = route_request(role, prompt)
    if route == CANDIDATE_JOB_SEARCH and os.getenv("ANETAI_CANDIDATE_TOOL") == "baseline":
        return BASELINE_ROUTE
    return route


def _evidence_summary(evidence: dict[str, Any]) -> str:
    if evidence["reason"] == "candidate_has_no_skills":
        return "Add skills to your profile to calculate skill coverage for available jobs."
    matches = evidence["matches"]
    if not matches:
        return "No scored matches were found among published offers with comparable skills."

    lines = []
    for match in matches:
        matched = ", ".join(match["matched_skills"]) or "none"
        missing = ", ".join(match["missing_skills"]) or "none"
        line = (
            f"{match['title']} at {match['organization']}: {match['score']}% skill coverage. "
            f"Matched skills: {matched}. Missing skills: {missing}."
        )
        if match["offer_url"]:
            line += f" Offer link: {match['offer_url']}"
        lines.append(line)
    return "\n".join(lines)


def _within_fallback_bounds(reply: str, fallback: str, known_urls: set[str]) -> bool:
    """No unsupported claim, no word outside the fallback text, no unknown link."""
    lowered = reply.casefold()
    if any(claim in lowered for claim in _UNSUPPORTED_CLAIMS):
        return False
    known_words = set(re.findall(r"[a-z0-9]+", fallback.casefold())) | _SAFE_REWORDING
    if set(re.findall(r"[a-z0-9]+", lowered)) - known_words:
        return False
    urls = {
        url.rstrip(".,;:!?)]")
        for url in re.findall(r"https?://[^\s)\]]+", reply, flags=re.IGNORECASE)
    }
    return urls.issubset(known_urls)


def _stays_within_evidence(reply: str, evidence: dict[str, Any]) -> bool:
    lowered = reply.casefold()
    known_urls = {match["offer_url"] for match in evidence["matches"] if match["offer_url"]}
    if not _within_fallback_bounds(reply, _evidence_summary(evidence), known_urls):
        return False

    reported_scores = {
        format(Decimal(score.rstrip("% ")).normalize(), "f")
        for score in re.findall(r"(?<![\d.])\d+(?:\.\d+)?\s*%", reply)
    }
    expected_scores = {
        format(Decimal(match["score"]).normalize(), "f") for match in evidence["matches"]
    }
    if not reported_scores.issubset(expected_scores):
        return False
    for match in evidence["matches"]:
        skills = match["offer_skills"]
        if set(match["matched_skills"]) | set(match["missing_skills"]) != set(skills):
            return False
        if set(match["matched_skills"]) & set(match["missing_skills"]):
            return False
        if (
            match["title"].casefold() not in lowered
            or match["organization"].casefold() not in lowered
            or format(Decimal(match["score"]).normalize(), "f") not in reported_scores
            or any(skill.casefold() not in lowered for skill in match["matched_skills"])
            or any(skill.casefold() not in lowered for skill in match["missing_skills"])
        ):
            return False
    return True


def _reword(messages: list[SystemMessage | HumanMessage]) -> str | None:
    """Model wording, or None when the model fails or times out."""
    try:
        # Unstreamed, so the read timeout bounds the whole generation, not each token.
        model = get_chat_model(timeout=WORDING_TIMEOUT_SECONDS)
        return str(model.invoke(messages, stream=False).content)
    except Exception as exc:
        logger.warning("Agent wording fell back to the template: %s", type(exc).__name__)
        return None


def explain_matches(prompt: str, evidence: dict[str, Any]) -> str:
    if not evidence["matches"]:
        return _evidence_summary(evidence)
    fallback = _evidence_summary(evidence)
    reply = _reword(
        [
            SystemMessage(
                content=(
                    "You are a wording editor for the Mahara Match candidate assistant. Rewrite "
                    "the deterministic explanation using only its supplied facts. Explain job "
                    "matches using only "
                    "the supplied persisted scores and skill evidence. The score is skill coverage, "
                    "not overall job suitability, eligibility, or qualification. Never call a score "
                    "a perfect/strong match and never infer qualifications, requirements, or facts. "
                    "State the score as skill coverage and list only the supplied title, organization, "
                    "matched skills, missing skills, and link. Say clearly when there are no scored "
                    "matches. If reason is candidate_has_no_skills, explain that the candidate can "
                    "add skills to their profile before matching."
                )
            ),
            HumanMessage(
                content=(
                    f"Request: {prompt}\nDeterministic explanation: {fallback}"
                    f"\nMatch evidence: {evidence}"
                )
            ),
        ]
    )
    if reply is None or not _stays_within_evidence(reply, evidence):
        return fallback
    return reply


def _stays_within_search_evidence(reply: str, evidence: dict[str, Any]) -> bool:
    """Grounding check for retrieval results: every fact must come from the evidence."""
    lowered = reply.casefold()
    known_urls = {match["offer_url"] for match in evidence["matches"] if match["offer_url"]}
    if not _within_fallback_bounds(reply, job_search_reply(evidence, "en"), known_urls):
        return False
    if re.search(r"\d\s*%", reply):
        return False
    for match in evidence["matches"]:
        if set(match["matched_skills"]) | set(match["missing_skills"]) != set(
            match["offer_skills"]
        ):
            return False
        required = [
            match["title"],
            match["organization"],
            *match["matched_skills"],
            *match["missing_skills"],
            *(program["title"] for program in match["training"]),
        ]
        if any(fact.casefold() not in lowered for fact in required):
            return False
    return True


def explain_job_search(prompt: str, evidence: dict[str, Any], language: str) -> str:
    """Deterministic reply in the request language; English may be reworded by the LLM."""
    fallback = job_search_reply(evidence, language)
    if language != "en" or not evidence["matches"]:
        return fallback
    reply = _reword(
        [
            SystemMessage(
                content=(
                    "You are a wording editor for the Mahara Match candidate assistant. Rewrite "
                    "the deterministic explanation using only its supplied facts. The offers are "
                    "ordered by search relevance to the request, not by suitability, eligibility "
                    "or qualification. Matched and missing skills compare the offer's listed "
                    "skills with the candidate profile. Training programs are suggestions for "
                    "missing skills, not enrollments. Keep every title, organization, skill, "
                    "training program and link; add no scores, percentages or other facts."
                )
            ),
            HumanMessage(content=f"Request: {prompt}\nDeterministic explanation: {fallback}"),
        ]
    )
    if reply is None or not _stays_within_search_evidence(reply, evidence):
        return fallback
    return reply


_CANDIDATE_SEARCH_TRACE_KEYS = ("reason", "offer_id", "vector_unavailable", "legs", "latency_ms")
_PROFILE_TRACE_KEYS = ("profile_id", "rank", "leg_ranks", "matched_skills")


def candidate_search_trace(evidence: dict[str, Any]) -> dict[str, Any]:
    """Allow-list for recruiter runs: IDs, ranks, scores and matched skill names only."""
    trace = {key: evidence[key] for key in _CANDIDATE_SEARCH_TRACE_KEYS if key in evidence}
    trace["matches"] = [
        {key: match[key] for key in _PROFILE_TRACE_KEYS if key in match}
        for match in evidence["matches"]
    ]
    return trace


def _candidate_search(actor: User, prompt: str) -> dict[str, Any]:
    offer_id = offer_reference(actor, prompt) if mentions_offer(prompt) else None
    return search_candidates(actor, prompt, offer_id)


def _routes() -> dict[str, RouteSpec]:
    # Lambdas resolve module attributes at call time so tests can patch them.
    return {
        CANDIDATE_JOB_SEARCH: RouteSpec(
            tool_name=JOB_SEARCH_TOOL,
            tool=lambda actor, prompt: search_jobs_for_candidate(actor, prompt),
            explain=lambda prompt, evidence, language: explain_job_search(
                prompt, evidence, language
            ),
            tool_input=lambda prompt: {"question": prompt},
        ),
        CANDIDATE_CV_ADVICE: RouteSpec(
            tool_name=CV_ADVICE_TOOL,
            tool=lambda actor, prompt: get_cv_advice(actor),
            explain=lambda prompt, evidence, language: cv_advice_reply(evidence, language),
        ),
        RECRUITER_CANDIDATE_SEARCH: RouteSpec(
            tool_name=CANDIDATE_TOOL_NAME,
            tool=lambda actor, prompt: _candidate_search(actor, prompt),
            explain=lambda prompt, evidence, language: candidate_search_reply(evidence, language),
            tool_input=lambda prompt: {"question": prompt},
            trace=candidate_search_trace,
        ),
        RECRUITER_OFFER_SEARCH: RouteSpec(
            tool_name=OFFER_TOOL_NAME,
            tool=lambda actor, prompt: search_own_offers(actor, prompt),
            explain=lambda prompt, evidence, language: own_offer_search_reply(evidence, language),
            tool_input=lambda prompt: {"question": prompt},
        ),
        BASELINE_ROUTE: RouteSpec(
            tool_name="get_candidate_job_matches",
            tool=lambda actor, prompt: get_candidate_job_matches(actor),
            explain=lambda prompt, evidence, language: explain_matches(prompt, evidence),
        ),
    }


def run_agent(actor: User, prompt: str, role: Role = "candidate") -> dict[str, Any]:
    route = resolve_route(role, prompt)
    graph = build_agent_graph(_routes(), lambda language: unsupported_reply(language, role))
    return graph.invoke(
        {"actor": actor, "prompt": prompt, "route": route, "language": detect_language(prompt)}
    )
