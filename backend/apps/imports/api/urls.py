from django.urls import path
from rest_framework.routers import DefaultRouter

from backend.apps.imports.api.views import BatchViewSet, RowViewSet, SourceViewSet

router = DefaultRouter()
router.register("data-sources", SourceViewSet, basename="data-source")
router.register("import-batches", BatchViewSet, basename="import-batch")

urlpatterns = [
    *router.urls,
    path(
        "import-rows/<uuid:pk>/",
        RowViewSet.as_view({"get": "retrieve"}),
        name="import-row-detail",
    ),
    path(
        "import-batches/<uuid:batch_id>/rows/",
        RowViewSet.as_view({"get": "list"}),
        name="import-batch-row-list",
    ),
]
