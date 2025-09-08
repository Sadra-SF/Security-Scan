from rest_framework.routers import DefaultRouter
from .views import (
    ComplianceFrameworkViewSet, ComplianceControlViewSet,
    ComplianceAssessmentViewSet, ComplianceMappingViewSet,
    ComplianceTagViewSet
)

router = DefaultRouter()
router.register(r"frameworks", ComplianceFrameworkViewSet, basename="compliance-framework")
router.register(r"controls", ComplianceControlViewSet, basename="compliance-control")
router.register(r"assessments", ComplianceAssessmentViewSet, basename="compliance-assessment")
router.register(r"mappings", ComplianceMappingViewSet, basename="compliance-mapping")
router.register(r"compliance-tags", ComplianceTagViewSet, basename="compliance-tag")

urlpatterns = router.urls