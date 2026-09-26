from rest_framework.routers import DefaultRouter

from backend.apps.matching.api.offer_matches_views import OfferMatchViewSet

router = DefaultRouter()
router.register("offer-matches", OfferMatchViewSet, basename="offer-match")

urlpatterns = router.urls
