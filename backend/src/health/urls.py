from django.urls import path
from .views import HealthCheckView, CeleryHealthView

urlpatterns = [
    path("", HealthCheckView.as_view(), name="health"),
    path("celery/", CeleryHealthView.as_view(), name="health-celery"),
]