# Placement: backend/apps/identity/management/commands/seed_demo.py
"""Fills a local development database with the demo reference data and one account per actor.

    uv run python backend/manage.py seed_demo --password "<demo password>" \
        --settings=backend.config.settings.development

Idempotent: every record is found by its natural key first, and records that already exist
(including ones this command did not create) are never modified. One transaction.
"""

from dataclasses import asdict, dataclass
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection, transaction

from backend.apps.candidates.models import ProfileVisibility
from backend.apps.candidates.services.records import update_profile
from backend.apps.identity.models import Organization, Role, RoleCode, User, UserRole, UserStatus
from backend.apps.identity.services.onboarding import register
from backend.apps.identity.services.organization_members import create_member
from backend.apps.identity.services.organizations import create_organization, verify_organization
from backend.apps.identity.services.user_roles import assign_role
from backend.apps.identity.services.users import create_account
from backend.apps.taxonomy.services.reference_seed import seed_education_levels, seed_esco_skills
from backend.common.exceptions import DomainError

DEMO_DOMAIN = "demo.mahara.test"


@dataclass(frozen=True)
class DemoOrganization:
    registration_number: str
    type: str
    legal_name: str
    matricule_fiscal: str
    governorate: str


@dataclass(frozen=True)
class DemoStaff:
    email: str
    first_name: str
    last_name: str
    role: str
    organization: DemoOrganization
    job_title: str


ADMIN_EMAIL = f"admin@{DEMO_DOMAIN}"
STAFF = (
    DemoStaff(
        f"ministere@{DEMO_DOMAIN}",
        "Leila",
        "Mansouri",
        RoleCode.MINISTRY_MANAGER,
        DemoOrganization(
            "DEMO-MINISTRY",
            "MINISTRY",
            "Ministère de l'Emploi et de la Formation Professionnelle (démo)",
            "9990001A00000",
            "Tunis",
        ),
        "Chargée des indicateurs",
    ),
    DemoStaff(
        f"recruteur@{DEMO_DOMAIN}",
        "Karim",
        "Jaziri",
        RoleCode.RECRUITER,
        DemoOrganization(
            "DEMO-COMPANY",
            "COMPANY",
            "Carthage Data Solutions (démo)",
            "9990002B00000",
            "Tunis",
        ),
        "Responsable recrutement",
    ),
    DemoStaff(
        f"formation@{DEMO_DOMAIN}",
        "Sonia",
        "Gharbi",
        RoleCode.TRAINING_MANAGER,
        DemoOrganization(
            "DEMO-TRAINING",
            "TRAINING_PROVIDER",
            "Institut Numérique de Sfax (démo)",
            "9990003C00000",
            "Sfax",
        ),
        "Responsable formation",
    ),
)


@dataclass(frozen=True)
class DemoCandidate:
    email: str
    first_name: str
    last_name: str
    headline: str
    governorate: str


CANDIDATES = (
    DemoCandidate(
        f"candidat@{DEMO_DOMAIN}", "Amine", "Ben Salah", "Développeur Python junior", "Tunis"
    ),
    DemoCandidate(
        f"candidat2@{DEMO_DOMAIN}", "Yasmine", "Trabelsi", "Analyste de données", "Sousse"
    ),
)


class Command(BaseCommand):
    help = "Seed the demo reference data and accounts (development databases only)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--password", required=True, help="Password given to every new demo account."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DEBUG on (development settings).")
        database = connection.settings_dict
        self.stdout.write(
            f"Target database: host {database['HOST'] or 'local socket'}, name {database['NAME']}"
        )
        password: str = options["password"]
        try:
            with transaction.atomic():
                call_command("seed_rbac", stdout=self.stdout)
                call_command("seed_languages", stdout=self.stdout)
                seed_esco_skills()
                seed_education_levels()
                admin = _admin(password)
                for staff in STAFF:
                    _staff(admin, staff, password)
                for candidate in CANDIDATES:
                    _candidate(candidate, password)
        except DomainError as exc:
            raise CommandError(
                f"Demo seed failed, nothing was written: {exc} {exc.details or ''}"
            ) from exc

        self.stdout.write(self.style.SUCCESS("Demo accounts (existing ones were left unchanged):"))
        self.stdout.write(f"  {ADMIN_EMAIL}  {RoleCode.ADMIN}")
        for staff in STAFF:
            self.stdout.write(f"  {staff.email}  {staff.role}")
        for candidate in CANDIDATES:
            self.stdout.write(f"  {candidate.email}  {RoleCode.CANDIDATE}")


def _exists(email: str) -> bool:
    return User.objects.filter(email__iexact=email).exists()


def _account(email: str, first_name: str, last_name: str, password: str) -> User:
    return create_account(
        {"email": email, "password": password, "first_name": first_name, "last_name": last_name},
        status=UserStatus.ACTIVE,
    )


def _admin(password: str) -> User:
    if _exists(ADMIN_EMAIL):
        return User.objects.get_by_natural_key(ADMIN_EMAIL)
    admin = _account(ADMIN_EMAIL, "Admin", "Démo", password)
    # assign_role refuses self-assignment and needs an acting admin: the first one is direct,
    # as registration does for the candidate role.
    UserRole.objects.create(user=admin, role=Role.objects.get(code=RoleCode.ADMIN))
    return admin


def _organization(admin: User, spec: DemoOrganization) -> Organization:
    existing = Organization.objects.filter(registration_number=spec.registration_number).first()
    if existing is not None:
        return existing
    return verify_organization(admin, create_organization(admin, asdict(spec)))


def _staff(admin: User, staff: DemoStaff, password: str) -> None:
    if _exists(staff.email):
        return
    organization = _organization(admin, staff.organization)
    user = _account(staff.email, staff.first_name, staff.last_name, password)
    create_member(
        admin,
        {"organization_id": organization.id, "user": user.id, "job_title": staff.job_title},
    )
    assign_role(
        admin,
        user_id=user.id,
        role_id=Role.objects.get(code=staff.role).id,
        organization_id=organization.id,
    )


def _candidate(candidate: DemoCandidate, password: str) -> None:
    if _exists(candidate.email):
        return
    user = register(
        {
            "email": candidate.email,
            "password": password,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "account_type": RoleCode.CANDIDATE,
        }
    )
    # RECRUITERS lets verified recruiters discover the profile (Q28).
    update_profile(
        user,
        {
            "profile_visibility": ProfileVisibility.RECRUITERS,
            "headline": candidate.headline,
            "governorate": candidate.governorate,
        },
    )
