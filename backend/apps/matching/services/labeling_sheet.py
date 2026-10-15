from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypedDict

from backend.apps.matching.services.evaluation_dataset import _skill_mentions


class LabelingCase(TypedDict):
    id: str
    language: str
    category: str
    question: str


class Candidate(TypedDict):
    type: str
    id: str
    title: str


CandidateDetails = Mapping[tuple[str, str], tuple[str, Sequence[str]]]


def render_labeling_sheet(
    cases: Sequence[LabelingCase],
    candidates_by_case: Mapping[str, Sequence[Candidate]],
    catalog: CandidateDetails,
) -> str:
    lines = [
        "# Retrieval relevance labeling sheet",
        "",
        "Check a candidate only when it is relevant to the question. Candidates are listed alphabetically by title.",
        "",
    ]
    for case in cases:
        lines.extend(
            (
                f"## {case['id']} | {case['language']} | {case['category']}",
                "",
                f"**Question:** {case['question']}",
                "",
            )
        )
        union: dict[tuple[str, str], Candidate] = {}
        for candidate in candidates_by_case.get(case["id"], ()):
            key = (candidate["type"], candidate["id"])
            union.setdefault(key, candidate)

        ordered = sorted(
            union,
            key=lambda key: (
                catalog.get(key, (union[key]["title"], ()))[0].casefold(),
                key[0],
                key[1],
            ),
        )
        if not ordered:
            lines.extend(("_Aucun candidat retourné._", ""))
            continue

        mentioned_skills = set(_skill_mentions(case["question"]))
        for key in ordered:
            details = catalog.get(key)
            if details is None:
                raise ValueError(f"Candidate {key[0]}:{key[1]} is missing from eval_graphrag.")
            title, skills = details
            display_title = _escape_markdown(title)
            identifier = f"{key[0]}:{key[1]}"
            lines.append(f"- [ ] **{display_title}** — `{identifier}`")
            lines.append("  - Compétences liées : " + (", ".join(skills) if skills else "aucune"))
            if case["category"] == "keywords" and key[0] == "offer":
                overlap = sorted(mentioned_skills & set(skills), key=str.casefold)
                suggestion = (
                    "l’offre est liée aux compétences citées : " + ", ".join(overlap)
                    if overlap
                    else "aucune compétence citée ne figure dans les liaisons de l’offre"
                )
                lines.append(f"  - Suggestion à valider : {suggestion}.")
        lines.append("")
    return "\n".join(lines)


def _escape_markdown(value: str) -> str:
    for character in ("\\", "`", "*", "_", "[", "]"):
        value = value.replace(character, f"\\{character}")
    return value
