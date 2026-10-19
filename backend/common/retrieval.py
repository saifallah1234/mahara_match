from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RetrievalDocument:
    """Searchable text for one entity, as returned by its owning domain's scope service."""

    entity_type: str
    entity_id: UUID
    text: str
    title: str = ""
