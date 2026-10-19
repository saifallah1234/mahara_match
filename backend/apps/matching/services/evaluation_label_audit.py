from __future__ import annotations

from collections.abc import Mapping, Set

from backend.apps.matching.services.evaluation_retrieval import RetrievalCase

SkillIndex = Mapping[str, Set[str]]


def expected_relevant_labels(
    case: RetrievalCase,
    offer_skills: SkillIndex,
    program_skills: SkillIndex,
) -> list[str]:
    case_id = case["id"]
    offer_ids: set[str] = set()
    program_ids: set[str] = set()

    if case_id.endswith(("keywords_01", "semantic_01")):
        offers = _offers_with_all(offer_skills, {"Python", "SQL"})
        offer_ids.update(offers)
        program_ids.update(_programs_covering(program_skills, {"Python", "SQL"}))
    elif case_id.endswith(("keywords_02", "semantic_02")):
        skills = {"Docker", "Machine Learning"}
        offer_ids.update(_offers_with_all(offer_skills, skills))
        program_ids.update(_programs_covering(program_skills, skills))
    elif case_id.endswith("keywords_03"):
        offer_ids.update(_offers_with_any(offer_skills, {"PostgreSQL", "Apache Spark"}))
    elif case_id.endswith("keywords_04"):
        skills = {"CI/CD", "Cloud Computing", "Azure", "Django"}
        offer_ids.update(_offers_with_any(offer_skills, skills))
        program_ids.update(_programs_covering(program_skills, skills))
    elif case_id.endswith("semantic_03"):
        offer_ids.update(_offers_with_all(offer_skills, {"CI/CD"}))
        program_ids.update(_programs_covering(program_skills, {"CI/CD"}))
    elif case_id.endswith("semantic_04"):
        skills = {"JavaScript", "Cloud Computing"}
        offer_ids.update(_offers_with_all(offer_skills, skills))
        program_ids.update(_programs_covering(program_skills, skills))
    elif case_id.endswith(("multi_hop_01", "multi_hop_03")):
        skill = "PostgreSQL" if case_id.endswith("multi_hop_01") else "Apache Spark"
        offer_ids.update(_offers_with_all(offer_skills, {skill}))
    elif case_id.endswith("multi_hop_02"):
        offer_ids.update(_offers_with_all(offer_skills, {"Docker"}))
        linked_skills = set().union(*(offer_skills[offer_id] for offer_id in offer_ids))
        program_ids.update(_programs_covering(program_skills, linked_skills))
    elif case_id.endswith("multi_hop_04"):
        offer_ids.update(_offers_with_all(offer_skills, {"Python", "SQL"}))
        linked_skills = set().union(*(offer_skills[offer_id] for offer_id in offer_ids))
        program_ids.update(_programs_covering(program_skills, linked_skills))
    else:
        raise ValueError(f"No relevance rule is defined for case {case_id!r}.")

    return sorted(
        [
            *(f"offer:{identifier}" for identifier in offer_ids),
            *(f"training:{identifier}" for identifier in program_ids),
        ]
    )


def _offers_with_all(index: SkillIndex, skills: set[str]) -> set[str]:
    return {entity_id for entity_id, linked in index.items() if skills <= linked}


def _offers_with_any(index: SkillIndex, skills: set[str]) -> set[str]:
    return {entity_id for entity_id, linked in index.items() if skills & linked}


def _programs_covering(index: SkillIndex, skills: set[str]) -> set[str]:
    return {entity_id for entity_id, linked in index.items() if skills & linked}
