from decimal import Decimal

import pytest

from backend.apps.recruitment.models import ApplicationStatus, JobOfferStatus
from backend.apps.recruitment.services.application_lifecycle import (
    _PROGRESSION,
    _TERMINAL,
    _valid_recruiter_transition,
)
from backend.apps.recruitment.services.job_offers import _validate_offer_fields
from backend.apps.recruitment.services.offer_lifecycle import _NEXT
from backend.common.exceptions import DomainValidationError

pytestmark = pytest.mark.unit


def test_offer_transitions_do_not_reopen_closed_offers() -> None:
    assert JobOfferStatus.PUBLISHED in _NEXT[JobOfferStatus.DRAFT]
    assert JobOfferStatus.PUBLISHED not in _NEXT[JobOfferStatus.CLOSED]


def test_application_final_states_cannot_progress() -> None:
    assert _PROGRESSION[0] == ApplicationStatus.SUBMITTED
    assert _PROGRESSION[-1] == ApplicationStatus.HIRED
    assert _TERMINAL == {
        ApplicationStatus.HIRED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }
    assert _valid_recruiter_transition(ApplicationStatus.SUBMITTED, ApplicationStatus.INTERVIEW)
    assert not _valid_recruiter_transition(ApplicationStatus.INTERVIEW, ApplicationStatus.SUBMITTED)
    assert not _valid_recruiter_transition("UNKNOWN", ApplicationStatus.HIRED)


def test_offer_rejects_invalid_salary_and_non_https_link() -> None:
    with pytest.raises(DomainValidationError):
        _validate_offer_fields({"min_salary": Decimal("20"), "max_salary": Decimal("10")})
    with pytest.raises(DomainValidationError):
        _validate_offer_fields({"min_salary": Decimal("-1")})
    with pytest.raises(DomainValidationError):
        _validate_offer_fields({"offer_url": "http://example.com/apply"})
