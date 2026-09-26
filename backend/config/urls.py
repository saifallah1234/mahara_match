from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("backend.apps.identity.api.urls")),
    path("api/v1/training/", include("backend.apps.training.api.urls")),
    path("api/v1/", include("backend.apps.taxonomy.api.urls")),
    path("api/v1/", include("backend.apps.documents.api.urls")),
    path("api/v1/", include("backend.apps.candidates.api.urls")),
    path("api/v1/", include("backend.apps.recruitment.api.urls")),
    path("api/v1/", include("backend.apps.matching.services.urls")),
    path("api/v1/", include("backend.apps.assistant.api.urls")),
    path("api/v1/", include("backend.apps.platform.api.urls")),
    path("api/v1/", include("backend.apps.imports.api.urls")),
]
