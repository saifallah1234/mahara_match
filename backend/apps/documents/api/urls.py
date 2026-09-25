from rest_framework.routers import DefaultRouter

from backend.apps.documents.api.views import DocumentViewSet

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
urlpatterns = router.urls
