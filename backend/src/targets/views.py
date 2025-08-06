import requests
from requests.exceptions import RequestException
from urllib.parse import urlparse

from rest_framework import viewsets, permissions, status, filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Target
from .serializers import TargetSerializer
from .filters import TargetFilter


class TargetViewSet(viewsets.ModelViewSet):
    """
    CRUD for targets with filtering/search/ordering.
    Includes POST /targets/{id}/test-connection action performing a simple GET with 3s timeout.
    """
    queryset = Target.objects.select_related("project", "project__organization").all()
    serializer_class = TargetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = TargetFilter
    search_fields = ["name", "address", "slug"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["project__organization__name", "project__name", "name"]

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        """
        Attempts a simple GET to the target's address with a 3 second timeout.
        Returns JSON with status information and a subset of headers.
        """
        target = self.get_object()
        address = target.address or ""
        # Normalize to URL if looks like hostname without scheme
        url = address
        parsed = urlparse(address)
        if not parsed.scheme:
            # default to http
            url = f"http://{address}"

        try:
            resp = requests.get(url, timeout=3)
            header_subset = {k: v for k, v in resp.headers.items() if k.lower() in {"server", "content-type", "date"}}
            data = {
                "ok": True,
                "url": url,
                "status_code": resp.status_code,
                "reason": resp.reason,
                "headers": header_subset,
            }
            return Response(data, status=status.HTTP_200_OK)
        except RequestException as e:
            return Response(
                {"ok": False, "url": url, "error": str(e)},
                status=status.HTTP_200_OK,
            )