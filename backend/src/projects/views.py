from rest_framework import viewsets, permissions, filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import Project
from .serializers import ProjectSerializer
from .filters import ProjectFilter


class ProjectViewSet(viewsets.ModelViewSet):
    """
    CRUD for projects with filtering/search/ordering.
    """
    queryset = Project.objects.select_related("organization").all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ["name", "slug"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["organization__name", "name"]