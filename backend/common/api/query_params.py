from typing import Literal, overload
from uuid import UUID

from rest_framework.request import Request

from backend.common.exceptions import DomainValidationError


@overload
def uuid_query_param(request: Request, name: str, *, required: Literal[True]) -> UUID: ...


@overload
def uuid_query_param(
    request: Request, name: str, *, required: Literal[False] = False
) -> UUID | None: ...


def uuid_query_param(request: Request, name: str, *, required: bool = False) -> UUID | None:
    raw = request.query_params.get(name)
    if not raw:
        if required:
            raise DomainValidationError(details={name: ["This query parameter is required."]})
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise DomainValidationError(details={name: ["Enter a valid UUID."]}) from exc
