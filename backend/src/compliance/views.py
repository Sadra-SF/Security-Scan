from rest_framework import viewsets, permissions, filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import ComplianceTag
from .serializers import ComplianceTagSerializer


class ComplianceTagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list of Compliance Tags.
    """
    queryset = ComplianceTag.objects.all()
    serializer_class = ComplianceTagSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["category", "slug"]
    search_fields = ["slug", "title", "description", "category"]
    ordering_fields = ["category", "slug", "title", "created_at"]
    ordering = ["category", "slug"]