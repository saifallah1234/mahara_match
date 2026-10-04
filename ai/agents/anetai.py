from __future__ import annotations

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from ai.llm.providers.ollama import get_chat_model
from ai.tools.job_matches import get_candidate_job_matches
from ai.workflows.job_matching import build_job_matching_graph

if TYPE_CHECKING:
    from backend.apps.identity.models import User

AGENT_VERSION = "anetai-v1"
ROUTE = "job_match_search"
UNSUPPORTED_ROUTE = "unsupported"
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


def is_job_match_request(prompt: str) -> bool:
    """Recognize the V1 English job-search intent; default to no tool call."""
    text = re.sub(r"[^a-z0-9]+", " ", prompt.casefold()).strip()
    unsupported = ("cv", "resume", "training", "course", "apply", "application")
    if any(re.search(rf"\b{term}\b", text) for term in unsupported):
        return False
    patterns = (
        r"\b(?:what|which) jobs? (?:match|fit)\b",
        r"\bmatch(?:ing)? jobs?\b",
        r"\bfind jobs?\b",
        r"\brecommend jobs?\b",
        r"\brecommend job opportunities\b",
        r"\bjob recommendations?\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


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


def _stays_within_evidence(reply: str, evidence: dict[str, Any]) -> bool:
    lowered = reply.casefold()
    if any(claim in lowered for claim in _UNSUPPORTED_CLAIMS):
        return False

    fallback = _evidence_summary(evidence)
    known_words = set(re.findall(r"[a-z0-9]+", fallback.casefold())) | _SAFE_REWORDING
    if set(re.findall(r"[a-z0-9]+", lowered)) - known_words:
        return False

    urls = {
        url.rstrip(".,;:!?)]")
        for url in re.findall(r"https?://[^\s)\]]+", reply, flags=re.IGNORECASE)
    }
    known_urls = {match["offer_url"] for match in evidence["matches"] if match["offer_url"]}
    if not urls.issubset(known_urls):
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


def explain_matches(prompt: str, evidence: dict[str, Any]) -> str:
    if not evidence["matches"]:
        return _evidence_summary(evidence)
    fallback = _evidence_summary(evidence)
    response = get_chat_model().invoke(
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
    reply = str(response.content)
    return reply if _stays_within_evidence(reply, evidence) else fallback


def run_job_matching_agent(actor: User, prompt: str) -> dict[str, Any]:
    graph = build_job_matching_graph(get_candidate_job_matches, explain_matches)
    return graph.invoke(
        {"actor": actor, "prompt": prompt, "supported": is_job_match_request(prompt)}
    )
