import os
from collections.abc import Generator
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test.utils import setup_databases, teardown_databases
from django.utils import timezone
from psycopg import sql

from backend.apps.candidates.models import CandidateProfile
from backend.apps.identity.models import Organization, OrganizationMember, Role, User, UserRole
from backend.apps.training.models import TrainingProgram, TrainingSession


@pytest.fixture(scope="session")
def django_db_setup(
    request: pytest.FixtureRequest,
    django_db_blocker: Any,
    django_db_keepdb: bool,
    django_db_createdb: bool,
    django_db_modify_db_settings: None,
) -> Generator[None]:
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        with django_db_blocker.unblock():
            database_config = setup_databases(
                verbosity=request.config.option.verbose,
                interactive=False,
                keepdb=django_db_keepdb and not django_db_createdb,
            )
        yield
        if not django_db_keepdb:
            with django_db_blocker.unblock():
                teardown_databases(database_config, verbosity=request.config.option.verbose)
        return

    original_options = connection.settings_dict["OPTIONS"].copy()
    schema_name = f"mahara_test_{uuid4().hex}"
    schema_created = False
    try:
        with django_db_blocker.unblock():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT namespace.nspname "
                    "FROM pg_extension AS extension "
                    "JOIN pg_namespace AS namespace ON namespace.oid = extension.extnamespace "
                    "WHERE extension.extname = %s",
                    ["vector"],
                )
                extension_row = cursor.fetchone()
                if extension_row is None:
                    raise pytest.UsageError(
                        "The PostgreSQL database configured by TEST_DATABASE_URL or "
                        "DATABASE_URL must have the vector extension installed."
                    )
                vector_schema = extension_row[0]
                cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
                schema_created = True

            connection.close()
            connection.settings_dict["OPTIONS"] = {
                **original_options,
                "options": f"-c search_path={schema_name}",
            }
            MigrationRecorder(connection).ensure_schema()
            connection.close()
            connection.settings_dict["OPTIONS"] = {
                **original_options,
                "options": f"-c search_path={schema_name},{vector_schema}",
            }
            call_command("migrate", interactive=False, verbosity=0)

        yield
    finally:
        connection.close()
        connection.settings_dict["OPTIONS"] = original_options
        if schema_created:
            with django_db_blocker.unblock():
                with connection.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                            sql.Identifier(schema_name)
                        )
                    )
            connection.close()


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


@pytest.fixture
def interview(phase3, settings):
    settings.MOCK_INTERVIEW_ENABLED = True
    from backend.apps.recruitment.models import JobOffer

    offer = JobOffer.objects.create(
        organization=phase3["recruiter_org"],
        created_by=phase3["recruiter"],
        title="Python developer",
        description="Build tested services",
        easy_apply=True,
        status="PUBLISHED",
    )
    phase3["offer"] = offer
    return phase3
