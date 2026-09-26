from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler

from backend.common.exceptions import DomainError

STATUS_CODES = {
    400: "validation_error",
    401: "authentication_failed",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
}


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        return Response(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
            status=exc.status_code,
        )

    response = exception_handler(exc, context)
    if response is None:
        return None

    original = response.data
    message = "The request could not be completed."
    if isinstance(original, dict) and isinstance(original.get("detail"), str):
        message = original["detail"]

    response.data = {
        "error": {
            "code": STATUS_CODES.get(response.status_code, "request_error"),
            "message": message,
            "details": original,
        }
    }
    return response
