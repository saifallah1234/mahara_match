from datetime import timedelta
from typing import Any

import pytest
from django.core.management import call_command
from django.utils import timezone

from backend.apps.candidates.models import CandidateProfile
from backend.apps.identity.models import Organization, OrganizationMember, Role, User, UserRole
from backend.apps.training.models import TrainingProgram, TrainingSession


@pytest.fixture
def phase3(db: None) -> dict[str, Any]:
    call_command("seed_rbac", verbosity=0)
    records: dict[str, Any] = {}
    for index, (name, role_code, org_type) in enumerate(
        (
            ("candidate", "CANDIDATE", None),
            ("other_candidate", "CANDIDATE", None),
            ("recruiter", "RECRUITER", "COMPANY"),
            ("other_recruiter", "RECRUITER", "COMPANY"),
            ("provider", "TRAINING_MANAGER", "TRAINING_PROVIDER"),
            ("other_provider", "TRAINING_MANAGER", "TRAINING_PROVIDER"),
            ("admin", "ADMIN", None),
        ),
        start=1,
    ):
        user = User.objects.create_user(
            f"{name}@example.test", first_name="Private", last_name="Identity", status="ACTIVE"
        )
        org = None
        if org_type:
            org = Organization.objects.create(
                type=org_type,
                legal_name=name,
                matricule_fiscal=f"{index:07d}A00000",
                verification_status="VERIFIED",
                governorate="Tunis" if index % 2 else "Sfax",
            )
            OrganizationMember.objects.create(user=user, organization=org)
            records[f"{name}_org"] = org
        UserRole.objects.create(user=user, role=Role.objects.get(code=role_code), organization=org)
        records[name] = user
        if role_code == "CANDIDATE":
            records[f"{name}_profile"] = CandidateProfile.objects.create(user=user)
    program = TrainingProgram.objects.create(
        organization=records["provider_org"],
        title="Python",
        status="ACTIVE",
        delivery_mode="ONLINE",
    )
    now = timezone.now()
    session = TrainingSession.objects.create(
        program=program,
        start_date=now + timedelta(days=2),
        end_date=now + timedelta(days=3),
        registration_deadline=now + timedelta(days=1),
        capacity=1,
        location_or_url="Tunis classroom",
    )
    records.update(program=program, session=session)
    return records
