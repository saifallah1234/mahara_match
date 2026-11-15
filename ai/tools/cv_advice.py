# Placement: ai/tools/cv_advice.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.apps.candidates.services.cv_review import latest_cv_advice

if TYPE_CHECKING:
    from backend.apps.identity.models import User

TOOL_NAME = "get_cv_advice"


def get_cv_advice(actor: User) -> dict[str, Any]:
    """The candidate's latest ATS analysis: score and its highest-severity issues."""
    return latest_cv_advice(actor)
