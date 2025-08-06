from rest_framework.routers import DefaultRouter
from .views import TargetViewSet

router = DefaultRouter()
router.register(r"targets", TargetViewSet, basename="target")

urlpatterns = router.urls