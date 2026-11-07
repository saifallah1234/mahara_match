# Placement: backend/apps/training/services/indicators.py
"""Aggregate training counts for reporting. Numbers only: no IDs, names or rows.

Counted programs are ACTIVE programs (archiving is how a program is retired).
"""

from collections import Counter

from django.db.models import Count

from backend.apps.training.models import (
    ProgramStatus,
    TrainingProgram,
    TrainingSkill,
    TrainingSkillPurpose,
)


def program_counts_by_governorate() -> Counter[str]:
    """Provider organization governorate (stripped) -> number of counted programs."""
    rows = (
        TrainingProgram.objects.filter(status=ProgramStatus.ACTIVE)
        .values("organization__governorate")
        .annotate(n=Count("id"))
    )
    counts: Counter[str] = Counter()
    for row in rows:
        counts[row["organization__governorate"].strip()] += row["n"]
    return counts


def program_supply_by_skill() -> Counter[str]:
    """Skill name -> number of counted programs teaching it (prerequisites excluded)."""
    rows = (
        TrainingSkill.objects.filter(
            program__status=ProgramStatus.ACTIVE, purpose=TrainingSkillPurpose.TAUGHT
        )
        .values("skill__canonical_name")
        .annotate(n=Count("program", distinct=True))
    )
    return Counter({row["skill__canonical_name"]: row["n"] for row in rows})
