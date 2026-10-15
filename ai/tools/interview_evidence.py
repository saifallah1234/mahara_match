from collections.abc import Callable
from typing import Any


def retrieve_evidence(retrieve: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """The caller supplies an already authorized, bounded application projection."""
    return retrieve()
