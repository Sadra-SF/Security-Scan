from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.views import ScansView  # legacy

urlpatterns = [
    path("admin/", admin.site.urls),

    # Health endpoints (must remain)
    path("api/v1/health/", include("health.urls")),

    # v1 API routers per app
    path("api/v1/", include(("projects.urls", "projects"), namespace="projects")),
    path("api/v1/", include(("targets.urls", "targets"), namespace="targets")),
    path("api/v1/", include(("scans.urls", "scans"), namespace="scans")),
    path("api/v1/", include(("findings.urls", "findings"), namespace="findings")),
    path("api/v1/", include(("evidence.urls", "evidence"), namespace="evidence")),
    path("api/v1/", include(("schedules.urls", "schedules"), namespace="schedules")),
    path("api/v1/", include(("notifications.urls", "notifications"), namespace="notifications")),
    path("api/v1/", include(("integrations.urls", "integrations"), namespace="integrations")),
    path("api/v1/", include(("compliance.urls", "compliance"), namespace="compliance")),
    path("api/v1/", include(("reports.urls", "reports"), namespace="reports")),

    # OpenAPI schema and Swagger UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # JWT auth
    path("api/auth/jwt/create", TokenObtainPairView.as_view(), name="jwt-obtain"),
    path("api/auth/jwt/refresh", TokenRefreshView.as_view(), name="jwt-refresh"),

    # Legacy (temporary, deprecated)
    path("api/legacy/scans/", ScansView.as_view(), name="legacy-scans"),
]