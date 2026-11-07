# Placement: backend/apps/reporting/api/urls.py
from django.urls import path

from backend.apps.reporting.api.views import IndicatorsView

urlpatterns = [path("indicators/", IndicatorsView.as_view(), name="reporting-indicators")]
