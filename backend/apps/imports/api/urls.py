from django.urls import path
from rest_framework.routers import DefaultRouter

from backend.apps.imports.api.views import BatchViewSet, RowViewSet, SourceViewSet

router = DefaultRouter()
router.register("data-sources", SourceViewSet, basename="data-source")
router.register("import-batches", BatchViewSet, basename="import-batch")
router.register("import-rows", RowViewSet, basename="import-row")

urlpatterns = [
    *router.urls,
    path(
        "import-batches/<uuid:batch_id>/rows/",
        RowViewSet.as_view({"get": "list"}),
        name="import-batch-row-list",
    ),
]
