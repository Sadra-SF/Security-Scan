from rest_framework.routers import DefaultRouter
from .views import FindingViewSet

router = DefaultRouter()
router.register(r"findings", FindingViewSet, basename="finding")

# Routes include:
# - /findings/ (list)
# - /findings/{id}/ (retrieve)
# - /findings/bulk-update/ (POST)
# - /findings/dashboard-summary/ (GET)

urlpatterns = router.urls