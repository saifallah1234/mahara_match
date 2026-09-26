from rest_framework.routers import DefaultRouter

from backend.apps.platform.api.views import AuditViewSet, NotificationViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register("audit-logs", AuditViewSet, basename="audit-log")

urlpatterns = router.urls
