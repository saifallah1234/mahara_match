from django.urls import include, path
from rest_framework.routers import DefaultRouter

from backend.apps.training.api.enrollments_views import TrainingEnrollmentViewSet
from backend.apps.training.api.programs_views import TrainingProgramViewSet
from backend.apps.training.api.recommendations_views import TrainingRecommendationViewSet
from backend.apps.training.api.sessions_views import TrainingSessionViewSet
from backend.apps.training.api.skills_views import TrainingSkillViewSet

app_name = "training"

router = DefaultRouter()
router.register("programs", TrainingProgramViewSet, basename="program")
router.register("skills", TrainingSkillViewSet, basename="skill")
router.register("sessions", TrainingSessionViewSet, basename="session")
router.register("enrollments", TrainingEnrollmentViewSet, basename="enrollment")
router.register("recommendations", TrainingRecommendationViewSet, basename="recommendation")

urlpatterns = [
    path("", include(router.urls)),
]
