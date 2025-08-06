from rest_framework.routers import DefaultRouter
from .views import ComplianceTagViewSet

router = DefaultRouter()
router.register(r"compliance-tags", ComplianceTagViewSet, basename="compliance-tag")

urlpatterns = router.urls