from rest_framework.routers import DefaultRouter

from backend.apps.taxonomy.api.views import EducationLevelViewSet, LanguageViewSet, SkillViewSet

router = DefaultRouter()
router.register("education-levels", EducationLevelViewSet, basename="education-level")
router.register("languages", LanguageViewSet, basename="language")
router.register("skills", SkillViewSet, basename="skill")
urlpatterns = router.urls
