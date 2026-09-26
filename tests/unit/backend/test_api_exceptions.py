import pytest

from backend.common.api.exceptions import api_exception_handler
from backend.common.exceptions import DomainValidationError

pytestmark = pytest.mark.unit


def test_domain_error_uses_shared_error_envelope() -> None:
    response = api_exception_handler(
        DomainValidationError(details={"email": ["Invalid email."]}),
        {},
    )

    assert response is not None
    assert response.status_code == 400
    assert response.data == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed.",
            "details": {"email": ["Invalid email."]},
        }
    }
