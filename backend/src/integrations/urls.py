from rest_framework.routers import DefaultRouter
from .views import IntegrationTokenViewSet, WebhookViewSet

router = DefaultRouter()
router.register(r"integration-tokens", IntegrationTokenViewSet, basename="integration-token")
router.register(r"webhooks", WebhookViewSet, basename="webhook")

urlpatterns = router.urls