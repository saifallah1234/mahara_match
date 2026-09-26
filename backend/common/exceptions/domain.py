from collections.abc import Mapping
from typing import Any


class DomainError(Exception):
    code = "domain_error"
    status_code = 400
    default_message = "The operation could not be completed."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = dict(details or {})
        super().__init__(self.message)


class DomainValidationError(DomainError):
    code = "validation_error"
    status_code = 400
    default_message = "Request validation failed."


class DomainPermissionError(DomainError):
    code = "permission_denied"
    status_code = 403
    default_message = "You do not have permission to perform this action."


class DomainNotFoundError(DomainError):
    code = "not_found"
    status_code = 404
    default_message = "The requested resource was not found."
