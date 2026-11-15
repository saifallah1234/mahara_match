from rest_framework.routers import DefaultRouter

from backend.apps.candidates.api.views import (
    CandidateLanguageViewSet,
    CandidatePreferenceViewSet,
    CandidateProfileViewSet,
    CandidateSkillViewSet,
    CertificationViewSet,
    CVAnalysisResultViewSet,
    CVReviewRoleViewSet,
    CVViewSet,
    EducationViewSet,
    ExperienceViewSet,
    ProjectViewSet,
)

router = DefaultRouter()
router.register("candidate-profiles", CandidateProfileViewSet, basename="candidate-profile")
router.register("experiences", ExperienceViewSet, basename="experience")
router.register("educations", EducationViewSet, basename="education")
router.register("candidate-languages", CandidateLanguageViewSet, basename="candidate-language")
router.register("candidate-skills", CandidateSkillViewSet, basename="candidate-skill")
router.register("certifications", CertificationViewSet, basename="certification")
router.register(
    "candidate-preferences", CandidatePreferenceViewSet, basename="candidate-preference"
)
router.register("projects", ProjectViewSet, basename="project")
router.register("cvs", CVViewSet, basename="cv")
router.register("cv-analysis-results", CVAnalysisResultViewSet, basename="cv-analysis-result")
router.register("cv-review-roles", CVReviewRoleViewSet, basename="cv-review-role")
urlpatterns = router.urls
