from uuid import UUID

from rest_framework.request import Request

from backend.common.exceptions import DomainValidationError


def optional_uuid_param(request: Request, name: str) -> UUID | None:
    raw = request.query_params.get(name)
    if raw is None:
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise DomainValidationError(details={name: ["Invalid UUID."]}) from exc
