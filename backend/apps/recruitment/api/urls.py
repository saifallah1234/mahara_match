from rest_framework.routers import DefaultRouter

from backend.apps.recruitment.api.application_status_history_views import (
    ApplicationStatusHistoryViewSet,
)
from backend.apps.recruitment.api.applications_views import ApplicationViewSet
from backend.apps.recruitment.api.interviews_views import InterviewViewSet
from backend.apps.recruitment.api.job_offers_views import JobOfferViewSet
from backend.apps.recruitment.api.offer_skills_views import OfferSkillViewSet

router = DefaultRouter()
router.register("job-offers", JobOfferViewSet, basename="job-offer")
router.register("offer-skills", OfferSkillViewSet, basename="offer-skill")
router.register("applications", ApplicationViewSet, basename="application")
router.register(
    "application-status-history",
    ApplicationStatusHistoryViewSet,
    basename="application-status-history",
)
router.register("interviews", InterviewViewSet, basename="interview")

urlpatterns = router.urls
