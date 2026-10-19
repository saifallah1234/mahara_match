"""Training programs open to retrieval: the public catalogue of active programs.

Programs are suggestions only; retrieval never enrolls anyone.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from django.db.models import QuerySet

from backend.apps.training.models import TrainingProgram, TrainingSkill
from backend.apps.training.services.programs import list_indexable_programs
from backend.common.retrieval import RetrievalDocument


@dataclass(frozen=True)
class ProgramSuggestion:
    program_id: UUID
    title: str
    organization: str
    skill_id: UUID
    skill_name: str


def visible_programs() -> QuerySet[TrainingProgram]:
    return list_indexable_programs()


def program_documents(programs: QuerySet[TrainingProgram]) -> list[RetrievalDocument]:
    documents = []
    for program in programs.select_related("organization").prefetch_related(
        "program_skills__skill"
    ):
        taught_skills = ", ".join(
            link.skill.canonical_name for link in program.program_skills.all()
        )
        text = "\n".join(
            part
            for part in (
                program.title,
                program.description,
                program.level,
                program.delivery_mode,
                program.organization.legal_name,
                taught_skills,
            )
            if part
        )
        documents.append(RetrievalDocument("training", program.id, text, program.title))
    return documents


def program_ids_for_skills(
    programs: QuerySet[TrainingProgram], skill_ids: Iterable[UUID]
) -> Counter[UUID]:
    """How many of ``skill_ids`` each in-scope program teaches."""
    links = TrainingSkill.objects.filter(program__in=programs, skill_id__in=list(skill_ids))
    return Counter(program_id for (program_id,) in links.values_list("program_id"))


def programs_teaching(skill_ids: Iterable[UUID], limit: int) -> list[ProgramSuggestion]:
    """Up to ``limit`` active programs covering ``skill_ids``, most skills covered first.

    Each program is reported once, against the first of ``skill_ids`` it teaches.
    """
    wanted = list(dict.fromkeys(skill_ids))
    if not wanted or limit < 1:
        return []
    links = (
        TrainingSkill.objects.filter(program__in=visible_programs(), skill_id__in=wanted)
        .select_related("program__organization", "skill")
        .order_by("program_id", "skill_id")
    )
    by_program: dict[UUID, list[TrainingSkill]] = {}
    for link in links:
        by_program.setdefault(link.program_id, []).append(link)
    order = {skill_id: index for index, skill_id in enumerate(wanted)}
    ranked = sorted(by_program.items(), key=lambda item: (-len(item[1]), str(item[0])))
    suggestions = []
    for program_id, program_links in ranked[:limit]:
        first = min(program_links, key=lambda link: order[link.skill_id])
        suggestions.append(
            ProgramSuggestion(
                program_id=program_id,
                title=first.program.title,
                organization=first.program.organization.legal_name,
                skill_id=first.skill_id,
                skill_name=first.skill.canonical_name,
            )
        )
    return suggestions
