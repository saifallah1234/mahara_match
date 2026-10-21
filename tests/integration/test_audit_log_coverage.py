# Placement: tests/integration/test_audit_log_coverage.py
import ast
from pathlib import Path
from typing import Any

import pytest

from backend.apps.identity.models import Organization
from backend.apps.identity.services.organizations import verify_organization
from backend.apps.platform.models import AuditLog
from backend.apps.training.models import TrainingEnrollment
from backend.apps.training.services.enrollments import cancel_enrollment
from backend.apps.training.services.sessions import update_session
from backend.common.exceptions import DomainPermissionError

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

ROOT = Path(__file__).resolve().parents[2]

# Owning service modules whose state changes must be audited.
AUDITED_MODULES = (
    "backend/apps/identity/services/users.py",
    "backend/apps/identity/services/user_roles.py",
    "backend/apps/identity/services/organizations.py",
    "backend/apps/identity/services/onboarding.py",
    "backend/apps/recruitment/services/application_lifecycle.py",
    "backend/apps/recruitment/services/interview_lifecycle.py",
    "backend/apps/training/services/enrollments.py",
    "backend/apps/training/services/programs.py",
    "backend/apps/training/services/sessions.py",
)

# Functions in those modules that change state but are outside the audited set (ticket 28).
NOT_AUDITED = {
    "create_account",  # self-registration path, no admin actor
    "update_profile",  # a user's own profile edits
    "register",  # candidate or organization self-registration
    "create_organization",  # organization creation, not verification
    "update_organization",
    "schedule_interview",  # scheduling, not completion or cancellation
    "create_program",
    "create_session",
}

STATE_CALLS = {"save", "delete", "create", "update"}


def _audit_gaps(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    gaps = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name in NOT_AUDITED:
            continue
        changes_state = any(
            isinstance(call.func, ast.Attribute) and call.func.attr in STATE_CALLS
            for call in ast.walk(node)
            if isinstance(call, ast.Call)
        )
        audited = any(
            isinstance(call.func, ast.Name) and call.func.id == "append_audit"
            for call in ast.walk(node)
            if isinstance(call, ast.Call)
        )
        if changes_state and not audited:
            gaps.append(node.name)
    return gaps


def test_every_state_change_in_audited_services_writes_an_audit_row() -> None:
    gaps = {module: _audit_gaps(ROOT / module) for module in AUDITED_MODULES}

    assert {module: names for module, names in gaps.items() if names} == {}


def test_admin_verification_writes_one_attributable_row(phase3: dict[str, Any]) -> None:
    organization = Organization.objects.create(
        type="COMPANY",
        legal_name="Pending Ltd",
        matricule_fiscal="9999999Z99999",
        verification_status="PENDING",
    )

    verify_organization(phase3["admin"], organization)

    row = AuditLog.objects.get()
    assert (row.action, row.entity_type, row.entity_id) == (
        "identity.organization.verify",
        "organization",
        organization.id,
    )
    assert row.actor_user == phase3["admin"]
    assert row.actor_type == "USER"


def test_rejected_verification_writes_no_row(phase3: dict[str, Any]) -> None:
    organization = Organization.objects.create(
        type="COMPANY",
        legal_name="Pending Ltd",
        matricule_fiscal="9999999Z99999",
        verification_status="PENDING",
    )

    with pytest.raises(DomainPermissionError):
        verify_organization(phase3["recruiter"], organization)

    assert not AuditLog.objects.exists()


def test_enrollment_cancel_and_session_update_write_one_row_each(phase3: dict[str, Any]) -> None:
    enrollment = TrainingEnrollment.objects.create(
        session=phase3["session"], candidate=phase3["candidate_profile"], status="REGISTERED"
    )
    cancel_enrollment(phase3["provider"], enrollment)
    update_session(phase3["provider"], phase3["session"], {"capacity": 5})

    actions = sorted(AuditLog.objects.values_list("action", flat=True))
    assert actions == ["training.enrollment.cancel", "training.session.update"]
