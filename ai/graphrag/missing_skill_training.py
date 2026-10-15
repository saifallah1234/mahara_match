"""Graph hop: an offer's missing skills -> active training programs that teach them.

Suggestions only; nothing here enrolls a candidate or persists a recommendation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from backend.apps.training.services.retrieval_scope import programs_teaching


def training_for_missing_skills(
    missing_skill_ids: Sequence[UUID], limit: int = 2
) -> list[dict[str, Any]]:
    return [
        {
            "program_id": str(suggestion.program_id),
            "title": suggestion.title,
            "organization": suggestion.organization,
            "skill": suggestion.skill_name,
        }
        for suggestion in programs_teaching(missing_skill_ids, limit)
    ]
