import pytest

from backend.apps.identity.models import Organization, User
from backend.apps.recruitment.models import JobOffer
from backend.apps.recruitment.services.interview_demo import seed_interview_demo_offer
from backend.apps.recruitment.services.job_offers import get_job_offer
from backend.common.exceptions import DomainValidationError


@pytest.mark.django_db
def test_demo_offer_is_published_visible_and_repeatable(phase3):
    User.objects.create_superuser("demo-admin@example.test", first_name="Demo", last_name="Admin")
    offer = seed_interview_demo_offer()
    assert offer.status == "PUBLISHED"
    assert offer.organization.verification_status == "VERIFIED"
    assert offer.offer_skills.get().skill.canonical_name == "Python"
    assert get_job_offer(phase3["candidate"], offer.pk).pk == offer.pk
    assert seed_interview_demo_offer().pk == offer.pk
    assert JobOffer.objects.filter(organization=offer.organization).count() == 1


@pytest.mark.django_db
def test_demo_seed_without_privileged_actor_writes_nothing():
    with pytest.raises(DomainValidationError, match="active superuser"):
        seed_interview_demo_offer()
    assert not Organization.objects.exists()
    assert not JobOffer.objects.exists()
