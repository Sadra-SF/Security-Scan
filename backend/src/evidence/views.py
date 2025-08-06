from rest_framework import viewsets, permissions, filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import Evidence
from .serializers import EvidenceSerializer


class EvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only Evidence endpoints, primarily filtered by finding.
    """
    queryset = Evidence.objects.select_related("finding").all()
    serializer_class = EvidenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["finding"]
    search_fields = ["content_type", "storage_url", "metadata"]
    ordering_fields = ["created_at", "size"]
    ordering = ["-created_at"]