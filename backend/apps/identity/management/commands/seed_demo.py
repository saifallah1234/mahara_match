# Placement: backend/apps/identity/management/commands/seed_demo.py
"""Fills a local development database with the demo reference data and one account per actor.

    uv run python backend/manage.py seed_demo --password "<demo password>" \
        --settings=backend.config.settings.development

Idempotent: every record is found by its natural key first, and records that already exist
(including ones this command did not create) are never modified. One exception: a demo
candidate profile with no skills at all gets the demo skills, so databases seeded before the
scenario existed catch up. One transaction.
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection, transaction
from django.utils import timezone

from backend.apps.candidates.models import (
    CandidateProfile,
    CandidateSkill,
    ProfileVisibility,
    SkillLevel,
    WorkMode,
)
from backend.apps.candidates.services.records import create_record, update_profile
from backend.apps.identity.models import Organization, Role, RoleCode, User, UserRole, UserStatus
from backend.apps.identity.services.onboarding import register
from backend.apps.identity.services.organization_members import create_member
from backend.apps.identity.services.organizations import create_organization, verify_organization
from backend.apps.identity.services.user_roles import assign_role
from backend.apps.identity.services.users import create_account
from backend.apps.recruitment.models import JobOffer, JobOfferStatus
from backend.apps.recruitment.services.job_offers import create_job_offer
from backend.apps.recruitment.services.offer_lifecycle import transition_offer
from backend.apps.recruitment.services.offer_skills import create_offer_skill
from backend.apps.taxonomy.models import Skill
from backend.apps.taxonomy.services.reference_seed import seed_education_levels, seed_esco_skills
from backend.apps.training.models import (
    DeliveryMode,
    ProgramLevel,
    ProgramStatus,
    TrainingProgram,
)
from backend.apps.training.services.programs import create_program, update_program
from backend.apps.training.services.sessions import create_session
from backend.apps.training.services.skills import add_skill
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
_, RECRUITER, TRAINING_MANAGER = STAFF


@dataclass(frozen=True)
class DemoCandidate:
    email: str
    first_name: str
    last_name: str
    headline: str
    governorate: str
    skills: tuple[tuple[str, str], ...]


# Skill labels are ESCO preferred labels from taxonomy/data/esco_skills.json.
# The main candidate covers only part of each offer, so scores show matched and missing skills.
CANDIDATES = (
    DemoCandidate(
        f"candidat@{DEMO_DOMAIN}",
        "Amine",
        "Ben Salah",
        "Développeur Python junior",
        "Tunis",
        (
            ("Python (computer programming)", SkillLevel.ADVANCED),
            ("SQL", SkillLevel.INTERMEDIATE),
            ("tools for software configuration management", SkillLevel.INTERMEDIATE),
            ("work in teams", SkillLevel.ADVANCED),
            ("communication", SkillLevel.INTERMEDIATE),
        ),
    ),
    DemoCandidate(
        f"candidat2@{DEMO_DOMAIN}",
        "Yasmine",
        "Trabelsi",
        "Analyste de données",
        "Sousse",
        (
            ("SQL", SkillLevel.ADVANCED),
            ("statistics", SkillLevel.ADVANCED),
            ("apply statistical analysis techniques", SkillLevel.INTERMEDIATE),
            ("deliver visual presentation of data", SkillLevel.ADVANCED),
            ("Python (computer programming)", SkillLevel.BEGINNER),
            ("think analytically", SkillLevel.ADVANCED),
        ),
    ),
)

# Publishing refuses a past deadline; the deadline is not part of the offer's natural key.
OFFER_OPEN_DAYS = 60


@dataclass(frozen=True)
class DemoOffer:
    title: str
    description: str
    governorate: str
    city: str
    contract_type: str
    work_mode: str
    experience_level: str
    min_salary: int
    max_salary: int
    mandatory: tuple[str, ...]
    optional: tuple[str, ...]
    publish: bool = True


OFFERS = (
    DemoOffer(
        "Développeur Python / Django",
        "Développement et maintenance d'API web en Python pour nos clients du secteur "
        "bancaire. Revue de code, tests unitaires et déploiement continu.",
        "Tunis",
        "Les Berges du Lac",
        "CDI",
        WorkMode.HYBRID,
        "1 à 3 ans",
        1800,
        2600,
        ("Python (computer programming)", "PostgreSQL", "perform software unit testing"),
        ("SQL", "tools for software configuration management"),
    ),
    DemoOffer(
        "Data Analyst",
        "Analyse des données commerciales, construction de tableaux de bord et présentation "
        "des résultats aux équipes métier.",
        "Sfax",
        "Sfax Ville",
        "CDI",
        WorkMode.ONSITE,
        "1 à 3 ans",
        1600,
        2400,
        ("SQL", "apply statistical analysis techniques"),
        ("deliver visual presentation of data", "Python (computer programming)"),
    ),
    DemoOffer(
        "Ingénieur Machine Learning",
        "Conception et mise en production de modèles de prévision de la demande, "
        "en lien avec l'équipe données.",
        "Sousse",
        "Technopole de Sousse",
        "CDI",
        WorkMode.HYBRID,
        "3 à 5 ans",
        2800,
        3800,
        ("Python (computer programming)", "utilise machine learning"),
        ("data mining", "cloud technologies"),
    ),
    DemoOffer(
        "Développeur Full Stack JavaScript",
        "Développement d'applications web TypeScript, du back-office à l'interface, "
        "au sein d'une équipe agile.",
        "Bizerte",
        "Bizerte",
        "CDI",
        WorkMode.ONSITE,
        "0 à 1 an",
        1500,
        2300,
        ("JavaScript", "TypeScript"),
        ("JavaScript Framework", "web programming", "Agile project management"),
    ),
    DemoOffer(
        "Stagiaire DevOps",
        "Stage de fin d'études : automatisation des déploiements et suivi de l'infrastructure "
        "cloud.",
        "Tunis",
        "Tunis",
        "INTERNSHIP",
        WorkMode.REMOTE,
        "Débutant",
        800,
        1000,
        ("cloud technologies",),
        ("tools for software configuration management",),
        publish=False,
    ),
)


@dataclass(frozen=True)
class DemoProgram:
    title: str
    description: str
    level: str
    skill_level: str
    delivery_mode: str
    price: int
    taught: tuple[str, ...]
    registration_deadline: date
    start_date: date
    end_date: date
    location_or_url: str


# Each program teaches a mandatory skill of a seeded offer that the main candidate lacks.
# shortcut: fixed session dates for the 2026-11-08 demo; move them forward to reuse the scenario.
PROGRAMS = (
    DemoProgram(
        "Bases de données PostgreSQL",
        "Modélisation, requêtes avancées et administration de PostgreSQL.",
        ProgramLevel.INTERMEDIATE,
        SkillLevel.INTERMEDIATE,
        DeliveryMode.PRESENTIAL,
        450,
        ("PostgreSQL", "database management systems"),
        date(2026, 11, 30),
        date(2026, 12, 7),
        date(2026, 12, 18),
        "Technopole de Sfax, salle 2",
    ),
    DemoProgram(
        "Tests logiciels et débogage",
        "Tests unitaires, couverture de code et débogage méthodique d'applications.",
        ProgramLevel.BEGINNER,
        SkillLevel.INTERMEDIATE,
        DeliveryMode.ONLINE,
        0,
        ("perform software unit testing", "debug software"),
        date(2026, 11, 25),
        date(2026, 11, 30),
        date(2026, 12, 11),
        "https://formation.demo.mahara.test/tests-logiciels",
    ),
    DemoProgram(
        "Introduction au Machine Learning",
        "Apprentissage supervisé, préparation des données et évaluation de modèles.",
        ProgramLevel.BEGINNER,
        SkillLevel.BEGINNER,
        DeliveryMode.HYBRID,
        600,
        ("utilise machine learning", "data mining"),
        date(2026, 12, 4),
        date(2026, 12, 14),
        date(2027, 1, 22),
        "Technopole de Sfax, salle 5",
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
                _offers()
                _programs()
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
        settings_flag = "--settings=backend.config.settings.development"
        self.stdout.write(
            "Next steps before the demo:\n"
            "  1. Build the retrieval index (needs Ollama):\n"
            "     uv run python backend/manage.py index_retrieval --schema public "
            f"{settings_flag}\n"
            "  2. Sign in as the administrator and authorize the Tanitjobs data source in the\n"
            "     admin Imports page, with permission evidence (Q17).\n"
            "  3. Run one import:\n"
            '     uv run python -m pipelines.ingestion.offer_import tanitjobs "python" '
            "--max-pages 1"
        )


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
    if not _exists(candidate.email):
        _register_candidate(candidate, password)
    user = User.objects.get_by_natural_key(candidate.email)
    profile = CandidateProfile.objects.filter(user=user).first()
    # No profile: an account this seed did not set up. Skills present: left as they are.
    if profile is None or CandidateSkill.objects.filter(candidate=profile).exists():
        return
    for label, level in candidate.skills:
        create_record(user, CandidateSkill, {"skill_id": _skill_id(label), "level": level})


def _register_candidate(candidate: DemoCandidate, password: str) -> None:
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


def _skill_id(label: str) -> Any:
    return Skill.objects.get(canonical_name=label).id


def _staff_member(staff: DemoStaff) -> tuple[User, Organization]:
    return (
        User.objects.get_by_natural_key(staff.email),
        Organization.objects.get(registration_number=staff.organization.registration_number),
    )


def _offers() -> None:
    recruiter, company = _staff_member(RECRUITER)
    deadline = timezone.localdate() + timedelta(days=OFFER_OPEN_DAYS)
    for spec in OFFERS:
        if JobOffer.objects.filter(organization=company, title=spec.title).exists():
            continue
        offer = create_job_offer(
            recruiter,
            {
                "organization_id": company.id,
                "title": spec.title,
                "description": spec.description,
                "contract_type": spec.contract_type,
                "work_mode": spec.work_mode,
                "experience_level": spec.experience_level,
                "country_code": "TN",
                "governorate": spec.governorate,
                "city": spec.city,
                "min_salary": spec.min_salary,
                "max_salary": spec.max_salary,
                "application_deadline": deadline,
                "easy_apply": True,
            },
        )
        for labels, mandatory in ((spec.mandatory, True), (spec.optional, False)):
            for label in labels:
                create_offer_skill(
                    recruiter,
                    {"offer_id": offer.id, "skill_id": _skill_id(label), "is_mandatory": mandatory},
                )
        if spec.publish:
            transition_offer(recruiter, offer.id, JobOfferStatus.PUBLISHED)


def _programs() -> None:
    manager, provider = _staff_member(TRAINING_MANAGER)
    for spec in PROGRAMS:
        # The session is created with its program, so a program found here is left alone.
        if TrainingProgram.objects.filter(organization=provider, title=spec.title).exists():
            continue
        program = create_program(
            manager,
            {
                "organization_id": provider.id,
                "title": spec.title,
                "description": spec.description,
                "level": spec.level,
                "delivery_mode": spec.delivery_mode,
                "is_free": spec.price == 0,
                "price": spec.price,
            },
        )
        for label in spec.taught:
            add_skill(
                manager,
                {
                    "program_id": program.id,
                    "skill_id": _skill_id(label),
                    "target_level": spec.skill_level,
                },
            )
        update_program(manager, program, {"status": ProgramStatus.ACTIVE})
        create_session(
            manager,
            {
                "program_id": program.id,
                "start_date": _local(spec.start_date, time(9)),
                "end_date": _local(spec.end_date, time(17)),
                "capacity": 20,
                "location_or_url": spec.location_or_url,
                "registration_deadline": _local(spec.registration_deadline, time(23, 59)),
            },
        )


def _local(day: date, at: time) -> datetime:
    return timezone.make_aware(datetime.combine(day, at))
