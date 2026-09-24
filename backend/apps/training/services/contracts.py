from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ProgramDTO:
    organization_id: UUID
    title: str
    description: str
    level: str
    delivery_mode: str
    status: str
    is_paid: bool
    price: float | None = None


@dataclass(frozen=True)
class EnrollmentDTO:
    session_id: UUID
    candidate_id: UUID
    status: str = "REGISTERED"


@dataclass(frozen=True)
class RecommendationDTO:
    candidate_id: UUID
    program_id: UUID
    reason_json: dict[str, Any]
    score: float
    model_version: str
