"""Explicit operator seed for the frontend interview test; no public API."""

from django.db import transaction

from backend.apps.identity.models import User
from backend.apps.identity.services.organizations import (
    create_organization,
    list_organizations,
    verify_organization,
)
from backend.apps.recruitment.models import JobOffer
from backend.apps.recruitment.services.job_offers import create_job_offer, list_job_offers
from backend.apps.recruitment.services.offer_lifecycle import transition_offer
from backend.apps.recruitment.services.offer_skills import create_offer_skill, list_offer_skills
from backend.apps.taxonomy.services.catalog import seed_interview_demo_skill
from backend.common.exceptions import DomainValidationError

COMPANY = "Mahara Interview Demo — TEST"
REGISTRATION = "MAHARA-INTERVIEW-DEMO-TEST"
TITLE = "Développeur Python junior — Offre de test"


@transaction.atomic
def seed_interview_demo_offer() -> JobOffer:
    actor = User.objects.filter(is_superuser=True, status="ACTIVE", deleted_at__isnull=True).first()
    if actor is None:
        raise DomainValidationError(
            "An existing active superuser is required; no account was created."
        )
    organization = list_organizations(actor).filter(registration_number=REGISTRATION).first()
    if organization is None:
        organization = create_organization(
            actor,
            {
                "type": "COMPANY",
                "legal_name": COMPANY,
                "registration_number": REGISTRATION,
                "matricule_fiscal": "9999999Z99999",
                "description": "Entreprise fictive pour tester les entretiens blancs. Aucun recrutement réel.",
                "governorate": "Tunis",
                "city": "Tunis",
            },
        )
    if organization.legal_name != COMPANY or organization.deleted_at:
        raise DomainValidationError("The demo identifier belongs to a different organization.")
    if organization.verification_status == "PENDING":
        verify_organization(actor, organization)
    if organization.verification_status != "VERIFIED":
        raise DomainValidationError("The demo company cannot be used in its current state.")
    offer = list_job_offers(actor).filter(organization=organization, title=TITLE).first()
    if offer is None:
        offer = create_job_offer(
            actor,
            {
                "organization_id": organization.pk,
                "title": TITLE,
                "description": (
                    "OFFRE FICTIVE — TEST TECHNIQUE, aucun recrutement réel. "
                    "Nous recherchons un développeur Python junior pour créer des API Django, "
                    "travailler avec PostgreSQL et Git, écrire des tests et collaborer en équipe. "
                    "Expliquez un projet, votre façon de résoudre un problème et votre motivation."
                ),
                "contract_type": "CDI",
                "work_mode": "HYBRID",
                "experience_level": "JUNIOR",
                "country_code": "TN",
                "governorate": "Tunis",
                "city": "Tunis",
                "easy_apply": True,
            },
        )
    skill = seed_interview_demo_skill(actor)
    if not list_offer_skills(actor, offer.pk).filter(skill=skill).exists():
        create_offer_skill(
            actor,
            {
                "offer_id": offer.pk,
                "skill_id": skill.pk,
                "required_level": "INTERMEDIATE",
                "is_mandatory": True,
            },
        )
    if offer.status == "DRAFT":
        offer = transition_offer(actor, offer.pk, "PUBLISHED")
    if offer.status != "PUBLISHED":
        raise DomainValidationError(
            "The demo offer is no longer published; its state was preserved."
        )
    return offer
