from rest_framework.routers import DefaultRouter
from .views import NotificationChannelViewSet, NotificationRuleViewSet

router = DefaultRouter()
router.register(r"notification-channels", NotificationChannelViewSet, basename="notification-channel")
router.register(r"notification-rules", NotificationRuleViewSet, basename="notification-rule")

urlpatterns = router.urls