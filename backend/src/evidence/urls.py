from rest_framework.routers import DefaultRouter
from .views import EvidenceViewSet

router = DefaultRouter()
router.register(r"evidence", EvidenceViewSet, basename="evidence")

urlpatterns = router.urls