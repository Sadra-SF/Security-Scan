from rest_framework import viewsets, permissions, status, filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Scan
from .serializers import ScanSerializer, TriggerScanSerializer
from .filters import ScanFilter
from scans.tasks import start_scan


class ScanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for Scan with filtering/search/ordering.
    Provides POST /api/v1/scans/trigger to create a queued Scan and enqueue Celery task.
    """
    queryset = Scan.objects.select_related("target", "target__project", "target__project__organization").all()
    serializer_class = ScanSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ScanFilter
    search_fields = ["scanner"]
    ordering_fields = ["started_at", "created_at"]
    ordering = ["-started_at", "-created_at"]

    @action(detail=False, methods=["post"], url_path="trigger")
    def trigger(self, request):
        """
        Body: { "target_id": UUID, "mode|type": "...", "scanner_keys": ["zap", "nmap"]? }
        Creates Scan row in 'pending' and enqueues scans.tasks.start_scan.delay(scan.id).
        """
        serializer = TriggerScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data["target"]
        scan_type = serializer.validated_data["type"]
        scanner_keys = serializer.validated_data.get("scanner_keys") or []

        scan = Scan.objects.create(
            target=target,
            scanner=",".join(scanner_keys) if scanner_keys else "auto",
            type=scan_type,
            status=Scan.Status.PENDING,
            config={},
        )

        # enqueue celery task
        start_scan.delay(str(scan.id))

        return Response(ScanSerializer(scan).data, status=status.HTTP_201_CREATED)